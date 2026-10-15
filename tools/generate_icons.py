#!/usr/bin/env python3
"""Generate cross-platform raster icons from approved Dusk artwork (Pillow >= 10)."""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw
from branding import APP_NAME, APP_VERSION, APP_SLUG

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/icons/dusk-icon-master.webp"
OUT = ROOT / "assets/icons/generated"


def remove_corner_matte(image: Image.Image) -> Image.Image:
    """Recover rounded-corner transparency from the original black-matted artwork.

    Never key out black pixels throughout the image: dark blue/black details
    inside the Dusk illustration must remain opaque.
    """
    rgba = image.convert("RGBA")
    if rgba.getextrema()[3][0] < 255:
        return rgba  # Preserve intentional alpha from future source artwork.
    width, height = rgba.size
    pixels = rgba.load()
    alpha = Image.new("L", (width, height), 255)
    mask = alpha.load()
    for y in range(height):
        luminance = [max(pixels[x, y][:3]) for x in range(width)]
        first = next((x for x, v in enumerate(luminance) if v >= 28), width)
        last = next((x for x in range(width - 1, -1, -1)
                     if luminance[x] >= 28), -1)
        if first > width // 3 or last < 2 * width // 3:
            raise ValueError(f"Unexpected rounded corner artwork in row {y}")
        for left in (True, False):
            boundary = first if left else last
            if (left and boundary <= 0) or (not left and boundary >= width - 1):
                continue
            inside = min(width - 1, boundary + 3) if left else max(0, boundary - 3)
            reference = max(25, luminance[inside])
            positions = (range(0, min(width, boundary + 3)) if left
                         else range(max(0, boundary - 2), width))
            for x in positions:
                v = luminance[x]
                if ((left and x < boundary - 2) or
                        (not left and x > boundary + 2) or v <= 8):
                    coverage = 0
                else:
                    coverage = round(min(1.0, v / reference) * 255)
                mask[x, y] = min(mask[x, y], coverage)
                if 0 < coverage < 255:
                    # Remove the embedded black backing from antialiased edges,
                    # so a light Windows desktop does not show a dark halo.
                    rgb = pixels[x, y][:3]
                    scale = 255 / coverage
                    pixels[x, y] = tuple(min(255, round(c * scale)) for c in rgb) + (255,)
    rgba.putalpha(alpha)
    return rgba

def save_png(image: Image.Image, path: Path, side: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize((side, side), Image.Resampling.LANCZOS).save(path, optimize=True)


def generate(source: Path = SOURCE, out: Path = OUT) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Approved icon missing: {source}")
    with Image.open(source) as loaded:
        if loaded.width != loaded.height or loaded.width < 256:
            raise ValueError("Master icon must be square and at least 256 pixels")
        art = remove_corner_matte(loaded)
    out.mkdir(parents=True, exist_ok=True)
    art.save(out / "dusk-icon-transparent.png", optimize=True)

    windows = out / "windows"
    windows.mkdir(parents=True, exist_ok=True)
    art.resize((256, 256), Image.Resampling.LANCZOS).save(
        windows / "dusk.ico", format="ICO",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    # Headerless RGBA is mapped into an SDL3 surface without SDL_image;
    # unlike BMP/RGB, the alpha channel survives all the way to the taskbar.
    (windows / "window-icon.rgba").write_bytes(
        art.resize((128, 128), Image.Resampling.LANCZOS).tobytes())
    major, minor = (int(part) for part in APP_VERSION.removeprefix("v").split("."))
    rc = (
        '1 ICON "assets/icons/generated/windows/dusk.ico"\n'
        '1 VERSIONINFO\n'
        f' FILEVERSION {major},{minor},0,0\n'
        f' PRODUCTVERSION {major},{minor},0,0\n'
        ' FILEFLAGSMASK 0x3f\n FILEFLAGS 0x0\n FILEOS 0x40004\n FILETYPE 0x1\n'
        ' BEGIN\n  BLOCK "StringFileInfo"\n   BEGIN\n    BLOCK "040904B0"\n'
        '     BEGIN\n'
        f'      VALUE "FileDescription", "{APP_NAME}"\n'
        f'      VALUE "ProductName", "{APP_NAME}"\n'
        f'      VALUE "FileVersion", "{major}.{minor}.0.0"\n'
        f'      VALUE "ProductVersion", "{APP_VERSION}"\n'
        '     END\n   END\n  BLOCK "VarFileInfo"\n   BEGIN\n'
        '    VALUE "Translation", 0x409, 1200\n   END\n END\n'
    )
    (windows / "dusk.rc").write_text(rc, encoding="utf-8")

    linux = out / "linux"
    for side in (16, 24, 32, 48, 64, 128, 256, 512):
        save_png(art, linux / f"hicolor/{side}x{side}/apps/{APP_SLUG.lower()}.png", side)
    (linux / f"{APP_SLUG.lower()}.desktop").write_text(
        f"[Desktop Entry]\nType=Application\nName={APP_NAME}\n"
        f"Exec={APP_SLUG.lower()}\nIcon={APP_SLUG.lower()}\n"
        "Categories=Game;\nTerminal=false\n",
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

    values = android / "values"
    values.mkdir(parents=True, exist_ok=True)
    (values / "strings.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<resources><string name="app_name">{APP_NAME}</string></resources>\n',
        encoding="utf-8")

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
