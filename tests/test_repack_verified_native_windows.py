"""ROM-free private EXE repack gate tests with synthetic bytes only."""
import hashlib
import io
import struct
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import repack_verified_native_windows as repack


def packed_bytes(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        for name, data in files.items():
            z.writestr(name, data)
    blob = stream.getvalue()
    body = b'MZ-synthetic-test-executable' + blob + repack.MAGIC
    return body + struct.pack('<Q', len(blob)) + hashlib.sha256(blob).digest()


class VerifiedRepackTests(unittest.TestCase):
    def files(self):
        return {
            'runner.exe': b'MZSDL3.dll executable',
            'SDL3.dll': b'MZ-fake-sdl',
            'libiconv-2.dll': b'MZ-fake-iconv',
            'game.nds': b'synthetic-not-a-ROM',
            'window-icon.rgba': b'asset-bytes',
            'dusk-splash.bmp': b'preview-bytes'
        }

    def test_old_assets_are_not_extracted_for_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = self.files()
            payload = packed_bytes(fake)
            exe = root / 'native.exe'
            exe.write_bytes(payload)
            with patch.object(repack, 'ROM_SHA256', hashlib.sha256(fake['game.nds']).hexdigest()):
                hashes = repack.verified_extract(exe, root / 'out', hashlib.sha256(payload).hexdigest())
            self.assertEqual(set(hashes), repack.RUNTIME_FILES)
            self.assertFalse((root / 'out/window-icon.rgba').exists())
            self.assertFalse((root / 'out/dusk-splash.bmp').exists())

    def test_missing_splash_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = self.files()
            del fake['dusk-splash.bmp']
            payload = packed_bytes(fake)
            exe = root / 'bad.exe'
            exe.write_bytes(payload)
            with self.assertRaisesRegex(ValueError, 'Missing or extraneous'):
                repack.verified_extract(exe, root / 'out', hashlib.sha256(payload).hexdigest())

    def test_sha_mismatch_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / 'bad.exe'
            exe.write_bytes(packed_bytes(self.files()))
            with self.assertRaisesRegex(ValueError, 'source executable hash'):
                repack.verified_extract(exe, root / 'out', '0'*64)


if __name__ == '__main__':
    unittest.main()
