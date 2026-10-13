#!/usr/bin/env python3
"""Refresh shipped ARM9 overlay AOT from exact-ROM, full-page owner captures.

Run in an owner-private workspace ONLY. Output C contains copyrighted game code:
NEVER commit generated/ or ROM/ to the public repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tomllib

from derive_verified_overlays import verified_overlay_roots
from merge_verified_profiles import merge

DUSK_USA_SHA256 = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"


def selected_overlays(rom: bytes, captures: list[dict], approved_ids: set[int]) -> list[dict]:
    if hashlib.sha256(rom).hexdigest() != DUSK_USA_SHA256:
        raise ValueError("Wrong Dusk USA ROM SHA256")
    merged = merge(captures)  # full-page SHA1, every RAM generation preserved
    observed = {int(b["overlay_id"]): b for b in verified_overlay_roots(rom, merged)}
    unknown = approved_ids - observed.keys()
    if unknown:
        raise ValueError(f"Requested IDs with no verified observed code: {sorted(unknown)}")
    return [observed[i] for i in sorted(approved_ids)]


def build_config(proof: dict, actual_rom_image: bytes, previous_config: str) -> str:
    """Fail closed: only update a previously shipped bank, identical ROM image."""
    prev = tomllib.loads(previous_config)
    name = proof["bank"]
    if (prev["program"]["name"] != name or
        prev["program"]["cpu"] != "arm9" or
        prev["program"]["load_address"] != proof["load_address"] or
        prev["identity"]["sha1"] != proof["source_sha1"] or
        hashlib.sha1(actual_rom_image).hexdigest() != proof["source_sha1"] or
        len(actual_rom_image) != proof["size"]):
        raise ValueError(f"{name}: shipped identity does not match verified cartridge image")
    if not proof["verified_pages"] or not proof["roots"]:
        raise ValueError(f"{name}: no full-page code proof")
    first = proof["roots"][0]
    lines = [
        "# Derived from owner ROM and exact 4096-byte executed RAM pages.",
        "# Emit with --validate-live-bytes; overlay RAM can be reused.",
        "[program]",
        f'name = "{name}"', f'id = "{name}"', 'cpu = "arm9"', 'isa = "armv5te"',
        f'load_address = 0x{proof["load_address"]:08X}',
        f'size = 0x{proof["size"]:X}', f'entry_pc = {first["addr"]}',
        "[identity]", f'sha1 = "{proof["source_sha1"]}"',
    ]
    for e in proof["roots"]:
        a = int(e["addr"], 16)
        mode = e["mode"]
        if mode not in ("arm", "thumb") or a % (4 if mode == "arm" else 2):
            raise ValueError(f"{name}: invalid ARM/Thumb root")
        lines.extend(("", "[[entry_point]]", f'addr = 0x{a:08X}',
                      f'mode = "{mode}"', f'name = "observed_{mode}_{a:08x}"'))
    result = "\n".join(lines) + "\n"
    tomllib.loads(result)
    return result


def stage_refresh(source_stage: Path, destination: Path, proofs: list[dict]) -> list[dict]:
    """Create isolated private configs, never mutate the last known good build."""
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {destination}")
    destination.mkdir(parents=True)
    manifest = []
    for proof in proofs:
        name = proof["bank"]
        image = (source_stage / (name + ".bin")).read_bytes()
        config = build_config(proof, image,
                              (source_stage / (name + ".toml")).read_text(encoding="utf-8"))
        shutil.copyfile(source_stage / (name + ".bin"), destination / (name + ".bin"))
        (destination / (name + ".toml")).write_text(config, encoding="utf-8")
        manifest.append({"bank": name, "verified_pages": len(proof["verified_pages"]),
                         "roots": len(proof["roots"]), "sha1": proof["source_sha1"]})
    (destination / "verified-aot-refresh.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def emit_private_banks(staged: Path, output: Path, manifest: list[dict],
                       recompiler: Path, shards: int) -> None:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite generated banks: {output}")
    output.mkdir(parents=True)
    for item in manifest:
        name = item["bank"]
        subprocess.run([
            str(recompiler), "--config", str(staged / (name + ".toml")),
            "--bin", str(staged / (name + ".bin")),
            "--out", str(output), "--bank", name, "--shards", str(shards),
            "--validate-live-bytes",
        ], check=True)
        if not (output / (name + "_dispatch.c")).is_file():
            raise RuntimeError(f"Missing guarded dispatch for {name}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rom", required=True, type=Path)
    ap.add_argument("--coverage", required=True, nargs="+", type=Path)
    ap.add_argument("--shipped-stage", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--overlay-ids", required=True, type=int, nargs="+")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--recompiler", type=Path)
    ap.add_argument("--shards", type=int, default=4)
    args = ap.parse_args()
    if args.emit and (not args.recompiler or args.shards < 1 or args.shards > 64):
        ap.error("--emit requires --recompiler; --shards must be within 1..64")
    proof = selected_overlays(args.rom.read_bytes(),
                              [json.loads(p.read_text(encoding="utf-8")) for p in args.coverage],
                              set(args.overlay_ids))
    manifest = stage_refresh(args.shipped_stage, args.out / "stage", proof)
    if args.emit:
        emit_private_banks(args.out / "stage", args.out / "generated",
                           manifest, args.recompiler, args.shards)
    print(json.dumps({"approved": sorted(set(args.overlay_ids)), "banks": manifest},
                     indent=2))


if __name__ == "__main__":
    main()
