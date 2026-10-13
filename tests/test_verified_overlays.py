"""ROM-free tests of multiple live overlay generations occupying the same RAM."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import random
import struct
import sys
import tempfile
import tomllib
import unittest

TOOLS=Path(__file__).resolve().parents[1]/"tools"
sys.path.insert(0,str(TOOLS))
from derive_verified_overlays import verified_overlay_roots,activate_verified_overlays


def fixture():
    random_source=random.Random(104)
    image0=random_source.randbytes(2*4096)
    image1=random_source.randbytes(2*4096)
    raw=bytearray(0x30000)
    # Valid header binaries are not required for overlay extraction.
    struct.pack_into("<II",raw,0x50,0x1800,64)
    struct.pack_into("<II",raw,0x48,0x2000,16)
    for i,(payload,pos) in enumerate(((image0,0x20000),(image1,0x22000))):
        raw[pos:pos+len(payload)]=payload
        struct.pack_into("<2I",raw,0x2000+8*i,pos,pos+len(payload))
        struct.pack_into("<8I",raw,0x1800+32*i,i,0x022A4000,len(payload),0,0,0,i,0)
    rom=bytes(raw)
    cover={"kind":"ndsrecomp-tier3-coverage",
           "rom_sha1":hashlib.sha1(rom).hexdigest(),
           "pages":{"entries":[]},"entry_points_arm9":[
             {"addr":"0x022A4010","mode":"arm","hits":100},
             {"addr":"0x022A5050","mode":"thumb","hits":10}],
           "entry_points_arm7":[]}
    for src in (image0,image1):
        page=src[:4096]
        cover["pages"]["entries"].append({
          "cpu":9,"addr":"0x022A4000","sha1":hashlib.sha1(page).hexdigest(),
          "data":base64.b64encode(page).decode("ascii")})
    return rom,cover,(image0,image1)


class VerifiedOverlayTests(unittest.TestCase):
    def test_overlapping_generations_remain_distinct(self):
        rom,cover,_=fixture()
        proof=verified_overlay_roots(rom,cover)
        self.assertEqual(len(proof),2)
        self.assertEqual([p["bank"] for p in proof],["dusk_arm9_ovl00","dusk_arm9_ovl01"])
        self.assertEqual([len(p["roots"]) for p in proof],[1,1])
        self.assertEqual([p["roots"][0]["addr"] for p in proof],["0x022A4010"]*2)
        self.assertNotEqual(proof[0]["source_sha1"],proof[1]["source_sha1"])

    def test_activator_replaces_unverified_load_entry_and_keeps_image_identity(self):
        rom,cover,blobs=fixture()
        proof=verified_overlay_roots(rom,cover)
        manifest={"banks":[]}
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for i,item in enumerate(proof):
                name=item["bank"]
                (folder/f"{name}.bin").write_bytes(blobs[i])
                (folder/f"{name}.toml").write_text(
                    f'[program]\nname = "{name}"\nid = "{name}"\n'
                    f'cpu = "arm9"\nload_address = {item["load_address"]}\n'
                    f'entry_pc = {item["load_address"]}\n'
                    f'[identity]\nsha1 = "{item["source_sha1"]}"\n')
                manifest["banks"].append({"bank":name,"cpu":"arm9","verifiedEntry":False})
            activate_verified_overlays(folder,manifest,proof)
            for bank in manifest["banks"]:
                self.assertTrue(bank["verifiedEntry"])
                config=tomllib.loads((folder/f'{bank["bank"]}.toml').read_text())
                self.assertEqual(config["program"]["entry_pc"],0x022A4010)
                self.assertEqual(len(config["entry_point"]),1)
            with self.assertRaises(ValueError):
                activate_verified_overlays(folder,manifest,proof)

    def test_tampered_page_not_activated(self):
        rom,cover,_=fixture()
        cover["pages"]["entries"][0]["sha1"]="0"*40
        with self.assertRaises(ValueError):
            verified_overlay_roots(rom,cover)


if __name__=="__main__":
    unittest.main(verbosity=2)
