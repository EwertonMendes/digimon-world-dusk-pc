#!/usr/bin/env python3
"""Analyze NDSRecomp's per-second native FPS/CPU/Tier3 performance log.

Works on the locally emitted performance-*.jsonl without ROM/game assets or
developer tools. Does not upload anything. Do not interpret GUI FPS alone as
guest speed; correlate emulator-frame timing, underruns and Tier3 work.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def load(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
            if isinstance(event, dict) and event.get("kind") == "perf":
                records.append(event)
    if not records:
        raise ValueError(f"No performance samples in {path}")
    return records


def summarize(records: list[dict], target: float = 59.8261) -> dict:
    samples = []
    for e in records:
        try:
            fps = float(e["fps"])
            timing = e.get("ms_per_frame") or {}
            t3 = (e.get("tier3_delta") or {}).get("arm9") or {}
            stage = (e.get("governor") or {}).get("stage")
            samples.append({
                "wall": str(e.get("wall", "")),
                "frame": int(e.get("frames", 0)),
                "fps": round(fps, 2),
                "emu_ms": round(float(timing.get("emu") or 0), 2),
                "present_ms": round(float(timing.get("present") or 0), 2),
                "draw_ms": round(float(timing.get("draw") or 0), 2),
                "swap_ms": round(float(timing.get("swap") or 0), 2),
                "audio_underruns": int(e.get("underruns_delta") or 0),
                "tier3_arm9": int(t3.get("instructions") or 0),
                "governor_stage": stage,
            })
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"Malformed performance sample: {e!r}") from exc
    fps_values = [e["fps"] for e in samples]
    slowest = sorted(samples, key=lambda e: e["fps"])[:12]
    return {
        "target_guest_frames_per_second": target,
        "sample_intervals": len(samples),
        "mean_fps": round(statistics.fmean(fps_values), 2),
        "min_fps": min(fps_values),
        "worst_intervals": slowest,
        "below_95pct_target": sum(e["fps"] < target * 0.95 for e in samples),
        "audio_underruns": sum(e["audio_underruns"] for e in samples),
        "notes": [
            "Intervals include loading, pauses, menus and battle; compare equivalent gameplay states.",
            "Tier3 counts indicate interpreter fallback work, not milliseconds by themselves.",
            "Total GUI FPS is not enough to attribute GPU vs guest-CPU cost.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path, help="performance-*.jsonl from DuskNativePC/v0.7/diagnostics")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    report = summarize(load(args.file))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Samples: {report['sample_intervals']}, mean {report['mean_fps']:.2f}, "
              f"min {report['min_fps']:.2f} FPS, slow (<95% of DS target): "
              f"{report['below_95pct_target']}")
        print("Worst intervals (sampled 1-second windows):")
        for s in report["worst_intervals"]:
            print(f"  frame={s['frame']:>6} fps={s['fps']:>6} emu={s['emu_ms']:>7} ms "
                  f"present={s['present_ms']:>6} ms t3_arm9={s['tier3_arm9']:>10} "
                  f"governor={s['governor_stage']} audio_underruns={s['audio_underruns']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
