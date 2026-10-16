#!/usr/bin/env python3
"""Visual inspection of exact Tamer NCER tiles; no ROM export."""
import argparse,hashlib,base64,io
from pathlib import Path
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource
from dusk_sprite_inplace_editor import extract_cell
from dusk_icon_pixel_guard import original_icon_pixels
from dusk_original_glyph_atlas import collect_original_glyphs

def inspect(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("unverified cartridge")
    fs=files(rom)
    sid=482
    src=packed_resource(rom,fs,"dat/SPR_CHR.PAK",sid)
    pal=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
    cel=packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid)
    views=[extract_cell(src,pal,cel,cell) for cell in range(4)]
    mask=original_icon_pixels(views,sid)
    glyph=collect_original_glyphs(rom,fs)["T"]
    print("TRAINER_T_SOURCE_GLYPH",glyph.width,sorted(glyph.pixels))
    print("TRAINER_T_GLYPH_MAP")
    for y in range(11):
        print("TROW",y,"".join({13:"g",14:"L",15:"W"}.get(dict(((x,yy),idx) for x,yy,idx in glyph.pixels).get((x,y),0),".") for x in range(glyph.width)))
    names=" .23456789abGLW"
    for c,v in enumerate(views):
        print("TAMER_FRAME",c,"protected",len(mask))
        for y in range(10,47):
            encoded="".join(
                ("#") if (x,y) in mask else
                "0123456789ABCDEF"[v.mapping[(x,y)][2]]
                for x in range(8,64))
            print("TAMER_ROW",c,y,encoded)
    zoom=Image.new("RGB",(64*8,64*4*8),(19,20,30))
    for c,v in enumerate(views):
        zoom.paste(v.image.resize((512,512),Image.Resampling.NEAREST),(0,c*512))
    p=io.BytesIO();zoom.save(p,format="PNG",optimize=True)
    print("TAMER_SOURCE64 "+base64.b64encode(p.getvalue()).decode())

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",required=True,type=Path)
    inspect(ap.parse_args().rom.read_bytes())
