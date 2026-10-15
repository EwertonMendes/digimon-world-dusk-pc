#!/usr/bin/env python3
"""Create true native DS sprite replacements from per-language declarative text.

Applies edits only inside original NCGR sprite tile graphics loaded from the
authenticated Dusk ROM, preserving palettes/cells, animations and ARM code.
No host SDL overlay or game-font pointer length assumptions. Builds a small
RLE-compressed C++ asset table; original English resources are not included.
"""
from __future__ import annotations
import argparse,base64,hashlib,io,json,zlib
from pathlib import Path
from PIL import Image
from probe_dusk_strings import SHA256,files,u32
from research_dusk_menu_strings import rle_decompress
from nitro_bg_preview import graphics,chunk,palette,tile_atlas
from dusk_sprite_oam_editor import edit_ncer_title
from dusk_sprite_tile_isolation import isolate_selected_cells
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
            cel_raw=read_resource(celpack,i)
            cel_source=rle_decompress(cel_raw)
            if cel_source is None:raise ValueError("invalid compressed NCER cell")
            isolated_chr,isolated_cel=isolate_selected_cells(src,cel_source,spec.get("edits",[]))
            dest=edit_ncer_title(isolated_chr,pal,isolated_cel,spec.get("edits",[]))
            packed=rle_compress(dest)
            rows.append((locale,i,26,zlib.crc32(raw)&0xffffffff,packed))
            if isolated_cel!=cel_source:
                rows.append((locale,i,25,zlib.crc32(cel_raw)&0xffffffff,rle_compress(isolated_cel)))
            if preview:
                print("EDITED_SPRITE",locale,i,"oldbytes",len(raw),"newbytes",len(packed))
                if locale=="pt-BR":
                    from probe_dusk_sprite_cells import get_cell_groups,render_one
                    cells,mode=get_cell_groups(cel_source)
                    translated_cells,_=get_cell_groups(isolated_cel)
                    original_image=render_one(graphics(src)[1],palette(pal),cells[0],mode)
                    translated_image=render_one(graphics(dest)[1],palette(pal),translated_cells[0],mode)
                    if original_image is None or translated_image is None:
                        raise ValueError("could not visualize real OAM cell")
                    w=max(original_image.width,translated_image.width)
                    h=original_image.height+translated_image.height+4
                    side=Image.new("RGB",(w,h),(30,25,46))
                    side.paste(original_image,(0,0))
                    side.paste(translated_image,(0,original_image.height+4))
                    side=side.resize((side.width*4,side.height*4),Image.Resampling.NEAREST)
                    buf=io.BytesIO();side.save(buf,"PNG",optimize=True)
                    print("TRANSLATED_SPRITE_ID",i)
                    print("TRANSLATED_SPRITE64 "+base64.b64encode(buf.getvalue()).decode("ascii"))

    lines=["// Generated from translations/sprites/<locale>/manifest.json by generate_dusk_sprite_header.py."]
    for n,(_,_,_,_,data) in enumerate(rows):
        lines.append(f"inline constexpr std::array<std::uint8_t,{len(data)}> kSpriteData{n}{{")
        for x in range(0,len(data),18):lines.append("    "+",".join(f"0x{k:02x}" for k in data[x:x+18])+",")
        lines.append("};")
    if rows:
        lines.append(f"inline constexpr std::array<SpriteAsset,{len(rows)}> kSprites{{{{")
        for n,(locale,i,pak,crc,data) in enumerate(rows):
            lines.append(f'    SpriteAsset{{"{locale}",{pak},{i},0x{crc:08x}u,kSpriteData{n}.data(),std::uint32_t(kSpriteData{n}.size())}},')
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
