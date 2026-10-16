"""Pure tests for audited Nintendo title prompt artwork geometry and style."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from dusk_native_title_prompt import make_title_pixels, source_glyphs, TARGET, SPANS

def source():
    plane=[[0]*104 for _ in range(16)]
    for a,b in SPANS:
        for y in range(3,13):
            for x in range(a,b):
                plane[y][x]=8 if y in (4,5,7) else (5 if y<10 else 3)
    return plane

class NativeTitleArtTests(unittest.TestCase):
    def test_all_portuguese_letters_covered(self):
        glyphs=source_glyphs(source())
        self.assertTrue(set(TARGET.replace(" ","")).issubset(glyphs))
        self.assertEqual(len(glyphs["E"][1]),len(set(glyphs["E"][1])))

    def test_native_canvas_and_palette_bounds(self):
        pix,stats=make_title_pixels(source())
        self.assertEqual(len(pix),16)
        self.assertTrue(all(len(r)==104 for r in pix))
        self.assertEqual(stats["glyph_count"],11)
        self.assertLessEqual(stats["rendered_width"],102)
        self.assertTrue(all(v in range(9) for row in pix for v in row))
        self.assertTrue(all(v==0 for v in pix[0]+pix[15]))
        self.assertTrue(all(pix[y][0]==0 and pix[y][-1]==0 for y in range(16)))

    def test_unsupported_prompt_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"only audited"):
            make_title_pixels(source(),"PUSH START")

    def test_missing_original_glyph_data_fails(self):
        with self.assertRaisesRegex(ValueError,"source font"):
            source_glyphs([[0]*104 for _ in range(16)])

if __name__=="__main__":
    unittest.main()
