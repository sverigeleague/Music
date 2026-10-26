"""The Unsigned export's links (ROADMAP 11.12): official public profiles only, never personal contact data."""
import json
from pathlib import Path

import pytest

from src.site_build import PUBLIC_LINKS, public_links

SITE = Path(__file__).resolve().parent.parent / "site" / "data"


def test_keeps_only_official_profiles():
    links = {"spotify": "https://open.spotify.com/artist/x", "youtube": "https://www.youtube.com/channel/UCx",
             "instagram": "https://www.instagram.com/x", "wikidata": "https://www.wikidata.org/wiki/Q1",
             "tiktok": "https://www.tiktok.com/@x", "x": "https://x.com/x", "email": "mailto:someone@example.com"}
    assert public_links(links) == {k: links[k] for k in ("spotify", "youtube", "instagram", "wikidata")}


def test_drops_missing_and_non_https():
    assert public_links({"spotify": "https://open.spotify.com/artist/x", "youtube": None, "instagram": "",
                         "wikidata": "http://www.wikidata.org/wiki/Q1"}) == {"spotify": "https://open.spotify.com/artist/x"}
    assert public_links(None) == {}
    assert public_links({}) == {}


@pytest.mark.parametrize("d", [SITE, SITE / "country"])
def test_built_unsigned_rows_carry_only_public_links(d):
    f = d / "unsigned.json"
    if not f.exists():
        pytest.skip("site not built")
    rows = json.loads(f.read_text())["unsigned"]
    if rows and "links" not in rows[0]:
        pytest.skip("built before the links were added")
    for u in rows:
        assert set(u["links"]) <= set(PUBLIC_LINKS), u["name"]
        assert u["links"].get("spotify", "").endswith(u["id"]), u["name"]
