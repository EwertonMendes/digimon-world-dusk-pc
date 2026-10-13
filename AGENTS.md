# Development rules

- **Never commit** any `.nds`, extracted game-owned `.bin`, BIOS/firmware dump, recompilation output, save, or other copyrighted resource.
- Do not imply the presentation prototype is a playable game or an emulator; generated frames are deliberately synthetic.
- Windows `dusk_pc.exe` is a Win32 presentation prototype; Linux builds only the portable core, tests and ROM inspector.
- CMake 3.20+, C++20; build with `cmake -S . -B build`, `cmake --build build --config Release`, `ctest --test-dir build -C Release --output-on-failure`.
- The optional real-ROM local test is `DUSK_TEST_ROM=/path/to/user.nds ctest --test-dir build --output-on-failure` (on Windows set the environment variable accordingly). CI must never require this variable.
- Maintain separation between ROM metadata/parser, compositor geometry, platform window, and future game execution core.
- For NDSRecomp, preserve upstream version/commit and verify actual interface before integration. Do not invent supported flags or BIOS/firmware requirements.
- Continue from `docs/roadmap.md`. Track verified results, not assumed compatibility.
