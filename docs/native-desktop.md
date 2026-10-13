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
