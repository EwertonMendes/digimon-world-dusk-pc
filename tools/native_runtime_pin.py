#!/usr/bin/env python3
"""Provenance gate: reuse native Windows runner only when native inputs are identical."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_FILE = ROOT / "tools" / "native-windows-runtime-pin.json"
PIN_INPUTS = (
    "tools/apply_dusk_patches.py",
    "tools/prepare_dusk_recomp.py",
    "tools/restore_verified_hotpaths.py",
    "tools/patch_windows_net.py",
)


def runtime_fingerprint(root: Path = ROOT) -> str:
    entries = [root / name for name in PIN_INPUTS]
    entries += sorted((root / "tools/patches").glob("*.patch"))
    if not entries or any(not p.is_file() for p in entries):
        raise FileNotFoundError("Missing native patch or source-generation file")
    h = hashlib.sha256()
    for path in entries:
        h.update(path.relative_to(root).as_posix().encode() + b"\0")
        # Windows Git may materialize checked-out text as CRLF while the
        # pinned Linux CI checkout uses LF. Normalize line endings ONLY;
        # meaningful source edits must still alter the provenance digest.
        normalized = path.read_bytes().replace(b"\r\n", b"\n")
        h.update(hashlib.sha256(normalized).digest())
    return h.hexdigest()


def verified_pin(path: Path = PIN_FILE, root: Path = ROOT) -> dict:
    pin = json.loads(path.read_text(encoding="utf-8"))
    for key in ("run_id", "artifact_id", "artifact_name", "artifact_digest", "exe_filename", "source_fingerprint"):
        if not pin.get(key):
            raise ValueError(f"Windows runtime pin missing {key}")
    if type(pin["run_id"]) is not int or pin["run_id"] <= 0:
        raise ValueError("Invalid pinned full-build run ID")
    if not pin["artifact_name"].startswith("Digimon-World-Dusk-Recompiled-"):
        raise ValueError("Unexpected pinned artifact name")
    if type(pin["artifact_id"]) is not int or pin["artifact_id"] <= 0:
        raise ValueError("Invalid pinned artifact ID")
    if not pin["artifact_digest"].startswith("sha256:") or len(pin["artifact_digest"]) != 71 or not all(c in "0123456789abcdef" for c in pin["artifact_digest"][7:]):
        raise ValueError("Expected sha256 artifact digest")
    if pin["source_fingerprint"] != runtime_fingerprint(root):
        raise ValueError("Native sources changed: refuse fast repack; full NDSRecomp build required")
    return pin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pin", type=Path, default=PIN_FILE)
    args = parser.parse_args()
    print(json.dumps(verified_pin(args.pin), sort_keys=True))


if __name__ == "__main__":
    main()
