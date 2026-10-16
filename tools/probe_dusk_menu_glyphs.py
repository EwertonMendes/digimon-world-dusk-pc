#!/usr/bin/env python3
"""Expose original DS menu caption foreground glyph columns (diagnostic only)."""
import argparse,hashlib
from pathlib import Path
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource
from dusk_sprite_inplace_editor import extract_cell

WORDS={477:"Digimon",478:"DigiFarm",479:"Items",480:"Save",481:"Quests",482:"Tamer Info"}
def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong game")
    fs=files(rom)
    for sid,word in WORDS.items():
        a=packed_resource(rom,fs,"dat/SPR_CHR.PAK",sid)
        b=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
        c=packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid)
        v=extract_cell(a,b,c,0)
        print("CAPTION_SOURCE",sid,word,v.size)
        x0,x1=5,60
        for y in range(20 if sid==482 else 31,45):
            if sid!=482 and y<31:continue
            row=[]
            for x in range(x0,x1):
                t=v.mapping[(x,y)][2]
                row.append({0:" ",1:".",2:".",9:"_",13:"g",14:"L",15:"W"}.get(t," "))
            print(f"CAPTION_PIXELS {sid} {y:02d} {''.join(row)}")
        for zone in ((31,45),) if sid!=482 else ((22,33),(33,45)):
            profile=[]
            for x in range(x0,x1):
                profile.append(sum(v.mapping[(x,y)][2] in (13,14,15) for y in range(*zone)))
            print("CAPTION_PROFILE",sid,zone,profile)
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    args=ap.parse_args()
    run(args.rom.read_bytes())
