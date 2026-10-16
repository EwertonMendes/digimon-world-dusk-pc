#!/usr/bin/env python3
"""Inspect source-native S-menu font palette rows (read-only)."""
import argparse,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource
from dusk_sprite_inplace_editor import extract_cell
from nitro_bg_preview import palette

def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("source mismatch")
    fs=files(rom)
    for id in (477,478,479,480,481,482):
        chars=packed_resource(rom,fs,"dat/SPR_CHR.PAK",id)
        pal=packed_resource(rom,fs,"dat/SPR_PAL.PAK",id)
        cel=packed_resource(rom,fs,"dat/SPR_CEL.PAK",id)
        v=extract_cell(chars,pal,cel,0)
        colors=palette(pal)
        print("MENU_SOURCE_PALETTE",id,[(i,c[:3]) for i,c in enumerate(colors[:16])])
        for y in range(29,47):
            outside=v.mapping.get((60,y))
            if outside is None:continue
            bg=outside[2]
            hist=Counter(v.mapping[(x,y)][2] for x in range(7,57)
                         if (x,y) in v.mapping and v.mapping[(x,y)][2]!=bg)
            print("MENU_SOURCE_ROW",id,y,"background",bg,"ink",sorted(hist.items()))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    args=ap.parse_args()
    run(args.rom.read_bytes())
