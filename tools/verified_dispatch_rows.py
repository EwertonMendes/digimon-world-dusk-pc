#!/usr/bin/env python3
"""Read *actual* NDSRecomp native dispatch entries, excluding validation metadata.

A validation initializer can look like {0xADDRu, 72u, ...}. The upstream
loose regex treats it as a dispatch row, inflating native coverage. This parser
requires the g_dispatch_* array and its exact declared length. Game-derived
generated C remains owner-private; this parser and synthetic tests are public.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

HEADER = re.compile(r"const\s+NdsDispatchEntry\s+g_dispatch_(\w+)\[\]\s*=\s*\{")
ENTRY = re.compile(
    r"\{0x([a-fA-F0-9]+)u,\s*([01])u,\s*[A-Za-z_]\w*,\s*(?:&[A-Za-z_]\w*|nullptr)\},?"
)
COUNT = re.compile(r"const\s+unsigned\s+g_dispatch_(\w+)_len\s*=\s*(\d+)u;")


def dispatch_files(paths: list[Path], cpu: int | None = None) -> list[Path]:
    found = []
    for path in paths:
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            found.extend(path.glob("*_dispatch.c"))
        else:
            raise FileNotFoundError(f"Missing dispatch source: {path}")
    found = sorted(set(found))
    if not found:
        raise ValueError("No native dispatch tables found")
    if cpu is not None and any(f"arm{cpu}" not in p.name for p in found):
        raise ValueError(f"Mixed CPU dispatch input for ARM{cpu}")
    return found


def parse_dispatch_file(path: Path) -> set[tuple[int, int]]:
    rows: set[tuple[int, int]] = set()
    inside = False
    array = None
    declared = False
    with path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            line = line.strip()
            if inside:
                if line == "};":
                    inside = False
                    continue
                match = ENTRY.fullmatch(line)
                if not match:
                    raise ValueError(f"{path}:{number}: invalid native dispatch entry")
                key = int(match.group(1), 16), int(match.group(2))
                if key in rows:
                    raise ValueError(f"{path}:{number}: duplicate native dispatch entry {key}")
                rows.add(key)
                continue
            header = HEADER.fullmatch(line)
            if header:
                if array is not None or path.name != f"{header.group(1)}_dispatch.c":
                    raise ValueError(f"{path}: duplicate/mismatched native dispatch array")
                array = header.group(1)
                inside = True
            count = COUNT.fullmatch(line)
            if count:
                if array is None or declared or count.group(1) != array:
                    raise ValueError(f"{path}: invalid native dispatch count declaration")
                if len(rows) != int(count.group(2)):
                    raise ValueError(
                        f"{path}: declared {count.group(2)} native rows; parsed {len(rows)}"
                    )
                declared = True
    if inside or not declared or not rows:
        raise ValueError(f"{path}: incomplete/empty native dispatch table")
    return rows


def read_dispatch_rows(paths: list[Path], expected_cpu: int | None = None) -> set[tuple[int, int]]:
    rows: set[tuple[int, int]] = set()
    for path in dispatch_files(paths, expected_cpu):
        rows.update(parse_dispatch_file(path))
    return rows


def verify_dispatch_growth(baseline: Path, candidate: Path) -> dict:
    """Every original dispatch row must survive, within its *same* bank."""
    old = {p.name: parse_dispatch_file(p) for p in dispatch_files([baseline])}
    new = {p.name: parse_dispatch_file(p) for p in dispatch_files([candidate])}
    absent = sorted(old.keys() - new.keys())
    if absent:
        raise ValueError(f"Missing original bank(s): {absent}")
    banks = {}
    for name, original in sorted(old.items()):
        candidate_rows = new[name]
        lost = original - candidate_rows
        if lost:
            sample = [f"0x{pc:08X}:{mode}" for pc, mode in sorted(lost)[:8]]
            raise ValueError(f"{name}: lost {len(lost)} native entries: {sample}")
        banks[name] = {
            "previous": len(original),
            "candidate": len(candidate_rows),
            "added": len(candidate_rows - original),
            "removed": 0,
        }
    return {"status": "no-native-dispatch-regressions",
            "new_rows_total": sum(item["added"] for item in banks.values()),
            "by_bank": banks}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify_dispatch_growth(args.baseline, args.candidate), indent=2))


if __name__ == "__main__":
    main()
