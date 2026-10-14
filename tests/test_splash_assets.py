"""ROM-free validation of the native startup splash and release-facing version."""
from __future__ import annotations

from pathlib import Path
import struct
import sys
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from branding import APP_NAME, APP_VERSION, APP_SLUG, WINDOWS_EXE, WINDOW_TITLE
from generate_splash import generate, SOURCE, WIDTH, HEIGHT


class SplashTests(unittest.TestCase):
    def test_splash_is_loadable_by_sdl3_without_sdl_image(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "dusk-splash.bmp"
            self.assertEqual(generate(SOURCE, out), out)
            data = out.read_bytes()
            self.assertEqual(data[:2], b"BM")
            self.assertEqual(struct.unpack_from("<ii", data, 18), (WIDTH, HEIGHT))
            self.assertEqual(struct.unpack_from("<H", data, 28)[0], 24)
            self.assertLess(len(data), 4 * 1024 * 1024)
            with Image.open(out) as bmp:
                self.assertEqual(bmp.format, "BMP")
                self.assertEqual(bmp.size, (1280, 720))
                self.assertEqual(bmp.mode, "RGB")
                self.assertNotEqual(bmp.getpixel((100, 100)), bmp.getpixel((1100, 100)))

    def test_one_release_identity_is_consistent(self):
        self.assertEqual(APP_NAME, "Digimon World Dusk Recompiled")
        self.assertEqual(APP_VERSION, "v0.24")
        self.assertEqual(WINDOW_TITLE, APP_NAME + " | " + APP_VERSION)
        self.assertEqual(WINDOWS_EXE, APP_SLUG + "-" + APP_VERSION + "-Windows.exe")
        desktop = (ROOT / "native-launcher/desktop/save_data.go").read_text()
        self.assertIn('appVersion = "' + APP_VERSION + '"', desktop)
        workflow = (ROOT / ".github/workflows/dusk-native-windows-playtest.yml").read_text()
        self.assertIn("RELEASE_FILENAME: " + WINDOWS_EXE, workflow)
        self.assertIn("--splash assets/splash/generated/dusk-splash.bmp", workflow)
        self.assertIn("python tools/generate_splash.py", workflow)
        native = (ROOT / "tools/patches/ndsrecomp-dusk-recompiled-splash.patch").read_text()
        self.assertIn(WINDOW_TITLE, native)
        self.assertIn("SDL_EVENT_QUIT", native)
        self.assertIn("SDL_EVENT_KEY_DOWN", native)
        self.assertIn("SDL_RenderTexture", native)


if __name__ == "__main__":
    unittest.main()
