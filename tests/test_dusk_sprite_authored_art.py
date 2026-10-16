"""ROM-free tests of authored native 4bpp sprite artwork import rules."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from dusk_sprite_inplace_editor import CellView
from dusk_sprite_authored_art import import_authored_art
import dusk_sprite_authored_art as importer

COLORS=[(0,0,0,255),(20,30,40,255),(255,255,255,255)]+[(0,0,0,255)]*13


def view(ncgr, _pal, _cel, cell):
    if cell not in (0,1):
        raise ValueError("unknown synthetic animation")
    im=Image.new("RGB",(8,8),(22,26,40))
    mapping={}
    for y in range(8):
        for x in range(8):
            off=y*4+x//2
            hi=bool(x%2)
            raw=ncgr[32+off]
            idx=(raw>>4 if hi else raw&15)
            if idx:
                im.putpixel((x,y),COLORS[idx][:3])
            mapping[x,y]=(off,hi,idx,0)
    return CellView((8,8),mapping,im)


class AuthoredArtTests(unittest.TestCase):
    def setUp(self):
        self.stack=tempfile.TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.root=Path(self.stack.name)
        self.original=b"x"*32 + bytes([0x11]*32)
        self.patches=[
            patch.object(importer,"graphics",return_value=(3,b"\x11"*32)),
            patch.object(importer,"palette",return_value=COLORS),
            patch.object(importer,"chunk",return_value=(0,64)),
            patch.object(importer,"extract_cell",side_effect=view),
            patch.object(importer,"get_cell_groups",return_value=([[]],2))
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def png(self, name="art.png",color=(255,255,255),pos=(2,3)):
        im=Image.new("RGB",(8,8),COLORS[1][:3])
        im.putpixel(pos,color)
        im.save(self.root/name)
        return name

    def run_import(self,filename="art.png",regions=None,cell=0):
        return import_authored_art(self.original,b"p",b"c",[
            {"cell":cell,"png":filename,"regions":regions or [[0,0,4,4]]}
        ],self.root)

    def test_import_single_pixel_without_metadata_changes(self):
        self.png()
        result=self.run_import()
        self.assertEqual(len(result),len(self.original))
        self.assertEqual(result[:32],self.original[:32])
        self.assertEqual(sum(a!=b for a,b in zip(result,self.original)),1)
        self.assertEqual(view(result,None,None,0).image.getpixel((2,3)),COLORS[2][:3])

    def test_original_transparent_palette_index_zero_roundtrip(self):
        self.png(color=(22,26,40))
        result=self.run_import()
        self.assertEqual(view(result,None,None,0).mapping[(2,3)][2],0)
        self.assertEqual(view(result,None,None,0).image.getpixel((2,3)),(22,26,40))

    def test_reject_icon_or_frame_pixels_outside_region(self):
        self.png(pos=(6,5))
        with self.assertRaisesRegex(ValueError,"icon/frame"):
            self.run_import()

    def test_reject_unmapped_rgb(self):
        self.png(color=(123,45,67))
        with self.assertRaisesRegex(ValueError,"NCLR"):
            self.run_import()

    def test_reject_wrong_image_size(self):
        Image.new("RGB",(7,8),COLORS[1][:3]).save(self.root/"art.png")
        with self.assertRaisesRegex(ValueError,"dimensions"):
            self.run_import()

    def test_reject_transparency(self):
        Image.new("RGBA",(8,8),(20,30,40,128)).save(self.root/"art.png")
        with self.assertRaisesRegex(ValueError,"alpha"):
            self.run_import()

    def test_reject_path_traversal(self):
        with self.assertRaisesRegex(ValueError,"escapes"):
            self.run_import("../art.png")

    def test_reject_unedited_animation_changes(self):
        self.png()
        with patch.object(importer,"get_cell_groups",return_value=([[],[]],2)):
            with self.assertRaisesRegex(ValueError,"animation 1"):
                self.run_import()

    def test_reject_two_shared_cell_conflicts(self):
        self.png(name="first.png",pos=(2,3))
        self.png(name="second.png",pos=(2,3),color=(0,0,0))
        with patch.object(importer,"get_cell_groups",return_value=([[],[]],2)):
            with self.assertRaisesRegex(ValueError,"share conflicting"):
                import_authored_art(self.original,b"p",b"c",[
                    {"cell":0,"png":"first.png","regions":[[0,0,4,4]]},
                    {"cell":1,"png":"second.png","regions":[[0,0,4,4]]}
                ],self.root)


if __name__=="__main__":
    unittest.main()
