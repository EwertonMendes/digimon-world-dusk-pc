#!/usr/bin/env python3
"""Find shop Buy/Sell/Quit menu sprites by layout, palette and OAM-template match
to Dusk's known 3-option green inventory action box (sprite 516).
"""
import argparse,hashlib
from pathlib import Path
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource,get_cell_groups
from nitro_bg_preview import graphics

def scan(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    fs=files(rom)
    base_pal=packed_resource(rom,fs,"dat/SPR_PAL.PAK",516)
    base_cell=packed_resource(rom,fs,"dat/SPR_CEL.PAK",516)
    pattern,base_mode=get_cell_groups(base_cell)
    pattern_sig=[tuple((a0&0xff, a1&0x3ff, (a0>>14)&3,(a1>>14)&3) for a0,a1,a2 in row)
                 for row in pattern[:3]]
    matches=[]
    for sid in range(650):
        pal=packed_resource(rom,fs,"dat/SPR_PAL.PAK",sid)
        cells=get_cell_groups(packed_resource(rom,fs,"dat/SPR_CEL.PAK",sid))
        table,mode=cells
        sig=[tuple((a0&0xff, a1&0x3ff, (a0>>14)&3,(a1>>14)&3) for a0,a1,a2 in row)
             for row in table[:3]]
        score=0
        if pal==base_pal:score+=5
        if len(table)==len(pattern):score+=4
        if mode==base_mode:score+=1
        if len(table[0])==3:score+=3
        if sig and pattern_sig and sig[0]==pattern_sig[0]:score+=6
        if len(sig)>1 and sig[1]==pattern_sig[1]:score+=3
        if score>=10:matches.append((score,sid,len(table),len(table[0]),pal==base_pal))
    matches.sort(reverse=True)
    print("SIMILAR_MENU_SPRITES",matches[:90])
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",type=Path,required=True)
    args=p.parse_args();scan(args.rom.read_bytes())
