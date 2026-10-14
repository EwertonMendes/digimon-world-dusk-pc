# Digimon World Dusk PC v0.16 — Immersive native frontend

This is an opt-in SDL3-only presentation change layered over the **unchanged**
ROM-derived AOT bank code from v0.15. It never writes original game RAM to
reconfigure menus, never patches story logic, and never changes cartridge
EEPROM saving (`userdata/A6RE/saves/dusk.sav`).

## Owner-visible changes

- Fullscreen borderless at first launch. `F11` or `Alt+Enter` switches between
  fullscreen/window and persists the selected state across launches.
- No permanent 42px toolbar. The desktop screen fills the window. A small
  `PC` corner tab only appears on upper-right hover; `Esc` or `F10`
  opens PC Options from both the title screen and active gameplay.
- PC Options uses an in-game-looking violet digital menu with keyboard,
  controller and mouse actions, containing layout, active display, auxiliary
  visibility/size/position, aspect, fullscreen and 30/60 presentation.
- Default `Focus + PiP`: the **lower physical DS touchscreen** is large,
  upper screen floats above and can be dragged using the 24px handle.
  `S` swaps main/aux screen sizes in one click. `_` minimizes the
  auxiliary screen, `SHOW AUX` restores it.
- When the *upper* DS screen is the large one, the smaller *lower* DS screen
  remains the interactive touchscreen with correct coordinate inversion.
- `4:3` preserves original pixels. `16:9 FILL *` stretches the original
  4:3 image into the target PC aspect **only when explicitly selected**.
  It does **not** expand the DS 2D camera, native HUD, or visible map.
- The existing Classic/Modern/Floating/Side by side/Main-only presets and
  F4-F9 keys are preserved. F8 changes focus when Focus+PiP is active.
  Game simulation timing stays ~59.826 Hz even when visual presentation
  is changed to 30 FPS.
- PC settings migrate from `native-layout-v3.cfg` or older
  `native-layout.cfg` to `native-layout-v4.cfg` via
  `SDL_GetPrefPath("DuskPC","DigimonWorldDusk")`. These files are **not**
  game saves. v0.15 remains available for rollback.

## Access and integration limits

The PC Options **host overlay** is available throughout the game, including
title and gameplay, but **there is not yet a new selectable entry in the
original cartridge's Main Menu/Options/S Menu ARM menu lists**. Those would
require game-specific reverse engineering and proof of safe injection points;
do not claim that their original ROM menus were modified. Visual style is
native SDL inspired by the game, **not a byte-identical game asset/font**.

The `16:9 FILL` control is explicitly a host stretch. The existing
NDSRecomp adaptive-widescreen pipeline needs Dusk-specific verification of
2D/HUD/3D scenes and cannot be represented as universally native Dusk 16:9.

## Tests and release gates

- [x] Native Windows x64 SDL3 runner compiled and linked with original v0.15
  ARM9/ARM7/overlay game banks; ROM SHA unchanged.
- [x] Pure deterministic geometry test covers 12,672 viewport/layout/focus,
  aux/minimized, ratio, float sizes, corner and touchscreen variants.
- [x] CI confirms patch applies **after** pinned native SDL3, screen swap,
  30Hz-settings and save-state-disable patches.
- [ ] Owner visually validates the PC Options overlay and draggable,
  minimizable and swappable PiP in live Windows play.
- [ ] Owner confirms Start/Continue, original in-game Save, inventory,
  battle animations, sound, maps and seamless fullscreen/Alt+Tab.
- [ ] Game-native ARM menu insertion and real scene-expanding widescreen
  remain separate, unimplemented tasks.

### Controls

| Operation | Input |
| --- | --- |
| Open/close PC Options | Esc, F10, or mouse upper-right hover -> PC |
| Choose settings row | Up/Down or controller D-pad |
| Change setting | Left/Right, Enter or gamepad A |
| Close menu | Esc, F10, Back / controller Start or B |
| Minimize/restore | PiP header `_` / small `SHOW AUX` tab |
| Swap main/aux | PiP header `S` or F8 in Focus |
| Drag PiP | Mouse drag on PiP header |
| Toggle fullscreen | F11 or Alt+Enter |
| Switch layout | F4 |
| Toggle aux | F5 |
| Size/position | F6/F7 |
| Presentation only 30/60 FPS | F9 |

Unlike a savestate feature, in-game Save/Continue remains the original
cartridge EEPROM mechanism. Do not publish the private full-game executable,
game sources or the owner's save files in GitHub Actions.
