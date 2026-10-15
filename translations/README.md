# Game localization catalogs (Digimon World Dusk USA)

This project ships one verified USA game ROM. Players never supply or switch ROMs.
PC Settings stores their chosen locale; a *new application launch* applies
translated game resources **only in memory**, after the ROM identity check.

## Adding or editing a language

- Dialogue/NPC/title text: edit `translations/msgpak/<language>.json`. Its keys
  are `"<group>/<message_id>"`, for example `"67/49"` is the original
  Dark Market equipment shopkeeper greeting. Values are natural translated
  strings with explicit `\n` line breaks and control markers preserved.
- ARM9 menu/shop **text data**: edit `translations/arm9/<language>.json`.
  Each decimal ROM offset has a verified `source` string and a `text`
  translation. Only same-length-or-shorter data is supported. Longer strings
  **must not** be shortened by overwriting adjacent ARM9 bytes; they require
  verified pointer/asset relocation or font-rendering hooks.
- Generate both C++ lookup headers with:

  ```bash
  python tools/generate_dusk_msgpak_header.py
  python tools/generate_dusk_arm9_header.py
  ```

  Commit the JSON and generated headers together. CI rejects stale/malformed
  catalogs using `--check` and validates replacement bytes against the
  original ROM on the owner-only Windows workflow.
- To enable a *new locale* in PC Settings, add the locale to the settings
  language registry and launcher allowlist. The message/ARM9 data mechanisms
  themselves are locale-independent; new translations are not hardcoded in C++.

## Safety rules

1. Never remove, reorder or fabricate original control codes such as
   `[PLAYER_NAME]`, `[RED]`, `[GREEN]` and `[END]`.
2. Break lines intentionally using `\n` and inspect long in-game pages.
   Extending the binary text table eliminates ROM pointer-length limits,
   **not** the physical 256x192 DS dialog window limits.
3. The in-memory MSG.PAK rebuilder verifies all original group boundaries,
   preserved special codes and unused cartridge padding before applying.
   Missing translations fall back to English.
4. The in-memory ARM9 data patcher validates *every original string and its
   terminator before writing any bytes*. A mismatch rejects that entire
   resource set and leaves original values intact.
5. Never edit ARM instruction bytes, precompiled AOT banks, saved EEPROM,
   or externally installed resources for localization.
6. Menus with baked-in tile/sprite artwork (for example the large six-button
   Digivice/S-key menu or shop action sprites) have a **separate graphical
   localization problem**. They do not become translated merely because
   an identically named dialogue or ARM9 help string changes.
   Do not paste translated SDL labels over original drawn text. Find and
   replace the game-owned tile resources or intercept the verified resource
   upload point before declaring these screens fully localized.

## Present coverage in PR #27

- **MSG.PAK:** 24 localized ID keys for PT-BR and Spanish, including
  title options, selected events, and Dark Market equipment/shop greetings.
- **ARM9 data:** 12 UI/help/prompt strings for both languages, including
  Digivice menu help, inventory/quest/farm/save hints, shop balance and
  equipment-category prompts.
- No claim of complete story, full item/skill lists, image labels,
  or Japanese character support. All remaining entries still show English.
- Manual in-game testing is required for each graphical surface and
  translated dialog (especially control markers, newlines, clipping).
