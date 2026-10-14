# Owner-only on-demand native Windows playtest (v0.17)

This is an **opt-in** GitHub Actions workflow:
`.github/workflows/dusk-native-windows-playtest.yml`.
It is separate from the ROM-free CI workflow.

## Workflow and deliverable

- Select **Actions → Dusk native Windows game (owner playtest) → Run workflow**.
- Enable the rights/packaging confirmation and execute.
- A successful run uploads
  `Digimon-Dusk-PC-Windows-v0.17-PLAYTEST-NATIVE-GAME`,
  containing one `Digimon-Dusk-PC-Windows-v0.17-PLAYTEST.exe`,
  its SHA-256 checksum and a short README.
- Download the ZIP, extract the EXE, and **double-click** it on Windows 10/11
  x64. No WSL, ROM selection, compilers or Python required on the
  player's Windows PC.
- Hold **Shift while opening** to access save-backup recovery UI.

## What gets compiled

1. Exact Dusk USA ROM SHA-256 checked before any generation.
2. Pinned NDSRecomp at `3a57236bb23d25dcb4caad7d58d733311062ff5e`
   and pinned `recomp-ui` at
   `41c88ffea852b970af8d50312620b17404e455ad`.
3. Original ARM9/ARM7 **main bank** compiled statically using
   `tools/prepare_dusk_recomp.py`. FreeBIOS images are compiled from
   their openly available source in NDSRecomp.
4. SDL3 native Windows UCRT64 runner with the existing Dusk interface patches
   and original EEPROM 64KiB support.
5. Go Windows GUI launcher `v0.17` wraps the actual runner, SDL3.dll and
   matching ROM into one SHA-256-verified PE file. If the MSYS2 SDL3 DLL
   imports `libiconv-2.dll`, that redistributable DLL is also embedded
   into the same EXE and installed next to SDL3; the player installs nothing.
6. A `--verify-bundle` subprocess checks the resulting executable before
   upload. This checks packaging identity, **not** gameplay compatibility.

## Explicit limitations

**The first CI-generated candidate is not claimed equivalent to the
previous owner-built v0.16 native code coverage.** The prior owner's
binary-specific AOT coverage/overlays and private generated banks were not
part of the Git repo. This initial workflow emits the two main title banks;
runtime overlay gaps continue through Tier3. It may perform worse than v0.16
until verified overlay generations are reconstructed from owner captures.

The Windows build gates unexpected runtime DLL imports. If SDL3's
transitive dependencies change, packaging fails until the declared
bundled dependency list is updated and verified.

No automated full story QA or Windows on-screen interaction is performed by
the CI runner. The owner must validate visual rendering, sound, in-game
Save/Continue, maps, gameplay menus and progress. A green build is a
**playtest candidate**, not proof of full campaign completion.

## Public repository warning

The game ROM is currently checked into this **public** repository by the owner.
Workflow artifacts of this job additionally contain the same ROM inside the
playtest EXE. Only execute with authority to distribute those materials.
The pinned NDSRecomp code is **PolyForm Noncommercial 1.0.0**; permission for
the ROM and the code have independent conditions. Public CI source-only
prototype artifacts remain distinct from real gameplay packages.

Build failures or uncertain identity abort the workflow rather than silently
substituting a synthetic runner or external emulator.
