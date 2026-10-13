#!/usr/bin/env python3
"""ROM-free validation of the bank preparation contract with NDSRecomp."""
from __future__ import annotations
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import tomllib
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prepare_dusk_recomp",ROOT/"tools"/"prepare_dusk_recomp.py")
pipeline=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

class BankTests(unittest.TestCase):
    def test_arm9_config(self):
        image=struct.pack("<IIII",0xe3a00000,0xe12fff1e,0xe1a00000,0xe12fff1e)
        config=tomllib.loads(pipeline.bank_config("test_arm9","arm9",image,0x02000800,0x02000800))
        self.assertEqual(config["program"]["size"],len(image))
        self.assertEqual(config["program"]["isa"],"armv5te")
        self.assertEqual(config["identity"]["sha1"],hashlib.sha1(image).hexdigest())
        self.assertEqual(config["entry_point"][0]["mode"],"arm")

    def test_arm7_config(self):
        config=tomllib.loads(pipeline.bank_config("test_arm7","arm7",b"\\0"*16,0x2380000,0x2380000))
        self.assertEqual(config["program"]["isa"],"armv4t")

    def test_reject_unverified_or_malformed_input(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            rom=folder/"not-dusk.nds"
            rom.write_bytes(b"\\0"*512)
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                pipeline.prepare(rom,folder/"out")
        with self.assertRaises(ValueError):
            pipeline.bank_config("bad/path","arm9",b"\\0"*8,0,0)

    def test_git_safety(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/".git").mkdir()
            with self.assertRaisesRegex(ValueError,".private"):
                pipeline.safe_destination(root/"generated",root/"rom.nds")
            pipeline.safe_destination(root/".private"/"recomp",root/"rom.nds")

    def test_normalize_runner_shard_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"synthetic_arm9.c").write_text("/* generated */")
            (root/"synthetic_arm9_dispatch.c").write_text("/* generated */")
            pipeline.normalize_emission(root,"synthetic_arm9")
            self.assertTrue((root/"synthetic_arm9_00.c").is_file())
            self.assertFalse((root/"synthetic_arm9.c").exists())

    def test_recompiler_contract_with_own_synthetic_arm(self):
        exe=os.environ.get("NDS_RECOMPILER")
        if not exe:
            self.skipTest("NDS_RECOMPILER not set")
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            image=struct.pack("<4I",0xe3a00000,0xe12fff1e,0xe1a00000,0xe12fff1e)
            (root/"sample.bin").write_bytes(image)
            (root/"sample.toml").write_text(pipeline.bank_config(
                "synthetic_arm9","arm9",image,0x02000800,0x02000800))
            cmd=[exe,"--config",str(root/"sample.toml"),"--bin",str(root/"sample.bin")]
            subprocess.run(cmd+["--audit"],check=True)
            (root/"generated").mkdir()
            subprocess.run(cmd+["--out",str(root/"generated"),"--bank","synthetic_arm9","--shards","4"],check=True)
            pipeline.normalize_emission(root/"generated","synthetic_arm9")
            self.assertGreaterEqual(len(list((root/"generated").glob("synthetic_arm9_[0-9][0-9].c"))),1)\n            self.assertLessEqual(len(list((root/"generated").glob("synthetic_arm9_[0-9][0-9].c"))),4)
            self.assertTrue((root/"generated"/"synthetic_arm9_00.c").is_file())

if __name__=="__main__":
    unittest.main(verbosity=2)
