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
                current = pages[key]
                current["executions"] = max(current.get("executions", 0), page.get("executions", 0))
                # Captures with the SAME full-page SHA1 may discover different
                # ARM/Thumb roots. Preserve their union only inside this
                # exact CPU/address/code-generation identity.
                for mode, bits_size in (("arm", PAGE_SIZE // 4 // 8),
                                        ("thumb", PAGE_SIZE // 2 // 8)):
                    field = "root_" + mode
                    a = base64.b64decode(current.get(field, ""), validate=True)
                    b = base64.b64decode(page.get(field, ""), validate=True)
                    if len(a) > bits_size or len(b) > bits_size:
                        raise ValueError(f"Invalid root bitmap size: {field} at {addr:#x}")
                    union = bytes(x | y for x, y in zip(
                        a.ljust(bits_size, b"\x00"), b.ljust(bits_size, b"\x00")))
                    if a or b:
                        current[field] = base64.b64encode(union).decode("ascii")
                # Hits are overlapping observations, not disjoint counters.
                # Taking a max avoids falsely adding duplicate sessions.
                a_hits, b_hits = current.get("root_hits", []), page.get("root_hits", [])
                if a_hits and b_hits and len(a_hits) != len(b_hits):
                    raise ValueError(f"Root histogram width mismatch at {addr:#x}")
                if b_hits:
                    current["root_hits"] = [
                        max(x, y) for x, y in zip(a_hits or [0] * len(b_hits), b_hits)]
                observed = {
                    (e.get("addr"), e.get("mode"), e.get("kind"), e.get("caller")): e
                    for e in current.get("entry_points", [])
                }
                for entry in page.get("entry_points", []):
                    k = (entry.get("addr"), entry.get("mode"),
                         entry.get("kind"), entry.get("caller"))
                    if k not in observed or int(entry.get("hits", 0)) > int(observed[k].get("hits", 0)):
                        observed[k] = entry
                if observed:
                    current["entry_points"] = list(observed.values())
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
