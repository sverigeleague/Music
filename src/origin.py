"""Country of origin for registry artists Wikidata gives no country for (2026-10-26, Scout by country).

The registry takes the country from Wikidata (citizenship P27 or country of origin P495, found by the Spotify ID).
Where that is blank, in this order, each looked up at the source and cached:
  1. Wikidata by the item's QID (items linked from MusicBrainz carry no Spotify ID, so the registry's query misses
     them): P27 / P495, the same rule as the registry (several: the country of birth among them); for a group with
     neither, the country of its place of formation (P740 -> P17).
  2. MusicBrainz: the artist's country (its area when the area is a country), else the country its area or begin area
     lies in (area -> "part of" parents, up to the country; a subdivision's ISO 3166-2 code names its country).
Wikidata and MusicBrainz disagreeing: left blank and listed in review/country_review.csv. Several Wikidata countries
with no birth country among them stay as the registry writes them ("Canada / United States").
Saved to data/country_of_origin.csv (spotify_id, country, source, basis, checked); registry() reads it, so a later
registry run keeps the filled countries.
"""
import csv
import json
from datetime import date

from .config import DATA, REVIEW
from .countries import ISO2
from .http import get

CSV = DATA / "country_of_origin.csv"
FIELDS = ["spotify_id", "name", "country", "source", "basis", "checked"]
AREAS = DATA / "musicbrainz_areas.json"  # area id -> {"name", "type", "code" (ISO 3166-1 alpha-2 of its country)}
REVIEW_CSV = REVIEW / "country_review.csv"
API = "https://musicbrainz.org/ws/2"
NAME_OF = {v: k for k, v in ISO2.items() if k not in ("Northern Ireland", "East Germany")}  # code -> registry name


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}


def save(rows: dict[str, dict]) -> None:
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: r["name"].casefold()))


def name_of(code: str) -> str:
    """'US' -> 'United States'; '' for codes the site has no name for (and MusicBrainz's XW, XE...)."""
    return NAME_OF.get((code or "").lower(), "")


def pick(countries: set[str], born: set[str]) -> str:
    """The registry's rule (wikidata.details): one country: it; several: the birth country among them, else all."""
    from .collectors.wikidata import COUNTRY_NAMES
    cs = sorted(countries)
    if len(cs) > 1:
        cs = sorted(set(cs) & born) or cs
    return " / ".join(sorted({COUNTRY_NAMES.get(c, c) for c in cs} - {""}))


def wikidata_by_qid(qids: list[str]) -> dict[str, tuple[str, str]]:
    """QID -> (country, basis) from P27 / P495 (birth country breaks ties), else P740's country."""
    from .collectors import wikidata
    got: dict[str, dict] = {}
    for chunk in [qids[i:i + 200] for i in range(0, len(qids), 200)]:
        for r in wikidata.query(f"""
SELECT ?item ?cLabel ?bLabel ?fLabel WHERE {{ VALUES ?item {{ {' '.join('wd:' + q for q in chunk)} }}
  OPTIONAL {{ ?item wdt:P27|wdt:P495 ?c }} OPTIONAL {{ ?item wdt:P19/wdt:P17 ?b }} OPTIONAL {{ ?item wdt:P740/wdt:P17 ?f }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""):
            d = got.setdefault(wikidata.qid(r["item"]), {"c": set(), "b": set(), "f": set()})
            for k in ("c", "b", "f"):
                if r.get(k + "Label"):
                    d[k].add(r[k + "Label"])
    out = {}
    for q, d in got.items():
        if d["c"]:
            out[q] = (pick(d["c"], d["b"]), "Wikidata: citizenship or country of origin (P27/P495)")
        elif len(d["f"]) == 1:
            out[q] = (pick(d["f"], set()), "Wikidata: country of the place of formation (P740)")
    return {q: v for q, v in out.items() if v[0]}


def _area(area_id: str, cache: dict) -> dict:
    if area_id not in cache:
        r = get(f"{API}/area/{area_id}", params={"fmt": "json", "inc": "area-rels"})
        if r.status_code != 200:
            return {}
        a = r.json()
        code = (a.get("iso-3166-1-codes") or [""])[0] or (a.get("iso-3166-2-codes") or [""])[0].split("-")[0]
        parent = next((x["area"]["id"] for x in a.get("relations", []) if x.get("type") == "part of"
                       and x.get("direction") == "backward" and x.get("area")), "")
        cache[area_id] = {"name": a.get("name", ""), "type": a.get("type") or "", "code": code, "parent": parent}
    return cache[area_id]


def area_country(area_id: str, cache: dict) -> str:
    """The ISO code of the country an area lies in, walking "part of" parents (a few levels)."""
    for _ in range(8):
        a = _area(area_id, cache)
        if not a:
            return ""
        if a["code"]:
            return a["code"]
        if not a["parent"]:
            return ""
        area_id = a["parent"]
    return ""


def musicbrainz_country(mbid: str, cached_code: str, cache: dict) -> tuple[str, str]:
    """(country, basis) for a MusicBrainz artist: its country field, else its area's or begin area's country."""
    if cached_code:
        return name_of(cached_code), "MusicBrainz: artist country"
    r = get(f"{API}/artist/{mbid}", params={"fmt": "json"})
    if r.status_code != 200:
        return "", ""
    a = r.json()
    if a.get("country"):
        return name_of(a["country"]), "MusicBrainz: artist country"
    for key, word in (("area", "area"), ("begin-area", "begin area")):
        if (a.get(key) or {}).get("id"):
            c = name_of(area_country(a[key]["id"], cache))
            if c:
                return c, f"MusicBrainz: {word} {a[key]['name']}, in {c}"
    return "", ""


def fill(artists: dict[str, dict], limit: int | None = None, genres=("hip_hop", "country", "review")) -> dict[str, int]:
    """Country for the registry artists with none (hip-hop and country first). Rows already checked are skipped; a
    row with an empty country records that both sources were asked and gave none (or disagreed)."""
    from .collectors import musicbrainz
    have, mbc = load(), musicbrainz.load()
    cache = json.loads(AREAS.read_text()) if AREAS.exists() else {}
    todo = [a for a in artists.values() if not a.get("country") and a["spotify_id"] not in have
            and (genres is None or a["genre"] in genres)][:limit]
    wd = wikidata_by_qid(sorted({a["wikidata_id"] for a in todo if a.get("wikidata_id")})) if todo else {}
    conflicts, n = [], {"wikidata": 0, "musicbrainz": 0, "none": 0, "conflict": 0}
    for i, a in enumerate(todo, 1):
        s, w = a["spotify_id"], wd.get(a.get("wikidata_id", ""), ("", ""))
        m = musicbrainz_country(a["musicbrainz_id"], (mbc.get(s) or {}).get("country", ""), cache) \
            if a.get("musicbrainz_id") else ("", "")
        row = {"spotify_id": s, "name": a["name"], "checked": date.today().isoformat()}
        if w[0] and m[0] and m[0] not in w[0].split(" / "):
            row.update(country="", source="", basis=f"sources disagree: {w[1]} {w[0]}; {m[1]} ({m[0]})")
            conflicts.append({**row, "genre": a["genre"], "wikidata": w[0], "musicbrainz": m[0]})
            n["conflict"] += 1
        elif w[0]:
            row.update(country=w[0], source="wikidata", basis=w[1])
            n["wikidata"] += 1
        elif m[0]:
            row.update(country=m[0], source="musicbrainz", basis=m[1])
            n["musicbrainz"] += 1
        else:
            row.update(country="", source="", basis="no country on Wikidata or MusicBrainz")
            n["none"] += 1
        have[s] = row
        if i % 50 == 0:
            save(have)
            AREAS.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    save(have)
    AREAS.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    if conflicts:
        old = list(csv.DictReader(REVIEW_CSV.open())) if REVIEW_CSV.exists() else []
        keep = {r["spotify_id"]: r for r in old} | {r["spotify_id"]: r for r in conflicts}
        with REVIEW_CSV.open("w", newline="") as f:
            w = csv.DictWriter(f, ["spotify_id", "name", "genre", "wikidata", "musicbrainz", "basis", "checked"],
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(keep.values(), key=lambda r: r["name"].casefold()))
    return n


def apply(artists: dict[str, dict]) -> int:
    """Copy filled countries into blank registry rows (the registry's own Wikidata country always wins)."""
    have, n = load(), 0
    for s, a in artists.items():
        if not a.get("country") and (have.get(s) or {}).get("country"):
            a["country"] = have[s]["country"]
            n += 1
    return n
