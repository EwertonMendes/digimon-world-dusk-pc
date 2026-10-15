#!/usr/bin/env python3
"""Inspect original huge OAM title/logo cells excluded by menu-width filters."""
from __future__ import annotations
import argparse,base64,hashlib,io,struct
from pathlib import Path
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files,u32
from probe_dusk_sprite_cells import get_cell_groups,SIZES
from research_dusk_menu_strings import rle_decompress
from dusk_sprite_inplace_editor import extract_cell
from nitro_bg_preview import graphics

def dimensions(objects):
    if not objects:return (0,0)
    bounds=[]
    for a0,a1,a2 in objects:
        shape=(a0>>14)&3;sz=(a1>>14)&3
        if shape>=3:continue
        w,h=SIZES[shape][sz]
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        bounds.append((x,y,w,h))
    if not bounds:return(0,0)
    return (max(x+w for x,y,w,h in bounds)-min(x for x,y,w,h in bounds),
            max(y+h for x,y,w,h in bounds)-min(y for x,y,w,h in bounds))

def pack(rom,fs,name):
    _,lo,hi=fs[name];data=rom[lo:hi];n=u32(data,0)
    if n!=1627:raise ValueError("wrong sprite pack")
    result=[]
    for i in range(n):
        at=u32(data,4+i*8);length=u32(data,8+i*8)&0x7fffffff
        if at<4+n*8 or at+length>len(data):raise ValueError("invalid pack")
        result.append(data[at:at+length])
    return result

def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    fs=files(rom)
    cp=pack(rom,fs,"dat/SPR_CEL.PAK")
    gp=pack(rom,fs,"dat/SPR_CHR.PAK")
    pp=pack(rom,fs,"dat/SPR_PAL.PAK")
    matches=[]
    for sid in range(1627):
        try:
            cells=rle_decompress(cp[sid]);chars=rle_decompress(gp[sid]);colors=rle_decompress(pp[sid])
            if not cells or not chars or not colors or graphics(chars)[0]!=3:continue
            groups,mode=get_cell_groups(cells)
            for ci,oam in enumerate(groups[:8]):
                w,h=dimensions(oam)
                if (h>96 or w>192) and 16<=w<=256 and 16<=h<=256:
                    image=extract_cell(chars,colors,cells,ci).image
                    matches.append((sid,ci,image));break
        except (ValueError,IndexError,struct.error):
            continue
    print("TITLE_LARGE_SPRITE_COUNT",len(matches))
    for start in range(0,len(matches),35):
        batch=matches[start:start+35];cols=5;sw=240;sh=160
        atlas=Image.new("RGB",(cols*sw,sh*((len(batch)+cols-1)//cols)),(22,22,36))
        pen=ImageDraw.Draw(atlas)
        for j,(sid,ci,im) in enumerate(batch):
            x=j%cols*sw;y=j//cols*sh
            scale=max(1,min((sw-6)//im.width,(sh-18)//im.height))
            scaled=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
            atlas.paste(scaled,(x+2,y+2))
            pen.text((x+2,y+sh-14),f"{sid}/cell{ci} {im.width}x{im.height}",fill="white")
        buf=io.BytesIO();atlas.save(buf,format="PNG",optimize=True)
        print("TITLE_LARGE_SHEET",start//35)
        print("TITLE_LARGE_SHEET64 "+base64.b64encode(buf.getvalue()).decode())

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--rom",type=Path,required=True)
    o=parser.parse_args()
    run(o.rom.read_bytes())
