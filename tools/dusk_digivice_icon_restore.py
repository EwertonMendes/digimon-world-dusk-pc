"""Conservatively restore the authentic Digivice's occluded lower edge.

The English source has its two-line Tamer/Info caption baked across the icon's
lower-left underside. Do not treat that text as part of the game icon, or paint
a large artificial white/cyan highlight across its bezel. Only the original
four-color indigo/teal casing is extended into the gap. The original display,
moving highlights, dark outline and right endcap remain pixel-exact.
"""
from __future__ import annotations

# Manually reviewed Nintendo-DS 64x64 sprite coordinates. These are the
# *obscured underside*, not the complete icon silhouette. The true upper
# icon and right-hand casing are retained verbatim in all original frames.
_LOWER_UNDERSIDE = {
    26: (37, 46),
    27: (38, 49),
    28: (40, 51),
    29: (43, 53),
    30: (47, 54),
}


def restored_digivice_pixels(
    source_view, cell: int, protected: set[tuple[int, int]]
) -> dict[tuple[int, int], int]:
    """Supply a small casing-edge repair without recoloring the animated icon.

    Only source NCLR indexes 2/3/4/9 are allowed in the extension. White,
    yellow and green belong to the *original moving display*; synthesizing
    those colors underneath the hardware produces detached blinking specks.
    """
    if source_view.size != (64, 64) or cell not in (0, 1, 2, 3):
        raise ValueError("unexpected original Digivice sprite animation")

    repaired = {}
    for y, (left, right) in _LOWER_UNDERSIDE.items():
        for x in range(left, right + 1):
            if (x, y) in protected:
                continue
            if y == 30 or x == right:
                index = 2  # original indigo external outline
            elif x == left:
                index = 3  # native blue-cyan leading edge
            elif y == 29:
                index = 4  # subdued cyan bottom edge
            else:
                index = 9  # deep teal body, matches original hardware casing
            repaired[(x, y)] = index

    if len(repaired) < 8:
        raise ValueError("source icon mask left no safe underside pixels to rebuild")
    if any(
        (x, y) in protected
        or not (37 <= x <= 54 and 26 <= y <= 30)
        or value not in (2, 3, 4, 9)
        for (x, y), value in repaired.items()
    ):
        raise ValueError("Digivice reconstruction escaped original dark casing")

    return repaired
