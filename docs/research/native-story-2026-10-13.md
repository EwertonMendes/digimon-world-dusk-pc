# Dusk USA — Native runtime progression evidence (2026-10-13)

## Verified result

The user-supplied Digimon World Dusk USA ROM (SHA-256
`df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb`)
was prepared privately with ARM9/ARM7 title banks, recompiled using pinned
NDSRecomp `3a57236bb23d25dcb4caad7d58d733311062ff5e`, and linked into
its Linux x64 native runner. No commercial ROM or game-derived sources are
published here.

With FreeBIOS and synthesized firmware (`--freebios --generated-firmware
--boot direct`), the native debug server completed an automated route:

1. Both ARM CPUs boot; copyright and publisher screens render.
2. Digimon World Dusk **PUSH START** screen is rendered.
3. START opens New / Continue / Nintendo Wi-Fi Connection.
4. A chooses New and opens Boy / Girl selection.
5. Choosing Boy opens a working touchscreen keyboard.
6. Entering a player name and accepting it opens the four starter packs.
7. Accepting the Balance Pack opens three nickname screens.
8. Confirming the defaults advances to the first **in-game story map**,
   including character sprites and the screen A/B HUD.

The local scripted run finished at **2,765 VBlanks**, ARM9 approximately
**3,106,511,280 cycles**, ARM7 approximately **1,553,255,640 cycles**.
The evidence consists of deterministic raw framebuffer captures, a CPU
counter report, and a process log. These files are private because they
contain derived game artwork.

## Reproduction (private environment only)

```bash
python3 tools/test_dusk_native_story.py \
  --runner /path/to/native/nds_runner \
  --rom /path/to/your/Digimon-World-Dusk-USA.nds \
  --bios-dir /path/to/private-firmware-directory \
  --out .private/story-smoke
```

The script validates the exact original ROM SHA-256, checks the runner's
network-local debug protocol, injects actual DS key and touch events, advances
virtual frames, collects two framebuffer screenshots as PPM and writes a
JSON summary. It deliberately disables cartridge saves.

## Playable experimental preview

A local-only browser control/display bridge has also been tested. It
renders **real native-runner frames** (both screens) and forwards keyboard and
touchscreen input. Its proof-of-concept supports fullscreen, separate and
floating secondary screen modes, and keyboard input. It uses a Linux x64
runtime under Windows WSL2 with Ubuntu 24.04+, **not** an independent Windows
binary. The private game-derived runner is distributed only to the ROM owner,
not through the public GitHub repository or Actions artifacts.

This is an *interactive pre-alpha preview*, not a verified complete game port:
audio is absent in the browser frontend, saves are disabled, and battle
systems, long-term stability, all maps, overlays, and save compatibility
remain untested. A native Windows build is a separate task.

## Specific limitations and next technical gates

- Verify reachable maps, exploration, battles, menus and all three Digimon.
- Determine the correct Dusk cartridge save chip/type/size from reliable
  primary cartridge data, then validate persistence and format compatibility.
- Port the real native runner to Windows x64 with its SDL/Win32 host frontend,
  using locally generated game code (never pushed to public Git).
- Add a reproducible ROM-private Windows build script for end users.
- Test mouse, keyboard, controller, audio, frame pacing and display scaling.
- Compare behavior at key points with a local melonDS oracle when practical.
- Measure native dispatch coverage. A working intro does not prove overlays
  are covered or that the entire game is playable.

## Source, privacy and licensing

The title project may publish only its own tooling, configurations and
test code. Never commit the ROM, BIOS dumps, firmware identity, generated
game banks, derived images or personal saves.

When furnishing a private runner binary, include or make available its
corresponding GPL-3.0-or-later combined-work source and compatible upstream
notices. Third-party game code and artwork retain their own rights.

## Windows native runner feasibility — CI diagnosis

The compiler itself builds on Windows with LLVM/Clang and Ninja. The
**NDSRecomp hardware runner** does not yet pass the ROM-free Windows build.
With the diagnostic FreeBIOS path, progress reached the networking layer,
where `runner/vendor/melonds/net/Net_Slirp.h` includes POSIX `poll.h`;
MSVC/Clang Windows toolchains do not provide that header. Earlier
portability issues involved `libslirp` CRT file descriptors and Winsock
socket close semantics.

Avoid replacing missing interfaces with fake shims or disabling essential
features to claim compatibility. The Windows hardware-runtime feasibility
job now runs manually (`workflow_dispatch`) rather than gating the
well-validated, ROM-free C++ and NDSRecomp recompiler CI jobs.

**Only the Linux x64 runner has successfully executed Dusk through the story
intro**. The Windows `dusk_pc.exe` published by GitHub remains a synthetic
presentation test. The WSL2/browser native preview is the current real-game
interactive testing path and remains without sound and saves.
