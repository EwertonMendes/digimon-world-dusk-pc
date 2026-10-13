# Dusk native PC — frame-time and battle profiling (v0.7)

## User-verified baseline

- Windows v0.6 is running in its own SDL3 window with the original game frames, audio and controls.
- During light title/dialogue scenes, the title bar shows approximately 59.6–59.8 FPS.
- The user reports notable frame drops when entering menus, changing scenes and especially battles. Those battle drops have **not yet been instrumented**, so no specific CPU/GPU root cause is proven.
- Original DS frame cadence is about **59.826 Hz**. The target is stable guest frame advance and audio at that rate, *not* an artificial 69 FPS display.

## Changes prepared for v0.7

1. The native SDL3 compositor supports **F8 / SWAP**. This reverses main/aux screen locations in Modern and Side-by-side layouts, inverts vertical order in Classic, and mirrors Floating horizontally. The actual touchscreen is still the bottom DS screen and its input mapping follows the transformed geometry; the screen swap never alters the ARM guest routing.
2. Layout preferences move to version 2, with backward support for the user's version-1 saved settings. Rendering/ARM code outside the compositor is unchanged.
3. Native Windows launcher starts the runtime with NDSRecomp's **existing built-in profiling**, locally: `--diagnostics on --diagnostics-dir %LOCALAPPDATA%\\DuskNativePC\\v0.7\\diagnostics --diagnostics-interval-ms 1000`. A `performance-*.jsonl` file is produced next to run-local timing and dispatch diagnostics.
4. `tools/analyze_native_perf.py` reports the worst 1-second intervals with emulation time, presentation time, interpreter fallback instructions, audio underruns and governor stage. This is a read-only, stdlib-only helper with synthetic tests.

## Accurate next performance investigation

Test the same character and battle entry several times, let the game run a few minutes and close it normally. Compare records before/during/after the battle in `performance-*.jsonl`:

- If `ms_per_frame.emu` and Tier3 ARM9 work spike while presentation remains low, inspect indirect branches and *verified* overlay dispatch coverage in the game banks.
- If presentation/draw/swap spike, profile scene-specific GPU2D/GPU3D and resource uploads, accounting for driver backend and shader cache. Avoid unjustified global quality reductions.
- If emulation stays normal but audio underruns or governor changes coincide with dips, inspect audio pacing, scheduler and governor transitions.
- Make any optimization against a reproducible replay that includes **battle**, not title-only benchmarks. Record worst-case frame time and stutter counts, not only average FPS.

## Important distribution and verification notes

The public GitHub repo and its CI contain **no** commercial ROM, generated ARM bank code, saves or game assets. The complete single-click build is privately packaged from the owner's supplied ROM and its corresponding source. The v0.7 Windows PE and integrity can be validated here; actual native Windows gameplay FPS still requires testing on the user's PC.

**No battle FPS improvement is claimed yet.** v0.7 provides the requested screen swap and evidence needed to make battle-specific fixes without speculation. Saves remain disabled.
