#!/usr/bin/env python3
"""Bounded NCGR/NCLR/NSCR renderer for read-only Dusk graphics inspection.

All parse offsets and dimensions are verified. Never modifies cartridge.
Useful for finding tile-encoded English UI art before building per-language
NitroFS resource replacements instead of screen overlays.
"""
from __future__ import annotations
import argparse,base64,hashlib,io,struct
from pathlib import Path
from PIL import Image
from probe_dusk_strings import SHA256,files

def u16(b,i):return struct.unpack_from("<H",b,i)[0]
def u32(b,i):return struct.unpack_from("<I",b,i)[0]
def chunk(src,outer,chunkname):
    if len(src)<32 or src[:4]!=outer or u16(src,4)!=0xfeff:
        raise ValueError(f"invalid {outer!r} magic/endian")
    at=u16(src,12)
    for _ in range(u16(src,14)):
        if at+8>len(src):raise ValueError("chunk truncated")
        size=u32(src,at+4)
        if size<8 or at+size>len(src):raise ValueError("chunk size")
        if src[at:at+4]==chunkname:return at,size
        at+=size
    raise ValueError(f"{chunkname!r} not present")
def graphics(src):
    at,length=chunk(src,b"RGCN",b"RAHC")
    depth=u32(src,at+12)
    if depth not in (3,4):raise ValueError("unsupported NCGR color depth")
    datasize=u32(src,at+24)
    begin=at+32
    if not datasize or datasize%(32 if depth==3 else 64) or begin+datasize>at+length:
        raise ValueError("NCGR data size")
    return depth,src[begin:begin+datasize]
def palette(src):
    at,length=chunk(src,b"RLCN",b"TTLP")
    size=u32(src,at+16)
    if size==0 or size>length-24: size=length-24
    begin=at+24
    if size<32 or size%2 or begin+size>at+length:raise ValueError("bad palette allocation")
    return [((x&31)*255//31,((x>>5)&31)*255//31,((x>>10)&31)*255//31,255)
            for x in struct.unpack_from("<"+"H"*(size//2),src,begin)]
def screen(src):
    at,length=chunk(src,b"RCSN",b"NRCS")
    width,height=u16(src,at+8),u16(src,at+10)
    datasize=u32(src,at+16)
    begin=at+20
    if not(8<=width<=2048 and 8<=height<=2048 and width%8==0 and height%8==0):
        raise ValueError("screen dimensions")
    if datasize!=width*height//32 or begin+datasize>at+length:
        raise ValueError("malformed screen map")
    return width,height,struct.unpack_from("<"+"H"*(datasize//2),src,begin)

def render(ncgr,nclr,nscr):
    depth,raw=graphics(ncgr)
    colors=palette(nclr)
    width,height,mapping=screen(nscr)
    tilesize=32 if depth==3 else 64
    ntiles=len(raw)//tilesize
    image=Image.new("RGB",(width,height))
    pixels=image.load()
    for n,item in enumerate(mapping):
        tid=item&0x3ff
        if tid>=ntiles:continue
        hf=bool(item&0x400);vf=bool(item&0x800)
        paloffset=((item>>12)&15)*16 if depth==3 else 0
        tx=n%(width//8)*8;ty=n//(width//8)*8
        for iy in range(8):
            for ix in range(8):
                xx=7-ix if hf else ix
                yy=7-iy if vf else iy
                if depth==3:
                    c=raw[tid*32+yy*4+xx//2]
                    index=paloffset+(c>>4 if xx%2 else c&15)
                else:index=raw[tid*64+yy*8+xx]
                if index<len(colors):pixels[tx+ix,ty+iy]=colors[index][:3]
    return image

def tile_atlas(ncgr,nclr):
    depth,raw=graphics(ncgr)
    colors=palette(nclr)
    tilebytes=32 if depth==3 else 64
    count=len(raw)//tilebytes
    cols=32 if count>=64 else 16
    rows=(count+cols-1)//cols
    if rows==0 or rows>128:raise ValueError("unreasonable tile count")
    im=Image.new("RGB",(cols*8,rows*8))
    pix=im.load()
    for t in range(count):
        palette_index=0
        for y in range(8):
            for x in range(8):
                if depth==3:
                    value=raw[t*32+y*4+x//2]
                    ix=value>>4 if x&1 else value&15
                else:ix=raw[t*64+y*8+x]
                pix[(t%cols)*8+x,(t//cols)*8+y]=colors[palette_index+ix][:3]
    return im

def run(rom,filename,tiles=False):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("ROM identity mismatch")
    fs=files(rom)
    parts=[]
    for suffix in (("NCGR","NCLR") if tiles else ("NCGR","NCLR","NSCR")):
        name=f"{filename}.{suffix}"
        if name not in fs:raise ValueError(f"resource missing: {name}")
        _,lo,hi=fs[name];parts.append(rom[lo:hi])
    im=tile_atlas(*parts) if tiles else render(*parts)
    # A bounded 1:1 PNG; raw encoded payload is diagnostic art from the
    # authenticated owner's ROM and is never checked in or published.
    buf=io.BytesIO()
    im.save(buf,format="PNG",optimize=True)
    print(f"PREVIEW_META {filename} {im.width}x{im.height} png={len(buf.getvalue())}")
    print("PREVIEW64 "+base64.b64encode(buf.getvalue()).decode("ascii"))

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    a.add_argument("--base",required=True,help="NitroFS path excluding .NCGR/.NCLR/.NSCR")
    a.add_argument("--tiles",action="store_true",help="show all tiles in the palette without an NSCR map")
    o=a.parse_args();run(o.rom.read_bytes(),o.base,o.tiles)
