#!/usr/bin/env python3
"""Find often-reachable UI/interaction text IDs in owner's verified Dusk ROM.

For ROM-owner CI research only: print small, filtered snippets; never export
binary game assets, transcripts, or an edited cartridge.
"""
import argparse
import hashlib
import re
from pathlib import Path
from probe_dusk_strings import SHA256, files, u32, u16

KEYWORDS=(
    "save","load","yes","no","cancel","are you sure","want to","would you",
    "do you","check","items","item","shop","welcome","continue","battle",
    "run away","flee","defeat","won","exp","bit","attack","skill","victory",
    "turn","next","choose","digivolve","escape","level","buy","sell","exit",
    "select","return","okay","all right","talk","press","wait","opened",
)
def decode(words):
    out=[]
    for c in words:
        if c==0xffff:break
        if c==0xfffe:break
        if c==0xfffd:out.append(" ");continue
        if c==0:out.append(" ")
        elif 1<=c<=10:out.append(chr(48+c-1))
        elif 0x20<=c<=0x39:out.append(chr(65+c-0x20))
        elif 0x3a<=c<=0x53:out.append(chr(97+c-0x3a))
        elif c==0x0b:out.append("/")
        elif c==0x0d:out.append(":")
        elif c==0x12:out.append(".")
        elif c==0x13:out.append("!")
        elif c==0x14:out.append("?")
        elif c==0x11:out.append(",")
        elif c==0xffed:out.append(" {PLAYER} ")
        elif c==0xfff0:out.append(" {VAR} ")
        elif c in (0xffe7,0xffe8,0xffe9,0xffea,0xffeb,0xffee,0xffef):
            out.append(" ")
        else:out.append(" ")
    return re.sub(r"\s+"," ","".join(out)).strip()

def discover(raw,limit=85):
    if hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError("verified ROM required")
    fid,lo,hi=files(raw)["dat/MSG.PAK"]
    n=u32(raw,lo)
    assert fid==23 and n==138
    candidates=[]
    for group in range(n):
        off=u32(raw,lo+4+group*8)
        size=u32(raw,lo+8+group*8)&0x7fffffff
        a=lo+off
        if a+size>hi:raise ValueError("MSG.PAK out of bounds")
        size_of_pointers=u32(raw,a)
        if size_of_pointers%4!=0 or not 4<=size_of_pointers<min(4096*4,size):
            continue
        count=size_of_pointers//4
        for mid in range(count):
            start=u32(raw,a+mid*4)
            end=u32(raw,a+(mid+1)*4) if mid+1<count else size
            if start<size_of_pointers or end>size or start>=end or (end-start)%2:
                continue
            words=[u16(raw,a+i) for i in range(start,min(end,start+280),2)]
            s=decode(words)
            if not s or len(s)<4:continue
            hits=[kw for kw in KEYWORDS if re.search(r"\b"+re.escape(kw)+r"\b",s,re.I)]
            if hits:
                score=max(len(kw) for kw in hits)
                if len(s)<52:score+=15
                if len(s)>100:score-=15
                candidates.append((score,group,mid,end-start,s))
    # Group results by hit category; prefer concise UI strings.
    candidates.sort(key=lambda it:(-it[0],it[1],it[2]))
    for score,group,mid,bytes_,s in candidates[:limit]:
        print(f"{group:03}/{mid:03}: {s[:115]} [bytes={bytes_}]")
    print(f"hits={len(candidates)} groups={len(set(x[1] for x in candidates))}")

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--rom",type=Path,required=True)
    cli.add_argument("--limit",type=int,default=85)
    opts=cli.parse_args()
    discover(opts.rom.read_bytes(),opts.limit)
