"""Draw the safe zones over a frame, one panel per platform."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .zones import PLATFORMS, ZONES, scaled_bands

UNSAFE = (255, 40, 60, 140)
EDGE = (255, 255, 255, 230)
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


def load_frame(path: str | Path, at: float = 0.0) -> Image.Image:
    """An image file, or the frame of a video at ``at`` seconds (needs ffmpeg on PATH)."""
    path = Path(path)
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        return Image.open(path).convert("RGB")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("reading a video needs ffmpeg on PATH; pass an image instead")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "frame.png"
        cmd = [ffmpeg, "-v", "error", "-ss", str(at), "-i", str(path), "-frames:v", "1", str(out)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not out.exists():
            raise RuntimeError(f"ffmpeg could not read a frame at {at}s: {result.stderr.strip()}")
        with Image.open(out) as frame:
            return frame.convert("RGB")


def unsafe_mask(width: int, height: int, key: str) -> Image.Image:
    """Mode "L" mask: 255 where the platform's UI may cover the frame, 0 where it is clear."""
    mask = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(mask)
    for top, bottom, left, right in scaled_bands(ZONES[key], width, height):
        draw.rectangle(
            [round(left), round(top), round(right) - 1, round(bottom) - 1], fill=0
        )
    return mask


def panel(frame: Image.Image, key: str) -> Image.Image:
    """``frame`` with the platform's unsafe area tinted and the safe edge outlined."""
    width, height = frame.size
    base = frame.convert("RGBA")
    mask = unsafe_mask(width, height, key)
    tint = Image.new("RGBA", (width, height), UNSAFE)
    base.alpha_composite(Image.composite(tint, Image.new("RGBA", (width, height)), mask))
    line = max(3, width // 270)
    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(line | 1))
    base.paste(Image.new("RGBA", (width, height), EDGE), (0, 0), edge)
    draw = ImageDraw.Draw(base)
    label = ZONES[key].label
    font = _font(max(14, width // 22))
    pad = width // 40
    box = draw.textbbox((pad, pad), label, font=font)
    draw.rectangle([box[0] - pad // 2, box[1] - pad // 2, box[2] + pad // 2, box[3] + pad // 2],
                   fill=(0, 0, 0, 170))
    draw.text((pad, pad), label, fill=(255, 255, 255, 255), font=font)
    return base.convert("RGB")


def sheet(frame: Image.Image, platforms: tuple[str, ...] = PLATFORMS) -> Image.Image:
    """Panels side by side, scaled to 540 px wide each."""
    panels = [panel(frame, key) for key in platforms]
    w = 540
    h = round(frame.height * w / frame.width)
    gap = 16
    out = Image.new("RGB", (len(panels) * w + (len(panels) - 1) * gap, h), (24, 24, 24))
    for i, p in enumerate(panels):
        out.paste(p.resize((w, h), Image.LANCZOS), (i * (w + gap), 0))
    return out


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)
