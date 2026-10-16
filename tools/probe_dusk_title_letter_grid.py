#!/usr/bin/env python3
"""Decode exact original colored title text glyph runs, without game modifications."""
from __future__ import annotations
import argparse,hashlib
from pathlib import Path
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource,get_cell_groups,SIZES
from nitro_bg_preview import graphics,palette

def original_title_pixels(ncgr:bytes,ncer:bytes):
    depth,raw=graphics(ncgr)
    cells,mode=get_cell_groups(ncer)
    if depth!=3 or mode!=2 or len(cells)!=4:
        raise ValueError("Unexpected source title NCGR/NCER")
    label=cells[0][:4]
    if label!=cells[2][:4] or len(cells[1])!=3:
        raise ValueError("Title text OAM layout changed")
    objects=[]
    for a0,a1,a2 in label:
        shape=(a0>>14)&3;size=(a1>>14)&3
        w,h=SIZES[shape][size]
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        objects.append((x,y,w,h,(a2&1023)*(1<<mode)))
    left=min(o[0] for o in objects)
    top=min(o[1] for o in objects)
    width=max(x+w for x,y,w,h,b in objects)-left
    height=max(y+h for x,y,w,h,b in objects)-top
    if width!=104 or height!=16:
        raise ValueError(f"unexpected label plane {width}x{height}")
    index=[[0]*width for _ in range(height)]
    for x,y,w,h,base in reversed(objects):
        for yy in range(h):
            for xx in range(w):
                tile=base+(yy//8)*(w//8)+xx//8
                at=tile*32+(yy%8)*4+(xx%8)//2
                if at>=len(raw):raise ValueError("label references missing tile")
                value=raw[at]
                idx=value>>4 if xx&1 else value&15
                if idx:index[y+yy-top][x+xx-left]=idx
    return index,objects

def runs(index):
    widths=len(index[0]);active=[]
    for x in range(widths):
        active.append(any(row[x]!=0 for row in index))
    found=[];started=None
    for x,v in enumerate([*active,False]):
        if v and started is None:started=x
        if not v and started is not None:
            found.append((started,x));started=None
    return found

def main(rom:bytes):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    fs=files(rom)
    g=packed_resource(rom,fs,"dat/SPR_CHR.PAK",620)
    c=packed_resource(rom,fs,"dat/SPR_CEL.PAK",620)
    p=packed_resource(rom,fs,"dat/SPR_PAL.PAK",620)
    indices,objects=original_title_pixels(g,c)
    print("TITLE_TEXT_NCLR",[(i,z[:3]) for i,z in enumerate(palette(p)[:16])])
    print("TITLE_TEXT_OBJECTS",objects)
    bounds=runs(indices)
    print("TITLE_TEXT_RUNS",bounds,"count",len(bounds),"char widths",[b-a for a,b in bounds])
    for y,row in enumerate(indices):
        print("TITLE_TEXT_PIXEL_ROW",y,"".join("0123456789abcdef"[v] for v in row))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--rom",type=Path,required=True)
    main(p.parse_args().rom.read_bytes())
