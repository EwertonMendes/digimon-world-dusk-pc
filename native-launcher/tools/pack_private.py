#!/usr/bin/env python3
"""Append a locally generated private ROM + recompilation runtime to ROM-free Windows launcher.
Never send resulting executable to public GitHub or public Actions artifacts.
"""
import argparse
import hashlib
import io
from pathlib import Path
import struct
import zipfile

EXPECTED_SHA256 = 'df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb'
MAGIC = b'DUSKPACKv1!!'
assert len(MAGIC) == 12

def verify_pe_amd64(content, description):
    if len(content) < 512 or content[:2] != b'MZ':
        raise ValueError(f'{description} is not a Windows PE executable')
    pe_offset = struct.unpack_from('<I', content, 0x3c)[0]
    if pe_offset + 6 > len(content) or content[pe_offset:pe_offset+4] != b'PE\0\0':
        raise ValueError(f'{description} has invalid PE header')
    arch = struct.unpack_from('<H',content,pe_offset+4)[0]
    if arch != 0x8664:
        raise ValueError(f'{description} machine 0x{arch:04x} is not AMD64')

def assemble(launcher, rom, runner, destination):
    launcher = Path(launcher).read_bytes()
    rom = Path(rom).read_bytes()
    runner = Path(runner).read_bytes()
    verify_pe_amd64(launcher, 'launcher')
    verify_pe_amd64(runner, 'NDSRecomp game runtime')
    rom_sha = hashlib.sha256(rom).hexdigest()
    if rom_sha != EXPECTED_SHA256:
        raise ValueError(f'ROM hash mismatch: {rom_sha}; expected only verified US Dusk')
    contents = io.BytesIO()
    with zipfile.ZipFile(contents,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('runner.exe', runner)
        z.writestr('game.nds', rom)
    blob = contents.getvalue()
    footer = MAGIC + struct.pack('<Q', len(blob)) + hashlib.sha256(blob).digest()
    assert len(footer) == 52
    output = launcher + blob + footer
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(output)
    return {'name':str(destination),'size':len(output),'sha256':hashlib.sha256(output).hexdigest(), 'romSHA256':rom_sha,'privateContent':'game ROM and recompilation runtime; DO NOT publish'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launcher',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--runner',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=assemble(a.launcher,a.rom,a.runner,a.out)
    for key,value in result.items():print(key,value)
