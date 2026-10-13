# Recompilation: truthful integration boundary

Source: <https://github.com/RetroPortingToolKit/ndsrecomp>

NDSRecomp is a **pre-alpha research** system. Merely identifying ARM9 and ARM7 does not make the game portable. The upstream runner depends on BIOS and firmware banks, synchronization, memory mappings, overlays, input/audio/video and other per-game details. Do not claim Dusk execution without a run of its real ARM/Thumb code and reproducible evidence.

## Current procedure

1. Identify and validate the user's own Dusk USA ROM with `dusk_rom_info`.
2. Optionally extract the ARM segments into ignored local `.private/extracted`.
3. Run `python tools/bootstrap_recompiler.py` to clone and test the upstream recompiler (internet/toolchain required).
4. Record the exact upstream commit after checkout.
5. Inspect upstream config examples and game-bank requirements **at that commit** before writing title configs.
6. Use Ghidra/NTRGhidra to map the ARM9 and ARM7 code and 18 overlays, keeping proprietary derived bytes private.
7. Implement game-owned bank configs and a real game dispatch bridge; test with actual binaries privately.
8. Only then connect real game frames/events to the PC display compositor.

## REA and Ghidra

REA can complement Ghidra analysis, but its experimental Windows provider is limited to native x86-64 PE input (not raw ARM Nintendo DS ROM). NTRGhidra supports importing DS binaries in a distinct Ghidra compatibility range, so run separate supported Ghidra installations if needed. Do not make REA a required step of the build. Refer to project releases/docs for current version compatibility.

## Risks

- Game-specific ARM/Thumb recompilation and overlay dispatch.
- ARM7/ARM9 interaction and timings.
- Firmware/BIOS requirements; use only legally provided files.
- PPU, textures, audio, save memory and touchscreen accuracy.
- Licensing implications of upstream runner components.
