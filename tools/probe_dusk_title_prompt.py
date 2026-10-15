#!/usr/bin/env python3
"""Read-only ROM-native scan of title prompt candidate sprite resources.

Produce contact sheets of 1D NCER sprites with dimensions compatible with the
PUSH START prompt, plus report exact game-text encoding hits. No ROM data or
images are committed; private Actions logs are for owner review only.
"""
from __future__ import annotations
import argparse,hashlib,io,base64,struct
from pathlib import Path
from PIL import Image,ImageDraw
from probe_dusk_strings import SHA256,files,u32
from research_dusk_menu_strings import rle_decompress
from probe_dusk_sprite_cells import get_cell_groups,SIZES
from dusk_sprite_inplace_editor import extract_cell
from nitro_bg_preview import graphics,palette

def entries(pack):
    n=u32(pack,0)
    if n!=1627:raise ValueError("not Dusk original sprite pack")
    for i in range(n):
        off=u32(pack,4+i*8);size=u32(pack,8+i*8)&0x7fffffff
        if not(size>=4 and 4+n*8<=off and off+size<=len(pack)):
            raise ValueError("bad indexed sprite resource")
        yield i,pack[off:off+size]

def candidate_size(objects):
    if not objects:return (0,0)
    shapes=[]
    for a0,a1,a2 in objects:
        shape=(a0>>14)&3;sz=(a1>>14)&3
        if shape>2:continue
        w,h=SIZES[shape][sz]
        x=a1&511;y=a0&255
        if x>=256:x-=512
        if y>=128:y-=256
        shapes.append((x,y,w,h))
    if not shapes:return (0,0)
    return (max(x+w for x,y,w,h in shapes)-min(x for x,y,w,h in shapes),
            max(y+h for x,y,w,h in shapes)-min(y for x,y,w,h in shapes))

def research(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("invalid source ROM")
    catalog=files(rom)
    for name,(fid,lo,hi) in catalog.items():
        print("TITLE_ROM_FILE",fid,name,hi-lo) if name.lower().endswith(
            (".pak",".ncgr",".nclr",".nscr",".ncer",".nftr",".narc")) else None
    needles=["Push Start","PUSH START","PushStart","Press Start","PRESS START"]
    print("TITLE_TEXT_SEARCH",needles)
    for name,(fid,lo,hi) in catalog.items():
        raw=rom[lo:hi]
        found=[]
        for needle in needles:
            for encoding in ("ascii","utf-16-le"):
                if needle.encode(encoding) in raw:found.append(needle+"/"+encoding)
        if found:print("TITLE_TEXT_MATCH",fid,name,found)
    packs={}
    for name in ("dat/SPR_CHR.PAK","dat/SPR_PAL.PAK","dat/SPR_CEL.PAK"):
        _,lo,hi=catalog[name];packs[name]=dict(entries(rom[lo:hi]))
    out=[]
    rejected=0
    for sid in range(1627):
        try:
            c=rle_decompress(packs["dat/SPR_CEL.PAK"][sid])
            if c is None:continue
            groups,mode=get_cell_groups(c)
            if mode not in (0,1,2,3):continue
            ww,hh=candidate_size(groups[0])
            if not (64<=ww<=256 and 12<=hh<=64):continue
            g=rle_decompress(packs["dat/SPR_CHR.PAK"][sid])
            p=rle_decompress(packs["dat/SPR_PAL.PAK"][sid])
            if g is None or p is None or graphics(g)[0]!=3:continue
            frame=extract_cell(g,p,c,0).image
            if frame.size!=(ww,hh):continue
            out.append((sid,mode,len(groups),frame.copy()))
        except (IndexError,ValueError,struct.error):
            rejected+=1
    print("TITLE_SPRITE_CANDIDATES",len(out),"rejected",rejected)
    for index in range(0,len(out),72):
        subset=out[index:index+72]
        cols=6;sw=190;sh=92
        contact=Image.new("RGB",(cols*sw,((len(subset)+cols-1)//cols)*sh),(20,24,35))
        draw=ImageDraw.Draw(contact)
        for j,(sid,mode,n,frame) in enumerate(subset):
            x=j%cols*sw;y=j//cols*sh
            scale=min(3, (sw-8)//frame.width, (sh-20)//frame.height)
            scale=max(1,scale)
            canvas=frame.resize((frame.width*scale,frame.height*scale),Image.Resampling.NEAREST)
            contact.paste(canvas,(x+2,y+2))
            draw.text((x+2,y+sh-15),f"ID {sid} | {frame.width}x{frame.height} | n{n}",fill="white")
        buf=io.BytesIO();contact.save(buf,format="PNG",optimize=True)
        print("TITLE_SPRITE_SHEET",index//72,len(subset))
        print("TITLE_SPRITE_SHEET64 "+base64.b64encode(buf.getvalue()).decode())
    print("TITLE_CANDIDATE_IDS",[x[0] for x in out])

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    args=ap.parse_args()
    research(args.rom.read_bytes())
