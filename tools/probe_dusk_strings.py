#!/usr/bin/env python3
"""Read-only, exact-ROM Digimon Dusk MSG.PAK structural probe.

Outputs numeric metadata only; does not export text, ROM bytes, or resources.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA256="df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"

def u16(buf:bytes,off:int)->int:return struct.unpack_from("<H",buf,off)[0]
def u32(buf:bytes,off:int)->int:return struct.unpack_from("<I",buf,off)[0]
def files(rom:bytes)->dict[str,tuple[int,int,int]]:
    fnt,size=u32(rom,0x40),u32(rom,0x44)
    fat,fatsize=u32(rom,0x48),u32(rom,0x4c)
    if not (0<fnt<fnt+size<len(rom) and 0<fat<fat+fatsize<len(rom)) or fatsize%8:
        raise ValueError("invalid FNT/FAT")
    count=u16(rom,fnt+6)
    if count<1 or count>8192 or count*8>size:raise ValueError("invalid FNT directory count")
    output={}
    visited=set()
    def walk(did:int,parent:str):
        if did in visited:return
        visited.add(did)
        idx=did-0xf000
        if not 0<=idx<count:raise ValueError("invalid FNT directory id")
        nameoff,fileid=u32(rom,fnt+8*idx),u16(rom,fnt+8*idx+4)
        if not 0<=nameoff<size:raise ValueError("invalid FNT directory offset")
        pos=fnt+nameoff
        while True:
            if pos>=fnt+size:raise ValueError("FNT directory not terminated")
            b=rom[pos];pos+=1
            if not b:break
            length=b&0x7f
            if length==0 or pos+length>fnt+size:raise ValueError("FNT entry overflow")
            name=rom[pos:pos+length].decode("ascii");pos+=length
            if b&0x80:
                child=u16(rom,pos);pos+=2
                walk(child,parent+name+"/")
            else:
                if fileid>=fatsize//8:raise ValueError("file id outside FAT")
                lo,hi=u32(rom,fat+8*fileid),u32(rom,fat+8*fileid+4)
                if lo>hi or hi>len(rom):raise ValueError("FAT bounds invalid")
                output[parent+name]=(fileid,lo,hi)
                fileid+=1
    walk(0xf000,"")
    return output

def probe(rom:bytes)->dict:
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("unexpected ROM")
    catalog=files(rom)
    result={"files":len(catalog),"candidates":[]}
    for name,(fid,lo,hi) in catalog.items():
        if "msg" not in name.lower() and "text" not in name.lower():continue
        header=rom[lo:min(hi,lo+64)]
        sample=[u32(header,i) for i in range(0,len(header)-3,4)]
        n=sample[0] if sample else 0
        valid_table=n>0 and n<100000 and 4+n*8<=hi-lo
        result["candidates"].append({"name":name,"file_id":fid,"start":lo,"size":hi-lo,
          "prefix32":sample[:8], "table_candidate":valid_table})
    result["candidates"].sort(key=lambda x:x["size"],reverse=True)
    for item in result["candidates"]:
        if item["name"].lower()!="dat/msg.pak":continue
        lo=item["start"]; end=lo+item["size"]
        n=u32(rom,lo)
        if n!=138 or 4+8*n>item["size"]:raise ValueError("unexpected MSG.PAK index")
        entries=[]
        for i in range(n):
            p=lo+4+i*8
            off=u32(rom,p);sizeflag=u32(rom,p+4)
            size=sizeflag&0x7fffffff
            if off+size>item["size"]:raise ValueError("MSG.PAK entry beyond FAT")
            b=rom[lo+off:lo+off+min(size,64)]
            entry={"i":i,"start":off,"size":size,
                   "flag":int(bool(sizeflag&0x80000000))}
            if i<12:
                entry["first_u32"]=[u32(b,j) for j in range(0,min(32,len(b)-3),4)]
                entry["first_u16"]=[u16(b,j) for j in range(0,min(24,len(b)-1),2)]
            entries.append(entry)
        item["entry_count"]=n
        item["subfiles"]=entries[:12]
        item["flagged_count"]=sum(e["flag"] for e in entries)
        item["nonoverlapping"]=all(entries[i]["start"]+entries[i]["size"] <=
                                  entries[i+1]["start"] for i in range(n-1))
        break
    # Independent research places the MSG.PAK payload around 0x0117E970.
    # Report whether the first candidate has an 8-byte (offset,size) index.
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--rom",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    report=probe(args.rom.read_bytes())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
