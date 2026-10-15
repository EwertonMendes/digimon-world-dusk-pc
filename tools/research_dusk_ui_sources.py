#!/usr/bin/env python3
"""Read-only title-specific menu/shop text source scan for the verified USA ROM.
Only prints short, context-scoped textual matches and source indices.
"""
from pathlib import Path
import argparse
import hashlib
import re
from probe_dusk_strings import files,u16,u32,SHA256
from find_dusk_common_text import decode
PHRASES=(
 "welcome", "equipment", "consumable", "buy", "sell", "quit",
 "money", "digimon", "items", "quests", "digifarm", "tamer info",
 "check digimon progress", "save", "new", "continue", "back",
 "what would you", "would you like", "shop", "digivolve",
 "farm goods", "press", "are you sure"
)
def extract(raw,group,mid):
    _,lo,hi=files(raw)["dat/MSG.PAK"]
    sub=lo+u32(raw,lo+4+8*group)
    nbytes=u32(raw,sub)
    if nbytes%4 or nbytes<=0 or nbytes>4096*4 or (mid+1)*4>nbytes:return ""
    a=u32(raw,sub+mid*4)
    length=u32(raw,lo+8+8*group)&0x7fffffff
    b=u32(raw,sub+(mid+1)*4) if (mid+1)*4<nbytes else length
    if a>=b or b>length:return ""
    return decode([u16(raw,sub+i) for i in range(a,min(b,a+350),2)])
def research(raw):
    assert hashlib.sha256(raw).hexdigest()==SHA256
    allfiles=files(raw)
    _,pak,pend=allfiles["dat/MSG.PAK"]
    for g in range(138):
        sub=pak+u32(raw,pak+4+8*g);nbytes=u32(raw,sub)
        if nbytes%4 or nbytes<=0 or nbytes>4096*4:continue
        for mid in range(nbytes//4):
            s=extract(raw,g,mid)
            if not s:continue
            lower=s.lower()
            keys=[p for p in PHRASES if p in lower]
            if not keys:continue
            if any(p in lower for p in ("equipment","consumable","farm goods",
                                        "what would you","buy sell","digimon progress",
                                        "quests", "tamer info", "money","new continue")):
                print(f"MSG {g:03}:{mid:03} {s[:135]} ")
    # Dusk game includes other resources. Search for compact text signs
    # in each file, rather than assuming MSG.PAK is the only text engine.
    needles=[b"Equipment",b"Quests",b"Tamer",b"Money",b"DigiFarm",b"Check Digimon"]
    for name,(fid,lo,hi) in allfiles.items():
        if hi<=lo:continue
        if fid==23:continue
        segment=raw[lo:hi]
        hits=[n.decode() for n in needles if n in segment or
              b"".join(bytes((c,0)) for c in n) in segment]
        if hits:print(f"RAW {fid} {name} [{', '.join(hits)}] size={hi-lo}")
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    opts=ap.parse_args()
    research(opts.rom.read_bytes())
