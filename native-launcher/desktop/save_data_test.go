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

func TestContentAddressedInstallsSharePlayerDataAndPreservePriorBuilds(t *testing.T) {
    base := t.TempDir()
    a := map[string][]byte{
        "runner.exe": []byte("MZ-runner-first"),
        "SDL3.dll": []byte("MZ-sdl"),
        "game.nds": []byte("verified-rom"),
    }
    // Stable regardless of map allocation or key insertion order.
    same := map[string][]byte{
        "game.nds": []byte("verified-rom"),
        "runner.exe": []byte("MZ-runner-first"),
        "SDL3.dll": []byte("MZ-sdl"),
    }
    b := map[string][]byte{
        "runner.exe": []byte("MZ-runner-second"),
        "SDL3.dll": []byte("MZ-sdl"),
        "game.nds": []byte("verified-rom"),
    }
    p1, p2, p3 := pathsForBundle(base,a), pathsForBundle(base,same), pathsForBundle(base,b)
    if p1.install != p2.install { t.Fatal("identical bundle got two installation paths") }
    if p1.install == p3.install { t.Fatal("new runner reused previous installation") }
    if !strings.Contains(p1.install, filepath.Join("DuskNativePC","installs",appVersion)) {
        t.Fatalf("unexpected install folder: %s",p1.install)
    }
    for _, property := range []struct {old, next string}{
        {p1.profile,p3.profile}, {p1.save,p3.save},
        {p1.console,p3.console}, {p1.firmware,p3.firmware},
    } {
        if property.old != property.next { t.Fatal("player state changed between builds") }
    }
    putSave(t,p1.save,0x57,duskSaveSize)
    for _, pair := range []struct {p gamePaths; files map[string][]byte}{{p1,a},{p3,b}} {
        if err:=prepareGameData(pair.p,base);err!=nil { t.Fatal(err) }
        if err:=provision(pair.p.install,pair.files);err!=nil { t.Fatal(err) }
    }
    prior,err:=os.ReadFile(filepath.Join(p1.install,"runner.exe"))
    if err!=nil || !bytes.Equal(prior,a["runner.exe"]) { t.Fatal("older runner was overwritten") }
    updated,err:=os.ReadFile(filepath.Join(p3.install,"runner.exe"))
    if err!=nil || !bytes.Equal(updated,b["runner.exe"]) { t.Fatal("new runner was not installed") }
    saved,err:=os.ReadFile(p3.save)
    if err!=nil || !bytes.Equal(saved,bytes.Repeat([]byte{0x57},duskSaveSize)) {
        t.Fatal("the shared EEPROM was modified during runtime upgrade")
    }
    // Reopening the exact same payload remains idempotent.
    if err:=provision(p2.install,same);err!=nil { t.Fatal(err) }
}

func TestSameBundleRejectsCorruptedInstalledRunner(t *testing.T) {
    base := t.TempDir()
    files:=map[string][]byte{"runner.exe":[]byte("MZ-expected")}
    p:=pathsForBundle(base,files)
    if err:=os.MkdirAll(p.install,0700);err!=nil { t.Fatal(err) }
    if err:=os.WriteFile(filepath.Join(p.install,"runner.exe"),[]byte("MZ-tampered"),0600);err!=nil {
        t.Fatal(err)
    }
    if err:=provision(p.install,files);err==nil { t.Fatal("tampered runtime was accepted") }
    installed,err:=os.ReadFile(filepath.Join(p.install,"runner.exe"))
    if err!=nil || string(installed)!="MZ-tampered" { t.Fatal("tampered file was silently replaced") }
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
    if err != nil || len(backups) != 1 { t.Fatalf("expected 1 deduplicated backup; %v %d",err,len(backups)) }
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
