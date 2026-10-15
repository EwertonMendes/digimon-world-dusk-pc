#!/usr/bin/env python3
"""Audit source/translated message coverage without mistaking a smoke test for 100%.

Parses all MSG.PAK indexed records in the authenticated Dusk USA cartridge;
checks validity of locale keys and reports per-group counts, controls and gaps.
Does not export the game's English dialogue text.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,struct
from pathlib import Path
from probe_dusk_strings import files,SHA256,u16,u32

ROOT=Path(__file__).resolve().parents[1]
def build(rom:bytes)->dict:
    if hashlib.sha256(rom).hexdigest()!=SHA256:
        raise ValueError("source ROM mismatch")
    catalog=files(rom)
    fid,lo,hi=catalog["dat/MSG.PAK"]
    if fid!=23 or u32(rom,lo)!=138:raise ValueError("unknown MSG.PAK index")
    groups=[]
    for g in range(138):
        off=u32(rom,lo+4+g*8)
        size=u32(rom,lo+8+g*8)&0x7fffffff
        base=lo+off
        count_size=u32(rom,base)
        if count_size<4 or count_size%4 or count_size>size:
            raise ValueError(f"malformed pointer index group {g}")
        n=count_size//4
        offsets=[u32(rom,base+i*4) for i in range(n)]+[size]
        if offsets[0]!=count_size or offsets!=sorted(offsets) or any(x>size for x in offsets):
            raise ValueError(f"malformed source offsets group {g}")
        groups.append({"id":g,"messages":n})
    all_ids={f"{g['id']}/{i}" for g in groups for i in range(g["messages"])}
    stats={}
    for path in sorted((ROOT/"translations/msgpak").glob("*.json")):
        doc=json.loads(path.read_text("utf-8"))
        locale=doc["language"]
        active=set(doc["messages"])
        unknown=active-all_ids
        if unknown:raise ValueError(f"{locale} unknown IDs: {sorted(unknown)[:10]}")
        missing=len(all_ids-active)
        stats[locale]={"translated_ids":len(active),"untranslated_ids":missing,
                       "coverage_percent":round(len(active)*100/len(all_ids),3),
                       "untranslated_per_group":[{"group":g["id"],"remaining":sum(f"{g['id']}/{i}" not in active for i in range(g["messages"]))}
                                                for g in groups if any(f"{g['id']}/{i}" not in active for i in range(g["messages"]))]}
    return {"source_sha256":SHA256,"total_groups":len(groups),"total_message_ids":len(all_ids),
            "locales":stats,"note":"MSG.PAK only; ARM9, overlays and graphics not included in coverage denominator"}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    report=build(args.rom.read_bytes())
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+"\n","utf-8")
    for language,s in report["locales"].items():
        print(f"{language}: {s['translated_ids']}/{report['total_message_ids']} IDs = {s['coverage_percent']}% of MSG.PAK")
    print("Groups:",len(groups) if False else report["total_groups"])
