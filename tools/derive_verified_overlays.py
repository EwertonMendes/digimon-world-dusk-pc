#!/usr/bin/env python3
"""Prove observed ARM9 overlay roots against exact original ROM and RAM pages.

Overlays sharing RAM addresses MUST emit --validate-live-bytes and retain their
own distinct content-validated dispatch candidates. No speculative roots.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tomllib

from derive_verified_aot import verified_pages

PAGE=4096


def verified_overlay_roots(rom: bytes, coverage: dict) -> list[dict]:
    if coverage.get("rom_sha1") != hashlib.sha1(rom).hexdigest():
        raise ValueError("Coverage ROM identity mismatch")
    table,size=struct.unpack_from("<II",rom,0x50)
    fat,nfat=struct.unpack_from("<II",rom,0x48)
    if size%32 or nfat%8 or table+size>len(rom) or fat+nfat>len(rom):
        raise ValueError("Invalid overlay table/FAT")
    pages=[p for p in verified_pages(coverage) if p["cpu"]==9]
    results=[]
    for i in range(size//32):
        overlay_id,load,size_bytes,bss,init_start,init_end,fid,flags=struct.unpack_from("<8I",rom,table+i*32)
        if fid>=nfat//8:
            raise ValueError("Overlay file id outside FAT")
        first,last=struct.unpack_from("<2I",rom,fat+8*fid)
        if last<=first or last>len(rom):
            raise ValueError("Invalid overlay extent")
        image=rom[first:last]
        if len(image)!=size_bytes:
            continue  # compressed overlay requires separate verified decoding
        matched={p["addr"] for p in pages if load<=p["addr"] and
                 p["addr"]+PAGE<=load+size_bytes and
                 image[p["addr"]-load:p["addr"]-load+PAGE]==p["data"]}
        roots={}
        for seed in coverage.get("entry_points_arm9",[]):
            addr=int(seed["addr"],16)
            mode=seed["mode"]
            hits=int(seed["hits"])
            if (addr & ~(PAGE-1)) not in matched or mode not in ("arm","thumb") or hits<1:
                continue
            if addr%(4 if mode=="arm" else 2):
                continue
            key=(addr,mode)
            if key not in roots or hits>roots[key]["hits"]:
                roots[key]={"addr":f"0x{addr:08X}","mode":mode,"hits":hits}
        if roots:
            results.append({"bank":f"dusk_arm9_ovl{overlay_id:02}",
                            "overlay_id":overlay_id,"load_address":load,
                            "size":size_bytes,
                            "source_sha1":hashlib.sha1(image).hexdigest(),
                            "verified_pages":[f"0x{x:08X}" for x in sorted(matched)],
                            "roots":[entry for _,entry in sorted(roots.items())]})
    return results


def activate_verified_overlays(directory: Path, manifest: dict, results: list[dict]) -> None:
    registry={b["bank"]:b for b in manifest["banks"]}
    changes=[]
    for item in results:
        name=item["bank"]
        if name not in registry:
            raise ValueError(f"Overlay not prepared: {name}")
        meta=registry[name]
        if meta.get("verifiedEntry",False) or meta["cpu"]!="arm9":
            raise ValueError("Overlay was already activated")
        binary=(directory/f"{name}.bin").read_bytes()
        if hashlib.sha1(binary).hexdigest()!=item["source_sha1"] or len(binary)!=item["size"]:
            raise ValueError(f"Overlay image identity changed: {name}")
        cfg=directory/f"{name}.toml"
        original=cfg.read_text(encoding="utf8")
        parsed=tomllib.loads(original)
        if (parsed["program"]["load_address"]!=item["load_address"] or
                parsed["identity"]["sha1"]!=item["source_sha1"]):
            raise ValueError("Overlay program identity mismatch")
        first=item["roots"][0]
        lines=["# Live full-page-verified overlay; mandatory --validate-live-bytes",
               "[program]",f'name = "{name}"',f'id = "{name}"',
               'cpu = "arm9"','isa = "armv5te"',
               f'load_address = 0x{item["load_address"]:08X}',
               f'size = 0x{item["size"]:X}',
               f'entry_pc = {first["addr"]}',
               "[identity]",f'sha1 = "{item["source_sha1"]}"']
        for seed in item["roots"]:
            lines.extend(("", "[[entry_point]]",f'addr = {seed["addr"]}',
                          f'mode = "{seed["mode"]}"',
                          f'name = "observed_{seed["mode"]}_{int(seed["addr"],16):08x}"'))
        updated="\n".join(lines)+"\n"
        tomllib.loads(updated)
        changes.append((cfg,original,updated,meta))
    for cfg,original,updated,meta in changes:
        backup=cfg.with_suffix(".toml.before-overlay-aot")
        if backup.exists():
            raise ValueError(f"Already patched: {cfg}")
        backup.write_text(original,encoding="utf8")
        cfg.write_text(updated,encoding="utf8")
        meta["verifiedEntry"]=True
        meta["certainty"]="verified-original-ROM-full-live-page"
        meta["reason"]="Observed original ROM overlay code; per-function content validation mandatory"
