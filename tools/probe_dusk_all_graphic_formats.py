#!/usr/bin/env python3
"""Census all native Dusk sprite graphic formats, including excluded 8bpp.

Read-only; no ROM bytes printed or exported.
"""
import argparse,hashlib
from collections import Counter
from pathlib import Path
from probe_dusk_strings import SHA256,files,u32
from research_dusk_menu_strings import rle_decompress
from nitro_bg_preview import graphics

def run(raw):
    if hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    fs=files(raw)
    _,lo,hi=fs["dat/SPR_CHR.PAK"]
    p=raw[lo:hi];n=u32(p,0)
    kinds=Counter();exceptions=[];non4=[]
    for i in range(n):
        pos=u32(p,4+i*8);length=u32(p,8+i*8)&0x7fffffff
        if not(4+n*8<=pos and pos+length<=len(p)):
            raise ValueError("invalid resource index")
        data=p[pos:pos+length]
        d=rle_decompress(data)
        if d is not None:
            try:
                depth,tiles=graphics(d)
                kinds[f"RLE_{depth}"]+=1
                if depth!=3:non4.append((i,depth,len(d)))
            except Exception:
                kinds["RLE_unknown"]+=1;exceptions.append(i)
        else:
            try:
                depth,tiles=graphics(data)
                kinds[f"RAW_{depth}"]+=1;non4.append((i,depth,len(data)))
            except Exception:
                kinds["unknown"]+=1;exceptions.append(i)
    print("TITLE_GRAPHIC_KIND_COUNT",dict(kinds))
    print("TITLE_NON4_IDS",non4[:130])
    print("TITLE_NON_NITRO_IDS",exceptions[:130])
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",type=Path,required=True)
    run(p.parse_args().rom.read_bytes())
