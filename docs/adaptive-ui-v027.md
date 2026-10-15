# Dusk Adaptive UI — v0.27 (Windows Playtest)

This UI is native SDL3, not a browser or a guest-ROM modification.
The original game ROM, video surfaces, scheduler, sound, cartridge and
`userdata/A6RE` save profile are untouched.

## New options surface

- Four navigation tabs: **Screens**, **Video**, **Controls**, **System**.
- Layout selector cards with graphical previews for all six existing layouts.
- Screens settings: main DS screen, show/hide auxiliary display, PiP sizing,
  PiP corner. Video: original 4:3 versus 16:9 stretch, window mode, frame
  presentation speed. System: resume and confirmed quit.
- Responsive centered window on desktop; narrow layouts fit within output
  bounds, use shorter tab labels and clip scrollable content inside a modal.
- Always-visible small PC options control; the game no longer requires hover
  to discover settings on touchscreens.
- Auxiliary PiP chrome is slimmer and keeps the existing header, swap,
  minimize, restore, drag and resize hit regions so tested gestures persist.

## Input behavior

- Keyboard: arrow keys move the focus and change values; Tab cycles tabs;
  Enter/space selects; Esc/F10 use the original native close behavior.
- Controller: D-pad + left analog move focus; A activates; B/Select retain
  the original close/menu semantics and the native quit confirmation.
- Mouse: click any tab/card/control and mouse-wheel scrolls long menus.
- Touch: tap tabs/card controls; scroll the menu with a vertical swipe;
  PiP header allows touch dragging, swapping, hiding and restoring.
  Touches on the lower DS surface still go through the original guest mapper.
- The original native PC Options input capture remains authoritative;
  guest keys must never be held down while host settings are open.

## Architecture

`tools/native-ui/dusk_modern_ui.hpp` is the separate, self-contained
presentation and input adapter. The thin
`tools/patches/ndsrecomp-dusk-adaptive-ui-v027.patch` integrates it after
the existing legacy settings helpers into the pinned NDSRecomp frontend.
The native private workflow installs that header into its pinned checkout
before compiling SDL3. No new SDL dependencies or backend are required.

## Validation

The ROM-free CI verifies patch integration, adaptive host UI contracts,
native input capture and launcher source tests. A private Windows v0.27
runner build is required before the EXE is considered playable.
Real phone packaging is not present yet: touch support is a native SDL3
capability prepared for the future Android/iOS ports, **not a claim that an
APK has already been tested**. Test Windows mouse, keyboard and gamepad,
then simulate touch or test on a touchscreen Windows device before merging.
