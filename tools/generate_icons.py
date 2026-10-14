#!/usr/bin/env python3
"""Generate cross-platform raster icons from approved Dusk artwork (Pillow >= 10)."""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/icons/dusk-icon-master.webp"
OUT = ROOT / "assets/icons/generated"


def save_png(image: Image.Image, path: Path, side: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize((side, side), Image.Resampling.LANCZOS).save(path, optimize=True)


def generate(source: Path = SOURCE, out: Path = OUT) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Approved icon missing: {source}")
    with Image.open(source) as loaded:
        if loaded.width != loaded.height or loaded.width < 256:
            raise ValueError("Master icon must be square and at least 256 pixels")
        art = loaded.convert("RGBA")
    out.mkdir(parents=True, exist_ok=True)

    windows = out / "windows"
    windows.mkdir(parents=True, exist_ok=True)
    art.resize((256, 256), Image.Resampling.LANCZOS).save(
        windows / "dusk.ico", format="ICO",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    # BMP is supported natively by SDL3; no SDL_image library is necessary.
    art.resize((128, 128), Image.Resampling.LANCZOS).convert("RGB").save(
        windows / "window-icon.bmp", format="BMP")
    (windows / "dusk.rc").write_text(
        '1 ICON "assets/icons/generated/windows/dusk.ico"\n', encoding="ascii")

    linux = out / "linux"
    for side in (16, 24, 32, 48, 64, 128, 256, 512):
        save_png(art, linux / f"hicolor/{side}x{side}/apps/dusk-pc.png", side)
    (linux / "dusk-pc.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Digimon World Dusk PC\n"
        "Exec=dusk-pc\nIcon=dusk-pc\nCategories=Game;\nTerminal=false\n",
        encoding="utf-8")

    mac = out / "macos"
    mac.mkdir(parents=True, exist_ok=True)
    art.resize((1024, 1024), Image.Resampling.LANCZOS).save(
        mac / "dusk.icns", format="ICNS")

    android = out / "android"
    for density, side in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
                          ("xxhdpi", 144), ("xxxhdpi", 192)):
        for filename in ("ic_launcher.png", "ic_launcher_round.png"):
            save_png(art, android / f"mipmap-{density}/{filename}", side)

    # 108dp canvas with central 66dp Android adaptive-icon safe area.
    foreground = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    inner = art.resize((248, 248), Image.Resampling.LANCZOS)
    foreground.alpha_composite(inner, ((432 - 248) // 2, (432 - 248) // 2))
    drawable = android / "drawable-nodpi"
    drawable.mkdir(parents=True, exist_ok=True)
    foreground.save(drawable / "ic_launcher_foreground.png", optimize=True)

    themed = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    brush = ImageDraw.Draw(themed)
    brush.ellipse((122, 122, 310, 310), fill="white")
    brush.ellipse((180, 82, 340, 260), fill=(0, 0, 0, 0))
    themed.save(drawable / "ic_launcher_monochrome.png", optimize=True)

    background = android / "drawable"
    background.mkdir(parents=True, exist_ok=True)
    (background / "ic_launcher_background.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<vector xmlns:android="http://schemas.android.com/apk/res/android" '
        'android:width="108dp" android:height="108dp" '
        'android:viewportWidth="108" android:viewportHeight="108">\n'
        '  <path android:fillColor="#061A57" '
        'android:pathData="M0,0h108v108h-108z" />\n'
        '</vector>\n', encoding="utf-8")
    mipmap = android / "mipmap-anydpi-v26"
    mipmap.mkdir(parents=True, exist_ok=True)
    adaptive = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '  <background android:drawable="@drawable/ic_launcher_background" />\n'
        '  <foreground android:drawable="@drawable/ic_launcher_foreground" />\n'
        '  <monochrome android:drawable="@drawable/ic_launcher_monochrome" />\n'
        '</adaptive-icon>\n')
    for filename in ("ic_launcher.xml", "ic_launcher_round.xml"):
        (mipmap / filename).write_text(adaptive, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    generate(args.source, args.out)


if __name__ == "__main__":
    main()
