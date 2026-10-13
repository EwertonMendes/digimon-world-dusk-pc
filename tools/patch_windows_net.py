#!/usr/bin/env python3
"""Apply narrowly scoped Win32 portability fix to pinned external NDSRecomp checkout.
Run before configuring the runner; never mutate main repository copy.
"""
from pathlib import Path
import argparse

def replace_exact(path: Path, old: str, new: str, count: int) -> None:
    before = path.read_text(encoding="utf-8")
    actual = before.count(old)
    if actual != count:
        raise RuntimeError(f"{path}: expected {count} occurrences of {old!r}, found {actual}")
    path.write_text(before.replace(old, new), encoding="utf-8")
    print(f"Updated {path}: {count} Win32 platform guards")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("checkout",type=Path)
    args=parser.parse_args()
    folder=args.checkout / "runner/vendor/melonds/net"
    replace_exact(folder/"Net_Slirp.h", "__WIN32__", "_WIN32", 1)
    replace_exact(folder/"Net_Slirp.cpp", "__WIN32__", "_WIN32", 6)
    replace_exact(folder/"Net_Slirp.h", "static ssize_t SlirpCbSendPacket", "static slirp_ssize_t SlirpCbSendPacket", 1)
    replace_exact(folder/"Net_Slirp.cpp", "ssize_t Net_Slirp::SlirpCbSendPacket", "slirp_ssize_t Net_Slirp::SlirpCbSendPacket", 1)

if __name__=="__main__":
    main()
