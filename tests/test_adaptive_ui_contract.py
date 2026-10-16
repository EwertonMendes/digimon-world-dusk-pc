"""Host UI regression contract: responsive, accessible and gameplay-safe SDL3."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
HEADER=(ROOT/'tools/native-ui/dusk_modern_ui.hpp').read_text(encoding='utf-8')
MATERIAL=(ROOT/'tools/native-ui/dusk_material_renderer.hpp').read_text(encoding='utf-8')
FONT=(ROOT/'tools/native-ui/dusk_ui_font.hpp').read_text(encoding='utf-8')
PATCH=(ROOT/'tools/patches/ndsrecomp-dusk-adaptive-ui-v027.patch').read_text(encoding='utf-8')
BUILD=(ROOT/'.github/workflows/dusk-native-windows-playtest.yml').read_text(encoding='utf-8')

class AdaptiveUiTests(unittest.TestCase):
    def test_pure_host_and_no_rom_mutation(self):
        self.assertIn('namespace dusk_modern',HEADER)
        self.assertNotIn('nds_set_touch(',HEADER)
        self.assertNotIn('scheduler_run_round(',HEADER)
        self.assertNotIn('cartridge',HEADER)
        self.assertIn('dusk_save(p)',HEADER)
        self.assertIn('hit_test(',HEADER)
        self.assertNotIn('contains(',HEADER)
    def test_responsive_and_touch_gestures(self):
        for item in ('const bool stacked = w < 910 || w < h','SDL_SetRenderClipRect','state.scroll',
                     'SDL_EVENT_FINGER_DOWN','SDL_EVENT_FINGER_MOTION',
                     'SDL_EVENT_FINGER_UP','finger_moved','finger_start_scroll',
                     'g.pip_restore','g.pip_swap','g.pip_minimize',
                     'pip_drag','floating_x','floating_y'):
            with self.subTest(item=item):self.assertIn(item,HEADER+MATERIAL)
    def test_keyboard_gamepad_mouse(self):
        for item in ('SDL_SCANCODE_LEFT','SDL_SCANCODE_UP','SDL_SCANCODE_TAB',
                     'SDL_SCANCODE_RETURN','SDL_CONTROLLER_BUTTON_DPAD_UP',
                     'SDL_CONTROLLER_BUTTON_A','SDL_EVENT_MOUSE_WHEEL',
                     'dusk_modern::input(presentation,event)',
                     'dusk_material::panel(renderer,presentation,geo)',
                     'dusk_material::pip(renderer,presentation,geo)'):
            with self.subTest(item=item):self.assertIn(item,HEADER+PATCH+MATERIAL)
    def test_original_gameplay_input_is_preserved(self):
        self.assertIn('return false;',HEADER)
        self.assertIn('if(p.dusk.quit_confirm)return false;',HEADER)
        self.assertIn('Existing confirmed quit modal stays authoritative',HEADER)
        self.assertIn('!p.dusk.menu_open',HEADER)
        self.assertIn('if (dusk_modern::input(presentation,event)) continue;',PATCH)
    def test_native_header_must_be_copied_into_real_runner(self):
        for filename in ('dusk_modern_ui.hpp','dusk_material_renderer.hpp',
                         'dusk_ui_font.hpp','dusk_font_atlas.hpp'):
            self.assertIn('cp tools/native-ui/'+filename+' upstream/runner/src/',BUILD)
    def test_settings_title_and_overlay_controls(self):
        self.assertEqual(MATERIAL.count('"CONFIGURACOES"'), 1)
        self.assertIn('menu_icon(r,',MATERIAL)
        self.assertIn('option_title(',MATERIAL)
        self.assertIn('focused?gold:(chosen?bright:stroke2)',MATERIAL)
        self.assertNotIn('DUSK  /  PC EDITION', MATERIAL)
        self.assertIn('center_label(r,g.pip_restore,"Show",14,ink,true)', MATERIAL)
        self.assertNotIn('label(r,g.pip_restore.x+8', MATERIAL)
        self.assertIn('gear_icon(r,g.settings,ink)', MATERIAL)
        self.assertNotIn('center_label(r,g.settings,"PC"', MATERIAL)
        self.assertIn('SDL_RenderGeometry(r,nullptr,vertices,samples*6', MATERIAL)
    def test_no_debug_font_in_new_renderer(self):
        self.assertNotIn('SDL_RenderDebugText',MATERIAL+FONT)
        self.assertIn('SDL_RenderGeometry',MATERIAL)
        self.assertIn('SDL_SetRenderClipRect',MATERIAL)
        self.assertIn('SDL_RenderTexture',FONT)
        self.assertIn('max_width',MATERIAL)


if __name__=="__main__":unittest.main()
