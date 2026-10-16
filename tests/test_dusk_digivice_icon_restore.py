"""Synthetic regression checks for the reconstructed native Digivice base."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from dusk_digivice_icon_restore import restored_digivice_pixels

class RestoreDigiviceTests(unittest.TestCase):
    def setUp(self):
        self.view=SimpleNamespace(size=(64,64))
        self.original={(53,y) for y in range(22,31)} | {(54,y) for y in range(23,30)}

    def test_rebuild_missing_lower_shell_in_all_four_original_frames(self):
        for frame in range(4):
            rebuilt=restored_digivice_pixels(self.view,frame,self.original)
            self.assertGreaterEqual(len(rebuilt),40)
            self.assertTrue(any(y==31 for x,y in rebuilt))
            self.assertTrue(any(y==24 for x,y in rebuilt))
            self.assertTrue(set(rebuilt).isdisjoint(self.original))
            self.assertTrue(all(35<=x<=56 and 24<=y<=31 for x,y in rebuilt))

    def test_original_animated_colors_follow_hover_states(self):
        frames=[restored_digivice_pixels(self.view,n,self.original) for n in range(4)]
        self.assertTrue(any(frames[0][p]!=frames[1][p] for p in frames[0] if p in frames[1]))
        self.assertTrue(any(frames[1][p]!=frames[2][p] for p in frames[1] if p in frames[2]))
        self.assertEqual(frames[2],frames[3])

    def test_never_retouch_original_icon_core(self):
        block={(x,y) for x in range(33,61) for y in range(10,27)}
        restored=restored_digivice_pixels(self.view,2,block)
        self.assertFalse(set(restored)&block)
        self.assertTrue(restored)

    def test_fail_if_original_mask_has_no_valid_base_room(self):
        mask={(x,y) for y in range(24,32) for x in range(35,57)}
        with self.assertRaisesRegex(ValueError,"reconstructable"):
            restored_digivice_pixels(self.view,0,mask)

if __name__=="__main__":
    unittest.main()
