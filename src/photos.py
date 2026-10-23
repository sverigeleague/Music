"""Artist photos from Wikimedia Commons (via Wikidata P18): a 160px thumbnail in site/photos/ and its credit line
(author, licence, link). No photo: the site shows the artist's initials."""
import re

from .config import SITE
from .http import get

API = "https://commons.wikimedia.org/w/api.php"
DIR = SITE / "photos"


def fetch(spotify_id: str, commons_url: str) -> dict | None:
    """commons_url: Wikidata's P18 value (http://commons.wikimedia.org/wiki/Special:FilePath/<file>)."""
    from urllib.parse import unquote
    name = unquote(commons_url.rsplit("/", 1)[-1])
    r = get(API, params={"action": "query", "titles": f"File:{name}", "prop": "imageinfo", "iiprop": "url|extmetadata",
                         "iiurlwidth": 160, "format": "json"})
    if r.status_code != 200:
        return None
    page = next(iter(r.json()["query"]["pages"].values()))
    info = (page.get("imageinfo") or [None])[0]
    if not info or not info.get("thumburl"):
        return None
    meta = info.get("extmetadata", {})
    lic = meta.get("LicenseShortName", {}).get("value", "")
    if not re.search(r"CC|Public domain|PD", lic, re.I):
        return None  # only free licences
    img = get(info["thumburl"])
    if img.status_code != 200:
        return None
    DIR.mkdir(parents=True, exist_ok=True)
    ext = ".png" if info["thumburl"].lower().endswith(".png") else ".jpg"
    (DIR / f"{spotify_id}{ext}").write_bytes(img.content)
    author = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip() or "unknown"
    return {"file": f"photos/{spotify_id}{ext}", "author": author[:120], "license": lic,
            "license_url": meta.get("LicenseUrl", {}).get("value", ""), "page": info.get("descriptionurl", "")}
