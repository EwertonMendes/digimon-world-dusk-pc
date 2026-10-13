"""ROM-free full-page safety and runtime-span promotion tests."""
import base64
import hashlib
from pathlib import Path
import tempfile
import tomllib
import unittest

from importlib.util import spec_from_file_location, module_from_spec
spec=spec_from_file_location("tier3",Path(__file__).resolve().parents[1]/"tools"/"promote_tier3_spans.py")
tier3=module_from_spec(spec)
spec.loader.exec_module(tier3)

BASE=0x02010000

def page(cpu, addr, body, root_addr, mode="arm"):
    stride=4 if mode=="arm" else 2
    raw=bytearray((tier3.PAGE//stride+7)//8)
    idx=(root_addr-addr)//stride
    raw[idx//8]|=1<<(idx%8)
    return ({
        "cpu":cpu,"addr":f"0x{addr:08X}",
        "sha1":hashlib.sha1(body).hexdigest(),
        "data":base64.b64encode(body).decode(),
        "root_"+mode:base64.b64encode(raw).decode()
    },body)

def bank(cpu, image, name="dusk_arm9_main", base=BASE, copies=None):
    return {"name":name,"cpu":cpu,"base":base,"image":image,
            "config":{"entry_point":[],"code_copy":copies or []}}

def window(pc,mode="arm",hits=100_000):
    return {"start":f"0x{pc:08X}","end":f"0x{pc+128:08X}",
            "mode":mode,"entries":hits,"bytes":128}

class Tier3SpanTests(unittest.TestCase):
    def test_native_known_page_promotes_one_seed(self):
        content=bytes((i*19)%256 for i in range(8192))
        b=bank(9,content)
        p=page(9,BASE,content[:4096],BASE+64)
        result=tier3.promote({"arm9":[window(BASE+64)]},[b],
            {(9,BASE):[p]}, {9:set(),7:set()},max_per_cpu=4)
        self.assertEqual(result["selected_by_bank"][b["name"]],1)
        self.assertEqual(result["seeds"][b["name"]][0]["addr"],BASE+64)

    def test_rejects_wrong_generation_and_missing_root(self):
        content=b"\x00"*8192
        b=bank(9,content)
        bad=page(9,BASE,b"\x01"*4096,BASE+64)
        out=tier3.promote({"arm9":[window(BASE+64)]},[b],
            {(9,BASE):[bad]}, {9:set(),7:set()})
        self.assertEqual(out["selected_by_bank"],{})
        good=page(9,BASE,content[:4096],BASE+80)
        out=tier3.promote({"arm9":[window(BASE+64)]},[b],
            {(9,BASE):[good]}, {9:set(),7:set()})
        self.assertEqual(out["selected_by_bank"],{})

    def test_never_repromotes_owned_dispatch_rows(self):
        content=b"\x27"*8192
        b=bank(9,content)
        p=page(9,BASE,content[:4096],BASE+64)
        out=tier3.promote({"arm9":[window(BASE+64)]},[b],
            {(9,BASE):[p]}, {9:{(BASE+64,0)},7:set()})
        self.assertEqual(out["selected_by_bank"],{})
        self.assertEqual(out["rejected"]["already_native_dispatch"],1)

    def test_handles_relocated_arm7_copies_only_with_matching_bytes(self):
        src=b"\xAB"*8192
        addr=0x037F9000
        b=bank(7,src,name="dusk_arm7_main",base=0x02380000,
               copies=[{"runtime_start":addr,"source_start":0x02380000,
                        "size":4096}])
        p=page(7,addr,src[:4096],addr+128)
        out=tier3.promote({"arm7":[window(addr+128)]},[b],
            {(7,addr):[p]}, {9:set(),7:set()})
        self.assertEqual(out["selected_by_bank"]["dusk_arm7_main"],1)

    def test_same_page_generation_unions_roots_across_sessions(self):
        import json
        content=bytes((i*7)%256 for i in range(8192))
        a,_=page(9,BASE,content[:4096],BASE+64)
        b,_=page(9,BASE,content[:4096],BASE+128)
        sample=lambda p: {
            "schema":4,"kind":"ndsrecomp-tier3-coverage",
            "rom_sha1":"a"*40,
            "pages":{"page_size":4096,"entries":[p]}
        }
        with tempfile.TemporaryDirectory() as temp:
            x=Path(temp)/"a.json"
            y=Path(temp)/"b.json"
            x.write_text(json.dumps(sample(a)))
            y.write_text(json.dumps(sample(b)))
            grouped=tier3.load_pages([x,y],"a"*40)
        self.assertEqual(len(grouped[(9,BASE)]),1)
        roots=grouped[(9,BASE)][0][0]
        self.assertTrue(tier3.bitmap_has_root(roots,BASE+64,"arm"))
        self.assertTrue(tier3.bitmap_has_root(roots,BASE+128,"arm"))
        both=tier3.promote(
            {"arm9":[window(BASE+64),window(BASE+128)]},
            [bank(9,content)],grouped,{9:set(),7:set()})
        self.assertEqual(both["selected_by_bank"]["dusk_arm9_main"],2)

    def test_different_code_at_same_address_never_shares_roots(self):
        import json
        one=b"A"*8192
        two=b"B"*8192
        a,_=page(9,BASE,one[:4096],BASE+64)
        b,_=page(9,BASE,two[:4096],BASE+128)
        sample=lambda p: {
            "schema":4,"kind":"ndsrecomp-tier3-coverage",
            "rom_sha1":"a"*40,
            "pages":{"page_size":4096,"entries":[p]}
        }
        with tempfile.TemporaryDirectory() as temp:
            x=Path(temp)/"a.json"
            y=Path(temp)/"b.json"
            x.write_text(json.dumps(sample(a)))
            y.write_text(json.dumps(sample(b)))
            grouped=tier3.load_pages([x,y],"a"*40)
        self.assertEqual(len(grouped[(9,BASE)]),2)
        result=tier3.promote(
            {"arm9":[window(BASE+64),window(BASE+128)]},
            [bank(9,one)],grouped,{9:set(),7:set()})
        self.assertEqual(result["selected_by_bank"]["dusk_arm9_main"],1)
        self.assertEqual(result["seeds"]["dusk_arm9_main"][0]["addr"],BASE+64)

    def test_limits_budget_and_refuses_overwrite(self):
        image=b"X"*8192
        b=bank(9,image)
        roots=[BASE+64, BASE+128, BASE+192]
        pp=[]
        for r in roots:
            pp.append(page(9,BASE,image[:4096],r))
        report=tier3.promote({"arm9":[window(r,hits=1000) for r in roots]},[b],
                {(9,BASE):pp}, {9:set(),7:set()}, max_per_cpu=2)
        self.assertEqual(len(report["accepted"]),2)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"source";source.mkdir()
            (source/"dusk_arm9_main.toml").write_text(
                '[program]\nname = "dusk_arm9_main"\ncpu = "arm9"\n'
                "[identity]\nsha1 = \"x\"\n")
            (source/"dusk_arm9_main.bin").write_bytes(image)
            dest=Path(temp)/"new"
            tier3.write_private_stage(source,dest,report)
            parsed=tomllib.loads((dest/"dusk_arm9_main.toml").read_text())
            self.assertEqual(len(parsed["entry_point"]),2)
            with self.assertRaises(FileExistsError):
                tier3.write_private_stage(source,dest,report)

if __name__=="__main__":
    unittest.main()
