#!/usr/bin/env python3
"""Identify non-MSG.PAK UI text sources in the verified original ROM.

Checks Digimon 16-bit character codes, ASCII and UTF-16, reporting only numeric
addresses and the containing NitroFS path; never dumps binary assets.
"""
from pathlib import Path
import argparse
from probe_dusk_strings import files,u32,SHA256
from hashlib import sha256

TERMS=("Buy","Sell","Quit","Items","Quests","DigiFarm","Tamer Info",
       "Save","Equipment Shop","Money","Equipment","Check Digimon progress",
       "Digimon","Shop","Digivolve")

def digicode(text):
    words=[]
    for c in text:
        if c==" ":x=0
        elif "0"<=c<="9":x=1+ord(c)-ord("0")
        elif "A"<=c<="Z":x=0x20+ord(c)-ord("A")
        elif "a"<=c<="z":x=0x3a+ord(c)-ord("a")
        else:return b""
        words.extend((x,0))
    return bytes(words)

def analyze(raw):
    if sha256(raw).hexdigest()!=SHA256:raise ValueError("ROM identity mismatch")
    fs=files(raw)
    spans=sorted([(lo,hi,name)for name,(fid,lo,hi)in fs.items()])
    paklo,pakhi=(fs["dat/MSG.PAK"][1:])
    arm9=u32(raw,0x20);arm9size=u32(raw,0x2c)
    arm7=u32(raw,0x30);arm7size=u32(raw,0x3c)
    scan=[(arm9,arm9+arm9size,"ARM9"),(arm7,arm7+arm7size,"ARM7")]
    scan.extend((lo,hi,name)for lo,hi,name in spans if not(lo==paklo and hi==pakhi))
    print("files",len(fs),"ARM9",arm9size,"ARM7",arm7size)
    for term in TERMS:
        values={}
        for encoding,needle in [("dusk16",digicode(term)),("ascii",term.encode()),
                                ("utf16",term.encode("utf-16le"))]:
            if not needle:continue
            matches=[]
            for start,end,name in scan:
                segment=raw[start:end];offset=segment.find(needle)
                while offset>=0 and len(matches)<12:
                    matches.append((name,start+offset))
                    offset=segment.find(needle,offset+1)
                if len(matches)>=12:break
            if matches:values[encoding]=matches
        if values:print("TERM",term,values)
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    args=ap.parse_args()
    analyze(args.rom.read_bytes())
