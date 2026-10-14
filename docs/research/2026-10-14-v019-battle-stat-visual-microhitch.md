# v0.19 owner session: isolate battle HP/stat visual hitch

## Accepted baseline (owner Windows test)
- Build: `d9da848-dirty`, UI app v0.19, Dusk USA ROM SHA1 `de1a1915e07288ffad654f3f9f2eb730a0fd1d9c`.
- User reports menu/map transitions no longer have audible freezes; preserve existing SDL SPU device parameters, ~188ms queue and clock pacing unchanged.
- Only remaining noticeable issue: **single video-only pause** while a battle technique/item changes HP or another combat statistic; moving background stops briefly and resumes.

## Actual measurement from one local 16:45:13–16:56:09 session
- 649 one-second samples, median ~59.846 host FPS.
- Median per-frame averaged guest emulation: **4.948ms**; 99th percentile of those *per-second averages* **8.545ms**; largest averaged interval **11.324ms** (initial 16:45:14).
- Median per-frame averaged presentation **0.328ms**; 99th percentile **0.370ms**. These values do **not** capture an exceptional, single long frame.
- Audio underrun deltas total 57, concentrated at 16:45:21 (17), 16:45:22 (32), 16:45:24 (8); not distributed throughout later battle play. These counters do not contradict the user's assessment that later audio played smoothly.
- Live overlays were disabled. GPU compositor is software-only in this session, at native resolution with no frame interpolation.
- Profiling was enabled, so measurement overhead is a caveat. The uploaded hostprof header reports 250Hz sampling and 5.8sec cumulative thread suspension over ~10.9 minutes; it does not prove the one-frame battle hitch is profiler-induced.
- Tier3 fallback still executes heavily in ARM9 during some periods, but none of the **per-second** counters uniquely attributes the HP/stat update to any function or distinguishes subsecond CPU jitter from a missed host presentation deadline.

## Why a tiny pause is hard to locate
At ~59.826 DS frames/second a single guest frame with >16.7ms work can visibly
hold a moving background for one refresh, yet 59 other fast frames keep the
**one-second average** FPS near 59.8. It is unsafe to select an arbitrary
ARM9/overlay target or alter interpolation/render pacing based on those averages.

## First scoped PR action
Measure only in the diagnostic-enabled build:
- Count guest-emulation frames >12ms and >16.715ms, not guest input events.
- Count **wall presentation gaps >20ms**, including event/pacing overhead.
- Retain session peak emulation, frame gap and host presentation with frame IDs.
- Emit **per-second deltas** in existing performance JSONL; no per-frame file
  writes, raw RAM, screenshots, game code, or runtime string allocations.
- A backward-compatible Python analyzer reports battle-window spike counts.
- **Do not touch** the SPU, audio queue sizes, gameplay clock, save format,
  player controls, game textures, or overlay dispatch tables.

## Next acceptance gate
1. Review compile/ROM-free patch integration.
2. Produce a Windows owner playtest candidate only after tests pass.
3. Reproduce 3+ instances of technique damage, heal/item HP restoration,
   buffs/debuffs (ATK/DEF/Speed etc) and compare nearby time windows for
   `frame_spikes` versus `tier3_delta` / `emu_attrib` / display/render.
4. Only then optimize the verified cause in a later commit on this PR;
   unchanged original audio is a regression gate.
No fix to the video hitch is claimed merely by adding instrumentation.

## Privacy
Only summarized aggregates are committed. The original capture's RAM-page
bytes, .nds, hostprof samples, save and raw performance trace remain private.
