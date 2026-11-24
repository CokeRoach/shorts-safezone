"""Safe areas of 9:16 short-video players, measured from each platform's own material.

Every zone is a stack of clear bands, top to bottom: ``(top, bottom, left, right)`` in the
units of ``width`` x ``height``. A box is safe when it fits inside the bands it overlaps.
A stepped zone (TikTok keeps its right-hand buttons clear only in the lower part) is two
bands.

All three platforms publish these for ads. Organic videos get the same player UI, so the
zones are a practical guide for them too, but no platform guarantees them for organic posts.
"""

from __future__ import annotations

from dataclasses import dataclass

Band = tuple[float, float, float, float]


@dataclass(frozen=True)
class Zone:
    key: str
    label: str
    width: float
    height: float
    bands: tuple[Band, ...]
    source: str
    method: str
    checked: str


ZONES: dict[str, Zone] = {
    "youtube": Zone(
        key="youtube",
        label="YouTube Shorts",
        width=1080,
        height=1920,
        bands=((288, 1248, 48, 888),),
        source="https://services.google.com/fh/files/misc/youtubesafezoneoverlay_vertical_final.png",
        method=(
            "Transparent area of Google's official vertical overlay, measured pixel by pixel "
            "(linked from https://services.google.com/fh/files/misc/universalsafezones-youtube.pdf)."
        ),
        checked="2026-11-24",
    ),
    "tiktok": Zone(
        key="tiktok",
        label="TikTok",
        width=720,
        height=1280,
        bands=((160, 560, 80, 640), (560, 840, 80, 520)),
        source="https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads",
        method=(
            "Clear area of TikTok's official 'In-Feed-Standard Version LTR' template, measured "
            "pixel by pixel. TikTok says the zone shrinks with longer captions and add-ons."
        ),
        checked="2026-11-24",
    ),
    "reels": Zone(
        key="reels",
        label="Instagram Reels",
        width=100,
        height=100,
        bands=((14, 65, 6, 94),),
        source="https://www.facebook.com/business/ads-guide/update/video/instagram-reels",
        method="Meta's Reels ad guide: keep roughly the top 14%, bottom 35% and sides 6% clear.",
        checked="2026-11-24",
    ),
}

PLATFORMS = tuple(ZONES)


@dataclass(frozen=True)
class Box:
    left: float
    top: float
    right: float
    bottom: float

    @classmethod
    def from_xywh(cls, x: float, y: float, w: float, h: float) -> Box:
        if w <= 0 or h <= 0:
            raise ValueError("box width and height must be positive")
        return cls(x, y, x + w, y + h)


def is_vertical_9_16(width: int, height: int) -> bool:
    return height > 0 and abs(width / height - 9 / 16) < 0.01


def scaled_bands(zone: Zone, width: int, height: int) -> list[Band]:
    """The zone's bands in pixels of a ``width`` x ``height`` canvas."""
    sx, sy = width / zone.width, height / zone.height
    return [(t * sy, b * sy, l * sx, r * sx) for t, b, l, r in zone.bands]


def edges_crossed(box: Box, zone: Zone, width: int, height: int) -> list[str]:
    """Edges of the safe area that ``box`` crosses, as ``left``/``top``/``right``/``bottom``."""
    bands = scaled_bands(zone, width, height)
    crossed = set()
    if box.top < bands[0][0]:
        crossed.add("top")
    if box.bottom > bands[-1][1]:
        crossed.add("bottom")
    for top, bottom, left, right in bands:
        if box.bottom <= top or box.top >= bottom:
            continue
        if box.left < left:
            crossed.add("left")
        if box.right > right:
            crossed.add("right")
    return [edge for edge in ("left", "top", "right", "bottom") if edge in crossed]


def check_box(
    box: Box, width: int = 1080, height: int = 1920, platforms: tuple[str, ...] = PLATFORMS
) -> dict[str, list[str]]:
    """Crossed edges per platform. An empty list means the box is safe there."""
    if not is_vertical_9_16(width, height):
        raise ValueError(f"{width}x{height} is not 9:16; these zones are for vertical video")
    return {key: edges_crossed(box, ZONES[key], width, height) for key in platforms}
