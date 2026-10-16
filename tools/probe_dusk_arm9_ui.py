#!/usr/bin/env python3
"""Map exact ARM9 menu text records for safe in-memory localization.
Only prints bounded textual snippets and numeric words from verified owner ROM.
"""
from pathlib import Path
import argparse
import hashlib
from probe_dusk_strings import u16,u32,SHA256
from find_dusk_common_text import decode

SITES={
    "shop_buy1":1130728,
    "shop_buy2":1130824,
    "shop_sell1":1130780,
    "shop_sell2":1130908,
    "shop_quit1":1133716,
    "shop_quit2":1133782,
    "menu_quit":1090652,
    "menu_quests":1122920,
    "menu_digifarm":1012966,
    "menu_save":1013032,
    "menu_money":1019578,
    "menu_progress":1012836,
    "menu_digimon":1012848,
    "shop_money":1079304,
}
def inspect(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("ROM mismatch")
    arm=u32(rom,0x20);size=u32(rom,0x2c);ram=u32(rom,0x28)
    print(f"ARM9 ROM: {arm} length={size} guest_ram={ram:#x}")
    # Inventory menu bottom-screen help text lives in a shared 16-bit
    # string block; enumerate all consecutive records from the verified ROM.
    for first,last in [(1012800,1013160),(1079200,1079450),(1130600,1131200)]:
        cursor=first
        print("BLOCK",first,last)
        while cursor+10<last:
            words=[u16(rom,p) for p in range(cursor,last-1,2)]
            try: end=words.index(0xffff)
            except ValueError:break
            if 3<=end<=72 and all((0<=v<=0xbf or v in(0xfffd,0xffed,0xfff0,0xfff1))
                                   for v in words[:end]):
                phrase=decode(words[:end])
                if len(phrase)>=3:
                    print(f"TEXT {cursor} chars={end}: {phrase[:100]!r}")
                cursor+=2*(end+1)
            else:cursor+=2
    for name,pos in SITES.items():
        if pos<arm or pos+96>arm+size:raise ValueError(f"{name} outside ARM9")
        words=[u16(rom,pos+i) for i in range(0,96,2)]
        # True encoded messages usually end at FFFF; preserve in place.
        term=next((i for i,w in enumerate(words) if w in(0xffff,0xfffe)),None)
        span=96 if term is None else 2*(term+1)
        text=decode(words[:min(40,term if term is not None else 40)])
        # Include 12 words following first terminator for spacing inspection
        trailer=words[term:term+18] if term is not None else words[:18]
        before=[u16(rom,pos-i) for i in range(2,16,2)]
        print(f"SITE {name} rom={pos} ram={ram+pos-arm:#x} bytes_to_term={span}"
              f" value={text!r} before={before} after={trailer}")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",type=Path,required=True)
    args=p.parse_args()
    inspect(args.rom.read_bytes())
