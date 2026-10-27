"""Smaller acts: hip-hop and country artists below kworb's 500k-listener floor, for Scout's country view (owner,
2026-10-26: "look into deezer fans for smaller countries"; "triangulate with other sources").

Who (each identity looked up at the source, never by name):
  wikidata  items with a hip-hop genre (P136 under Q11401) or the occupation rapper (P106 Q2252262), or a country
            genre (Q83440), that carry a Spotify ID (P1902) or a Deezer ID (P2722)
  related   Deezer's related artists of those and of the registry's artists from the same countries, kept only when
            a Wikidata item carries that Deezer ID (the item gives the country and, where it has one, the Spotify ID).
            A related artist with no Wikidata item has no country source: counted, never listed.
  wider     (2026-10-27, `_widen`) the related artists with no Wikidata item, Deezer's chart and editor playlists,
            the official national charts, our Spotify / Apple Music / Shazam charts: each ID to Wikidata (P2722,
            P1902, P2850), else MusicBrainz url relations; a chart never gives the country
Country: Wikidata P27/P495 by QID (src/origin.py's rule), else MusicBrainz (country, area or begin area). Left out: anyone on kworb's listener pages or already in the
registry (their genre was decided there).

What is read per artist (all free, no key; src.http paces each host):
  Deezer    fans (artist/{id}); release shares by genre, latest release and each release's date (albums); the top 10
            tracks' Deezer rank and which of them came out in the last 90 days (top)
  Wikipedia monthly views of the English and the home-country-language article (Wikidata sitelinks), last 6 months
  ListenBrainz all-time listeners (popularity/artist, by the MusicBrainz ID on the Wikidata item)
  YouTube   the official channel ID (Wikidata P2397): the daily `ytapi` step reads its statistics (run.youtube_channels)
The same signals are read for the registry's artists with kworb listener counts (CAL): the calibration and hold-out set
(src/small_acts.py). Files: data/small_acts.csv, data/small_acts_calibration.csv, data/deezer_fans_history.csv (weekly
fans snapshot, `smallfans`), review/small_acts_review.csv.
"""
import csv
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from urllib.parse import quote

from ..config import DATA, REVIEW
from ..http import get
from . import wikidata

API = "https://api.deezer.com"
CSV = DATA / "small_acts.csv"
CAL = DATA / "small_acts_calibration.csv"
FANS = DATA / "deezer_fans_history.csv"
REVIEW_CSV = REVIEW / "small_acts_review.csv"
MB_LINKS = DATA / "musicbrainz_deezer_links.json"  # MBID -> the Deezer and Spotify pages its url relations link
FIELDS = ["genre", "decision", "basis", "qid", "name", "country", "spotify_id", "deezer_id", "youtube_channel", "mbid",
          "found_via", "fans", "releases", "rap_share", "latin_share", "country_share", "latest", "rank_sum", "top_n",
          "fresh_n", "dated_n", "fresh_title", "wiki_lang", "wiki_3m", "wiki_prev3m", "lb_users", "checked",
          "lead_n", "top_dated", "top_latin", "rapper", "country_source"]
CAL_FIELDS = ["genre", "spotify_id", "name", "country", "ml", "deezer_id", "fans", "rank_sum", "top_n", "wiki_lang",
              "wiki_3m", "wiki_prev3m", "lb_users", "checked"]
RAPPER = "Q2252262"
FRESH_DAYS = 90
# the home country's Wikipedia, read beside English (a country not listed: English only)
LANG = {"Sweden": "sv", "Norway": "no", "Denmark": "da", "Finland": "fi", "Iceland": "is", "Netherlands": "nl",
        "Belgium": "nl", "Germany": "de", "Austria": "de", "Switzerland": "de", "France": "fr", "Spain": "es",
        "Italy": "it", "Portugal": "pt", "Brazil": "pt", "Poland": "pl", "Czech Republic": "cs", "Slovakia": "sk",
        "Turkey": "tr", "Russia": "ru", "Ukraine": "uk", "Greece": "el", "Romania": "ro", "Hungary": "hu",
        "Serbia": "sr", "Croatia": "hr", "Bulgaria": "bg", "Mexico": "es", "Argentina": "es", "Chile": "es",
        "Colombia": "es", "Peru": "es", "Venezuela": "es", "Japan": "ja", "South Korea": "ko", "Estonia": "et",
        "Latvia": "lv", "Lithuania": "lt", "Slovenia": "sl", "Israel": "he", "Indonesia": "id", "Vietnam": "vi",
        "Thailand": "th", "Philippines": "tl", "Morocco": "fr", "Algeria": "fr", "Tunisia": "fr"}


_cache: dict | None = None  # SMALL_ACTS_CACHE=<file.json>: Deezer answers kept between runs of one session


def _json(path: str, **params) -> dict:
    global _cache
    import json
    import os
    key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    cf = os.environ.get("SMALL_ACTS_CACHE")
    if cf and _cache is None:
        _cache = json.loads(open(cf).read()) if os.path.exists(cf) else {}
    if cf and key in _cache:
        return _cache[key]
    out = _fetch(path, **params)
    if cf:
        _cache[key] = out
        if len(_cache) % 500 == 0:
            _save_cache()
    return out


def _save_cache() -> None:
    import json
    import os
    if os.environ.get("SMALL_ACTS_CACHE") and _cache is not None:
        with open(os.environ["SMALL_ACTS_CACHE"], "w") as f:
            json.dump(dict(_cache), f)


def _fetch(path: str, **params) -> dict:
    for wait in (5, 10, 20, None):
        r = get(f"{API}/{path}", params=params)
        j = r.json() if r.status_code == 200 else {}
        if isinstance(j, dict) and j.get("error", {}).get("code") == 4 and wait:  # quota exceeded: wait and retry
            time.sleep(wait)
            continue
        return j if isinstance(j, dict) and "error" not in j else {}
    return {}


def _read(path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def load() -> list[dict]:
    return _read(CSV)


def load_calibration() -> list[dict]:
    return _read(CAL)


def _write(path, fields, rows) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---------- who
def wikidata_items(genre: str) -> dict[str, dict]:
    """QID -> {name, spotify_ids, deezer_ids, youtube, mbid} for the genre's Wikidata items with a Spotify or Deezer ID."""
    # one query per route: a UNION of the two runs into the endpoint's 60 s limit and comes back cut short
    wheres = ([f"?item wdt:P136 ?g . ?g wdt:P279* wd:{wikidata.HIP_HOP} .", f"?item wdt:P106 wd:{RAPPER} ."]
              if genre == "hip_hop" else [f"?item wdt:P136 ?g . ?g wdt:P279* wd:{wikidata.COUNTRY} ."])
    rows = []
    for where in wheres:
        rows += wikidata.query(f"""
SELECT DISTINCT ?item ?itemLabel ?sp ?dz ?yt ?mb WHERE {{ {where}
  OPTIONAL {{ ?item wdt:P1902 ?sp }} OPTIONAL {{ ?item wdt:P2722 ?dz }} FILTER(BOUND(?sp) || BOUND(?dz))
  OPTIONAL {{ ?item wdt:P2397 ?yt }} OPTIONAL {{ ?item wdt:P434 ?mb }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")
    return _items(rows)


def _items(rows: list[dict]) -> dict[str, dict]:
    import re
    out: dict[str, dict] = {}
    for r in rows:
        if not re.fullmatch(r"Q\d+", wikidata.qid(r["item"])):
            continue  # not an item (a lexeme or a blank value)
        d = out.setdefault(wikidata.qid(r["item"]), {"name": r.get("itemLabel", ""), "spotify_ids": set(),
                                                      "deezer_ids": set(), "youtube": set(), "mbid": set()})
        for k, col in (("spotify_ids", "sp"), ("deezer_ids", "dz"), ("youtube", "yt"), ("mbid", "mb")):
            if r.get(col):
                d[k].add(r[col])
    return out


def items_by_deezer(deezer_ids: list[str]) -> dict[str, dict]:
    """QID -> item, for Wikidata items carrying any of these Deezer artist IDs (P2722)."""
    out: dict[str, dict] = {}
    for i in range(0, len(deezer_ids), 1000):
        v = " ".join(f'"{d}"' for d in deezer_ids[i:i + 1000])
        out.update(_items(wikidata.query(f"""
SELECT ?item ?itemLabel ?sp ?dz ?yt ?mb WHERE {{ VALUES ?dz {{ {v} }} ?item wdt:P2722 ?dz .
  OPTIONAL {{ ?item wdt:P1902 ?sp }} OPTIONAL {{ ?item wdt:P2397 ?yt }} OPTIONAL {{ ?item wdt:P434 ?mb }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")))
    return out


def wikidata_genres(qids: list[str]) -> dict[str, list[tuple[str, bool, bool]]]:
    """QID -> [(genre label, under hip-hop, Latin)], as wikidata.details gives them for the registry."""
    out: dict[str, list] = {}
    for i in range(0, len(qids), 300):
        v = " ".join("wd:" + q for q in qids[i:i + 300])
        for r in wikidata.query(f"""
SELECT ?item ?gLabel ?hh ?latin WHERE {{ VALUES ?item {{ {v} }} ?item wdt:P136 ?g .
  BIND(EXISTS {{ ?g wdt:P279* wd:{wikidata.HIP_HOP} }} AS ?hh)
  BIND(EXISTS {{ VALUES ?l {{ {' '.join('wd:' + x for x in wikidata.LATIN)} }} ?g wdt:P279* ?l }} AS ?latin)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""):
            out.setdefault(wikidata.qid(r["item"]), []).append((r["gLabel"], r["hh"] == "true", r["latin"] == "true"))
    return out


# ---------- Deezer
def deezer_read(dz: str, today: date) -> dict:
    """fans, release shares, latest release, and the top 10 tracks: Deezer rank sum and how many are under 90 days old."""
    from .deezer_genres import RAP, LATIN, COUNTRY
    a = _json(f"artist/{dz}")
    if not a:
        return {}
    al = _json(f"artist/{dz}/albums", limit=100).get("data", [])
    g = [x.get("genre_id") for x in al if x.get("genre_id", -1) > 0]
    share = lambda ids: round(sum(x in ids for x in g) / len(g), 3) if g else ""
    dated = {str(x["id"]): x.get("release_date", "") for x in al}
    top = _json(f"artist/{dz}/top", limit=10).get("data", [])
    since = (today - timedelta(days=FRESH_DAYS)).isoformat()
    days = [(t, dated.get(str((t.get("album") or {}).get("id")), "")) for t in top]
    fresh = [t for t, d in days if d and d >= since]
    # the songs (owner 2026-10-27): how many top tracks the artist leads, and how many of the top tracks' own releases
    # Deezer files as Latin (reggaeton or urbano singers that Wikidata calls rappers)
    gen = {str(x["id"]): x.get("genre_id", -1) for x in al}
    tg = [gen[str((t.get("album") or {}).get("id"))] for t in top if gen.get(str((t.get("album") or {}).get("id")), -1) > 0]
    return {"name": a.get("name", ""), "fans": a.get("nb_fan", 0), "releases": len(g), "rap_share": share(RAP),
            "latin_share": share(LATIN), "country_share": share(COUNTRY),
            "latest": max((x.get("release_date", "") for x in al), default=""),
            "rank_sum": sum(int(t.get("rank") or 0) for t in top), "top_n": len(top),
            "fresh_n": len(fresh), "dated_n": sum(1 for _, d in days if d),
            "fresh_title": fresh[0].get("title", "") if fresh else "",
            "lead_n": sum(1 for t in top if str((t.get("artist") or {}).get("id", "")) == str(dz)),
            "top_dated": len(tg), "top_latin": round(sum(x in LATIN for x in tg) / len(tg), 3) if tg else ""}


def related(dz: str) -> list[str]:
    return [str(b["id"]) for b in _json(f"artist/{dz}/related", limit=50).get("data", [])]


# ---------- Wikipedia, ListenBrainz
def sitelinks(qids: list[str], langs: set[str]) -> dict[str, dict[str, str]]:
    """QID -> {lang: article title} for English and the given languages."""
    wikis = " ".join(f"<https://{l}.wikipedia.org/>" for l in sorted(langs | {"en"}))
    out: dict[str, dict] = {}
    for i in range(0, len(qids), 300):
        v = " ".join("wd:" + q for q in qids[i:i + 300])
        for r in wikidata.query(f"""
SELECT ?item ?wiki ?title WHERE {{ VALUES ?item {{ {v} }} VALUES ?wiki {{ {wikis} }}
  ?a schema:about ?item ; schema:isPartOf ?wiki ; schema:name ?title . }}"""):
            out.setdefault(wikidata.qid(r["item"]), {})[r["wiki"].split("//")[1].split(".")[0]] = r["title"]
    return out


def views6(lang: str, title: str, today: date) -> list[int] | None:
    """Views (people, all devices) in each of the last 6 full months, oldest first; None when refused."""
    y, m = today.year, today.month - 6
    while m <= 0:
        y, m = y - 1, m + 12
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/"
           f"{quote(title.replace(' ', '_'), safe='')}/monthly/{y}{m:02d}0100/{today.year}{today.month:02d}0100")
    import os
    if os.environ.get("SMALL_ACTS_CACHE") and _cache is not None and url in _cache:
        return _cache[url]
    r = get(url)
    if r.status_code == 404:
        return [0] * 6
    if r.status_code != 200:
        return None
    v = [i["views"] for i in r.json().get("items", [])][-6:]
    v = [0] * (6 - len(v)) + v
    if _cache is not None:
        _cache[url] = v
    return v


def last6(series: list[tuple[str, int]], today: date) -> list[int]:
    """The last 6 full months from a stored monthly series [(YYYY-MM, views)] (data/wikipedia_pageviews.csv)."""
    months = []
    y, m = today.year, today.month
    for _ in range(6):
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
        months.append(f"{y}-{m:02d}")
    d = dict(series)
    return [d.get(k, 0) for k in reversed(months)]


def wiki_signal(links: dict[str, str], home: str, today: date, known: dict[str, list[int]] | None = None) -> dict:
    """English plus home-language views: the last 3 full months and the 3 before (for the trend). known: views
    already stored ({"en": [6 months]}), not asked again."""
    langs = [l for l in dict.fromkeys(["en", LANG.get(home, "en")]) if l in links or l in (known or {})]
    if not langs:
        return {}
    tot = [0] * 6
    for l in langs:
        v = (known or {}).get(l) or views6(l, links[l], today)
        if v is None:
            return {}
        tot = [a + b for a, b in zip(tot, v)]
    return {"wiki_lang": "+".join(langs), "wiki_3m": sum(tot[3:]), "wiki_prev3m": sum(tot[:3])}


def lb_users(mbids: list[str]) -> dict[str, int]:
    from . import listenbrainz
    import re
    ids = sorted({m for m in mbids if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", m or "")})
    out = {}
    for i in range(0, len(ids), listenbrainz.BATCH):  # a batch ListenBrainz refuses is skipped, not fatal
        try:
            pop = listenbrainz.popularity(ids[i:i + listenbrainz.BATCH], date.today().strftime("%Y-%m"))
        except RuntimeError:
            continue
        out.update({m: v[0] for m, v in pop.items() if v})
    return out


def mb_links(mbids: list[str]) -> int:
    """MusicBrainz url relations (artist/<mbid>?inc=url-rels, 1 request a second) for MBIDs not yet cached: the Deezer
    and Spotify artist pages each links. For Wikidata items with no Deezer ID (P2722) but a MusicBrainz ID (P434)."""
    import json
    from ..http import get as hget
    cache = json.loads(MB_LINKS.read_text()) if MB_LINKS.exists() else {}
    todo = [m for m in dict.fromkeys(mbids) if m and m not in cache]
    for i, m in enumerate(todo, 1):
        r = hget(f"https://musicbrainz.org/ws/2/artist/{m}", params={"inc": "url-rels", "fmt": "json"})
        if r.status_code not in (200, 404):
            continue
        urls = [(x.get("url") or {}).get("resource", "") for x in (r.json().get("relations", []) if r.status_code == 200 else [])]
        cache[m] = {"deezer": sorted({u.rstrip("/").split("/artist/")[1].split("?")[0] for u in urls if "deezer.com/" in u and "/artist/" in u}),
                    "spotify": sorted({u.rstrip("/").split("/artist/")[1].split("?")[0] for u in urls if "open.spotify.com/artist/" in u}),
                    "checked": date.today().isoformat()}
        if i % 50 == 0 or i == len(todo):
            MB_LINKS.write_text(json.dumps(cache, indent=0, sort_keys=True))
    return len(todo)


def _mb_deezer(item: dict) -> str:
    """The one Deezer page MusicBrainz links from the item's MusicBrainz artist, when that artist links no Spotify page
    other than the item's own; "" otherwise."""
    import json
    global _mbl
    if _mbl is None:
        _mbl = json.loads(MB_LINKS.read_text()) if MB_LINKS.exists() else {}
    if len(item["mbid"]) != 1:
        return ""
    c = _mbl.get(next(iter(item["mbid"])), {})
    if len(c.get("deezer", [])) != 1 or (c.get("spotify") and set(c["spotify"]) != item["spotify_ids"]):
        return ""
    return c["deezer"][0]


_mbl: dict | None = None


def key(r: dict) -> str:
    """A smaller act's key: its Wikidata QID, else its MusicBrainz ID (found through MusicBrainz alone)."""
    return r.get("qid") or ("mb:" + r["mbid"] if r.get("mbid") else "dz:" + (r.get("deezer_id") or ""))


# ---------- wider discovery (owner 2026-10-27: "lower the bar for all until you get to 100 for each country"). Every
# source below gives a Spotify, Deezer or Apple Music ID only; the country still comes from Wikidata or MusicBrainz,
# never from a chart, and the genre from the rule.
IDS = DATA / "chart_identities.csv"  # a charted song -> the Deezer artist IDs Deezer credits on it
IDS_FIELDS = ["kind", "artist", "title", "item_id", "deezer_ids", "checked"]
MB_URLS = DATA / "musicbrainz_url_lookup.json"  # streaming page URL -> the MusicBrainz artists whose url relations link it
MB_ARTISTS = DATA / "musicbrainz_small_artists.json"  # MBID -> country, areas, genre votes, Deezer/Spotify/Wikidata links
TOP_USER = "637006841"  # Deezer's "Deezer Charts" account: the "Top <country>" playlists
EDITORS = {"hip_hop": {"6141327361": r"rap|hip", "304139225": r"rap|hip|urban|straat|nederhop", "917475151": "",
                       "5374230724": "", "2534988706": "", "6795176503": "", "6749565983": ""},
           "country": {"4294642822": ""}}  # Deezer's editor accounts (Denmark, Benelux, rap, country), looked up 2026-10-27


def items_by(prop: str, ids: list[str]) -> dict[str, dict]:
    """QID -> item for Wikidata items carrying any of these IDs: P2722 Deezer, P1902 Spotify, P2850 Apple Music."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 800):
        v = " ".join(f'"{d}"' for d in ids[i:i + 800])
        out.update(_items(wikidata.query(f"""
SELECT ?item ?itemLabel ?sp ?dz ?yt ?mb WHERE {{ VALUES ?v {{ {v} }} ?item wdt:{prop} ?v .
  OPTIONAL {{ ?item wdt:P1902 ?sp }} OPTIONAL {{ ?item wdt:P2722 ?dz }} OPTIONAL {{ ?item wdt:P2397 ?yt }}
  OPTIONAL {{ ?item wdt:P434 ?mb }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")))
    return out


def items_by_qid(qids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(qids), 300):
        v = " ".join("wd:" + q for q in qids[i:i + 300])
        out.update(_items(wikidata.query(f"""
SELECT ?item ?itemLabel ?sp ?dz ?yt ?mb WHERE {{ VALUES ?item {{ {v} }}
  OPTIONAL {{ ?item wdt:P1902 ?sp }} OPTIONAL {{ ?item wdt:P2722 ?dz }} OPTIONAL {{ ?item wdt:P2397 ?yt }}
  OPTIONAL {{ ?item wdt:P434 ?mb }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")))
    return out


def wikidata_rappers(qids: list[str]) -> set[str]:
    """The QIDs among these whose occupation (P106) is rapper."""
    out = set()
    for i in range(0, len(qids), 500):
        v = " ".join("wd:" + q for q in qids[i:i + 500])
        out |= {wikidata.qid(r["item"]) for r in wikidata.query(
            f"SELECT ?item WHERE {{ VALUES ?item {{ {v} }} ?item wdt:P106 wd:{RAPPER} . }}")}
    return out


def _load_json(p) -> dict:
    import json
    return json.loads(p.read_text()) if p.exists() else {}


def _save_json(p, d: dict) -> None:
    import json
    p.write_text(json.dumps(d, ensure_ascii=False, indent=0, sort_keys=True))


def mb_by_urls(urls: list[str]) -> dict[str, list[list[str]]]:
    """URL -> [[MBID, country code]] of the artists whose url relations link it (MusicBrainz url lookup, up to 100 URLs
    a request, 1 request a second; cached in data/musicbrainz_url_lookup.json, an unlinked URL as [])."""
    cache = _load_json(MB_URLS)
    todo = [u for u in dict.fromkeys(urls) if u not in cache]
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        r = get("https://musicbrainz.org/ws/2/url", params=[("resource", u) for u in chunk] + [("inc", "artist-rels"), ("fmt", "json")])
        if r.status_code not in (200, 404):
            continue
        js = r.json() if r.status_code == 200 else {}
        got = {x["resource"]: sorted({(rel["artist"]["id"], rel["artist"].get("country") or "") for rel in x.get("relations", []) if rel.get("artist")})
               for x in (js.get("urls") or ([js] if js.get("resource") else []))}
        for u in chunk:
            cache[u] = [list(x) for x in got.get(u, [])]
        if (i // 100) % 10 == 9:
            _save_json(MB_URLS, cache)
    _save_json(MB_URLS, cache)
    return {u: cache[u] for u in urls if u in cache}


def mb_artists(mbids: list[str]) -> dict[str, dict]:
    """MBID -> {name, country (code), area, begin_area, genres [[name, votes]], deezer, spotify, wikidata} from
    artist/<mbid>?inc=genres+url-rels (1 a second; cached in data/musicbrainz_small_artists.json)."""
    cache = _load_json(MB_ARTISTS)
    todo = [m for m in dict.fromkeys(mbids) if m and m not in cache]
    for i, m in enumerate(todo, 1):
        r = get(f"https://musicbrainz.org/ws/2/artist/{m}", params={"inc": "genres+url-rels", "fmt": "json"})
        if r.status_code != 200:
            continue
        a = r.json()
        urls = [(x.get("url") or {}).get("resource", "") for x in a.get("relations", [])]
        tail = lambda u: u.rstrip("/").split("/")[-1].split("?")[0]
        cache[m] = {"name": a.get("name", ""), "country": a.get("country") or "",
                    "area": (a.get("area") or {}).get("id", ""), "area_name": (a.get("area") or {}).get("name", ""),
                    "begin_area": (a.get("begin-area") or {}).get("id", ""), "begin_area_name": (a.get("begin-area") or {}).get("name", ""),
                    "genres": [[g["name"], g.get("count", 0)] for g in a.get("genres", [])],
                    "deezer": sorted({tail(u) for u in urls if "deezer.com/" in u and "/artist/" in u}),
                    "spotify": sorted({tail(u) for u in urls if "open.spotify.com/artist/" in u}),
                    "wikidata": sorted({tail(u) for u in urls if "wikidata.org/wiki/Q" in u}),
                    "checked": date.today().isoformat()}
        if i % 50 == 0:
            _save_json(MB_ARTISTS, cache)
    _save_json(MB_ARTISTS, cache)
    return {m: cache[m] for m in mbids if m in cache}


def mb_country(a: dict) -> tuple[str, str]:
    """(country, basis) of a MusicBrainz artist (src/origin.py's rule: its country, else its area's or begin area's)."""
    import json
    from .. import origin
    if origin.name_of(a.get("country", "")):
        return origin.name_of(a["country"]), "MusicBrainz: artist country"
    cache = json.loads(origin.AREAS.read_text()) if origin.AREAS.exists() else {}
    for k, word in (("area", "area"), ("begin_area", "begin area")):
        if a.get(k):
            c = origin.name_of(origin.area_country(a[k], cache))
            if c:
                origin.AREAS.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
                return c, f"MusicBrainz: {word} {a.get(k + '_name', '')}, in {c}"
    origin.AREAS.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    return "", ""


def deezer_playlists(genre: str, countries: set[str]) -> dict[str, str]:
    """Deezer artist ID -> how found: the "Top <country>" playlists of Deezer's charts account for these countries
    (main artists and each track's credited contributors), and the genre's editor playlists (main artists)."""
    out: dict[str, str] = {}
    pls = []
    nxt = f"user/{TOP_USER}/playlists"
    while nxt:
        j = _json(nxt, limit=100) if "?" not in nxt else _json(nxt)
        pls += [(p, "Deezer chart playlist " + p["title"]) for p in j.get("data", [])
                if p["title"].startswith("Top ") and p["title"][4:] in countries]
        nxt = j.get("next", "").replace(API + "/", "") if j.get("next") else ""
    import re
    for user, pat in EDITORS.get(genre, {}).items():
        j = _json(f"user/{user}/playlists", limit=200)
        pls += [(p, "Deezer editor playlist " + p["title"]) for p in j.get("data", []) if not pat or re.search(pat, p["title"], re.I)]
    for p, via in pls:
        tracks = _json(f"playlist/{p['id']}/tracks", limit=200).get("data", [])
        for t in tracks:
            out.setdefault(str((t.get("artist") or {}).get("id", "")), via)
            if via.startswith("Deezer chart"):
                for c in _json(f"track/{t['id']}").get("contributors", []):
                    out.setdefault(str(c["id"]), via)
    out.pop("", None)
    return out


def _clean_title(t: str) -> str:
    import re
    from .apple_charts import fold
    return fold(re.split(r"\s[\(\[-]\s*(?:feat|ft|with|med)\b", t, flags=re.I)[0])


def identify(songs: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], list[str]]:
    """(kind "track"/"album", artist credit, title) -> the Deezer artist IDs Deezer credits on that song or album, when
    Deezer's search finds it with the title and a credited name both matching (folded). Cached in
    data/chart_identities.csv (an unmatched song as no IDs), so each song is searched once."""
    from .apple_charts import fold
    from .national_charts import names
    have = {(r["kind"], r["artist"], r["title"]): r for r in _read(IDS)}
    todo = [s for s in dict.fromkeys(songs) if s not in have]

    def one(s):
        kind, artist, title = s
        nm = names(artist)
        want = {fold(x) for x in nm}
        q = f'{nm[1] if len(nm) > 1 else nm[0]} {title}'  # Deezer's artist:"" track:"" form returns nothing (2026-10-27)
        hits = _json("search/album" if kind == "album" else "search", q=q, limit=10).get("data", [])
        ct = _clean_title(title)
        for h in hits:
            ht = _clean_title(h.get("title_short") or h.get("title") or "")
            if ht and ct and (ht == ct or ht.startswith(ct) or ct.startswith(ht)) and fold((h.get("artist") or {}).get("name", "")) in want:
                ids = {str(h["artist"]["id"])}
                if kind != "album":
                    ids |= {str(c["id"]) for c in _json(f"track/{h['id']}").get("contributors", []) if fold(c.get("name", "")) in want}
                return {"kind": kind, "artist": artist, "title": title, "item_id": h["id"],
                        "deezer_ids": ";".join(sorted(ids)), "checked": date.today().isoformat()}
        return {"kind": kind, "artist": artist, "title": title, "item_id": "", "deezer_ids": "", "checked": date.today().isoformat()}
    with ThreadPoolExecutor(6) as pool:
        for r in pool.map(one, todo):
            have[(r["kind"], r["artist"], r["title"])] = r
    _save_cache()
    _write(IDS, IDS_FIELDS, sorted(have.values(), key=lambda r: (r["kind"], r["artist"].casefold(), r["title"].casefold())))
    return {k: [x for x in v["deezer_ids"].split(";") if x] for k, v in have.items()}


def chart_songs(countries: set[str], days: int = 7) -> list[tuple[str, str, str, str]]:
    """(country name, kind, artist, title) of every song on the official national charts (data/national_charts.csv,
    the last 52 weeks) and on the archived Shazam country and city charts (last `days` days), for these countries."""
    import gzip
    from .. import origin
    from . import national_charts, shazam
    from ..config import RAW
    from ..countries import ISO2
    out = []
    for r in national_charts.load():
        c = origin.name_of(r["country"])
        if c in countries:
            out.append((c, "album" if r["chart"] in ("albums", "hiphop") else "track", r["artist"], r["title"]))
    slug = {k.lower().replace(" ", "-"): k for k in ISO2}
    base = RAW / "shazam"
    if base.exists():
        for day in sorted(p for p in base.iterdir() if p.is_dir())[-days:]:
            for p in day.glob("*.csv.gz"):
                place = p.name.split("-", 1)[1][:-7]
                c = next((v for k, v in slug.items() if place == k or place.startswith(k + "-")), "")
                if c in countries:
                    with gzip.open(p, "rt", encoding="utf-8-sig") as f:
                        out += [(c, "track", x["artist"], x["title"]) for x in shazam.parse(f.read())]
    return list(dict.fromkeys(out))


def chart_ids(countries: set[str]) -> tuple[dict[str, str], dict[str, str]]:
    """(Spotify ID -> how found, Apple Music artist ID -> how found) from our own local charts for these countries:
    the latest archived Spotify weekly top 200 per country (kworb's pages) and the Apple Music daily top 100 (last
    30 days)."""
    import glob
    import gzip
    from .. import origin
    from . import kworb_countries
    from .apple_charts import CSV as APPLE
    from ..config import RAW
    sp, ap = {}, {}
    weeks = sorted(glob.glob(str(RAW / "kworb" / "country" / "*")))
    if weeks:
        for p in glob.glob(weeks[-1] + "/*.html.gz"):
            cc = p.split("/")[-1].split(".")[0]
            if origin.name_of(cc) in countries:
                with gzip.open(p, "rt") as f:
                    for s in kworb_countries.parse(f.read())[1]:
                        sp.setdefault(s, f"Spotify weekly chart ({cc.upper()})")
    if APPLE.exists():
        with APPLE.open() as f:
            rows = list(csv.DictReader(f))
        days = sorted({r["date"] for r in rows})[-30:]
        for r in rows:
            if r["date"] in days and r.get("apple_artist_id") and origin.name_of(r["country"]) in countries:
                ap.setdefault(r["apple_artist_id"], f"Apple Music chart ({r['country'].upper()})")
    return sp, ap


# ---------- the steps
def discover(genre: str, skip_countries: set[str], workers: int = 6, wide: bool = True, views_budget: float = 1800) -> dict:
    """Find, read and decide the genre's smaller acts; rewrites that genre's rows in data/small_acts.csv and
    review/small_acts_review.csv. skip_countries: countries whose list is already full from kworb (no graph crawl,
    no Deezer reads there). wide (2026-10-27): also the Deezer related artists with no Wikidata item, Deezer's chart
    and editor playlists, the official national charts, our Spotify, Apple Music and Shazam charts, each identity looked
    up on Wikidata (Deezer P2722, Spotify P1902, Apple Music P2850) or MusicBrainz (url relations). Returns counts."""
    from .. import genre as genre_rule, origin
    from ..run import latest_listeners, load_artists
    from .deezer_genres import load as dz_load
    from .wikidata import COUNTRY_NAMES
    today = date.today()
    reg = load_artists()
    on_kworb = {r["spotify_id"] for r in latest_listeners()}
    known_dz = {str(a["deezer_id"]) for a in reg.values() if a.get("deezer_id")} | \
               {str(r["deezer_id"]) for r in dz_load().values() if r.get("deezer_id") and r.get("spotify_id") in on_kworb}
    items = wikidata_items(genre)
    for q, d in items.items():
        d["via"] = "wikidata"
        if not d["deezer_ids"] and (dz := _mb_deezer(d)):  # Wikidata has no Deezer ID; MusicBrainz links one
            d["deezer_ids"], d["via"] = {dz}, "wikidata; Deezer page from MusicBrainz"
    # Deezer's related artists of the seeds, kept when a Wikidata item carries the Deezer ID
    country_of = origin.wikidata_by_qid(sorted(items))
    seeds = {dz for q, d in items.items() if country_of.get(q, ("",))[0] not in skip_countries | {""}
             for dz in d["deezer_ids"]}
    seeds |= {str(a["deezer_id"]) for a in reg.values() if a["genre"] == genre and a.get("deezer_id")
              and a.get("deezer_match") in ("isrc", "titles", "links", "exact") and a.get("country")
              and a["country"] not in skip_countries}
    print(f"  {len(items)} Wikidata items; reading Deezer's related artists of {len(seeds)} seeds", flush=True)
    with ThreadPoolExecutor(workers) as pool:
        rel = {x for xs in pool.map(related, sorted(seeds)) for x in xs}
    _save_cache()
    have_dz = {dz for d in items.values() for dz in d["deezer_ids"]}
    fresh = sorted(rel - have_dz - known_dz)
    print(f"  {len(fresh)} related artists not yet known: looking for their Wikidata items", flush=True)
    found = items_by_deezer(fresh)
    linked_dz = {dz for d in found.values() for dz in d["deezer_ids"]}
    for q, d in found.items():
        if q not in items:
            items[q] = {**d, "via": "deezer related, Wikidata item"}
    country_of.update(origin.wikidata_by_qid(sorted(set(found) - set(country_of))))
    orphans = sorted(set(fresh) - linked_dz)
    stats = {}
    if wide:
        stats = _widen(genre, skip_countries, items, country_of, orphans, known_dz, on_kworb, reg)
    # who is left: not on kworb, not in the registry, with a country, from a country still short of 100
    todo = []
    for q, d in items.items():
        sps = sorted(d["spotify_ids"])
        if any(s in on_kworb or s in reg for s in sps) or (d["deezer_ids"] and d["deezer_ids"] <= known_dz):
            continue
        c, csrc = country_of.get(q, ("", ""))
        if not c and d.get("mb_country"):
            c, csrc = d["mb_country"]
        c = COUNTRY_NAMES.get(c, c)
        if not c or any(x.strip() in skip_countries for x in c.split(" / ")):
            continue
        todo.append((q, d, c, csrc))
    print(f"  {len(todo)} candidates; reading their Deezer pages", flush=True)
    reads: dict[str, dict] = {}
    all_dz = sorted({dz for _, d, _c, _s in todo for dz in d["deezer_ids"] if dz not in known_dz})
    with ThreadPoolExecutor(workers) as pool:
        for dz, r in zip(all_dz, pool.map(lambda x: deezer_read(x, today), all_dz)):
            reads[dz] = r
    _save_cache()
    wqs = [q for q, _d, _c, _s in todo if not q.startswith("mb:")]
    wd_genres = wikidata_genres(wqs)
    rappers = wikidata_rappers(wqs)
    links = sitelinks(wqs, {LANG[c] for _q, _d, c, _s in todo if c in LANG})
    rows, review = [], []
    hand = genre_rule.small_overrides()
    import re
    for q, d, c, csrc in todo:
        dzs = sorted((x for x in d["deezer_ids"] if reads.get(x)), key=lambda x: -int(reads[x].get("fans") or 0))
        dz = dzs[0] if dzs else ""
        rd = reads.get(dz, {})
        sp = sorted(d["spotify_ids"])
        mb_only = q.startswith("mb:")
        label = "" if re.fullmatch(r"Q\d+", d["name"] or "") else d["name"]  # no English label: Deezer's name
        row = {"genre": genre, "qid": "" if mb_only else q, "name": label or rd.get("name", "") or q, "country": c,
               "spotify_id": sp[0] if len(sp) == 1 else "", "deezer_id": dz, "found_via": d["via"],
               "youtube_channel": next(iter(d["youtube"])) if len(d["youtube"]) == 1 else "",
               "mbid": next(iter(d["mbid"])) if len(d["mbid"]) == 1 else "", "checked": today.isoformat(),
               "rapper": "yes" if q in rappers else "", "country_source": csrc,
               **{k: rd.get(k, "") for k in ("fans", "releases", "rap_share", "latin_share", "country_share", "latest",
                                             "rank_sum", "top_n", "fresh_n", "dated_n", "fresh_title", "lead_n",
                                             "top_dated", "top_latin")}}
        dzrow = {"match": "links", "releases": rd.get("releases") or 0, "rap_share": rd.get("rap_share", ""),
                 "latin_share": rd.get("latin_share", ""), "country_share": rd.get("country_share", ""),
                 "top_latin": rd.get("top_latin", ""), "top_dated": rd.get("top_dated", "")} if rd else None
        votes = [tuple(x) for x in d.get("mb_genres", [])]
        wdg = wd_genres.get(q, [])
        dec, basis = genre_rule.decide_small(votes, wdg, dzrow, country=c, rapper=q in rappers)
        if dec in ("other", "review"):
            cd = genre_rule.decide_country(votes, wdg, dzrow, wikidata=True, small=True)
            if cd:  # a hip-hop "review" with no sign of hip-hop at all does not hold back a country decision
                hh_doubt = dec == "review" and _evidence("hip_hop", wdg, votes, rd, q in rappers)
                dec, basis = cd if cd[0] == "review" or not hh_doubt else ("review", basis + "; " + cd[1])
        dec, basis = _hand(hand, genre, q, dec, basis)
        want ="hip_hop" if genre == "hip_hop" else "country"
        row["decision"] = "include" if dec == want else "review" if dec == "review" else "other"
        row["basis"] = basis + ("" if dz else "; no Deezer page linked")
        if row["decision"] == "review" and d.get("wide") and not _evidence(genre, wdg, votes, rd, q in rappers):
            row["decision"], row["basis"] = "other", row["basis"] + "; found through a chart or playlist, no genre evidence"
        if len(sp) > 1:
            row["decision"], row["basis"] = "review", row["basis"] + f"; Wikidata lists {len(sp)} Spotify IDs"
        issue = "genre unclear"
        n_top, n_lead = int(rd.get("top_n") or 0), int(rd.get("lead_n") or 0)
        if row["decision"] == "include" and n_top >= 4 and 2 * n_lead < n_top:  # the owner's features-led hold
            row["decision"], issue = "review", "features-led"
            row["basis"] += f"; held back: features-led ({n_lead} of the top {n_top} Deezer tracks as lead artist)"
        rows.append(row)
        if row["decision"] == "review":
            review.append({**row, "issue": issue})
    # Wikipedia and ListenBrainz for the included ones
    inc = [r for r in rows if r["decision"] == "include"]
    # Wikimedia throttles the pageviews API hard (429, Retry-After 7 s): an act read in the last 30 days keeps its
    # views, the rest are read one at a time within `views_budget` seconds; any left over have no Wikipedia signal
    # until the next run (counted in the result)
    prev = {r["qid"]: r for r in load() if r["genre"] == genre and r.get("qid") and r.get("wiki_lang")
            and r.get("checked", "") >= (today - timedelta(days=30)).isoformat()}
    t0, left = time.monotonic(), 0
    for i, r in enumerate(inc, 1):
        if r["qid"] in prev:
            r.update({k: prev[r["qid"]][k] for k in ("wiki_lang", "wiki_3m", "wiki_prev3m")})
        elif not links.get(r["qid"]):
            continue
        elif time.monotonic() - t0 < views_budget:
            r.update(wiki_signal(links.get(r["qid"], {}), r["country"], today))
        else:
            left += 1
        if i % 100 == 0:
            _save_cache()
    _save_cache()
    lb = lb_users([r["mbid"] for r in inc if r["mbid"]])
    for r in inc:
        r["lb_users"] = lb.get(r["mbid"], "")
    keep = [r for r in load() if r["genre"] != genre]
    _write(CSV, FIELDS, keep + sorted(rows, key=lambda r: (r["country"], r["name"].casefold())))
    old = [r for r in _read(REVIEW_CSV) if r.get("genre") != genre]
    # related artists with no Wikidata item are counted, not listed for review: nothing says where they are from
    _write(REVIEW_CSV, ["genre", "issue", "decision", "basis", "name", "country", "qid", "spotify_id", "deezer_id",
                        "found_via", "checked", "mbid"], old + review)
    return {"wikidata items": len(items), "seeds": len(seeds), "related read": len(rel), "related with item": len(found),
            **stats, "Wikipedia views left for the next run": left, "candidates": len(todo), "included": len(inc), "review": sum(r["decision"] == "review" for r in rows),
            "other": sum(r["decision"] == "other" for r in rows)}


def _hand(hand: dict, genre: str, q: str, dec: str, basis: str) -> tuple[str, str]:
    """A hand decision (registry/small_acts_overrides.csv, genre.small_overrides) replaces the rule's genre decision;
    the rule's own basis is kept beside it."""
    o = hand.get((genre, q))
    return (o["decision"], f"hand check {o['decided']}: {o['reason']} (rule: {dec}; {basis})") if o else (dec, basis)


def _evidence(genre: str, wdg: list, votes: list, rd: dict, rapper: bool) -> bool:
    """Any sign of the genre at all (for finds from charts and playlists, which say nothing about genre)."""
    from .. import genre as genre_rule
    if genre == "hip_hop":
        return rapper or any(h for _g, h, _l in wdg) or any(genre_rule.family(g) == "hip_hop" for g, _n in votes) \
            or float(rd.get("rap_share") or 0) >= 0.2
    return any(genre_rule.is_country(g[0]) for g in wdg) or any(genre_rule.is_country(g) for g, _n in votes) \
        or float(rd.get("country_share") or 0) >= 0.3


def _widen(genre, skip, items, country_of, orphans, known_dz, on_kworb, reg) -> dict:
    """Adds to `items` (and `country_of`) the acts found through the wider sources (discover's docstring). An item
    found on MusicBrainz alone is keyed "mb:<mbid>" and carries its MusicBrainz country and genre votes."""
    from .. import origin
    from ..countries import ISO2
    countries = {k for k in ISO2 if k not in ("Northern Ireland", "East Germany")} - skip
    have_dz = {dz for d in items.values() for dz in d["deezer_ids"]}
    have_sp = {sp for d in items.values() for sp in d["spotify_ids"]}
    dz_x = {o: "Deezer related artist" for o in orphans}
    pl = deezer_playlists(genre, countries)
    songs = chart_songs(countries)
    ids = identify([(k, a, t) for _c, k, a, t in songs])
    via_song = {}
    for c, k, a, t in songs:
        for x in ids.get((k, a, t), []):
            src = "national chart" if k == "album" or any(c == origin.name_of(cc) for cc in ("se", "dk", "fi")) else "chart"
            via_song.setdefault(x, f"{src} ({c})")
    for d, v in {**pl, **via_song}.items():
        dz_x.setdefault(d, v)
    dz_x = {d: v for d, v in dz_x.items() if d not in have_dz and d not in known_dz}
    sp_c, ap_c = chart_ids(countries)
    sp_x = {s: v for s, v in sp_c.items() if s not in on_kworb and s not in reg and s not in have_sp}
    print(f"  wider: {len(dz_x)} Deezer IDs ({len(orphans)} related, {len(pl)} from playlists, {len(via_song)} from "
          f"charted songs), {len(sp_x)} Spotify IDs, {len(ap_c)} Apple Music IDs: looking for Wikidata items", flush=True)
    new: dict[str, dict] = {}
    for prop, xs, field in (("P2722", dz_x, "deezer_ids"), ("P1902", sp_x, "spotify_ids"), ("P2850", ap_c, None)):
        got = items_by(prop, sorted(xs))
        for q, d in got.items():
            if q in items or q in new:
                continue
            via = next((xs[x] for x in (d[field] if field else []) if x in xs), None) or next(iter(xs.values()), "")
            if prop == "P2850":
                via = "Apple Music chart"
            new[q] = {**d, "via": f"{via}, Wikidata item", "wide": True}
    linked_dz = {x for d in new.values() for x in d["deezer_ids"]}
    linked_sp = {x for d in new.values() for x in d["spotify_ids"]}
    urls = {f"https://www.deezer.com/artist/{d}": v for d, v in dz_x.items() if d not in linked_dz}
    urls.update({f"https://open.spotify.com/artist/{s}": v for s, v in sp_x.items() if s not in linked_sp})
    print(f"  {len(new)} Wikidata items; {len(urls)} pages to look up on MusicBrainz", flush=True)
    hits = mb_by_urls(sorted(urls))
    # one artist links the page; an artist MusicBrainz already places in a full country is not looked up further
    one = {u: ms[0][0] for u, ms in hits.items() if len(ms) == 1 and origin.name_of(ms[0][1]) not in skip}
    arts = mb_artists(sorted(set(one.values())))
    via_mb = {}
    for u, m in one.items():
        via_mb.setdefault(m, (urls[u], u))
    to_qid = {}
    mb_only = 0
    for m, (via, u) in via_mb.items():
        a = arts.get(m)
        if not a:
            continue
        dz = {u.rsplit("/", 1)[-1]} if "deezer.com" in u else set(a["deezer"][:1] if len(a["deezer"]) == 1 else [])
        sp = {u.rsplit("/", 1)[-1]} if "spotify.com" in u else set(a["spotify"] if len(a["spotify"]) == 1 else [])
        if len(a["wikidata"]) == 1:
            to_qid[a["wikidata"][0]] = (m, via, dz, sp)
            continue
        c = mb_country(a)
        if not c[0]:
            continue
        mb_only += 1
        new["mb:" + m] = {"name": a["name"], "spotify_ids": sp, "deezer_ids": dz, "youtube": set(), "mbid": {m},
                          "via": f"{via}, MusicBrainz", "wide": True, "mb_country": c,
                          "mb_genres": [tuple(g) for g in a["genres"]]}
    for q, d in items_by_qid(sorted(set(to_qid) - set(items) - set(new))).items():
        m, via, dz, sp = to_qid[q]
        d["deezer_ids"] |= dz if not d["deezer_ids"] else set()
        d["spotify_ids"] |= sp if not d["spotify_ids"] else set()
        d["mbid"] = d["mbid"] or {m}
        c = mb_country(arts[m])
        new[q] = {**d, "via": f"{via}, MusicBrainz, Wikidata item", "wide": True, "mb_country": c if c[0] else None,
                  "mb_genres": [tuple(g) for g in arts[m]["genres"]]}
    country_of.update(origin.wikidata_by_qid(sorted(q for q in new if not q.startswith("mb:") and q not in country_of)))
    items.update(new)
    return {"wider Deezer IDs": len(dz_x), "wider Spotify IDs": len(sp_x), "wider Apple IDs": len(ap_c),
            "wider Wikidata items": sum(1 for q in new if not q.startswith("mb:")), "MusicBrainz only": mb_only,
            "MusicBrainz pages looked up": len(urls), "MusicBrainz links found": sum(1 for v in hits.values() if v),
            "no country source": sum(1 for v in hits.values() if not v)}


def calibrate(genre: str, workers: int = 6) -> int:
    """The same signals for the registry's artists of the genre with kworb listener counts and a confirmed Deezer
    page: Deezer top-10 rank sum, English + home-language Wikipedia views, ListenBrainz listeners. Fans come from the
    registry's Deezer match."""
    from ..run import latest_listeners, load_artists
    from .deezer import CONFIRMED
    today = date.today()
    ml = {r["spotify_id"]: r["monthly_listeners"] for r in latest_listeners()}
    reg = [a for a in load_artists().values() if a["genre"] == genre and ml.get(a["spotify_id"]) and a.get("country")]
    print(f"  calibration: {len(reg)} artists", flush=True)
    with ThreadPoolExecutor(workers) as pool:
        tops = dict(zip([a["spotify_id"] for a in reg], pool.map(
            lambda a: _json(f"artist/{a['deezer_id']}/top", limit=10).get("data", [])
            if a.get("deezer_id") and a.get("deezer_match") in CONFIRMED else None, reg)))
    _save_cache()
    home = lambda a: a["country"].split(" / ")[0]
    links = sitelinks([a["wikidata_id"] for a in reg if a.get("wikidata_id")], {LANG[home(a)] for a in reg if home(a) in LANG})
    from . import wikipedia
    en = wikipedia.load()  # English views are stored for listed artists (depth-views): only the home language is asked
    known = lambda a: {"en": last6(en[a["spotify_id"]], today)} if a["spotify_id"] in en else {}
    print(f"  Wikipedia: {sum(1 for a in reg if LANG.get(home(a), 'en') in links.get(a.get('wikidata_id'), {}) and LANG.get(home(a)) != 'en')} home-language articles to read", flush=True)
    wiki = {}
    for i, a in enumerate(reg, 1):  # one at a time: Wikimedia throttles this API (429, Retry-After 7 s)
        wiki[a["spotify_id"]] = wiki_signal(links.get(a.get("wikidata_id"), {}), home(a), today, known(a))
        if i % 200 == 0:
            _save_cache()
            print(f"  Wikipedia: {i} of {len(reg)}", flush=True)
    _save_cache()
    lb = lb_users([a["musicbrainz_id"] for a in reg if a.get("musicbrainz_id")])
    rows = []
    for a in reg:
        t = tops.get(a["spotify_id"])
        rows.append({"genre": genre, "spotify_id": a["spotify_id"], "name": a["name"], "country": a["country"],
                     "ml": ml[a["spotify_id"]], "deezer_id": a.get("deezer_id", "") if t is not None else "",
                     "fans": a.get("deezer_fans", "") if t is not None else "",
                     "rank_sum": sum(int(x.get("rank") or 0) for x in t) if t else "", "top_n": len(t) if t else "",
                     **wiki.get(a["spotify_id"], {}), "lb_users": lb.get(a.get("musicbrainz_id"), ""),
                     "checked": today.isoformat()})
    keep = [r for r in load_calibration() if r["genre"] != genre]
    _write(CAL, CAL_FIELDS, keep + rows)
    return len(rows)


def fans_snapshot(today: date | None = None, workers: int = 6) -> int:
    """Weekly: Deezer fans of every smaller act (artist/{id}), appended to data/deezer_fans_history.csv, so fan growth
    becomes a signal once two snapshots a week or more apart exist. A day already stored is skipped."""
    today = (today or date.today()).isoformat()
    have = {(r["date"], r["deezer_id"]) for r in _read(FANS)}
    ids = sorted({r["deezer_id"] for r in load() if r.get("deezer_id") and r["decision"] == "include"})
    ids = [d for d in ids if (today, d) not in have]
    with ThreadPoolExecutor(workers) as pool:
        got = list(zip(ids, pool.map(lambda d: _json(f"artist/{d}").get("nb_fan"), ids)))
    new = not FANS.exists()
    with FANS.open("a", newline="") as f:
        w = csv.DictWriter(f, ["date", "deezer_id", "fans"])
        if new:
            w.writeheader()
        w.writerows({"date": today, "deezer_id": d, "fans": n} for d, n in got if n is not None)
    return sum(1 for _, n in got if n is not None)


def fan_growth(min_days: int = 7) -> dict[str, float]:
    """deezer_id -> fan growth (newest / oldest snapshot - 1) when the snapshots span `min_days`+ days."""
    by: dict[str, list] = {}
    for r in _read(FANS):
        by.setdefault(r["deezer_id"], []).append((r["date"], int(r["fans"] or 0)))
    out = {}
    for d, v in by.items():
        v.sort()
        if (date.fromisoformat(v[-1][0]) - date.fromisoformat(v[0][0])).days >= min_days and v[0][1] > 0:
            out[d] = v[-1][1] / v[0][1] - 1
    return out
