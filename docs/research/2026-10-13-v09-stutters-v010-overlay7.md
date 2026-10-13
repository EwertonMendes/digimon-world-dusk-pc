# Dusk Windows v0.9 -> v0.10: menu and combat stutter investigation

Date: 2026-10-13. Owner-only local Windows profile from the native SDL3 executable:
`performance-20261013-182309.jsonl`, `hostprof-20261013-182309.ndshp`,
`game-coverage-20261013-182309-part00.json`.
These files, all RAM page bytes, original ROM, proprietary game source, and release EXE are **private**, not GitHub artifacts.

## Measurements actually observed

The profile has **972 one-second FPS samples** from 18:23:10 to 18:39:31.
Overall median was 59.841 FPS; after the first ten seconds the lowest
interval was 37.260 FPS. These are averages over intervals, not per-frame
traces, so **cannot** prove that every individual frame meets the ~16.715 ms
budget.

| Windows time | Interval FPS | Game execution (ms/frame) | ARM9 Tier3 (ms/frame) | SDL presentation (ms/frame) | Audio underruns |
|---|---:|---:|---:|---:|---:|
| 18:31:54 | 42.483 | 22.979 | 15.011 | 0.390 | 46 |
| 18:34:25 | 42.522 | 22.659 | 14.989 | 0.390 | 46 |
| 18:37:20 | 37.260 | 25.816 | 19.157 | 0.470 | 58 |
| 18:38:05 | 42.914 | 21.799 | 14.240 | 0.390 | 41 |

These samples attribute ~65–74% of game execution time to **ARM9 Tier3**.
ARM7 Tier3 is approximately 0.10 ms/frame during these dips.
The software 2D/3D rendering and SDL presentation are **not the primary measured bottleneck**.
Substantial Tier3 entry rates/cache-absent counters correlate with those
windows; those counters should not be interpreted as unique function calls.

Owner reports short hitches on menu and submenu opening/closing, battle
entry, each enemy appearing, item use and technique animations. **The log
does not contain in-game event markers**, so the timestamps above cannot
be assigned to any particular reported action without further evidence.
The Windows host profiler sampled many sleeping / waiting threads in
ntdll.dll; those waiting stacks cannot be counted as guest CPU work.

## New proven executable code

This session supplied 181 captured page versions (157 ARM9, 24 ARM7)
and 623 ARM9 / 84 ARM7 recorded call sites. Merging this and the earlier
two owner sessions gives **230 distinct byte-identified RAM page generations**
and **6 addresses with different code generations**. Exact ROM-backed
overlay verification finds:

| Bank | Full RAM pages matching original ROM | AOT seed roots across all 3 profiles |
|---|---:|---:|
| overlay 0 | 9 | 86 |
| overlay 1 | 6 | 88 |
| overlay 2 | 35 | 201 |
| overlay 6 | 3 | 13 |
| **overlay 7** | **9** | **47** |
| overlay 13 | 1 | 4 |
| overlay 17 | 2 | 22 |

The v0.9 private release already contained ARM9 main, ARM7 main and
overlays 0, 1, 2, 6, 13 and 17. **Incremental v0.10 adds only
overlay 7**, not guessed scene code or wholesale replacement of previous
approved banks. Offline pinned NDSRecomp generated **689 ARM9 function
candidates** in four C shards for overlay 7, with `--validate-live-bytes`
to reject stale or replaced overlay RAM.

The new public selector `tools/select_verified_aot_delta.py` takes a
ROM and one or more private profiles, checks ROM/page identity, compares
observed overlays with a declared shipped list and produces a private
delta plan. Synthetic regression tests cover mismatched ROM identity,
modified pages, overlapping overlay variants and already-shipped banks.
Never publish generated C or captured page bytes.

## Validation completed before Windows owner test

- **Native Windows x64 SDL3 runner compiled/linked**, with the additional
  generated overlay 7 shard files and content-verified dispatch.
- **Native Linux test completed** the same scripted title, player naming,
  starter selection and story-intro route: exactly **2,765 VBlanks** with
  unchanged ARM9+ARM7 guest cycle counts and six framebuffer SHA256 digests.
- Windows GUI launcher built as GUI subsystem, isolated in
  `%LOCALAPPDATA%\\DuskNativePC\\v0.10`, not WSL or browser; owner ROM
  and SDL3 packed privately in one executable. ROM and payload SHA256
  verified, but Windows interactive playback needs the owner's real test.
- Existing save-disabling, UI layout, audio and F8/F11 controls preserved.

### Not yet proven

**No Windows FPS improvement in menu/battle is claimed.**
Adding the newly observed overlay 7 removes potential interpreter work
where it is loaded, but the captured performance dips have no
fine-grained markers connecting them to that overlay. Dynamic code and
other uncovered ARM9 addresses still enter Tier3. We have not completed
a full battle replay with deterministic state checks, all possible
overlays, or a complete native-only game implementation.

Next gate: compare v0.9 versus v0.10 **same menu and battle actions on
the same Windows machine**. Measure guest-frame p95/p99 and the worst
second, ARM9 Tier3 ms/frame, audio underruns and correctness. Do not
merge based solely on title screen or performance averages.

Public GitHub keeps only scripts/tests/docs, all owner-specific binary
and content-derived results are distributed privately alongside
corresponding source.
