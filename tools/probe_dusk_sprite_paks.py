#!/usr/bin/env python3
"""Investigate Dusk sprite PAK containers, focusing on UI labels rendered as sprites.
Read-only; emits index and entropy metadata from owner ROM, not binary assets.
"""
import argparse,hashlib,struct,collections
from pathlib import Path
from probe_dusk_strings import SHA256,files,u32,u16
TARGETS=("dat/SPR_CHR.PAK","dat/SPR_PAL.PAK","dat/SPR_CEL.PAK","dat/SPR_ANM.PAK")
def inspect(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("ROM wrong")
    fs=files(rom)
    for name in TARGETS:
        fid,lo,hi=fs[name]
        blob=rom[lo:hi];n=u32(blob,0)
        print("PAK",name,fid,len(blob),"FIRST_U32",[u32(blob,i) for i in range(0,64,4)])
        print("FIRST_U16",[u16(blob,i) for i in range(0,32,2)])
        if not 0<n<=10000:continue
        for variant in (4,8,12):
            need=4+variant*n
            if need>len(blob):continue
            offs=[u32(blob,4+variant*i) for i in range(n)]
            valid=offs==sorted(offs) and offs[0]>=need and offs[-1]<len(blob)
            print("TABLE",variant,"valid",valid,"count",n,"head",offs[:8])
            if valid:
                for i in list(range(min(n,15)))+list(range(max(15,n-8),n)):
                    a=offs[i];z=offs[i+1] if i+1<len(offs) else len(blob)
                    print("CHUNK",i,"start",a,"bytes",z-a,"magic",repr(blob[a:a+8]),"prefix",[u32(blob,a+k) for k in range(0,min(16,z-a)//4*4,4)])
                break
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--rom",type=Path,required=True);o=p.parse_args();inspect(o.rom.read_bytes())
