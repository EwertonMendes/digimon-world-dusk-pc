"""ROM-free regression coverage for the one-line native Treinador art."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from dusk_original_glyph_atlas import Glyph,TRAINER_PT_WIDTHS,layout_trainer_one_line


class TrainerOneLineTests(unittest.TestCase):
    def setUp(self):
        # Match the minimum foreground bounding-box widths recovered from
        # Dusk's original glyphs. Every glyph has a top and bottom highlight.
        self.word="Treinador"
        source_widths=[9,5,7,2,7,9,7,7,5]
        self.glyphs={}
        for char,width in zip(self.word,source_widths):
            self.glyphs[char]=Glyph(width,tuple(
                (x,y,13 if y in (0,10) else 14 if y in (1,9) else 15)
                for y in (0,1,5,9,10) for x in range(width)
            ))

    def test_single_native_row_never_exceeds_sprite_plate(self):
        pixels,width=layout_trainer_one_line(self.glyphs,49)
        self.assertEqual(width,49)
        self.assertTrue(pixels)
        self.assertTrue(all(0<=x<49 and 0<=y<11 for x,y in pixels))
        self.assertEqual({v for v in pixels.values()},{13,14,15})

    def test_every_letter_has_one_clear_separation_column(self):
        pixels,width=layout_trainer_one_line(self.glyphs,49)
        cursor=0
        for i,target in enumerate(TRAINER_PT_WIDTHS):
            self.assertTrue(any(cursor<=x<cursor+target for x,y in pixels))
            cursor+=target
            if i<len(TRAINER_PT_WIDTHS)-1:
                self.assertFalse(any(x==cursor for x,y in pixels))
                cursor+=1
        self.assertEqual(cursor,width)

    def test_reject_narrower_plate_instead_of_breaking_text(self):
        with self.assertRaisesRegex(ValueError,"available"):
            layout_trainer_one_line(self.glyphs,48)

    def test_reject_source_glyph_smaller_than_target(self):
        wrong=dict(self.glyphs)
        wrong["T"]=Glyph(2,((0,0,14),))
        with self.assertRaisesRegex(ValueError,"invalid width"):
            layout_trainer_one_line(wrong,49)


if __name__=="__main__":
    unittest.main()
