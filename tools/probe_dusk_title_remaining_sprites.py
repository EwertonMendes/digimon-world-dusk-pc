#!/usr/bin/env python3
"""Read-only remaining native OAM sprites not included by wide-banner scan."""
from __future__ import annotations
import argparse,hashlib,base64,io,struct
from pathlib import Path
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files,u32
from probe_dusk_sprite_cells import get_cell_groups,SIZES
from research_dusk_menu_strings import rle_decompress
from dusk_sprite_inplace_editor import extract_cell
from nitro_bg_preview import graphics

def dimensions(objects):
    if not objects:return(0,0)
    cells=[]
    for a0,a1,_ in objects:
        shape=(a0>>14)&3;size=(a1>>14)&3
        if shape>2:continue
        w,h=SIZES[shape][size]
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        cells.append((x,y,w,h))
    if not cells:return(0,0)
    return(max(x+w for x,y,w,h in cells)-min(x for x,y,w,h in cells),
           max(y+h for x,y,w,h in cells)-min(y for x,y,w,h in cells))

def entries(pack):
    n=u32(pack,0)
    if n!=1627:raise ValueError("unexpected pack index")
    for i in range(n):
        at=u32(pack,4+i*8);size=u32(pack,8+i*8)&0x7fffffff
        if at<4+8*n or at+size>len(pack):raise ValueError("bad pack offsets")
        yield pack[at:at+size]

def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("source ROM mismatch")
    f=files(rom);packs=[]
    for name in ("dat/SPR_CEL.PAK","dat/SPR_CHR.PAK","dat/SPR_PAL.PAK"):
        _,lo,hi=f[name];packs.append(list(entries(rom[lo:hi])))
    result=[]
    for sid in range(1627):
        try:
            cel=rle_decompress(packs[0][sid])
            if cel is None:continue
            groups,mode=get_cell_groups(cel)
            if not groups or not 0<=mode<=3:continue
            w,h=dimensions(groups[0])
            if 64<=w<=256 and 12<=h<=64:continue
            selection=None
            for c,parts in enumerate(groups[:12]):
                w,h=dimensions(parts)
                if 24<=w<=256 and 12<=h<=96:
                    selection=c;break
            if selection is None:continue
            src=rle_decompress(packs[1][sid]);pal=rle_decompress(packs[2][sid])
            if src is None or pal is None or graphics(src)[0]!=3:continue
            img=extract_cell(src,pal,cel,selection).image
            result.append((sid,selection,img))
        except (IndexError,ValueError,struct.error):
            continue
    print("TITLE_REMAINING_SPRITE_COUNT",len(result))
    for start in range(0,len(result),120):
        subset=result[start:start+120]
        sw,sh,cols=150,85,8
        sheet=Image.new("RGB",(sw*cols,sh*((len(subset)+cols-1)//cols)),(24,20,38))
        draw=ImageDraw.Draw(sheet)
        for q,(sid,cell,img) in enumerate(subset):
            x=q%cols*sw;y=q//cols*sh
            scale=min(3,(sw-6)//img.width,(sh-16)//img.height)
            scale=max(1,scale)
            canvas=img.resize((scale*img.width,scale*img.height),Image.Resampling.NEAREST)
            sheet.paste(canvas,(x+3,y+2))
            draw.text((x+3,y+sh-13),f"ID {sid}/cell {cell}",fill="white")
        buf=io.BytesIO();sheet.save(buf,format="PNG",optimize=True)
        print("TITLE_REMAINING_SHEET",start//120,len(subset))
        print("TITLE_REMAINING_SHEET64 "+base64.b64encode(buf.getvalue()).decode("ascii"))
    print("TITLE_REMAINING_IDS",[sid for sid,_,_ in result])

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    run(a.parse_args().rom.read_bytes())
