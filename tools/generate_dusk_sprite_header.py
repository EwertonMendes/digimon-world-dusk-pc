#!/usr/bin/env python3
"""Create true native DS sprite replacements from per-language declarative text.

Applies edits only inside original NCGR sprite tile graphics loaded from the
authenticated Dusk ROM, preserving palettes/cells, animations and ARM code.
No host SDL overlay or game-font pointer length assumptions. Builds a small
RLE-compressed C++ asset table; original English resources are not included.
"""
from __future__ import annotations
import argparse,base64,collections,hashlib,io,json,zlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from probe_dusk_strings import SHA256,files,u32
from research_dusk_menu_strings import rle_decompress
from nitro_bg_preview import graphics,chunk,palette,tile_atlas
from dusk_sprite_oam_editor import edit_ncer_title
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"tools/native-ui/dusk_sprite_catalog.generated.hpp"

def rle_compress(blob:bytes)->bytes:
    if not 0<len(blob)<=0xffffff:raise ValueError("bad decoded resource size")
    out=bytearray([0x30,len(blob)&255,(len(blob)>>8)&255,(len(blob)>>16)&255])
    p=0
    while p<len(blob):
        run=1
        while p+run<len(blob) and run<130 and blob[p+run]==blob[p]:run+=1
        if run>=3:
            out.extend((0x80+(run-3),blob[p]));p+=run
        else:
            start=p;p+=run
            while p<len(blob) and p-start<128:
                nxt=1
                while p+nxt<len(blob) and nxt<3 and blob[p+nxt]==blob[p]:nxt+=1
                if nxt>=3:break
                p+=1
            out.append(p-start-1);out.extend(blob[start:p])
    while len(out)%4:out.append(0xff)
    if rle_decompress(out)!=blob:raise ValueError("RLE roundtrip failed")
    return bytes(out)

def read_resource(pack:bytes,index:int)->bytes:
    if not 0<=index<u32(pack,0):raise ValueError("bad sprite ID")
    off=u32(pack,4+8*index);size=u32(pack,8+8*index)&0x7fffffff
    if off<4+8*u32(pack,0) or size<4 or off+size>len(pack):raise ValueError("invalid sprite bounds")
    return pack[off:off+size]

def pixels(src:bytearray):
    depth,raw=graphics(src)
    if depth!=3:raise ValueError("only palette-indexed 4bpp NCGR sprite labels supported")
    tilecount=len(raw)//32
    cols=32 if tilecount>=64 else 16
    width,height=cols*8,((tilecount+cols-1)//cols)*8
    grid=Image.new("P",(width,height))
    array=grid.load()
    for tile in range(tilecount):
        for y in range(8):
            for x in range(8):
                b=raw[tile*32+y*4+x//2]
                array[(tile%cols)*8+x,(tile//cols)*8+y]=(b>>4)&15 if x%2 else b&15
    return grid,depth

def encode_pixels(img:Image.Image,old:bytearray):
    at,_=chunk(old,b"RGCN",b"RAHC")
    base=at+32
    width,height=img.size
    cols=width//8
    pixels=img.load()
    _,source_chars=graphics(old)
    for tile in range(len(source_chars)//32):
        for y in range(8):
            for b in range(4):
                a=pixels[tile%cols*8+b*2,tile//cols*8+y]
                z=pixels[tile%cols*8+b*2+1,tile//cols*8+y]
                if a>15 or z>15:raise ValueError("palette index out of range")
                old[base+tile*32+y*4+b]=a|(z<<4)
    return bytes(old)

def modify(original_ncgr,original_nclr,edits):
    ncgr=bytearray(original_ncgr)
    im,depth=pixels(ncgr)
    colors=palette(original_nclr)
    if len(colors)<16:raise ValueError("palette missing colors")
    freq=collections.Counter(im.getdata())
    foreground=max(range(1,16),key=lambda i:sum(colors[i][:3]))
    dst=im.load()
    mask_all=set()
    for item in edits:
        rect=item.get("rect")
        text=item.get("text")
        if not isinstance(rect,list) or len(rect)!=4 or not isinstance(text,str):
            raise ValueError("invalid sprite edit schema")
        x,y,w,h=rect
        if any(not isinstance(z,int) for z in rect) or not(0<=x<im.width and 0<=y<im.height and
             1<=w<=im.width-x and 6<=h<=im.height-y):
            raise ValueError(f"invalid sprite rect: {rect}")
        if not text or any(ord(c)<32 or ord(c)>126 for c in text):
            raise ValueError("only verified ASCII UI sprite glyphs supported in this pack")
        if any((xx,yy) in mask_all for xx in range(x,x+w) for yy in range(y,y+h)):
            raise ValueError("two sprite translations have overlapping destinations")
        for xx in range(x,x+w):
            for yy in range(y,y+h):
                mask_all.add((xx,yy))
        bg=item.get("background",0)
        if not isinstance(bg,int) or not 0<=bg<16:raise ValueError("invalid BG index")
        for xx in range(x,x+w):
            for yy in range(y,y+h):dst[xx,yy]=bg
        font=None; bounds=None
        for size in range(min(h+4,13),5,-1):
            sample=ImageFont.load_default(size=size)
            box=ImageDraw.Draw(Image.new("1",(1,1))).textbbox((0,0),text,font=sample)
            if box[2]-box[0]<=w-2 and box[3]-box[1]<=h:
                font=sample;bounds=box;break
        if font is None:raise ValueError(f"unrenderable text {text!r} for {rect}")
        glyph=Image.new("1",(w,h),0)
        draw=ImageDraw.Draw(glyph)
        left=max(0,(w-(bounds[2]-bounds[0]))//2-bounds[0])
        top=max(0,(h-(bounds[3]-bounds[1]))//2-bounds[1])
        draw.text((left,top),text,font=font,fill=1)
        pix=glyph.load()
        for xx in range(w):
            for yy in range(h):
                if pix[xx,yy]:dst[x+xx,y+yy]=foreground
    new=encode_pixels(im,ncgr)
    if new==original_ncgr:raise ValueError("sprite edit made no changes")
    return new

def generate(rom:bytes,preview=False)->str:
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong source ROM")
    f=files(rom)
    def load(name):
        _,lo,hi=f[name];return rom[lo:hi]
    chrpack=load("dat/SPR_CHR.PAK");palpack=load("dat/SPR_PAL.PAK");celpack=load("dat/SPR_CEL.PAK")
    if u32(chrpack,0)!=1627 or u32(palpack,0)!=1627:raise ValueError("original sprite pack layout changed")
    rows=[]
    for manifest in sorted((ROOT/"translations/sprites").glob("*/manifest.json")):
        obj=json.loads(manifest.read_text("utf-8"))
        locale=manifest.parent.name
        if obj.get("schema")!=1 or obj.get("language")!=locale:raise ValueError("invalid sprite locale manifest")
        for spec in obj.get("sprites",[]):
            i=spec.get("id")
            if not isinstance(i,int) or not 0<=i<1627:raise ValueError("invalid sprite index")
            if any(v[0]==locale and v[1]==i for v in rows):raise ValueError("duplicate sprite translated twice")
            raw=read_resource(chrpack,i)
            src=rle_decompress(raw)
            pal=rle_decompress(read_resource(palpack,i))
            if src is None or pal is None:raise ValueError("bad compressed Nitro sprite data")
            if hashlib.sha256(src).hexdigest()!=spec.get("source_sha256"):
                raise ValueError(f"sprite {i} source SHA-256 mismatch")
            dest=edit_ncer_title(src,pal,rle_decompress(read_resource(celpack,i)),spec.get("edits",[]))
            packed=rle_compress(dest)
            rows.append((locale,i,zlib.crc32(raw)&0xffffffff,packed))
            if preview:
                print("EDITED_SPRITE",locale,i,"oldbytes",len(raw),"newbytes",len(packed))
                if locale=="pt-BR":
                    a=tile_atlas(src,pal);z=tile_atlas(dest,pal)
                    side=Image.new("RGB",(a.width,a.height*2+4),(30,25,46))
                    side.paste(a,(0,0));side.paste(z,(0,a.height+4))
                    side=side.resize((side.width*4,side.height*4),Image.Resampling.NEAREST)
                    buf=io.BytesIO();side.save(buf,"PNG",optimize=True)
                    print("TRANSLATED_SPRITE_ID",i)
                    print("TRANSLATED_SPRITE64 "+base64.b64encode(buf.getvalue()).decode("ascii"))
    lines=["// Generated from translations/sprites/<locale>/manifest.json by generate_dusk_sprite_header.py."]
    for n,(_,_,_,data) in enumerate(rows):
        lines.append(f"inline constexpr std::array<std::uint8_t,{len(data)}> kSpriteData{n}{{")
        for x in range(0,len(data),18):lines.append("    "+",".join(f"0x{k:02x}" for k in data[x:x+18])+",")
        lines.append("};")
    if rows:
        lines.append(f"inline constexpr std::array<SpriteAsset,{len(rows)}> kSprites{{{{")
        for n,(locale,i,crc,data) in enumerate(rows):
            lines.append(f'    SpriteAsset{{"{locale}",{i},0x{crc:08x}u,kSpriteData{n}.data(),std::uint32_t(kSpriteData{n}.size())}},')
        lines.append("}};")
    else:lines.append("inline constexpr std::array<SpriteAsset,0> kSprites{};")
    lines.append("")
    return "\n".join(lines)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--check",action="store_true")
    a=p.parse_args()
    content=generate(a.rom.read_bytes(),preview=True)
    if a.check:
        if not DEST.exists() or content!=DEST.read_text("utf-8"):raise SystemExit("sprite catalog stale")
    else:
        DEST.write_text(content,"utf-8")
        print("Generated sprite translation resources:",len(content),"bytes")
