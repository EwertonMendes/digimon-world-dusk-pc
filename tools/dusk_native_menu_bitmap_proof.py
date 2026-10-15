#!/usr/bin/env python3
"""Prototype hand-authored bitmap glyph artwork on original Nintendo DS sprites.

No Pillow desktop fonts, antialiasing, generic OAM address guesses, or NCER edits.
Uses the authenticated ROM and native NCLR only to draw review previews. The
output remains an experimental proof until the owner approves gameplay images.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
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

ROOT = Path(__file__).resolve().parents[1]

# Original hand-drawn bitmap shapes. Each source glyph has seven 5-pixel rows.
# Variable bearing/advance is computed from ink columns, unlike the earlier
# Pillow load_default() substitution. The DS will never load a desktop font.
FONT = {
    "A":("01110","10001","10001","11111","10001","10001","10001"),
    "B":("11110","10001","10001","11110","10001","10001","11110"),
    "D":("11110","10001","10001","10001","10001","10001","11110"),
    "E":("11111","10000","10000","11110","10000","10000","11111"),
    "F":("11111","10000","10000","11110","10000","10000","10000"),
    "G":("01111","10000","10000","10111","10001","10001","01110"),
    "I":("111","010","010","010","010","010","111"),
    "M":("10001","11011","10101","10101","10001","10001","10001"),
    "O":("01110","10001","10001","10001","10001","10001","01110"),
    "S":("01111","10000","10000","01110","00001","00001","11110"),
    "T":("11111","00100","00100","00100","00100","00100","00100"),
    "a":("00000","00000","01110","00001","01111","10001","01111"),
    "b":("10000","10000","10110","11001","10001","10001","11110"),
    "c":("00000","00000","01111","10000","10000","10000","01111"),
    "d":("00001","00001","01101","10011","10001","10011","01101"),
    "e":("00000","00000","01110","10001","11111","10000","01111"),
    "f":("00110","01001","01000","11110","01000","01000","01000"),
    "g":("00000","01111","10001","10001","01111","00001","11110"),
    "i":("1","0","1","1","1","1","1"),
    "l":("10","10","10","10","10","10","01"),
    "m":("00000","00000","11010","10101","10101","10101","10101"),
    "n":("00000","00000","10110","11001","10001","10001","10001"),
    "o":("00000","00000","01110","10001","10001","10001","01110"),
    "p":("00000","00000","11110","10001","11110","10000","10000"),
    "r":("0000","0000","1011","1100","1000","1000","1000"),
    "s":("00000","00000","01111","10000","01110","00001","11110"),
    "t":("0100","0100","1111","0100","0100","0101","0010"),
    "u":("00000","00000","10001","10001","10001","10011","01101"),
    "v":("00000","00000","10001","10001","10001","01010","00100"),
    "ç":("00000","00000","01111","10000","10000","01111","00100"),
    "õ":("01010","10100","01110","10001","10001","10001","01110"),
    "ó":("00100","01000","01110","10001","10001","10001","01110"),
    "é":("00100","01000","01110","10001","11111","10000","01111"),
    "í":("1","0","1","1","1","1","1"),
}

# The four original Digivice states share exactly three NCGR bitmaps.
MENUS = {
    "pt-BR": {479:"Itens",480:"Salvar",481:"Missões",482:"Treinador"},
    "es-ES": {479:"Objetos",480:"Guardar",481:"Misiones",482:"Entrenador"},
}
REGIONS = {
    479:(6,32,53,16),
    480:(10,32,47,16),
    481:(6,32,54,16),
    482:(6,28,54,17),
}
# Only source-caption fragments known from the ROM mapping, outside the new
# text band. These masks deliberately avoid the character's original icon.
EXTRA = {482:((10,23,12,2),(14,25,4,1),(14,26,42,2))}


def glyph(char: str) -> tuple[str,...]:
    if char not in FONT:
        raise ValueError(f"No reviewed DS glyph for {char!r}")
    return FONT[char]


def composition(text: str) -> tuple[list[tuple[int,int]],int,int]:
    """Return native one-pixel glyph dots and the exact ink extents."""
    all_rows = [glyph(ch) for ch in text]
    x = 0
    dots = []
    for rows in all_rows:
        width = len(rows[0])
        if any(len(row)!=width for row in rows):
            raise ValueError("invalid font glyph shape")
        for yy,row in enumerate(rows):
            for xx,point in enumerate(row):
                if point=="1":
                    dots.append((x+xx,yy))
                elif point!="0":
                    raise ValueError("non-binary custom glyph")
        x += width+1
    return dots,x-1,7


def _regions(sprite: int):
    region = REGIONS[sprite]
    return (region,*EXTRA.get(sprite,()))


def draft_cell(src: bytes, nclr: bytes, ncer: bytes, sprite: int, cell: int, word: str) -> Image.Image:
    view = extract_cell(src,nclr,ncer,cell)
    rect = REGIONS[sprite]
    rx,ry,rw,rh = rect
    dots,width,height = composition(word)
    if width+1 > rw-1:
        # Prefer a legible word with reduced tracking instead of scaling.
        if len(word)>1:
            raise ValueError(f"{word!r}: {width}px does not fit {rw}px")
    xbase=rx+(rw-width)//2
    ybase=ry+(rh-height)//2
    if xbase<=rx or ybase<=ry or xbase+width>rx+rw or ybase+height>=ry+rh:
        raise ValueError(f"{word!r}: pixel font outside native caption")
    colors=palette(nclr)
    # Select authentic index-14 lime (if present) and OAM-dark index 2.
    # Source palette/char indices are never extended.
    arr=Image.new("RGB",view.size)
    out=arr.load()
    orig=view.image.load()
    for yy in range(view.size[1]):
        for xx in range(view.size[0]):
            out[xx,yy]=orig[xx,yy]
    affected=set()
    for x,y,w,h in _regions(sprite):
        for yy in range(y,y+h):
            for xx in range(x,x+w):
                affected.add((xx,yy))
    # Determine original horizontal stripe from outside the source caption:
    # then reconstruct ONLY the declared text mask, never the border or icon.
    row_bg={}
    for yy in sorted({y for x,y in affected}):
        samples=[view.mapping[(xx,yy)][2] for xx in range(12,54)
                 if (xx,yy) in view.mapping and (xx,yy) not in affected]
        if not samples:
            samples=[view.mapping[(xx,yy)][2] for xx in (11,12,54,55,56,57)
                     if (xx,yy) in view.mapping]
        safe=[v for v in samples if v not in (12,13,14,15)]
        if not safe: raise ValueError("could not infer row background")
        row_bg[yy]=Counter(safe).most_common(1)[0][0]
    for x,y in affected:
        bank=view.mapping[(x,y)][3]
        idx=2 if (sprite==482 and (x,y) in {
            (xx,yy) for x0,y0,w,h in EXTRA[482]
            for yy in range(y0,y0+h) for xx in range(x0,x0+w)}) else row_bg[y]
        out[x,y]=colors[bank*16+idx][:3]
    # Draw dark drop shadow then authentic lime glyphs. No antialias or
    # transforms: a single pixel is exactly one native Nintendo DS pixel.
    bright=set((xbase+xx,ybase+yy) for xx,yy in dots)
    shadows={(x+1,y+1) for x,y in bright if (x+1,y+1) not in bright}
    for x,y in shadows:
        if (x,y) not in affected:raise ValueError("text shadow outside mask")
        bank=view.mapping[(x,y)][3]
        out[x,y]=colors[bank*16+2][:3]
    for x,y in bright:
        if (x,y) not in affected:raise ValueError("text glyph outside mask")
        bank=view.mapping[(x,y)][3]
        out[x,y]=colors[bank*16+14][:3]
    return arr


def generate(rom: bytes, locale: str, outdir:Path, preview:bool=True):
    if hashlib.sha256(rom).hexdigest()!=SHA256:
        raise ValueError("wrong owner ROM")
    fs=files(rom)
    outdir.mkdir(parents=True,exist_ok=True)
    for sid,word in MENUS[locale].items():
        source=packed_resource(rom,fs,"dat/SPR_CHR.PAK",sid)
        palette_data=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
        cell_data=packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid)
        if sid in (479,480,481,482):
            images=[]
            for state in range(4):
                original=extract_cell(source,palette_data,cell_data,state).image
                art=draft_cell(source,palette_data,cell_data,sid,state,word)
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
    a=ap.parse_args()
    generate(a.rom.read_bytes(),a.locale,a.outdir)
