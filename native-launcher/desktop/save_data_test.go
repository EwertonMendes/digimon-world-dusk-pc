package main

import (
    "bytes"
    "os"
    "path/filepath"
    "strings"
    "testing"
)

func putSave(t *testing.T, path string, data byte, size int) {
    t.Helper()
    if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil { t.Fatal(err) }
    if err := os.WriteFile(path, bytes.Repeat([]byte{data}, size), 0600); err != nil { t.Fatal(err) }
}

func TestProfilePathIsVersionIndependent(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    if !strings.HasSuffix(p.install, appVersion) { t.Fatal("versioned install missing") }
    for _, stable := range []string{p.profile, p.save, p.console, p.firmware} {
        if strings.Contains(stable, appVersion) { t.Fatalf("player data is version-bound: %s", stable) }
    }
    if !strings.HasSuffix(p.save, filepath.Join("A6RE","saves","dusk.sav")) { t.Fatal(p.save) }
}

func TestFirstRunSets64KiBEEPROMWithoutCreatingSave(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    if err := prepareGameData(p, base); err != nil { t.Fatal(err) }
    if b, err := os.ReadFile(p.config); err != nil || string(b) != duskCartridgeConfig {
        t.Fatalf("wrong cartridge save geometry: %v %q", err, b)
    }
    if _, err := os.Stat(p.save); !os.IsNotExist(err) { t.Fatal("launcher must not create an artificial in-game save") }
    if _, err := os.Stat(filepath.Join(p.console, "generated-identity.bin")); !os.IsNotExist(err) {
        t.Fatal("identity must be initialized by NDSRecomp, not the launcher")
    }
}

func TestExistingSaveIsNeverOverwrittenAndBackedUp(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    putSave(t, p.save, 0xA5, duskSaveSize)
    if err := prepareGameData(p, base); err != nil { t.Fatal(err) }
    if err := prepareGameData(p, base); err != nil { t.Fatal(err) }
    b, err := os.ReadFile(p.save)
    if err != nil || len(b) != duskSaveSize || b[0] != 0xA5 { t.Fatal("canonical save modified") }
    backups, err := os.ReadDir(filepath.Join(p.profile,"backups"))
    if err != nil || len(backups) != 2 { t.Fatalf("expected 2 non-destructive backups; %v %d",err,len(backups)) }
    for _, e := range backups {
        b, err := os.ReadFile(filepath.Join(p.profile,"backups",e.Name()))
        if err != nil || !bytes.Equal(b, bytes.Repeat([]byte{0xA5},duskSaveSize)) { t.Fatalf("invalid backup %s: %v",e.Name(),err) }
    }
}

func TestWrongSizeIsRejectedWithoutRepair(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    putSave(t, p.save, 0xCC, 8192)
    if err := prepareGameData(p, base); err == nil || !strings.Contains(err.Error(), "65536") { t.Fatalf("expected fail-closed invalid size, got %v",err) }
    b, err := os.ReadFile(p.save)
    if err != nil || len(b) != 8192 || b[0] != 0xCC { t.Fatal("user's invalid save was modified") }
}

func TestMigratesOneLegacySaveWithoutDeletingOriginal(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    old := filepath.Join(base,"DuskNativePC","v0.13","game.sav")
    putSave(t, old, 0x33, duskSaveSize)
    if err := prepareGameData(p, base); err != nil { t.Fatal(err) }
    now, err := os.ReadFile(p.save)
    if err != nil || now[0] != 0x33 || len(now)!=duskSaveSize { t.Fatalf("legacy migration missing: %v",err) }
    if _, err := os.Stat(old); err != nil { t.Fatal("original legacy save lost") }
}

func TestConflictingLegacySavesBlockLaunch(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    putSave(t, filepath.Join(base,"DuskNativePC","v0.12","game.sav"), 0x12, duskSaveSize)
    putSave(t, filepath.Join(base,"DuskNativePC","v0.13","game.sav"), 0x13, duskSaveSize)
    if err := prepareGameData(p, base); err == nil || !strings.Contains(err.Error(),"múltiplos saves") { t.Fatalf("expected conflict: %v",err) }
    if _, err := os.Stat(p.save); !os.IsNotExist(err) { t.Fatal("conflicting saves should never be auto-selected") }
}

func TestDuplicateLegacySavesAreIdempotent(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    putSave(t, filepath.Join(base,"DuskNativePC","v0.12","game.sav"), 0x12, duskSaveSize)
    putSave(t, filepath.Join(base,"DuskNativePC","v0.13","dusk.sav"), 0x12, duskSaveSize)
    if err := prepareGameData(p, base); err != nil { t.Fatal(err) }
    if err := prepareGameData(p, base); err != nil { t.Fatal(err) }
}

func TestMigratesLegacyIdentityWithoutReplacingSharedOne(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    old := filepath.Join(base,"DuskNativePC","v0.13","generated-identity.bin")
    if err := os.MkdirAll(filepath.Dir(old),0700); err!=nil { t.Fatal(err) }
    identity := []byte{0x02,0x11,0x22,0x33,0x44,0x55}
    if err := os.WriteFile(old,identity,0600);err!=nil { t.Fatal(err) }
    if err := prepareGameData(p,base);err!=nil { t.Fatal(err) }
    got,err:=os.ReadFile(filepath.Join(p.console,"generated-identity.bin"))
    if err!=nil || !bytes.Equal(got,identity) { t.Fatal("identity was not migrated") }
    if err := prepareGameData(p,base);err!=nil { t.Fatal(err) }
}

func TestInvalidOldSaveIsNotImported(t *testing.T) {
    base := t.TempDir()
    p := pathsFor(base)
    putSave(t, filepath.Join(base,"DuskNativePC","v0.13","game.sav"),0x99,8192)
    if err:=prepareGameData(p,base);err==nil { t.Fatal("wrong EEPROM size must not be imported") }
    if _,err:=os.Stat(p.save);!os.IsNotExist(err) { t.Fatal("invalid save migrated") }
}


func TestRunnerArgsOnlyUseOriginalCartridgeSave(t *testing.T) {
    p := pathsFor(t.TempDir())
    args := runnerArgs(p)
    for _, forbidden := range []string{"--no-save", "--savestate-dir", "--force-tier3"} {
        for _, a := range args {
            if a == forbidden { t.Fatalf("forbidden runner argument: %s", a) }
        }
    }
    values := map[string]string{}
    for i := 0; i+1 < len(args); i++ {
        if strings.HasPrefix(args[i], "--") { values[args[i]] = args[i+1] }
    }
    if values["--save-path"] != p.save || values["--config"] != p.config ||
        values["--firmware-state-path"] != p.firmware {
        t.Fatalf("missing stable in-game save arguments: %v", values)
    }
    if args[0] != p.console { t.Fatal("firmware console identity must be permanent") }
}
