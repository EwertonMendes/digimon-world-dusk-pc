"""ROM-free visual invariants for all original Dusk Digivice hover frames."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from dusk_icon_pixel_guard import original_icon_pixels,assert_icon_pixels_intact


def sprite_view(color,english=False):
    mapping={}
    for y in range(64):
        for x in range(64):
            index=2
            if 40<=x<48 and 19<=y<27:
                index=color
            elif english and 45<=x<49 and y==28:
                index=14
            mapping[x,y]=(0,False,index,0)
    return SimpleNamespace(size=(64,64),mapping=mapping)


class OriginalAnimationMaskTests(unittest.TestCase):
    def test_flash_green_and_white_are_preserved_from_all_frames(self):
        views=[sprite_view(c) for c in (4,6,14,15)]
        mask=original_icon_pixels(views,479)
        self.assertIn((43,22),mask)
        self.assertIn((40,18),mask)
        bad=sprite_view(15)
        bad.mapping[(43,22)]=(0,False,2,0)
        with self.assertRaisesRegex(ValueError,"clipped original"):
            assert_icon_pixels_intact(views[-1],bad,479,3,mask)

    def test_static_original_english_caption_is_not_icon(self):
        views=[sprite_view(c,True) for c in (4,6,14,15)]
        mask=original_icon_pixels(views,482)
        self.assertIn((44,26),mask)
        self.assertNotIn((46,28),mask)

    def test_all_four_original_frames_are_unchanged(self):
        views=[sprite_view(c) for c in (4,6,14,15)]
        mask=original_icon_pixels(views,480)
        for cell,view in enumerate(views):
            assert_icon_pixels_intact(view,sprite_view((4,6,14,15)[cell]),480,cell,mask)


if __name__=="__main__":
    unittest.main()
