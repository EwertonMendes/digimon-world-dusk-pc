"""ROM-free protection tests for private original in-game save replay."""
from __future__ import annotations
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from dusk_gameplay_scenarios import cartridge_fixture


class OriginalSaveFixtureTests(unittest.TestCase):
    def test_save_clone_is_exact_and_source_cannot_be_written_by_runner(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "owner.sav"
            data = bytes(range(256)) * 256
            self.assertEqual(len(data), 65536)
            source.write_bytes(data)
            args, digest = cartridge_fixture(source, root)
            flags = dict(zip(args[::2], args[1::2]))
            self.assertNotEqual(source, Path(flags["--save-path"]))
            self.assertEqual(Path(flags["--save-path"]).read_bytes(), data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
            self.assertEqual(source.read_bytes(), data)
            config = Path(flags["--config"]).read_text()
            self.assertIn('save_type = "eeprom"\n', config)
            self.assertIn('save_size = 65536\n', config)

    def test_invalid_save_size_fails_without_copy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "owner.sav"
            source.write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError, "65536"):
                cartridge_fixture(source, root)
            self.assertEqual(list(root.glob("cartridge-fixture-*")), [])

    def test_every_replay_uses_separate_copy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "owner.sav"
            original = b"x" * 65536
            source.write_bytes(original)
            a, _ = cartridge_fixture(source, root)
            b, _ = cartridge_fixture(source, root)
            copy1, copy2 = Path(a[1]), Path(b[1])
            self.assertNotEqual(copy1, copy2)
            copy1.write_bytes(b"y" * 65536)
            self.assertEqual(copy2.read_bytes(), original)
            self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
