#!/usr/bin/env python3
"""Read-only 8-bpp NCGR/NCER sprite atlas, previously invisible to title search.

8-bpp OAM must map characterName units in bytes, not with 4bpp tile math.
This audit never writes original game assets; it emits bounded preview sheets
to the ephemeral owner-only CI log.
"""
from __future__ import annotations
import argparse,hashlib,io,base64
from pathlib import Path
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource,get_cell_groups,SIZES
from nitro_bg_preview import graphics,palette

def render_8(ncgr,nclr,ncer,state):
    depth,raw=graphics(ncgr)
    if depth!=4:raise ValueError("not 8bpp")
    colors=palette(nclr)
    cells,mode=get_cell_groups(ncer)
    if not (0<=mode<=3 and state<len(cells)):raise ValueError("invalid mode/cell")
    objects=[]
    for a0,a1,a2 in cells[state]:
        shape=(a0>>14)&3;size=(a1>>14)&3
        if shape>=3:continue
        w,h=SIZES[shape][size]
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        byte_start=(a2&0x3ff)*32*(1<<mode)
        if byte_start%64:raise ValueError("8bpp OAM base not aligned to tile")
        objects.append((x,y,w,h,byte_start//64,bool(a1&0x1000),bool(a1&0x2000)))
    if not objects:raise ValueError("empty 8bpp cell")
    minx=min(x for x,*_ in objects);miny=min(y for x,y,*_ in objects)
    w=max(x+ow for x,y,ow,oh,*_ in objects)-minx
    h=max(y+oh for x,y,ow,oh,*_ in objects)-miny
    if not (1<=w<=256 and 1<=h<=256):raise ValueError("unreasonable dimensions")
    image=Image.new("RGB",(w,h),(22,26,40))
    px=image.load()
    for x,y,ow,oh,base,flipx,flipy in objects:
        for dy in range(oh):
            for dx in range(ow):
                cx=ow-1-dx if flipx else dx
                cy=oh-1-dy if flipy else dy
                tile=base+(cy//8)*(ow//8)+(cx//8)
                offset=tile*64+(cy%8)*8+(cx%8)
                if offset>=len(raw):raise ValueError("sprite 8bpp missing tile")
                color=raw[offset]
                if color and color<len(colors):
                    px[x+dx-minx,y+dy-miny]=colors[color][:3]
    return image

def main(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("original ROM required")
    fs=files(rom);found=[]
    for sid in range(1627):
        try:
            chr=packed_resource(rom,fs,"dat/SPR_CHR.PAK",sid)
            depth,_=graphics(chr)
            if depth!=4:continue
            pal=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
            cel=packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid)
            im=render_8(chr,pal,cel,0)
            found.append((sid,im))
        except (ValueError,IndexError):
            continue
    print("TITLE_8BPP_SPRITES",len(found),[i for i,_ in found])
    for start in range(0,len(found),80):
        batch=found[start:start+80]
        sw,sh,cols=170,96,7
        atlas=Image.new("RGB",(sw*cols,sh*((len(batch)+cols-1)//cols)),(22,22,36))
        pen=ImageDraw.Draw(atlas)
        for j,(sid,im) in enumerate(batch):
            x=j%cols*sw;y=j//cols*sh
            scale=max(1,min(3,(sw-6)//im.width,(sh-18)//im.height))
            view=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
            atlas.paste(view,(x+2,y+2))
            pen.text((x+2,y+sh-15),f"ID {sid} {im.width}x{im.height}",fill="white")
        buffer=io.BytesIO();atlas.save(buffer,"PNG",optimize=True)
        print("TITLE_8BPP_SHEET",start//80)
        print("TITLE_8BPP_SHEET64 "+base64.b64encode(buffer.getvalue()).decode())

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--rom",type=Path,required=True)
    main(p.parse_args().rom.read_bytes())
