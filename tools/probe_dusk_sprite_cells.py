#!/usr/bin/env python3
"""Render Digimon Dusk's native 3-PAK sprite cell graphics for exact UI edits.

Uses Nintendo NCER CEBK OAM cells to un-scramble NCGR char tiles. Logs owner
diagnostics only: no ROM graphics committed or shipped as separate originals.
"""
from __future__ import annotations
import argparse,base64,hashlib,io,struct
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files,u16,u32
from research_dusk_menu_strings import rle_decompress
from nitro_bg_preview import chunk,graphics,palette

SIZES=[
 [(8,8),(16,16),(32,32),(64,64)],
 [(16,8),(32,8),(32,16),(64,32)],
 [(8,16),(8,32),(16,32),(32,64)],
]

def packed_resource(rom,fs,name,i):
    _,a,z=fs[name];raw=rom[a:z]
    n=u32(raw,0)
    if n!=1627 or not 0<=i<n:raise ValueError("unsupported original sprite pack")
    off=u32(raw,4+8*i);length=u32(raw,8+8*i)&0x7fffffff
    if off+length>len(raw):raise ValueError("file record overflow")
    data=rle_decompress(raw[off:off+length])
    if data is None:raise ValueError("invalid Nintendo compressed subresource")
    return data

def get_cell_groups(raw):
    at,size=chunk(raw,b"RECN",b"KBEC")
    n=u16(raw,at+8)
    extended=u16(raw,at+10)
    table_off=u32(raw,at+12)
    mode=u32(raw,at+16)
    if n<1 or n>256 or extended not in(0,1):raise ValueError("invalid cell bank")
    table=at+8+table_off
    entrysize=16 if extended else 8
    objbase=table+n*entrysize
    if table<at+8 or objbase>=at+size:raise ValueError("NCER cell table offset invalid")
    groups=[]
    for i in range(n):
        e=table+i*entrysize
        count=u16(raw,e)
        rel=u32(raw,e+4)
        p=objbase+rel
        if count>96 or p+count*6>at+size:raise ValueError("OAM attributes exceed NCER cell bank")
        attrs=[(u16(raw,p+6*j),u16(raw,p+6*j+2),u16(raw,p+6*j+4)) for j in range(count)]
        groups.append(attrs)
    return groups,mode

def render_one(chars,colors,objects,mode):
    shape_objs=[]
    for a0,a1,a2 in objects:
        shape=(a0>>14)&3;size=(a1>>14)&3
        if shape>=3:continue
        w,h=SIZES[shape][size]
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        tileid=a2&0x3ff
        bank=(a2>>12)&15
        flip_h=bool(a1&0x1000);flip_v=bool(a1&0x2000)
        shape_objs.append((x,y,w,h,tileid,bank,flip_h,flip_v))
    if not shape_objs:return None
    minx=min(o[0] for o in shape_objs);miny=min(o[1] for o in shape_objs)
    maxx=max(o[0]+o[2] for o in shape_objs);maxy=max(o[1]+o[3] for o in shape_objs)
    if maxx-minx>512 or maxy-miny>512:raise ValueError("invalid cell draw region")
    out=Image.new("RGB",(maxx-minx,maxy-miny),(22,26,40))
    pix=out.load()
    for x,y,w,h,tile,bank,hf,vf in shape_objs:
        tw=w//8
        for yy in range(h):
            for xx in range(w):
                cx=(w-1-xx) if hf else xx
                cy=(h-1-yy) if vf else yy
                tid=tile+(cy//8)*tw+(cx//8)
                off=tid*32+(cy%8)*4+(cx%8)//2
                if off>=len(chars):continue
                z=chars[off]
                idx=(z>>4 if cx%2 else z&15)
                if idx==0:continue
                color=colors[(bank*16+idx)%len(colors)]
                tx=x-minx+xx;ty=y-miny+yy
                if 0<=tx<out.width and 0<=ty<out.height:pix[tx,ty]=color[:3]
    return out

def inspect(rom,ids,count=10):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    fs=files(rom)
    for sid in ids:
        a=packed_resource(rom,fs,"dat/SPR_CHR.PAK",sid)
        b=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
        c=packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid)
        depth,chars=graphics(a)
        colors=palette(b)
        cells,mode=get_cell_groups(c)
        print("SPRITE_CELLS",sid,"depth",depth,"n",len(cells),"mode",mode,
              "sizes",[len(x) for x in cells[:20]])
        if depth!=3:continue
        pictures=[]
        for i,objects in enumerate(cells[:count]):
            try:im=render_one(chars,colors,objects,mode)
            except ValueError as exc:
                print("CELL_ERROR",sid,i,str(exc));continue
            if im is None:continue
            im.thumbnail((240,110))
            pictures.append((i,im))
        if not pictures:continue
        canvas=Image.new("RGB",(512,((len(pictures)+1)//2)*145),(30,33,51))
        draw=ImageDraw.Draw(canvas)
        for j,(ci,im) in enumerate(pictures):
            xx=j%2*256;yy=j//2*145
            canvas.paste(im,(xx,yy))
            draw.text((xx,yy+113),f"sprite {sid} / cell {ci}",fill=(255,255,255))
        buf=io.BytesIO();canvas.save(buf,"PNG",optimize=True)
        print("CELL_SHEET",sid,canvas.size)
        print("CELL_SHEET64 "+base64.b64encode(buf.getvalue()).decode())
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",required=True)
    p.add_argument("--ids",default="531")
    p.add_argument("--count",type=int,default=12)
    v=p.parse_args();inspect(open(v.rom,"rb").read(),[int(x) for x in v.ids.split(",")],v.count)
