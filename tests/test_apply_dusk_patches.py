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
        self.assertEqual(names[-5], "ndsrecomp-dusk-pc-menu-input-capture.patch")
        self.assertEqual(names[-4], "ndsrecomp-dusk-battle-frame-spikes.patch")
        self.assertEqual(names[-3], "ndsrecomp-dusk-precise-pacing.patch")
        self.assertEqual(names[-2], "ndsrecomp-dusk-window-icon.patch")
        self.assertEqual(names[-1], "ndsrecomp-dusk-recompiled-splash.patch")
        for name in names:
            self.assertTrue((p.parent / "patches" / name).is_file(), name)

    def test_pacing_patch_only_replaces_host_sleep_without_touching_guest_or_audio(self):
        patch = (p.parent / "patches" /
                 "ndsrecomp-dusk-precise-pacing.patch").read_text()
        self.assertEqual(patch.count("+        dusk_audio_pace_wait(queued - pace_floor);"), 1)
        self.assertIn("+                dusk_audio_pace_wait(0);", patch)
        self.assertIn("+    SDL_DelayPrecise(bounded_ns);", patch)
        self.assertIn("std::clamp(wanted_ns, 250000ull, 2000000ull)", patch)
        self.assertIn("+    SDL_Delay(1);", patch)  # SDL2 compatibility
        self.assertNotIn("kAudioQueueFrames", patch)
        self.assertNotIn("kSystemCyclesPerFrame", patch)
        self.assertNotIn("scheduler_run_round", patch)
        self.assertEqual(patch.count("-                SDL_Delay(1);"), 1)
        self.assertEqual(patch.count("-        SDL_Delay(1);"), 1)

    def test_splash_patch_does_not_touch_guest_execution(self):
        patch = (p.parent / "patches" /
                 "ndsrecomp-dusk-recompiled-splash.patch").read_text()
        self.assertIn("dusk_show_startup", patch)
        self.assertIn("SDL_LoadBMP(path)", patch)
        self.assertIn("Digimon World Dusk Recompiled | v0.25", patch)
        self.assertNotIn("scheduler_run_round", patch)
        self.assertNotIn("cartridge", patch)

    def test_small_contract_is_prefix_of_desktop(self):
        self.assertEqual(module.DESKTOP[:len(module.NATIVE_UI)], module.NATIVE_UI)
        self.assertEqual(len(module.PINNED_RECOMP_COMMIT), 40)

    def test_missing_checkout_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            module.integrate(Path("/unlikely-nonexistent-dusk-checkout"), "desktop")


if __name__ == "__main__":
    unittest.main()
