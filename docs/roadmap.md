# Roadmap (verified vs future)

## Phase 1 — completed in this iteration

- [x] Analyze user ROM locally and confirm known US variant, header CRC16, SHA-256, ARM banks and overlays.
- [x] Portable C++20 ROM inspector with strict bounds checking and ignored private code extraction.
- [x] Pure layout geometry module and settings persistence.
- [x] Windows fullscreen native **presentation-only** prototype: synthetic frames, F1/F2/F3/F11, floating drag/scale.
- [x] Linux C++ build + unit tests and optional real-ROM test.
- [x] Windows/Linux CI workflow declared (results depend on completed GitHub Actions runs).

## Phase 2 — static code generation and bring-up

- [x] Build pinned NDSRecomp recompiler on Linux and Windows and run decode/cycle tests.
- [ ] Install and confirm Ghidra/NTRGhidra compatibility, import Dusk ARM9 and overlays.
- [x] Generate ROM-hash-verified ARM9/ARM7 title-bank configs, audit and emit actual title C sources privately.
- [x] Document FreeBIOS generated-firmware direct boot path without distributing retail BIOS.
- [x] Link ARM9/ARM7 recompilation banks into an instrumented native Linux runtime and reach game intro.

## Phase 3 — game execution

- [ ] Verify all ARM7/ARM9 synchronization, code coverage and dynamic overlay dispatch beyond the first story scene.
- [x] Reach real Dusk title screen and first story map in private native runtime.
- [x] Prototype a separate browser compositor driven by real native-runner framebuffer data (Linux/WSL); native Windows compositor remains pending.
- [ ] Map input, audio and saves into original game data and test with melonDS oracle.

## Phase 4 — polished PC experience

- [ ] Dynamic context-driven secondary screen based on verified game-state hooks.
- [ ] Proper graphics backend, settings UI and controller configuration.
- [ ] Native save compatibility tests, regression screenshots, stable release build.

## Phase 3a — current private playable preview (Linux/WSL)

- [x] Navigate New Game, select player, enter name, choose Balance Pack,
  confirm three Digimon names, and reach the first in-game scene.
- [x] Automate ROM-private title-to-story traversal with real input and
  framebuffer inspection (`tools/test_dusk_native_story.py`).
- [x] Build and locally test a basic browser frontend with keyboard/touchscreen,
  fullscreen and layouts, communicating with the native Linux runtime.
- [ ] Verify full story controls, movement, battles, sound and long sessions.
- [ ] Validate save device, native save persistence and compatibility.
- [ ] Build the fully independent **Windows x64** native runner with
  locally derived game banks, then attach the full native host frontend.


## Current Dusk Native Windows v0.14 gates (2026-10-13)

- [x] Private Windows v0.13 SDL3 native gameplay approved by the owner;
      old roadmap references to Windows/native being pending are historical.
- [x] Original in-game Dusk cartridge backup plumbing in public launcher
      (explicit 64 KiB EEPROM, stable user profile, pre-launch backups,
      conservative legacy migration, concurrency guard).
- [x] Public pinned upstream patch for save-state shortcut suppression; apply
      when rebuilding the private Windows SDL3 runtime.
- [x] ROM-free tests for save geometry, corruption refusal, migration,
      backup copy, stable path and runner flags.
- [x] Deterministic gameplay scenario runner and known intro-to-first-map
      script without save states or manual gameplay rewriting.
- [ ] Real owner's Windows **in-game Save -> quit -> Continue** roundtrip with
      confirmation of inventory, party, location and quest flags.
- [ ] Confirm same save in a second, rebuilt release (not only restart v0.14).
- [ ] Rebuild the private native SDL3 game runner with the new save-state
      suppression patch; interim v0.14 test package may reuse v0.13 runtime.
- [ ] Extend reproducible checks to battle, items, rewards, maps,
      digivolution, story ending and long-play sound integrity.
- [ ] AOT long-tail route coverage and elimination of remaining Tier3 paths.

Do not mark the original full campaign proven just because ROM-free CI
and a first-story-map regression pass.
