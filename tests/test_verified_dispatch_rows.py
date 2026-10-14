"""Synthetic proof: validation initializers are not ARM-native dispatch rows."""
from __future__ import annotations
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from verified_dispatch_rows import (
    parse_dispatch_file, read_dispatch_rows, verify_dispatch_growth,
)

def source(bank="dusk_arm9_main", rows=((0x2000800,0),(0x2000804,0))):
    initial = (
        "static const NdsStaticValidation v1 = {0x02000800u, 72u, static_bytes, 0, 0u};\n"
        "static const NdsStaticValidation v2 = {0x02000804u, 12u, static_bytes, 0, 0u};\n"
    )
    records="\n".join(
        f"    {{0x{pc:08X}u, {mode}u, some_func, &v1}}," for pc,mode in rows
    )
    return (initial+f"const NdsDispatchEntry g_dispatch_{bank}[] = {{\n"+
            records+"\n};\n"+
            f"const unsigned g_dispatch_{bank}_len = {len(rows)}u;\n")

class DispatchTests(unittest.TestCase):
    def write(self, root, name, content):
        path=root/name
        path.write_text(content,encoding="utf-8")
        return path

    def test_exact_rows_not_validation_bytes_or_lengths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            f=self.write(root,"dusk_arm9_main_dispatch.c",source())
            self.assertEqual(parse_dispatch_file(f),{(0x2000800,0),(0x2000804,0)})
            self.assertEqual(len(read_dispatch_rows([root],expected_cpu=9)),2)
            with self.assertRaises(ValueError):
                read_dispatch_rows([root],expected_cpu=7)

    def test_declared_length_is_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.write(Path(tmp),"dusk_arm9_main_dispatch.c",
                source().replace("_len = 2u", "_len = 72u"))
            with self.assertRaisesRegex(ValueError,"declared 72"):
                parse_dispatch_file(f)

    def test_rejects_invalid_thumb_mode_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"dusk_arm9_main_dispatch.c"
            p.write_text(source(rows=((0x2000800,12),)))
            with self.assertRaisesRegex(ValueError,"invalid native dispatch entry"):
                parse_dispatch_file(p)
            p.write_text(source(rows=((0x2000800,0),(0x2000800,0))))
            with self.assertRaisesRegex(ValueError,"duplicate"):
                parse_dispatch_file(p)

    def test_bank_specific_monotonic_growth(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"old",Path(tmp)/"new"
            a.mkdir();b.mkdir()
            self.write(a,"dusk_arm9_main_dispatch.c",source())
            self.write(b,"dusk_arm9_main_dispatch.c",
                       source(rows=((0x2000800,0),(0x2000804,0),(0x2000808,0))))
            outcome=verify_dispatch_growth(a,b)
            self.assertEqual(outcome["new_rows_total"],1)
            self.assertEqual(outcome["status"],"no-native-dispatch-regressions")
            self.write(b,"dusk_arm9_main_dispatch.c",
                       source(rows=((0x2000804,0),(0x2000808,0))))
            with self.assertRaisesRegex(ValueError,"lost 1"):
                verify_dispatch_growth(a,b)

    def test_no_silent_loss_of_bank_or_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"old",Path(tmp)/"new"
            a.mkdir();b.mkdir()
            self.write(a,"dusk_arm9_main_dispatch.c",source())
            self.write(b,"dusk_arm7_main_dispatch.c",source("dusk_arm7_main"))
            with self.assertRaisesRegex(ValueError,"Missing original bank"):
                verify_dispatch_growth(a,b)
            with self.assertRaises(ValueError):
                read_dispatch_rows([a/"missing_dispatch.c"])

if __name__ == "__main__":
    unittest.main()
