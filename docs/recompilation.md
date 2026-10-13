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

## Verified Dusk USA private static-bank pipeline (2026-10-13)

After building NDSRecomp at the pinned upstream commit, run locally with your own ROM:

```powershell
python tools/prepare_dusk_recomp.py --rom "C:\\Games\\Digimon World - Dusk (USA).nds"
python tools/prepare_dusk_recomp.py --rom "C:\\Games\\Digimon World - Dusk (USA).nds" --recompiler "C:\\tools\\nds_recompile.exe"
python tools/prepare_dusk_recomp.py --rom "C:\\Games\\Digimon World - Dusk (USA).nds" --recompiler "C:\\tools\\nds_recompile.exe" --emit
```

This prepares the ARM9 main bank starting at `0x02000800` and ARM7 main bank at `0x02380000` under ignored `.private/recomp`. With `--overlays`, it also records 18 **research-only** overlay banks; their load addresses are not verified executable entrypoints, so the generator refuses to emit them. The ARM9 secure-area prefix (0x800 bytes) is intentionally not interpreted as plaintext code. Always inspect `.private/recomp/manifest.json` and verify compiler output. The tool cannot start the game without missing runtime/firmware and dynamic dispatcher integration. Recompiled C and all private images are game-derived and must not be published.

The upstream audit and synthetic-code emission contract run on GitHub Actions without any proprietary data. Genuine Dusk-bank audit/emission is only possible locally with the user's ROM. The benchmark is not a claim of playable native execution.
