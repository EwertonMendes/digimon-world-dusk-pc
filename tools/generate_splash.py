#!/usr/bin/env python3
"""Generate the version-independent, approved Lunamon splash for SDL3.

One checked-in WebP illustration is the single visual source. The host runtime
owns the version overlay and transition; artwork never changes per release.
SDL3 loads an uncompressed 24-bit BMP without SDL_image at boot.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/splash/dusk-recompiled-art.webp"
SOURCE_SHA256 = "8efca812bc7842fe8cfdb0d722b1b9247c1f23ad04806e173ddfe4a86f6d2842"
WIDTH, HEIGHT = 3840, 2160
OUTPUT = ROOT / "assets/splash/generated/dusk-splash.bmp"


def generate(source: Path = SOURCE, output: Path = OUTPUT) -> Path:
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unapproved or modified splash artwork")
    with Image.open(source) as illustration:
        if illustration.width < 1600 or illustration.height < 900:
            raise ValueError("Source art must be at least 1600 by 900 pixels")
        if abs(illustration.width / illustration.height - WIDTH / HEIGHT) > 0.01:
            raise ValueError("Splash artwork must be close to 16:9")
        # Source image is 1672x941: LANCZOS produces a clean 4K output.
        # This is high-quality interpolation, not fabricated native 4K detail.
        frame = illustration.convert("RGB").resize(
            (WIDTH, HEIGHT), Image.Resampling.LANCZOS
        )
        frame = frame.filter(ImageFilter.UnsharpMask(
            radius=0.65, percent=100, threshold=3
        ))
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.save(output, format="BMP")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(generate(args.source, args.out))
