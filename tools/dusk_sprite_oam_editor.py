"""Patch game-owned translated title sprites by their NCER cell coordinates.

Unlike the NCGR tile atlas, NCER OAM cell positions describe how a label
looks on screen. Using these coordinates avoids leftover English letters
when a title is split into multiple OAM objects.
"""
from PIL import Image,ImageDraw,ImageFont
from nitro_bg_preview import graphics,palette,chunk
from probe_dusk_sprite_cells import get_cell_groups,SIZES

def edit_ncer_title(ncgr:bytes,nclr:bytes,ncer:bytes,labels:list[dict])->bytes:
    chars=bytearray(ncgr)
    depth,raw=graphics(chars)
    if depth!=3:raise ValueError("only indexed 4bpp supported")
    count=len(raw)//32
    cols=32 if count>=64 else 16
    width=cols*8
    height=((count+cols-1)//cols)*8
    img=Image.new("P",(width,height))
    px=img.load()
    for tile in range(count):
        for row in range(8):
            for j in range(4):
                c=raw[tile*32+row*4+j]
                ox=(tile%cols)*8+j*2;oy=(tile//cols)*8+row
                px[ox,oy]=c&15
                px[ox+1,oy]=c>>4
    colors=palette(nclr)
    cells,_=get_cell_groups(ncer)
    used_cells=set();used_pixels=set()
    for edit in labels:
        cell=edit.get("cell",0);title=edit.get("text")
        if not isinstance(cell,int) or not 0<=cell<len(cells):
            raise ValueError("cell outside sprite")
        if cell in used_cells:raise ValueError("duplicate title edit")
        used_cells.add(cell)
        if not isinstance(title,str) or not title or any(not 32<=ord(c)<127 for c in title):
            raise ValueError("unsupported title characters")
        mapping={}
        for a0,a1,a2 in cells[cell]:
            shape=(a0>>14)&3;size=(a1>>14)&3
            if shape>=3:raise ValueError("invalid OAM shape")
            ow,oh=SIZES[shape][size]
            x=a1&511;y=a0&255
            if x>=256:x-=512
            if y>=128:y-=256
            tile=a2&1023
            flipx=bool(a1&0x1000);flipy=bool(a1&0x2000)
            for dy in range(oh):
                for dx in range(ow):
                    tx=ow-1-dx if flipx else dx
                    ty=oh-1-dy if flipy else dy
                    tid=tile+(ty//8)*(ow//8)+(tx//8)
                    if tid>=count:raise ValueError("cell tile exceeds original sprite resource")
                    point=((tid%cols)*8+tx%8,(tid//cols)*8+ty%8)
                    at=(x+dx,y+dy)
                    if at in mapping and mapping[at]!=point:
                        raise ValueError("overlapping OAM objects need manual editing")
                    mapping[at]=point
        if not mapping:raise ValueError("empty OAM title")
        minx=min(k[0] for k in mapping);maxx=max(k[0] for k in mapping)
        miny=min(k[1] for k in mapping);maxy=max(k[1] for k in mapping)
        w=maxx-minx+1;h=maxy-miny+1
        if not 6<=h<=64:raise ValueError("unexpected text bounding box")
        glyph=Image.new("1",(w,h))
        draw=ImageDraw.Draw(glyph)
        chosen=None
        for fontsize in range(min(h+4,12),5,-1):
            font=ImageFont.load_default(size=fontsize)
            l,t,r,b=draw.textbbox((0,0),title,font=font)
            if r-l<=w-2 and b-t<=h:
                chosen=(font,l,t,r,b);break
        if chosen is None:raise ValueError(f"translated title {title!r} doesn't fit cell")
        font,l,t,r,b=chosen
        draw.text(((w-(r-l))//2-l,(h-(b-t))//2-t),title,font=font,fill=1)
        glyphpx=glyph.load()
        ink=max(range(1,16),key=lambda c:sum(colors[c][:3]))
        for point,(pxx,pyy) in mapping.items():
            if (pxx,pyy) in used_pixels:
                raise ValueError("shared OAM tile was already overwritten")
            used_pixels.add((pxx,pyy))
            px[pxx,pyy]=ink if glyphpx[point[0]-minx,point[1]-miny] else 0
        print("REPLACED_NATIVE_NCER_CELL",cell,title,w,h)
    at,_=chunk(chars,b"RGCN",b"RAHC")
    base=at+32
    for t in range(count):
        for iy in range(8):
            for j in range(4):
                x=(t%cols)*8+j*2;y=(t//cols)*8+iy
                chars[base+t*32+iy*4+j]=px[x,y]|(px[x+1,y]<<4)
    if chars==ncgr:raise ValueError("source graphic unchanged after edit")
    return bytes(chars)
