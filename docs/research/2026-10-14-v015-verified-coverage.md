# v0.15: original-game AOT coverage work (2026-10-13/14)

**Scope:** Continue converting the ROM owner's original Digimon World Dusk
(USA, A6RE) ARM/Thumb code into native Windows x64 dispatch, while preserving
v0.14 in-game EEPROM saves and existing UI. **No original game code, cartridge,
save, screenshots or runtime RAM pages are committed to GitHub.**

## Important source-audit correction (real dispatch count)

The previous NDSRecomp `read_dispatch_rows` regex scanned **all**
`{0xADDRu, NUMBERu, ...}` expressions in generated `*_dispatch.c`.
This accidentally included `NdsStaticValidation` initializers, whose second
field is a byte length (e.g., 12u or 72u), not the ARM/Thumb mode.

The exact pinned v0.13 **main-bank actual** dispatch arrays declare:

| ARM core | Real g_dispatch_*_len | Previously reported with metadata |
| --- | ---: | ---: |
| ARM9 main | **64,354** | 75,928 |
| ARM7 main | **12,141** | 14,392 |

The reported larger values were **not native dispatch counts**.
`tools/verified_dispatch_rows.py` now reads only the explicit
`const NdsDispatchEntry g_dispatch_*[]` array, requires 0/1 for ARM/Thumb,
requires the declared `_len` to match parsed rows, detects duplicate entries
and compares baselines by **the same bank**. Any lost row aborts the release.
`promote_tier3_spans.py` now uses this strict parser with separate CPU sets.
Synthetic ROM-free tests run in CI.

## Owner-private v0.13 -> candidate v0.15 expansion

Using the latest owner session `game-coverage-20261013-203750-part00.json`:

- ROM SHA-256 `df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb`, exact original.
- 136 captured 4KiB code-page versions; **127** proved to match complete
  generation/address-correct pages in the original ARM9/ARM7 main images and
  already-known overlays. **Nine unmatched pages were excluded** rather
  than compiled speculatively. Some boundary/unaligned full pages may
  require separate investigation, not blanket relabeling as dynamic code.
- No *additional* one of the 11 unshipped overlays was provably executed in
  this session. 18 overlay images remain preserved as isolated private
  `.bin/.toml` candidates; only 0,1,2,6,7,13,17 ship in the current runtime.
- The upstream ingester supplied interpreted spans after CPU-specific native
  dispatch ownership filtering. 80 ARM9 + 8 ARM7 new seed entries were
  **full 4KiB page byte and generation-root verified**, across the two
  main images and ARM9 overlays 0,1,2,6,7,17.
- The pinned NDSRecomp recompiler emitted eight updated banks using
  `--validate-live-bytes`, preserving one unchanged shipped overlay (13).
  Only these specific native dispatch entries, not all original Dusk game
  logic, are candidates for replacement.

### Correct native dispatch comparison of private generated C

| Modified bank | Before v0.13 | Candidate v0.15 | Added | Lost |
| --- | ---: | ---: | ---: | ---: |
| ARM7 main | 12,141 | 12,199 | 58 | 0 |
| ARM9 main | 64,354 | 65,097 | 743 | 0 |
| ARM9 overlay 00 | 5,513 | 6,417 | 904 | 0 |
| ARM9 overlay 01 | 5,019 | 5,385 | 366 | 0 |
| ARM9 overlay 02 | 27,518 | 27,532 | 14 | 0 |
| ARM9 overlay 06 | 1,094 | 3,745 | 2,651 | 0 |
| ARM9 overlay 07 | 10,082 | 15,582 | 5,500 | 0 |
| ARM9 overlay 17 | 993 | 1,701 | 708 | 0 |
| ARM9 overlay 13 (unchanged) | 97 | 97 | 0 | 0 |
| **Total across shipped banks** | **126,811** | **137,755** | **10,944** | **0** |

These are **true native (PC, Thumb) dispatch entries**, not function counts,
percentage of campaign covered, or FPS. New entries may overlap unseen scene
behavior; the full game must still be tested.

## Regression and release gates

1. Rebuild the **private** Windows SDL3 runner from matching source, with all
   eight generated replacements and unchanged overlay 13. Never link mixed
   ROM revisions or publish derived sources to public Actions.
2. Apply the existing ROM-free `ndsrecomp-dusk-disable-savestates.patch`
   in the private runner (the launcher already sets the corresponding opt-in
   environment variable).
3. Run exact title-to-first-map differential checkpoints, original ARM9/ARM7
   virtual cycles and deterministic framebuffer digest comparisons against
   v0.14. Check the save/continue replay from an **isolated copy** of the
   owner's cartridge save; never point a development run to their canonical
   save path.
4. Compare v0.14 and v0.15 **on the same real game scenes**, especially menus,
   walking between regions, battle HUD, damage/effects, inventory, quests and
   audio. Inspect Tier3 and missed native guards; verify no visual/audio/FPS
   regression before merge.
5. Continue collecting longer private traces through story, Digivolutions,
   Digifarm, quest changes and post-game; promote missing overlays only with
   runtime byte and generation proof. No speculative complete-playthrough
   claim until actually traversed.

## User-facing acceptance

Any candidate full Windows EXE must open by double-click only, without WSL,
compilers or external ROM selection. The unchanged persistent path is:
`%LOCALAPPDATA%\\DuskNativePC\\userdata\\A6RE\\saves\\dusk.sav`.

Keep v0.14 available for rollback. Do not restructure UI until gameplay and
save completeness have passed the tests above.
