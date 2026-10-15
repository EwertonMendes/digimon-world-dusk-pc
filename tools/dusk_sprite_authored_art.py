"""Strict native-Nitro sprite artwork importer for manually authored PNG cells.

Unlike the legacy Pillow text painter, this module NEVER renders fonts. The
artwork is pixel-authored at original DS resolution (for example in Tinke or
NitroPaint), must use exact NCLR palette colors, and may change only declared
caption pixels in a cell's original NCGR tile bank. No ROM is exported here.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image

from dusk_sprite_inplace_editor import extract_cell, _write_pixel
from probe_dusk_sprite_cells import get_cell_groups
from nitro_bg_preview import graphics, palette, chunk


def _rectangles(raw: list, size: tuple[int, int]) -> list[tuple[int,int,int,int]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("artwork requires at least one explicit text-only rectangle")
    width, height = size
    result = []
    for rect in raw:
        if not isinstance(rect,list) or len(rect)!=4 or any(type(v) is not int for v in rect):
            raise ValueError("malformed artwork caption rectangle")
        x,y,w,h = rect
        if not (0 <= x < width and 0 <= y < height and
                w > 0 and h > 0 and x+w <= width and y+h <= height):
            raise ValueError("artwork edit rectangle exceeds source OAM cell")
        result.append((x,y,w,h))
    return result


def import_authored_art(
    ncgr: bytes, nclr: bytes, ncer: bytes, edits: list[dict], root: Path,
) -> bytes:
    """Replace explicitly masked source pixels from lossless, indexed-color art."""
    depth, raw = graphics(ncgr)
    if depth != 3:
        raise ValueError("only verified 4bpp Nintendo DS sprites are supported")
    colors = palette(nclr)
    at, _ = chunk(ncgr, b"RGCN", b"RAHC")
    raw_begin = at + 32
    out = bytearray(ncgr)
    pending: dict[tuple[int,bool], int] = {}
    seen = set()
    for edit in edits:
        cell = edit.get("cell")
        if type(cell) is not int or cell in seen:
            raise ValueError("invalid or repeated artwork animation cell")
        seen.add(cell)
        source_view = extract_cell(ncgr, nclr, ncer, cell)
        regions = _rectangles(edit.get("regions"), source_view.size)
        art_rel = edit.get("png")
        if not isinstance(art_rel, str) or not art_rel.endswith(".png"):
            raise ValueError("artwork must reference a PNG image")
        image_path = (root / art_rel).resolve()
        if not image_path.is_relative_to(root.resolve()):
            raise ValueError("art path escapes translation asset directory")
        with Image.open(image_path) as source_art:
            if source_art.format != "PNG":
                raise ValueError("artwork must be an actual PNG file")
            if source_art.mode not in ("RGB", "RGBA"):
                raise ValueError("authored DS images must be RGB or RGBA PNG")
            if source_art.size != source_view.size:
                raise ValueError("authored pixel dimensions differ from original OAM cell")
            if source_art.mode == "RGBA" and source_art.getchannel("A").getextrema() != (255,255):
                raise ValueError("alpha/translucency not allowed; use source palette")
            artwork = source_art.convert("RGB")
        old_pixels = source_view.image.load()
        new_pixels = artwork.load()
        changed = 0
        for y in range(source_view.size[1]):
            for x in range(source_view.size[0]):
                new_color = new_pixels[x,y]
                if old_pixels[x,y] == new_color:
                    continue
                if not any(rx<=x<rx+rw and ry<=y<ry+rh
                           for rx,ry,rw,rh in regions):
                    raise ValueError(f"authored artwork modifies button icon/frame at {x},{y}")
                offset, high, old_index, bank = source_view.mapping[x,y]
                # extract_cell() displays NCLR index 0 using this private
                # diagnostic matte. Encode it back as native transparent
                # palette index zero, never as an invented RGB color.
                if new_color==(22,26,40):
                    lookup=[0]
                else:
                    lookup = [i for i in range(1,16)
                              if bank*16+i<len(colors) and colors[bank*16+i][:3]==new_color]
                if not lookup:
                    raise ValueError(f"PNG pixel at {x},{y} not present in original NCLR bank {bank}")
                idx = old_index if old_index in lookup else lookup[0]
                key = (offset,high)
                if key in pending and pending[key]!=idx:
                    raise ValueError("OAM animation frames share conflicting source pixels")
                pending[key] = idx
                changed += 1
        if changed == 0:
            raise ValueError("authored sprite identical to original; no localization supplied")
    for (offset, high), value in pending.items():
        _write_pixel(out, raw_begin+offset, high, value)
    if len(out)!=len(ncgr):
        raise ValueError("art importer modified original NCGR length")
    allowed={raw_begin+offset for offset,_ in pending}
    if any(a!=b and index not in allowed
           for index,(a,b) in enumerate(zip(out,ncgr))):
        raise ValueError("art importer changed NCGR headers or non-caption pixels")
    # Inspect EVERY original NCER animation, even unedited cells. Shared
    # 1D tile names can otherwise corrupt a frame omitted from the manifest.
    groups, mode = get_cell_groups(ncer)
    if mode not in (0,1,2,3):
        raise ValueError("unsupported original NCER mapping mode")
    authored = {edit["cell"]:edit for edit in edits}
    for cell in range(len(groups)):
        before = extract_cell(ncgr,nclr,ncer,cell)
        after = extract_cell(bytes(out),nclr,ncer,cell)
        regions = _rectangles(authored[cell]["regions"],before.size) if cell in authored else []
        for y in range(before.size[1]):
            for x in range(before.size[0]):
                if before.image.getpixel((x,y)) != after.image.getpixel((x,y)):
                    if not any(rx<=x<rx+rw and ry<=y<ry+rh
                               for rx,ry,rw,rh in regions):
                        raise ValueError(f"unapproved artwork change in OAM animation {cell}")
    return bytes(out)
