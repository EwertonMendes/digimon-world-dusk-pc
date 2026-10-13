# Windows setup and testing

## Download CI prototype

Go to GitHub Actions > `Build and test - ROM free` > successful run > Artifacts > `dusk-pc-windows-presentation-prototype`. Unzip and run `dusk_pc.exe` (no ROM required). Requires Windows 10/11 x64. It is **not** a Digimon game executable yet.

## Build from sources

Install Git, CMake >=3.20 and Visual Studio 2022 C++ Build Tools or Visual Studio with C++ desktop workload. From Developer PowerShell:

```powershell
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

For the ROM analyzer:

```powershell
.\build\Release\dusk_rom_info.exe "C:\path\to\Digimon World - Dusk (USA).nds" --json
.\build\Release\dusk_rom_info.exe "C:\path\to\Digimon World - Dusk (USA).nds" --extract-code .private\extracted
```

The application accepts the ROM path as an optional argument but only **checks its identity**. No game code is executed. Do not place the ROM in the repository or CI.

## Controls

`F1` help, `F2` secondary toggle, `F3` layout selection, `F11` fullscreen, `+`/`-` floating scale, drag floating screen with mouse, `Esc` exits fullscreen.

Settings are persisted in `%APPDATA%\DuskPC\presentation-settings.txt`.

## Research tool setup

- Ghidra: <https://github.com/NationalSecurityAgency/ghidra>
- NTRGhidra: <https://github.com/pedro-javierf/NTRGhidra>
- NDSRecomp: <https://github.com/RetroPortingToolKit/ndsrecomp>
- REA: <https://github.com/morluto/rea>

REA on Windows cannot analyze a Nintendo DS ARM ROM directly. Setup for REA is optional and not required for this prototype. Use native Ghidra/NTRGhidra for DS binaries.
