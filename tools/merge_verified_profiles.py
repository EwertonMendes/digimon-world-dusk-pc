#!/usr/bin/env python3
"""Merge owner-only coverage snapshots, preserving distinct RAM code generations.

All inputs must target the same ROM; each 4-KiB page is verified by SHA-1.
Same-address pages with different contents remain separate. Root observations
do not identify a particular overlay generation; --validate-live-bytes is
mandatory for generated banks.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

PAGE_SIZE = 4096


def merge(captures: list[dict]) -> dict:
    if not captures:
        raise ValueError("At least one coverage capture required")
    rom_sha1 = captures[0].get("rom_sha1")
    if not isinstance(rom_sha1, str) or len(rom_sha1) != 40:
        raise ValueError("Missing ROM SHA1 identity")
    pages = {}
    roots = {7: {}, 9: {}}
    contents_per_address = {}
    for capture in captures:
        if capture.get("kind") != "ndsrecomp-tier3-coverage" or capture.get("rom_sha1") != rom_sha1:
            raise ValueError("Incompatible coverage kind or ROM identity")
        if capture.get("pages", {}).get("page_size") not in (None, PAGE_SIZE):
            raise ValueError("Unsupported page size")
        for page in capture.get("pages", {}).get("entries", []):
            cpu = page.get("cpu")
            addr = int(page["addr"], 16)
            raw = base64.b64decode(page["data"], validate=True)
            digest = hashlib.sha1(raw).hexdigest()
            if cpu not in (7, 9) or addr % PAGE_SIZE or len(raw) != PAGE_SIZE or digest != page.get("sha1"):
                raise ValueError(f"Untrusted RAM page at {addr:#x}")
            key = (cpu, addr, digest)
            if key not in pages:
                pages[key] = dict(page)
            else:
                pages[key]["executions"] = max(pages[key].get("executions", 0), page.get("executions", 0))
            contents_per_address.setdefault((cpu, addr), set()).add(digest)
        for cpu in (7, 9):
            for root in capture.get(f"entry_points_arm{cpu}", []):
                addr = int(root["addr"], 16)
                mode = root.get("mode")
                hits = int(root.get("hits", 0))
                if mode not in ("arm", "thumb") or hits < 1 or addr % (4 if mode == "arm" else 2):
                    continue
                key = (addr, mode, root.get("kind", ""), root.get("caller", ""))
                if key not in roots[cpu] or hits > roots[cpu][key]["hits"]:
                    roots[cpu][key] = dict(root)
    return {
        "schema": 4,
        "kind": "ndsrecomp-tier3-coverage",
        "rom_sha1": rom_sha1,
        "rom_name": captures[0].get("rom_name", "game.nds"),
        "build_id": "offline-merged-not-a-runtime-build",
        "entry_points_arm9": sorted(roots[9].values(), key=lambda x: (int(x["addr"], 16), x["mode"], x.get("caller", ""))),
        "entry_points_arm7": sorted(roots[7].values(), key=lambda x: (int(x["addr"], 16), x["mode"], x.get("caller", ""))),
        "pages": {"page_size": PAGE_SIZE, "entries": [pages[k] for k in sorted(pages)]},
        "merge_provenance": {
            "input_count": len(captures),
            "unique_page_generations": len(pages),
            "different_contents_at_same_page": sum(len(v) > 1 for v in contents_per_address.values()),
            "note": "A root address alone does not prove the active overlay version.",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = merge([json.loads(f.read_text(encoding="utf8")) for f in args.captures])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result["merge_provenance"], indent=2))


if __name__ == "__main__":
    main()
