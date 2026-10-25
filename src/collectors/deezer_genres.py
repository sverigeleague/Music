"""Deezer as a second genre source, for artists Wikidata does not tag: the share of an artist's releases that Deezer
files under Rap/Hip Hop (genre 116), and under Latin genres (Reggaeton 122, Latin Music 197). Saved to
data/deezer_genres.csv with the Deezer artist ID and fans, so later steps need no second search.

Match: exact normalised name, the one with most fans; a second exact match with over 10% of those fans makes the
match "ambiguous", and an ambiguous artist is never taken on Deezer's genre alone.
"""
import csv
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from ..config import DATA
from ..http import get
from .deezer import _norm

API = "https://api.deezer.com"
CSV = DATA / "deezer_genres.csv"
FIELDS = ["spotify_id", "name", "deezer_id", "fans", "match", "releases", "rap_share", "latin_share", "checked",
          "country_share"]
RAP, LATIN, COUNTRY = {116}, {122, 197}, {84}  # Deezer genre IDs (api.deezer.com/genre): Country 84, added 2026-10-24


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}


def lookup(spotify_id: str, name: str) -> dict:
    row = {"spotify_id": spotify_id, "name": name, "checked": date.today().isoformat()}
    r = get(f"{API}/search/artist", params={"q": name, "limit": 10})
    hits = [a for a in (r.json().get("data", []) if r.status_code == 200 else []) if _norm(a["name"]) == _norm(name)]
    if not hits:
        return {**row, "match": "none"}
    hits.sort(key=lambda a: -a.get("nb_fan", 0))
    best = hits[0]
    match = "ambiguous" if len(hits) > 1 and hits[1].get("nb_fan", 0) > 0.1 * best.get("nb_fan", 0) else "exact"
    al = get(f"{API}/artist/{best['id']}/albums", params={"limit": 50})
    rel = al.json().get("data", []) if al.status_code == 200 else []
    g = [a.get("genre_id") for a in rel if a.get("genre_id", -1) > 0]
    return {**row, "deezer_id": best["id"], "fans": best.get("nb_fan"), "match": match, "releases": len(g),
            "rap_share": round(sum(x in RAP for x in g) / len(g), 3) if g else "",
            "latin_share": round(sum(x in LATIN for x in g) / len(g), 3) if g else "",
            "country_share": round(sum(x in COUNTRY for x in g) / len(g), 3) if g else ""}


def add_confirmed(spotify_id: str, name: str, deezer_id, fans, match: str = "titles") -> dict:
    """A row for an artist whose Deezer match was confirmed from their songs (match "titles" or "isrc"): the release
    shares read from that Deezer artist, not from a name search."""
    rows = load()
    al = get(f"{API}/artist/{deezer_id}/albums", params={"limit": 50})
    g = [a.get("genre_id") for a in (al.json().get("data", []) if al.status_code == 200 else []) if a.get("genre_id", -1) > 0]
    share = lambda ids: round(sum(x in ids for x in g) / len(g), 3) if g else ""
    rows[spotify_id] = {"spotify_id": spotify_id, "name": name, "deezer_id": deezer_id, "fans": fans, "match": match,
                        "releases": len(g), "rap_share": share(RAP), "latin_share": share(LATIN),
                        "country_share": share(COUNTRY), "checked": date.today().isoformat()}
    _save(rows)
    return rows[spotify_id]


def refresh_country(workers: int = 4, limit: int | None = None) -> int:
    """Rows read before country_share existed (2026-10-24): read the artist's releases again for the country share
    (one request each) and rewrite the file. The rap and Latin shares are refreshed from the same read."""
    rows = load()
    todo = [r for r in rows.values() if r.get("deezer_id") and r.get("country_share") in (None, "")][:limit]

    def work(r):
        al = get(f"{API}/artist/{r['deezer_id']}/albums", params={"limit": 50})
        if al.status_code != 200:
            return
        g = [a.get("genre_id") for a in al.json().get("data", []) if a.get("genre_id", -1) > 0]
        if g:
            r.update(releases=len(g), rap_share=round(sum(x in RAP for x in g) / len(g), 3),
                     latin_share=round(sum(x in LATIN for x in g) / len(g), 3),
                     country_share=round(sum(x in COUNTRY for x in g) / len(g), 3))
        else:
            r["country_share"] = ""
    for i in range(0, len(todo), 500):  # save as it goes
        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(work, todo[i:i + 500]))
        _save(rows)
    _save(rows)
    return len(todo)


def _save(rows: dict) -> None:
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in FIELDS} for r in rows.values())


def update(todo: list[tuple[str, str]], workers: int = 4) -> int:
    """todo: (spotify_id, name); artists already checked are skipped."""
    have = load()
    jobs = [j for j in todo if j[0] not in have]
    new = not CSV.exists()
    lock = threading.Lock()
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()

        def work(job):
            row = lookup(*job)
            with lock:
                w.writerow({k: row.get(k, "") for k in FIELDS})
                f.flush()
        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(work, jobs))
    return len(jobs)
