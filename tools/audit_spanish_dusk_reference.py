#!/usr/bin/env python3
"""Read-only comparison of an authorized Spanish Dusk ROM against the exact USA source.

A third-party patch must be applied separately to the user's authorized source.
This script NEVER downloads games, writes a ROM, or exports extracted resources.
It emits numeric inventory only, sufficient to locate the graphic/text changes
made by a native translation without mistaking FAT relocations for edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from probe_dusk_strings import SHA256, files, u32

RESOURCE_PACKS = ("dat/SPR_CHR.PAK", "dat/SPR_CEL.PAK", "dat/SPR_PAL.PAK", "dat/MSG.PAK")
MAX_ROM = 256 * 1024 * 1024
MAX_ENTRY = 8192


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pack_entries(data: bytes, maximum: int = MAX_ENTRY) -> list[bytes]:
    """Decode only the index/bounds of the game's indexed resource packs."""
    if len(data) < 12:
        raise ValueError("pack truncated")
    count = u32(data, 0)
    if not 1 <= count <= maximum or 4 + count * 8 > len(data):
        raise ValueError("invalid resource pack index")
    bounds = []
    for i in range(count):
        at = u32(data, 4 + 8 * i)
        size = u32(data, 8 + 8 * i) & 0x7fffffff
        if size == 0 or at < 4 + count * 8 or at + size > len(data):
            raise ValueError(f"invalid resource pack entry {i}")
        bounds.append((at, at + size))
    ordered = sorted(bounds)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        raise ValueError("overlapping resource entries")
    return [data[start:end] for start, end in bounds]


def changed_entries(original: bytes, translated: bytes) -> dict:
    a = pack_entries(original)
    b = pack_entries(translated)
    common = min(len(a), len(b))
    changes = [i for i in range(common) if a[i] != b[i]]
    return {
        "original_entries": len(a),
        "translated_entries": len(b),
        "changed_ids": changes,
        "added_ids": list(range(common, len(b))),
        "removed_ids": list(range(common, len(a))),
    }


def compare_source_roms(source: bytes, translation: bytes) -> dict:
    if sha(source) != SHA256:
        raise ValueError("source must be the exact authenticated Dusk USA cartridge")
    if not 0 < len(translation) <= MAX_ROM:
        raise ValueError("unexpected translated ROM size")
    if translation[12:16] != source[12:16]:
        raise ValueError("different NDS game ID; not a Dusk USA translation")
    sf, tf = files(source), files(translation)
    all_names = sorted(set(sf) | set(tf))
    changed = []
    for name in all_names:
        old = source[sf[name][1]:sf[name][2]] if name in sf else None
        new = translation[tf[name][1]:tf[name][2]] if name in tf else None
        if old == new:
            continue
        changed.append({
            "name": name,
            "source_bytes": len(old) if old is not None else None,
            "reference_bytes": len(new) if new is not None else None,
            "category": (
                "sprite_pack" if name in RESOURCE_PACKS[:3]
                else "message_pack" if name == RESOURCE_PACKS[3]
                else "nitro_graphics" if name.upper().endswith(
                    (".NCGR", ".NCLR", ".NCER", ".NSCR", ".NFTR", ".NANR"))
                else "other"
            ),
        })
    packs = {}
    for name in RESOURCE_PACKS:
        if name in sf and name in tf:
            original = source[sf[name][1]:sf[name][2]]
            translated = translation[tf[name][1]:tf[name][2]]
            packs[name] = changed_entries(original, translated)
    def bank(offset: int, size: int, buf: bytes) -> bytes:
        a, length = u32(buf, offset), u32(buf, size)
        if not 0 < a < len(buf) or length > len(buf) - a:
            raise ValueError("invalid ARM bank location")
        return buf[a:a+length]
    arm = {}
    for name, off, size in (("ARM9", 0x20, 0x2c), ("ARM7", 0x30, 0x3c)):
        a, b = bank(off, size, source), bank(off, size, translation)
        arm[name] = {
            "bytes_original": len(a),
            "bytes_translated": len(b),
            "changed": a != b,
        }
    return {
        "format": 1,
        "source_sha256": SHA256,
        "reference_sha256": sha(translation),
        "reference_bytes": len(translation),
        "game_code": source[12:16].decode("ascii"),
        "nitrofs": {
            "source_files": len(sf), "reference_files": len(tf),
            "modified_file_count": len(changed),
            "modified_files": changed,
        },
        "indexed_packs": packs,
        "arm_banks": arm,
        "caution": "Structural differences are not proof of correct in-game rendering.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--translated", type=Path, required=True,
                        help="Locally produced translation from a lawful patch")
    parser.add_argument("--out", type=Path, required=True,
                        help="Metadata-only JSON report, not a ROM dump")
    args = parser.parse_args()
    if args.original.resolve() == args.translated.resolve():
        raise SystemExit("original and translated paths must differ")
    result = compare_source_roms(args.original.read_bytes(), args.translated.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Modified NitroFS:", result["nitrofs"]["modified_file_count"])
    for name, pack in result["indexed_packs"].items():
        print(name, "modified IDs:", len(pack["changed_ids"]), pack["changed_ids"][:40])


if __name__ == "__main__":
    main()
