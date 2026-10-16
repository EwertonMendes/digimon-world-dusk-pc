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
from dusk_sprite_inplace_editor import replace_labels, assert_frames, extract_cell
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
            edits=spec.get("edits",[])
            if i in (479,480,481,482):
                from probe_dusk_sprite_cells import get_cell_groups
                groups,mode=get_cell_groups(cel_source)
                if mode!=2 or len(groups)!=4 or any(len(g)!=1 for g in groups):
                    raise ValueError("original S-menu OAM mapping / animation layout changed")
                anchors=[(g[0][2]&0x3ff)*(1<<mode) for g in groups]
                print("NITRO_OAM_ACTUAL_MAPPING",i,anchors,"total_original_tiles",len(graphics(src)[1])//32)
                if anchors!=[0,64,128,128] or len(graphics(src)[1])//32 < 192:
                    raise ValueError("original three-frame/four-state OAM layout differs from verified Dusk ROM")
                print("NITROPAINT_VERIFIED_128_BYTE_MAPPING",i,anchors)
            artwork=spec.get("artwork")
            native_title=spec.get("title_prompt")
            if native_title is not None:
                if i!=620 or locale!="pt-BR" or edits or artwork is not None or native_title!="APERTE START":
                    raise ValueError("title localization must be audited sprite 620 in PT-BR")
                from dusk_native_title_prompt import replace_title
                dest,metadata=replace_title(src,pal,cel_source)
                print("VERIFIED_ORIGINAL_TITLE_NATIVE",locale,i,metadata)
                preview_cells=[{"cell":k} for k in range(4)]
            elif artwork is not None:
                if edits or not isinstance(artwork,list):
                    raise ValueError("authored PNG sprites cannot mix with procedural labels")
                from dusk_sprite_authored_art import import_authored_art
                dest=import_authored_art(src,pal,cel_source,artwork,manifest.parent)
                # No font renderer is involved; every authored input PNG is
                # validated against the original NCER/NCLR and caption mask.
                preview_cells=artwork
            else:
                dest=replace_labels(src,pal,cel_source,edits)
                assert_frames(src,pal,cel_source,dest,edits)
                preview_cells=edits
            if i in (479,480,481,482) and artwork is not None:
                from dusk_icon_pixel_guard import assert_icon_pixels_intact
                from probe_dusk_sprite_cells import get_cell_groups
                source_groups,_=get_cell_groups(cel_source)
                # Protect *every* original animated icon at the final NCGR
                # level. A merely valid mask is not evidence that the icon
                # survived overlapping caption tile writes.
                for state in range(len(source_groups)):
                    assert_icon_pixels_intact(
                        extract_cell(src,pal,cel_source,state),
                        extract_cell(dest,pal,cel_source,state),
                        i,state
                    )
                print("VERIFIED_ALL_ORIGINAL_ICON_PIXELS",locale,i,
                      "frames",len(source_groups))
            packed=rle_compress(dest)
            rows.append((locale,i,26,zlib.crc32(raw)&0xffffffff,packed))
            if preview:
                print("EDITED_SPRITE",locale,i,"oldbytes",len(raw),"newbytes",len(packed))
                if locale=="pt-BR":
                    from PIL import ImageDraw
                    # Each action state is validated independently, rather
                    # than previewing a swizzled NCGR texture atlas.
                    images=[]
                    for k in range(min(4,len(preview_cells))):
                        cell=preview_cells[k]["cell"]
                        if native_title is not None:
                            from probe_dusk_title_prompt_exact import composite_cell
                            old_image=composite_cell(src,pal,cel_source,cell)
                            new_image=composite_cell(dest,pal,cel_source,cell)
                        else:
                            old_image=extract_cell(src,pal,cel_source,cell).image
                            new_image=extract_cell(dest,pal,cel_source,cell).image
                        images.append((cell,old_image,new_image))
                    width=max(im.width for _,old,new in images for im in (old,new))
                    height=sum(max(old.height,new.height)+6 for _,old,new in images)
                    canvas=Image.new("RGB",(width*2,height),(24,20,45))
                    pen=ImageDraw.Draw(canvas)
                    y=0
                    for cell,old,new in images:
                        canvas.paste(old,(0,y))
                        canvas.paste(new,(width,y))
                        pen.text((0,y+max(old.height,new.height)),f"animation {cell}",fill="white")
                        y+=max(old.height,new.height)+6
                    canvas=canvas.resize((canvas.width*3,canvas.height*3),Image.Resampling.NEAREST)
                    buf=io.BytesIO();canvas.save(buf,"PNG",optimize=True)
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
