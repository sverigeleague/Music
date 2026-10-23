"""kworb.net YouTube artist pages: total views and current daily views of the artist's videos (official channel and
Content ID-tracked uploads that kworb counts). Saved to data/youtube.csv.

The page is found from the link on the artist's kworb Spotify page; otherwise from the artist's name. A page is
accepted only if it links back to the same Spotify artist ID, so a namesake is never matched.
"""
import csv
import glob
import gzip
import re
import unicodedata

from .. import storage
from ..config import DATA, RAW
from ..http import get

URL = "https://kworb.net/youtube/artist/{slug}.html"
CSV = DATA / "youtube.csv"
FIELDS = ["date", "spotify_id", "slug", "total_views", "daily_views", "videos"]
_int = lambda s: int(s.replace(",", "")) if s and s.replace(",", "").isdigit() else None


def slug_from_spotify_page(spotify_id: str) -> str | None:
    pages = sorted(glob.glob(str(RAW / "kworb" / "artist" / "*" / f"{spotify_id}.html.gz")))
    if not pages:
        return None
    with gzip.open(pages[-1], "rt") as f:
        m = re.search(r'href="[./]*/?youtube/artist/([^"/]+)\.html"', f.read())
    return m[1] if m else None


def slug_guess(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def parse(html: str) -> dict:
    total = re.search(r"Total views:</td><td[^>]*>([\d,]+)<", html)
    daily = re.search(r"Current daily avg:</td><td[^>]*>([\d,]+)<", html)
    videos = len(re.findall(r'href="\.\./video/[^"]+\.html"', html))
    back = re.search(r'spotify/artist/([0-9A-Za-z]{22})_songs\.html', html)
    return {"total_views": _int(total[1]) if total else None, "daily_views": _int(daily[1]) if daily else None,
            "videos": videos, "spotify_id": back[1] if back else None}


def fetch(spotify_id: str, name: str, day: str) -> dict | None:
    for slug in dict.fromkeys(filter(None, (slug_from_spotify_page(spotify_id), slug_guess(name)))):
        r = get(URL.format(slug=slug))
        if r.status_code != 200:
            continue
        p = parse(r.text)
        if p["spotify_id"] != spotify_id or p["total_views"] is None:
            continue  # not this artist's page
        storage.archive(f"kworb/youtube/{day}/{spotify_id}.html", URL.format(slug=slug), r.content)
        return {"date": day, "spotify_id": spotify_id, "slug": slug, **{k: p[k] for k in ("total_views", "daily_views", "videos")}}
    return None


def save(rows: list[dict]) -> None:
    new = not CSV.exists()
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def load_latest() -> dict[str, dict]:
    out = {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                if r["spotify_id"] not in out or r["date"] >= out[r["spotify_id"]]["date"]:
                    out[r["spotify_id"]] = r
    return out
