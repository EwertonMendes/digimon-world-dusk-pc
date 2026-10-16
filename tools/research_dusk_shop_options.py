#!/usr/bin/env python3
"""Find original menu words in MSG.PAK, ARM9 or compressed NitroFS without
requiring a particular end-of-string marker. Reports source ID or binary offset
for further verification, never blindly writes to game text memory.
"""
import argparse,hashlib,re
from pathlib import Path
from probe_dusk_strings import SHA256,files,u32,u16
from find_dusk_common_text import decode
from research_dusk_menu_strings import rle_decompress,enc
WORDS=("Buy","Sell","Quit","Money","Shop","Equipment","Digimon","Items","Quests","Save")

def main(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("ROM identity mismatch")
    fs=files(rom)
    fid,lo,hi=fs["dat/MSG.PAK"]
    print("MSG_MATCHES")
    seen=0
    for g in range(u32(rom,lo)):
        start=lo+u32(rom,lo+4+8*g)
        length=u32(rom,lo+8+8*g)&0x7fffffff
        numbytes=u32(rom,start)
        if numbytes%4 or numbytes<4 or numbytes>length:continue
        n=numbytes//4
        for j in range(n):
            a=u32(rom,start+4*j)
            z=u32(rom,start+4*(j+1)) if j+1<n else length
            if a<numbytes or z<=a or z>length or (z-a)%2:continue
            tokens=[u16(rom,start+k) for k in range(a,min(z,a+400),2)]
            text=decode(tokens)
            if text and len(text)<=65 and re.search(r"\b(?:Buy|Sell|Quit|Money|Shop)\b",text,re.I):
                print("MSG",g,j,repr(text[:65]))
                seen+=1
                if seen>=90:break
        if seen>=90:break
    arm9=u32(rom,0x20);arm9len=u32(rom,0x2c)
    print("RAW16_MATCHES")
    totals=0
    for path,data in [("ARM9",rom[arm9:arm9+arm9len])]+[(name,rom[a:z]) for name,(fid,a,z) in fs.items() if z-a<2000000 and name!="dat/MSG.PAK"]:
        dec=rle_decompress(data)
        if dec is not None:data=dec
        found=[]
        for token in WORDS:
            signature=enc(token)
            if not signature:continue
            i=data.find(signature)
            if i>=0 and i%2==0:
                found.append((token,i))
        if found:
            print("RESOURCE",path,"hits",found[:12],"mode",("rle" if dec is not None else "raw"))
            totals+=1
            if totals>=80:break
    print("RAW16_TOTAL_FILES",totals)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",type=Path,required=True)
    a=p.parse_args();main(a.rom.read_bytes())
