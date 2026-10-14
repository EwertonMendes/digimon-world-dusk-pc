#!/usr/bin/env python3
"""Render a portable 16:9 startup splash using the approved local Dusk artwork.

SDL3 can decode BMP without SDL_image. Generation is deterministic, requires no
web access and runs at build time; the player receives only the packaged asset.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont

from branding import APP_VERSION, AUTHOR_CREDIT
from generate_icons import SOURCE, remove_corner_matte

WIDTH, HEIGHT = 1280, 720
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "splash" / "generated" / "dusk-splash.bmp"


def font_path(bold: bool = False) -> str:
    names = (
        ["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else
        ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf"]
    )
    for name in names:
        if Path(name).is_file():
            return name
    # Pillow includes a scalable fallback on supported platforms.
    return "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path(bold), size)


def generate(source: Path = SOURCE, output: Path = OUTPUT) -> Path:
    with Image.open(source) as raw:
        if raw.width != raw.height or raw.width < 256:
            raise ValueError("Splash artwork must be square and at least 256 pixels")
        icon = remove_corner_matte(raw).resize((466, 466), Image.Resampling.LANCZOS)

    # Dark indigo / violet gradient with a restrained neon horizon.
    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    pix = canvas.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            t = y / (HEIGHT - 1)
            right = x / (WIDTH - 1)
            pix[x, y] = (
                int(7 + 12 * (1 - t) + 13 * right),
                int(11 + 12 * (1 - t) + 8 * right),
                int(30 + 45 * (1 - t) + 51 * right),
            )
    draw = ImageDraw.Draw(canvas, "RGBA")
    # Decorative circuit-like rays and stars are static and do not mask the credit.
    draw.polygon([(730, 0), (1280, 0), (1280, 720), (1100, 720)],
                 fill=(41, 33, 136, 60))
    draw.polygon([(960, 0), (1280, 0), (1280, 400)], fill=(16, 120, 219, 35))
    rng = random.Random(12427)
    for _ in range(160):
        x, y = rng.randrange(30, WIDTH - 30), rng.randrange(30, HEIGHT - 35)
        if x < 680 and 135 < y < 665:
            continue
        radius = rng.choice((1, 1, 1, 2))
        draw.ellipse((x-radius, y-radius, x+radius, y+radius),
                     fill=(143, 178, 255, rng.randrange(45, 135)))
    for offset in (0, 11, 22):
        draw.line([(744+offset, 70), (1192+offset, 70),
                   (1192+offset, 650)], fill=(87, 67, 187, 60), width=2)
    draw.ellipse((745, 125, 1230, 615), fill=(22, 92, 230, 35),
                 outline=(144, 69, 252, 75), width=3)
    draw.ellipse((776, 155, 1198, 583), outline=(55, 212, 246, 85), width=3)

    canvas = canvas.convert("RGBA")
    # Reuse the approved icon as a standalone illustration, no screenshots/ROM content.
    canvas.alpha_composite(icon, (758, 125))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((78, 93, 276, 130), radius=9,
                           fill=(31, 110, 161, 110), outline=(70, 209, 247, 210), width=2)
    draw.text((95, 99), "NATIVE PC EDITION", font=get_font(18, True),
              fill=(199, 249, 255, 255))
    draw.text((79, 178), "DIGIMON WORLD", font=get_font(50, True),
              fill=(241, 244, 255, 255), stroke_width=1, stroke_fill=(26, 46, 104, 255))
    draw.text((73, 230), "DUSK", font=get_font(132, True),
              fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(32, 87, 207, 255))
    draw.rounded_rectangle((82, 393, 663, 467), radius=10,
                           fill=(35, 18, 107, 230), outline=(61, 229, 245, 230), width=3)
    draw.text((99, 401), "RECOMPILED", font=get_font(51, True),
              fill=(102, 234, 255, 255))
    draw.line((84, 510, 641, 510), fill=(175, 97, 250, 220), width=3)
    draw.text((82, 536), "RECOMPILED BY", font=get_font(23, True),
              fill=(194, 195, 239, 255))
    draw.text((80, 569), "TBLACK", font=get_font(54, True),
              fill=(253, 253, 255, 255))
    draw.text((81, 662), f"{APP_VERSION}   ·   A NATIVE RECOMPILATION PROJECT",
              font=get_font(17), fill=(155, 163, 206, 255))
    draw.line((0, HEIGHT-6, WIDTH, HEIGHT-6), fill=(63, 214, 245, 170), width=3)
    draw.line((0, HEIGHT-3, WIDTH, HEIGHT-3), fill=(211, 55, 204, 190), width=3)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="BMP")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(generate(args.source, args.out))
