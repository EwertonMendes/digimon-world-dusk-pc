#!/usr/bin/env python3
"""Search original DS sprite banks for full, shared Tamer-Digivice icon tiles."""
import argparse,hashlib,collections
from pathlib import Path
from probe_dusk_strings import SHA256,files,u32
from probe_dusk_sprite_cells import packed_resource
from dusk_sprite_inplace_editor import extract_cell
from nitro_bg_preview import graphics
from research_dusk_menu_strings import rle_decompress

def scan(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("ROM mismatch")
    fs=files(rom)
    s=packed_resource(rom,fs,"dat/SPR_CHR.PAK",482)
    p=packed_resource(rom,fs,"dat/SPR_PAL.PAK",482)
    c=packed_resource(rom,fs,"dat/SPR_CEL.PAK",482)
    glyph=extract_cell(s,p,c,0)
    _,raw=graphics(s)
    targets=collections.defaultdict(list)
    for y in range(12,25,4):
        for x in range(34,62,4):
            offset,_,idx,_=glyph.mapping[(x,y)]
            tile=offset//32
            targets[raw[tile*32:tile*32+32]].append((tile,x,y))
    _,lo,hi=fs["dat/SPR_CHR.PAK"]
    pak=rom[lo:hi];count=u32(pak,0)
    matches=[]
    for sid in range(count):
        if sid==482:continue
        ix=u32(pak,4+8*sid);size=u32(pak,8+8*sid)&0x7fffffff
        if size<=4 or ix+size>len(pak):continue
        decoded=rle_decompress(pak[ix:ix+size])
        if decoded is None:continue
        try:_,data=graphics(decoded)
        except (ValueError,IndexError):continue
        tiles={data[j:j+32] for j in range(0,len(data)-31,32)}
        overlap=[(coords[0][0],coords[0][1:]) for key,coords in targets.items()
                 if key in tiles]
        if overlap:
            matches.append((len(overlap),sid,overlap[:12]))
    matches.sort(reverse=True)
    print("DIGIVICE_REFERENCE_TILE_COUNT",len(targets),"matches",len(matches))
    for n,sid,descs in matches[:50]:print("DIGIVICE_REFERENCE_SPRITE",sid,n,descs)
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--rom",type=Path,required=True)
    scan(a.parse_args().rom.read_bytes())
