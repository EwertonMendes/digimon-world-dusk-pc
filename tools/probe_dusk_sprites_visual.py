#!/usr/bin/env python3
"""Find native UI labels among 1627 Nintendo DS sprites in SPR_CHR.PAK.
Read-only owner ROM workflow. Sprite resources are RLE packed Nitro chunks.
"""
import argparse,base64,collections,hashlib,io,json
from pathlib import Path
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files,u32
from research_dusk_menu_strings import rle_decompress
from nitro_bg_preview import tile_atlas,graphics,palette

def sprites(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("Dusk ROM hash mismatch")
    fs=files(rom); packs={}
    for name in ("dat/SPR_CHR.PAK","dat/SPR_PAL.PAK"):
        _,lo,hi=fs[name]; packs[name]=rom[lo:hi]
    cs=packs["dat/SPR_CHR.PAK"];ps=packs["dat/SPR_PAL.PAK"]
    n=u32(cs,0)
    if n!=1627 or u32(ps,0)!=n:raise ValueError("unexpected sprite pack count")
    for i in range(n):
        a=u32(cs,4+i*8);size=u32(cs,8+i*8)&0x7fffffff
        b=u32(ps,4+i*8);psize=u32(ps,8+i*8)&0x7fffffff
        if a+size>len(cs) or b+psize>len(ps):raise ValueError("sprite out of bounds")
        ca=rle_decompress(cs[a:a+size]);pa=rle_decompress(ps[b:b+psize])
        yield i,ca,pa,size

def index(rom):
    groups=collections.defaultdict(list)
    for i,ca,pa,size in sprites(rom):
        if ca is None or pa is None:
            print("INVALID",i,ca is None,pa is None)
            continue
        try:
            depth,raw=graphics(ca)
            colors=palette(pa)
        except (ValueError,IndexError) as exc:
            print("INVALID_NITRO",i,str(exc));continue
        pixels=len(raw)*2 if depth==3 else len(raw)
        groups[f"depth{depth}"].append((i,pixels,size))
    print("INDEX",json.dumps({key:{"count":len(values),"small":values[:6],"large":sorted(values,key=lambda x:-x[1])[:35]} for key,values in groups.items()}))
    print("SIZE_COUNTS",json.dumps(dict(collections.Counter((i[1]//512)*512 for v in groups.values() for i in v).most_common())))

def inspect_ids(rom,ids):
    chosen=set(ids)
    for i,ca,pa,size in sprites(rom):
        if i not in chosen: continue
        if ca is None or pa is None:continue
        im=tile_atlas(ca,pa)
        out=io.BytesIO();im.save(out,"PNG",optimize=True)
        print("SPRITE_DETAIL",i,im.size,len(out.getvalue()))
        print("SPRITE_DETAIL64 "+base64.b64encode(out.getvalue()).decode("ascii"))

def sheet(rom,begin,num,min_pixels,max_pixels):
    picks=[]
    for i,ca,pa,size in sprites(rom):
        if ca is None or pa is None:continue
        try:
            depth,raw=graphics(ca)
            pixel_count=len(raw)*(2 if depth==3 else 1)
            if min_pixels<=pixel_count<=max_pixels:
                picks.append((i,ca,pa,pixel_count))
        except (ValueError,IndexError):continue
    print(f"SELECTION {len(picks)} match pixels {min_pixels}..{max_pixels}")
    chosen=picks[begin:begin+num]
    if not chosen:return
    cellw,cellh,cols=180,124,6
    canvas=Image.new("RGB",(cellw*cols,cellh*((len(chosen)+cols-1)//cols)),(26,28,47))
    draw=ImageDraw.Draw(canvas)
    for j,(i,ca,pa,pixels) in enumerate(chosen):
        im=tile_atlas(ca,pa)
        im.thumbnail((cellw-8,cellh-25),Image.Resampling.NEAREST)
        xx=j%cols*cellw+4;yy=j//cols*cellh+4
        canvas.paste(im,(xx,yy))
        draw.text((xx,yy+cellh-22),f"#{i} {pixels}px",fill=(245,245,245))
    out=io.BytesIO();canvas.save(out,"PNG",optimize=True)
    print("SPRITE_SHEET_INFO",begin,len(chosen),canvas.size)
    print("SPRITE_SHEET64 "+base64.b64encode(out.getvalue()).decode("ascii"))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    ap.add_argument("--index",action="store_true")
    ap.add_argument("--begin",type=int,default=0)
    ap.add_argument("--count",type=int,default=48)
    ap.add_argument("--min-pixels",type=int,default=256)
    ap.add_argument("--max-pixels",type=int,default=16384)
    ap.add_argument("--ids",default="",help="comma-separated sprite IDs to inspect at native resolution")
    a=ap.parse_args();rom=a.rom.read_bytes()
    if a.ids:inspect_ids(rom,[int(i) for i in a.ids.split(",")])
    elif a.index:index(rom)
    else:sheet(rom,a.begin,a.count,a.min_pixels,a.max_pixels)
