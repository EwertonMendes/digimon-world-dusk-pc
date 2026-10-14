"""ROM-free tests for byte-verified AOT root recovery."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import restore_verified_hotpaths as hot
from prepare_dusk_recomp import bank_config


class RecoveryContractTests(unittest.TestCase):
    def make_stage(self, home):
        stage = Path(home) / "stage"
        stage.mkdir()
        name = "dusk_arm9_main"
        base = 0x02000800
        image = bytes(i % 251 for i in range(12288))
        (stage / (name + ".bin")).write_bytes(image)
        (stage / (name + ".toml")).write_text(
            bank_config(name, "arm9", image, base, base), encoding="utf-8")
        name2 = "dusk_arm9_ovl00"
        overlay = bytes((i * 3 + 13) % 241 for i in range(8192))
        (stage / (name2 + ".bin")).write_bytes(overlay)
        (stage / (name2 + ".toml")).write_text(
            bank_config(name2, "arm9", overlay, 0x02200000, 0x02200000),
            encoding="utf-8")
        (stage / "manifest.json").write_text(json.dumps({"banks":[
            {"bank":name, "cpu":"arm9", "verifiedEntry":True},
            {"bank":name2, "cpu":"arm9", "verifiedEntry":False}
        ]}))
        return stage, image, overlay

    def manifest(self, image, overlay):
        return {"schema":1, "rom_sha256":hashlib.sha256(b"synthetic").hexdigest(),
                "banks":{
                    "dusk_arm9_main":[{"pc":"0x02001000","mode":"arm",
                                      "page_sha1":hashlib.sha1(image[2048:6144]).hexdigest()}],
                    "dusk_arm9_ovl00":[{"pc":"0x02201000","mode":"arm",
                                       "page_sha1":hashlib.sha1(overlay[4096:8192]).hexdigest()}],
                }}

    def test_matching_full_pages_activate_separate_overlay_bank(self):
        with tempfile.TemporaryDirectory() as td:
            stage, image, overlay = self.make_stage(td)
            manifest = self.manifest(image, overlay)
            with patch.object(hot, "ROM_SHA256", manifest["rom_sha256"]):
                report = hot.recover(stage, manifest, b"synthetic")
            self.assertEqual(report, {"dusk_arm9_main":1, "dusk_arm9_ovl00":1})
            self.assertTrue(json.loads((stage/"manifest.json").read_text())["banks"][1]["verifiedEntry"])
            self.assertIn("addr = 0x02201000", (stage/"dusk_arm9_ovl00.toml").read_text())

    def test_mismatched_generation_aborts_before_changing_any_bank(self):
        with tempfile.TemporaryDirectory() as td:
            stage, image, overlay = self.make_stage(td)
            manifest = self.manifest(image, overlay)
            manifest["banks"]["dusk_arm9_ovl00"][0]["page_sha1"] = "0"*40
            original=(stage/"dusk_arm9_main.toml").read_bytes()
            with patch.object(hot, "ROM_SHA256", manifest["rom_sha256"]):
                with self.assertRaisesRegex(ValueError, "disagrees"):
                    hot.recover(stage, manifest, b"synthetic")
            self.assertEqual(original,(stage/"dusk_arm9_main.toml").read_bytes())

    def test_proof_cannot_spoof_wrong_cpu_or_misaligned_mode(self):
        with tempfile.TemporaryDirectory() as td:
            stage, image, overlay = self.make_stage(td)
            manifest = self.manifest(image, overlay)
            manifest["banks"]["dusk_arm9_main"][0]["pc"] = "0x02001002"
            with patch.object(hot, "ROM_SHA256", manifest["rom_sha256"]):
                with self.assertRaisesRegex(ValueError, "Invalid root"):
                    hot.recover(stage, manifest, b"synthetic")


if __name__ == "__main__":
    unittest.main()
