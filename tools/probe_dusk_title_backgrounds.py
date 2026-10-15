#!/usr/bin/env python3
"""Title background atlas for exact Nintendo NSCR/NCGR source discovery."""
from __future__ import annotations
import argparse,base64,hashlib,io
from pathlib import Path
from PIL import Image,ImageDraw
from probe_dusk_strings import files,SHA256
from nitro_bg_preview import render,tile_atlas

CANDIDATES=["dat/bg/t_bg00","dat/bg/t_bg00_m","dat/bg/t_bg01",
"dat/bg/t_bg01_m","dat/bg/t_charaall","dat/bg/t_charaall_m",
"dat/bg/t_menubg","dat/bg/t_menubg01","dat/bg/op_us_dt00",
"dat/bg/t_kk00logo","dat/bg/t_kk01text"]

def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong cartridge")
    f=files(rom)
    for base in CANDIDATES:
        triplet=[base+".NCGR",base+".NCLR",base+".NSCR"]
        if not all(x in f for x in triplet):continue
        blobs=[rom[f[name][1]:f[name][2]] for name in triplet]
        try:
            im=render(*blobs)
            atlas=tile_atlas(*blobs[:2])
        except (ValueError,IndexError) as exc:
            print("TITLE_BG_ERROR",base,str(exc));continue
        if im.width>512 or im.height>512:continue
        canvas=Image.new("RGB",(max(im.width,atlas.width)*2,im.height+atlas.height+32),(14,18,34))
        for y in (0,):
            canvas.paste(im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST),(0,y))
            canvas.paste(atlas.resize((atlas.width*2,atlas.height*2),Image.Resampling.NEAREST),(0,im.height*2+16))
        buf=io.BytesIO();canvas.save(buf,format="PNG",optimize=True)
        print("TITLE_BG_ID",base)
        print("TITLE_BG64 "+base64.b64encode(buf.getvalue()).decode("ascii"))

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    q=a.parse_args()
    run(q.rom.read_bytes())
