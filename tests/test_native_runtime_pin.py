"""ROM-free guarantees for safe cosmetic repacking of a compiled game."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from native_runtime_pin import PIN_INPUTS, runtime_fingerprint, verified_pin


class RuntimePinTests(unittest.TestCase):
    def make_source(self, root):
        for name in PIN_INPUTS:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"stable")
        patch = root / "tools/patches/sdl.patch"
        patch.parent.mkdir(parents=True, exist_ok=True)
        patch.write_bytes(b"original native patch")
        return patch

    def test_cosmetic_asset_is_safe_but_native_change_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patch = self.make_source(root)
            digest = runtime_fingerprint(root)
            new_art = root / "assets/splash/new.png"
            new_art.parent.mkdir(parents=True)
            new_art.write_bytes(b"updated splash picture")
            self.assertEqual(runtime_fingerprint(root), digest)
            pin = root / "runtime.json"
            pin.write_text(json.dumps({
                "run_id": 123, "artifact_id": 456,
                "artifact_digest": "sha256:" + "b" * 64,
                "artifact_name": "Digimon-World-Dusk-Recompiled-v0.25-Windows-NATIVE-GAME",
                "exe_filename": "Digimon-World-Dusk-Recompiled-v0.25-Windows.exe",
                "source_fingerprint": digest
            }))
            self.assertEqual(verified_pin(pin, root)["artifact_id"], 456)
            patch.write_bytes(b"changed native patch")
            with self.assertRaisesRegex(ValueError, "Native sources changed"):
                verified_pin(pin, root)

    def test_windows_crlf_checkout_matches_linux_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patch = self.make_source(root)
            source = root / PIN_INPUTS[0]
            source.write_bytes(b"one\ntwo\n")
            patch.write_bytes(b"minus\nplus\n")
            linux_hash = runtime_fingerprint(root)
            source.write_bytes(b"one\r\ntwo\r\n")
            patch.write_bytes(b"minus\r\nplus\r\n")
            self.assertEqual(runtime_fingerprint(root), linux_hash)
            patch.write_bytes(b"minus\r\nchanged\r\n")
            self.assertNotEqual(runtime_fingerprint(root), linux_hash)

    def test_missing_native_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                runtime_fingerprint(Path(tmp))


if __name__ == "__main__":
    unittest.main()
