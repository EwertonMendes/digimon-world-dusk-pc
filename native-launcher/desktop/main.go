//go:build windows

// Digimon World Dusk PC native desktop launcher.
// No HTTP server, browser, WSL, external emulator, or build tools at runtime.
// A private ROM-owner build appends a SHA256-authenticated ZIP and fixed footer.
package main

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
)

const (
	magic      = "DUSKPACKv1!!"
	footerSize = 52
	romSHA256  = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"
)

// readPayload rejects unknown files and untrusted/unbounded sizes.
func readPayload(executable string) (map[string][]byte, error) {
	f, err := os.Open(executable)
	if err != nil { return nil, err }
	defer f.Close()
	stat, err := f.Stat()
	if err != nil { return nil, err }
	if stat.Size() < footerSize { return nil, errors.New("pacote privado não encontrado") }
	trailer := make([]byte, footerSize)
	if _, err = f.ReadAt(trailer, stat.Size()-footerSize); err != nil { return nil, err }
	if string(trailer[:12]) != magic { return nil, errors.New("pacote não assinado no executável") }
	n := binary.LittleEndian.Uint64(trailer[12:20])
	if n == 0 || n > 150<<20 || int64(n) > stat.Size()-footerSize {
		return nil, errors.New("tamanho do pacote inválido")
	}
	buffer := make([]byte, int(n))
	if _, err = f.ReadAt(buffer, stat.Size()-footerSize-int64(n)); err != nil { return nil, err }
	checksum := sha256.Sum256(buffer)
	if !bytes.Equal(checksum[:], trailer[20:52]) { return nil, errors.New("assinatura do pacote divergente") }
	reader, err := zip.NewReader(bytes.NewReader(buffer), int64(n))
	if err != nil { return nil, err }
	required := map[string]uint64{"runner.exe":100 << 20, "game.nds":100 << 20, "SDL3.dll":20 << 20}
	if len(reader.File) != len(required) { return nil, errors.New("quantidade de arquivos incorreta") }
	contents := make(map[string][]byte, len(required))
	for _, entry := range reader.File {
		max, ok := required[entry.Name]
		if !ok || entry.UncompressedSize64 > max || entry.FileInfo().IsDir() {
			return nil, fmt.Errorf("arquivo privado inválido: %s", entry.Name)
		}
		if _, present := contents[entry.Name]; present { return nil, fmt.Errorf("arquivo duplicado: %s", entry.Name) }
		r, err := entry.Open()
		if err != nil { return nil, err }
		b, err := io.ReadAll(io.LimitReader(r, int64(max)+1))
		r.Close()
		if err != nil || uint64(len(b)) != entry.UncompressedSize64 { return nil, errors.New("arquivo extraído inválido") }
		contents[entry.Name] = b
	}
	romHash := sha256.Sum256(contents["game.nds"])
	if hex.EncodeToString(romHash[:]) != romSHA256 { return nil, errors.New("esta versão exige Dusk USA original") }
	if !bytes.HasPrefix(contents["runner.exe"], []byte("MZ")) { return nil, errors.New("runner Windows inválido") }
	if !bytes.HasPrefix(contents["SDL3.dll"], []byte("MZ")) { return nil, errors.New("SDL3 inválido") }
	return contents, nil
}

func provision(path string, files map[string][]byte) error {
	for name, b := range files {
		dst := filepath.Join(path, name)
		old, err := os.ReadFile(dst)
		if err == nil {
            if sha256.Sum256(old) == sha256.Sum256(b) { continue }
            return fmt.Errorf("a instalação %s já contém um runtime diferente; atualize appVersion em vez de sobrescrever o executável existente", path)
        }
        if !errors.Is(err, os.ErrNotExist) { return err }
		tmp, err := os.CreateTemp(path, name+".*.tmp")
		if err != nil { return err }
		temp := tmp.Name()
		if _, err = tmp.Write(b); err == nil { err = tmp.Sync() }
		closeErr := tmp.Close()
		if err == nil { err = closeErr }
		if err != nil { os.Remove(temp); return err }
		// Windows rename cannot replace an open existing file. A failed update
		// is explicit; never fall back to executing stale/unverified code.
		if err = os.Rename(temp, dst); err != nil { os.Remove(temp); return err }
        verified := sha256.Sum256(b)
        diskBytes, readErr := os.ReadFile(dst)
        if readErr != nil || sha256.Sum256(diskBytes) != verified { return fmt.Errorf("arquivo instalado não passou na validação SHA-256: %s (%v)", name, readErr) }
	}
	return nil
}

func launch(p gamePaths) error {
	logPath := filepath.Join(p.install, "native-performance.log")
	file, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil { return err }
	defer file.Close()
	// Firmware identity, firmware state and in-game EEPROM belong to the player,
	// never to a release folder. No savestate directory is configured.
	args := runnerArgs(p)
	cmd := exec.Command(filepath.Join(p.install, "runner.exe"), args...)
	cmd.Dir = p.install
	cmd.Stdout, cmd.Stderr = file, file
	cmd.Env = append(os.Environ(), "NDS_FRONTEND_STATS=1", "NDS_DEEP_TRACE=0", "NDS_DUSK_NATIVE_UI=1", "NDS_DUSK_DISABLE_SAVESTATES=1")
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000} // CREATE_NO_WINDOW: SDL window remains visible
	if err := cmd.Start(); err != nil { return err }
	if err := cmd.Wait(); err != nil {
		return fmt.Errorf("jogo terminou com erro: %w (consulte %s)", err, logPath)
	}
	return nil
}

func main() {
	exe, err := os.Executable()
	if err != nil { fatal(err) }
	files, err := readPayload(exe)
	if err != nil { fatal(err) }
	if len(os.Args)==2 && strings.EqualFold(os.Args[1],"--verify-bundle") {
		fmt.Printf("Pacote privado Dusk %s íntegro\n", appVersion)
		return
	}
	base := os.Getenv("LOCALAPPDATA")
	if base == "" { fatal(errors.New("LOCALAPPDATA indisponível")) }
	p := pathsFor(base)
	release, err := acquireSaveSession()
	if err != nil { fatal(err) }
	defer release()
    if (len(os.Args) == 1 && shiftHeld()) || (len(os.Args) == 2 && strings.EqualFold(os.Args[1], "--manage-saves")) {
        if err := manageSaves(p); err != nil { fatal(err) }
        return
    }
    if len(os.Args) == 2 && strings.HasPrefix(os.Args[1], "--restore-backup=") {
        if err := ensureGameDirectories(p); err != nil { fatal(err) }
        if err := recoverInterruptedRestore(p); err != nil { fatal(err) }
        name := strings.TrimPrefix(os.Args[1], "--restore-backup=")
        if err := restoreBackup(p,name); err != nil { fatal(err) }
        fmt.Println("Backup validado e restaurado:", name)
        return
    }
    if len(os.Args) != 1 { fatal(errors.New("argumento de inicialização desconhecido")) }
	if err := prepareGameData(p, base); err != nil { fatal(err) }
	if err := provision(p.install, files); err != nil { fatal(err) }
	if err := launch(p); err != nil { fatal(err) }
}