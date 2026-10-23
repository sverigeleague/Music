"""Apple Music: the daily top 100 most-played songs in COUNTRIES (Apple's public marketing-tools RSS feed, no key).
A second platform to confirm what Spotify shows. Saved to data/apple_charts.csv, one file per day appended.

Apple names the artists on each song ("Drake & Don Toliver", "A, B & C"). Each name is matched to our list by its
exact (case- and accent-folded) name; a name shared by two artists in our list is skipped. This is chart presence
only, so a name match is enough; Apple's artist ID is kept for a later ID map.
"""
import csv
import re
import unicodedata

from ..config import DATA
from ..http import get

FEED = "https://rss.marketingtools.apple.com/api/v2/{cc}/music/most-played/100/songs.json"
CSV = DATA / "apple_charts.csv"
FIELDS = ["date", "country", "position", "song", "artist_name", "apple_artist_id", "release_date", "genre"]
COUNTRIES = ("us", "gb", "ca", "au", "nz", "ie", "de", "fr", "nl", "be", "ch", "at", "se", "no", "dk", "fi", "it",
             "es", "pl", "br", "mx", "za", "ng", "jp", "in")


def fetch(cc: str) -> tuple[str, list[dict]]:
    r = get(FEED.format(cc=cc))
    if r.status_code != 200:
        return "", []
    feed = r.json().get("feed", {})
    return feed.get("updated", ""), feed.get("results", [])


def update(day: str) -> int:
    """Append today's charts unless already stored for this day."""
    have = set()
    if CSV.exists():
        with CSV.open() as f:
            have = {(r["date"], r["country"]) for r in csv.DictReader(f)}
    new = not CSV.exists()
    n = 0
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for cc in COUNTRIES:
            if (day, cc) in have:
                continue
            _updated, rows = fetch(cc)
            for i, s in enumerate(rows, 1):
                w.writerow({"date": day, "country": cc, "position": i, "song": s.get("name", ""),
                            "artist_name": s.get("artistName", ""), "apple_artist_id": s.get("artistId", ""),
                            "release_date": s.get("releaseDate", ""),
                            "genre": next((g["name"] for g in s.get("genres", []) if g.get("name") != "Music"), "")})
                n += 1
    return n


def fold(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9$]+", "", s)


def split_names(artist_name: str) -> list[str]:
    """'A, B & C' -> ['A', 'B', 'C']; a name that itself contains '&' is also tried whole."""
    parts = [p.strip() for p in re.split(r",\s*|\s+&\s+|\s+x\s+", artist_name) if p.strip()]
    return [artist_name] + parts if len(parts) > 1 else parts


def presence(names: dict[str, str]) -> tuple[dict[str, dict], str | None]:
    """Latest day's chart presence per spotify_id: {countries, best_pos, songs}. names: spotify_id -> name."""
    if not CSV.exists():
        return {}, None
    by_fold: dict[str, list[str]] = {}
    for sid, n in names.items():
        by_fold.setdefault(fold(n), []).append(sid)
    with CSV.open() as f:
        rows = list(csv.DictReader(f))
    day = max((r["date"] for r in rows), default=None)
    out: dict[str, dict] = {}
    for r in rows:
        if r["date"] != day:
            continue
        for nm in split_names(r["artist_name"]):
            ids = by_fold.get(fold(nm), [])
            if len(ids) != 1:
                continue  # unknown or ambiguous name
            p = out.setdefault(ids[0], {"countries": set(), "best_pos": 999, "songs": set()})
            p["countries"].add(r["country"])
            p["best_pos"] = min(p["best_pos"], int(r["position"]))
            p["songs"].add(r["song"])
    return {k: {"countries": sorted(v["countries"]), "best_pos": v["best_pos"], "songs": sorted(v["songs"])[:5]}
            for k, v in out.items()}, day
