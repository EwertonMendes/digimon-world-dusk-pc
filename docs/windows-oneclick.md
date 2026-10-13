# Windows native one-click preview (v0.4)

## User experience

The **privately bundled** `Digimon-Dusk-PC-Windows-v0.4.exe` is a standalone **Windows x64** entrypoint. Double-click it. No WSL, Python, user-provided ROM file, compiler, or build steps are required on the tester's computer. On launch it:

1. Validates a cryptographically authenticated, appended private archive.
2. Verifies the exact Dusk USA ROM SHA-256 and a Windows AMD64 runtime.
3. Extracts the required private NDSRecomp executable and ROM to `%LOCALAPPDATA%\DuskNativePC\v0.4`.
4. Creates and persists a locally administered generated firmware identity.
5. Starts the Windows x64 **recompiled** ARM9/ARM7 runner and its local debug socket.
6. Opens the default browser to a loopback-only interface, fullscreen/layout capable.
7. Uses keyboard/touch to drive the **actual game** via the runner. No streamed remote gaming, nor a substituted emulator executable.

**Important:** The Windows binary was compiled and validated as a Windows PE/AMD64 file, but interactive boot and renderer correctness **have not yet been tested on the user's Windows machine**. The earlier full title-to-first-map route is validated on **Linux x64** only. The Windows executable is an experimental alpha, **not** a verified complete game port. Audio, saves, battles and long sessions are unverified/disabled.

## Repository and legal boundary

**NEVER** commit or upload ROMs, proprietary assets, extracted game code, generated ARM C, privately packaged Windows executable or saves. This GitHub repository is public.

The public build workflow builds the ROM-free Go launcher template, using:

```sh
cd native-launcher
go test ./...
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o ../DuskPC-Launcher-Windows-x64.exe .
```

GitHub Actions uploads `dusk-windows-one-click-launcher-rom-free`. **This template alone is not playable.** The private Linux/Windows native runner, compiled title banks and the user's own ROM are inserted locally by the packaging command below.

## Private one-click packaging for each subsequent test build

Prerequisites **on the developer/packaging machine only** (never on the tester's PC):

- The verified Dusk USA ROM: SHA-256 `df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb`.
- A Windows x64 NDSRecomp runner compiled with that exact ROM's private ARM7/ARM9 banks, pinned upstream `3a57236bb23d25dcb4caad7d58d733311062ff5e`.
- The ROM-free Windows launcher template, built from public source/CI.

Create private `Digimon-Dusk-PC-Windows-v0.4.exe` in **one packaging command**:

```sh
python native-launcher/tools/pack_private.py \
  --launcher DuskPC-Launcher-Windows-x64.exe \
  --runner /private/build/nds_runner.exe \
  --rom /private/Digimon-World-Dusk-USA.nds \
  --out /private/releases/Digimon-Dusk-PC-Windows-v0.4.exe
```

The produced PE contains an appended ZIP archive with the ROM and native runtime, plus a fixed-length trailer containing the compressed archive's length and SHA-256. The launcher verifies all archive contents and exact ROM identity before extracting. The packer validates both executable PE architectures. It produces a truly self-contained one-click test binary for Windows, not another WSL development kit.

The private bundle is distributed directly to the user and must never be uploaded to this public GitHub repository or Actions artifacts. The corresponding modified NDSRecomp sources, private generated C and frontend sources should accompany privately shared builds to satisfy licenses and preserve reproducibility.

## Controls

- Z / X: DS A / B
- Enter: Start
- Arrows or WASD: D-pad
- Q / E: shoulders L/R
- Mouse click/touchscreen: lower DS screen
- Tab: hide/show secondary display
- F11: browser fullscreen
- Screen layout dropdown: modern, floating, side by side, classic or main-only.

## Diagnostics

Windows runner logs are at `%LOCALAPPDATA%\DuskNativePC\v0.4\native-preview.log`. The launcher writes to a user-writable directory and binds both its debug and browser servers to localhost; no inbound public networking is required.

No production saves are performed in this alpha (`--no-save`), so progress from tests is temporary.

## Cross-platform follow-up

The native launcher is written in Go and the runner in portable C/C++. The packaging format can be extended for Linux/macOS after platform-specific runner binaries and validation exist. **Do not call the current Windows PE multi-platform**.

## Current engineering caveat

The public repository's Windows ROM-free runner feasibility job has separately encountered upstream POSIX network porting issues; the private Windows runner was cross-compiled from an explicitly patched tree with Zig 0.14.1 and includes the title banks. This proves a Windows PE was linked, not that its runtime boot logic is already verified on Windows.
