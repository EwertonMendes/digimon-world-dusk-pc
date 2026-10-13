# Dusk USA: verified AOT coverage from owner's Windows menu-hitch trace
Date: 2026-10-13 · Issue #3 · Branch `feature/dusk-verified-aot-coverage`

## Source and test boundary

Three **private, owner-supplied** diagnostics from the Windows SDL3 v0.7 build:
- `performance-20261013-170344.jsonl` (195 one-second `perf` intervals, roughly 17:03:45–17:07:01);
- `game-coverage-20261013-170344-part00.json` (runtime candidate calls, ARM9/ARM7 ROM and RAM snapshot pages);
- `hostprof-20261013-170344.ndshp` (Windows host sampling report).

Original game ROM SHA-1: `de1a1915e07288ffad654f3f9f2eb730a0fd1d9c`, code `A6RE`. The original ROM, its page snapshots, live host profiler data, private recompiled source and binaries are **not** committed to this public repository.

**This trace is predominantly boot/title/menu, not a documented battle replay.** It proves a bottleneck in the tested menu path, not every cause of battle stutters.

## Actual Windows evidence

| Metric | Observation |
|---|---:|
| CPU | AMD Ryzen 7 5700X3D, 8 physical / 16 logical cores |
| Memory | ~31.9 GiB |
| Frontend effective renderer | `soft` |
| Median reported 1-second FPS | 59.824 |
| Minimum reported 1-second FPS | 22.686 |
| Median emulator time / frame | 8.564 ms |
| p95 emulator time / frame | ~14.662 ms |
| p99 emulator time / frame | ~31.222 ms |
| Worst emulator time / frame | 32.133 ms |
| Median presentation time / frame | 0.383 ms |
| ARM9 Tier3 cumulative **instructions** | 465,476,003 |
| ARM7 Tier3 cumulative **instructions** | 276,733,898 |
| Approx. Tier3 interpreter instructions | 742,209,901 |
| Reported audio underruns, sum of intervals | 395 |

The visible FPS is a **one-second average**: it is not the duration of each individual frame and cannot prove a flawless 16.715-ms frame deadline.

At 17:04:29 (FPS 31.556) the host reports ~31.222 ms emulator time/frame and ~0.425 ms presentation. Exact Tier3 timing: **ARM9 22.733 ms/frame**, **ARM7 4.279 ms/frame**. Thus ~86.5% of emulator time in this measured interval is consumed by Tier3 fallback on those two CPUs, not the SDL presenter.

At 17:04:45 (FPS 38.975), emulator ~23.739 ms/frame; ARM9 Tier3 ~18.324 ms/frame, ARM7 Tier3 ~0.513 ms/frame. Native ARM9 Tier3 is again the dominant measured time component.

Other intervals include audio underruns and adaptive governor stage changes. Those require controlled A/B validation; do not automatically label them as causes. The .ndshp host sampler also has substantial waiting samples in Windows system DLLs; samples from waiting threads are **not** evidence of a CPU bottleneck themselves.

## Why the baseline "ARM7 main compiled" was insufficient

- Original ARM9 code's header load is `0x02000000`; known entry is `0x02000800`.
- Original ARM7 header load is `0x02380000`.
- In the runtime trace **97 ARM9 full 4-KiB RAM pages** matched their original ROM bytes exactly.
- **18 ARM7 4-KiB RAM pages** were exact unique copies of ROM image pages, **at runtime aliases** (most notably around `0x037F8000..0x03807000`). None of the captured ARM7 hot pages lay at the original ARM7 header load address.
- ARM9 also had 12 captured pages not provably matching the static main image (unknown/ambiguous and therefore excluded).
- Code addresses are not sufficient to justify execution: overlay loads and relocated code require runtime byte/content verification.

The new `tools/derive_verified_aot.py` **does not infer a function from a naked address**. It validates the cartridge SHA, each captured page SHA-1, compares an entire page against the exact original ARM9/ARM7 image, accepts only uniquely proven originals/copies, and emits explicit `[[entry_point]]` and `[[code_copy]]` configuration for a private NDSRecomp build. Gaps between proven copied pages remain gaps: never assume the intervening RAM still contains the source image. ARM mode, Thumb mode and alignment are preserved.

### Preliminary local AOT generator results

- **794 ARM9 entries** whose full execution page matched original image content.
- **222 ARM7 entries** in verified copied/relocated regions.
- **5 disjoint ARM7 code-copy ranges**, covering 18 complete pages.
- All 12 unverified ARM9 pages excluded; no heuristic overlay entrypoint used.
- With the pinned upstream recompiler (`3a57236bb23d25dcb4caad7d58d733311062ff5e`), `--audit` succeeded for both CPUs:
  - ARM9: **7,472 discovered functions**, ~306,136 decoded instructions in the audit.
  - ARM7: **1,664 discovered functions**, but audit's decoded-instruction count did not reflect all copied/relocated functions. This discrepancy requires verification; counts of functions are **not proof of correctness**.
- `--shards 24 --validate-live-bytes` for ARM9 and `--shards 16 --validate-live-bytes` for ARM7 emitted the respective C bodies and guarded dispatch tables. The emitted sources remain private.

The AOT generator is a *candidate coverage expansion*, **not** proof that the game is now native-only, stutter-free or even boot-stable. All new banks must pass differential runtime state, menu replay, and overlay-replacement tests before a user release.

## Private reproduction — no new tools needed for player

Developer-only, in an ignored/private workspace:

```bash
python3 tools/prepare_dusk_recomp.py --rom /path/to/own/Dusk-USA.nds \
    --coverage /path/to/private/game-coverage-*.json \
    --out .private/dusk-aot \
    --recompiler /path/to/pinned/nds_recompile --emit \
    --arm9-shards 24 --arm7-shards 16
```

This uses `--validate-live-bytes` **automatically** when a coverage file is supplied; do not remove it. Never distribute generated C, RAM snapshots or ROM in public GitHub CI.

### Acceptance gates before replacing the owner's v0.7

1. ROM-private runner compiles/links with generated banks, using content-validated dispatch.
2. Boot, title, New Game, menu open/close, map transition and battle all produce equivalent guest state and screenshots against v0.7 at matching virtual frame counts.
3. Same Windows machine/replay: compare 1-second and per-frame p50/p95/p99/p99.9, worst frame, Tier3 milliseconds, fallback instructions, guest input latency and audio underruns; no timing shortcuts or frame duplication.
4. Only after tests pass, package a user-friendly one-click Windows SDL3 EXE, with a rollback to v0.7. Keep Linux/macOS native plans independent.
5. No merge until user validates this improvement and CI/tests demonstrate no regression.

## Architectural clarification

The project performs actual **static ARM-to-C recompilation**, but still needs a native compatibility runtime to faithfully expose Nintendo DS hardware semantics (MMIO, timers, DMA, memory map, dual CPUs, 2D/3D graphics, audio and inputs). Removing **all** DS-derived hardware behavior without replacing it in host-native equivalents would break the program. The goal is to remove **instruction interpretation from hot game-code paths** through verified AOT execution, then progressively replace individual hardware components with maintainable native APIs where semantics are known. A complete high-level rewrite is a separate and much larger undertaking.
