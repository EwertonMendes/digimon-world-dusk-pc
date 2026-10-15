#!/usr/bin/env python3
"""Find original DS-encoded menu labels in direct and Nintendo BIOS RLE assets.

Read-only on SHA-pinned Dusk ROM. Finds exact strings with FF FF and FE FF
terminators, avoiding accidental replacements of substrings in prose.
"""
from __future__ import annotations
import argparse,hashlib
from pathlib import Path
from probe_dusk_strings import files,SHA256,u32

TERMS=("Buy","Sell","Quit","Digimon","Items","Quests","DigiFarm",
       "Tamer Info","Save","Equipment Shop","Money","Digivolve",
       "Return","Back","Confirm","Equipment","Next","Move","Deposit")
def enc(s):
    out=bytearray()
    for c in s:
        if c==" ":v=0
        elif c.isascii() and c.isdigit():v=ord(c)-48+1
        elif "A"<=c<="Z":v=ord(c)-65+0x20
        elif "a"<=c<="z":v=ord(c)-97+0x3a
        else:return b""
        out.extend((v,0))
    return bytes(out)
def rle_decompress(data):
    if len(data)<5 or data[0]!=0x30:return None
    limit=data[1]|data[2]<<8|data[3]<<16
    if limit<4 or limit>4_194_304:return None
    out=bytearray();p=4
    while len(out)<limit and p<len(data):
        op=data[p];p+=1
        if op&0x80:
            n=(op&0x7f)+3
            if p>=len(data):return None
            out.extend(bytes([data[p]])*n);p+=1
        else:
            n=(op&0x7f)+1
            if p+n>len(data):return None
            out.extend(data[p:p+n]);p+=n
        if len(out)>limit:return None
    return bytes(out) if len(out)==limit else None
def scan(data,maxout=7):
    results=[]
    for phrase in TERMS:
        b=enc(phrase)
        if not b:continue
        for ending in (b"\xff\xff",b"\xfe\xff"):
            signature=b+ending
            j=data.find(signature)
            n=0
            while j>=0 and n<maxout:
                prev=data[j-2:j] if j>=2 else b""
                if prev in (b"\xff\xff",b"\xfe\xff",b"") or j%2==0:
                    results.append((phrase,j,ending.hex(),prev.hex()))
                    n+=1
                j=data.find(signature,j+2)
    return results

def inspect(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("owner ROM hash mismatch")
    fs=files(rom)
    arm9,sz=u32(rom,0x20),u32(rom,0x2c)
    for phase,name,blob in [("direct","ARM9",rom[arm9:arm9+sz])]:
        for p,j,ending,prev in scan(blob):
            print("HIT",phase,name,p,arm9+j,ending,prev)
    perfile=0;found=0
    for name,(fid,lo,hi) in fs.items():
        data=rom[lo:hi]
        if not data:continue
        decoded=rle_decompress(data)
        if decoded is None:decoded=data
        phase="rle" if decoded is not data else "raw"
        hits=scan(decoded,maxout=3)
        if hits:
            perfile+=1
            for p,j,ending,prev in hits:
                print("HIT",phase,fid,name,p,j,ending,prev);found+=1
    print("SUMMARY",perfile,"files",found,"hits")
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    opts=a.parse_args()
    inspect(opts.rom.read_bytes())
