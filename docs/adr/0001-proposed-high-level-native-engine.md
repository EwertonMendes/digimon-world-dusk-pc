# ADR 0001 — Proposed high-level native game engine, without Nintendo DS CPU interpreter

Status: **PROPOSED — user decision pending**, not adopted, not implemented.
Date: 2026-10-13
Scope: Digimon World Dusk PC, original user-owned USA cartridge reference.

## Decision being proposed

Stop treating iterative NDSRecomp overlay expansion as the final shipping architecture. Preserve the old v0.12 runnable research build as a private reference and correctness oracle; it must not be packaged into the new native engine.

Reimplement Dusk gameplay rules and scene orchestration as original C++20 code, using a native SDL3 application layer. The final game binary must not include NDSRecomp's runner, Tier3 ARM interpreter, ARM9/ARM7 guest executors, Nintendo DS memory-mapped device scheduler, virtual firmware or BIOS. It may use game-specific data extracted locally from the user's own verified ROM, subject to rights and lawful use. This is a **full reverse-engineered game reimplementation**, not a further static ARM recompilation. It is a large project; no timeframe or frame-rate result can be guaranteed before validating actual slices.

This is a proposal because the user must explicitly accept the substantial scope and functional-parity tradeoff. Do not merge to master merely by publishing this ADR.

## Why the previous plan repeatedly fell short

1. Current private Windows builds execute recompiled original ARM9/ARM7 alongside Tier3 ARM interpretation for uncovered addresses and dynamic overlay generations. The game still depends on a Nintendo DS hardware compatibility runtime.
2. Real owner v0.11 diagnostics: interval 19:21:04 has guest execution ~22.14 ms/frame, exact Tier3 ARM9 ~14.79 ms/frame and SDL present ~0.228 ms/frame, with 38 audio underrun notifications. This supports ARM9 interpreter as the dominant measured bottleneck in that sample; it does not prove all freezes are exclusively caused by ARM interpretation.
3. Seven regenerated overlays and about 1,967 generated candidate functions in overlay 7 still did not reliably eliminate battle damage, menu or transition hitches according to owner's v0.12 test. An increasing count of generated functions is NOT evidence that all live ARM control flow executes natively.
4. The 30Hz visual-present mode leaves original ~59.826Hz guest emulation/audio work unchanged, and therefore cannot cure expensive guest-frame deadlines.
5. Merely removing the interpreter or changing guest clock would break unknown code paths or game timing. The architectural goal is different: **do not use any guest ARM runtime** in the new game process.

## Proposed program modules and clean boundaries

- **app / platform**: SDL3 desktop window, fullscreen, controller/touch/mouse, video backends, timing and reliable application lifecycle. Portable Windows first, Linux/macOS thereafter. The Android runtime needs separate lifecycle/input/package work.
- **core**: deterministic fixed-step simulation, game state, command/event queue, scene coordinator, save/load schema and serialization. Gameplay never calls SDL/window APIs directly.
- **content**: a **private, versioned, ROM-identity-checked** import pipeline for static sprite tiles, palettes, background layouts, fonts, animations, audio, world maps, monster/item/trainer data and story/event scripts. Distinguish faithfully decoded fields from inferred formats and partially understood data. No cartridge bytes or copyrighted asset exports in public repo or CI.
- **ui**: PC-native menus, touch layout, battle HUD and preexisting five desktop layouts, swap F8, fullscreen F11. Reuse/reimplement approved layout geometry concepts, not NDSRecomp frontend internals.
- **gameplay/world**: maps, collision, encounters, area transitions, NPC interaction, triggers, dialogues, quests and story flags.
- **gameplay/battle**: turn and initiative rules, stat formulas, enemy selection, Digimon/skills/items, targeting, status/damage effects, encounter entry/exit and animations. Each mechanic must have native automated tests against documented original behavior; don't invent unknown formulas.
- **audio**: native mixer and streaming output with independent real-time callback, lock-free or carefully bounded producer ring, predecoded frequently used effects, explicit underrun/latency metrics. Never decode/load game resources or write diagnostics synchronously on the audio callback.
- **graphics/resources**: SDL3 GPU or appropriate backend (and software reference renderer for tests if useful), background sprite/tile composition and necessary 3D assets; asynchronous I/O/decompression, worker uploads only where supported by API, bounded caches. Do not place arbitrary I/O or decompression in a frame-critical scene-change path.
- **reference**: legacy private NDSRecomp only in offline/dev tools to observe behavior, obtain approved golden input/replay sequences and compare state/screens/sound. No reference runtime is linked or launched by the final app.

## Implementation phases and gates (do not shortcut)

0. **Inventory**: enumerate all ROM archives/files, compression and asset/script formats; document what is known vs unknown; create a rights/privacy safe importer contract. Preserve prior ROM hashes/test assets only in private workspace.
1. **Native engine skeleton**: genuinely native SDL3 executable that opens a window, handles 59.826Hz fixed ticks and asynchronous audio, with menu/scene transitions from synthetic original test data. **No Nintendo DS emulation code or ARM interpreter reachable in process**. ROM-free CI on Windows/Linux.
2. **Vertical playable slice**: private user-owned asset import + title screen, new-game UI, one navigable scene, party status submenu opened by S, transition and one complete battle: enemy entry, skill, damage, effects, item use, exit. Include native sound and menu controls. Baseline with original version offline.
3. **Correctness**: differential gameplay replay, reference screenshots, exact rule and save-state checks, map/event extraction, test every required combat branch, dialogue/quest flags and audio event timing. Never equate matching screenshot with semantic correctness.
4. **Performance gates**: 59.826Hz guest-equivalent gameplay clock (or precisely documented gameplay rules tick), frame rendering ~59.826 FPS on owner's Windows hardware; after warmup, p99 frame-work <=16.715ms, no >33.4ms scene-transition stalls in automated slice, **zero audio underruns** in repeated gameplay runs. Measure p99.9, worst and 1-percent lows; don't rely on 1-second averaged FPS. These are goals, not proven guarantees. OS scheduling can cause outliers; report honestly.
5. **Breadth**: implement all game maps, story events, NPCs, Digimon data, evolutions, combat abilities/items, animations, audio, saves, ending and hidden progression; performance and deterministic save/reload across long sessions. A single slice is not a full playable port.
6. **Release**: Windows private owner-only standalone native EXE, no browser, WSL, NDS runner or required ROM installation if privately packaged with assets. Source-only public CI; owner's actual game content remains private. Other platforms require separate tested native packaging.

## Before declaring final replacement complete

- Final EXE/module list and build-time dependency manifests contain NO ARM/Tier3/FreeBIOS/NDSRecomp runtime executables or code, and no external emulator process.
- Each scene, menu and battle runs from high-level original source logic and verified imported structured content.
- No hidden ARM interpretation on fallback or whole-game recompiled guest code path.
- All known gameplay progression, graphics, audio and persistence tests pass; user validates hardware performance and parity. Legal redistribution considerations handled before any public binary/content release.

## Alternatives considered

**A: Stay with guarded static recompilation and finish AOT/native coverage.** Potentially much less work and closest preservation of original semantics; could remove hot-path interpreter time if coverage completed. Still includes hardware-level DS compatibility and may require fallback for unknown dynamic code; does **not** meet the owner's literal wish to abandon NDS runtime. Keep archived as reference or an alternate faster port, not the high-level engine implementation.

**B: Recompile all ARM, delete Tier3 abruptly.** Rejected: uncovered code/dynamic overlays would fail; gives false confidence and corrupts correctness.

**C: Cap game simulation to 30Hz, buffer audio extra or fake drawn 60Hz.** Rejected as stutter cure: changes speed or hides missed guest deadlines, doesn't remove observed ARM9 ~10-19ms interpreter cost. Optional visual presentation settings may be revisited with evidence.

## Scope, risks, and compliance

- This could require substantially more engineering effort than completing AOT, including reverse-engineering the entire game's content formats, every scripted event, battle rules and animations. Never promise an instant 60FPS complete Dusk port.
- The current repo contains an original C++20 parser/layout/config base but **no implemented high-level battle, game state or scene engine**. SDL3 UX currently lives primarily in patches of the external runner and must be ported or redesigned.
- Reading a user's original ROM does not itself grant public redistribution rights to the game, art, code, music or brand. Never commit extracted game assets, ROM, recompiled copyrighted source, commercial music or packed private game EXE to PUBLIC GitHub or Actions.
- Preserve the v0.6 tested public base and v0.12 owner-only runtime as reference artifacts, but do not continue marking AOT coverage as 'port complete'.
