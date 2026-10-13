# Windows v0.11 real-menu and battle-audio stutter investigation — 2026-10-13

## Ground truth from the user's Windows v0.11 diagnostics

User supplied three owner-private files: performance-20261013-191804.jsonl, hostprof-20261013-191804.ndshp and game-coverage-20261013-191804-part00.json. They are private and are NOT published in GitHub.

The new run contains 379 1-second performance records, median guest FPS 59.833 and a gameplay low of 43.870 FPS at 19:21:04 (ignoring cold boot). Recorded audio underrun notifications total 475. Median emulation time is 8.32 ms/guest frame and median native SDL presentation is 0.22 ms/frame in the ~30 visual FPS experiment.

The most relevant slow 1-second windows:

| Time | Guest FPS | Guest execution ms/frame | Exact ARM9 Tier3 ms/frame | SDL presentation ms/frame | Audio underruns |
| --- | ---: | ---: | ---: | ---: | ---: |
| 19:21:04 | 43.870 | 22.140 | 14.790 | 0.228 | 38 |
| 19:23:22 | 46.777 | 19.296 | 13.424 | 0.222 | 39 |
| 19:22:25 | 46.793 | 14.662 | 10.056 | 0.225 | 27 |
| 19:22:56 | 46.961 | 20.046 | 12.606 | 0.231 | 36 |

ARM9 interpreter fallback cost is about 67–70% of guest execution in the slow samples, while SDL is ~0.2 ms. The user hears audio micro-freezes coinciding with menu, battle start, damage and techniques. Correlation in the profile supports guest-time underruns, but no log has an in-game event marker; do NOT attribute any particular sample to a specific technique, item, submenu or enemy.

Host profiling sampled at nominal 250Hz. It reports 240,452 thread observations and around 3.7 seconds cumulative suspended time distributed across the entire recording, not a 3.7-second contiguous hitch. Its overhead should be tested separately, not presumed causal. Never conceal interpreter slowness by skipping guest ticks or doubling audio buffer duration without measured validation.

## Verification of native overlay source coverage

Five owner-private captures were checked against the same Dusk USA ROM (game code A6RE) with exact 4096-byte live RAM page SHA-1 and full-byte ROM image comparison. The merged evidence includes 248 distinct code-page generations and 10 RAM addresses with multiple byte versions; overlapping overlays must be distinguished by byte identity and guarded native dispatch.

| ARM9 overlay | Exact live full pages | Observed ARM/Thumb root candidates |
| --- | ---: | ---: |
| 0 | 12 | 142 |
| 1 | 6 | 109 |
| 2 | 36 | 206 |
| 6 | 3 | 27 |
| 7 | 21 | 154 |
| 13 | 1 | 4 |
| 17 | 2 | 24 |

Observed addresses are candidate roots, not automatic proof that a function begins there. The public refresh tool tools/refresh_shipped_overlays.py accepts the ROM and owner captures locally, verifies content identity and previously shipped overlay binary hashes, creates separate configurations and generates only code banks with the NDSRecomp --validate-live-bytes option. It refuses an unknown or unverified overlay. The generated C bodies and exact ROM bytes stay private.

The controlled native build changes only those seven already-shipped overlay bank bodies. It preserves ARM9/ARM7 main banks, game input logic, guest clock (~59.826 Hz), SDL3 window, fullscreen, 30/60 visual toggle and sound path. It is NOT a complete interpreter-free port.

### Validation requirements

- Windows x64 native SDL3 runner compiles and links with all refreshed overlay banks.
- Linux scripted 2765-VBlank original title/new-game/starter/story intro test must match prior exact ARM9 and ARM7 cycles plus six framebuffer SHA256 digests; this does NOT cover battle, and cannot alone justify a full gameplay claim.
- Private one-click exe must include original verified ROM and matching source, never public GitHub artifacts.
- Owner Windows compare same menu and battle sequence v0.11 versus candidate; log precise FPS, audio underruns, Tier3 ARM9 exact time, and visually check damage effects/items.
- Only after that comparison can we describe any FPS improvement. Do NOT merge speculative perf changes based on mean 59.8 FPS or ROM-free CI alone.
