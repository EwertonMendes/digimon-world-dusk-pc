#!/usr/bin/env python3
"""Apply the pinned NDSRecomp Dusk SDL3 integration in one deterministic order.

This consolidates the integration *workflow*, not upstream game code.
Desktop patches are still a temporary compatibility layer; replacing them
with modular Dusk components requires private native-runner regression tests.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PINNED_RECOMP_COMMIT = "3a57236bb23d25dcb4caad7d58d733311062ff5e"

NATIVE_UI = ("ndsrecomp-dusk-native-ui.patch",)
DESKTOP = NATIVE_UI + (
    "ndsrecomp-dusk-screen-swap.patch",
    "ndsrecomp-dusk-native-30hz.patch",
    "ndsrecomp-dusk-native-30hz-settings-v3.patch",
    "ndsrecomp-dusk-disable-savestates.patch",
    "ndsrecomp-dusk-immersive-ui.patch",
    "ndsrecomp-dusk-immersive-ui-hotfix.patch",
    "ndsrecomp-dusk-ux-polish-v2.patch",
    "ndsrecomp-dusk-transition-audio-headroom.patch",
    "ndsrecomp-dusk-pc-menu-input-capture.patch",
    "ndsrecomp-dusk-battle-frame-spikes.patch",
    "ndsrecomp-dusk-precise-pacing.patch",
    "ndsrecomp-dusk-window-icon.patch",
    "ndsrecomp-dusk-recompiled-splash.patch",
    "ndsrecomp-dusk-intro-crossfade-v026.patch",
)


def integrate(upstream: Path, component: str) -> list[str]:
    upstream = upstream.resolve(strict=True)
    if not (upstream / ".git").exists():
        raise ValueError(f"Not a git checkout: {upstream}")
    commit = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if commit != PINNED_RECOMP_COMMIT:
        raise ValueError(f"Unexpected NDSRecomp upstream commit: {commit}")
    patch_dir = Path(__file__).resolve().parent / "patches"
    patches = NATIVE_UI if component == "native-ui" else DESKTOP
    if len(patches) != len(set(patches)):
        raise ValueError("Duplicated integration patches")
    for name in patches:
        path = patch_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing integration patch: {path}")
        subprocess.run(["git", "-C", str(upstream), "apply", "--check",
                        str(path)], check=True)
        subprocess.run(["git", "-C", str(upstream), "apply", str(path)], check=True)
    return list(patches)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--component", choices=("native-ui", "desktop"),
                        default="desktop")
    args = parser.parse_args()
    patches = integrate(args.upstream, args.component)
    print(f"NDSRecomp {PINNED_RECOMP_COMMIT}: applied {len(patches)} patches:")
    for name in patches:
        print(" -", name)


if __name__ == "__main__":
    main()
