package main

import (
    "fmt"
    "os"
    "syscall"
    "unsafe"
)
func fatal(err error) {
    message, _ := syscall.UTF16PtrFromString(fmt.Sprintf("Falha ao iniciar Dusk PC %s:\n\n%v\n\nDados permanentes: %%LOCALAPPDATA%%\\DuskNativePC\\userdata\\A6RE\nLogs: %%LOCALAPPDATA%%\\DuskNativePC\\%s", appVersion, err, appVersion))
    title, _ := syscall.UTF16PtrFromString("Digimon World Dusk PC")
    syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(
        0, uintptr(unsafe.Pointer(message)), uintptr(unsafe.Pointer(title)), 0x10)
    os.Exit(1)
}
