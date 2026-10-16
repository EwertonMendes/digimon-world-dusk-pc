"""Guard the complete authentic Nintendo DS Digivice icon on every NCER frame.

The four original buttons carry colored artwork above and, on some frames,
slightly over the first caption scanline. Their distinctive cyan/blue indices
(3-8, 10-12) are not used by the lime letter glyphs (13-15). Source icon
pixels plus their bordering indigo/transparent pixels must be immutable.
"""
from __future__ import annotations

CORE_INDICES=frozenset((3,4,5,6,7,8,10,11,12))
MENU_ICON_IDS=frozenset((479,480,481,482))
ICON_SCAN_X={479:29,480:27,481:27,482:31}
ICON_SCAN_Y=(7,37)


def original_icon_pixels(view, sprite_id:int)->set[tuple[int,int]]:
    if sprite_id not in MENU_ICON_IDS:
        raise ValueError("not an audited Digivice button")
    width,height=view.size
    left=ICON_SCAN_X[sprite_id]
    if width!=64 or height!=64:
        raise ValueError("unexpected original Digivice cell size")
    seeds={
        (x,y)
        for y in range(ICON_SCAN_Y[0],min(ICON_SCAN_Y[1],height))
        for x in range(left,width)
        if view.mapping[(x,y)][2] in CORE_INDICES
    }
    if not seeds:
        raise ValueError(f"no original icon source palette pixels: sprite {sprite_id}")
    # The seed color core includes the native cyan outline and the
    # animation-specific highlight; an exact 1-pixel corona guards the
    # dark outline and its transparent antialias-free neighboring tiles.
    mask={(xx,yy) for x,y in seeds
          for xx in range(max(0,x-1),min(width,x+2))
          for yy in range(max(0,y-1),min(height,y+2))}
    return mask


def assert_icon_pixels_intact(before,after,sprite_id:int,cell:int)->None:
    if before.size!=after.size:
        raise ValueError("sprite dimensions changed")
    mask=original_icon_pixels(before,sprite_id)
    differences=[(x,y) for x,y in mask
                 if before.mapping[(x,y)][2]!=after.mapping[(x,y)][2]]
    if differences:
        raise ValueError(f"sprite {sprite_id} cell {cell} cut original icon pixels: "
                         f"{len(differences)}, first {differences[:5]}")
