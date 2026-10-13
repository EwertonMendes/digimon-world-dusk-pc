# Roadmap (verified vs future)

## Phase 1 — completed in this iteration

- [x] Analyze user ROM locally and confirm known US variant, header CRC16, SHA-256, ARM banks and overlays.
- [x] Portable C++20 ROM inspector with strict bounds checking and ignored private code extraction.
- [x] Pure layout geometry module and settings persistence.
- [x] Windows fullscreen native **presentation-only** prototype: synthetic frames, F1/F2/F3/F11, floating drag/scale.
- [x] Linux C++ build + unit tests and optional real-ROM test.
- [x] Windows/Linux CI workflow declared (results depend on completed GitHub Actions runs).

## Phase 2 — next technical milestone

- [ ] Build NDSRecomp upstream recompiler in a connected environment, run decode/cycle tests.
- [ ] Install and confirm Ghidra/NTRGhidra compatibility, import Dusk ARM9 and overlays.
- [ ] Generate title-specific static bank configurations and prove deterministic ARM instruction translation.
- [ ] Document supported ROM boot path and firmware/BIOS dependencies without redistribution.
- [ ] Integrate at least one genuine ARM9 code entry point into an instrumented native runner.

## Phase 3 — game execution

- [ ] ARM7/ARM9 interaction and overlay dispatch.
- [ ] Implement/extend game-specific runtime and reach the real title screen.
- [ ] Drive the compositor with actual game frames, not synthetic ones.
- [ ] Map input, audio and saves into original game data and test with melonDS oracle.

## Phase 4 — polished PC experience

- [ ] Dynamic context-driven secondary screen based on verified game-state hooks.
- [ ] Proper graphics backend, settings UI and controller configuration.
- [ ] Native save compatibility tests, regression screenshots, stable release build.
