# Digimon World Dusk PC — Native Desktop SDL3 (v0.5)

## Native runtime and window

The game ARM9/ARM7 images are statically recompiled to C and linked into the native NDSRecomp hardware runtime. The runner is compiled on Windows with NDS_SDL_BACKEND=SDL3 and presents its two framebuffers in an actual SDL3 window. No HTTP, browser, PNG/Base64 relay, WSL, or external DS emulator is launched by this build.

A ROM-free Go GUI launcher in native-launcher/desktop reads a hash-verified private overlay attached to its EXE. The overlay contains only the user's own verified ROM, the native SDL3 runner, and SDL3.dll. Those files are extracted to %LOCALAPPDATA%/DuskNativePC/v0.5 and run with --interactive, --boot direct, --generated-firmware, --freebios and --network off.

## Frame-rate investigation

A diagnostic Linux native-runner test with the same Dusk USA ROM measured 22.4 VBlanks/s when the game bank C files were built with -O0. Building them with -O1 increased throughput to 32.4 VBlanks/s (approximately 44% improvement). The previous FreeBIOS diagnostic configuration unconditionally forced -O0 for the game banks. Our isolated upstream patch tools/patches/ndsrecomp-title-opt-level.patch separates BIOS choice from title code optimization and accepts the CMake cache option NDS_TITLE_BANK_OPT_LEVEL=0|1|2.

These are benchmark figures for the Linux builder, not real Windows FPS. Even the optimized build is below the original DS's approximately 59.83 frames/s on this machine, so performance is not yet solved. The SDL3 presenter eliminates browser/HTTP overhead but cannot by itself solve runtime CPU bottlenecks.

The log from the Windows native SDL frontend is under %LOCALAPPDATA%/DuskNativePC/v0.5/native-performance.log. The launcher enables NDS_FRONTEND_STATS=1 so when the window closes we can inspect emulation, presentation, and overall measured FPS.

## Reproducible release process

GitHub Actions builds and unit-tests the Windows GUI launcher without the ROM and optionally fetches the pinned SDL3 3.2.20 GNU SDK. Downloading this ROM-free CI artifact alone will NOT run Dusk.

In a PRIVATE local build environment with the owner's ROM, build the exact game title banks and SDL3-backed native runner using the pinned NDSRecomp revision. Then compile the Go module in native-launcher/desktop for windows/amd64 as a GUI subsystem binary.

Finally run the privacy-conscious single-file packer:

    python tools/pack_native_private.py --launcher build/Dusk-PC-Native-Launcher-ROM-Free.exe --runner private/nds_runner.exe --sdl sdk/SDL3.dll --rom "Digimon World - Dusk (USA).nds" --output private/Digimon-Dusk-PC-Windows-Nativo.exe

The packer refuses wrong ROM hashes, non-Windows binaries, a runtime not linked to SDL3, and oversized payloads. NEVER commit or publish the resulting full EXE, ROM, or game-derived C sources to the public repository. For each private release provide matching source and license notices separately.

## Controls and limitations

The native SDL runner maps Z=A, X=B, Enter=Start, arrow keys=D-pad, Q/E=L/R, and mouse clicks on the touch screen. The initial SDL preview uses the classic stacked screens; floating/asymmetric secondary display will be implemented in the native SDL3 compositor, not HTML.

Saves are disabled until integrity and persistence are tested. Battles, complete gameplay, audio and long sessions are not validated. The EXE was built for Windows x64 and the embedded payload and DLL imports were verified; actual GUI execution and FPS on a Windows PC still require the user's test. macOS/Linux can use SDL3-native builds; Android requires a separate toolchain and app lifecycle.

## Native Dusk-specific SDL3 experience — v0.6

Source: `tools/patches/ndsrecomp-dusk-native-ui.patch` (applied to pinned
NDSRecomp only for the Dusk build); ROM-free geometry in the new header
`runner/src/dusk_native_ui.h`. The launcher now sets
`NDS_DUSK_NATIVE_UI=1` and uses its own per-user `v0.6` directory.
Other NDSRecomp titles retain the existing frontend when this opt-in flag
is absent.

Five presentation modes in a resizable native Windows application:

- **Modern** (default): lower/touch game screen large, upper screen in a side panel.
- **Floating**: maximized lower screen with upper overlay; drag upper screen
  by holding the left mouse button, or use F7 for preset corners.
- **Classic**: original vertical stacked dual screens.
- **Side by side**: equal-scale horizontal dual screens.
- **Main only**: large game screen and instant toggle to reveal secondary.

Toolbar buttons: MODE, AUX, FULLSCREEN and HELP. Keyboard: F4 cycles
layouts, F5 toggles auxiliary screen, F6 changes floating scale, F7
changes corner, F11/Alt+Enter toggles fullscreen, F1 toggles hints.
Window resizing recalculates presentation live, maintaining per-screen
4:3 proportions without stretching the game. Touch coordinates are
inverse-mapped from the transformed lower screen into original
DS 256x192 points; clicks outside the actual lower screen are ignored.
Floating drag and toolbar gestures do not become touches.

Layout, auxiliary visibility, floating scale/corner/position and help
visibility persist via `SDL_GetPrefPath("DuskPC","DigimonWorldDusk")`
in `native-layout.cfg`. Invalid/out-of-range values fall back to defaults.
Guest RAM, scheduler, DSP and framebuffers are not modified by layout changes.

Performance: the previous client already ran near 58-60 FPS in the
user's title/intro screenshots. There are scene-transition dips.
The new presenter keeps the same optimized ARM banks and native SDL3
rendering; it adds one rate-limited `[dusk-perf]` line for CPU
execution frames exceeding 70 ms. This is instrumentation,
**not a guaranteed fix for stutters**. The user should provide
`%LOCALAPPDATA%\DuskNativePC\v0.6\native-performance.log` if needed.

ROM-free regression gate: `tests/native_layout_geometry.cpp` verifies
layouts, aspect ratio, bounds, keyboard-independent touchscreen mappings
on 240 combinations of window sizes/layouts/visibility. The CI verifies
the public upstream patch applies against the pinned NDSRecomp revision.

Private artifact: a one-click Windows GUI EXE created with
`tools/pack_native_private.py`, with the owner's locally supplied Dusk
USA ROM and SDL3 DLL. **Never upload that binary or any game-derived
code/assets to the public GitHub Actions artifact store**.

Windows native build is cross-compiled and independently checked for
correct PE/DLL linkage, SHA-256 of ROM payload and overlay integrity.
Live Windows graphical behavior is **pending user validation**.
