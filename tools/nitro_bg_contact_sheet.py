#!/usr/bin/env python3
"""Inspect themed Nitro graphic atlases as labelled contact sheets, in memory.

Reads only the verified source ROM; exports diagnostic PNG as base64 to the
owner's private Actions log for identifying original menu art/resources.
"""
import argparse,base64,hashlib,io
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from probe_dusk_strings import SHA256,files
from nitro_bg_preview import render,tile_atlas

def contact_sheet(rom,prefix,start=0,count=24):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    fs=files(rom)
    names=sorted(x[:-5] for x in fs if x.startswith(prefix) and x.endswith(".NCGR"))
    names=names[start:start+count]
    if not names:raise ValueError("no NCGR assets matching prefix")
    cellw,cellh,cols=195,142,4
    rows=(len(names)+cols-1)//cols
    sheet=Image.new("RGB",(cellw*cols,cellh*rows),(24,28,45))
    draw=ImageDraw.Draw(sheet)
    for i,stem in enumerate(names):
        base=stem[:-1] if stem.endswith(".") else stem
        res=[]
        for x in ("NCGR","NCLR","NSCR"):
            name=base+"."+x
            res.append(rom[fs[name][1]:fs[name][2]] if name in fs else None)
        if res[0] is None or res[1] is None:continue
        try:
            im=render(*res) if res[2] else tile_atlas(res[0],res[1])
            im.thumbnail((cellw-8,cellh-26),Image.Resampling.NEAREST)
            x=(i%cols)*cellw+4;y=(i//cols)*cellh+4
            sheet.paste(im,(x,y))
            draw.text((x,y+cellh-25),base.rsplit("/",1)[-1],fill=(245,245,245))
        except (ValueError,IndexError) as exc:
            x=(i%cols)*cellw+4;y=(i//cols)*cellh+4
            draw.text((x,y),str(exc)[:22],fill=(255,120,120))
    b=io.BytesIO();sheet.save(b,"PNG",optimize=True)
    print("SHEET",prefix,start,len(names),sheet.size,len(b.getvalue()))
    print("SHEET64",base64.b64encode(b.getvalue()).decode())
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    a.add_argument("--prefix",default="dat/bg/m")
    a.add_argument("--start",type=int,default=0)
    a.add_argument("--count",type=int,default=24)
    args=a.parse_args()
    contact_sheet(args.rom.read_bytes(),args.prefix,args.start,args.count)
