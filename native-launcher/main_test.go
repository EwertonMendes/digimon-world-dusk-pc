package main

import (
  "encoding/binary"
  "crypto/sha256"
  "encoding/json"
  "os"
  "path/filepath"
  "strings"
  "testing"
)

func TestBundleTrailerInvariant(t *testing.T) {
  if len(footerMagic) != 12 || footerSize != 52 {
    t.Fatalf("private payload trailer format incompatible: magic %d, footer %d", len(footerMagic), footerSize)
  }
}

func TestNoBundleIsRejected(t *testing.T) {
  path := filepath.Join(t.TempDir(), "plain-launcher.exe")
  if err := os.WriteFile(path, []byte("not a private Dusk bundle"), 0600); err != nil {
    t.Fatal(err)
  }
  if _, err := getBundle(path); err == nil {
    t.Fatal("ROM-free launcher must reject absent private payload")
  }
}

func TestCorruptPrivateBundleRejected(t *testing.T) {
  path := filepath.Join(t.TempDir(), "bad.exe")
  footer := make([]byte, footerSize)
  copy(footer, []byte(footerMagic))
  binary.LittleEndian.PutUint64(footer[12:], 5)
  sum := sha256.Sum256([]byte("wrong"))
  copy(footer[20:], sum[:])
  data := append([]byte("fake windows header"),
    append([]byte("hello"), footer...)...)
  if err := os.WriteFile(path, data, 0600); err != nil { t.Fatal(err) }
  if _, err := getBundle(path); err == nil ||
     !strings.Contains(err.Error(), "private payload integrity mismatch") {
    t.Fatalf("expected integrity error, got %v", err)
  }
}

func TestMissingGuestField(t *testing.T) {
  if _, err := fieldInt(map[string]json.RawMessage{}, "vblank9"); err == nil {
    t.Fatal("missing native cycle counter must be rejected")
  }
}

func TestInvalidGuestField(t *testing.T) {
  if _, err := fieldInt(map[string]json.RawMessage{
    "vblank9": json.RawMessage(`"not a number"`),
  }, "vblank9"); err == nil {
    t.Fatal("invalid counter must be rejected")
  }
}
