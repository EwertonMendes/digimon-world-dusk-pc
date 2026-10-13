#!/usr/bin/env python3
"""Plan only newly observed byte-proven AOT overlays for incremental private builds.

No ARM code or ROM image is written into source control. A plan is evidence,
not a promise that a scene or specific transition is fixed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from derive_verified_overlays import verified_overlay_roots
from merge_verified_profiles import merge

def delta_plan(rom: bytes, captures: list[dict], shipped_overlay_ids: set[int]) -> dict:
    if not captures:
        raise ValueError("Missing coverage snapshots")
    merged = merge(captures)
    proven = verified_overlay_roots(rom, merged)
    observed = {record["overlay_id"]: record for record in proven}
    selected = [record for record in proven if record["overlay_id"] not in shipped_overlay_ids]
    return {
        "rom_sha1": merged["rom_sha1"],
        "profile_count": len(captures),
        "page_generations": merged["merge_provenance"]["unique_page_generations"],
        "same_address_variants": merged["merge_provenance"]["different_contents_at_same_page"],
        "shipped_overlay_ids": sorted(shipped_overlay_ids),
        "observed_overlay_ids": sorted(observed),
        "new_overlay_ids": [record["overlay_id"] for record in selected],
        "new_banks": [
            {"bank": record["bank"], "overlay_id": record["overlay_id"],
             "image_sha1": record["source_sha1"],
             "verified_pages": len(record["verified_pages"]),
             "observed_roots": len(record["roots"])}
            for record in selected
        ],
        "requirements": ["validate_live_bytes", "staged_link", "differential_guest_replay",
                         "owner_windows_performance_verification"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom", type=Path, required=True)
    p.add_argument("--coverage", type=Path, nargs="+", required=True)
    p.add_argument("--shipped-overlays", type=int, nargs="*", default=[0, 1, 2, 6, 13, 17])
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = delta_plan(args.rom.read_bytes(),
                        [json.loads(path.read_text(encoding="utf8")) for path in args.coverage],
                        set(args.shipped_overlays))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
