# Digimon World Dusk (USA) — verified header analysis

Validated locally against the user-supplied `Digimon World - Dusk (USA).nds` copy on 2026-10-13. Original ROM and game-derived data were not committed.

| Field | Verified value |
|---|---|
| Internal title | `DS2_USA_DUSK` |
| Game code | `A6RE` |
| Maker code | `AF` |
| ROM size | 67,108,864 bytes (64 MiB) |
| MD5 | `35b6209cf0a69b68a5f78c07d9433c27` |
| SHA-256 | `df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb` |
| Header CRC16 | `0x2c83` (matches calculated) |
| ARM9 ROM offset | `0x4000` |
| ARM9 RAM | `0x02000000` |
| ARM9 entry | `0x02000800` |
| ARM9 size | 1,249,432 bytes |
| ARM7 ROM offset | `0x280140` |
| ARM7 RAM/entry | `0x02380000` |
| ARM7 size | 166,336 bytes |
| ARM9 overlays | 18 (576 bytes total / 32-byte entries) |
| ARM7 overlays | 0 |
| FAT records | 8,868 |

Some ARM9 overlays share load addresses and must be treated as alternative dynamically loaded banks, NOT simultaneously mapped into the same memory. Overlays reference FAT file IDs and contain separate BSS regions. The first overlay's RAM address is `0x021FAB00`. Loader/linker behavior and actual entrypoints remain to be investigated with Ghidra. These fields are not by themselves proof that the game can boot in NDSRecomp.

External research starting points:

- <https://github.com/joaomlsantos/Digimon-World-Dawn-Dusk-Research-Notes>
- <https://github.com/joaomlsantos/DigimonNDSRomEditor>
- <https://github.com/pedro-javierf/NTRGhidra>
