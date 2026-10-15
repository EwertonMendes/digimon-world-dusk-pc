#!/usr/bin/env python3
"""Find the title prompt with unknown contiguous alphabet ordinal offsets.

Searches native 8-bit or 16-bit contiguous alphabet encodings whose glyph codes
for A..Z differ only by a constant. Does NOT rewrite assets or emit ROM bytes.
"""
import argparse,hashlib
from pathlib import Path
from probe_dusk_strings import SHA256
from research_dusk_menu_strings import rle_decompress
from probe_dusk_strings import files,u32

def scan(data,owner):
    words={"PUSH":[15,20,18,7],"START":[18,19,0,17,19]}
    # Candidate encodings are injective, ordinal and of fixed 8/16-bit stride.
    # Match PUSH + optional word separator + START, testing 0..4 filler codes.
    results=[]
    for stride in (1,2):
        for at in range(0,len(data)-25,stride):
            a=data[at]
            if stride==2 and data[at+1]!=0:continue
            base=(a-15)&255
            if any(data[at+i*stride]!=(base+d)&255 or
                   (stride==2 and data[at+i*stride+1]!=0)
                   for i,d in enumerate(words["PUSH"])):
                continue
            for gap in range(0,8):
                p=at+(4+gap)*stride
                if p+5*stride>len(data):break
                if all(data[p+i*stride]==(base+d)&255 and
                       (stride==1 or data[p+i*stride+1]==0)
                       for i,d in enumerate(words["START"])):
                    results.append((at,stride,base,gap))
                    if len(results)>=50:break
    print("TITLE_ORDINAL_HITS",owner,results[:50])
    return results

def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("owner source mismatch")
    offsets=(u32(rom,0x20),u32(rom,0x2c))
    scan(rom[offsets[0]:offsets[0]+offsets[1]],"ARM9")
    fs=files(rom)
    for name,(fid,lo,hi) in fs.items():
        if name.lower().endswith((".pak",".ntt",".ntp")):
            scan(rom[lo:hi],name)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    run(a.parse_args().rom.read_bytes())
