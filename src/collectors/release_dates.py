"""First release date per Spotify track: Deezer matches in data/track_dates.csv, MusicBrainz dates by ISRC in
data/isrc_dates.csv (two caches, so the two passes can run at the same time, each at its own site's rate limit).

1. Deezer search (artist + title): candidates with the same normalised title whose credits include the artist (lead or
   featured). Each candidate's track record gives its ISRC and the release date of that edition.
2. MusicBrainz by ISRC: the recording's first release date (CC0 data), which catches remasters and compilations
   dated later than the original.
3. Songs Deezer cannot match (some catalogues are missing there): MusicBrainz recording search by title and artist,
   the earliest first release date among recordings with the same title credited to the artist.
The first release date is the earliest of these. No match: the track stays undated and counts towards the coverage
gap, never as current or catalog.
"""
import csv
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import unicodedata
from datetime import date

from ..config import DATA
from ..http import get

CACHE = DATA / "track_dates.csv"
FIELDS = ["track_id", "artist_id", "title", "deezer_date", "isrc", "deezer_id", "checked"]
ISRC_CACHE = DATA / "isrc_dates.csv"
ISRC_FIELDS = ["isrc", "musicbrainz_date", "checked"]
# songs Deezer could not match: MusicBrainz recording search by title and artist
SEARCH_CACHE = DATA / "musicbrainz_search_dates.csv"
SEARCH_FIELDS = ["track_id", "musicbrainz_date", "checked"]


def norm(s: str) -> str:
    """Title or name for matching: no accents, case, brackets ("(feat. X)", "[Remix]") or " - From ..." suffixes."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    s = re.sub(r"\s*[\(\[].*?[\)\]]", "", s)
    s = re.sub(r"\s+-\s+.*$", "", s)
    s = re.sub(r"\s+(feat|ft|featuring)\.?\s.*$", "", s)  # "LOVE. FEAT. ZACARI." -> "love"
    return re.sub(r"[^a-z0-9]", "", s)


def _read(path, key) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open() as f:
        return {r[key]: r for r in csv.DictReader(f)}


def _key(d: str) -> str:
    """Sort key for dates that may be year-only ('2016') or year-month: compare on the latest day they allow."""
    return {4: d + "-12-31", 7: d + "-28"}.get(len(d), d[:10])


def load() -> dict[str, dict]:
    """track_id -> row with `first_release`: the earlier of the Deezer and MusicBrainz dates."""
    tracks, isrcs = _read(CACHE, "track_id"), _read(ISRC_CACHE, "isrc")
    searched = _read(SEARCH_CACHE, "track_id")
    for t, r in tracks.items():
        mb = isrcs.get(r["isrc"], {}).get("musicbrainz_date", "") if r["isrc"] else ""
        mb = mb or searched.get(t, {}).get("musicbrainz_date", "")
        r["musicbrainz_date"] = mb
        dates = [d for d in (r["deezer_date"], mb) if d]
        r["first_release"] = min(dates, key=_key) if dates else ""
    return tracks


def _deezer(artist: str, title: str) -> list[dict]:
    q = re.sub(r"[\(\[].*?[\)\]]", "", title)
    r = get("https://api.deezer.com/search", params={"q": f"{artist} {q}", "limit": 50})
    hits = [t for t in (r.json().get("data", []) if r.status_code == 200 else []) if norm(t["title"]) == norm(title)]
    # covers and "sped up" uploads often rank first: the artist's own releases go first, guest spots after
    hits.sort(key=lambda t: norm(t["artist"]["name"]) != norm(artist))
    out = []
    for t in hits[:3]:
        d = get(f"https://api.deezer.com/track/{t['id']}")
        if d.status_code != 200:
            continue
        d = d.json()
        names = {norm(c["name"]) for c in d.get("contributors", [])} | {norm(d.get("artist", {}).get("name", ""))}
        if norm(artist) in names and (d.get("release_date") or "") > "1900":
            out.append(d)
    return out


def _musicbrainz(isrc: str) -> str | None:
    r = get(f"https://musicbrainz.org/ws/2/isrc/{isrc}", params={"fmt": "json"})
    if r.status_code != 200:
        return None
    dates = [x["first-release-date"] for x in r.json().get("recordings", []) if x.get("first-release-date")]
    return min(dates) if dates else None


def lookup(artist_id: str, artist: str, track_id: str, title: str) -> dict:
    row = {"track_id": track_id, "artist_id": artist_id, "title": title, "checked": date.today().isoformat()}
    found = _deezer(artist, title)
    if found:
        first = min(found, key=lambda d: d["release_date"])
        row.update(deezer_date=first["release_date"], isrc=first.get("isrc", ""), deezer_id=first["id"])
    return row


def _musicbrainz_search(artist: str, title: str) -> str | None:
    q = re.sub(r'["\\]', "", re.sub(r"[\(\[].*?[\)\]]", "", title)).strip()
    r = get("https://musicbrainz.org/ws/2/recording", params={
        "fmt": "json", "limit": 25, "query": f'recording:"{q}" AND artist:"{artist}"'})
    if r.status_code != 200:
        return None
    dates = []
    for rec in r.json().get("recordings", []):
        credited = {norm(c.get("name", "")) for c in rec.get("artist-credit", []) if isinstance(c, dict)}
        if norm(rec.get("title", "")) == norm(title) and norm(artist) in credited and rec.get("first-release-date"):
            dates.append(rec["first-release-date"])
    return min(dates, key=_key) if dates else None


def update_musicbrainz_search(limit: int | None = None) -> int:
    """MusicBrainz recording search for every song in the Deezer cache that Deezer could not date."""
    done = _read(SEARCH_CACHE, "track_id")
    names = {}
    from .. import config  # artist names come from the registry
    with (config.REGISTRY / "artists.csv").open() as f:
        names = {r["spotify_id"]: r["name"] for r in csv.DictReader(f)}
    todo = [r for t, r in _read(CACHE, "track_id").items() if not r["deezer_date"] and t not in done][:limit]
    new = not SEARCH_CACHE.exists()
    with SEARCH_CACHE.open("a", newline="") as f:
        w = csv.DictWriter(f, SEARCH_FIELDS)
        if new:
            w.writeheader()
        for r in todo:
            d = _musicbrainz_search(names.get(r["artist_id"], ""), r["title"]) if names.get(r["artist_id"]) else None
            w.writerow({"track_id": r["track_id"], "musicbrainz_date": d or "", "checked": date.today().isoformat()})
            f.flush()
    return len(todo)


def update_musicbrainz(limit: int | None = None) -> int:
    """MusicBrainz first release date for every ISRC in the Deezer cache not yet looked up."""
    done = _read(ISRC_CACHE, "isrc")
    todo = sorted({r["isrc"] for r in _read(CACHE, "track_id").values() if r["isrc"]} - set(done))[:limit]
    new = not ISRC_CACHE.exists()
    with ISRC_CACHE.open("a", newline="") as f:
        w = csv.DictWriter(f, ISRC_FIELDS)
        if new:
            w.writeheader()
        for isrc in todo:
            w.writerow({"isrc": isrc, "musicbrainz_date": _musicbrainz(isrc) or "", "checked": date.today().isoformat()})
            f.flush()
    return len(todo)


def update(todo: list[tuple[str, str, str, str]], limit: int | None = None, retry: bool = False) -> dict[str, dict]:
    """Deezer pass. todo: (artist_id, artist name, track_id, title); tracks already in the cache are skipped
    (with retry, only those that have a date: undated ones are looked up again and the newer row wins)."""
    cache = _read(CACHE, "track_id")
    seen = {t for t, r in cache.items() if r["deezer_date"]} if retry else set(cache)
    jobs = []
    for job in todo:
        if job[2] not in seen:
            seen.add(job[2])
            jobs.append(job)
    jobs = jobs[:limit]
    new = not CACHE.exists()
    lock = threading.Lock()
    with CACHE.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()

        def work(job):
            row = lookup(*job)
            with lock:
                w.writerow({k: row.get(k, "") for k in FIELDS})
                f.flush()
        # 8 workers overlap Deezer's response time; src.http keeps the shared pace under its limit
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(work, jobs))
    return load()
