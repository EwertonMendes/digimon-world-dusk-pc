#!/usr/bin/env python3
"""Read-only ARM9 UI/script pointer investigation for Buy/Sell/Quit.

Enumerates encoded records and absolute ARM9 pointers, to determine whether
entire native dialog records can be safely relocated for longer translations.
"""
import argparse,hashlib,struct
from pathlib import Path
from probe_dusk_strings import SHA256,u16,u32
from find_dusk_common_text import decode
SITES=[1130728,1130780,1130824,1130908,1133716,1133782]
def scan(rom):
  if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("Source ROM mismatch")
  start=u32(rom,0x20);size=u32(rom,0x2c);ram=u32(rom,0x28)
  arm=rom[start:start+size]
  print("ARM9",hex(start),size,hex(ram))
  for off in SITES:
    ix=off-start
    lo=ix
    for at in range(ix-2,max(0,ix-320),-2):
      if u16(arm,at)==0xffff:
        lo=at+2;break
    hi=ix
    for at in range(ix+2,min(size-2,ix+320),2):
      if u16(arm,at)==0xffff:
        hi=at+2;break
    print("SITE",off,"record",start+lo,start+hi,"size",hi-lo,
          "value",repr(decode([u16(arm,p) for p in range(lo,hi-2,2)])))
    for name,pos in [("start",lo),("term",hi),("word",ix),("preceding",max(0,lo-2))]:
      val=struct.pack("<I",ram+pos)
      hits=[];at=arm.find(val)
      while at>=0 and len(hits)<50:
        hits.append(at+start)
        at=arm.find(val,at+1)
      print("PTR",off,name,hex(ram+pos),"hits",len(hits),hits[:35])
  counts=[]
  for rel in range(0,size-4096,512):
    seg=arm[rel:rel+4096]
    if all(c in (0,255) for c in seg):
      counts.append((rel+start,4096))
  print("EMPTY_BLOCKS",counts[-12:])
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--rom",type=Path,required=True);a=p.parse_args()
 scan(a.rom.read_bytes())
