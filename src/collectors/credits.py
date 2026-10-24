"""Producer and songwriter credits from MusicBrainz (core data CC0), for each tracked artist's biggest songs.

Song -> recording code (ISRC, from data/track_dates.csv) -> MusicBrainz recording (GET /isrc/<isrc>) -> its relations
(GET /recording/<id>?inc=artist-rels+work-rels+work-level-rels): producers on the recording, writers on the work.
Two requests per song at MusicBrainz's 1 a second; each recording code is looked up once (data/credits.csv) and
retried after RETRY_DAYS if MusicBrainz had nothing then. Coverage is partial: MusicBrainz volunteers have entered
producer credits for about a third of the hip-hop hits tested (2026-10-24), and the site says so.
"""
import csv
from datetime import date, timedelta

from ..config import DATA
from ..http import get

API = "https://musicbrainz.org/ws/2"
CSV = DATA / "credits.csv"
FIELDS = ["isrc", "recording", "title", "producers", "writers", "checked"]
PER_ARTIST, RETRY_DAYS = 3, 90
_join = lambda people: ";".join(f"{n}~{m}" for n, m in people)


def split(cell: str) -> list[tuple[str, str]]:
    """'Mustard~<mbid>;Sounwave~<mbid>' -> [('Mustard', '<mbid>'), ...]"""
    return [tuple(p.split("~", 1)) for p in filter(None, (cell or "").split(";"))]


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["isrc"]: r for r in csv.DictReader(f)}


def lookup(isrc: str) -> dict:
    row = {"isrc": isrc, "recording": "", "title": "", "producers": "", "writers": "", "checked": date.today().isoformat()}
    r = get(f"{API}/isrc/{isrc}", params={"fmt": "json"})
    recs = r.json().get("recordings", []) if r.status_code == 200 else []
    if not recs:
        return row
    rec = recs[0]
    d = get(f"{API}/recording/{rec['id']}", params={"fmt": "json", "inc": "artist-rels+work-rels+work-level-rels"})
    if d.status_code != 200:
        return row
    j = d.json()
    rels = j.get("relations", [])
    prod = {(x["artist"]["name"], x["artist"]["id"]) for x in rels if x.get("artist") and x.get("type") == "producer"}
    writers = {(y["artist"]["name"], y["artist"]["id"]) for x in rels if x.get("work")
               for y in x["work"].get("relations", []) if y.get("artist") and y.get("type") in ("writer", "composer", "lyricist")}
    row.update(recording=rec["id"], title=j.get("title", ""), producers=_join(sorted(prod)), writers=_join(sorted(writers)))
    return row


def update(isrcs: list[str], limit: int | None = None) -> int:
    have = load()
    stale = (date.today() - timedelta(days=RETRY_DAYS)).isoformat()
    todo = [i for i in dict.fromkeys(isrcs) if i and (i not in have or (not have[i]["recording"] and have[i]["checked"] < stale))]
    n = 0
    for isrc in todo[:limit]:
        have[isrc] = lookup(isrc)
        n += 1
        if n % 50 == 0:
            _save(have)
    _save(have)
    return n


def _save(rows: dict) -> None:
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: r["isrc"]))


def leaderboard(songs: list[dict], role: str = "producers", top: int = 50) -> list[dict]:
    """songs: [{isrc, title, daily, artist_id, artist}] -> people ranked by the daily streams of the songs they are
    credited on, with how many songs and artists."""
    cred, people = load(), {}
    for s in songs:
        c = cred.get(s.get("isrc") or "")
        for name, mbid in split(c[role]) if c else []:
            p = people.setdefault(mbid, {"name": name, "mbid": mbid, "daily": 0, "songs": [], "artists": set(), "isrcs": set()})
            if s["isrc"] in p["isrcs"]:  # one song on several artists' pages (a duo and its members) counts once
                continue
            p["isrcs"].add(s["isrc"])
            p["daily"] += s["daily"]
            p["songs"].append({"title": s["title"], "artist": s["artist"], "artist_id": s["artist_id"], "daily": s["daily"]})
            p["artists"].add(s["artist_id"])
    out = sorted(people.values(), key=lambda p: -p["daily"])[:top]
    for p in out:
        p["songs"] = sorted(p["songs"], key=lambda s: -s["daily"])[:5]
        p["artists"] = len(p["artists"])
        del p["isrcs"]
    return out
