"""Reconstruct the Digivice's obscured lower shell in the Tamer button.

The original game's two-line Tamer/Info letters are baked *over* the icon.
Erasing English therefore removes the icon's lower cyan bezel as well. Unlike
a preservation mask, this original-palette reconstruction restores the
missing bezel in all four original animated NCER states. No icon resizing,
partial-state substitutions or SDL overlays.
"""
from __future__ import annotations

# Original 64x64 cell coordinates, not PC-screen coordinates. Rows follow
# the authentic icon's downward-right slope. The last 2 pixels join the
# surviving, animated NCLR-colored right-hand hardware tip.
_LOWER_SHELL={
    24:(36,47),
    25:(36,49),
    26:(37,51),
    27:(38,53),
    28:(39,55),
    29:(41,55),
    30:(43,53),
    31:(46,51),
}


def restored_digivice_pixels(source_view,cell:int,protected:set[tuple[int,int]])->dict[tuple[int,int],int]:
    """Return missing source-palette indices, never change authentic pixels."""
    if source_view.size!=(64,64) or cell not in (0,1,2,3):
        raise ValueError("unexpected original Digivice sprite animation")
    bright=(6,10,13,13)[cell]
    shine=(7,15,15,15)[cell]
    dest={}
    for y,(left,right) in _LOWER_SHELL.items():
        for x in range(left,right+1):
            if (x,y) in protected:
                continue
            # The outer indigo outline and cyan bezel reproduce the colors
            # seen in the unobstructed top/side of the same NCER frame.
            if y==31 or x==left or x==right:
                index=2
            elif y==30 or x==left+1:
                index=3
            elif y==29 or x==left+2:
                index=5
            elif y in (25,26) and x<right-2:
                index=shine if (x+y)%5==0 else bright
            elif y==28:
                index=9
            else:
                index=bright if (x+y)%4==0 else 9
            dest[(x,y)]=index
    if len(dest)<15:
        raise ValueError("original text/icon collision left no reconstructable lower shell")
    if any((x,y) in protected or not 35<=x<=56 or not 24<=y<=31 or v not in
           (2,3,5,6,7,9,10,13,15) for (x,y),v in dest.items()):
        raise ValueError("icon restoration escaped its original graphics footprint")
    return dest
