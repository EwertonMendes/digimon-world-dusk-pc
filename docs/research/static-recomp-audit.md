# Recompilation evidence — Dusk USA, 2026-10-13

This report is based on the **user-provided, SHA-256 verified US ROM**, analyzed locally with the upstream NDSRecomp compiler pinned to `3a57236bb23d25dcb4caad7d58d733311062ff5e`. It contains no game bytes or compiled ROM-derived code. The generated bodies are private and uncommitted.

## Concrete local result

| Bank | Input code | Candidate functions | Candidate ARM/Thumb | Instructions audited | Unknown indirect outcomes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dusk ARM9 main excluding secure-area prefix | 1,247,384 B | 2,674 | 2,674 / 0 | 67,408 | 94 |
| Dusk ARM7 main | 166,336 B | 1,365 | 1,357 / 8 | 513 | 39 |

- `nds_recompile --audit` returned success for both hash-verified input binaries.
- `nds_recompile --out ... --bank ...` generated real C body/headers/dispatch files for both banks.
- ARM9 reloc scan hit an internal 4,194,304 step cap; ARM7 stopped when PC left the module.
- ARM9 audit also identified 8 undefined instruction encodings; ARM7 reported 3 undefined outcomes. These are signs that heuristically discovered functions/data boundaries require independent verification.
- The candidate-function totals are not validated symbol maps. Numerous computed branches and dynamic overlays remain undiscovered.
- None of this proves a successful runtime boot or execution of the game.

## What this proves (and doesn't)

This establishes that the static ARM->C emission pipeline can consume **this exact ROM's primary binary images**, preserving the original bytes privately, and pass its own code-generation stages.

It does **not** establish that the emitted code correctly covers every runtime branch, handles the entire secure area, dispatches overlays dynamically, or produces real audio/video. An executable built around those generated banks can still fail before the logo. Treating recompiler exit code zero as gameplay validation would be a severe correctness error.

## Native runtime next gate

The upstream runtime expects verified BIOS/firmware execution banks or a specially validated FreeBIOS direct-boot option; an offline FreeBIOS-only diagnostic build is being investigated in a *private, local upstream checkout*.

The required next evidence is a reproducible launch of this ROM, actual ARM7/ARM9 instruction progress, frame captures from the real game, and successful input and save behavior. Until then all distributed Windows frontends are expressly **presentation prototypes**, not playable Dusk.

## Reproduction locally

```sh
python3 tools/prepare_dusk_recomp.py --rom /path/to/DigimonWorldDuskUSA.nds
python3 tools/prepare_dusk_recomp.py --rom /path/to/DigimonWorldDuskUSA.nds --recompiler /path/to/nds_recompile --emit
```

Results under ignored `.private/recomp/` must never be committed to a public repository.
