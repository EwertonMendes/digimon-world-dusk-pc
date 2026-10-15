"""Host UI regression contract: responsive, accessible and gameplay-safe SDL3."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
HEADER=(ROOT/'tools/native-ui/dusk_modern_ui.hpp').read_text(encoding='utf-8')
PATCH=(ROOT/'tools/patches/ndsrecomp-dusk-adaptive-ui-v027.patch').read_text(encoding='utf-8')
BUILD=(ROOT/'.github/workflows/dusk-native-windows-playtest.yml').read_text(encoding='utf-8')

class AdaptiveUiTests(unittest.TestCase):
    def test_pure_host_and_no_rom_mutation(self):
        self.assertIn('namespace dusk_modern',HEADER)
        self.assertNotIn('nds_set_touch(',HEADER)
        self.assertNotIn('scheduler_run_round(',HEADER)
        self.assertNotIn('cartridge',HEADER)
        self.assertIn('dusk_save(p)',HEADER)
    def test_responsive_and_touch_gestures(self):
        for item in ('w<730 || w<h','SDL_SetRenderClipRect','state.scroll',
                     'SDL_EVENT_FINGER_DOWN','SDL_EVENT_FINGER_MOTION',
                     'SDL_EVENT_FINGER_UP','finger_moved','finger_start_scroll',
                     'g.pip_restore','g.pip_swap','g.pip_minimize',
                     'pip_drag','floating_x','floating_y'):
            with self.subTest(item=item):self.assertIn(item,HEADER)
    def test_keyboard_gamepad_mouse():
        for item in ('SDL_SCANCODE_LEFT','SDL_SCANCODE_UP','SDL_SCANCODE_TAB',
                     'SDL_SCANCODE_RETURN','SDL_CONTROLLER_BUTTON_DPAD_UP',
                     'SDL_CONTROLLER_BUTTON_A','SDL_EVENT_MOUSE_WHEEL',
                     'dusk_modern::input(presentation,event)',
                     'dusk_modern::draw_panel(renderer,presentation,geo)',
                     'dusk_modern::draw_pip(renderer,presentation,geo)'):
            with self.subTest(item=item):self.assertIn(item,HEADER+PATCH)
    def test_original_gameplay_input_is_preserved(self):
        self.assertIn('return false;',HEADER)
        self.assertIn('if(p.dusk.quit_confirm)return false;',HEADER)
        self.assertIn('Existing confirmed quit modal stays authoritative',HEADER)
        self.assertIn('!p.dusk.menu_open',HEADER)
        self.assertIn('if(dusk_modern::input(presentation,event)) continue;',PATCH)
    def test_native_header_must_be_copied_into_real_runner(self):
        self.assertIn('cp tools/native-ui/dusk_modern_ui.hpp upstream/runner/src/',BUILD)

if __name__=="__main__":unittest.main()
