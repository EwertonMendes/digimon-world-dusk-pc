# v0.16 owner gameplay evidence — sanitized (2026-10-14)

Source: four gameplay sessions recorded on Oct 13–14, 2026, consisting of private
`game-coverage-*.json`, `performance-*.jsonl` and `hostprof-*.ndshp` data.
The **raw files must never be committed**: captured RAM pages include original
game code; profiler headers include local machine paths and binary stack data.

## Measured observations

| Start (local) | 1-s samples | Median FPS | Min FPS | Audio underruns | ARM9 interpreted entries | Captured pages |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oct 13 22:50:39 | 1,791 | 59.84 | 38.58 | 0 | 6,227,301 | 99 |
| Oct 13 23:21:09 | 645 | 59.85 | 38.58 | 0 | 2,348,386 | 53 |
| Oct 13 23:56:37 | 1,123 | 59.84 | 6.08 | 204 | 4,133,316 | 141 |
| Oct 14 00:15:43 | 822 | 59.85 | 38.62 | 18 | 2,720,032 | 152 |

- 4,381 one-second windows (~73.0 minutes), 222 cumulative audio underruns.
- Every capture reports zero `clean_ram_rejects9/7` and zero dropped RAM pages.
- Across four private coverage captures: **197 distinct page generations**
  at **173 CPU/address pairs**, including **16 pairs with multiple different
  page hashes**. This is why dispatch must retain CPU, address, ARM/Thumb
  mode, **live page bytes**, and overlay generation identity.
- All sessions share the expected cartridge SHA1. Their build ID is
  `unknown`, so code-generation version cannot be inferred from the logs.
- The low 6.08 FPS interval warrants correlation with audio underruns,
  CPU occupancy and presenter behavior. These aggregate windows **do not**
  prove the root cause.
- Hostprof reports significant ring eviction. Only retained stack samples
  can be symbolized to infer hottest native modules; raw `.ndshp` files
  remain with the game owner.
- A handful of **observed fallback roots** worth verifying against private
  code banks: `0x02062418`, `0x02201DC0`, `0x022040C0`,
  `0x0204D2BC`, `0x020CC914`. These are runtime addresses,
  **not pre-approved AOT candidates**. Validate real code-generation bytes
  and existing native ownership before any promotion.

## How to use the evidence safely

1. Keep private source captures outside Git (including private RAM, binary
   hostprof stacks, extracted ROM code, save files and unique user paths).
2. Run `tools/analyze_v016_sessions.py` on local paths to generate aggregate
   statistics only. Public automated tests use synthetic fixtures.
3. Run `tools/merge_verified_profiles.py` privately on the four coverage
   captures, unioning root bits only for identical verified page generations.
4. Rebuild verified ARM banks with the **owner's local ROM** and the pinned
   NDSRecomp recompiler, using `--validate-live-bytes`.
5. Compare baseline/candidate dispatch and AOT metrics. Do not claim reduced
   Tier3 work or improved FPS until a new real-game build has been benchmarked.

## Interpretation boundaries

- These are per-second FPS samples, **not frame-time p95/p99**.
- Tier3 count is interpreted work, not millisecond time or code percentage.
- No automated full-campaign QA was performed; ongoing owner playtesting is
  supplemental and is not equivalent to complete gameplay certification.
- The public CI includes a presentation-only executable and **cannot build**
  the full private ROM-derived game runner by itself.
