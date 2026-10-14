#!/usr/bin/env python3
"""Summarize private NDSRecomp gameplay diagnostics without exporting ROM pages.

Only aggregate metrics, ROM identity and virtual CPU addresses leave local input.
The script never writes RAM pages, host user names, absolute paths or stack samples.
One-second FPS samples are not per-frame p95/p99 measurements.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

DS_FPS = 59.8261


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("Cannot quantify an empty series")
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * quantile
    lower = int(position)
    upper = min(len(sorted_values) - 1, lower + 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def read_perf(path: Path) -> tuple[str, dict]:
    samples = []
    cartridge = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("kind") == "session":
                cartridge = event.get("rom_sha1")
            elif event.get("kind") == "perf":
                samples.append(event)
    if not samples or cartridge is None:
        raise ValueError(f"Missing session header or samples in {path.name}")
    fps = [float(e["fps"]) for e in samples]
    emu = [float(e.get("ms_per_frame", {}).get("emu", 0)) for e in samples]
    present = [float(e.get("ms_per_frame", {}).get("present", 0)) for e in samples]
    underruns = sum(int(e.get("underruns_delta", 0)) for e in samples)
    def round_pct(xs: list[float], q: float) -> float: return round(percentile(xs, q), 3)
    return cartridge, {
        "one_second_intervals": len(samples),
        "fps_median": round_pct(fps, 0.5),
        "fps_p05": round_pct(fps, 0.05),
        "fps_min": round(min(fps), 3),
        "intervals_below_95pct_target": sum(x < DS_FPS * 0.95 for x in fps),
        "emu_ms_p95": round_pct(emu, 0.95),
        "present_ms_p95": round_pct(present, 0.95),
        "audio_underruns": underruns,
        "tier3_arm9_instructions": sum(int(e.get("tier3_delta", {}).get("arm9", {}).get("instructions", 0)) for e in samples),
        "tier3_arm7_instructions": sum(int(e.get("tier3_delta", {}).get("arm7", {}).get("instructions", 0)) for e in samples),
    }


def read_coverage(path: Path) -> tuple[str, dict, set, dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != 4 or doc.get("kind") != "ndsrecomp-tier3-coverage":
        raise ValueError(f"Unsupported coverage format in {path.name}")
    unique = set()
    by_address = defaultdict(set)
    for page in doc.get("pages", {}).get("entries", []):
        # This is metadata for prioritization, NOT enough to authorize AOT.
        key = (page["cpu"], page["addr"], page["sha1"])
        unique.add(key)
        by_address[(page["cpu"], page["addr"])].add(page["sha1"])
    stat = doc.get("static_coverage", {})
    return doc["rom_sha1"], {
        "captured_page_generations": len(unique),
        "dropped_pages": doc.get("pages", {}).get("dropped"),
        "tier3_arm9_entries": stat.get("tier3_entries9"),
        "tier3_arm7_entries": stat.get("tier3_entries7"),
        "clean_ram_rejects9": stat.get("clean_ram_rejects9"),
        "clean_ram_rejects7": stat.get("clean_ram_rejects7"),
    }, unique, dict(by_address)


def read_hostprof(path: Path) -> dict:
    # Read metadata only; binary stack data and module paths are never exported.
    with path.open("rb") as stream:
        header = stream.readline(1024 * 1024)
    if not header.endswith(b"\\n"):
        raise ValueError(f"Host profiler header exceeds limit in {path.name}")
    doc = json.loads(header)
    if doc.get("format") != "ndsrecomp-hostprof" or doc.get("version") != 1:
        raise ValueError(f"Unsupported host profiler: {path.name}")
    return {
        "hist_total": int(doc.get("hist_total", 0)),
        "ring_evicted": int(doc.get("ring_evicted", 0)),
        "hist_overflow": int(doc.get("hist_overflow", 0)),
        "emu_samples": int(doc.get("roles", {}).get("emu", 0)),
        "render_samples": int(doc.get("roles", {}).get("render", 0)),
        "profiler_suspended_ms": round(float(doc.get("overhead", {}).get("suspended_ms", 0)), 3),
    }


def summarize(perf: list[Path], coverage: list[Path], hostprof: list[Path]) -> dict:
    identity = None
    perf_results = []
    coverage_results = []
    hostprof_results = []
    generations = set()
    changed = defaultdict(set)

    def ensure_identity(value: str) -> None:
        nonlocal identity
        if not isinstance(value, str) or len(value) != 40:
            raise ValueError("Invalid ROM SHA-1 identity")
        if identity is None:
            identity = value
        elif identity != value:
            raise ValueError("Mixed ROM identities are forbidden")

    for path in perf:
        rom, item = read_perf(path)
        ensure_identity(rom)
        perf_results.append(item)
    for path in coverage:
        rom, item, codes, addresses = read_coverage(path)
        ensure_identity(rom)
        generations.update(codes)
        for key, hashes in addresses.items():
            changed[key].update(hashes)
        coverage_results.append(item)
    for path in hostprof:
        hostprof_results.append(read_hostprof(path))

    return {
        "format": "dusk-v017-safe-diagnostics",
        "source": "v0.16 gameplay diagnostics (sanitized metadata)",
        "rom_sha1": identity,
        "performance_sessions": perf_results,
        "coverage_sessions": coverage_results,
        "hostprof_sessions": hostprof_results,
        "totals": {
            "one_second_intervals": sum(x["one_second_intervals"] for x in perf_results),
            "audio_underruns": sum(x["audio_underruns"] for x in perf_results),
            "unique_cpu_address_page_generations": len(generations),
            "unique_cpu_address_pages": len(changed),
            "pages_with_multiple_generations": sum(len(v) > 1 for v in changed.values()),
        },
        "interpretation": [
            "An interval's FPS is not a per-frame latency distribution.",
            "Tier3 entries from different sessions must not be interpreted as unique functions.",
            "Captured overlay pages must be byte-validated against original code before AOT promotion.",
            "Host profiler ring eviction means detailed old samples may have been lost.",
            "The report does not contain ROM page data, user paths or profiler stacks.",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--perf", nargs="+", type=Path, required=True)
    ap.add_argument("--coverage", nargs="+", type=Path, required=True)
    ap.add_argument("--hostprof", nargs="+", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    report = summarize(args.perf, args.coverage, args.hostprof)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report["totals"], indent=2))


if __name__ == "__main__":
    main()
