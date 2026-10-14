#!/usr/bin/env python3
"""Bundle a verified, user-owned Dusk ROM and native SDL3 runner in one private EXE.

NEVER run this in public CI or commit its output. All game-derived files stay local.
"""
import argparse
import hashlib
import io
from pathlib import Path
import struct
import zipfile

from verified_dispatch_rows import verify_dispatch_growth

MAGIC = b'DUSKPACKv1!!'
ROM_SHA256 = 'df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb'

def build(launcher: Path, runner: Path, sdl: Path, rom: Path, output: Path,
          baseline: Path | None = None, candidate: Path | None = None,
          iconv: Path | None = None,
          window_icon: Path | None = None) -> dict:
    if (baseline is None) != (candidate is None):
        raise ValueError('Provide both --baseline-dispatch and --candidate-dispatch')
    # Game-derived banks are not uploaded. Compare byte-validated C dispatch
    # tables locally before accepting an owner-private one-click executable.
    dispatch_report = (verify_dispatch_growth(baseline, candidate)
                       if baseline is not None else None)

    files = {
        'runner.exe': runner.read_bytes(),
        'SDL3.dll': sdl.read_bytes(),
        'game.nds': rom.read_bytes(),
    }
    if iconv is not None:
        files['libiconv-2.dll'] = iconv.read_bytes()
    if window_icon is not None:
        icon_bytes = window_icon.read_bytes()
        if not icon_bytes.startswith(b'BM') or not 54 <= len(icon_bytes) <= 1 << 20:
            raise ValueError('SDL window icon must be a valid bounded BMP file')
        files['window-icon.bmp'] = icon_bytes
    if hashlib.sha256(files['game.nds']).hexdigest() != ROM_SHA256:
        raise ValueError('Expected the verified Dusk USA ROM')
    for name in ('runner.exe', 'SDL3.dll', 'libiconv-2.dll'):
        if name not in files:
            continue
        if not files[name].startswith(b'MZ'):
            raise ValueError(f'Not a Windows PE file: {name}')
    if b'SDL3.dll' not in files['runner.exe']:
        raise ValueError('Runner must import SDL3.dll; headless/browser runner rejected')
    binary = launcher.read_bytes()
    if not binary.startswith(b'MZ') or binary[-52:-40] == MAGIC:
        raise ValueError('Launcher is missing or already bundled')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    data = stream.getvalue()
    if not data or len(data) > 150 * 1024 * 1024:
        raise ValueError('Payload too large')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(binary + data + MAGIC + struct.pack('<Q', len(data)) +
                       hashlib.sha256(data).digest())
    return {
        'dispatch_check': dispatch_report,
        'exe': str(output),
        'bytes': output.stat().st_size,
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'rom_sha256': ROM_SHA256,
        'note': 'Native SDL3 host; use only in private ROM-owner environment',
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('launcher', 'runner', 'sdl', 'rom', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--baseline-dispatch', type=Path)
    p.add_argument('--candidate-dispatch', type=Path)
    p.add_argument('--iconv', type=Path, help='Windows libiconv-2.dll needed by certain SDL3 builds')
    p.add_argument('--window-icon', type=Path, help='BMP displayed by the SDL3 game window')
    args = p.parse_args()
    print(build(args.launcher, args.runner, args.sdl, args.rom, args.output,
                args.baseline_dispatch, args.candidate_dispatch, args.iconv))

if __name__ == '__main__':
    main()
