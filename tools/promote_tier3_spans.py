#!/usr/bin/env python3
"""Promote the *actual* hottest interpreted spans into private guarded AOT banks.

Consumes interpreted-ranges.json from the pinned upstream
tools/ingest_coverage_manifests.py, NOT guessed call roots. Span starts are
accepted only when a captured full 4KiB RAM page contained that ARM/Thumb
instruction and matches the exact original ROM bank bytes at its live address.

Use private copies of the ROM and verified stage. Never commit output banks.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tomllib

PAGE = 4096
ROM_SHA256 = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"
ROM_SHA1 = "de1a1915e07288ffad654f3f9f2eb730a0fd1d9c"


def bitmap_has_root(page: dict, pc: int, mode: str) -> bool:
    """Only a generation-bound ROOT bit authorizes a candidate entry."""
    if mode not in ("arm", "thumb"):
        return False
    start = int(page["addr"], 16)
    width = 4 if mode == "arm" else 2
    if not start <= pc < start + PAGE or pc % width:
        return False
    bit = (pc - start) // width
    raw = base64.b64decode(page.get("root_" + mode, ""), validate=True)
    if bit // 8 >= len(raw):
        return False
    return bool(raw[bit // 8] & (1 << (bit % 8)))


def load_pages(manifests: list[Path], rom_sha1: str) -> dict[tuple[int,int], list[tuple[dict,bytes]]]:
    pages: dict[tuple[int,int], list[tuple[dict,bytes]]] = {}
    seen: dict[tuple[int,int,str], dict] = {}
    for path in manifests:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("kind") != "ndsrecomp-tier3-coverage" or doc.get("rom_sha1") != rom_sha1:
            raise ValueError(f"Unexpected cartridge/manifest: {path}")
        if doc.get("schema") != 4 or int(doc["pages"].get("page_size",PAGE)) != PAGE:
            raise ValueError("Expected generation-bound schema-4 4-KiB pages")
        for page in doc["pages"]["entries"]:
            cpu = page["cpu"]
            base = int(page["addr"], 16)
            raw = base64.b64decode(page["data"], validate=True)
            digest = hashlib.sha1(raw).hexdigest()
            if cpu not in (7,9) or base % PAGE or len(raw) != PAGE or page.get("sha1") != digest:
                raise ValueError(f"Invalid private page digest/cpu/size: {path} 0x{base:x}")
            key = (cpu,base,digest)
            # A byte-identical page generation may appear in several sessions
            # with DIFFERENT root bitmaps. Union only roots of that same
            # (CPU, RAM address, complete-page SHA1) generation; never union
            # different overlay contents merely because addresses match.
            normalized=dict(page)
            for mode,expected_bytes in (("arm",PAGE//4//8),("thumb",PAGE//2//8)):
                field="root_"+mode
                bits=base64.b64decode(page.get(field,""),validate=True)
                if len(bits)>expected_bytes:
                    raise ValueError(f"Invalid {field} bitmap size: {path} 0x{base:x}")
                normalized[field]=base64.b64encode(
                    bits.ljust(expected_bytes,b"\x00")
                ).decode("ascii")
            if key not in seen:
                seen[key]=normalized
                pages.setdefault((cpu,base),[]).append((normalized,raw))
            else:
                current=seen[key]
                for mode in ("arm","thumb"):
                    field="root_"+mode
                    a=base64.b64decode(current[field],validate=True)
                    b=base64.b64decode(normalized[field],validate=True)
                    current[field]=base64.b64encode(
                        bytes(x|y for x,y in zip(a,b))
                    ).decode("ascii")
    return pages


def stage_banks(stage: Path) -> list[dict]:
    banks=[]
    for path in sorted(stage.glob("dusk_arm*.toml")):
        doc=tomllib.loads(path.read_text(encoding="utf-8"))
        if "program" not in doc or "identity" not in doc:
            continue
        cfg=doc["program"]
        if cfg["cpu"] not in ("arm9","arm7") or cfg["name"] != path.stem:
            continue
        image=(stage / (path.stem+".bin")).read_bytes()
        if len(image) != int(cfg["size"]) or hashlib.sha1(image).hexdigest() != doc["identity"]["sha1"]:
            raise ValueError(f"Stage image identity mismatch: {path.name}")
        banks.append({"name":path.stem,"cpu":int(cfg["cpu"][-1]),
                      "base":int(cfg["load_address"]),"config":doc,
                      "source":path,"image":image})
    if not banks:
        raise ValueError("No valid private game banks")
    return banks


def image_offset(bank: dict, pc: int) -> int | None:
    """Map runtime PC into original image; handle verified ARM7 code_copy."""
    if bank["base"] <= pc < bank["base"] + len(bank["image"]):
        return pc - bank["base"]
    for c in bank["config"].get("code_copy",[]):
        begin=int(c["runtime_start"])
        length=int(c["size"])
        if begin <= pc < begin+length:
            return int(c["source_start"]) - bank["base"] + (pc-begin)
    return None


def prove_entry(bank: dict, pc: int, mode: str,
                pages: dict[tuple[int,int],list[tuple[dict,bytes]]]) -> bool:
    offset=image_offset(bank,pc)
    if offset is None:
        return False
    root_page=pc & ~(PAGE-1)
    for record,ram in pages.get((bank["cpu"],root_page),[]):
        if not bitmap_has_root(record,pc,mode):
            continue
        page_delta=pc-root_page
        source_at_page=offset-page_delta
        if source_at_page < 0 or source_at_page+PAGE > len(bank["image"]):
            continue
        if ram == bank["image"][source_at_page:source_at_page+PAGE]:
            return True
    return False


def promote(hot: dict, banks: list[dict], pages: dict, owned: dict[int,set],
            max_per_cpu: int = 48, max_per_bank: int = 24,
            min_hits: int = 100) -> dict:
    if min_hits < 1 or max_per_cpu < 1 or max_per_bank < 1:
        raise ValueError("Seed budgets must be positive")
    registry = {b["name"]:[] for b in banks}
    existing={}
    for bank in banks:
        existing[bank["name"]] = {
            (int(e["addr"]),e["mode"]) for e in bank["config"].get("entry_point",[])
        }
    report={"accepted":[], "rejected":{}, "total_sampled_entries":0}
    cpu_used={7:0,9:0}
    def reject(reason):
        report["rejected"][reason] = report["rejected"].get(reason,0)+1
    for cpu in (9,7):
        for span in hot.get(f"arm{cpu}", []):
            pc=int(span["start"],16)
            mode=span["mode"]
            hits=int(span["entries"])
            report["total_sampled_entries"]+=hits
            if hits < min_hits:
                reject("below_threshold");continue
            if cpu_used[cpu]>=max_per_cpu:
                reject("cpu_budget");continue
            if (pc,1 if mode=="thumb" else 0) in owned.get(cpu,set()):
                reject("already_native_dispatch");continue
            viable=[b for b in banks if b["cpu"]==cpu and prove_entry(b,pc,mode,pages)]
            if not viable:
                reject("no_generation_bound_rom_proof");continue
            accepted_here=False
            for bank in viable:
                name=bank["name"]
                if (pc,mode) in existing[name]:
                    continue
                if len(registry[name]) >= max_per_bank:
                    reject("bank_budget");continue
                if any(e["addr"]==pc and e["mode"]==mode for e in registry[name]):
                    continue
                registry[name].append({"addr":pc,"mode":mode,"hits":hits})
                accepted_here=True
            if accepted_here:
                cpu_used[cpu]+=1
                report["accepted"].append({"pc":f"0x{pc:08X}","mode":mode,
                                           "hits":hits,"banks":[b["name"] for b in viable]})
            else:
                reject("already_seeded_or_bank_budget")
    report["selected_by_bank"]={k:len(v) for k,v in registry.items() if v}
    report["selected_by_cpu"]=cpu_used
    report["seeds"]=registry
    return report


def write_private_stage(original: Path, destination: Path, report: dict) -> None:
    if destination.exists():
        raise FileExistsError(f"Cannot overwrite private stage: {destination}")
    destination.mkdir(parents=True)
    for bank, seeds in report["seeds"].items():
        if not seeds:continue
        path=original/(bank+".toml")
        text=path.read_text(encoding="utf-8")
        known=tomllib.loads(text)
        existing={(int(e["addr"]),e["mode"]) for e in known.get("entry_point",[])}
        chunks=["\n# Full 4-KiB RAM generation proven Tier3 interpreted span START seeds."]
        for e in seeds:
            key=(e["addr"],e["mode"])
            if key in existing:
                raise ValueError(f"Duplicate private seed {bank} {key}")
            chunks.extend(["", "[[entry_point]]",f'addr = 0x{e["addr"]:08X}',
                           f'mode = "{e["mode"]}"',
                           f'name = "tier3_span_{e["mode"]}_{e["addr"]:08x}"'])
        updated=text+"\n".join(chunks)+"\n"
        tomllib.loads(updated)
        (destination/(bank+".toml")).write_text(updated,encoding="utf-8")
        shutil.copyfile(original/(bank+".bin"), destination/(bank+".bin"))
    (destination/"span-promotion-report.json").write_text(
        json.dumps({k:v for k,v in report.items() if k!="seeds"},indent=2)+"\n",
        encoding="utf-8")


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rom",type=Path,required=True)
    ap.add_argument("--ingest",type=Path,required=True,
                    help="Result dir from upstream ingester with owned rows and ROM aliases")
    ap.add_argument("--stage",type=Path,required=True)
    ap.add_argument("--coverage",type=Path,nargs="+",required=True)
    ap.add_argument("--dispatch-arm9",type=Path,nargs="+",required=True)
    ap.add_argument("--dispatch-arm7",type=Path,nargs="+",required=True)
    ap.add_argument("--upstream",type=Path,required=True,
                    help="Pinned NDSRecomp source root; imports its original dispatch-row parser")
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--max-per-cpu",type=int,default=48)
    ap.add_argument("--max-per-bank",type=int,default=24)
    ap.add_argument("--min-hits",type=int,default=100)
    args=ap.parse_args()
    raw=args.rom.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ROM_SHA256 or hashlib.sha1(raw).hexdigest()!=ROM_SHA1:
        ap.error("Exact Dusk USA ROM identity required")
    import sys
    sys.path.insert(0,str(args.upstream/"tools"))
    from ingest_coverage_manifests import read_dispatch_rows
    ingest=json.loads((args.ingest/"ingest-report.json").read_text())
    if ingest["rom_sha1"]!=ROM_SHA1 or ingest["manifests_accepted"]!=len(args.coverage) or ingest["manifests_incomplete"]:
        ap.error("Ingest evidence incomplete or incompatible")
    hot=json.loads((args.ingest/"interpreted-ranges.json").read_text())
    owned={9:read_dispatch_rows(args.dispatch_arm9),7:read_dispatch_rows(args.dispatch_arm7)}
    if not all(owned.values()):
        ap.error("Missing native dispatch baseline for one CPU")
    pages=load_pages(args.coverage,ROM_SHA1)
    banks=stage_banks(args.stage)
    report=promote(hot,banks,pages,owned,args.max_per_cpu,args.max_per_bank,args.min_hits)
    write_private_stage(args.stage,args.out,report)
    print(json.dumps({k:v for k,v in report.items() if k!="seeds"},indent=2))


if __name__=="__main__":
    main()
