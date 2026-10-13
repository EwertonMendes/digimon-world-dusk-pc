#!/usr/bin/env python3
"""Bootstrap experimental NDSRecomp *recompiler only*, without any ROM or proprietary BIOS.

Not a Dusk recompilation: this prepares and tests the upstream toolchain, pending
explicit game-owned bank configs, BIOS/firmware compatibility, and runtime integration.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

UPSTREAM = "https://github.com/RetroPortingToolKit/ndsrecomp.git"
PINNED = "3a57236bb23d25dcb4caad7d58d733311062ff5e"


def command(*args: str, cwd: Path | None = None) -> None:
    print("$", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Use preexisting local NDSRecomp checkout")
    parser.add_argument("--build-dir", type=Path, default=Path("build/ndsrecomp-recompiler"))
    parser.add_argument("--no-clone", action="store_true", help="Do not fetch upstream; require --source")
    args = parser.parse_args()
    missing = [name for name in ("cmake", "git") if not shutil.which(name)]
    if missing:
        parser.error("Missing executable(s): " + ", ".join(missing))
    if args.no_clone and args.source is None:
        parser.error("--no-clone requires --source")
    source = args.source or Path("external/ndsrecomp")
    if not source.exists():
        if args.no_clone:
            parser.error("NDSRecomp checkout missing")
        source.parent.mkdir(parents=True, exist_ok=True)
        command("git", "clone", UPSTREAM, str(source))
        command("git", "checkout", "--detach", PINNED, cwd=source)
        command("git", "submodule", "update", "--init", "--recursive", cwd=source)
    else:
        print("Using checkout:", source.resolve())
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if current != PINNED:
        parser.error(f"Expected pinned NDSRecomp {PINNED}; found {current}. Use a separate checkout at the pinned commit.")
    print("Pinned upstream revision:", current)
    recompiler = source / "recompiler"
    if not (recompiler / "CMakeLists.txt").is_file():
        parser.error("NDSRecomp checkout does not contain recompiler/CMakeLists.txt")
    command("cmake", "-S", str(recompiler.resolve()), "-B", str(args.build_dir.resolve()), "-DCMAKE_BUILD_TYPE=Release")
    command("cmake", "--build", str(args.build_dir.resolve()), "--parallel", "2")
    for binary in ("armv5te_decode_test", "interpreter_cycle_test"):
        exe = args.build_dir / (binary + (".exe" if sys.platform == "win32" else ""))
        if not exe.exists():
            print(f"ERROR: Expected upstream test missing: {exe}")
            return 1
        command(str(exe.resolve()))
    print("Recompiler tests passed. No game or firmware recompilation attempted.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("Bootstrap command failed:", exc, file=sys.stderr)
        raise SystemExit(exc.returncode)
