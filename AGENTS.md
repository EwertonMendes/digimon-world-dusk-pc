# Development rules — Dusk PC

1. **Preserve original Dusk gameplay.** Do not rewrite cartridge battles,
   menus, evolution or campaign logic by hand. Improve the existing ARM/Thumb
   NDSRecomp static recompiler and verified AOT banks.
2. **Never commit private bytes**: `.nds`, `.sav`, BIOS, dumped/extracted
   code, RAM coverage `pages[].data`, `.ndshp` stack samples, generated ARM C,
   private full-game bundles or personally identifying Windows paths.
3. Public ROM-free CI artifacts (`dusk_pc.exe`) are synthetic visualization
   prototypes; never advertise them as the playable private game.
4. Upstream NDSRecomp must stay pinned to a recorded SHA. Separate upstream
   updates from host-UI refactors. Make integration patches reproducible with
   `git apply --check`, retain checked regression tests, and avoid new
   monolithic frontend patches where a Dusk-specific module suffices.
5. Dispatch requires correct CPU (ARM9/ARM7), ARM/Thumb mode, live bytes
   and code-generation identity. Merging roots is allowed only for identical
   page hashes. Never infer full-campaign coverage from root counts.
6. Preserve original ~59.826 Hz guest timing. Presentation changes must not
   modify game-world speed. Treat one-second FPS statistics separately from
   true per-frame latency and record audio underruns.
7. Keep original 64KiB A6RE EEPROM and identity in the **stable user profile**,
   independent of launcher version. Never overwrite player progress silently.
   Lock the profile during save, backup, restore and runner execution.
8. Maintain double-click Windows x64 private artifacts; do not require WSL,
   Python, compilers, browsers or ROM selection on the player's computer.
9. Test changes: `cmake -S . -B build -DDUSK_BUILD_TESTS=ON`,
   `cmake --build build --config Release`,
   `ctest --test-dir build -C Release --output-on-failure`;
   run Python tests and `go test ./...` in Windows launcher directory.
   Public tests are ROM-free; native gameplay build/QA remains private.
10. Work by topic-scoped branches/PRs. Require CI review before promoting
    to master. Maintain a fallback copy of the last playable private build.
11. Repository documentation must distinguish **implemented, tested,
    experimental, and not yet implemented** states; never claim a v0.17
    game package until it exists and has been tried.
12. Respect NDSRecomp's PolyForm Noncommercial 1.0.0 and all applicable
    independent game permissions when packaging/distributing.

See `docs/architecture.md`, `docs/roadmap.md`, and
`docs/research/2026-10-14-v016-owner-sessions-safe.md`.
