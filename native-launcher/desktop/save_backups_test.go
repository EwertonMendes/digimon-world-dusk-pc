package main

import (
    "bytes"
    "os"
    "path/filepath"
    "strings"
    "testing"
)

func TestBackupsDeduplicateIdenticalProgress(t *testing.T) {
    p := pathsFor(t.TempDir())
    putSave(t, p.save, 0x15, duskSaveSize)
    for i := 0; i < 5; i++ {
        if err := makeBackup(p); err != nil { t.Fatal(err) }
    }
    names, err := listBackups(p)
    if err != nil || len(names) != 1 { t.Fatalf("expected one unique backup: %v %v", names, err) }
}

func TestBackupsRotateDistinctProgress(t *testing.T) {
    p := pathsFor(t.TempDir())
    for i := 0; i < maxAutomaticBackups + 5; i++ {
        putSave(t, p.save, byte(i+1), duskSaveSize)
        if err := makeBackup(p); err != nil { t.Fatal(err) }
    }
    names, err := listBackups(p)
    if err != nil || len(names) != maxAutomaticBackups {
        t.Fatalf("expected last %d backups: %d %v", maxAutomaticBackups, len(names), err)
    }
    _, lastHash, err := validateBackup(p, names[0])
    nowHash, _ := hashFile(p.save)
    if err != nil || lastHash != nowHash { t.Fatal("newest backup not retained", err) }
}

func TestRestoreSaveKeepsPreviousProgress(t *testing.T) {
    p := pathsFor(t.TempDir())
    putSave(t, p.save, 0x11, duskSaveSize)
    if err := makeBackup(p); err != nil { t.Fatal(err) }
    names, _ := listBackups(p)
    first := names[0]
    putSave(t, p.save, 0x22, duskSaveSize)
    if err := restoreBackup(p, first); err != nil { t.Fatal(err) }
    restored, err := os.ReadFile(p.save)
    if err != nil || !bytes.Equal(restored, bytes.Repeat([]byte{0x11}, duskSaveSize)) {
        t.Fatal("restore did not recover selected save")
    }
    names, _ = listBackups(p)
    if len(names) != 2 { t.Fatalf("lost pre-restore backup: %v", names) }
    foundOldProgress := false
    for _, name := range names {
        source, _, err := validateBackup(p, name)
        if err != nil { t.Fatal(err) }
        data, _ := os.ReadFile(source)
        if data[0] == 0x22 { foundOldProgress = true }
    }
    if !foundOldProgress { t.Fatal("prior progress was not preserved") }
}

func TestRestoreRejectsTraversalAndCorruption(t *testing.T) {
    p := pathsFor(t.TempDir())
    putSave(t, p.save, 0x15, duskSaveSize)
    if err := makeBackup(p); err != nil { t.Fatal(err) }
    for _, invalid := range []string{"../save", "..\\save", "evil.sav", ""} {
        if err := restoreBackup(p, invalid); err == nil {
            t.Fatalf("accepted invalid backup name %q", invalid)
        }
    }
    names, _ := listBackups(p)
    backup := filepath.Join(backupDirectory(p), names[0])
    putSave(t, backup, 0xff, duskSaveSize)
    if err := restoreBackup(p, names[0]); err == nil || !strings.Contains(err.Error(), "hash") {
        t.Fatalf("corrupted backup accepted: %v", err)
    }
    save, _ := os.ReadFile(p.save)
    if save[0] != 0x15 { t.Fatal("corrupted backup changed active progress") }
}

func TestRecoverInterruptedRestore(t *testing.T) {
    p := pathsFor(t.TempDir())
    putSave(t, p.save+".restore-rollback", 0x77, duskSaveSize)
    if err := recoverInterruptedRestore(p); err != nil { t.Fatal(err) }
    save, err := os.ReadFile(p.save)
    if err != nil || save[0] != 0x77 { t.Fatal("rollback not recovered", err) }
    if _, err := os.Stat(p.save+".restore-rollback"); !os.IsNotExist(err) {
        t.Fatal("rollback left behind after recovery")
    }
}

func TestRestoreDoesNotOverwriteMalformedExistingSave(t *testing.T) {
    p := pathsFor(t.TempDir())
    putSave(t, p.save, 0x11, duskSaveSize)
    if err := makeBackup(p); err != nil { t.Fatal(err) }
    names, _ := listBackups(p)
    putSave(t, p.save, 0xee, 8192)
    if err := restoreBackup(p, names[0]); err == nil { t.Fatal("should reject malformed canonical save") }
    data, _ := os.ReadFile(p.save)
    if len(data) != 8192 || data[0] != 0xee { t.Fatal("invalid save was modified") }
}
