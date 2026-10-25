"""MusicBrainz: community genre votes per artist, cached in data/musicbrainz.csv.

The votes are licensed CC BY-NC-SA: used here only as one input to our own genre decision, never shown on the
site (DECISIONS.md, 2026-10-23). One request per second, as MusicBrainz asks.
"""
import csv
from datetime import date
from urllib.parse import quote

from ..config import DATA
from ..http import get

API = "https://musicbrainz.org/ws/2"
CACHE = DATA / "musicbrainz.csv"
FIELDS = ["spotify_id", "musicbrainz_id", "genres", "country", "fetched"]


def load() -> dict[str, dict]:
    if not CACHE.exists():
        return {}
    with CACHE.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}


def genres_of(row: dict) -> list[tuple[str, int]]:
    """'hip hop:21|r&b:10' -> [('hip hop', 21), ('r&b', 10)]"""
    out = []
    for part in filter(None, (row.get("genres") or "").split("|")):
        name, _, n = part.rpartition(":")
        out.append((name, int(n)))
    return out


def mbid_for_spotify(spotify_id: str) -> str | None:
    r = get(f"{API}/url", params={"fmt": "json", "inc": "artist-rels",
                                  "resource": f"https://open.spotify.com/artist/{spotify_id}"})
    if r.status_code != 200:
        return None
    rels = [x for x in r.json().get("relations", []) if x.get("artist")]
    return rels[0]["artist"]["id"] if len(rels) == 1 else None  # several artists on one URL: leave unmatched


def fetch(spotify_id: str, mbid: str | None) -> dict:
    mbid = mbid or mbid_for_spotify(spotify_id)
    row = {"spotify_id": spotify_id, "musicbrainz_id": mbid or "", "genres": "", "country": "",
           "fetched": date.today().isoformat()}
    if mbid:
        r = get(f"{API}/artist/{quote(mbid)}", params={"fmt": "json", "inc": "genres"})
        if r.status_code == 200:
            a = r.json()
            g = sorted(((x["name"], x["count"]) for x in a.get("genres", []) if x["count"] > 0), key=lambda x: -x[1])
            row.update(genres="|".join(f"{n}:{c}" for n, c in g), country=a.get("country") or "")
    return row


def update(wanted: dict[str, str | None], limit: int | None = None) -> dict[str, dict]:
    """Fetch artists missing from the cache. wanted: spotify_id -> MusicBrainz ID from Wikidata (or None)."""
    cache = load()
    todo = [s for s in wanted if s not in cache][:limit]
    new = not CACHE.exists()
    with CACHE.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for s in todo:
            row = fetch(s, wanted[s])
            w.writerow(row)
            f.flush()
            cache[s] = row
    return cache


def wikidata_of(mbid: str) -> str | None:
    """The Wikidata item MusicBrainz links from the artist (a curated url relation), e.g. 'Q123'; None if none."""
    r = get(f"{API}/artist/{mbid}", params={"inc": "url-rels", "fmt": "json"})
    if r.status_code != 200:
        return None
    for rel in r.json().get("relations", []):
        url = (rel.get("url") or {}).get("resource", "")
        if rel.get("type") == "wikidata" and "/wiki/Q" in url:
            return url.rsplit("/", 1)[-1]
    return None
