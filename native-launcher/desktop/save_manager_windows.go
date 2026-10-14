//go:build windows

package main

import (
    "fmt"
    "os/exec"
    "strings"
    "syscall"
    "unsafe"
)

const (
    windowsYes = 6
    windowsNo = 7
)

func messageBox(title, message string, flags uintptr) int {
    body, _ := syscall.UTF16PtrFromString(message)
    heading, _ := syscall.UTF16PtrFromString(title)
    ret, _, _ := syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(
        0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(heading)), flags)
    return int(ret)
}

// Hold Shift while launching the game to open this menu without a terminal.
func shiftHeld() bool {
    pressed, _, _ := syscall.NewLazyDLL("user32.dll").NewProc("GetAsyncKeyState").Call(0x10)
    return pressed & 0x8000 != 0
}

// The launcher holds the save mutex during this dialog: a second game instance
// cannot write the EEPROM while backup restoration takes place.
func manageSaves(p gamePaths) error {
    if err := ensureGameDirectories(p); err != nil { return err }
    if err := recoverInterruptedRestore(p); err != nil { return err }
    names, err := listBackups(p)
    if err != nil { return err }
    if len(names) == 0 {
        messageBox("Dusk PC - Saves", "Nenhum backup disponível ainda.\n\nSalve normalmente dentro do jogo e abra-o novamente para gerar um backup.", 0x40)
        return nil
    }
    shown := names
    if len(shown) > 8 { shown = shown[:8] }
    menu := fmt.Sprintf("Backups mais recentes (%d):\n\n%s\n\nSIM: restaurar o backup mais recente\nNÃO: abrir a pasta de backups\nCANCELAR: voltar sem alterações",
        len(names), strings.Join(shown, "\n"))
    switch messageBox("Dusk PC - Gerenciar saves", menu, 0x23) {
    case windowsYes:
        if messageBox("Confirmar restauração", "Restaurar o save do backup mais recente?\n\n"+names[0]+"\n\nO progresso atual será guardado em backup antes da restauração.", 0x24) != windowsYes {
            return nil
        }
        if err := restoreBackup(p, names[0]); err != nil { return err }
        messageBox("Dusk PC - Save restaurado", "Restauração concluída. Agora você pode abrir o jogo normalmente.", 0x40)
    case windowsNo:
        return exec.Command("explorer.exe", backupDirectory(p)).Start()
    }
    return nil
}
