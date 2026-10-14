# Dusk PC v0.14 — in-game save and gameplay validation

This work targets the **original Dusk in-game save menu**, not NDSRecomp save states.
Keep the v0.13 reference build. This repository is public: **do not commit or
upload Dusk ROMs, save files, screenshots, generated title banks or full private
Windows executables**.

## Save implementation

The owner-only Windows x64 SDL3 GUI launcher remains a single-click executable.
The verified Dusk USA ROM and statically recompiled ARM9/ARM7 code are packaged
**privately** in the same way as v0.13. Public GitHub Actions publishes only a
ROM-free launcher template.

The v0.14 launcher:

- Removes `--no-save`; explicitly uses `--save-path` with the NDSRecomp
  original cartridge-backup mechanism (automatic atomic EEPROM persistence).
- Declares Dusk USA `[cartridge] save_type="eeprom", save_size=65536`,
  rather than accepting the upstream generic 8 KiB default. Reference:
  NTR-A6RE-USA 64 KiB EEPROM cartridge database (0x10000).
- Writes player saves at
  `%LOCALAPPDATA%\DuskNativePC\userdata\A6RE\saves\dusk.sav`.
  This path does not contain a version number.
- Keeps `generated-identity.bin` and mutable generated firmware in
  `userdata\A6RE\console` across upgrades. Runner binaries/ROM/DLL
  stay in `DuskNativePC\v0.14`; diagnostics remain version-scoped.
- Preserves the original save before each launch in
  `userdata\A6RE\backups` and checks each backup SHA-256.
- Imports a single exact-size legacy `game.sav`/`dusk.sav` from a previous
  `v0.*` directory without deleting the source. If multiple *different*
  legacy saves or an invalid-size save exist, the launcher refuses automatic
  import. It never silently truncates/replaces progress.
- Blocks running two game processes against the same live cartridge save.
- Passes `NDS_DUSK_DISABLE_SAVESTATES=1` and requires the isolated upstream
  patch `tools/patches/ndsrecomp-dusk-disable-savestates.patch` in the
  private SDL3 runner. **F-key save/load snapshots must not be available**.

The pinned upstream NDSRecomp has a cartridge save load/atomic write path.
Launcher code/ROM-free tests verify configuration and backup mechanics;
the owner's *real-game* save/write/reload behavior still requires a private
Windows execution test. This distinction must not be blurred.

## Owner acceptance test — Windows executable only

No WSL, Python, compiler or command line is necessary for this checklist.

1. Keep v0.13 available as a reference; open the **privately packaged v0.14
   Dusk SDL3 executable**, never the ROM-free public launcher.
2. Start **New Game** and reach a controllable map. Open the game's **own
   S-menu/save option**. Save progress and wait for its completion message.
3. Quit the game normally. Reopen the same executable: the native Dusk
   title screen must show **Continue**, and the party/location/time/currency
   must match the saved data.
4. Open the same build again after saving more progress. Verify Continue
   reflects the newer in-game save (not a stale backup).
5. Confirm the file under `userdata\A6RE\saves\dusk.sav` has **65,536 bytes**.
   On the next launch there should be a separate file in `backups`. If
   the launcher shows an integrity warning, **do not remove the save**.
6. Close the game. Install a subsequent new launcher version without deleting
   the `userdata` folder. Continue on the newer build. Inspect actual
   party, location, experience, items and quest flags, not just the title
   screen. This cross-version gate needs a second tested build.
7. Try to launch a second executable while the first is running. It must
   refuse rather than allowing two simultaneous writers.
8. Try Shift+F1 / F1 (and other old save-state shortcuts) during gameplay.
   No save state should be created or loaded. The native F1 help, F4 layouts,
   F8 swap and F9 visual presentation should still work as designed.

## Gameplay coverage matrix (not automatically certified)

Track each route as PASS, FAIL or NOT TESTED in a private test notebook:

| Area | Required behavior |
| --- | --- |
| Title and character creation | New/Continue, nickname keyboard, starter selection |
| Map navigation | Walk, transitions, interact with NPCs, no softlock |
| Menus | Party, bag, status, save and return without missing audio |
| Battle entry | Load scene/enemies with correct HUD |
| Turns | Attacks, target selection, effects and damage |
| Battle resources | MP, items, victory, defeat, rewards and stat changes |
| Team management | Move party, recruit / DigiConvert when available |
| Digivolution | Requirements, evolve/devolve, stats retained correctly |
| Story | Missions, quest flags, new areas, cutscenes |
| Save/reload | Preserve recruited partners, inventory, quests, Digifarm |
| Long play | 60+ min, multiple scene swaps, no freezes or audio faults |
| Post-game | Final boss and optional content without path divergence |

For deterministic developer runs, use
`tools/dusk_gameplay_scenarios.py` and
`tests/scenarios/intro-to-first-map.json`. It sends only original button
and touchscreen input to the ROM-private debug runner, checks framebuffer
SHA-256 and CPU cycle progress, and intentionally runs **without writing a
player save**. It does not change or implement any Dusk story/battle logic.
Additional battle/area routes should be recorded from actual owner gameplay.
A tested title-to-first-map script is not a complete-playthrough certification.

## Private runner rebuild integration

Apply `tools/patches/ndsrecomp-dusk-disable-savestates.patch` after
the v0.6 native compositor, screen-swap and 30Hz-settings patches when
building the pinned upstream NDSRecomp version. Public CI now validates that
patch in the existing sequence.

Locally package with `tools/pack_native_private.py`, supplying the ROM-owner's
original USA cartridge image, the matching real-game ARM9/ARM7 Windows SDL3
runner, the pinned SDL3.dll and the **v0.14** Windows GUI launcher.
No game-derived binaries are published in public Actions.

### Release-blocking limitations

- The publicly downloadable launcher template **does not contain the game**.
- This repository alone does not hold the user's original-ROM-derived runtime.
  A private executable cannot be rebuilt from the ROM-free CI artifacts alone.
- Unit tests cannot prove that Dusk's save *menu* actually commits the backup
  over AUXSPI. That must be confirmed with owner gameplay and (ideally) an
  independent original cartridge/melonDS save oracle.
- Newly covered battles, all story areas, overlay loads and Digivolutions
  still require reproducible private tests. Do not mark complete based on
  synthetic input tests or intro-only screenshots.
