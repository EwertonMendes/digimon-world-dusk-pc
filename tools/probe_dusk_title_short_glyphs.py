#!/usr/bin/env python3
"""Find title command glyph sequences without assuming Dusk's text encoding.

A diagnostic for variable alphabet bases: accepts any consecutive alphabet
offset for PUSH or START in uncompressed ARM9, ARM9 overlays and selected
text banks. This does not modify the game or claim a title text callsite.
"""
from __future__ import annotations
import argparse
import hashlib
import struct
from pathlib import Path
from probe_dusk_strings import SHA256,files,u32

WORDS=("PUSH","START")
HIGH=(0,1,2,0x20,0x80,0xff)

def scan(name:str, data:bytes):
    found=[]
    for word in WORDS:
        nums=[ord(ch)-ord("A") for ch in word]
        for offset in range(256):
            b=bytes(((offset+n)&255) for n in nums)
            for mode,pattern in (("byte",b),("word0",b"".join(bytes([c,0]) for c in b))):
                at=data.find(pattern)
                count=0
                while at!=-1 and count<12:
                    found.append((word,mode,offset,at))
                    count+=1;at=data.find(pattern,at+len(pattern))
    if found:
        # If the two words appear within a few dozen source bytes,
        # that is much stronger evidence than any isolated four-byte hit.
        push=[r for r in found if r[0]=="PUSH"]
        start=[r for r in found if r[0]=="START"]
        for word,mode,offset,at in found[:80]:
            near=any(abs(at-t[3])<160 and mode==t[1] and offset==t[2]
                     for t in (start if word=="PUSH" else push))
            if word=="START" or near:
                print("TITLE_SHORT_GLYPH_HIT",name,word,mode,offset,at,"nearOther",near)
        return len(start),len(push)
    return 0,0

def run(rom:bytes):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("source mismatch")
    a=u32(rom,0x20);n=u32(rom,0x2c)
    result={"ARM9":scan("ARM9",rom[a:a+n])}
    fat=u32(rom,0x48);fat_len=u32(rom,0x4c)
    ov=u32(rom,0x50);ov_len=u32(rom,0x54)
    for i in range(ov_len//32):
        at=ov+i*32
        oid,ram,size,bss,i0,i1,fileid,flags=struct.unpack_from("<8I",rom,at)
        if 8*(fileid+1)>fat_len:raise ValueError("overlay FAT mismatch")
        lo,hi=struct.unpack_from("<II",rom,fat+fileid*8)
        result[f"overlay {oid}"]=scan(f"overlay{oid}",rom[lo:hi])
    f=files(rom)
    for name,(fid,lo,hi) in f.items():
        if name.endswith(("MSG.PAK","SPR_ANM.PAK","MCHR_ANM.PAK")):
            result[name]=scan(name,rom[lo:hi])
    print("TITLE_SHORT_GLYPH_SUMMARY",{k:v for k,v in result.items() if v[0]})

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--rom",type=Path,required=True)
    run(p.parse_args().rom.read_bytes())
