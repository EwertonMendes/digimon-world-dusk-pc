"""ROM-free incremental overlay selection tests."""
import importlib.util
from pathlib import Path
import sys
import unittest

TOOLS=Path(__file__).resolve().parents[1]/"tools"
sys.path.insert(0,str(TOOLS))
spec=importlib.util.spec_from_file_location("overlay_fixtures",Path(__file__).resolve().parent/"test_verified_overlays.py")
fx=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)
from select_verified_aot_delta import delta_plan


class DeltaTests(unittest.TestCase):
    def test_new_only_and_identity(self):
        rom,cover,_=fx.fixture()
        result=delta_plan(rom,[cover],{0})
        self.assertEqual(result["observed_overlay_ids"],[0,1])
        self.assertEqual(result["new_overlay_ids"],[1])
        self.assertEqual(result["new_banks"][0]["verified_pages"],1)
        self.assertEqual(result["new_banks"][0]["observed_roots"],1)
        self.assertIn("validate_live_bytes",result["requirements"])

    def test_all_shipped_is_empty(self):
        rom,cover,_=fx.fixture()
        result=delta_plan(rom,[cover],{0,1})
        self.assertEqual(result["new_banks"],[])

    def test_wrong_rom_or_corrupted_page_fails(self):
        rom,cover,_=fx.fixture()
        with self.assertRaises(ValueError):
            delta_plan(rom[:-1], [cover], set())
        cover["pages"]["entries"][0]["sha1"]="0"*40
        with self.assertRaises(ValueError):
            delta_plan(rom, [cover], set())

    def test_no_capture_rejected(self):
        with self.assertRaises(ValueError):
            delta_plan(b"",[],set())


if __name__=="__main__":
    unittest.main()
