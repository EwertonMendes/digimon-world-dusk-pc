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
            invalid = root / "bad.rgba"
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

    def test_cli_forwards_window_icon_to_private_packer(self):
        import sys
        from unittest.mock import patch
        from pack_native_private import main
        cli = ["pack_native_private.py",
               "--launcher", "a.exe", "--runner", "runner.exe",
               "--sdl", "SDL3.dll", "--rom", "game.nds",
               "--output", "out.exe", "--window-icon", "window-icon.rgba"]
        with patch.object(sys, "argv", cli), patch("pack_native_private.build") as mock:
            main()
        self.assertEqual(mock.call_args.args[-1], Path("window-icon.rgba"))

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
