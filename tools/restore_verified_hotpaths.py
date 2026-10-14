#!/usr/bin/env python3
"""Restore verified executed Dusk ARM/Thumb hot paths from sanitized evidence.

The metadata contains *no* ROM pages, RAM bytes, saves, or stack samples.
Every entry is accepted only when a complete 4KiB ROM image page has the
SHA-1 observed in the owner's runtime RAM coverage. Native dispatch MUST
be compiled with --validate-live-bytes for RAM overlays and code replacement.

This tool never trusts only an address, never rewrites cartridge game logic,
and never modifies the player's existing save or the prior native build.
"""
from __future__ import annotations

import argparse
import base64
import zlib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib

from prepare_dusk_recomp import normalize_emission

ROM_SHA256 = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"
PAGE = 4096
BANK_RE = re.compile(r"dusk_arm(9|7)_(main|ovl[0-9]{2})\Z")


def recover(stage: Path, evidence: dict, rom: bytes) -> dict:
    if hashlib.sha256(rom).hexdigest() != ROM_SHA256:
        raise ValueError("Wrong cartridge; refusing verified AOT recovery")
    if evidence.get("schema") not in (1, 2) or evidence.get("rom_sha256") != ROM_SHA256:
        raise ValueError("Unsupported evidence or cartridge mismatch")
    items = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    banks = {b["bank"]: b for b in items["banks"]}
    updates = []
    accepted = {}
    copies_by_bank = evidence.get("code_copies", {}) if evidence["schema"] == 2 else {}
    if not isinstance(copies_by_bank, dict):
        raise ValueError("Invalid verified relocated code-copy manifest")
    for name, roots in sorted(evidence["banks"].items()):
        if not BANK_RE.fullmatch(name) or name not in banks:
            raise ValueError(f"Unknown verified bank: {name}")
        meta = banks[name]
        path = stage / (name + ".toml")
        original = path.read_text(encoding="utf-8")
        cfg = tomllib.loads(original)
        image = (stage / (name + ".bin")).read_bytes()
        base = int(cfg["program"]["load_address"])
        cpu = int(cfg["program"]["cpu"][-1])
        if meta["cpu"] != f"arm{cpu}" or hashlib.sha1(image).hexdigest() != cfg["identity"]["sha1"]:
            raise ValueError(f"Stage bank identity mismatch: {name}")
        if int(cfg["program"]["size"]) != len(image):
            raise ValueError(f"Stage bank size mismatch: {name}")
        if not isinstance(roots, list) or not roots or len(roots) > 3072:
            raise ValueError(f"Unbounded or absent AOT evidence: {name}")
        # Copied ARM7 executable pages use original-ROM bytes at a distinct
        # runtime PC. Every 4KiB page of every mapping MUST match the
        # original image by SHA-1, not just the intended seed instruction.
        code_copies = []
        for raw_copy in copies_by_bank.get(name, []):
            if cpu != 7 or name != "dusk_arm7_main":
                raise ValueError("Only verified ARM7 main relocation is allowed")
            run_start = int(raw_copy["runtime_start"], 16)
            source_start = int(raw_copy["source_start"], 16)
            length = int(raw_copy["size"])
            hashes = raw_copy["pages"]
            source_offset = source_start - base
            if (run_start % PAGE or length < 2 * PAGE or
                length % PAGE or len(hashes) != length // PAGE or
                source_offset < 0 or source_offset + length > len(image)):
                raise ValueError("Invalid ARM7 copied-code geometry")
            if any(not re.fullmatch("[a-f0-9]{40}", h) for h in hashes):
                raise ValueError("Malformed relocated page digest")
            for ix, digest in enumerate(hashes):
                off = source_offset + ix * PAGE
                if hashlib.sha1(image[off:off + PAGE]).hexdigest() != digest:
                    raise ValueError("ARM7 code-copy page differs from verified ROM")
            for prev in code_copies:
                if max(run_start, prev["runtime_start"]) < min(run_start + length, prev["runtime_start"] + prev["size"]):
                    raise ValueError("Overlapping ARM7 runtime relocations")
            code_copies.append({"runtime_start":run_start,
                                "source_start":source_start, "size":length})

        valid = []
        seen = set()
        for root in roots:
            pc = int(root["pc"], 16)
            mode = root["mode"]
            digest = root["page_sha1"]
            width = 4 if mode == "arm" else 2 if mode == "thumb" else 0
            if not width or pc % width or len(digest) != 40 or not re.fullmatch("[a-f0-9]{40}", digest):
                raise ValueError(f"Invalid root mode/identity: {name} {root}")
            if (pc, mode) in seen:
                raise ValueError(f"Duplicate AOT root: {name} {pc:#x}")
            seen.add((pc, mode))
            page = pc & ~(PAGE - 1)
            if "source_page_offset" in root:
                # The source offset is an exact 4KiB-page mapping, not a
                # guessed relocated symbol, and must belong to an accepted
                # all-pages-verified code_copy interval.
                if cpu != 7 or name != "dusk_arm7_main":
                    raise ValueError("Only ARM7 relocations can use source offsets")
                at = int(root["source_page_offset"], 16)
                mappings = [
                    c for c in code_copies
                    if c["runtime_start"] <= page < c["runtime_start"] + c["size"] and
                    at == c["source_start"] - base + page - c["runtime_start"]
                ]
                if len(mappings) != 1:
                    raise ValueError(f"Unproved ARM7 runtime/source mapping: {pc:#x}")
            else:
                at = page - base
            # Full 4096-byte observed RAM page must match exact cartridge
            # image; stale overlay generations and 2-byte-only matches fail.
            if at < 0 or at + PAGE > len(image):
                raise ValueError(f"Uncovered page for AOT root: {name} {pc:#x}")
            if hashlib.sha1(image[at:at + PAGE]).hexdigest() != digest:
                raise ValueError(f"Captured RAM generation disagrees with ROM: {name} {pc:#x}")
            valid.append((pc, mode))
        # Overlay header "base" was only a placeholder, not a verified entry;
        # replace it using the actual byte-verified observed execution roots.
        entries = [(int(e["addr"]), e["mode"]) for e in cfg.get("entry_point", [])
                   ] if name.endswith("_main") else []
        for root in valid:
            if root not in entries:
                entries.append(root)
        if not entries:
            raise ValueError(f"Bank has no proved seeds: {name}")
        program = cfg["program"]
        output = [
            "# Owner session metadata only; bank bytes must match the original ROM.",
            "# Runtime generated code MUST use --validate-live-bytes.",
            "[program]",
            f'name = "{name}"', f'id = "{name}"',
            f'cpu = "arm{cpu}"',
            f'isa = "{program["isa"]}"',
            f'load_address = 0x{base:08X}',
            f'size = 0x{len(image):X}',
            f'entry_pc = 0x{entries[0][0]:08X}',
            "",
            "[identity]",
            f'sha1 = "{hashlib.sha1(image).hexdigest()}"',
        ]
        if name.endswith("_main"):
            # Retain any validated code-copy mappings from the main-bank
            # stage; do not silently discard ARM7 copy protection.
            for copy in [*cfg.get("code_copy", []), *code_copies]:
                output.extend(["", "[[code_copy]]"])
                for key, val in copy.items():
                    output.append(f"{key} = " + (f'0x{val:X}' if isinstance(val, int) else json.dumps(val)))
        for pc, mode in entries:
            output += ["", "[[entry_point]]", f'addr = 0x{pc:08X}',
                       f'mode = "{mode}"', f'name = "verified_{mode}_{pc:08x}"']
        assembled = "\n".join(output) + "\n"
        parsed = tomllib.loads(assembled)
        if len(parsed.get("entry_point", [])) != len(entries):
            raise ValueError(f"Unable to parse verified seeds: {name}")
        updates.append((path, assembled))
        accepted[name] = len(valid)
    # No partial mutations: ALL evidence and bank checks above must pass.
    for path, data in updates:
        path.write_text(data, encoding="utf-8")
    for bank in banks.values():
        if bank["bank"] in accepted:
            bank["verifiedEntry"] = True
            bank["certainty"] = "ROM page SHA1 equals owner-observed runtime page"
    (stage / "manifest.json").write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
    return accepted


def emit(stage: Path, recompiler: Path, arm9_shards: int = 16, arm7_shards: int = 8) -> dict:
    state = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    generated = stage / "generated"
    generated.mkdir(exist_ok=False)
    built = {}
    for bank in state["banks"]:
        if not bank.get("verifiedEntry"):
            continue
        name = bank["bank"]
        shards = arm9_shards if bank["cpu"] == "arm9" else arm7_shards
        cmd = [str(recompiler.resolve()), "--config", str((stage / (name + ".toml")).resolve()),
               "--bin", str((stage / (name + ".bin")).resolve()),
               "--out", str(generated.resolve()), "--bank", name,
               "--shards", str(shards), "--validate-live-bytes"]
        subprocess.run(cmd, check=True)
        normalize_emission(generated, name)
        built[name] = len(tomllib.loads((stage / (name + ".toml")).read_text())["entry_point"])
    return built



def load_evidence(path: Path) -> dict:
    data = path.read_bytes()
    if path.suffix != ".b64":
        return json.loads(data)
    if len(data) > 500_000:
        raise ValueError("Unbounded owner evidence")
    # Small, byte-free diagnostic metadata, never ROM, screenshots or RAM.
    decoded = base64.b64decode(data, validate=False)
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(decoded, 3 * 1024 * 1024)
    if not decompressor.eof or decompressor.unconsumed_tail:
        raise ValueError("Oversized/truncated compressed evidence")
    metadata = json.loads(raw)
    if metadata.get("s") != 3:
        raise ValueError("Unsupported compact proof schema")
    hashes = metadata["h"]
    if not isinstance(hashes, list) or len(hashes) > 4096 or any(
        not isinstance(h, str) or not re.fullmatch("[0-9a-f]{40}", h)
        for h in hashes
    ):
        raise ValueError("Invalid code-page checksum dictionary")
    def digest(index: int) -> str:
        if not isinstance(index, int) or not 0 <= index < len(hashes):
            raise ValueError("Unknown code-page checksum")
        return hashes[index]
    banks = {}
    if not isinstance(metadata["b"], dict) or len(metadata["b"]) > 32:
        raise ValueError("Invalid bank manifest")
    for bank, entries in metadata["b"].items():
        if not BANK_RE.fullmatch(bank) or len(entries) > 3072:
            raise ValueError("Invalid bank/root count")
        roots = []
        for entry in entries:
            if not isinstance(entry, list) or len(entry) not in (3, 4):
                raise ValueError("Invalid execution-root tuple")
            pc, mode, sha_index = entry[:3]
            if not isinstance(pc, int) or pc < 0 or pc > 0xFFFFFFFF or mode not in (0, 1):
                raise ValueError("Invalid executed address/mode")
            root = {"pc": f"0x{pc:08X}", "mode": "thumb" if mode else "arm",
                    "page_sha1": digest(sha_index)}
            if len(entry) == 4:
                if not isinstance(entry[3], int) or entry[3] < 0:
                    raise ValueError("Invalid code-copy source offset")
                root["source_page_offset"] = f"0x{entry[3]:X}"
            roots.append(root)
        banks[bank] = roots
    copies = {}
    for bank, mappings in metadata.get("c", {}).items():
        if bank != "dusk_arm7_main" or len(mappings) > 64:
            raise ValueError("Unsupported relocated copied-code bank")
        copies[bank] = []
        for mapping in mappings:
            if not isinstance(mapping, list) or len(mapping) != 4:
                raise ValueError("Invalid code-copy geometry tuple")
            run, source, length, page_hashes = mapping
            if any(not isinstance(x, int) or x < 0 for x in (run, source, length)):
                raise ValueError("Invalid code-copy location")
            copies[bank].append({
                "runtime_start": f"0x{run:08X}",
                "source_start": f"0x{source:08X}",
                "size": length,
                "pages": [digest(x) for x in page_hashes],
            })
    return {"schema": 2, "rom_sha256": ROM_SHA256,
            "banks": banks, "code_copies": copies}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--recompiler", type=Path, required=True)
    args = p.parse_args()
    report = recover(args.stage, load_evidence(args.evidence), args.rom.read_bytes())
    print("Verified root entries:", report, flush=True)
    outputs = emit(args.stage, args.recompiler)
    overlays = [n for n in outputs if "_ovl" in n]
    if len(overlays) < 6:
        raise SystemExit(f"Native recovery incomplete: only {len(overlays)} overlay banks compiled")
    print("Native byte-guarded banks:", outputs, flush=True)


if __name__ == "__main__":
    main()
