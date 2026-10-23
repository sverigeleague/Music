"""Deezer releases per artist: the label printed on each recent release (the ℗ line's owner as Deezer shows it) and
Deezer's genre for each release. Saved to data/release_labels.csv; refreshed monthly for releases not yet seen.

The artist's albums list gives every release with its date and Deezer genre (116 = Rap/Hip Hop); the label needs
one request per release, so labels are read only for the most recent releases (RECENT within YEARS years).
"""
import csv
from datetime import date

from ..config import DATA
from ..http import get

API = "https://api.deezer.com"
CSV = DATA / "release_labels.csv"
FIELDS = ["deezer_artist_id", "album_id", "title", "release_date", "record_type", "genre_id", "label", "checked"]
RECENT, YEARS = 6, 2
RAP = 116  # Deezer's Rap/Hip Hop genre


def load() -> dict[str, list[dict]]:
    """deezer_artist_id -> releases, newest first."""
    out: dict[str, list[dict]] = {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                out.setdefault(r["deezer_artist_id"], []).append(r)
    for v in out.values():
        v.sort(key=lambda r: r["release_date"], reverse=True)
    return out


def releases(deezer_id: str) -> list[dict]:
    r = get(f"{API}/artist/{deezer_id}/albums", params={"limit": 100})
    return r.json().get("data", []) if r.status_code == 200 else []


def update(deezer_ids: list[str], today: date | None = None) -> int:
    today = today or date.today()
    cutoff = date(today.year - YEARS, today.month, min(today.day, 28)).isoformat()
    have = {(a, r["album_id"]) for a, rs in load().items() for r in rs}
    new = not CSV.exists()
    n = 0
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for did in deezer_ids:
            rel = sorted(releases(did), key=lambda a: a.get("release_date", ""), reverse=True)
            for a in [a for a in rel if a.get("release_date", "") >= cutoff][:RECENT]:
                if (did, str(a["id"])) in have:
                    continue
                d = get(f"{API}/album/{a['id']}")
                label = d.json().get("label", "") if d.status_code == 200 else ""
                w.writerow({"deezer_artist_id": did, "album_id": a["id"], "title": a["title"],
                            "release_date": a["release_date"], "record_type": a.get("record_type", ""),
                            "genre_id": a.get("genre_id", ""), "label": label, "checked": today.isoformat()})
                n += 1
            f.flush()
    return n
