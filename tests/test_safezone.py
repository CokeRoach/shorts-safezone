import json
import shutil
import subprocess

import pytest
from PIL import Image

from shorts_safezone import PLATFORMS, ZONES, Box, check_box, load_frame, panel, scaled_bands, sheet, unsafe_mask
from shorts_safezone.__main__ import main


def test_youtube_zone_on_1080x1920():
    assert scaled_bands(ZONES["youtube"], 1080, 1920) == [(288, 1248, 48, 888)]


def test_tiktok_zone_scales_from_720x1280():
    assert scaled_bands(ZONES["tiktok"], 1080, 1920) == [(240, 840, 120, 960), (840, 1260, 120, 780)]


def test_reels_zone_is_percent():
    top, bottom, left, right = scaled_bands(ZONES["reels"], 1080, 1920)[0]
    assert (top, bottom, left, right) == pytest.approx((268.8, 1248, 64.8, 1015.2))


def test_box_exactly_on_the_youtube_edges_is_safe():
    assert check_box(Box(48, 288, 888, 1248), platforms=("youtube",)) == {"youtube": []}


def test_one_pixel_past_an_edge_is_covered():
    result = check_box(Box(47, 288, 889, 1249), platforms=("youtube",))
    assert result == {"youtube": ["left", "right", "bottom"]}


def test_tiktok_right_buttons_cover_only_the_lower_part():
    upper = Box.from_xywh(120, 300, 840, 100)
    lower = Box.from_xywh(120, 1000, 840, 100)
    assert check_box(upper, platforms=("tiktok",)) == {"tiktok": []}
    assert check_box(lower, platforms=("tiktok",)) == {"tiktok": ["right"]}
    assert check_box(Box.from_xywh(120, 1000, 660, 100), platforms=("tiktok",)) == {"tiktok": []}


def test_box_spanning_both_tiktok_bands_must_fit_the_narrow_one():
    assert check_box(Box.from_xywh(120, 700, 800, 300), platforms=("tiktok",)) == {"tiktok": ["right"]}


def test_typical_low_caption_is_covered_on_every_platform():
    caption = Box.from_xywh(150, 1250, 780, 90)
    result = check_box(caption)
    assert set(result) == set(PLATFORMS)
    assert all("bottom" in crossed for crossed in result.values())


def test_other_9_16_sizes_scale():
    assert check_box(Box(24, 144, 444, 624), 540, 960, ("youtube",)) == {"youtube": []}


def test_non_vertical_canvas_is_rejected():
    with pytest.raises(ValueError):
        check_box(Box(0, 0, 10, 10), 1920, 1080)


def test_bad_box_is_rejected():
    with pytest.raises(ValueError):
        Box.from_xywh(0, 0, 0, 10)


def test_every_zone_names_its_source():
    for zone in ZONES.values():
        assert zone.source.startswith("https://")
        assert zone.method and zone.checked


@pytest.mark.parametrize(
    "key, point, covered",
    [
        ("youtube", (540, 960), False),
        ("youtube", (540, 100), True),
        ("youtube", (1000, 960), True),
        ("tiktok", (900, 500), False),
        ("tiktok", (900, 1000), True),
        ("reels", (540, 1500), True),
    ],
)
def test_unsafe_mask(key, point, covered):
    assert unsafe_mask(1080, 1920, key).getpixel(point) == (255 if covered else 0)


def test_panel_tints_only_the_unsafe_area():
    frame = Image.new("RGB", (1080, 1920), (0, 0, 255))
    out = panel(frame, "youtube")
    assert out.size == (1080, 1920)
    assert out.getpixel((540, 960)) == (0, 0, 255)
    r, g, b = out.getpixel((540, 1700))
    assert r > 80 and b < 255


def test_sheet_has_one_panel_per_platform():
    out = sheet(Image.new("RGB", (1080, 1920)))
    assert out.size == (3 * 540 + 2 * 16, 960)


def test_cli_box_exit_code(capsys):
    assert main(["box", "200", "400", "600", "200"]) == 0
    assert main(["box", "150", "1250", "780", "90", "--json"]) == 1
    data = json.loads(capsys.readouterr().out.split("\n", 3)[-1])
    assert data["youtube"] == {"safe": False, "crossed": ["bottom"]}


def test_cli_zones_json_has_sources(capsys):
    assert main(["zones", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["zones"]["tiktok"]["bands_top_bottom_left_right"] == [[240, 840, 120, 960], [840, 1260, 120, 780]]
    assert data["zones"]["youtube"]["source"].startswith("https://services.google.com/")


def test_cli_rejects_unknown_platform():
    with pytest.raises(SystemExit):
        main(["box", "0", "0", "1", "1", "--platform", "snapchat"])


def test_cli_check_image(tmp_path):
    src = tmp_path / "frame.png"
    Image.new("RGB", (1080, 1920), (30, 30, 30)).save(src)
    assert main(["check", str(src), "--platform", "youtube,tiktok"]) == 0
    out = tmp_path / "frame.safezone.png"
    assert Image.open(out).size == (2 * 540 + 16, 960)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_video_frame(tmp_path):
    video = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=1080x1920:d=2",
         "-pix_fmt", "yuv420p", str(video)],
        check=True,
    )
    frame = load_frame(video, at=1.0)
    assert frame.size == (1080, 1920)
    assert frame.getpixel((540, 960))[0] > 200
    assert main(["check", str(video), "--at", "1", "-o", str(tmp_path / "out.png")]) == 0
