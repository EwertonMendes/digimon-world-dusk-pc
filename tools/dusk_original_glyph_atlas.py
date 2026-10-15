"""Pixel-perfect native Dusk alphabet sourced from the game's own OAM glyphs.

Every glyph in SOURCE comes from the original multi-shaded S-menu artwork
(sprites 477-482). This is intentionally not Pillow's desktop font. The few
glyphs missing from Nintendo's six English button names are hand-composed
using the source NCLR indices 13/14/15, with no antialiasing.
"""
from __future__ import annotations
from dataclasses import dataclass
from probe_dusk_sprite_cells import packed_resource
from dusk_sprite_inplace_editor import extract_cell

@dataclass(frozen=True)
class Glyph:
    width: int
    pixels: tuple[tuple[int,int,int], ...]  # x, baseline-aligned y, original NCLR index

# crop x0,x1,y0,y1; preserve empty glyph columns for native kerning.
SOURCE = {
    "D":(477,7,17,33,44),
    "I":(479,12,17,33,44),
    "S":(480,13,23,33,44),
    "T":(482,11,20,23,33),
    "F":(478,29,36,33,44),
    "a":(480,25,34,33,44),
    "e":(479,25,32,33,44),
    "g":(477,21,28,33,44),
    "i":(477,18,20,33,44),
    "m":(479,33,43,33,44),
    "n":(477,52,59,33,44),
    "o":(477,44,51,33,44),
    "r":(478,45,50,33,44),
    "s":(479,44,50,33,44),
    "t":(479,20,24,33,44),
    "u":(481,20,27,33,44),
    "v":(480,35,44,33,44),
}
MISSING={
    "E":("111111","110000","110000","111110","110000","110000","110000","110000","110000","110000","111111"),
    "G":("0111111","1100000","1100000","1100000","1100111","1100011","1100011","1100011","1100011","1100011","0111111"),
    "M":("110000011","111000111","111101111","110111011","110010011","110000011","110000011","110000011","110000011","110000011","110000011"),
    "O":("0111110","1100011","1100011","1100011","1100011","1100011","1100011","1100011","1100011","1100011","0111110"),
    "b":("1100000","1100000","1100000","1111110","1100011","1100011","1100011","1100011","1100011","1100011","1111110"),
    "d":("0000011","0000011","0000011","0111111","1100011","1100011","1100011","1100011","1100011","1100011","0111111"),
    "j":("00011","00011","00000","00011","00011","00011","00011","00011","00011","11011","01110"),
    "l":("110","110","110","110","110","110","110","110","110","110","111"),
}
def handmade(rows:tuple[str,...])->Glyph:
    if len(rows)!=11 or any(len(row)!=len(rows[0]) for row in rows):
        raise ValueError("manual native glyph must have 11 equal-height rows")
    coords=[]
    for y,row in enumerate(rows):
        for x,c in enumerate(row):
            if c not in ("0","1"):raise ValueError("non-bitmapped hand glyph")
            if c=="1":
                ix = 13 if y<=1 or y>=8 else 14 if y<=2 or y>=6 else 15
                coords.append((x,y,ix))
    return Glyph(len(rows[0]),tuple(coords))


def collect_original_glyphs(rom:bytes,fs:dict)->dict[str,Glyph]:
    cache={}
    out={}
    for letter,(sid,x0,x1,y0,y1) in SOURCE.items():
        if sid not in cache:
            a=packed_resource(rom,fs,"dat/SPR_CHR.PAK",sid)
            b=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
            c=packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid)
            cache[sid]=extract_cell(a,b,c,0)
        source=cache[sid]
        points=tuple((x-x0,y-(23 if sid==482 else 33),source.mapping[(x,y)][2])
                     for y in range(y0,y1) for x in range(x0,x1)
                     if source.mapping[(x,y)][2] in (13,14,15))
        if not points:raise ValueError(f"source glyph {letter} has no authentic color pixels")
        # Original OAM label rectangles include spacer/background columns.
        # Do not include those invisible margins in translated glyph advance:
        # nine-letter Portuguese labels otherwise get squeezed until their
        # letters collide, especially Tamer Info -> Treinador.
        min_ink=min(x for x,y,index in points)
        max_ink=max(x for x,y,index in points)
        tight=tuple((x-min_ink,y,index) for x,y,index in points)
        out[letter]=Glyph(max_ink-min_ink+1,tight)
    for char,shape in MISSING.items():out[char]=handmade(shape)
    # The original game's lower-case 'o' and its authentic shading anchor
    # Portuguese nasal vowels; add the 3-pixel accent in the empty top rows.
    o=out["o"]
    out["õ"]=Glyph(o.width,o.pixels+((2,0,13),(4,0,13),(3,1,14),(5,1,14)))
    out["ó"]=Glyph(o.width,o.pixels+((4,0,14),(3,1,13)))
    return out


def layout_native_word(word:str,glyphs:dict[str,Glyph],max_width:int)->tuple[dict[tuple[int,int],int],int]:
    missing=set(word)-glyphs.keys()
    if missing:raise ValueError(f"no native-font glyph for {sorted(missing)!r}")
    widths=sum(glyphs[ch].width for ch in word)
    # Prefer the source 2px tracking. In a long localized label, remove
    # inter-glyph spacing BEFORE touching any original character pixels.
    # A zero-tracking word can still be readable because real DS glyph
    # margins are measured from the original foreground bounding box.
    spacer=2 if widths+2*(len(word)-1)<=max_width else (
        1 if widths+(len(word)-1)<=max_width else 0)
    positions={}
    x=0
    for ch in word:
        g=glyphs[ch]
        for px,py,ix in g.pixels:
            positions[x+px,py]=ix
        x+=g.width+spacer
    width=x-spacer
    if width<=0:raise ValueError("empty title")
    return positions,width
