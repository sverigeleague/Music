"""Country artists below kworb's 500k-listener floor (owner C1, 2026-10-24): a crawl of Deezer's related-artists graph.

kworb lists Spotify monthly listeners only down to about 500k, which covers some 400 country artists. Below that the
only free, allowed route found (research of 2026-10-24, DECISIONS.md) is Deezer:
  seeds    Deezer's country chart and genre lists (genre 84), artists already matched in data/deezer_genres.csv with a
           country share of 0.5+, and Wikidata country artists with a Deezer ID (P2722)
  crawl    most fans first; each country artist's related artists (up to 50) are read and admitted when at least half
           of 3+ releases are filed under Country
  order    the sum of Deezer's rank for the artist's top 10 tracks (r = 0.79 with log Spotify listeners on 240 country
           artists above the floor; Spearman only 0.22 among artists of similar size, so the order is grade C)

Spotify IDs come from Wikidata (P2722 -> P1902); never guessed from the name. Deezer's data is used internally, credited,
and not republished as a table. Saved to data/country_deezer.csv.
"""
import csv
import heapq
import time
from datetime import date

from ..config import DATA
from ..http import get
from . import deezer_genres, wikidata

API = "https://api.deezer.com"
CSV = DATA / "country_deezer.csv"
FIELDS = ["deezer_id", "name", "fans", "releases", "country_share", "latest", "top10_rank_sum", "spotify_id", "qid",
          "source", "checked", "mbid", "id_source", "id_checked"]
COUNTRY, MIN_SHARE, MIN_RELEASES = 84, 0.5, 3


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["deezer_id"]: r for r in csv.DictReader(f)}


def _json(path: str, **params) -> dict:
    for wait in (5, 10, 20, None):
        r = get(f"{API}/{path}", params=params)
        j = r.json() if r.status_code == 200 else {}
        if isinstance(j, dict) and j.get("error", {}).get("code") == 4 and wait:  # quota exceeded: wait and retry
            time.sleep(wait)
            continue
        return j if isinstance(j, dict) and "error" not in j else {}
    return {}


def releases(deezer_id) -> tuple[int, float | None, str]:
    """(releases with a genre, share filed under Country, latest release date)."""
    d = _json(f"artist/{deezer_id}/albums", limit=100).get("data", [])
    g = [a.get("genre_id") for a in d if a.get("genre_id", -1) > 0]
    latest = max((a.get("release_date", "") for a in d), default="")
    return len(g), (sum(x == COUNTRY for x in g) / len(g) if g else None), latest


def wikidata_deezer() -> dict[str, dict]:
    """Deezer ID -> {qid, spotify_id} for Wikidata items with a country genre (P136 under country music)."""
    rows = wikidata.query(f"""
SELECT ?dz ?item ?sp WHERE {{ ?item wdt:P2722 ?dz ; wdt:P136 ?g . ?g wdt:P279* wd:{wikidata.COUNTRY} .
  OPTIONAL {{ ?item wdt:P1902 ?sp }} }}""")
    out: dict[str, dict] = {}
    for r in rows:
        d = out.setdefault(r["dz"], {"qid": wikidata.qid(r["item"]), "spotify_id": ""})
        d["spotify_id"] = d["spotify_id"] or r.get("sp", "")
    return out


def seeds(wd: dict[str, dict]) -> dict[str, tuple[str, str, int]]:
    """Deezer ID -> (name, source, fans)."""
    out: dict[str, tuple[str, str, int]] = {}
    for path, src in ((f"chart/{COUNTRY}/artists", "chart"), (f"genre/{COUNTRY}/artists", "genre")):
        for a in _json(path, limit=100).get("data", []):
            out.setdefault(str(a["id"]), (a["name"], src, a.get("nb_fan", 0)))
    for r in deezer_genres.load().values():
        if r.get("deezer_id") and r.get("match") == "exact" and r.get("country_share") not in ("", None) \
                and float(r["country_share"]) >= MIN_SHARE:
            out.setdefault(str(r["deezer_id"]), (r["name"], "kworb", int(r.get("fans") or 0)))
    for dz in wd:
        out.setdefault(dz, ("", "wikidata", 0))
    return out


def crawl(limit: int | None = None) -> int:
    """Read the graph from the seeds and rewrite data/country_deezer.csv. Returns the country artists found."""
    wd = wikidata_deezer()
    seen: dict[str, dict] = {}
    heap: list[tuple[int, str]] = []
    today = date.today().isoformat()

    def admit(dz: str, name: str, src: str, fans: int) -> None:
        if dz in seen:
            return
        n, share, latest = releases(dz)
        seen[dz] = {"deezer_id": dz, "name": name, "fans": fans, "releases": n, "latest": latest, "source": src,
                    "country_share": round(share, 3) if share is not None else "", "checked": today,
                    "country": share is not None and share >= MIN_SHARE and n >= MIN_RELEASES}
        if seen[dz]["country"]:
            heapq.heappush(heap, (-fans, dz))

    for dz, (name, src, fans) in seeds(wd).items():
        if not name or not fans:  # Wikidata seeds carry no name or fans: read the artist
            a = _json(f"artist/{dz}")
            if not a:
                continue
            name, fans = a.get("name", name), a.get("nb_fan", 0)
        admit(dz, name, src, fans)
    done = 0
    while heap and (limit is None or done < limit):
        _, dz = heapq.heappop(heap)
        a = seen[dz]
        a["top10_rank_sum"] = sum(t.get("rank", 0) for t in _json(f"artist/{dz}/top", limit=10).get("data", []))
        for b in _json(f"artist/{dz}/related", limit=50).get("data", []):
            admit(str(b["id"]), b["name"], "related", b.get("nb_fan", 0))
        done += 1
    rows = [a for a in seen.values() if a["country"] and a.get("top10_rank_sum") is not None]
    if limit is not None:  # a partial crawl (a test run) updates the rows it read and keeps the rest
        fresh = {a["deezer_id"] for a in rows}
        rows += [r for k, r in load().items() if k not in fresh]
        for r in rows:
            r["top10_rank_sum"] = int(r.get("top10_rank_sum") or 0)
    prev = load()
    for a in rows:
        a.update(wd.get(a["deezer_id"], {}))
        if a.get("spotify_id"):
            a["id_source"] = "wikidata"
        p = prev.get(a["deezer_id"], {})
        for k in ("mbid", "id_checked"):  # MusicBrainz lookups of earlier runs are kept
            a[k] = a.get(k) or p.get(k, "")
        if not a.get("spotify_id") and p.get("id_source") == "musicbrainz":
            a.update(spotify_id=p["spotify_id"], qid=a.get("qid") or p.get("qid", ""), id_source="musicbrainz")
    rows.sort(key=lambda a: -a["top10_rank_sum"])
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def spotify_ids(limit: int | None = None, recheck_days: int = 90) -> int:
    """Spotify IDs for crawled artists that have none, from MusicBrainz (musicbrainz.ids_for_deezer): the artist's
    Deezer page and Spotify page linked on one MusicBrainz artist. Artists looked up in the last `recheck_days` days
    are skipped. Returns the IDs found."""
    from datetime import timedelta
    from . import musicbrainz
    rows = load()
    since = (date.today() - timedelta(days=recheck_days)).isoformat()
    todo = [r for r in rows.values() if not r.get("spotify_id") and (r.get("id_checked") or "") < since][:limit]
    from concurrent.futures import ThreadPoolExecutor
    found = 0
    # three requests in flight: http.get still spaces MusicBrainz requests 1.1 s apart across threads, but its
    # answers take 2-3 s, so one at a time would leave the allowed rate mostly unused
    with ThreadPoolExecutor(3) as pool:
        for i, (r, ids) in enumerate(zip(todo, pool.map(lambda r: musicbrainz.ids_for_deezer(r["deezer_id"]), todo)), 1):
            r["id_checked"] = date.today().isoformat()
            r["mbid"] = ids["mbid"] or r.get("mbid", "")
            if ids["spotify_id"]:
                r.update(spotify_id=ids["spotify_id"], id_source="musicbrainz", qid=r.get("qid") or ids["qid"])
                found += 1
            if i % 50 == 0 or i == len(todo):
                _write(rows.values())
    return found


def _write(rows) -> None:
    rows = sorted(rows, key=lambda a: -int(a.get("top10_rank_sum") or 0))
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
