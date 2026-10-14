#!/usr/bin/env python3
"""Extract and verify the exact previously built native AOT runner for repack.

We do not modify/recompile ARM game code. Only the Go Windows desktop
launcher is rebuilt to isolate its appVersion; original ROM, SDL3 and the
original runner must all pass full SHA256 bundle integrity verification.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import struct
import zipfile

MAGIC = b"DUSKPACKv1!!"
FOOTER_SIZE = 52
ROM_SHA256 = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"
RUNTIME_FILES = {"runner.exe", "SDL3.dll", "game.nds", "libiconv-2.dll"}
EXPECTED_FILES = RUNTIME_FILES | {"window-icon.rgba", "dusk-splash.bmp"}


def verified_extract(executable: Path, destination: Path, expected_sha256: str) -> dict[str, str]:
    if not expected_sha256 or len(expected_sha256) != 64:
        raise ValueError("Expected full known original AOT build SHA256")
    data = executable.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError("Wrong native AOT source executable hash")
    if not data.startswith(b"MZ") or len(data) <= FOOTER_SIZE:
        raise ValueError("Not a Windows launcher PE")
    footer = data[-FOOTER_SIZE:]
    if footer[:12] != MAGIC:
        raise ValueError("Missing native bundle trailer")
    length = struct.unpack_from("<Q", footer, 12)[0]
    if not length or length > 150 << 20 or length > len(data) - FOOTER_SIZE:
        raise ValueError("Malformed bundled archive length")
    blob = data[-FOOTER_SIZE-length:-FOOTER_SIZE]
    if hashlib.sha256(blob).digest() != footer[20:]:
        raise ValueError("Incorrect bundled archive SHA256")
    contents: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if set(z.namelist()) != EXPECTED_FILES:
            raise ValueError("Missing or extraneous original native dependencies")
        for name in EXPECTED_FILES:
            record = z.getinfo(name)
            if record.file_size > (100 << 20):
                raise ValueError(f"Oversized native file: {name}")
            contents[name] = z.read(name)
    if hashlib.sha256(contents["game.nds"]).hexdigest() != ROM_SHA256:
        raise ValueError("ROM identity mismatch")
    for name in RUNTIME_FILES - {"game.nds"}:
        if not contents[name].startswith(b"MZ"):
            raise ValueError(f"Invalid Windows PE file: {name}")
    if b"SDL3.dll" not in contents["runner.exe"]:
        raise ValueError("AOT runner is not the SDL3 Windows binary")
    destination.mkdir(parents=True, exist_ok=False)
    result: dict[str, str] = {}
    for name, file_data in contents.items():
        if name not in RUNTIME_FILES:
            continue  # Replace cosmetic resources with newly generated, validated assets.
        (destination / name).write_bytes(file_data)
        result[name] = hashlib.sha256(file_data).hexdigest()
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sha256", required=True)
    args = ap.parse_args()
    hashes = verified_extract(args.exe, args.out, args.sha256)
    for name in sorted(hashes):
        print(name, hashes[name])


if __name__ == "__main__":
    main()
