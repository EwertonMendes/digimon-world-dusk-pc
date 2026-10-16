#!/usr/bin/env python3
"""Prototype hand-authored bitmap glyph artwork on original Nintendo DS sprites.

No Pillow desktop fonts, antialiasing, generic OAM address guesses, or NCER edits.
Uses the authenticated ROM and native NCLR only to draw review previews. The
output remains an experimental proof until the owner approves gameplay images.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw
from probe_dusk_strings import SHA256, files, u32
from research_dusk_menu_strings import rle_decompress
from dusk_sprite_inplace_editor import extract_cell
from probe_dusk_sprite_cells import packed_resource
from nitro_bg_preview import palette
from dusk_original_glyph_atlas import collect_original_glyphs, layout_native_word, layout_trainer_one_line
from dusk_icon_pixel_guard import original_icon_pixels

ROOT = Path(__file__).resolve().parents[1]

# Original DS glyphs are extracted from the verified cartridge's own button artwork.
# Variable bearing/advance is computed from ink columns, unlike the earlier
# Pillow load_default() substitution. The DS will never load a desktop font.
# The four original Digivice states share exactly three NCGR bitmaps.
MENUS = {
    "pt-BR": {479:"Itens",480:"Salvar",481:"Missões",482:"Treinador"},
    "es-ES": {479:"Objetos",480:"Guardar",481:"Misiones",482:"Entrenador"},
}
REGIONS = {
    479:(6,32,53,16),
    480:(10,32,47,16),
    481:(6,32,54,16),
    482:(6,33,55,13),
}
# Only source-caption fragments known from the ROM mapping, outside the new
# text band. These masks deliberately avoid the character's original icon.
EXTRA = {482:((10,22,50,11),)}


def _regions(sprite: int, word: str):
    # Spanish retained its earlier two-line layout and original caption bounds.
    region=(9,33,51,12) if sprite==482 and word=="Entrenador" else REGIONS[sprite]
    return (region,*EXTRA.get(sprite,()))


def draft_cell(src: bytes, nclr: bytes, ncer: bytes, sprite: int, cell: int, word: str,
               pristine=None, glyph_atlas=None, icon_mask=None) -> Image.Image:
    view = extract_cell(src,nclr,ncer,cell)
    rect = _regions(sprite,word)[0]
    rx,ry,rw,rh = rect
    if glyph_atlas is None:
        raise ValueError("must supply pixel-font glyphs extracted from source cartridge")
    if sprite==482 and word=="Treinador":
        # Keep the PT-BR caption on ONE line, just like the other Digivice
        # buttons. The original English Tamer/Info source occupies two
        # rows; only its background is restored above this single label.
        # Condense source glyph columns individually without modifying
        # their NCLR highlights, contours or eleven-pixel height.
        dots,width=layout_trainer_one_line(glyph_atlas,max_width=52)
        if width>rw-2:
            raise ValueError("Treinador exceeds the original title plate")
        left=rx+(rw-width)//2
        baseline=34
        lettering={(left+gx,baseline+gy):idx for (gx,gy),idx in dots.items()}
        if any(not (rx+1<=x<rx+rw-1 and ry<=y<ry+rh)
               for x,y in lettering):
            raise ValueError("Treinador overlaps the original icon or border")
    elif sprite==482 and word=="Entrenador":
        # Preserve the existing Spanish animation artwork until its
        # separate locale has been visually approved for one-line layout.
        lettering={}
        for line,row_y,row_x,row_width in (("Ent",23,10,23),("renador",34,9,51)):
            dots,width=layout_native_word(line,glyph_atlas,row_width)
            if width>row_width:
                raise ValueError(f"{line!r} exceeds original Nintendo text band")
            left=row_x+(row_width-width)//2
            for (gx,gy),idx in dots.items():
                key=(left+gx,row_y+gy)
                if key in lettering:
                    raise ValueError("native Spanish two-row lettering overlap")
                lettering[key]=idx
    else:
        dots,width=layout_native_word(word,glyph_atlas,rw-3)
        scale_x=min(1.0,(rw-3)/width)
        scaled_width=max(1,int(width*scale_x))
        xbase=rx+(rw-scaled_width)//2
        ybase=36 if sprite==480 and word=="Guardar" else ry+(rh-11)//2
        if xbase<rx or ybase<ry or xbase+scaled_width>rx+rw or ybase+11>ry+rh:
            raise ValueError(f"{word!r}: original DS glyph outside caption")
        lettering={(xbase+min(scaled_width-1,int(gx*scale_x)),ybase+gy):idx
                   for (gx,gy),idx in dots.items()}
    colors=palette(nclr)
    # Select authentic index-14 lime (if present) and OAM-dark index 2.
    # Source palette/char indices are never extended.
    arr=Image.new("RGB",view.size)
    out=arr.load()
    orig=view.image.load()
    if icon_mask is None:
        raise ValueError("all original animation states must inform the icon guard")
    for yy in range(view.size[1]):
        for xx in range(view.size[0]):
            out[xx,yy]=orig[xx,yy]
    affected=set()
    for x,y,w,h in _regions(sprite,word):
        for yy in range(y,y+h):
            for xx in range(x,x+w):
                affected.add((xx,yy))
    # Native background is a 4-row striped pattern. The right-hand
    # control sample (x=60) is outside every original label, so it retains
    # palette index zero transparency rather than painting solid stripes.
    # Sprite 482's overlapping two-row title is restored from the original
    # unlettered top half of sprite 479, matched by animation state.
    transparent=(22,26,40)
    for x,y in affected:
        bank=view.mapping[(x,y)][3]
        if (x,y) in icon_mask:
            continue  # exact original icon pixel, including cyan contour/shadow
        if sprite==482:
            if pristine is None:
                raise ValueError("Tamer backdrop must use original Items plate")
            # Sampling x=60 on sprite 482 is unsafe: it sometimes reads
            # the selected clipboard's white/cyan ICON pixels and paints a
            # horizontal white bar into the erased Tamer upper caption.
            # Sprite 479 shares this exact Nintendo plate / NCLR palette.
            # Its x=24 at y<33 is clear of BOTH the button caption and cube.
            # Its x=60 at y>=33 is outside both cube and caption.
            if y<33:
                control_x=x if x<22 else 24
            else:
                control_x=60
            idx=pristine.mapping[(control_x,y)][2]
        else:
            idx=view.mapping[(60,y)][2]
        out[x,y] = transparent if idx==0 else colors[bank*16+idx][:3]
    if sprite==482 and word=="Treinador":
        # Restore only the device's concealed immediate lower edge, using
        # the adjacent original edge pixels of THIS selected animation.
        # The edge must remain visually connected to the main body; a
        # larger mirrored surface produced a rejected detached reflection.
        for yy in (24,25,26):
            source_y=23-(yy-24)
            for xx in range(38,54):
                if (xx,yy) in icon_mask:
                    continue
                _,_,idx,bank=view.mapping[(xx,source_y)]
                if idx in (3,4,5,6,7,8,10,11,12,13,14,15):
                    out[xx,yy]=colors[bank*16+idx][:3]
    # Transplant the authentic foreground palette indices for every
    # recovered letter. No synthesized lime-only rasterization: index 13
    # (green), 14 (yellow-green), and 15 (specular white) are copied from
    # the original English Nintendo DS glyphs.
    # Letter coordinates are now final original-resolution DS coordinates;
    # no anisotropic glyph compression is allowed for Tamer Info.
    bright=dict(lettering)
    # Original Nintendo menu letters have a full one-pixel indigo contour,
    # including the top/left edge, not only a bottom-right drop shadow.
    # Keep it wholly inside the authored caption masks and preserve glyph
    # highlights after drawing the surrounding dark pixels.
    shadows={(x+dx,y+dy) for x,y in bright
             for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(1,1))
             if (x+dx,y+dy) not in bright}
    for x,y in shadows:
        if (x,y) not in affected or (x,y) in icon_mask:continue
        bank=view.mapping[(x,y)][3]
        out[x,y]=colors[bank*16+2][:3]
    collisions=sorted(set(bright).intersection(icon_mask))
    if collisions:
        raise ValueError(f"sprite {sprite}, cell {cell}, translated text overlaps original icon: {collisions[:12]}")
    for (x,y),idx in bright.items():
        if (x,y) not in affected:raise ValueError("original pixel glyph outside text mask")
        bank=view.mapping[(x,y)][3]
        out[x,y]=colors[bank*16+idx][:3]
    return arr


def generate(rom: bytes, locale: str, outdir:Path, preview:bool=True):
    if hashlib.sha256(rom).hexdigest()!=SHA256:
        raise ValueError("wrong owner ROM")
    fs=files(rom)
    outdir.mkdir(parents=True,exist_ok=True)
    # Sprite 479's top-left artwork is an original unlettered template for
    # the two-row Tamer caption. Match animation state, never use a desktop
    # UI theme color to patch an original Nintendo frame.
    clean_chr=packed_resource(rom,fs,"dat/SPR_CHR.PAK",479)
    clean_pal=packed_resource(rom,fs,"dat/SPR_PAL.PAK",479)
    clean_cel=packed_resource(rom,fs,"dat/SPR_CEL.PAK",479)
    glyph_atlas=collect_original_glyphs(rom,fs)
    for sid,word in MENUS[locale].items():
        source=packed_resource(rom,fs,"dat/SPR_CHR.PAK",sid)
        palette_data=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
        cell_data=packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid)
        if sid in (479,480,481,482):
            images=[]
            # Original selected and unselected icons use different palette
            # indices and sometimes move; freeze their collective footprint.
            source_views=[extract_cell(source,palette_data,cell_data,k) for k in range(4)]
            icon_mask=original_icon_pixels(source_views,sid)
            print("UNION_ANIMATED_ICON_MASK",locale,sid,len(icon_mask))
            for state in range(4):
                original=extract_cell(source,palette_data,cell_data,state).image
                pristine=extract_cell(clean_chr,clean_pal,clean_cel,state) if sid==482 else None
                art=draft_cell(source,palette_data,cell_data,sid,state,word,pristine,glyph_atlas,icon_mask)
                output=outdir/f"{sid}-state{state}.png"
                art.save(output,optimize=True)
                images.append((original,art))
            if preview:
                canvas=Image.new("RGB",(128,4*69),(24,20,45))
                for state,(original,art) in enumerate(images):
                    canvas.paste(original,(0,state*69))
                    canvas.paste(art,(64,state*69))
                canvas=canvas.resize((512,1104),Image.Resampling.NEAREST)
                b=io.BytesIO();canvas.save(b,"PNG",optimize=True)
                print("CUSTOM_MENU_SPRITE_ID",locale,sid)
                print("CUSTOM_MENU_SPRITE64 "+base64.b64encode(b.getvalue()).decode("ascii"))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",required=True,type=Path)
    ap.add_argument("--locale",default="pt-BR",choices=MENUS.keys())
    ap.add_argument("--outdir",type=Path,default=ROOT/".private"/"authored-menu-preview")
    ap.add_argument("--no-preview",action="store_true")
    a=ap.parse_args()
    generate(a.rom.read_bytes(),a.locale,a.outdir,preview=not a.no_preview)
