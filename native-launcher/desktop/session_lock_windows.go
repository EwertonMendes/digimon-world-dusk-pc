//go:build windows

package main

import (
    "errors"
    "fmt"
    "syscall"
    "unsafe"
)

// One running game per user profile. Two simultaneous runners must never
// write the same EEPROM image. Kernel mutex is released by the OS on crash.
func acquireSaveSession() (func(), error) {
    name, err := syscall.UTF16PtrFromString("Local\\DuskNativePC_A6RE_CartridgeSave")
    if err != nil { return nil, err }
    kernel := syscall.NewLazyDLL("kernel32.dll")
    create := kernel.NewProc("CreateMutexW")
    closeHandle := kernel.NewProc("CloseHandle")
    handle, _, callErr := create.Call(0, 0, uintptr(unsafe.Pointer(name)))
    if handle == 0 {
        return nil, fmt.Errorf("não foi possível bloquear o save: %w", callErr)
    }
    if errors.Is(callErr, syscall.Errno(183)) { // ERROR_ALREADY_EXISTS
        closeHandle.Call(handle)
        return nil, errors.New("Digimon World Dusk já está aberto; feche a outra janela para proteger o save")
    }
    return func() { closeHandle.Call(handle) }, nil
}
