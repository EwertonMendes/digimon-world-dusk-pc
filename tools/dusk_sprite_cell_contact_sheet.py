#!/usr/bin/env python3
"""Read-only contact sheets of assembled Nintendo DS OAM UI sprites.
The normal tile atlas does not show on-screen text due to OAM tile reuse.
"""
import argparse,base64,hashlib,io
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource,get_cell_groups,render_one
from nitro_bg_preview import graphics,palette

def sheet(rom,lo,hi):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("invalid game ROM")
    fs=files(rom)
    images=[]
    for i in range(lo,hi):
        try:
            a=packed_resource(rom,fs,"dat/SPR_CHR.PAK",i)
            b=packed_resource(rom,fs,"dat/SPR_PAL.PAK",i)
            c=packed_resource(rom,fs,"dat/SPR_CEL.PAK",i)
            depth,raw=graphics(a)
            if depth!=3:continue
            cols=palette(b)
            cells,mode=get_cell_groups(c)
            pic=render_one(raw,cols,cells[0],mode)
            if pic is None or pic.width<10 or pic.height<7:continue
            images.append((i,pic))
        except (IndexError,ValueError):continue
    W,H,C=180,96,6
    result=Image.new("RGB",(C*W,((len(images)+C-1)//C)*H),(30,32,50))
    d=ImageDraw.Draw(result)
    for j,(i,pic) in enumerate(images):
        pic.thumbnail((W-8,H-26),Image.Resampling.NEAREST)
        x=(j%C)*W+4;y=(j//C)*H+4
        result.paste(pic,(x,y))
        d.text((x,y+H-24),f"#{i}",fill=(255,255,255))
    out=io.BytesIO();result.save(out,"PNG",optimize=True)
    print("CELL_CONTACT",lo,hi,"selected",len(images),"image",result.size)
    print("CELL_CONTACT64 "+base64.b64encode(out.getvalue()).decode())
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",required=True)
    p.add_argument("--start",type=int,required=True)
    p.add_argument("--count",type=int,default=75)
    v=p.parse_args();sheet(open(v.rom,"rb").read(),v.start,v.start+v.count)
