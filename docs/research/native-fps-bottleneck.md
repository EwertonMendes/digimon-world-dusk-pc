# Native frame-time investigation (2026-10-13)

The Windows v0.4 browser host imposed a synchronous bottleneck: debug command -> advance 2 virtual frames -> JSON hex framebuffer per screen -> PNG encode -> Base64 -> HTTP -> browser repaint; next request only after processing.

Native SDL3 v0.5 eliminates that entire transport. The guest ARM9/ARM7 code is still statically recompilated and linked into the native runner.

## Actual offline measurements

All runs used the exact user-provided USA ROM locally; Linux x64 container, NDSRecomp headless debug control, counting VBlanks instead of inventing visual FPS:

- Title banks -O0 (first 30 VBlanks): 30 / 1.338 s = 22.4 VBlanks/s.
- Title banks -O1 (first 60 VBlanks): 60 / 1.855 s = 32.35 VBlanks/s. Approx. 44% higher rate than the initial small -O0 measurement; windows and sample-window differences prevent treating it as a stable in-game improvement metric.
- Title banks -O2 (first 60 VBlanks): 60 / 1.859 s = 32.28 VBlanks/s. No material gain over -O1 for this early boot sample.
- Title banks -O2 (first 180 VBlanks): 180 / 2.273 s = 79.2 VBlanks/s on average. **Not a sustained in-game figure**: boot/idle phases differ strongly across that window. It does prove the host can sometimes advance VBlanks faster than wall-clock 60 Hz.

The important profiler finding at 180 VBlanks is in the exclusive, exact engine buckets: **ARM9 Tier3 fallback interpreter ~1.499 s** of ~2.273 s elapsed, while GPU2D raster was ~0.107 s. ARM7 Tier3 cost was ~0.116 s. This strongly suggests that *verified native coverage of the ARM9 dynamic execution paths*, rather than merely raising optimization of already generated C from -O1 to -O2, is the most valuable next performance target. The sampled 'exec' PCs included addresses in the known ARM9 main image (0x0200F9E0, 0x02008EE4, 0x0200DF14, etc.); those are diagnostic samples, **not automatically validated function entry points**. Do not promote them to generated banks without checking instruction mode, live bytes, memory ownership and control flow.

## Next rigorous gates

1. Have the owner execute the GUI v0.5 on Windows and report the FPS in the native SDL title and the native-performance.log phase diagnostics.
2. Reproduce the same 60+ frame window on a loaded first story map, not just an intro/boot window; compare -O0 and -O1 with identical replay input.
3. Instrument native guest PC fallback hotspots and statically recompile *verified* missing paths/overlays only with runtime live-byte guards and regression checks.
4. Keep guest timers and music at their original clock. Do not fake 60 FPS by presenting duplicate frames as if the underlying game had accelerated.
5. Preserve title/dispatched bank build optimization as a separate, documented setting NDS_TITLE_BANK_OPT_LEVEL.

This research includes no ROM bytes or generated game code.
