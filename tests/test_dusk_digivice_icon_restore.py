"""Regression checks for the subtle original-palette Digivice underside.

The opaque moving display is source-ROM artwork, not synthesized here.
Only a small dark-teal casing edge may be supplied under the removed
English 'Tamer' heading.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from dusk_digivice_icon_restore import restored_digivice_pixels


class RestoreDigiviceTests(unittest.TestCase):
    def setUp(self):
        self.view = SimpleNamespace(size=(64, 64))
        self.original = {(53, y) for y in range(22, 31)} | {
            (54, y) for y in range(23, 30)
        }

    def test_casing_repairs_only_native_obscured_underside(self):
        for frame in range(4):
            rebuilt = restored_digivice_pixels(self.view, frame, self.original)
            self.assertGreaterEqual(len(rebuilt), 8)
            self.assertTrue(any(y == 30 for x, y in rebuilt))
            self.assertTrue(any(y == 26 for x, y in rebuilt))
            self.assertTrue(set(rebuilt).isdisjoint(self.original))
            self.assertTrue(all(37 <= x <= 54 and 26 <= y <= 30
                                for x, y in rebuilt))

    def test_no_synthetic_white_green_or_bright_blinking_pixels(self):
        frames = [restored_digivice_pixels(self.view, n, self.original)
                  for n in range(4)]
        self.assertTrue(all(frame == frames[0] for frame in frames[1:]))
        self.assertTrue(all(color in (2, 3, 4, 9)
                            for color in frames[0].values()))

    def test_never_touch_original_animated_hardware(self):
        protected = {(x, y) for x in range(33, 61)
                     for y in range(10, 27)}
        restored = restored_digivice_pixels(self.view, 2, protected)
        self.assertFalse(set(restored) & protected)
        self.assertTrue(restored)

    def test_blocked_icon_pixels_reject_reconstruction(self):
        mask = {(x, y) for y in range(26, 31) for x in range(37, 55)}
        with self.assertRaisesRegex(ValueError, "safe underside"):
            restored_digivice_pixels(self.view, 0, mask)


if __name__ == "__main__":
    unittest.main()
