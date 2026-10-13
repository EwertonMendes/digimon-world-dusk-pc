#!/usr/bin/env python3
"""Derive and validate static ARM9/ARM7 recompilation seeds from captured RAM.

Strictly offline, ROM-private. Execution roots are only accepted when their
entire captured 4-KiB page matches the original ROM image byte-for-byte.
Copied ARM7 code uses code_copy and MUST emit --validate-live-bytes dispatch.
"""
from __future__ import annotations

import argparse
import base64
import collections
import hashlib
import json
from pathlib import Path
import struct
import tomllib

ROM_SHA256 = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"
PAGE = 4096


def images(rom: bytes) -> dict:
    result = {}
    for cpu, header in ((9, 0x20), (7, 0x30)):
        offset, entry, base, length = struct.unpack_from("<4I", rom, header)
        if not length or offset + length > len(rom) or not base <= entry < base + length:
            raise ValueError(f"Invalid ARM{cpu} image bounds")
        result[cpu] = (base, rom[offset:offset + length])
    return result


def verified_pages(snapshot: dict) -> list[dict]:
    if snapshot.get("kind") != "ndsrecomp-tier3-coverage":
        raise ValueError("Wrong coverage format")
    pages = []
    for item in snapshot.get("pages", {}).get("entries", []):
        addr = int(item["addr"], 16)
        if item["cpu"] not in (7, 9) or addr % PAGE:
            raise ValueError("Invalid captured CPU/page")
        data = base64.b64decode(item["data"], validate=True)
        if len(data) != PAGE or hashlib.sha1(data).hexdigest() != item["sha1"]:
            raise ValueError(f"Invalid RAM page identity: 0x{addr:08X}")
        pages.append({"cpu": item["cpu"], "addr": addr, "data": data})
    return pages


def unique_offset(image: bytes, data: bytes) -> int | None:
    pos = image.find(data)
    if pos < 0 or image.find(data, pos + 1) >= 0:
        return None
    return pos


def derive(rom: bytes, snapshot: dict) -> dict:
    if snapshot.get("rom_sha1") != hashlib.sha1(rom).hexdigest():
        raise ValueError("Coverage ROM SHA1 mismatch")
    binaries = images(rom)
    proven = collections.defaultdict(dict)
    aliases = collections.defaultdict(list)
    rejected = collections.Counter()

    for page in verified_pages(snapshot):
        cpu, addr, data = page["cpu"], page["addr"], page["data"]
        base, image = binaries[cpu]
        if base <= addr and addr + PAGE <= base + len(image):
            if data == image[addr - base:addr - base + PAGE]:
                proven[cpu][addr] = ("original", addr - base)
            else:
                rejected[f"arm{cpu}_modified_in_place"] += 1
            continue
        offset = unique_offset(image, data)
        if offset is None:
            rejected[f"arm{cpu}_unmatched_or_ambiguous_page"] += 1
            continue
        aliases[(cpu, addr - offset)].append((addr, offset))

    copies = []
    for (cpu, alias_base), pages in sorted(aliases.items()):
        if len(pages) < 2:
            rejected[f"arm{cpu}_unproven_isolated_alias"] += len(pages)
            continue
        groups = []
        for addr, offset in sorted(pages):
            if groups and addr == groups[-1][-1][0] + PAGE and offset == groups[-1][-1][1] + PAGE:
                groups[-1].append((addr, offset))
            else:
                groups.append([(addr, offset)])
        for group in groups:
            # A gap ends the proof: never assume nearby RAM matches.
            for addr, offset in group:
                proven[cpu][addr] = ("copy", offset)
            copies.append({"cpu": cpu, "runtime_start": group[0][0],
                           "source_start": binaries[cpu][0] + group[0][1],
                           "size": PAGE * len(group), "verified_pages": len(group),
                           "alias_base": f"0x{alias_base:08X}"})

    seeds = {"dusk_arm9_main": [], "dusk_arm7_main": []}
    skipped = collections.Counter()
    for cpu in (9, 7):
        found = {}
        for candidate in snapshot.get(f"entry_points_arm{cpu}", []):
            addr = int(candidate["addr"], 16)
            mode = candidate["mode"]
            hits = int(candidate.get("hits", 0))
            if mode not in ("arm", "thumb") or addr % (4 if mode == "arm" else 2) or hits < 1:
                skipped[f"arm{cpu}_invalid_entry"] += 1
                continue
            pg = addr & ~(PAGE - 1)
            proof = proven[cpu].get(pg)
            if proof is None:
                skipped[f"arm{cpu}_unverified_page"] += 1
                continue
            kind, offset = proof
            image = binaries[cpu][1]
            pos = offset + addr - pg
            if pos + (4 if mode == "arm" else 2) > len(image):
                skipped[f"arm{cpu}_out_of_image"] += 1
                continue
            key = (addr, mode)
            if key not in found or hits > found[key]["hits"]:
                found[key] = {"addr": f"0x{addr:08X}", "mode": mode,
                              "hits": hits, "page_kind": kind}
        seeds[f"dusk_arm{cpu}_main"] = [item for _, item in sorted(found.items())]
    return {"seeds": seeds, "code_copies": copies,
            "original_verified_pages": {str(cpu): sum(v[0] == "original" for v in proven[cpu].values())
                                        for cpu in (7,9)},
            "copied_verified_pages": {str(cpu): sum(v[0] == "copy" for v in proven[cpu].values())
                                      for cpu in (7,9)},
            "rejected_pages": dict(rejected), "skipped_roots": dict(skipped)}


def apply_private_configs(folder: Path, report: dict) -> None:
    # Fail closed: only apply to ROM-verified, unmodified original bank configs.
    # Backups preserve original configuration in the same private folder.
    pending = []
    for cpu in (9, 7):
        bank = f"dusk_arm{cpu}_main"
        path = folder / f"{bank}.toml"
        original = path.read_text(encoding="utf-8")
        cfg = tomllib.loads(original)
        binary = (folder / f"{bank}.bin").read_bytes()
        if cfg["program"]["cpu"] != f"arm{cpu}" or cfg["identity"]["sha1"] != hashlib.sha1(binary).hexdigest():
            raise ValueError(f"{bank}: unsafe input identity")
        if "verified-AOT-seeds" in original or path.with_suffix(".toml.before-aot").exists():
            raise ValueError(f"{bank}: already patched")
        known = {(int(e["addr"]), e["mode"]) for e in cfg.get("entry_point", [])}
        lines = ["", "# verified-AOT-seeds: full-page ROM/RAM identity proofs"]
        for seed in report["seeds"][bank]:
            key = (int(seed["addr"], 16), seed["mode"])
            if key in known:
                continue
            lines.extend(("", "[[entry_point]]", f'addr = {seed["addr"]}',
                          f'mode = "{seed["mode"]}"',
                          f'name = "observed_{seed["mode"]}_{key[0]:08x}"'))
        for copy in report["code_copies"]:
            if copy["cpu"] != cpu:
                continue
            lines.extend(("", "[[code_copy]]",
                          f'runtime_start = 0x{copy["runtime_start"]:08X}',
                          f'source_start = 0x{copy["source_start"]:08X}',
                          f'size = 0x{copy["size"]:X}',
                          'name = "verified_full_page_copy"'))
        updated = original + "\n".join(lines) + "\n"
        tomllib.loads(updated)
        pending.append((path, original, updated))
    for path, original, updated in pending:
        path.with_suffix(".toml.before-aot").write_text(original, encoding="utf-8")
        path.write_text(updated, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rom", type=Path, required=True)
    ap.add_argument("--coverage", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--prepared", type=Path, help="Private directory containing already verified .toml and .bin banks")
    args = ap.parse_args()
    raw = args.rom.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ROM_SHA256:
        ap.error("Only exact Dusk USA image is supported")
    result = derive(raw, json.loads(args.coverage.read_text(encoding="utf-8")))
    if args.prepared:
        apply_private_configs(args.prepared, result)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "verified-aot.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"roots": {k: len(v) for k,v in result["seeds"].items()},
                      "copies": result["code_copies"],
                      "rejections": result["rejected_pages"]}, indent=2))
    print("Emit derived banks only with --validate-live-bytes. Do not publish derived source/ROM.")


if __name__ == "__main__":
    main()
