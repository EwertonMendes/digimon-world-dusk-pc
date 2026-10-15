#!/usr/bin/env python3
"""Render true 1D-128 native title prompt cells, not legacy no-stride atlas."""
from __future__ import annotations
import argparse,hashlib,base64,io
from pathlib import Path
from PIL import Image
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource,get_cell_groups
from probe_dusk_sprite_cells import SIZES
from nitro_bg_preview import graphics
from nitro_bg_preview import palette
def composite_cell(chr, pal, ncer, state):
    # Sprite 620 is layered: multiple OAM entries intentionally overlap.
    # Render them with correct 1D 128-byte char names and transparent index
    # zero instead of calling the non-overlap-only localization editor.
    colors=palette(pal)
    depth, raw=graphics(chr)
    if depth!=3:raise ValueError("title composite requires 4bpp NCGR")
    groups, mode=get_cell_groups(ncer)
    objects=[]
    for a0,a1,a2 in groups[state]:
        shape=(a0>>14)&3;sz=(a1>>14)&3
        if shape>2:raise ValueError("invalid OAM shape")
        w,h=SIZES[shape][sz]
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        base=(a2&1023)*(1<<mode)
        bank=(a2>>12)&15
        objects.append((x,y,w,h,base,bank,bool(a1&0x1000),bool(a1&0x2000)))
    minx=min(o[0] for o in objects);miny=min(o[1] for o in objects)
    maxx=max(x+w for x,y,w,h,*_ in objects);maxy=max(y+h for x,y,w,h,*_ in objects)
    if maxx-minx>512 or maxy-miny>256:raise ValueError("unreasonable title cell")
    canvas=Image.new("RGB",(maxx-minx,maxy-miny),(22,26,40))
    px=canvas.load()
    # Lower OAM index draws on top of higher index; reversed traversal is
    # only used in this read-only audit, not as a guessed write mask.
    for x,y,w,h,base,bank,hflip,vflip in reversed(objects):
        for dy in range(h):
            for dx in range(w):
                cx=w-1-dx if hflip else dx
                cy=h-1-dy if vflip else dy
                tid=base+(cy//8)*(w//8)+(cx//8)
                off=tid*32+(cy%8)*4+(cx%8)//2
                if off>=len(raw):raise ValueError("referenced tile missing")
                z=raw[off];idx=(z>>4 if cx&1 else z&15)
                if idx:
                    palette_ix=bank*16+idx
                    if palette_ix>=len(colors):raise ValueError("palette bank missing")
                    px[x+dx-minx,y+dy-miny]=colors[palette_ix][:3]
    return canvas

def run(raw):
    if hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError("wrong exact ROM")
    fs=files(raw)
    for sid in (620,625,626):
        ch=packed_resource(raw,fs,"dat/SPR_CHR.PAK",sid)
        cl=packed_resource(raw,fs,"dat/SPR_CEL.PAK",sid)
        pl=packed_resource(raw,fs,"dat/SPR_PAL.PAK",sid)
        states,mode=get_cell_groups(cl)
        print("TITLE_EXACT_ID",sid,"states",len(states),"mode",mode,"palette",[(i,p[:3]) for i,p in enumerate(palette(pl)[:16])])
        for i in range(min(len(states),8)):
            print("TITLE_EXACT_OAM",sid,i,states[i])
            view=composite_cell(ch,pl,cl,i)
            print("TITLE_EXACT_SIZE",sid,i,view.size)
            pic=view.resize((view.size[0]*3,view.size[1]*3),Image.Resampling.NEAREST)
            buf=io.BytesIO();pic.save(buf,"PNG",optimize=True)
            print("TITLE_EXACT_FRAME",sid,i)
            print("TITLE_EXACT_FRAME64 "+base64.b64encode(buf.getvalue()).decode())
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--rom",type=Path,required=True)
    run(ap.parse_args().rom.read_bytes())
