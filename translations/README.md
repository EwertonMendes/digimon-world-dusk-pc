## Game-owned animated sprite button labels (15 Oct 2026)

The 6-button Digivice/S-key menu was traced to the compressed game-native
`SPR_CHR.PAK`, `SPR_CEL.PAK`, `SPR_PAL.PAK` resource triplets:
- 477 Digimon (proper name retained)
- 478 DigiFarm (proper name retained)
- 479 Items → Itens / Objetos
- 480 Save → Salvar / Guardar
- 481 Quests → Missões / Misiones
- 482 Tamer Info → Treinador / Entrenador

The source ROM SHA-256 and each source NCGR subresource SHA-256 are pinned in
`translations/sprites/{pt-BR,es-ES}/manifest.json`. The renderer rebuilds the
original Nintendo DS RLE files, **not an external overlay**. The earlier experimental version **incorrectly** treated Nintendo DS
1D-128-byte OAM indices as 32-byte tile offsets. It also added new tile
banks, which caused overlapping images and corrupt menu graphics. That
approach was removed. The corrected parser uses NitroPaint's verified
mappingMode=2 stride (4 x 32-byte tiles per OAM character index). Its
four animation states already occupy independent 64-tile ranges
[0..63, 64..127, 128..191, 192..255]. Translation now changes pixels
**inside the existing original NCGR**, never expands it and **never edits
NCER or palettes**. The rebuilt CHR PAK is placed in verified unused
ROM padding only in memory. Original ARM9, NCER, NCLR and saves are
unchanged.

Generate using the original ROM:
```bash
python -m pip install Pillow==11.3.0
python tools/generate_dusk_sprite_header.py --rom 'Digimon World - Dusk (USA).nds'
```
CI compiles a checksum-pinned C++ asset catalog. Tests verify byte-for-byte
preservation of ARM9 and original PAKs, an **unchanged NCER file table**,
atomic rejection on checksum mismatch, correct four-state 128-byte mapping,
and pixels differing only inside declared label regions (never icons/frames).
True native Windows gameplay screenshots still require owner playtesting;
asset-level previews are not equivalent to full runtime coverage.

**Remaining interface gap:** Equipment Shop `Buy/Sell/Quit` is not included.
A source scan located its ARM9 entries near ROM offset 1130728/1130780,
but each action is followed immediately by control codes and dynamic text.
Those are **not safely expandable in place**. They require relocating the
actual ARM9 text/script resource and its verified references, or a game-native
string-resolution hook, before translation. Do not claim the shop is
fully localized. The rest of the 14,223 MSG.PAK messages also need cataloging.

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

## Native graphic resources (new)

Game-owned labels baked into Nintendo DS image resources are handled as native
NitroFS files, **not overlaid** over the SDL framebuffer. The new
`dusk_graphics_runtime.hpp` can relocate verified `NCGR/NCLR/NSCR/NCER`
files to free cartridge padding, rewrite their FAT entries in memory, and
preserve the original unpatched ROM and saves. It validates the original
asset CRC, file bounds, padding and all replacements before any write.

Each language has `translations/graphics/<locale>/manifest.json` with records:

```json
{
  "rom_path": "dat/bg/example.NCGR",
  "asset": "example-translated.NCGR",
  "expected_sha256": "<exact SHA-256 of this source asset>"
}
```

Replacement files must be valid native Nitro graphics generated/edited with
a proper tile-and-palette-aware editor (Tinke/NitroPaint). Run
`python tools/generate_dusk_graphics_header.py --rom '<original game>.nds'`
to generate embedded C++ resources from the manifests. The native Windows
owner-only CI validates the original source ROM and generated bytes.

The manifests are **currently empty** because the original graphics were
only inventoried, not yet translated. This feature is groundwork, not
a completed menu translation. All non-catalogued graphics remain original.

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
