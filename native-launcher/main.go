package main

import (
	"archive/zip"
	"bufio"
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"embed"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"image"
	"image/png"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"sync"
	"time"
)

const (
	version           = "0.4.0-alpha"
	romSHA256         = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"
	footerMagic       = "DUSKPACKv1!!"
	footerSize        = 12 + 8 + 32
	nativeFrameWidth  = 256
	nativeFrameHeight = 192
)

//go:embed web/ui.html
var fs embed.FS

type payloadFile struct {
	Name string
	data []byte
}

type nativeClient struct {
	conn   net.Conn
	reader *bufio.Reader
	mu     sync.Mutex
}

func (c *nativeClient) command(command string, params map[string]any) (map[string]json.RawMessage, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	m := map[string]any{"cmd": command}
	for k, v := range params {
		m[k] = v
	}
	line, err := json.Marshal(m)
	if err != nil {
		return nil, err
	}
	if err = c.conn.SetDeadline(time.Now().Add(120 * time.Second)); err != nil {
		return nil, err
	}
	if _, err = c.conn.Write(append(line, '\n')); err != nil {
		return nil, err
	}
	reply, err := c.reader.ReadBytes('\n')
	if err != nil {
		return nil, err
	}
	if len(reply) > 2_000_000 {
		return nil, errors.New("native debug reply too large")
	}
	var parsed map[string]json.RawMessage
	if err = json.Unmarshal(reply, &parsed); err != nil {
		return nil, err
	}
	if e, exists := parsed["error"]; exists {
		return nil, fmt.Errorf("native %s: %s", command, e)
	}
	return parsed, nil
}
func fieldInt(m map[string]json.RawMessage, k string) (int64, error) {
	v, ok := m[k]
	if !ok {
		return 0, fmt.Errorf("missing %s", k)
	}
	var n int64
	err := json.Unmarshal(v, &n)
	return n, err
}
func (c *nativeClient) advance(frames int) (int64, error) {
	m, err := c.command("event_counts", nil)
	if err != nil {
		return 0, err
	}
	n, err := fieldInt(m, "vblank9")
	if err != nil {
		return 0, err
	}
	target := n + int64(frames)
	for i := 0; i < 20; i++ {
		m, err = c.command("run_to_event", map[string]any{"event": "vblank9", "count": target, "max_rounds": 2500000})
		if err != nil {
			return 0, err
		}
		if string(m["terminal"]) == "true" || string(m["stalled"]) == "true" {
			return 0, fmt.Errorf("guest execution terminal/stalled: %v", m)
		}
		m, err = c.command("event_counts", nil)
		if err != nil {
			return 0, err
		}
		n, err = fieldInt(m, "vblank9")
		if err != nil {
			return 0, err
		}
		if n >= target {
			return n, nil
		}
	}
	return 0, errors.New("guest frame deadline exceeded")
}
func (c *nativeClient) framePNG(engine string) (string, error) {
	m, err := c.command("framebuffer", map[string]any{"engine": engine})
	if err != nil {
		return "", err
	}
	w, err := fieldInt(m, "w")
	if err != nil {
		return "", err
	}
	h, err := fieldInt(m, "h")
	if err != nil {
		return "", err
	}
	if w != nativeFrameWidth || h != nativeFrameHeight {
		return "", fmt.Errorf("invalid frame dimensions %dx%d", w, h)
	}
	var hexText string
	if err = json.Unmarshal(m["rgb"], &hexText); err != nil {
		return "", err
	}
	rgb, err := hex.DecodeString(hexText)
	if err != nil {
		return "", err
	}
	if len(rgb) != nativeFrameWidth*nativeFrameHeight*3 {
		return "", errors.New("invalid frame pixel count")
	}
	frame := image.NewRGBA(image.Rect(0, 0, nativeFrameWidth, nativeFrameHeight))
	for i := 0; i < nativeFrameWidth*nativeFrameHeight; i++ {
		frame.Pix[4*i] = rgb[3*i]
		frame.Pix[4*i+1] = rgb[3*i+1]
		frame.Pix[4*i+2] = rgb[3*i+2]
		frame.Pix[4*i+3] = 255
	}
	var buf bytes.Buffer
	if err = png.Encode(&buf, frame); err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(buf.Bytes()), nil
}

func getBundle(exe string) ([]payloadFile, error) {
	f, err := os.Open(exe)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	fi, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if fi.Size() < footerSize {
		return nil, errors.New("missing bundled game: executable too small")
	}
	if _, err = f.Seek(-footerSize, io.SeekEnd); err != nil {
		return nil, err
	}
	footer := make([]byte, footerSize)
	if _, err = io.ReadFull(f, footer); err != nil {
		return nil, err
	}
	if string(footer[:12]) != footerMagic {
		return nil, errors.New("ROM-free launcher: no private payload was appended")
	}
	sz := binary.LittleEndian.Uint64(footer[12:20])
	if sz == 0 || sz > 200*1024*1024 || int64(sz) > fi.Size()-footerSize {
		return nil, errors.New("invalid private payload length")
	}
	if _, err = f.Seek(fi.Size()-footerSize-int64(sz), io.SeekStart); err != nil {
		return nil, err
	}
	payload := make([]byte, int(sz))
	if _, err = io.ReadFull(f, payload); err != nil {
		return nil, err
	}
	hash := sha256.Sum256(payload)
	if !bytes.Equal(hash[:], footer[20:]) {
		return nil, errors.New("private payload integrity mismatch")
	}
	zr, err := zip.NewReader(bytes.NewReader(payload), int64(sz))
	if err != nil {
		return nil, err
	}
	allowed := map[string]bool{"runner.exe": true, "game.nds": true}
	extracted := map[string][]byte{}
	for _, entry := range zr.File {
		if !allowed[entry.Name] || entry.UncompressedSize64 > 100*1024*1024 {
			return nil, fmt.Errorf("unrecognized private archive entry: %q", entry.Name)
		}
		if _, ok := extracted[entry.Name]; ok {
			return nil, fmt.Errorf("duplicate payload entry %q", entry.Name)
		}
		fd, err := entry.Open()
		if err != nil {
			return nil, err
		}
		data, err := io.ReadAll(io.LimitReader(fd, int64(entry.UncompressedSize64)+1))
		fd.Close()
		if err != nil {
			return nil, err
		}
		if len(data) != int(entry.UncompressedSize64) {
			return nil, errors.New("payload entry size mismatch")
		}
		extracted[entry.Name] = data
	}
	if len(extracted) != 2 {
		return nil, errors.New("missing ROM or recompilation runtime")
	}
	r := sha256.Sum256(extracted["game.nds"])
	if hex.EncodeToString(r[:]) != romSHA256 {
		return nil, errors.New("bundled ROM checksum mismatch")
	}
	if b := extracted["runner.exe"]; len(b) < 0x100 || b[0] != 'M' || b[1] != 'Z' {
		return nil, errors.New("bundled native runner is not a Windows executable")
	}
	return []payloadFile{{"runner.exe", extracted["runner.exe"]}, {"game.nds", extracted["game.nds"]}}, nil
}
func prepareUserData() (string, error) {
	base := os.Getenv("LOCALAPPDATA")
	if base == "" {
		base = os.TempDir()
	}
	dir := filepath.Join(base, "DuskNativePC", "v0.4")
	if err := os.MkdirAll(dir, 0700); err != nil {
		return "", err
	}
	identity := filepath.Join(dir, "generated-identity.bin")
	if _, err := os.Stat(identity); errors.Is(err, os.ErrNotExist) {
		data := make([]byte, 6)
		if _, err = rand.Read(data); err != nil {
			return "", err
		}
		data[0] = (data[0] | 2) &^ byte(1)
		if err = os.WriteFile(identity, data, 0600); err != nil {
			return "", err
		}
	}
	return dir, nil
}
func writePayload(dir string, files []payloadFile) error {
	for _, f := range files {
		name := filepath.Join(dir, f.Name)
		sum := sha256.Sum256(f.data)
		old, err := os.ReadFile(name)
		if err == nil {
			oldSum := sha256.Sum256(old)
			if bytes.Equal(sum[:], oldSum[:]) {
				continue
			}
		}
		temp := name + ".new"
		if err = os.WriteFile(temp, f.data, 0600); err != nil {
			return err
		}
		if err = os.Rename(temp, name); err != nil {
			os.Remove(temp)
			return err
		}
	}
	return nil
}
func openBrowser(url string) error {
	if runtime.GOOS == "windows" {
		return exec.Command("rundll32.exe", "url.dll,FileProtocolHandler", url).Start()
	}
	return nil
}
func listenClient(port int, cmd *exec.Cmd) (*nativeClient, error) {
	for i := 0; i < 500; i++ {
		conn, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 120*time.Millisecond)
		if err == nil {
			return &nativeClient{conn: conn, reader: bufio.NewReaderSize(conn, 1024*1024)}, nil
		}
		if cmd.ProcessState != nil && cmd.ProcessState.Exited() {
			return nil, errors.New("runner process ended early")
		}
		time.Sleep(100 * time.Millisecond)
	}
	return nil, errors.New("native runner did not open loopback debug server")
}
func token() string {
	b := make([]byte, 20)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b)
}

func main() {
	flagSelfTest := flag.Bool("self-test", false, "verify package integrity and return")
	flag.Parse()
	exe, err := os.Executable()
	if err != nil {
		log.Fatal(err)
	}
	files, err := getBundle(exe)
	if *flagSelfTest {
		if err != nil {
			fmt.Println("CHECK: ROM-free launcher, private bundle required:", err)
			return
		}
		fmt.Println("CHECK: verified private Dusk US payload, Windows native runner, version", version)
		return
	}
	if err != nil {
		log.Fatal("Este executável não contém o pacote privado de Dusk: ", err)
	}
	dir, err := prepareUserData()
	if err != nil {
		log.Fatal(err)
	}
	if err = writePayload(dir, files); err != nil {
		log.Fatal(err)
	}
	logPath := filepath.Join(dir, "native-preview.log")
	logger, err := os.OpenFile(logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		log.Fatal(err)
	}
	defer logger.Close()
	debugPort := 19878
	child := exec.Command(filepath.Join(dir, "runner.exe"), dir, "--serve", "--port", strconv.Itoa(debugPort), "--rom", filepath.Join(dir, "game.nds"), "--no-save", "--boot", "direct", "--generated-firmware", "--freebios", "--network", "off")
	child.Dir = dir
	child.Stdout = logger
	child.Stderr = logger
	if err = child.Start(); err != nil {
		log.Fatal("Não conseguiu iniciar o runtime Windows: ", err)
	}
	defer func() { child.Process.Kill(); child.Wait() }()
	client, err := listenClient(debugPort, child)
	if err != nil {
		log.Fatal(err)
	}
	defer client.conn.Close()
	if _, err = client.command("reset", nil); err != nil {
		log.Fatal(err)
	}
	if _, err = client.command("keys", map[string]any{"mask": 4095}); err != nil {
		log.Fatal(err)
	}
	if _, err = client.command("touch", map[string]any{"x": 0, "y": 0, "down": false}); err != nil {
		log.Fatal(err)
	}
	securityToken := token()
	html, err := fs.ReadFile("web/ui.html")
	if err != nil {
		log.Fatal(err)
	}
	html = bytes.ReplaceAll(html, []byte("{{TOKEN}}"), []byte(securityToken))
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		w.Write(html)
	})
	var ioMutex sync.Mutex
	authorized := func(r *http.Request) bool {
		return r.Header.Get("X-Dusk-Token") == securityToken && r.Header.Get("Origin") != "http://localhost:8790.invalid"
	}
	mux.HandleFunc("/api/frame", func(w http.ResponseWriter, r *http.Request) {
		if !authorized(r) {
			http.Error(w, "unauthorized", 403)
			return
		}
		ioMutex.Lock()
		defer ioMutex.Unlock()
		n := 2
		if q, err := strconv.Atoi(r.URL.Query().Get("frames")); err == nil && q >= 1 && q <= 12 {
			n = q
		}
		current, err := client.advance(n)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		a, err := client.framePNG("A")
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		b, err := client.framePNG("B")
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		json.NewEncoder(w).Encode(map[string]any{"A": a, "B": b, "frame": current})
	})
	mux.HandleFunc("/api/input", func(w http.ResponseWriter, r *http.Request) {
		if !authorized(r) || r.Method != "POST" {
			http.Error(w, "unauthorized", 403)
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, 8192)
		var data struct {
			Mask  int `json:"mask"`
			Touch *struct {
				X    int  `json:"x"`
				Y    int  `json:"y"`
				Down bool `json:"down"`
			} `json:"touch"`
		}
		if err = json.NewDecoder(r.Body).Decode(&data); err != nil {
			http.Error(w, "invalid input", 400)
			return
		}
		if data.Mask < 0 || data.Mask > 4095 {
			http.Error(w, "invalid mask", 400)
			return
		}
		ioMutex.Lock()
		defer ioMutex.Unlock()
		if _, err := client.command("keys", map[string]any{"mask": data.Mask}); err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		x, y, down := 0, 0, false
		if data.Touch != nil {
			x, y, down = data.Touch.X, data.Touch.Y, data.Touch.Down
		}
		if x < 0 || x >= 256 || y < 0 || y >= 192 {
			http.Error(w, "touch outside screen", 400)
			return
		}
		if _, err := client.command("touch", map[string]any{"x": x, "y": y, "down": down}); err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte("{\"ok\":true}"))
	})
	address := "127.0.0.1:8790"
	server := &http.Server{Addr: address, Handler: mux, ReadHeaderTimeout: 3 * time.Second}
	listener, err := net.Listen("tcp", address)
	if err != nil {
		log.Fatal("Porta ocupada: ", err)
	}
	url := "http://localhost:8790/"
	if err := openBrowser(url); err != nil {
		log.Println("Abra", url, err)
	}
	log.Println("Dusk Windows Native Preview", version, "available at", url, "logs", logPath)
	if err := server.Serve(listener); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
