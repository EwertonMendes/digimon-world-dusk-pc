"""ROM-free release gate: no private Windows executable without preserved dispatch."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pack_native_private import build

def fake_table(rows):
    lines = ["static const NdsStaticValidation v = {0x2000800u, 72u, nullptr, 0, 0u};",
             "const NdsDispatchEntry g_dispatch_dusk_arm9_main[] = {"]
    lines.extend(f"{{0x{x:08X}u, 0u, func, &v}}," for x in rows)
    lines.extend(["};", f"const unsigned g_dispatch_dusk_arm9_main_len = {len(rows)}u;"])
    return "\n".join(lines)+"\n"

class BundleProtectionTests(unittest.TestCase):
    def test_missing_paired_gate(self):
        with self.assertRaisesRegex(ValueError, "both"):
            build(*(Path("missing") for _ in range(5)), baseline=Path("none"))

    def test_rejects_invalid_window_icon_without_private_rom(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            invalid = root / "bad.bmp"
            invalid.write_bytes(b"not a bitmap")
            for name, data in (
                ("launcher", b"MZfake"),
                ("runner", b"MZSDL3.dll"),
                ("sdl", b"MZdll"),
                ("rom", b"not real ROM"),
            ):
                (root / name).write_bytes(data)
            with self.assertRaisesRegex(ValueError, "SDL window icon"):
                build(*(root / name for name in ("launcher", "runner", "sdl", "rom", "out")),
                      window_icon=invalid)

    def test_dropped_bank_refuses_packaging_before_opening_private_game(self):
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/"old",Path(td)/"new"
            a.mkdir();b.mkdir()
            (a/"dusk_arm9_main_dispatch.c").write_text(fake_table([0x2000800,0x2000804]))
            (b/"dusk_arm9_main_dispatch.c").write_text(fake_table([0x2000804]))
            with self.assertRaisesRegex(ValueError,"lost 1"):
                build(*(Path("nonexistent") for _ in range(5)), baseline=a, candidate=b)

if __name__ == "__main__":
    unittest.main()
