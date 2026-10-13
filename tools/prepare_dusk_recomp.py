#!/usr/bin/env python3
"""Generate private NDSRecomp inputs from the exact verified Dusk USA ROM.

Not a playable port: title runtime/firmware, dynamic entrypoints, and overlays
require further reverse engineering. Never commit generated code or ROM bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tomllib

REFERENCE_SHA256 = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"
UPSTREAM_COMMIT = "3a57236bb23d25dcb4caad7d58d733311062ff5e"


def crc16_header(data: bytes) -> int:
    crc = 0xffff
    for byte in data[:0x15e]:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xa001 if crc & 1 else 0)
    return crc


def checked_slice(raw: bytes, offset: int, size: int) -> bytes:
    if offset < 0 or size <= 0 or offset > len(raw) or size > len(raw) - offset:
        raise ValueError("ROM section outside file")
    return raw[offset:offset+size]


def safe_destination(dst: Path, rom: Path) -> Path:
    dst = dst.resolve()
    if dst == rom.resolve() or dst == Path.cwd().resolve():
        raise ValueError("Refusing unsafe output path")
    for ancestor in (dst, *dst.parents):
        if (ancestor / ".git").exists() and ".private" not in dst.relative_to(ancestor).parts:
            raise ValueError("Output under Git worktree must be in .private")
    return dst


def bank_config(bank: str, cpu: str, image: bytes, base: int, entry: int) -> str:
    if not re.fullmatch(r"[a-z0-9_]+", bank):
        raise ValueError("Bad bank name")
    if cpu not in ("arm7", "arm9") or base % 4 or entry % 4 or not base <= entry < base+len(image):
        raise ValueError("Invalid verified entry")
    lines = [
        "# Auto-generated locally, derived from private ROM. DO NOT COMMIT.",
        "[program]", f'name = "{bank}"', f'id = "{bank}"',
        f'cpu = "{cpu}"', f'isa = "{"armv5te" if cpu == "arm9" else "armv4t"}"',
        f'load_address = 0x{base:08x}', f'size = 0x{len(image):x}',
        f'entry_pc = 0x{entry:08x}', "", "[identity]",
        f'sha1 = "{hashlib.sha1(image).hexdigest()}"', "",
        "[[entry_point]]", f'addr = 0x{entry:08x}',
        'mode = "arm"', 'name = "verified_header_entry"',
    ]
    text = "\n".join(lines) + "\n"
    if tomllib.loads(text)["program"]["size"] != len(image):
        raise ValueError("Bad generated config")
    return text


def prepare(rom: Path, dst: Path, overlays: bool=False) -> dict:
    raw = rom.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError("ROM SHA-256 mismatch: only verified Dusk USA accepted")
    if raw[12:16] != b"A6RE" or crc16_header(raw) != struct.unpack_from("<H",raw,0x15e)[0]:
        raise ValueError("Invalid ROM header")
    dst = safe_destination(dst, rom)
    dst.mkdir(parents=True,exist_ok=True)
    items=[]

    def add(bank: str, cpu: str, image: bytes, base: int, entry: int, verified: bool) -> None:
        config = bank_config(bank,cpu,image,base,entry)
        (dst/(bank+".bin")).write_bytes(image)
        (dst/(bank+".toml")).write_text(config,encoding="utf-8")
        items.append(dict(bank=bank,cpu=cpu,entry=f"0x{entry:08x}",
                          loadAddress=f"0x{base:08x}",size=len(image),
                          sha1=hashlib.sha1(image).hexdigest(),
                          verifiedEntry=verified))

    # ARM9 secure area first 0x800 bytes is not safe to treat as plaintext code.
    a9off,a9entry,a9base,a9size=struct.unpack_from("<4I",raw,0x20)
    if a9entry != a9base+0x800:
        raise ValueError("Unexpected ARM9 protected prefix/entry")
    a9=checked_slice(raw,a9off,a9size)[0x800:]
    add("dusk_arm9_main","arm9",a9,a9base+0x800,a9entry,True)
    a7off,a7entry,a7base,a7size=struct.unpack_from("<4I",raw,0x30)
    add("dusk_arm7_main","arm7",checked_slice(raw,a7off,a7size),a7base,a7entry,True)

    if overlays:
        overlay_offset,overlay_size=struct.unpack_from("<2I",raw,0x50)
        fat_offset,fat_size=struct.unpack_from("<2I",raw,0x48)
        if overlay_size%32 or fat_size%8:
            raise ValueError("Misaligned DS overlay/FAT tables")
        checked_slice(raw,overlay_offset,overlay_size)
        checked_slice(raw,fat_offset,fat_size)
        for i in range(overlay_size//32):
            id_,base,size,bss,init_lo,init_hi,file_id,flags=struct.unpack_from("<8I",raw,overlay_offset+i*32)
            if file_id >= fat_size//8 or flags >> 24:
                raise ValueError("Unsupported/invalid overlay record")
            file_lo,file_hi=struct.unpack_from("<2I",raw,fat_offset+8*file_id)
            image=checked_slice(raw,file_lo,file_hi-file_lo)
            if len(image)!=size:
                raise ValueError("Compressed overlay requires explicit decompression")
            # Overlay header does NOT specify a verified function entrypoint.
            # Stored for analysis only; never emit/dispatch these without tracing.
            add(f"dusk_arm9_ovl{id_:02}","arm9",image,base,base,False)

    report={"status":"private-bank-preparation-not-bootable",
            "upstreamCommit":UPSTREAM_COMMIT,
            "romSHA1":hashlib.sha1(raw).hexdigest(),
            "romSHA256":REFERENCE_SHA256,
            "banks":items,
            "warnings":["ARM9 0x800-byte secure region excluded.",
                        "Main bank entrypoints are verified, but indirect code entries are not.",
                        "Overlay load addresses are NOT verified function entries.",
                        "No ARM9/ARM7 runtime boot or actual gameplay demonstrated."]}
    (dst/"manifest.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report


def normalize_emission(output: Path, name: str) -> None:
    """Adapt one-body NDSRecomp output to the runner's *_00.c glob contract."""
    bare=output/(name+".c")
    indexed=output/(name+"_00.c")
    if bare.is_file() and not indexed.exists():
        bare.rename(indexed)
    if not indexed.is_file() or not (output/(name+"_dispatch.c")).is_file():
        raise ValueError(f"Missing generated body/dispatch for {name}")


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--out",type=Path,default=Path(".private/recomp"))
    p.add_argument("--overlays",action="store_true")
    p.add_argument("--recompiler",type=Path)
    p.add_argument("--emit",action="store_true")
    p.add_argument("--arm9-shards",type=int,default=16,help="ARM9 C body shards (1..99)")
    p.add_argument("--arm7-shards",type=int,default=8,help="ARM7 C body shards (1..99)")
    args=p.parse_args()
    if args.emit and not args.recompiler:
        p.error("--emit requires --recompiler")
    if not (1 <= args.arm9_shards <= 99 and 1 <= args.arm7_shards <= 99):
        p.error("Shard counts must be 1..99")
    try:
        report=prepare(args.rom,args.out,args.overlays)
        print("ROM SHA-1:",report["romSHA1"])
        print("Prepared",len(report["banks"]),"private bank inputs")
        if args.recompiler:
            executable=str(args.recompiler.resolve())
            output=args.out.resolve()
            if args.emit:
                (output/"generated").mkdir(parents=True,exist_ok=True)
            for bank in report["banks"]:
                if not bank["verifiedEntry"]:
                    print("SKIP overlay with unverified entry:",bank["bank"])
                    continue
                name=bank["bank"]
                cmd=[executable,"--config",str(output/(name+".toml")),
                     "--bin",str(output/(name+".bin"))]
                cmd+=["--out",str(output/"generated"),"--bank",name,
                      "--shards",str(args.arm9_shards if bank["cpu"]=="arm9" else args.arm7_shards)] if args.emit else ["--audit"]
                print("Running",name,"in",("emit" if args.emit else "audit"),"mode",flush=True)
                subprocess.run(cmd,check=True)
                if args.emit:
                    normalize_emission(output/"generated",name)
    except (ValueError,OSError,subprocess.CalledProcessError) as e:
        print("ERROR:",e,file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
