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
                "run_id": 123,
                "artifact_name": "Digimon-World-Dusk-Recompiled-v0.25-Windows-NATIVE-GAME",
                "exe_filename": "Digimon-World-Dusk-Recompiled-v0.25-Windows.exe",
                "exe_sha256": "a" * 64, "source_fingerprint": digest
            }))
            self.assertEqual(verified_pin(pin, root)["run_id"], 123)
            patch.write_bytes(b"changed native patch")
            with self.assertRaisesRegex(ValueError, "Native sources changed"):
                verified_pin(pin, root)

    def test_missing_native_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                runtime_fingerprint(Path(tmp))


if __name__ == "__main__":
    unittest.main()
