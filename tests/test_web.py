"""The web page in docs/index.html must use the same zones as the Python package."""

import json
import re
from pathlib import Path

from shorts_safezone import ZONES

PAGE = Path(__file__).resolve().parent.parent / "docs" / "index.html"


def page_zones():
    html = PAGE.read_text(encoding="utf-8")
    match = re.search(r'<script type="application/json" id="zone-data">(.*?)</script>', html, re.S)
    assert match, "zone-data block missing from docs/index.html"
    return json.loads(match.group(1))


def test_web_page_zones_match_python():
    expected = {
        key: {
            "label": z.label,
            "width": z.width,
            "height": z.height,
            "bands": [list(b) for b in z.bands],
            "source": z.source,
            "checked": z.checked,
        }
        for key, z in ZONES.items()
    }
    assert page_zones() == expected


def test_web_page_loads_nothing_from_other_sites():
    html = PAGE.read_text(encoding="utf-8")
    assert not re.search(r"<script[^>]+src=", html)
    for href in re.findall(r'<link[^>]+href="([^"]+)"', html):
        assert not href.startswith(("http:", "https:", "//")), href
    fonts = (PAGE.parent / "fonts" / "fonts.css").read_text(encoding="utf-8")
    assert "http" not in fonts


def test_every_language_has_every_string():
    html = PAGE.read_text(encoding="utf-8")
    block = html[html.index("const I18N = {"):html.index("const LANGS")]
    langs = re.findall(r"^  (\w\w): \{", block, re.M)
    assert langs == ["en", "ko", "ja", "fr", "ru", "zh"]
    keys = {}
    for lang, body in re.findall(r"^  (\w\w): \{(.*?)^  \},", block, re.M | re.S):
        keys[lang] = set(re.findall(r"(?<![^\s,])([A-Za-z][A-Za-z0-9]*): \"", body))
    for lang in langs[1:]:
        assert keys[lang] == keys["en"], (lang, keys["en"] ^ keys[lang])
    options = re.findall(r'<option value="(\w+)">', html)
    assert options == langs
