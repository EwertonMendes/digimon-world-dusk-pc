"""ROM-free tests of live-page identity and safe relocation seed discovery."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import random
import struct
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("aot",Path(__file__).resolve().parents[1]/"tools"/"derive_verified_aot.py")
aot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(aot)


def fixture():
    rng=random.Random(27)
    arm9=rng.randbytes(6*4096)
    arm7=rng.randbytes(8*4096)
    rom=bytearray(0x30000)
    struct.pack_into("<4I",rom,0x20,0x4000,0x02000800,0x02000000,len(arm9))
    struct.pack_into("<4I",rom,0x30,0x10000,0x02380000,0x02380000,len(arm7))
    rom[0x4000:0x4000+len(arm9)]=arm9
    rom[0x10000:0x10000+len(arm7)]=arm7
    raw=bytes(rom)
    snapshot={"kind":"ndsrecomp-tier3-coverage","rom_sha1":hashlib.sha1(raw).hexdigest(),
              "pages":{"entries":[]},"entry_points_arm9":[],"entry_points_arm7":[]}

    def add(cpu,addr,data):
        snapshot["pages"]["entries"].append({
          "addr":f"0x{addr:08X}","cpu":cpu,"sha1":hashlib.sha1(data).hexdigest(),
          "data":base64.b64encode(data).decode("ascii")})

    add(9,0x02001000,arm9[4096:8192])
    # Three adjacent complete pages prove a unique, non-header runtime copy.
    copied_base=0x037F8000
    for n in range(3):
        add(7,copied_base+4096*n,arm7[4096*n:4096*(n+1)])
    snapshot["entry_points_arm9"]=[
        {"addr":"0x02001040","mode":"arm","hits":8},
        {"addr":"0x02003000","mode":"arm","hits":18}]
    snapshot["entry_points_arm7"]=[
        {"addr":"0x037F8040","mode":"arm","hits":333},
        {"addr":"0x037FA080","mode":"thumb","hits":23},
        {"addr":"0x037FD080","mode":"arm","hits":8}]
    return raw,snapshot


class VerifiedAOTTests(unittest.TestCase):
    def test_original_and_copied_regions(self):
        raw,snapshot=fixture()
        result=aot.derive(raw,snapshot)
        self.assertEqual(len(result["seeds"]["dusk_arm9_main"]),1)
        self.assertEqual(len(result["seeds"]["dusk_arm7_main"]),2)
        self.assertEqual(result["original_verified_pages"]["9"],1)
        self.assertEqual(result["copied_verified_pages"]["7"],3)
        self.assertEqual(len(result["code_copies"]),1)
        self.assertEqual(result["code_copies"][0]["size"],3*4096)
        self.assertEqual(result["skipped_roots"]["arm9_unverified_page"],1)

    def test_modified_page_never_seeds_native_code(self):
        raw,snapshot=fixture()
        entry=snapshot["pages"]["entries"][0]
        altered=bytearray(base64.b64decode(entry["data"]))
        altered[35]^=1
        entry["data"]=base64.b64encode(altered).decode()
        entry["sha1"]=hashlib.sha1(altered).hexdigest()
        result=aot.derive(raw,snapshot)
        self.assertEqual(result["seeds"]["dusk_arm9_main"],[])
        self.assertEqual(result["rejected_pages"]["arm9_modified_in_place"],1)

    def test_corrupted_snapshot_or_foreign_rom_fails_closed(self):
        raw,snapshot=fixture()
        snapshot["pages"]["entries"][0]["sha1"]="0"*40
        with self.assertRaises(ValueError):
            aot.derive(raw,snapshot)
        raw,snapshot=fixture()
        snapshot["rom_sha1"]="0"*40
        with self.assertRaisesRegex(ValueError,"SHA1"):
            aot.derive(raw,snapshot)

    def test_toml_updates_preserve_identity_and_are_not_repeatable(self):
        raw,snapshot=fixture()
        result=aot.derive(raw,snapshot)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for cpu in (9,7):
                bank=f"dusk_arm{cpu}_main"
                base,image=aot.images(raw)[cpu]
                (folder/f"{bank}.bin").write_bytes(image)
                (folder/f"{bank}.toml").write_text(
                    "[program]\n"
                    f'cpu = "arm{cpu}"\n'
                    f'load_address = {base}\n'
                    "[identity]\n"
                    f'sha1 = "{hashlib.sha1(image).hexdigest()}"\n')
            aot.apply_private_configs(folder,result)
            self.assertIn("[[code_copy]]",(folder/"dusk_arm7_main.toml").read_text())
            self.assertIn("[[entry_point]]",(folder/"dusk_arm9_main.toml").read_text())
            with self.assertRaises(ValueError):
                aot.apply_private_configs(folder,result)


if __name__=="__main__":
    unittest.main(verbosity=2)
