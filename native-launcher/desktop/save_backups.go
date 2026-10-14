package main

import (
    "errors"
    "fmt"
    "io"
    "os"
    "path/filepath"
    "regexp"
    "sort"
    "strings"
    "time"
)

// Backups belong to the stable A6RE profile, never to a versioned runtime.
// Keep the most recent distinct saves; unknown files and migration archives
// are deliberately left untouched.
const maxAutomaticBackups = 20

var backupNamePattern = regexp.MustCompile(`^dusk-[0-9]{8}T[0-9]{6}\.[0-9]{9}Z-[a-f0-9]{12}\.sav$`)

func backupDirectory(p gamePaths) string { return filepath.Join(p.profile, "backups") }

func listBackups(p gamePaths) ([]string, error) {
    entries, err := os.ReadDir(backupDirectory(p))
    if errors.Is(err, os.ErrNotExist) { return nil, nil }
    if err != nil { return nil, err }
    names := make([]string, 0, len(entries))
    for _, entry := range entries {
        if entry.Type().IsRegular() && backupNamePattern.MatchString(entry.Name()) {
            names = append(names, entry.Name())
        }
    }
    sort.Sort(sort.Reverse(sort.StringSlice(names)))
    return names, nil
}

func validateBackup(p gamePaths, name string) (string, string, error) {
    if filepath.Base(name) != name || !backupNamePattern.MatchString(name) {
        return "", "", fmt.Errorf("nome de backup inválido: %q", name)
    }
    source := filepath.Join(backupDirectory(p), name)
    info, err := os.Lstat(source)
    if err != nil { return "", "", err }
    if !info.Mode().IsRegular() || info.Size() != duskSaveSize {
        return "", "", fmt.Errorf("backup não é um save regular de 64 KiB: %s", name)
    }
    digest, err := hashFile(source)
    if err != nil { return "", "", err }
    claimed := strings.TrimSuffix(strings.Split(name, "-")[2], ".sav")
    if !strings.HasPrefix(digest, claimed) {
        return "", "", fmt.Errorf("backup com hash divergente: %s", name)
    }
    return source, digest, nil
}

// makeBackup runs only while the launcher holds the named session mutex.
// A byte-identical newest backup is reused instead of producing an unlimited
// collection on repeated launches.
func makeBackup(p gamePaths) error {
    exists, err := validSave(p.save)
    if err != nil || !exists { return err }
    digest, err := hashFile(p.save)
    if err != nil { return err }
    if err := os.MkdirAll(backupDirectory(p), 0700); err != nil { return err }
    names, err := listBackups(p)
    if err != nil { return err }
    if len(names) > 0 {
        _, previous, checkErr := validateBackup(p, names[0])
        if checkErr != nil { return fmt.Errorf("backup mais recente inválido; nenhuma limpeza automática: %w", checkErr) }
        if previous == digest { return nil }
    }
    name := fmt.Sprintf("dusk-%s-%s.sav", time.Now().UTC().Format("20060102T150405.000000000Z"), digest[:12])
    target := filepath.Join(backupDirectory(p), name)
    if err := copyNewFile(target, p.save); err != nil { return fmt.Errorf("falha no backup pré-jogo: %w", err) }
    if _, written, err := validateBackup(p, name); err != nil || written != digest {
        _ = os.Remove(target)
        return fmt.Errorf("backup pré-jogo não verificado: %v", err)
    }
    names, err = listBackups(p)
    if err != nil { return err }
    // Prune only backups created by this format. If deletion fails, leave the
    // verified backup and report the issue; never compromise the active save.
    if len(names) > maxAutomaticBackups { for _, old := range names[maxAutomaticBackups:] {
        if err := os.Remove(filepath.Join(backupDirectory(p), old)); err != nil {
            return fmt.Errorf("retenção de backups: %w", err)
        }
    }
    }
    return nil
}

// After an unexpected interruption between the two renames of a restore,
// recover the original canonical save before any attempt to launch the game.
func recoverInterruptedRestore(p gamePaths) error {
    rollback := p.save + ".restore-rollback"
    if _, err := os.Lstat(rollback); errors.Is(err, os.ErrNotExist) { return nil } else if err != nil { return err }
    ok, err := validSave(rollback)
    if err != nil || !ok { return fmt.Errorf("rollback de restauração inválido; recuperação manual necessária: %w", err) }
    exists, err := validSave(p.save)
    if err != nil { return fmt.Errorf("save atual inválido; rollback preservado: %w", err) }
    if exists {
        // A crash may occur *after* the new save was installed, but before
        // cleanup. Retire the old rollback only when its full SHA256 is
        // already preserved in a verified backup; otherwise fail closed.
        previousHash, err := hashFile(rollback)
        if err != nil { return err }
        names, err := listBackups(p)
        if err != nil { return err }
        for _, name := range names {
            _, hash, err := validateBackup(p, name)
            if err != nil { return fmt.Errorf("backup inválido durante recuperação: %w", err) }
            if hash == previousHash {
                return os.Remove(rollback)
            }
        }
        return fmt.Errorf("rollback não encontrado nos backups verificados, preservado para revisão: %s", rollback)
    }
    return os.Rename(rollback, p.save)
}

// restoreBackup is explicitly opt-in and must only be invoked with the
// session mutex held and the game runner stopped.
func restoreBackup(p gamePaths, name string) error {
    source, digest, err := validateBackup(p, name)
    if err != nil { return err }
    exists, err := validSave(p.save)
    if err != nil { return err }
    rollback := p.save + ".restore-rollback"
    if _, err := os.Lstat(rollback); err == nil { return fmt.Errorf("há uma restauração pendente: %s", rollback) } else if !errors.Is(err, os.ErrNotExist) { return err }

    // Keep an independent backup of current progress before changing anything.
    if exists {
        if err := makeBackup(p); err != nil { return err }
    }
    tmp, err := os.CreateTemp(filepath.Dir(p.save), "restore-*.tmp")
    if err != nil { return err }
    tmpName := tmp.Name()
    defer os.Remove(tmpName)
    reader, err := os.Open(source)
    if err != nil { tmp.Close(); return err }
    n, err := io.Copy(tmp, reader)
    reader.Close()
    if err == nil { err = tmp.Sync() }
    closeErr := tmp.Close()
    if err == nil { err = closeErr }
    if err != nil || n != duskSaveSize { return fmt.Errorf("falha ao preparar restauração de 64 KiB: %v", err) }
    verified, err := hashFile(tmpName)
    if err != nil || verified != digest { return fmt.Errorf("hash da cópia de restauração divergente: %v", err) }

    if exists {
        if err := os.Rename(p.save, rollback); err != nil { return err }
    }
    if err := os.Rename(tmpName, p.save); err != nil {
        if exists {
            if undoErr := os.Rename(rollback, p.save); undoErr != nil {
                return fmt.Errorf("restauração falhou (%v) e rollback requer recuperação: %w", err, undoErr)
            }
        }
        return err
    }
    if exists {
        // The old progress has already been verified in backups; retain a
        // rollback file on deletion failures to avoid silent loss.
        if err := os.Remove(rollback); err != nil { return fmt.Errorf("save restaurado, mas não foi possível remover rollback: %w", err) }
    }
    return nil
}

