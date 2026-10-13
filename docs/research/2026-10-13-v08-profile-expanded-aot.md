# v0.8 Windows profile -> v0.9 verified overlay expansion

## Private evidence, Oct 13, 2026

The ROM owner supplied `performance-20261013-175502.jsonl`, `hostprof-20261013-175502.ndshp`, and `game-coverage-20261013-175502-part00.json` from **Windows v0.8**, including game menus, transitions and some battle activity. The private profile captures 361 one-second performance intervals, 174 RAM page snapshots, 711 ARM9 and 84 ARM7 observed call records. Commercial ROM, page bytes and profile binary must **not** be committed to public GitHub.

### v0.8 Windows observed statistics

| Statistic | Value |
|---|---:|
| Median FPS (1-second intervals) | 59.838 |
| Minimum including boot | 19.945 |
| Minimum excluding first ~10s | 42.088 |
| Median emulation duration / displayed frame | 8.281 ms |
| Worst interval emulation duration / displayed frame | 34.581 ms (startup) |
| Typical SDL presentation | ~0.35 ms |
| Accumulated audio underrun notices | 414 |
| ARM9 Tier3 interpreted guest instructions | 1,080,529,801 |
| ARM7 Tier3 interpreted guest instructions | 10,316,493 |

All are **session-level or averaged interval measurements**. The per-second FPS figure cannot prove any individual frame met its 16.715-ms deadline. Cumulative Tier3 instructions cannot be compared directly between sessions of differing length and user actions. At 17:57:57 the profile shows 42.716 FPS, 22.681 ms emulation, 0.355 ms presentation, 42 audio underruns and 7,356,410 ARM9 interpreted guest instructions during that interval. At 18:00:36, 42.088 FPS, 19.419 ms emulation, 0.352 ms presentation, 41 underruns and 6,634,781 ARM9 interpreter instructions. This is strong evidence that residual slowdown is **guest runtime execution**, not viewport rendering.

### New byte-proven cartridge code

The v0.8 build included the verified primary ARM9/ARM7 images, copied ARM7 pages, and three overlays 0,1,17. The new capture includes extensive *different* code, especially overlay 2, and overlays 6,13:

| Overlay bank | Exact matching 4-KiB live RAM pages | Observed ARM/Thumb roots in newly captured profile |
|---|---:|---:|
| ARM9 0 | 9 | 73 |
| ARM9 1 | 6 | 62 |
| ARM9 2 | **33** | **184** |
| ARM9 6 | 3 | 10 |
| ARM9 13 | 1 | 4 |
| ARM9 17 | 2 | 1 |

The fact that an overlay appeared during this multi-scene session **does not identify which visual scene or battle used it** without correlated per-event trace.

`tools/merge_verified_profiles.py` validates each snapshot page (SHA1, exact 4096-byte size, CPU and aligned RAM address), requires one ROM identity, retains **distinct generations** at matching RAM addresses and merges observed call roots conservatively (maximum observed hits per identical caller/entry, not summed). It is deliberately ROM-free/public-code-only. The additional capture can be passed using `--coverage-extra` to `tools/prepare_dusk_recomp.py`, which still forces `--validate-live-bytes` for emitted C banks.

With both captures combined:
- **202 uniquely content-identified page generations** were preserved.
- **5 same-address pages with differing content** remain distinct, avoiding an unsafe address-only dispatch.
- Main-image observed roots: **1,176 ARM9, 305 ARM7** (observed candidate entries, not automatically proven correct functions).
- Guarded candidate overlay banks: **0, 1, 2, 6, 13, 17**.
- 8 AOT banks total including the two main CPU images; unverified cartridge code and RAM variants remain outside native dispatch.

These are preparation/generation metrics, **not yet a Windows FPS improvement**.

## Required native validation

1. Run all generated C with mandatory `--validate-live-bytes`; allow Tier3 correctness fallback where code is genuinely dynamic or changes across overlays.
2. Differential native Linux execution: exact original guest ARM9/ARM7 virtual cycle counts, 2,765 VBlank introduction flow and six framebuffer hashes matching v0.8.
3. When available, simulate transition and battle with deterministic input and compare guest-state checks before and after overlay 2 activation.
4. Build Windows x64 SDL3 through pinned Zig cross compiler; link with all eight bank dispatch registries; never upload ROM-derived code or complete game bundle to public GitHub Actions.
5. Package owner-only Windows .exe; compare **same scene and actions** on v0.8 and v0.9 using actual FPS, 99th percentile frame time, ARM9 Tier3 time, audio underruns, and correct graphics. Do not merge if either screen state or FPS regresses.
6. To make a broad 'native only' claim would require closing every possible dynamic instruction path, even never-observed scenes, and replacing the DS device layer with equivalent native device APIs. This revision **does not** make that claim.

## Private AOT reproduction

```bash
python tools/prepare_dusk_recomp.py \
  --rom /path/to/owner/Dusk-USA.nds \
  --coverage /path/to/owner/game-coverage-170344.json \
  --coverage-extra /path/to/owner/game-coverage-175502.json \
  --overlays --out .private/dusk-aot-v09 \
  --recompiler /path/to/pinned/nds_recompile --emit \
  --arm9-shards 24 --arm7-shards 16
```

No guest ROM bytes, extracted assets, frame data or private binary logs are included in this document or tracked source.

## v0.9 private Windows release — incremental, isolated change

A fully combined 8-bank AOT C generation was completed with mandatory live-byte checks, but a Linux full rebuild was deferred for separate validation because all large main-bank translation units must be reoptimized. **The actual v0.9 user-facing binary deliberately retains the v0.8 main ARM9/ARM7 bank implementations and original overlay 0/1/17 implementations**, and adds only newly verified ARM9 overlays **2, 6 and 13**. It is therefore a controlled one-dimension change, preserving previously user-validated guest execution paths while adding newly observed scene code. Do not claim all 1,176/305 merged seeds are active in the v0.9 runtime; these are candidate generation results for the next complete AOT variant.

Private native Linux validation succeeded after linking the incremental overlays: the scripted intro reached the first story scene after 2,765 VBlanks, with ARM9/ARM7 cycle counts and all 6 framebuffer SHA256 digests exactly equal to v0.8. Private Windows Zig/GNU SDL3 3.2.20 compilation and link succeeded; linked registry includes dispatch for overlays 02,06,13. The single owner-only GUI EXE includes exactly the verified Dusk USA ROM and the matching SDL3 DLL; bundle payload SHA256 was verified independently.

**Battle FPS in Windows v0.9 is not yet measured.** The overlay capture was from a session containing menus/transitions/battle, but the trace does not prove which scene used each overlay; only real-owner A/B tests can validate whether observed hitching is eliminated. No merge is appropriate before that gate.
