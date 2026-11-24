"""Check what YouTube Shorts, TikTok and Instagram Reels cover on a 9:16 video."""

from .overlay import load_frame, panel, sheet, unsafe_mask
from .zones import PLATFORMS, ZONES, Box, Zone, check_box, edges_crossed, scaled_bands

__version__ = "0.1.1"

__all__ = [
    "PLATFORMS",
    "ZONES",
    "Box",
    "Zone",
    "check_box",
    "edges_crossed",
    "load_frame",
    "panel",
    "scaled_bands",
    "sheet",
    "unsafe_mask",
]
