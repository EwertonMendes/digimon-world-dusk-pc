"""Deterministic edits of existing 1D Nintendo DS NCGR tiles.

The original Digivice NCER animation has mappingMode=2 (128-byte 1D
granularity). An OAM characterName is in 128-byte units, NOT 32-byte tiles.
No NCER edits and no VRAM growth are required. Preserve every pixel outside
strictly verified label rectangles and all original NCGR/NCER file lengths.

Reference: NitroPaint CellViewerMapGraphicsUsage/NCGR_CHNAME (1D 128K=>4).
"""
from collections import Counter
from dataclasses import dataclass
from PIL import Image,ImageDraw,ImageFont
from nitro_bg_preview import graphics,palette,chunk
from probe_dusk_sprite_cells import SIZES,get_cell_groups

@dataclass(frozen=True)
class CellView:
    size: tuple[int,int]
    mapping: dict
    image: Image.Image

def extract_cell(ncgr:bytes,nclr:bytes,ncer:bytes,cell:int)->CellView:
    depth,raw=graphics(ncgr)
    colors=palette(nclr)
    groups,mode=get_cell_groups(ncer)
    if depth!=3 or not 0<=cell<len(groups) or mode not in (0,1,2,3):
        raise ValueError("unsupported native indexed OAM 1D mapping")
    stride=1 << mode                 # mappingMode=2 => four 32-byte tiles
    items=[]
    for a0,a1,a2 in groups[cell]:
        shape=(a0>>14)&3
        size=(a1>>14)&3
        if shape>=3:raise ValueError("invalid OAM object shape")
        w,h=SIZES[shape][size]
        if (a0>>13)&1:raise ValueError("8-bit graphics unsupported in this editor")
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        base=(a2&0x3ff)*stride
        bank=(a2>>12)&15
        flipx=bool(a1&0x1000);flipy=bool(a1&0x2000)
        items.append((x,y,w,h,base,bank,flipx,flipy))
    if not items:raise ValueError("empty NCER cell")
    minx=min(o[0] for o in items);miny=min(o[1] for o in items)
    maxx=max(o[0]+o[2] for o in items);maxy=max(o[1]+o[3] for o in items)
    w=maxx-minx;h=maxy-miny
    if not (1<=w<=256 and 1<=h<=256):raise ValueError("unreasonable NCER dimensions")
    im=Image.new("RGB",(w,h),(22,26,40))
    pixels=im.load()
    mapping={}
    for x,y,ow,oh,base,bank,hflip,vflip in items:
        for dy in range(oh):
            for dx in range(ow):
                cx=ow-1-dx if hflip else dx
                cy=oh-1-dy if vflip else dy
                tile=base+(cy//8)*(ow//8)+(cx//8)
                off=tile*32+(cy%8)*4+(cx%8)//2
                if off>=len(raw):raise ValueError("NCER references missing original NCGR tile")
                key=(x+dx-minx,y+dy-miny)
                if key in mapping:
                    raise ValueError("overlapping OAM objects require a different editor")
                z=raw[off]
                ix=(z>>4 if cx&1 else z&15)
                colorix=bank*16+ix
                if colorix>=len(colors):raise ValueError("NCER palette index exceeds NCLR")
                mapping[key]=(off,bool(cx&1),ix,bank)
                if ix: pixels[key]=colors[colorix][:3]
    return CellView((w,h),mapping,im)

def _write_pixel(buf:bytearray,offset:int,high:bool,value:int):
    old=buf[offset]
    buf[offset]=(old&15)|(value<<4) if high else (old&240)|value

def _draw_label(image:Image.Image,rect,text):
    rx,ry,rw,rh=rect
    glyph=Image.new("1",(rw,rh),0)
    draw=ImageDraw.Draw(glyph)
    for fontsize in range(min(17,rh+4),5,-1):
        font=ImageFont.load_default(size=fontsize)
        l,t,r,b=draw.textbbox((0,0),text,font=font,stroke_width=1)
        if r-l<=rw-2 and b-t<=rh-2:
            draw.text(((rw-(r-l))//2-l,(rh-(b-t))//2-t),
                      text,font=font,fill=1,stroke_width=1,stroke_fill=1)
            return glyph
    raise ValueError(f"translated text {text!r} does not fit {rw}x{rh}")

def replace_labels(ncgr:bytes,nclr:bytes,ncer:bytes,edits:list[dict])->bytes:
    depth,oldraw=graphics(ncgr)
    colors=palette(nclr)
    if depth!=3:raise ValueError("only indexed 4bpp sprite text")
    replacement=bytearray(ncgr)
    at,_=chunk(replacement,b"RGCN",b"RAHC")
    raw_begin=at+32
    seen=set()
    original_tile_owners={}
    pending={}
    for spec in edits:
        cell=spec.get("cell",0)
        text=spec.get("text")
        if not isinstance(cell,int) or cell in seen:raise ValueError("duplicate/invalid cell")
        seen.add(cell)
        if not isinstance(text,str) or not text or any(ord(c)<32 for c in text):
            raise ValueError("empty or invalid translated text")
        view=extract_cell(ncgr,nclr,ncer,cell)
        w,h=view.size
        rect=spec.get("region")
        if rect is None:
            # Legacy secondary resource: allow whole standalone sprite only
            rect=[0,0,w,h]
        if not (isinstance(rect,list) and len(rect)==4 and
                all(type(v) is int for v in rect)):
            raise ValueError("invalid text rectangle")
        rx,ry,rw,rh=rect
        if not(0<=rx<w and 0<=ry<h and rw>=8 and rh>=8 and rx+rw<=w and ry+rh<=h):
            raise ValueError("edit exceeds original sprite cell")
        if spec.get("color")=="lime":
            ink=max(range(1,16),key=lambda i:colors[i][1]-0.35*(colors[i][0]+colors[i][2]))
        else:
            ink=max(range(1,16),key=lambda i:sum(colors[i][:3]))
        glyph=_draw_label(view.image,rect,text)
        ink_pixels=glyph.load()
        # Infer palette indices per row from original background (not by
        # overwriting icons), preferring dominant stripe in the label band.
        row_bg={}
        for yy in range(ry,ry+rh):
            vals=[view.mapping[(xx,yy)][2] for xx in range(rx,rx+rw)
                  if (xx,yy) in view.mapping and view.mapping[(xx,yy)][2]!=ink]
            if not vals:raise ValueError("can't infer original frame background")
            row_bg[yy]=Counter(vals).most_common(1)[0][0]
        for yy in range(ry,ry+rh):
            for xx in range(rx,rx+rw):
                key=(xx,yy)
                if key not in view.mapping:raise ValueError("text rect traverses missing OAM pixels")
                off,hi,original_index,bank=view.mapping[key]
                target=ink if ink_pixels[xx-rx,yy-ry] else row_bg[yy]
                place=(off,hi)
                # Translation MUST NOT rewrite a shared source pixel in
                # different states. For Digivice 128-byte mapping, the
                # original four states are disjoint.
                if place in pending and pending[place]!=target:
                    raise ValueError("cross-cell shared character pixels cannot be edited")
                pending[place]=target
        print("NATIVE_CELL_IN_PLACE",cell,text,rect,"mode-aware no relocation")
    for (off,high),value in pending.items():
        _write_pixel(replacement,raw_begin+off,high,value)
    if len(replacement)!=len(ncgr):raise ValueError("in-place edit changed file length")
    if replacement==ncgr:raise ValueError("no image pixels modified")
    # Strict byte-level preservation outside declared OAM label pixels.
    allowed={raw_begin+offset for offset,high in pending}
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(replacement,ncgr))):
        raise ValueError("modified Nintendo sprite metadata or other pixels")
    return bytes(replacement)

def assert_frames(ncgr,nclr,ncer,replacement,edits):
    if len(ncgr)!=len(replacement):raise ValueError("original NCGR length changed")
    for edit in edits:
        before=extract_cell(ncgr,nclr,ncer,edit["cell"])
        after=extract_cell(replacement,nclr,ncer,edit["cell"])
        if before.size!=after.size:raise ValueError("animated frame dimensions changed")
        rx,ry,rw,rh=edit.get("region",[0,0,*before.size])
        bp=before.image.load();ap=after.image.load()
        changed=0
        for yy in range(before.size[1]):
            for xx in range(before.size[0]):
                if bp[xx,yy]!=ap[xx,yy]:
                    changed+=1
                    if not (rx<=xx<rx+rw and ry<=yy<ry+rh):
                        raise ValueError("sprite icon, outline or other frame pixels changed")
        if changed<4:raise ValueError("translation did not change visible text")
    print("VERIFIED_OAM_FRAME_PIXELS",len(edits),"original frames preserved outside labels")
