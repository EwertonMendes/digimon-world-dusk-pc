"""Patch order and exact upstream version are ROM-free public contracts."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "tools" / "apply_dusk_patches.py"
spec = importlib.util.spec_from_file_location("dusk_patch_tool", p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IntegrationTests(unittest.TestCase):
    def test_full_patch_manifest_includes_all_ui_modes(self):
        names = module.DESKTOP
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[0], "ndsrecomp-dusk-native-ui.patch")
        self.assertEqual(names[-2], "ndsrecomp-dusk-pc-menu-input-capture.patch")
        self.assertEqual(names[-1], "ndsrecomp-dusk-battle-frame-spikes.patch")
        for name in names:
            self.assertTrue((p.parent / "patches" / name).is_file(), name)

    def test_small_contract_is_prefix_of_desktop(self):
        self.assertEqual(module.DESKTOP[:len(module.NATIVE_UI)], module.NATIVE_UI)
        self.assertEqual(len(module.PINNED_RECOMP_COMMIT), 40)

    def test_missing_checkout_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            module.integrate(Path("/unlikely-nonexistent-dusk-checkout"), "desktop")


if __name__ == "__main__":
    unittest.main()
