# Native Dusk Windows one-click builds: v0.19 owner playtest

**Player experience:** the Windows x64 build is a single `.exe`. No WSL,
compilers, command-line work or external dependency installation.

## Two routes, one source of truth

In **Actions → Dusk native Windows game (owner playtest) → Run workflow**,
check `approve_game_bundle` to acknowledge that the game ROM will be
included in an executable artifact.

- **Full native build:** `fast_repack=false` (default). Build from the exact
  USA original ROM and pinned NDSRecomp/recomp-ui, validate ROM and original
  runtime code pages, regenerate title ARM9/ARM7/overlay banks, compile the
  actual Windows SDL3 runner, build Go launcher, and verify the embedded
  ROM/PE/DLL checksum package. This is required whenever emulation, audio,
  graphics, bank selections, source patches or the compiler changes.
- **Fast launcher-only repack:** `fast_repack=true`. Download the known-good
  native Windows runner artifact from exact, successful run
  [38622682716](https://github.com/EwertonMendes/digimon-world-dusk-pc/actions/runs/38622682716)
  and require its **exact SHA-256**, then extract the signed-by-hash ZIP
  payload, test/rebuild the Go desktop launcher and repack it as a Windows PE.
  This mode never recompiles game ARM code. It is only suitable for
  launcher/menu UI changes that do *not* require changing native runner code.
  The pinned source artifact is retained for seven days; repack intentionally
  fails when it expires. Do not silently fall back to older game builds.

The last v0.19 **full** package is
`Digimon-Dusk-PC-Windows-v0.19-SCENE-AUDIO-PLAYTEST-NATIVE-GAME`.
The fast-only launcher package is separate:
`Digimon-Dusk-PC-Windows-v0.19-LAUNCHER-REPACK-GAME`.
Neither is automatically merged into `master`.

## Why full Windows builds have been slow

From native Windows CI run
[38622682716](https://github.com/EwertonMendes/digimon-world-dusk-pc/actions/runs/38622682716),
the complete job took ~23m54s. **20m18s** was the
`Build Windows x64 SDL3 native runner from original code` step.
MSYS2 installation was ~1m29s. ARM code generation itself took only ~6s.

The bulk of the delay is the **huge optimized generated C objects**. Repeating
them on every one-line Python/workflow edit is wasted work.

### Build speed protections added after that run

1. UCRT64 `ccache` is installed and explicitly connected to CMake's C and
   C++ compiler launchers. **Compiler input fingerprints** determine which
   objects may be reused. The full build continues with fresh generation and
   full verification; stale compiled code does not get to bypass checks.
2. `actions/cache/restore@v4` and `actions/cache/save@v4` persist at most
   ~1.5 GiB of ccache objects across Windows runs, with input-sensitive
   primary keys and reusable restore-key prefix. Cache hits and misses are
   printed at the end. Cache restore/save are best-effort; an outage does not
   break actual game compilation.
3. Ninja's compiled runner parallelism is cautiously raised from **2 to 3**
   jobs. Revisit only after inspecting memory stability and timings.
4. Superseded manual builds in the *same branch* are automatically cancelled
   to avoid wasting a runner on an outdated game revision. A finished build is
   never silently substituted into a newer version.

**Expected impact:** a cold full build can still be slow; later builds with
unchanged generated C should reuse objects and become faster. Actual speed
must be taken from GitHub job timings and `ccache --show-stats`, not assumed.
The separate fast repack takes only the launcher/test/verification steps.
The compiler cache is not a game-save cache, and it does not change emulator
timing, game audio or rendering.

## Runtime and integrity

The exact Dusk USA ROM must SHA-256 match
`df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb`.
NDSRecomp is pinned to `3a57236bb23d25dcb4caad7d58d733311062ff5e`;
recomp-ui to `41c88ffea852b970af8d50312620b17404e455ad`.
The SDL3 UCRT64 runner packages needed DLLs inside the one-click EXE,
without dependency setup on the player's PC. The launcher verifies member
checksums before installation. The cartridge's **actual 64KiB EEPROM save**
stays at
`%LOCALAPPDATA%\\DuskNativePC\\userdata\\A6RE\\saves\\dusk.sav`.
Hold Shift at launch for save/backups management.

The v0.19 native AOT profile builds more ARM9 dispatch coverage than the
v0.15 baseline but does **not** yet restore the ARM7 baseline. That is why
the existing PR remains **draft**. The `--verify-bundle` and CI success
checks verify generated binaries, package integrity and test fixtures; they
do **not** prove no audio/video frame hitches. Re-test area transitions,
S-menu/submenus, battle entrance and HP/MP changes on Windows before merging.

## Rights and visibility

The owner uploaded the ROM to this currently **public GitHub repository**,
and manual owner game-build artifacts additionally include the ROM in the
one-click executable. Only publish and distribute assets you have rights to.
NDSRecomp has its own PolyForm Noncommercial 1.0.0 terms independent of
ROM permissions. Public ROM-free CI source-build outputs are separate from
opt-in game-containing Windows artifacts.
