#!/usr/bin/env python3
"""Read-only exact-ROM NitroFS / DS graphics-resource inventory.
Never exports ROM data or game images. Output is metadata for research.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path
from probe_dusk_strings import SHA256, files, u16, u32

MAGICS=("RGCN","RLCN","RCSN","RECN","RNAN","RTFN","NARC","BMD0","BTX0","BCA0","BTP0","BCM0","BMA0","BTA0","RCSN","PCKF","PCK2")
EXTS=("NCGR","NCLR","NSCR","NCER","NANR","NFTR","NARC","NSBMD","NSBTX","NSBCA","NSBTP")
def classify(data:bytes):
    if not data:return "empty"
    prefix=data[:4]
    try:
        s=prefix.decode("ascii")
        if s in MAGICS:return "nitro:"+s
    except UnicodeDecodeError:pass
    if len(data)>=4 and data[0]==0x10:
        decompressed=(data[1]|data[2]<<8|data[3]<<16)
        if 32<=decompressed<=16777216:return "lz10"
    if len(data)>=4 and data[0]==0x11:
        decompressed=(data[1]|data[2]<<8|data[3]<<16)
        if 32<=decompressed<=16777216:return "lz11"
    if len(data)>=4 and data[0]==0x30:
        decompressed=(data[1]|data[2]<<8|data[3]<<16)
        if 32<=decompressed<=16777216:return "rle"
    if len(data)>=4 and data[0]==0x24:return "possible-pak"
    return "raw"

def inspect(rom:bytes)->dict:
    if hashlib.sha256(rom).hexdigest()!=SHA256:
        raise ValueError("unexpected owner ROM SHA256")
    catalog=files(rom)
    totals=collections.Counter()
    extension=collections.Counter()
    samples=collections.defaultdict(list)
    candidates=[]
    groups=collections.defaultdict(lambda: {"count":0,"bytes":0})
    for name,(fid,start,end) in catalog.items():
        blob=rom[start:end]
        kind=classify(blob)
        totals[kind]+=1
        ext=name.rsplit(".",1)[-1].upper() if "." in name else "(none)"
        extension[ext]+=1
        first=name.split("/",1)[0]
        groups[first]["count"]+=1
        groups[first]["bytes"]+=len(blob)
        if len(samples[kind])<18:
            samples[kind].append({"id":fid,"name":name,"bytes":len(blob)})
        if any(k in name.lower() for k in
               ("menu","font","bg","sprite","icon","window","shop","obj","screen","digivice","tile","face")):
            if len(candidates)<100:
                candidates.append({"id":fid,"file":name,"bytes":len(blob),"kind":kind})
    return {"rom":SHA256,"count":len(catalog),"kinds":dict(totals.most_common()),
            "extensions":dict(extension.most_common(35)),
            "directories":groups,"examples":samples,"possible_ui_files":candidates}
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    a.add_argument("--out",type=Path)
    o=a.parse_args()
    report=inspect(o.rom.read_bytes())
    if o.out:
        o.out.parent.mkdir(parents=True,exist_ok=True)
        o.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
