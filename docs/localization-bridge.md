# Digimon World Dusk localization: in-memory resource prototype

Status: experimental. Keep PR #27 in draft until a Windows owner playtest
proves that the original engine actually renders the translated messages.

## Confirmed against the original owner ROM

The exact Dusk USA ROM (SHA-256
`df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb`)
contains `dat/MSG.PAK` at NitroFS FAT file ID 23. It has 138 indexed
subfiles. The subfiles have a 32-bit offset table followed by variable-length
2-byte character streams. Dialogue entries terminate in **FE FF ([END])**,
while other records terminate in **FF FF**. The original game character map
already supports Portuguese diacritics.

An isolated Windows Actions proof loaded the ORIGINAL ROM, rebuilt the text
pack for PT-BR and ES, placed each resulting pack in unused game-card padding
and confirmed that the original ARM instructions, cartridge resource bytes
and save-related data were untouched. This proves resource relocation, not
that all translated messages have been visited in gameplay.

## Current runtime flow

1. Launcher verifies its signed embedded original ROM and executable.
2. Launcher reads `native-language-v1.cfg` from SDL's DuskPC preference
   folder and passes `NDS_DUSK_LANGUAGE` to the native runner.
3. The runner verifies the **original** ROM SHA-1. Only after this gate does
   the opt-in Dusk-specific hook rebuild the selected MSG.PAK text group.
4. The replacement is moved into proven unused bytes within the original
   64 MiB cartridge capacity, and the NitroFS FAT entry 23 is updated
   **in the host's memory**, never on disk. Program ARM9/ARM7 banks,
   guest ROM file, and saves are not rewritten.
5. The normal DS text renderer consumes the updated pack when that message
   group is requested. No SDL overlay or masking of English glyphs is used.

The selected language takes effect on **the next game launch**, not
immediately for a dialogue already loaded in guest RAM.

On any missing/invalid translation, record-format problem, unexpected ROM
or insufficient padding, the host logs the reason and continues with the
unmodified English original. It never patches guest execution addresses
nor changes the EEPROM.

## Repeatable experimental gameplay catalog

The verified MSG.PAK resource catalog now has **24 Portuguese and Spanish
message IDs**. The selected texts were inspected in the original cartridge,
including original line breaks, green/red color toggles, player-name tokens,
and FEFF record terminators. The rebuilder refuses any record whose special
tokens differ between source and translation.

The selections are intended to be reachable from existing saves:

- **Title/menu string (124/45):** New, Continue, Nintendo Wi-Fi Connection,
  Back. Select a non-English language in Settings, exit and restart. Check
  whether the cartridge-driven title choices become Novo/Continuar/Voltar
  or Nuevo/Continuar/Volver.
- **Confirmation (125/33):** Are you sure? (context may vary).
- **Shops:** Equipment, consumables, farm goods, and Farm Island upgrades
  in group 70 (IDs 31–34), plus equipment/consumables greetings in
  groups 63, 64, 69 and 71. Visit a shopkeeper rather than waiting for
  a story dialogue.
- **Dark Square:** player-name greeting messages 66/90 and 69/35;
  **elevator:** group 72/26.
- **Earlier five proof records:** party defeat/fleeing and three NPC lines.

Exact MSG.PAK IDs are validated, but **their runtime callsites have not
been traced**. The title text may be used in a particular game context rather
than always on the title screen. That is a game-playtest hypothesis, not
a certified guarantee. No gameplay automation was used to claim otherwise.

All other in-game strings remain English. Japanese remains unsupported.
The host preference changes gameplay resources on **next restart**.
We did not implement dynamic relayout for longer multi-page dialogue; the
selected messages have conservative hand-authored line breaks, keeping the
original end/color/control markers.

### Simple owner test

1. Select Portuguese (Brazil) or Spanish in PC Settings.
2. Close the application and reopen the new test EXE.
3. Observe the title options (Novo / Continuar / Voltar, if actually
   read from MSG.PAK 124/45). If still in English, do not assume the
   MSG.PAK rebuild failed: report the context for further hook tracing.
4. Continue an existing save. Talk to shopkeepers and to NPCs in Dark
   Square, if accessible; check elevator interaction.
5. Revert to English and restart. Original strings and save must remain
   unchanged. Report screenshots of any overlong or truncated message.

A private-ROM test checks **every one of the 24 translated encoded records**,
and verifies that a neighboring unmodified record remains byte-identical.

## Additional ARM9 in-memory interface text

A second, independent data-only adapter translates a verified subset of
repeatedly visible original 16-bit ARM9 strings, including Digivice/S-key menu
bottom help (Digimon progress, inventory, quests, DigiFarm, Tamer information
and save progress) and shop prompts (balance, stock, action question, category
selection, insufficient Bits and full inventory).

- The 12 entries per language are stored in
  `translations/arm9/<locale>.json`; the checked-in C++ table is generated.
- Each exact original value is checked in the owner's ROM **before any data is
  changed**. The replacement must fit the original encoded slot, so nearby
  strings and ARM9 code stay untouched. Anything unknown safely remains
  English.
- The native sprite pack adapter now replaces **four Digivice button
  graphics** in PT-BR (479 Items -> Itens; 480 Save -> Salvar; 481 Quests ->
  Missões; 482 Tamer Info -> Treinador) and corresponding Spanish labels.
  The two proper names (477 Digimon; 478 DigiFarm) deliberately remain
  unchanged. Secondary item/equipment captions (388/389) are also in the
  per-language sprite manifests. This is an NCGR graphics edit, not an
  SDL/desktop text overlay.
- Dusk's actual NCER mapping uses **1D 128-byte OAM names** (mode 2):
  the four animation cells start at decoded tile indices 0, 64, 128, 128,
  and the last two cells share the third frame. All original 192 tiles,
  NCER cell definitions, NCLR palettes and visible icon pixels outside the
  declared text-only masks remain unchanged. Multi-row captions are
  cleared using original palette indices rather than expanding the VRAM
  bank or relocating OAM structures.
- Deterministic owner-ROM preprocessing checks decoded source SHA-256,
  RLE roundtrip, original cell mapping, fixed NCGR size, unchanged pixels
  outside the defined label areas, and PT-BR/Spanish relocation against the
  unmodified cartridge. The Windows pipeline can render side-by-side
  comparisons for all four states. **These are isolated sprite validations;
  no automated screenshot of the actual game menu has been certified.**
- **Equipment Shop Buy / Sell / Quit remains untranslated.** The
  Buy {VAR} for ? and Sell {VAR} for ? data records at original ARM9
  offsets 1130728/1130780 (and quantity variants 1130824/1130908)
  are tightly packed with control tokens. Direct 32-bit absolute-pointer
  searches did not find callers. Length-changing writes are forbidden
  until a verified message dispatcher or index-based callsite can supply
  a correctly sized native buffer without corrupting adjacent records.

Translations are authored in locale JSON files, with generators and safeguards
documented in `translations/README.md`.

## Before promoting the PR

- Run the new owner playtest EXE, select PT-BR and restart. Confirm that
  a reachable translated event really appears as a replacement, with
  correct accent glyphs, line breaks and character animations.
- Reopen a previous 64 KiB Dusk EEPROM save (not a save state), verify
  progress and normal battle transitions, then switch back to English.
- Verify original game-menu labels still behave, especially typewriter
  dialogue delays, scripted [END] markers and runtime variables.
- Convert the proof translations into external validated text catalogs,
  translate the remaining messages across 138 groups, and define an explicit source
  identity and token schema. ARM9 and overlay strings require a separate
  extraction/rendering path, not a guessed MSG.PAK ID.
- Extend Unicode host glyph coverage for Japanese before enabling CJK menus.
- Do not mark fully localized until the menu, story, item, battle, naming
  and graphical text surfaces have been inventoried and verified.

## Reproducing the resource validation

Run the owner-only native workflow with `research_only=true`. It executes
`tools/probe_dusk_strings.py` and
`tests/msgpak_runtime_probe.cpp` against the verified private ROM,
exports numeric metadata, and does **not** publish any modified ROM.
The normal native playtest workflow recompiles the same code into the
single-file Windows EXE, with the original ROM embedded as before.
