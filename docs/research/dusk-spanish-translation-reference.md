# Spanish Dusk translation: verified sources and native UI investigation

Status: **research only**. No third-party patch has yet been successfully retrieved,
applied, or validated against the authenticated owner ROM. Do not describe the
existing PIL-generated game sprites as visually approved; owner screenshots from
15 Oct 2026 show distorted, jagged labels and icon interference.

## Original 2013 release (Traductores DW)

- Original project: https://digimonworlddstraduccion.blogspot.com/p/traduccion-digimon-duskdawn-espanol.html
- Original team forum: https://traductoresdw.foroactivo.com/t178-parches-digimon-alba-y-digimon-ocaso-espanol
- Game title: Digimon Ocaso = Digimon World Dusk (USA), **not** Digimon
  World DS (the preceding standalone game) and not Dawn (Alba).
- Release: 17 May 2013. The authors distributed an **xDelta patch**, not the
  whole ROM. The blog's old Dusk link is http://adf.ly/P8RWE, which currently
  redirects to an inaccessible ad migrator.
- Their 2013 toolchain credits **Tinke by Pleonex** (editing Nitro graphics)
  and **CUE tools** (text compilation). These are author statements, not
  evidence that a particular NCGR/NCER was edited in a particular way.
- The team acknowledged that some accent glyphs were missing in particular
  menu fonts; we cannot assume the Spanish art/encoding is bug-free.
- A later forum post asked users to recover the lost xDelta patches. The
  third-party ROM copies available on ROM sites are *not* official patches.

## Reusable and auditable tooling

- Tinke original code (GPL-3.0):
  https://github.com/pleonex/tinke
- NitroPaint original code:
  https://github.com/Garhoogin/NitroPaint
- Dusk/Dawn ROM research/editor:
  https://github.com/joaomlsantos/DigimonNDSRomEditor
- Nitro 1D sprite mapping still needs exact OAM, VRAM, animation and palette
  validation. The old editor builds letters using Pillow's default desktop
  font, which is the wrong artwork source for final in-game buttons.

Do not import third-party binaries or source code into this repository until
license, provenance and compatibility are verified. Reuse technical methods
and source references, not unreviewed copyrighted game assets.

## Structural comparison when a genuine xDelta patch is recovered

1. Confirm the patch is Dusk/Ocaso **USA** and is not a downloaded game ROM.
2. Apply it to a temporary copy of the verified original using a trusted
   xdelta3 binary. For example, in an owner-only working directory:

   ```bash
   xdelta3 -d -s "Digimon World - Dusk (USA).nds" dusk-es.xdelta .private/dusk-spanish-reference.nds
   python tools/audit_spanish_dusk_reference.py \
     --original "Digimon World - Dusk (USA).nds" \
     --translated .private/dusk-spanish-reference.nds \
     --out .private/spanish-audit.json
   ```

3. Compare the source/reference NitroFS files **by decoded file content**,
   not by FAT positions, using the metadata-only report.
4. Inspect changed sprite resource entries by ID: `SPR_CHR.PAK`,
   `SPR_CEL.PAK`, `SPR_PAL.PAK`. Inspect changed `MSG.PAK` group IDs,
   graphic resources and ARM banks, then cross-check with Tinke/NitroPaint.
5. Reimplement approved Portuguese graphics as fixed-size, palette-verified
   Nitro assets; do not render PIL text atop existing English glyphs. Keep
   the source names and icon/backplate artwork intact; use pixel-accurate
   localization masks and check every animated frame.
6. Test in the real Windows runtime (S-menu, submenus, shop, save/resume and
   language switch) before releasing a new build.

The structural audit emits **only offsets-independent file names, lengths,
resource IDs, hashes and flags**. It does not export ROM content, graphics,
translation text or patched executable. No .nds/.sav/third-party ROM should
be added to Git commits or public Actions artifacts.

## Acceptance threshold

Do not promote the existing procedural-font in-place sprites as definitive.
Pixel integrity checks, animation references and release build success are
necessary but **not sufficient**: translated labels must be legible, not
cover the original art, and match the visual style of the authentic game.
Await game-level screenshots of all six buttons and Equipment Shop options.

## Replacement implementation prepared on PR #27

`tools/dusk_sprite_authored_art.py` and the native catalog generator support
an optional `artwork` array in each locale's existing sprite manifest.
Artwork has to be drawn **at the native OAM cell size**, not resized from the
PC presentation and not generated using Pillow desktop fonts. For example:

```json
{
  "id": 479,
  "source_sha256": "<verified original NCGR SHA-256>",
  "artwork": [
    {
      "cell": 0,
      "png": "art/479-state0.png",
      "regions": [[6, 32, 53, 16]]
    }
  ]
}
```

This JSON illustrates the format only; no artwork is currently checked in.
Each PNG must use exact `NCLR` palette colors at 1:1 pixel size; alpha is
forbidden; pixels beyond the caption masks are forbidden. The importer
detects conflicting animation data when different NCER cells share tiles,
validates the palette bank and re-renders each cell after editing. Metadata
and original file size remain unchanged. No external SDL label overlay or
rendered font is added.

When a sprite uses `artwork`, it must **not** also contain procedural
`edits`. This makes the transition to curated full-frame art explicit:
it is not a silent modification of the existing experimental graphics.
