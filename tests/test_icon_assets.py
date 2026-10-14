"""ROM-free tests for cross-platform Dusk icon exports."""
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
import sys
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from generate_icons import SOURCE, generate


class IconTests(unittest.TestCase):
    def test_generates_all_platforms(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate(SOURCE, out)
            for relative, fmt in (
                ("windows/dusk.ico", "ICO"),
                ("windows/window-icon.bmp", "BMP"),
                ("macos/dusk.icns", "ICNS"),
                ("linux/hicolor/256x256/apps/dusk-pc.png", "PNG"),
                ("android/mipmap-xxxhdpi/ic_launcher.png", "PNG"),
                ("android/drawable-nodpi/ic_launcher_foreground.png", "PNG"),
            ):
                with Image.open(out / relative) as icon:
                    self.assertEqual(icon.format, fmt, relative)
                    icon.verify()
            with Image.open(out / "windows/dusk.ico") as icon:
                self.assertIn((256, 256), icon.info["sizes"])
                self.assertIn((16, 16), icon.info["sizes"])
            ET.parse(out / "android/mipmap-anydpi-v26/ic_launcher.xml")
            ET.parse(out / "android/drawable/ic_launcher_background.xml")
            self.assertIn("Icon=dusk-pc", (out / "linux/dusk-pc.desktop").read_text())

    def test_rejects_missing_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                generate(Path(tmp) / "missing.webp", Path(tmp) / "icons")


if __name__ == "__main__":
    unittest.main()
