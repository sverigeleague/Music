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
    optimise(DIR / f"{spotify_id}{ext}")
    author = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip() or "unknown"
    return {"file": f"photos/{spotify_id}{ext}", "author": author[:120], "license": lic,
            "license_url": meta.get("LicenseUrl", {}).get("value", ""), "page": info.get("descriptionurl", "")}


def optimise(path, min_bytes: int = 40_000) -> int:
    """Re-encodes a large thumbnail in place (2026-10-25, page speed): Commons sometimes serves a PNG or an
    uncompressed JPEG of a few hundred KB for a 250px photo shown at 32-120px. Opaque images become JPEG (quality 82),
    ones with real transparency WebP with alpha; the file name stays (browsers read the format from the bytes).
    Kept only when at least a fifth smaller. Returns the bytes saved."""
    import io
    from PIL import Image
    before = path.stat().st_size
    if before < min_bytes:
        return 0
    im = Image.open(path)
    im.load()
    clear = im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)
    if clear:
        im = im.convert("RGBA")
        clear = im.getchannel("A").getextrema()[0] < 255
    out = io.BytesIO()
    if clear:
        im.save(out, "WEBP", quality=82, method=6)
    else:
        im.convert("RGB").save(out, "JPEG", quality=82, optimize=True, progressive=True)
    if len(out.getvalue()) > before * 0.8:
        return 0
    path.write_bytes(out.getvalue())
    return before - len(out.getvalue())


if __name__ == "__main__":  # python -m src.photos: re-encode the photos already stored
    saved = sum(optimise(p) for p in sorted(DIR.glob("*.*")) if p.suffix in (".jpg", ".png"))
    print(f"photos: {saved // 1024} KB saved")
