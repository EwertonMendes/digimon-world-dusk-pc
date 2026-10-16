"""Native original-palette title prompt replacement (Nintendo NCGR only).

The original Dusk title sprite 620 is a layered NCER animation. Its first
four OAM objects form a compact 104x16 title-label plane; the remaining
objects own the animated cyan/magenta ribbon and MUST stay unchanged.
No SDL drawing, desktop fonts, scaled screenshots or OAM table hacks.
"""
from __future__ import annotations

from hashlib import sha256
from collections import Counter
from PIL import Image
from nitro_bg_preview import chunk,graphics
from probe_dusk_title_letter_grid import original_title_pixels
from probe_dusk_title_prompt_exact import composite_cell
from probe_dusk_sprite_cells import get_cell_groups
from dusk_sprite_inplace_editor import _write_pixel

ORIGINAL="PUSHSTART"
TARGET="APERTE START"
# Exact colored glyph spans in the verified original Nintendo sprite 620.
# The original word gap is at x47..50.
SPANS=((3,13),(14,24),(25,34),(35,46),(51,61),
       (62,71),(72,81),(82,92),(93,102))
INK={3,4,5,6,7,8}
WORDS={"PUSHSTART":ORIGINAL}


def source_glyphs(grid):
    if len(grid)!=16 or any(len(row)!=104 for row in grid):
        raise ValueError("invalid source title glyph plane")
    glyphs={}
    for letter,(a,b) in zip(ORIGINAL,SPANS):
        coords={(x-a,y):grid[y][x]
                for y in range(16) for x in range(a,b)
                if grid[y][x] in INK}
        if not coords or any(y<3 or y>12 for x,y in coords):
            raise ValueError(f"native source font invalid for {letter}")
        glyphs.setdefault(letter,(b-a,coords))
    # E comes from the original P's authentic letter strokes. Only the
    # lower crossbar is synthesized using Nintendo's S bottom-stroke
    # colors, which match the native title's multiple highlight bands.
    width,p=glyphs["P"]
    s_w,s=glyphs["S"]
    e=dict(p)
    for x in range(2,width-1):
        # The original S lower edge supplies native shadow/shine values.
        for yy in (11,12):
            source_col=min(s_w-1,int(x*s_w/width))
            e[(x,yy)]=s.get((source_col,yy),5 if yy==12 else 7)
    glyphs["E"]=(width,e)
    return glyphs


def make_title_pixels(grid,text=TARGET):
    if text!=TARGET:
        raise ValueError("only audited PT-BR title text permitted")
    glyphs=source_glyphs(grid)
    non_space=[c for c in text if c!=" "]
    if set(non_space)-set(glyphs):
        raise ValueError("source-native title font missing character")
    # Rebuild only the independent text plane. The original banding in
    # background OAM objects 4+ is never even addressed by this editor.
    pix=[[0]*104 for _ in range(16)]
    for yy in range(1,15):
        for xx in range(1,103):
            pix[yy][xx]=2
    raw_width=sum(glyphs[c][0] for c in non_space)+4*text.count(" ")
    target_width=min(102,raw_width)
    if raw_width>116:
        raise ValueError("translated title is too wide for original OAM plane")
    k=target_width/raw_width
    base=(104-target_width)//2
    label={}
    pos=0
    for char in text:
        if char==" ":
            pos+=4
            continue
        ww,dots=glyphs[char]
        for (dx,dy),idx in dots.items():
            xp=base+min(target_width-1,int((pos+dx)*k))
            if not 1<=xp<=102 or not 2<=dy<=13:
                raise ValueError("native title glyph outside original caption plane")
            key=(xp,dy)
            label[key]=max(idx,label.get(key,0))
        pos+=ww
    # Indigo (index 1) silhouette is the game's existing shadow color;
    # light-blue/white pixels retain their exact source NCLR indexes.
    shadow={(x+dx,y+dy) for (x,y) in label
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))
            if (x+dx,y+dy) not in label}
    for x,y in shadow:
        if 1<=x<=102 and 2<=y<=13:
            pix[y][x]=1
    for (x,y),idx in label.items():
        pix[y][x]=idx
    return pix, {"original_width":raw_width,"rendered_width":target_width,
                 "glyph_count":len(non_space),"spacing":"native 0px + word separator"}


def replace_title(ncgr,nclr,ncer):
    before,items=original_title_pixels(ncgr,ncer)
    target,stats=make_title_pixels(before)
    groups,mode=get_cell_groups(ncer)
    if mode!=2 or len(groups)!=4 or groups[0][:4]!=groups[2][:4]:
        raise ValueError("native title animation state changed")
    at,_=chunk(ncgr,b"RGCN",b"RAHC")
    raw_begin=at+32
    modified=bytearray(ncgr)
    indices={}
    left=min(x for x,y,w,h,base in items)
    top=min(y for x,y,w,h,base in items)
    for x,y,w,h,base in items:
        for dy in range(h):
            for dx in range(w):
                gx=x+dx-left;gy=y+dy-top
                tile=base+(dy//8)*(w//8)+(dx//8)
                off=tile*32+(dy%8)*4+(dx%8)//2
                high=bool(dx&1)
                key=(off,high)
                index=target[gy][gx]
                if key in indices and indices[key]!=index:
                    raise ValueError("different OAM mapping targets same Nintendo tile")
                indices[key]=index
    # Only text tile names 0..27 may be written. The animated ribbon begins
    # at NCGR tile 28 (original OAM characterName 7, mode2).
    if any(off>=28*32 for off,_ in indices):
        raise ValueError("attempt to overwrite animated ribbon tile bank")
    for (off,hi),val in indices.items():
        _write_pixel(modified,raw_begin+off,hi,val)
    if len(modified)!=len(ncgr):
        raise ValueError("native title header size changed")
    if modified==ncgr:
        raise ValueError("title prompt localization was a no-op")
    allowed={raw_begin+off for off,_ in indices}
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(modified,ncgr))):
        raise ValueError("title editor modified metadata or ribbon frames")
    # Animations 1/3 MUST be byte-for-byte identical on visible pixels:
    # neither contains a text OAM component.
    for state in (1,3):
        a=composite_cell(ncgr,nclr,ncer,state)
        b=composite_cell(bytes(modified),nclr,ncer,state)
        if a.tobytes()!=b.tobytes():
            raise ValueError("title prompt changed an animation without text")
    # Text cells change only the verified OAM label plane (104x16),
    # leaving 192x32 banner pixels outside the label unchanged.
    for state in (0,2):
        a=composite_cell(ncgr,nclr,ncer,state)
        b=composite_cell(bytes(modified),nclr,ncer,state)
        if a.size!=(192,32) or b.size!=a.size:
            raise ValueError("title canvas dimensions changed")
        diff=0
        for yy in range(32):
            for xx in range(192):
                if a.getpixel((xx,yy))!=b.getpixel((xx,yy)):
                    diff+=1
                    if not (44<=xx<148 and 8<=yy<24):
                        raise ValueError("title artwork changed outside text-only label layer")
        if diff<24:
            raise ValueError("title glyph changes missing from visible animation")
    return bytes(modified),stats
