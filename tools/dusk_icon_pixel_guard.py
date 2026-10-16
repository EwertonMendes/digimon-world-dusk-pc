"""Protect the *whole moving icon* across all four original NCER states.

Each DS button reuses native NCGR character tiles but the colored highlight
cycles through palette indexes including white (15) and lime (13/14). Looking
for blue indexes in one frame is insufficient: translated text may erase a
green/white frame's outline and cause the visible icon to blink or truncate.
This module derives a union mask from ORIGINAL source animation states only.
"""
from __future__ import annotations

CORE_INDICES=frozenset((3,4,5,6,7,8,10,11,12))
MENU_ICON_IDS=frozenset((479,480,481,482))
ICON_SCAN_X={479:29,480:27,481:27,482:31}
ICON_SCAN_Y=(7,39)


def original_icon_pixels(views, sprite_id:int)->set[tuple[int,int]]:
    if sprite_id not in MENU_ICON_IDS:
        raise ValueError("not an audited Digivice button")
    if not isinstance(views,(tuple,list)):
        views=(views,)
    if not views or any(v.size!=(64,64) for v in views):
        raise ValueError("unexpected Digivice cell size")
    left=ICON_SCAN_X[sprite_id]
    # Include every coordinate where the authentic animation changes palette
    # index, not just blue pixels. This keeps selected white/green highlights.
    # Detect differences only in the icon's upper-right footprint; original
    # letters and cyan plate borders are static across all four states.
    seeds=set()
    for y in range(*ICON_SCAN_Y):
        for x in range(left,64):
            indices=[v.mapping[(x,y)][2] for v in views]
            if len(set(indices))>1 or any(i in CORE_INDICES for i in indices):
                seeds.add((x,y))
    if len(seeds)<12:
        raise ValueError(f"not enough original animated icon pixels: {sprite_id}")
    # Two-pixel safety envelope covers colored highlights, dark contour and
    # transparency around moving sprites. It must never be regenerated as
    # text background. This mask does NOT infer from translated artwork.
    mask={(xx,yy) for x,y in seeds
          for xx in range(max(left,x-2),min(64,x+3))
          for yy in range(max(ICON_SCAN_Y[0],y-2),min(ICON_SCAN_Y[1],y+3))}
    return mask


def assert_icon_pixels_intact(before,after,sprite_id:int,cell:int,mask=None)->None:
    if before.size!=after.size:
        raise ValueError("sprite dimensions changed")
    if mask is None:
        mask=original_icon_pixels((before,),sprite_id)
    differences=[(x,y) for x,y in mask
                 if before.mapping[(x,y)][2]!=after.mapping[(x,y)][2]]
    if differences:
        raise ValueError(f"sprite {sprite_id} cell {cell} clipped original "
                         f"animated icon pixels: {len(differences)}, first {differences[:5]}")
