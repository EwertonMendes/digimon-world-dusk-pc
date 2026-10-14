"""ROM-free tests for byte-verified AOT root recovery."""
from pathlib import Path
import hashlib
import importlib.util
import json
import base64
import zlib
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

    def test_supplement_preserves_known_rom_pages_and_rejects_conflicts(self):
        with tempfile.TemporaryDirectory() as td:
            stage, image, overlay = self.make_stage(td)
            base = self.manifest(image, overlay)
            base["schema"] = 2
            base["code_copies"] = {}
            extra = {"schema":2,"rom_sha256":base["rom_sha256"],
                     "banks":{"dusk_arm9_main":[
                         dict(base["banks"]["dusk_arm9_main"][0]),
                         {"pc":"0x02001100","mode":"arm",
                          "page_sha1":base["banks"]["dusk_arm9_main"][0]["page_sha1"]}]},
                     "code_copies":{}}
            with patch.object(hot,"ROM_SHA256",base["rom_sha256"]):
                merged=hot.merge_safe_supplement(base,extra)
                self.assertEqual(len(merged["banks"]["dusk_arm9_main"]),2)
                self.assertEqual(len(base["banks"]["dusk_arm9_main"]),1)
                self.assertEqual(hot.recover(stage,merged,b"synthetic")["dusk_arm9_main"],2)
                bad=dict(extra)
                bad["banks"]={"dusk_arm9_main":[
                    dict(extra["banks"]["dusk_arm9_main"][0],
                         page_sha1="0"*40)]}
                with self.assertRaisesRegex(ValueError,"Conflicting"):
                    hot.merge_safe_supplement(base,bad)

    def test_compressed_expanded_owner_schema_two_is_loaded(self):
        with tempfile.TemporaryDirectory() as td:
            stage, image, overlay = self.make_stage(td)
            payload = self.manifest(image, overlay)
            payload["schema"] = 2
            payload["code_copies"] = {}
            file = Path(td) / "owner-proof.b64"
            file.write_bytes(base64.b64encode(
                zlib.compress(json.dumps(payload).encode("utf-8"))))
            self.assertEqual(hot.load_evidence(file), payload)
            with patch.object(hot, "ROM_SHA256", payload["rom_sha256"]):
                self.assertEqual(hot.recover(stage, hot.load_evidence(file),
                                             b"synthetic")["dusk_arm9_main"], 1)

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


    def test_compact_root_dictionary_and_arm7_copy_are_full_page_verified(self):
        import tomllib
        with tempfile.TemporaryDirectory() as td:
            stage = Path(td) / "stage"
            stage.mkdir()
            name = "dusk_arm7_main"
            original_base = 0x02380000
            runtime_base = 0x037F8000
            # As observed on the real title, the ARM7 code copy source is
            # *not* page-aligned relative to the original DS bank base.
            image = bytes(i % 251 for i in range(4 * 4096))
            (stage / (name + ".bin")).write_bytes(image)
            (stage / (name + ".toml")).write_text(
                bank_config(name, "arm7", image, original_base, original_base),
                encoding="utf-8")
            (stage / "manifest.json").write_text(json.dumps({"banks":[
                {"bank":name,"cpu":"arm7","verifiedEntry":True}]}))
            source_off = 0x1B0
            hashes = [
                hashlib.sha1(image[source_off + 4096 * i:
                                   source_off + 4096 * (i + 1)]).hexdigest()
                for i in range(2)
            ]
            compact = {"s": 3, "h": hashes,
                       "b": {name: [[runtime_base + 0x120, 0, 0, source_off]]},
                       "c": {name: [[runtime_base, original_base + source_off,
                                       8192, [0, 1]]]}}
            evidence = Path(td) / "owner-compact.b64"
            evidence.write_bytes(base64.b64encode(
                zlib.compress(json.dumps(compact).encode())))
            with patch.object(hot, "ROM_SHA256", hashlib.sha256(b"synthetic").hexdigest()):
                parsed = hot.load_evidence(evidence)
                self.assertEqual(parsed["schema"], 2)
                accepted = hot.recover(stage, parsed, b"synthetic")
            self.assertEqual(accepted, {name: 1})
            config = tomllib.loads((stage / (name + ".toml")).read_text())
            self.assertEqual(len(config["code_copy"]), 1)
            self.assertEqual(config["code_copy"][0]["runtime_start"], runtime_base)
            self.assertIn({"addr": runtime_base + 0x120, "mode": "arm",
                           "name": "verified_arm_037f8120"}, config["entry_point"])

    def test_relocated_page_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            stage = Path(td) / "stage"
            stage.mkdir()
            name = "dusk_arm7_main"
            b = 0x02380000
            image = bytes(i % 255 for i in range(16384))
            (stage/(name + ".bin")).write_bytes(image)
            (stage/(name + ".toml")).write_text(
                bank_config(name, "arm7", image, b, b))
            (stage/"manifest.json").write_text(json.dumps({"banks":[
                {"bank":name, "cpu":"arm7", "verifiedEntry":True}]}))
            # Missing/incorrect full-page relocation proof must never
            # install an executable candidate.
            evidence = {"schema": 2,
                "rom_sha256": hashlib.sha256(b"synthetic").hexdigest(),
                "banks": {name:[{"pc":"0x037F8120","mode":"arm",
                                 "page_sha1":"0"*40,
                                 "source_page_offset":"0x1B0"}]},
                "code_copies": {name:[{"runtime_start":"0x037F8000",
                    "source_start":"0x023801B0","size":8192,
                    "pages":["0"*40,"0"*40]}]}}
            original = (stage/(name + ".toml")).read_bytes()
            with patch.object(hot, "ROM_SHA256", evidence["rom_sha256"]):
                with self.assertRaisesRegex(ValueError, "differs"):
                    hot.recover(stage, evidence, b"synthetic")
            self.assertEqual(original,(stage/(name + ".toml")).read_bytes())


if __name__ == "__main__":
    unittest.main()
