"""Command line: ``shorts-safezone check|box|zones``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .overlay import load_frame, sheet
from .zones import PLATFORMS, ZONES, Box, check_box, is_vertical_9_16


def _platforms(value: str) -> tuple[str, ...]:
    if value == "all":
        return PLATFORMS
    keys = tuple(v.strip() for v in value.split(","))
    unknown = [k for k in keys if k not in ZONES]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown platform {', '.join(unknown)}; use {', '.join(PLATFORMS)}")
    return keys


def _size(value: str) -> tuple[int, int]:
    try:
        w, h = (int(v) for v in value.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError("size is WIDTHxHEIGHT, for example 1080x1920") from None
    return w, h


def cmd_check(args) -> int:
    frame = load_frame(args.file, args.at)
    if not is_vertical_9_16(*frame.size):
        print(f"warning: {frame.width}x{frame.height} is not 9:16; zones are scaled anyway",
              file=sys.stderr)
    out = Path(args.output or Path(args.file).with_suffix("").as_posix() + ".safezone.png")
    sheet(frame, args.platform).save(out)
    print(out)
    return 0


def cmd_box(args) -> int:
    width, height = args.size
    result = check_box(Box.from_xywh(args.x, args.y, args.w, args.h), width, height, args.platform)
    if args.json:
        print(json.dumps({k: {"safe": not v, "crossed": v} for k, v in result.items()}, indent=2))
    else:
        for key, crossed in result.items():
            verdict = ("safe" if not crossed else "covered at the " + " and ".join(crossed)
                       + (" edges" if len(crossed) > 1 else " edge"))
            print(f"{ZONES[key].label:16} {verdict}")
    return 0 if not any(result.values()) else 1


def cmd_zones(args) -> int:
    width, height = args.size
    data = {}
    for key in args.platform:
        zone = ZONES[key]
        sx, sy = width / zone.width, height / zone.height
        bands = [[round(t * sy), round(b * sy), round(l * sx), round(r * sx)] for t, b, l, r in zone.bands]
        data[key] = {"label": zone.label, "bands_top_bottom_left_right": bands,
                     "source": zone.source, "method": zone.method, "checked": zone.checked}
    if args.json:
        print(json.dumps({"size": [width, height], "zones": data}, indent=2))
        return 0
    print(f"Safe areas on {width}x{height} (clear bands: top-bottom, left-right in px)")
    for key, z in data.items():
        print(f"\n{z['label']}")
        for t, b, l, r in z["bands_top_bottom_left_right"]:
            print(f"  y {t}-{b}, x {l}-{r}")
        print(f"  source:  {z['source']}")
        print(f"  method:  {z['method']}")
        print(f"  checked: {z['checked']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shorts-safezone",
        description="See what YouTube Shorts, TikTok and Instagram Reels cover on a 9:16 video.",
    )
    parser.add_argument("--version", action="version", version=f"shorts-safezone {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="draw the safe zones over an image or a video frame")
    p.add_argument("file", help="image (png, jpg) or video (mp4, mov, webm...)")
    p.add_argument("--at", type=float, default=0.0, help="video time in seconds (default 0)")
    p.add_argument("-o", "--output", help="output PNG (default: FILE.safezone.png)")
    p.add_argument("--platform", type=_platforms, default=PLATFORMS,
                   help="all, or a comma list of " + ", ".join(PLATFORMS))
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("box", help="check whether a box (x y width height) is safe; exit 1 if not")
    for name in ("x", "y", "w", "h"):
        p.add_argument(name, type=float)
    p.add_argument("--size", type=_size, default=(1080, 1920), help="canvas WIDTHxHEIGHT (default 1080x1920)")
    p.add_argument("--platform", type=_platforms, default=PLATFORMS)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_box)

    p = sub.add_parser("zones", help="print the safe areas and where each number comes from")
    p.add_argument("--size", type=_size, default=(1080, 1920))
    p.add_argument("--platform", type=_platforms, default=PLATFORMS)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_zones)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
