# Dusk Localization Bridge — host-side foundation (experimental)

Updated 2026-10-15. This branch is a **partial implementation**, not a translated
Digimon World Dusk. Do not advertise or merge it as full in-game localization.

## What is implemented

- A C++20 typed catalog keyed by `(region, message_id)` with language choice
  `en-US`, `pt-BR`, `es-ES`, and `ja-JP`. Missing IDs/languages fall back
  to the original English string.
- UTF-8 validation and preservation of bracketed control tokens in catalog
  lookups. Translations are **not constrained to original byte length**.
- The `Settings → System → Language` host UI row. The selected language is
  persisted in `native-language-v1.cfg` in the native SDL preference directory,
  not in the `A6RE` EEPROM and not in versioned installation data.
- Basic host menu translations for English, Brazilian Portuguese and Spanish.
  Japanese host labels currently fall back to English. For now the font atlas
  is ASCII-only; the host labels use safe transliteration.
- ROM-free native catalog tests in GitHub Actions.

## What is **not** implemented

- No verified Dusk ARM9/overlay text-resolution hook has yet been found.
  The catalog is **not connected to the game dialogue renderer**.
- No original in-game messages have been modified or translated, even when
  selecting a language other than English.
- No CJK/diacritic-capable host glyph atlas yet.
- Automatic word wrapping, pagination, timing, guest UI rendering and sprite
  text localization all require real game analysis and tests.
- A successful Windows bundle build proves packaging, **not** that in-game
  translation works. The English guest game continues to operate as before.

## Why a renderer overlay is not safe yet

The original game may use `MSG.PAK` as well as ARM9/overlay string regions.
The text editor at
https://github.com/joaomlsantos/DigimonNDSRomEditor documents 16-bit string
codes, control markers and fixed-length ROM editing limitations. Rendering
translated SDL text over an already-rendered DS framebuffer would double the
text, obscure backgrounds, break typewriter animations and fail during screen
transitions. Patching guessed guest pointers risks invalidating AOT-bank
identity and corrupting save/gameplay state.

The desired production hook intercepts the *original text resolution* or
the glyph submission step, with an exact verified CPU/mode/bank generation,
while preserving the original implementation as an unconditional fallback.
For the latter method, do not draw English glyphs in the target region; only
draw translated glyphs in their stead. Never silence the entire framebuffer.

## Next reverse-engineering gate

1. With the **original verified USA ROM** in the private Windows runner,
   capture a known dialogue ID from `MSG.PAK`, a menu string, and a battle
   string. Record the title-specific call site, data source, guest buffer
   contract and chosen font renderer, without committing ROM-derived bytes.
2. Confirm which generated ARM9/overlay bank handles each call. Hook the
   exact, byte-qualified routine so direct generated calls and Tier3 fallback
   reach the same observer. Retain unmodified guest code execution on miss.
3. Translate one dialogue longer than the English original. Measure the real
   layout and implement word wrapping/pages using the guest's advance timing;
   ensure placeholder/colors and events are unchanged.
4. Validate English/Portuguese/English switches on the same 64 KiB EEPROM
   with backup, plus startup, title menu, character naming, Digimon screen,
   battle, save/load, scene transitions and UI clipping.
5. Only then enable gameplay language choice by default and add larger
   translated language catalogs.

No external ROM is required from a player: the existing single-file Windows
bundle embeds the verified USA ROM. The bridge is a host capability with a
per-player language setting; not a selectable ROM loader.

## Compatibility and rollback

- Original ROM SHA-256 remains unchanged.
- AOT bank generation, Tier3 fallback, game timing and EEPROM path unchanged.
- The last known playable Windows build can be used to roll back.
- An absent or corrupt language setting resolves to English.
- A missing or unsafe translation resolves to the original in-game text.
