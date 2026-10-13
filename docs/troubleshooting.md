# Troubleshooting

- `dusk_pc.exe` opens but no Digimon appears: expected. Current version only renders labeled synthetic presentation frames, not the game.
- ROM invalid: check user-provided file path, expected US version, and SHA-256 output. Corrupted header CRC16 is a hard error.
- Windows compiler not found: launch Developer PowerShell after installing Visual Studio C++ Build Tools; CMake can generate Visual Studio builds.
- Windows executable absent: check the Actions build status and job logs. Linux local builds do not include the Windows GUI.
- NDSRecomp bootstrap fails: inspect upstream tool requirements and the commit checked out; no proprietary BIOS, firmware or game ROM is fetched by the helper.
- Do not upload ROM dumps to Actions. The public repo must remain free of game-owned bytes.
