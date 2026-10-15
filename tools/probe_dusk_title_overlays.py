#!/usr/bin/env python3
"""Locate title prompt in authenticated ARM9 overlays and custom DS fonts.

Reads binary overlays through cartridge FAT and ARM9 overlay table, not through
NitroFS filenames; old probes missed this code/data class. Metadata only.
"""
from __future__ import annotations
import argparse,hashlib,struct
from pathlib import Path
from probe_dusk_strings import SHA256,u32
from research_dusk_menu_strings import enc,rle_decompress

SEARCH=("PUSH START","Push Start","PRESS START","Press Start",
        "PUSH","Push","START","Start","PRESS","Press","PUSHSTART")

def scan(label,data,limit=80):
    entries=[]
    for needle in SEARCH:
        patterns={
          "ascii":needle.encode("ascii"),
          "utf16le":needle.encode("utf-16-le"),
          "game16":enc(needle),
          "shift-jis":needle.encode("shift_jis")
        }
        for kind,p in patterns.items():
            if not p:continue
            offset=data.find(p)
            count=0
            while offset!=-1 and count<8:
                entries.append((needle,kind,offset))
                offset=data.find(p,offset+len(p))
                count+=1
    for needle,kind,at in entries[:limit]:
        around=data[max(0,at-12):min(len(data),at+len(needle)*2+12)]
        print("TITLE_OVERLAY_MATCH",label,repr(needle),kind,at,around.hex())
    return len(entries)

def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong source ROM")
    fat=u32(rom,0x48);fat_len=u32(rom,0x4c)
    arm9_overlays=u32(rom,0x50);ov_len=u32(rom,0x54)
    count=ov_len//32
    if ov_len%32 or count>4096:raise ValueError("invalid ARM9 overlay table")
    print("TITLE_OVERLAY_TABLE",arm9_overlays,ov_len,count)
    hits=0
    for i in range(count):
        at=arm9_overlays+32*i
        if at+32>len(rom):raise ValueError("overlay table overflow")
        over_id,ram,size,bss,init0,init1,fileid,flags=struct.unpack_from("<8I",rom,at)
        if fileid*8+8>fat_len:raise ValueError("overlay file ID invalid")
        lo,hi=struct.unpack_from("<II",rom,fat+8*fileid)
        if hi<lo or hi>len(rom):raise ValueError("overlay bounds overflow")
        data=rom[lo:hi]
        if i<15:print("TITLE_OVERLAY_HEADER",i,over_id,fileid,len(data),size,hex(ram),hex(flags),data[:12].hex())
        hits+=scan(f"ARM9-over-{over_id}-fat{fileid}",data)
        # Some game resources embed Nintendo RLE in overlay data.
        if len(data)>12 and data[0]==0x30:
            dec=rle_decompress(data)
            if dec:hits+=scan(f"ARM9-over-{over_id}-RLE",dec)
    print("TITLE_OVERLAY_TEXT_MATCHES",hits)
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    run(a.parse_args().rom.read_bytes())
