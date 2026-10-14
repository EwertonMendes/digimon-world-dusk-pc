"""ROM-free regression tests for merging separate code-generation captures."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("merge_profile",Path(__file__).resolve().parents[1]/"tools"/"merge_verified_profiles.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def page(cpu,addr,byte):
    data=bytes([byte])*4096
    return {"cpu":cpu,"addr":f"0x{addr:08X}",
            "sha1":hashlib.sha1(data).hexdigest(),
            "data":base64.b64encode(data).decode("ascii"),
            "executions":5}


def capture(page_data,addr="0x02200040"):
    return {
        "kind":"ndsrecomp-tier3-coverage",
        "rom_sha1":"a"*40,
        "pages":{"page_size":4096,"entries":[page_data]},
        "entry_points_arm9":[{"addr":addr,"mode":"arm","kind":"call","caller":"0x02000100","hits":11}],
        "entry_points_arm7":[]}


class MergeTests(unittest.TestCase):
    def test_duplicate_page_generation_deduplicated(self):
        p=page(9,0x02200000,1)
        merged=module.merge([capture(p),capture(p)])
        self.assertEqual(len(merged["pages"]["entries"]),1)
        self.assertEqual(len(merged["entry_points_arm9"]),1)

    def test_generation_bound_root_bitmaps_are_unioned(self):
        first = page(9, 0x02200000, 1)
        second = page(9, 0x02200000, 1)
        first["root_arm"] = base64.b64encode(bytes([1])).decode("ascii")
        second["root_arm"] = base64.b64encode(bytes([2])).decode("ascii")
        first["root_hits"] = [3, 4]
        second["root_hits"] = [7, 2]
        result = module.merge([capture(first), capture(second)])
        record = result["pages"]["entries"][0]
        bits = base64.b64decode(record["root_arm"])
        self.assertEqual(len(bits), 128)
        self.assertEqual(bits[0], 3)
        self.assertEqual(record["root_hits"], [7, 4])

    def test_same_address_different_contents_kept_distinct(self):
        a=module.merge([capture(page(9,0x02200000,1)),
                        capture(page(9,0x02200000,2))])
        self.assertEqual(len(a["pages"]["entries"]),2)
        self.assertEqual(a["merge_provenance"]["different_contents_at_same_page"],1)

    def test_different_rom_rejected(self):
        b=capture(page(9,0x02200000,1))
        b["rom_sha1"]="b"*40
        with self.assertRaises(ValueError):
            module.merge([capture(page(9,0x02200000,2)),b])

    def test_tamper_detected(self):
        b=capture(page(9,0x02200000,1))
        b["pages"]["entries"][0]["sha1"]="0"*40
        with self.assertRaises(ValueError):
            module.merge([b])

    def test_unaligned_and_invalid_mode_not_promoted(self):
        b=capture(page(9,0x02200000,1),addr="0x02200041")
        out=module.merge([b])
        self.assertEqual(out["entry_points_arm9"],[])


if __name__=="__main__":
    unittest.main()
