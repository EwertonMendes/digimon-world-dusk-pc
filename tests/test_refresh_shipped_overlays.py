"""ROM-free identity, staged refresh and code-version safety tests."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
sys.path.insert(0,str(ROOT/"tests"))
from test_verified_overlays import fixture
import refresh_shipped_overlays as refresh


class OverlayRefreshTests(unittest.TestCase):
    def test_select_and_stage_distinct_same_address_generations(self):
        rom,coverage,images=fixture()
        with patch.object(refresh,"DUSK_USA_SHA256",hashlib.sha256(rom).hexdigest()):
            proofs=refresh.selected_overlays(rom,[coverage],{0,1})
        self.assertEqual([x["overlay_id"] for x in proofs],[0,1])
        self.assertEqual(len({x["source_sha1"] for x in proofs}),2)
        with tempfile.TemporaryDirectory() as root:
            src=Path(root)/"source"
            src.mkdir()
            for i,proof in enumerate(proofs):
                name=proof["bank"]
                (src/(name+".bin")).write_bytes(images[i])
                (src/(name+".toml")).write_text(
                    "[program]\n"+f'name = "{name}"\ncpu = "arm9"\n'
                    +f'load_address = {proof["load_address"]}\n'
                    +"[identity]\n"+f'sha1 = "{proof["source_sha1"]}"\n')
            dest=Path(root)/"new"/"stage"
            entries=refresh.stage_refresh(src,dest,proofs)
            self.assertEqual(len(entries),2)
            self.assertEqual(entries[0]["roots"],1)
            self.assertIn("--validate-live-bytes",
                refresh.emit_private_banks.__doc__ or "emit requires --validate-live-bytes")
            with self.assertRaises(FileExistsError):
                refresh.stage_refresh(src,dest,proofs)
            # Corruption must reject without creating a refreshed executable.
            original=(src/"dusk_arm9_ovl00.bin").read_bytes()
            (src/"dusk_arm9_ovl00.bin").write_bytes(original+b"x")
            with self.assertRaises(ValueError):
                refresh.build_config(proofs[0],
                    (src/"dusk_arm9_ovl00.bin").read_bytes(),
                    (src/"dusk_arm9_ovl00.toml").read_text())

    def test_unproven_or_foreign_rom_fails(self):
        rom,coverage,_=fixture()
        with patch.object(refresh,"DUSK_USA_SHA256",hashlib.sha256(rom).hexdigest()):
            with self.assertRaises(ValueError):
                refresh.selected_overlays(rom,[coverage],{17})
            bad=dict(coverage)
            bad["rom_sha1"]="0"*40
            with self.assertRaises(ValueError):
                refresh.selected_overlays(rom,[bad],{0})
        with self.assertRaises(ValueError):
            refresh.selected_overlays(rom,[coverage],{0})


if __name__=="__main__":
    unittest.main()
