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

## Tiny experimental gameplay catalog

To verify the end-to-end pathway without creating unreviewed story translations,
`dusk_msgpak_runtime.hpp` currently replaces only 5 message IDs:

- Group 0, IDs 0 and 1 — party wipe / flee messages.
- Group 1, IDs 0 and 1 — NPC dialogue about TV programs and comedies.
- Group 3, ID 2 — NPC's lucky-day dialogue.

These have PT-BR and ES translations using the original DS font codes.
**The rest of the story, menus, Digimon descriptions, items and battle
strings remain in English.** Japanese also remains in English. This is not
a full localization release. The host Settings UI shows a partial-translation
notice, and accents are rendered as composited Inter glyphs.

The existing separate `TranslationCatalog` is an ID-based host-side
library and still needs to be connected to a full, human-reviewed message
catalog; it should not be confused with the five game-resource test entries.

## Before promoting the PR

- Run the new owner playtest EXE, select PT-BR and restart. Confirm that
  a reachable translated event really appears as a replacement, with
  correct accent glyphs, line breaks and character animations.
- Reopen a previous 64 KiB Dusk EEPROM save (not a save state), verify
  progress and normal battle transitions, then switch back to English.
- Verify original game-menu labels still behave, especially typewriter
  dialogue delays, scripted [END] markers and runtime variables.
- Convert the proof translations into external validated text catalogs,
  translate the remaining 138 groups, and define an explicit source
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
