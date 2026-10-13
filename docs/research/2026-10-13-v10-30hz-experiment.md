# Windows v0.10 battle/menu hitches and 30 Hz presentation experiment

Date: 2026-10-13. Source: owner-only Windows Dusk PC v0.10 files:
`performance-20261013-185225.jsonl`, `hostprof-20261013-185225.ndshp` and
`game-coverage-20261013-185225-part00.json`. None of the raw files, extracted
RAM pages or retail game bytes are in this public repository.

## Facts measured

- **458 one-second windows** between 18:52:26 and 19:00:08.
- Median reported application/guest FPS **59.834**. Worst interval after
  first 15 seconds **37.697** at 18:58:35; 18:59:49 was 40.985.
- At 18:58:35, mean game execution **24.658 ms/guest frame**, with
  **18.43 ms** inside exact ARM9 Tier3 fallback (~74.7% of game emulation time).
  ARM7 Tier3 cost ~0.09 ms; SDL presentation **0.392 ms**; reported audio
  underruns for that interval **50**. On 18:59:49, ARM9 fallback cost
  ~16.61 of 22.657 ms per frame, SDL presentation only 0.363 ms.
- Over the post-startup sampling window, ~1.1% of 1-second averages were
  below 45 FPS, ~7.8% below 55 and ~14.5% below 59. **These aggregated
  statistics do not report individual worst-frame durations** and do not
  align particular moments to damage, item usage, new enemies or menu input.
- Renderer `effective=soft`; the SDL phase is not the measured primary
  bottleneck. ARM9 Tier3 dominates the slow samples, as in earlier releases.
- The performance governor was stage 2 for most windows; changed stages
  should be investigated as correlated events, **not automatically classified
  as their cause**.

## Is 30 FPS the right solution?

**Not if it means advancing the original DS game at half its intended
speed.** ARM guest code, virtual clocks, the two DS CPUs, audio synthesis,
input sampling and in-game animation time are tied to the original approximate
**59.826 VBlanks/second**. Artificially advancing only 30 guest frames per
second would slow or desynchronize gameplay and sound.

The technically safe experiment is a **presentation-rate mode**: keep the
guest scheduler and sound on every guest frame while presenting one SDL image
for every two completed virtual frames. At nominal 59.826 Hz this is **29.913
unique visual frames/second** (not exactly 30.000). F9 or the toolbar chooses
30 or 60 and the choice persists, without changing virtual game speed.

This reduces SDL presentation cost by only about 0.18 ms per 16.7-ms guest
frame in typical scenes, based on actual measured ~0.36-ms cost. **It cannot
recover the ~18-ms ARM9 fallback cost of slow guest frames**. An observed
37.7-FPS guest slowdown could cause a 30-present mode to display only about
18.9 distinct FPS during the affected window. Therefore this is a
perceptual/compatibility experiment, not a proven fix for all stutter.

### Implementation and confidence boundaries

- Patched only upstream SDL3 native frontend:
  `tools/patches/ndsrecomp-dusk-native-30hz.patch`.
- 30 FPS visual presentation is default for this experimental branch;
  pressing **F9** or toolbar button switches 30/60 and saves preferences
  in schema v3 (old v1/v2 settings load correctly).
- The rest of the loop still executes the original full guest scheduler,
  input, graphics emulation, audio production/drain and frame-digest logging.
  Actual present count and simulated guest FPS are tracked separately in
  window title and native performance log.
- ROM-free 1,200-guest-frame cadence test passes (600 or 1,200 presents), as
  do CI validation and patch application checks.
- The private Windows 64-bit SDL3 runner cross-compiled and linked, the
  single owner-only EXE includes the correct original game image and SDL3,
  PE imports and bundle SHA256 integrity verified locally. Real Windows GUI
  operation and subjective battle smoothness need the owner's test.
- We **do not claim** a locked 30.000 visual FPS, elimination of all
  battle hitching, or completion of native recompilation. No merge before
  owner confirmation.

## Next real performance work (not replaced by the display experiment)

Another full RAM capture now demonstrates **247 distinct byte-identified code
page generations** across 4 sessions; ten RAM addresses had different
observed code contents. No *new* original-ROM overlay ID is observed beyond
0,1,2,6,7,13,17, but overlay 7 has expanded from 9/47 to **21 exact pages /
154 observed entry candidates**. Those are not automatically valid function
starts and are not all used by the current release. Next prioritize
**byte-verified static recompilation of hot ARM9 paths and overlapping
overlay versions**, with exact ARM/Thumb mode, live-byte validation and
battle-specific differential replays. Optimize guest runtime, not the
renderer's inconsequential ~0.36-ms presentation.

### Exit criteria

Run exactly the same battle menu, damage animation, item use and submenu
actions in F9 30 and F9 60 modes. Compare guest FPS, actual drawn FPS,
per-frame long-tail latencies, Tier3 ARM9 milliseconds per guest frame,
missed VBlanks, audio underruns, image/state hashes and player-perceived
smoothness. Choose the default with results, not based on speculation.
