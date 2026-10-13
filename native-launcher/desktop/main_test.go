//go:build windows

package main

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"os"
	"path/filepath"
	"testing"
)

func TestRejectsExecutableWithoutPrivateBundle(t *testing.T) {
	p := filepath.Join(t.TempDir(), "empty.exe")
	if err := os.WriteFile(p, []byte("MZ"), 0600); err != nil { t.Fatal(err) }
	if _, err := readPayload(p); err == nil { t.Fatal("missing footer was accepted") }
}

func TestRejectsTamperedPrivatePayload(t *testing.T) {
	var stream bytes.Buffer
	z := zip.NewWriter(&stream)
	w, err := z.Create("game.nds")
	if err != nil { t.Fatal(err) }
	_, _ = w.Write([]byte("not a ROM"))
	if err := z.Close(); err != nil { t.Fatal(err) }
	data := stream.Bytes()
	hash := sha256.Sum256(data)
	buf := append([]byte("MZ-test"), data...)
	buf = append(buf, []byte(magic)...)
	n := make([]byte, 8)
	binary.LittleEndian.PutUint64(n, uint64(len(data)))
	buf = append(append(buf, n...), hash[:]...)
	buf[len(buf)-footerSize-1] ^= 0x01 // tamper archive after hashing
	path := filepath.Join(t.TempDir(), "tampered.exe")
	if err := os.WriteFile(path, buf, 0600); err != nil { t.Fatal(err) }
	if _, err := readPayload(path); err == nil { t.Fatal("tampering was accepted") }
}

func TestProvisionKeepsIdentityAndReusesFiles(t *testing.T) {
	dir := t.TempDir()
	files := map[string][]byte{"runner.exe":[]byte("MZmock"), "SDL3.dll":[]byte("MZmock"), "game.nds":[]byte("synthetic")}
	if err := provision(dir, files); err != nil { t.Fatal(err) }
	id := filepath.Join(dir, "generated-identity.bin")
	old, err := os.ReadFile(id)
	if err != nil { t.Fatal(err) }
	if len(old) != 6 { t.Fatalf("identity bytes: %d",len(old)) }
	if err := provision(dir, files); err != nil { t.Fatal(err) }
	now, err := os.ReadFile(id)
	if err != nil { t.Fatal(err) }
	if !bytes.Equal(old, now) { t.Fatal("persistent identity was replaced") }
}
