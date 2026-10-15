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

def inspect(raw:bytes,spec:str):
    if hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError("unexpected ROM")
    _,lo,hi=files(raw)["dat/MSG.PAK"]
    for pair in spec.split(","):
        group,mid=map(int,pair.split(":"))
        if not 0<=group<138:raise ValueError("group outside MSG.PAK")
        off=u32(raw,lo+4+group*8)
        size=u32(raw,lo+8+group*8)&0x7fffffff
        begin=lo+off
        ptrbytes=u32(raw,begin)
        if ptrbytes%4 or ptrbytes<4 or ptrbytes>size:raise ValueError("not a valid group")
        if not 0<=mid<ptrbytes//4:raise ValueError("message outside group")
        a=u32(raw,begin+4*mid)
        b=u32(raw,begin+4*(mid+1)) if (mid+1)<ptrbytes//4 else size
        if a<ptrbytes or b<=a or b>size:raise ValueError("bad offsets")
        decoded=[]
        for i in range(a,b,2):
            v=u16(raw,begin+i)
            if v==0xffff:decoded.append("[FFFF]");continue
            if v==0xfffe:decoded.append("[END]");continue
            if v==0xfffd:decoded.append("\\n");continue
            if v==0xffed:decoded.append("[PLAYER_NAME]");continue
            if v==0xfff0:decoded.append("[VAR]");continue
            if v==0xffee:decoded.append("[RED]");continue
            if v==0:decoded.append(" ");continue
            if 1<=v<=10:decoded.append(chr(48+v-1));continue
            if 0x20<=v<=0x39:decoded.append(chr(65+v-0x20));continue
            if 0x3a<=v<=0x53:decoded.append(chr(97+v-0x3a));continue
            table={0x0b:"/",0x0c:"%",0x0d:":",0x0e:"'",0x0f:'"',
              0x11:",",0x12:".",0x13:"!",0x14:"?",0x15:"(",0x16:")",
              0x17:"+",0x18:"-",0x19:"=",0x9f:"¿",0x9e:"¡"}
            decoded.append(table.get(v,f"[{v:04x}]"))
        print(f"EXACT {group:03}/{mid:03}: {''.join(decoded)[:240]} (bytes={b-a})")


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--rom",type=Path,required=True)
    cli.add_argument("--limit",type=int,default=85)
    cli.add_argument("--inspect",default="")
    opts=cli.parse_args()
    raw=opts.rom.read_bytes()
    discover(raw,opts.limit)
    if opts.inspect:inspect(raw,opts.inspect)
