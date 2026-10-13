# Dusk native: converting interpreter hotspots instead of guessing overlays

Date: 2026-10-13. Issue #11. **Owner-only profile and game data are never published in GitHub.**

## Corrected implementation path

Dusk's current Windows SDL3 executable uses the NDSRecomp static ARM9/ARM7 banks but executes uncovered game-code PCs through the Tier3 interpreter. On the owner's PC, the slowest Windows menu/battle windows repeatedly spend most guest milliseconds in ARM9 Tier3, with correlated audio underruns. Halving only SDL visual presentation could not fix this.

Older \`derive_verified_aot.py\`/overlay tools consumed sparse call/indirect targets and ignored most Tier3 ROOT bitmap coverage. Generating many "functions found" is not proof they appear in compiled dispatch tables. This change instead consumes the pinned upstream NDSRecomp's built-in \`tools/ingest_coverage_manifests.py\` **interpreted spans**, which merge adjacent ROOT bitmaps and use just one seed at the beginning of each previously interpreted run.

## Private five-session observations

- Exact owner Dusk USA ROM SHA1 \`de1a1915e07288ffad654f3f9f2eb730a0fd1d9c\`.
- All 5 schema-4 session manifests accepted, 0 rejected.
- 248 captured code page versions; **234 full 4096-byte pages resolved exactly to prepared ROM code images**, 14 not found in original images. The latter must be investigated as dynamic/transformed code; they are not blindly promoted.
- ARM7's active executable image has at least two observed relocated bases, \`0x027CFAAC\` and \`0x037F7E50\`, different from header load \`0x02380000\`. Existing protected code-copy ranges must be preserved and verified against live bytes before native dispatch.
- After filtering the registered baseline dispatch rows, the upstream aggregator reported 4956 ARM9 and 475 ARM7 interpreted spans. These **are not 5431 verified functions**; they are interpreted spans requiring mode/byte/generation checks. A small bounded subset should be used first.
- Hottest ARM9 span starts: \`0x0200F96C\` (~28.63M estimated entries), \`0x0207ED18\` (~23.95M, already seeded in older TOML), \`0x0207EDC8\` (~9.50M), \`0x020097DC\` (~6.42M). A high hit count is a ranking signal, not guaranteed host milliseconds saved.

## New promotion tool

\`tools/promote_tier3_spans.py\` requires:

1. Original ROM matching both SHA1 and SHA256.
2. **Schema-4 RAM pages from the user's exact sessions**; each captured page validated for CPU, alignment, length and SHA1.
3. Full-page byte equality against an existing bank image at the actual runtime PC; copied ARM7 RAM handled only through declared \`[[code_copy]]\` mapping.
4. **Generation-bound \`root_arm\`/\`root_thumb\` bit** for the exact candidate PC and instruction mode. Session-wide ROOT maps alone are ambiguous when two overlays occupy the same RAM address.
5. Rows from the **matching CPU's existing dispatch table**, preventing reseeding already-native PCs; exclude existing TOML entrypoints.
6. Configured per-CPU and per-bank budgets, and minimum entries threshold. Emit isolated staged TOMLs and a report without modifying previously verified game banks.

The owner-private recompilation stage must emit with \`--validate-live-bytes\` and preserve the old banks alongside the proposed ones. The game-derived generated C output, ROM and RAM page dumps do not go to GitHub CI.

## Private AOT generator audit (not a FPS claim)

A conservative first batch selected 48 ARM9 and 24 ARM7 previously uncovered ROOT-aligned candidates, retaining all original bank configurations and protected ARM7 code-copy mappings. Using the pinned NDSRecomp C emitter with \`--validate-live-bytes\`, native dispatch tables changed:

| Rows checked by the upstream dispatch-row parser | Previous v0.12 main bank | New hot-span main bank | Net |
| --- | ---: | ---: | ---: |
| ARM9 | 50,291 | 75,928 | **+25,637** |
| ARM7 | 10,564 | 14,392 | **+3,828** |

No older rows were lost. Most importantly, \`0x0200F96C\`, \`0x0207EDC8\`, \`0x020097DC\` and relocated ARM7 \`0x03807D10\` change from **no native dispatch row** to a native dispatch row in their correct CPU bank. These numbers are **dispatch-row counts**, not distinct functions, not actual runtime native hits, and not a proven FPS increase.

## Verification and release gates

- ROM-free tests for exact root bitmap mode, alien/stale code versions, unchanged existing dispatch rows, relocated ARM7, seed cap and non-overwriting stage.
- Compile & link new Windows x64 SDL3 runner and separate Linux runner using the owner's original-ROM-generated banks, entirely outside public GitHub. Reject any compile warning indicating correctness issues.
- Differential story intro: 2765 VBlanks, exact ARM9/ARM7 cycles and six framebuffer hashes equal v0.12.
- Compare at least one identical, **uncapped** headless replay with perf metrics: true Tier3 ARM9/ARM7 ms and interpreted instructions, CPU native dispatch hits/absent guards, real max and p99 frame duration, audio underruns. An increase in generated code does not pass this gate alone.
- Owner's Windows gameplay validates S-menu, submenus, battle entry, enemy spawns, techniques, damage effects, items, audio continuity. **Do not claim zero stutters without that result**.
- Only merge when correctness and performance are demonstrated. New Windows one-click artifacts and matching game source are delivered privately only.

## Limits

This is recompilation of the original game's ARM/Thumb program; the executable will still need a native implementation of original Nintendo DS hardware contracts (DMA, MMIO, GPU, clocks, audio). Such compatibility code is **not itself ARM interpretation**. Removing the interpreter from all gameplay requires proving every executed code generation and handling never-observed dynamic code; a finite five-session coverage set cannot certify the entire game.

**Avoid:** manually rewriting Dusk, stretching a 30Hz guest simulation, repeating visual frames as real FPS, putting game assets in GitHub, speculative overlay entrypoints, and silent Tier3 fallback in a final purportedly interpretation-free release.
