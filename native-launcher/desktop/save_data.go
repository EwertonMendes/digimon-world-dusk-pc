package main

import (
    "crypto/sha256"
    "encoding/hex"
    "errors"
    "fmt"
    "io"
    "os"
    "path/filepath"
    "sort"
    "strconv"
    "strings"
    "time"
)

const (
    appVersion = "v0.16"
    // NTR-A6RE-USA: 512-kbit cartridge EEPROM. No save states are used.
    duskSaveSize = 64 * 1024
    duskCartridgeConfig = "[cartridge]\nsave_type = \"eeprom\"\nsave_size = 65536\n"
    duskTitleID = "A6RE"
)

type gamePaths struct {
    install, profile, console, save, config, firmware, diagnostics string
}

// Executables and diagnostics may change between builds. Player data never does.
func pathsFor(base string) gamePaths {
    root := filepath.Join(base, "DuskNativePC")
    profile := filepath.Join(root, "userdata", duskTitleID)
    install := filepath.Join(root, appVersion)
    return gamePaths{
        install: install,
        profile: profile,
        console: filepath.Join(profile, "console"),
        save: filepath.Join(profile, "saves", "dusk.sav"),
        config: filepath.Join(install, "dusk-cartridge.toml"),
        firmware: filepath.Join(profile, "console", "firmware-state.bin"),
        diagnostics: filepath.Join(install, "diagnostics"),
    }
}

func ensureGameDirectories(p gamePaths) error {
    for _, d := range []string{p.install, p.console, filepath.Dir(p.save), filepath.Join(p.profile, "backups"), p.diagnostics} {
        if err := os.MkdirAll(d, 0700); err != nil { return fmt.Errorf("não foi possível criar %s: %w", d, err) }
    }
    return nil
}

func writeGameConfig(p gamePaths) error {
    // This exact title-specific override is required: upstream defaults to 8 KiB.
    if err := os.WriteFile(p.config, []byte(duskCartridgeConfig), 0600); err != nil {
        return fmt.Errorf("não foi possível configurar EEPROM de 64 KiB: %w", err)
    }
    return nil
}

func validSave(path string) (bool, error) {
    fi, err := os.Stat(path)
    if errors.Is(err, os.ErrNotExist) { return false, nil }
    if err != nil { return false, err }
    if !fi.Mode().IsRegular() || fi.Size() != duskSaveSize {
        return false, fmt.Errorf("save existente inválido (%s): esperado arquivo de %d bytes, encontrado %d; nada será sobrescrito", path, duskSaveSize, fi.Size())
    }
    return true, nil
}

func copyNewFile(dst, src string) error {
    // O_EXCL ensures that import/backup never overwrites player data.
    r, err := os.Open(src)
    if err != nil { return err }
    defer r.Close()
    w, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
    if err != nil { return err }
    n, copyErr := io.Copy(w, r)
    if copyErr == nil { copyErr = w.Sync() }
    closeErr := w.Close()
    if copyErr == nil { copyErr = closeErr }
    if copyErr != nil || n == 0 {
        os.Remove(dst)
        if copyErr != nil { return copyErr }
        return errors.New("arquivo de origem vazio")
    }
    return nil
}

func hashFile(path string) (string, error) {
    f, err := os.Open(path)
    if err != nil { return "", err }
    defer f.Close()
    h := sha256.New()
    if _, err := io.Copy(h, f); err != nil { return "", err }
    return hex.EncodeToString(h.Sum(nil)), nil
}

func legacyVersionDirs(base string) ([]string, error) {
    entries, err := os.ReadDir(filepath.Join(base, "DuskNativePC"))
    if errors.Is(err, os.ErrNotExist) { return nil, nil }
    if err != nil { return nil, err }
    dirs := []string{}
    for _, e := range entries {
        if e.IsDir() && strings.HasPrefix(e.Name(), "v0.") && e.Name() != appVersion {
            dirs = append(dirs, filepath.Join(base, "DuskNativePC", e.Name()))
        }
    }
    sort.Slice(dirs, func(i, j int) bool {
        vi, ei := strconv.Atoi(strings.TrimPrefix(filepath.Base(dirs[i]), "v0."))
        vj, ej := strconv.Atoi(strings.TrimPrefix(filepath.Base(dirs[j]), "v0."))
        if ei == nil && ej == nil { return vi < vj }
        return dirs[i] < dirs[j]
    })
    return dirs, nil
}

func migrateLegacySave(p gamePaths, base string) error {
    if ok, err := validSave(p.save); err != nil || ok { return err }
    dirs, err := legacyVersionDirs(base)
    if err != nil { return err }
    var source, digest string
    for _, d := range dirs {
        for _, name := range []string{"game.sav", "dusk.sav"} {
            candidate := filepath.Join(d, name)
            exists, err := validSave(candidate)
            if err != nil { return fmt.Errorf("save antigo requer verificação manual: %w", err) }
            if !exists { continue }
            hash, err := hashFile(candidate)
            if err != nil { return err }
            if source != "" && digest != hash {
                return fmt.Errorf("múltiplos saves antigos diferentes encontrados (%s e %s); cópia automática bloqueada para evitar perda de progresso", source, candidate)
            }
            source, digest = candidate, hash
        }
    }
    if source == "" { return nil }
    if err := copyNewFile(p.save, source); err != nil { return fmt.Errorf("falha na cópia preservando save original: %w", err) }
    ok, err := validSave(p.save)
    if err != nil || !ok {
        os.Remove(p.save)
        return fmt.Errorf("cópia do save antigo inválida: %v", err)
    }
    copiedHash, err := hashFile(p.save)
    if err != nil || copiedHash != digest {
        os.Remove(p.save)
        return fmt.Errorf("save importado não corresponde ao original: %v", err)
    }
    return nil
}

func migrateLegacyIdentity(p gamePaths, base string) error {
    dst := filepath.Join(p.console, "generated-identity.bin")
    if b, err := os.ReadFile(dst); err == nil {
        if len(b) != 6 || b[0]&1 != 0 { return fmt.Errorf("identidade de firmware existente inválida: %s", dst) }
        return nil
    } else if !errors.Is(err, os.ErrNotExist) { return err }
    dirs, err := legacyVersionDirs(base)
    if err != nil { return err }
    // Earlier launchers stored the identity in the versioned runtime directory.
    for i := len(dirs)-1; i >= 0; i-- {
        source := filepath.Join(dirs[i], "generated-identity.bin")
        b, err := os.ReadFile(source)
        if errors.Is(err, os.ErrNotExist) { continue }
        if err != nil { return err }
        if len(b) != 6 || b[0]&1 != 0 { return fmt.Errorf("identidade antiga inválida: %s", source) }
        return copyNewFile(dst, source)
    }
    // The pinned NDSRecomp runtime generates a persistent MAC here on first boot.
    return nil
}

func backupSave(p gamePaths) error {
    exists, err := validSave(p.save)
    if err != nil || !exists { return err }
    digest, err := hashFile(p.save)
    if err != nil { return err }
    dest := filepath.Join(p.profile, "backups", fmt.Sprintf("dusk-%s-%s.sav", time.Now().UTC().Format("20060102T150405.000000000Z"), digest[:12]))
    if err := copyNewFile(dest, p.save); err != nil { return fmt.Errorf("backup pré-jogo falhou, execução bloqueada: %w", err) }
    copiedHash, err := hashFile(dest)
    if err != nil || copiedHash != digest {
        os.Remove(dest)
        return fmt.Errorf("backup pré-jogo divergiu do save de origem: %v", err)
    }
    return nil
}

func prepareGameData(p gamePaths, base string) error {
    if err := ensureGameDirectories(p); err != nil { return err }
    if err := writeGameConfig(p); err != nil { return err }
    if err := migrateLegacySave(p, base); err != nil { return err }
    if err := migrateLegacyIdentity(p, base); err != nil { return err }
    return backupSave(p)
}


func runnerArgs(p gamePaths) []string {
    // Original Dusk DS menu saves only. The patched SDL frontend disables
    // save-state hotkeys independently; never pass --no-save here.
    return []string{
        p.console, "--rom", filepath.Join(p.install, "game.nds"),
        "--interactive", "--boot", "direct", "--generated-firmware", "--freebios",
        "--network", "off", "--config", p.config,
        "--save-path", p.save, "--firmware-state-path", p.firmware,
        "--screen-layout", "stacked", "--fullscreen", "off",
        "--diagnostics", "on", "--diagnostics-dir", p.diagnostics,
        "--diagnostics-interval-ms", "1000",
    }
}
