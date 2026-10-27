"""Smaller acts: hip-hop and country artists below kworb's 500k-listener floor, for Scout's country view (owner,
2026-10-26: "look into deezer fans for smaller countries"; "triangulate with other sources").

Who (each identity looked up at the source, never by name):
  wikidata  items with a hip-hop genre (P136 under Q11401) or the occupation rapper (P106 Q2252262), or a country
            genre (Q83440), that carry a Spotify ID (P1902) or a Deezer ID (P2722)
  related   Deezer's related artists of those and of the registry's artists from the same countries, kept only when
            a Wikidata item carries that Deezer ID (the item gives the country and, where it has one, the Spotify ID).
            A related artist with no Wikidata item has no country source: counted, never listed.
Country: Wikidata P27/P495 by QID (src/origin.py's rule). Left out: anyone on kworb's listener pages or already in the
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
          "fresh_n", "dated_n", "fresh_title", "wiki_lang", "wiki_3m", "wiki_prev3m", "lb_users", "checked"]
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
    return {"name": a.get("name", ""), "fans": a.get("nb_fan", 0), "releases": len(g), "rap_share": share(RAP),
            "latin_share": share(LATIN), "country_share": share(COUNTRY),
            "latest": max((x.get("release_date", "") for x in al), default=""),
            "rank_sum": sum(int(t.get("rank") or 0) for t in top), "top_n": len(top),
            "fresh_n": len(fresh), "dated_n": sum(1 for _, d in days if d),
            "fresh_title": fresh[0].get("title", "") if fresh else ""}


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
    if not mbids:
        return {}
    pop = listenbrainz.popularity(sorted(set(mbids)), date.today().strftime("%Y-%m"))
    return {m: v[0] for m, v in pop.items() if v}


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


# ---------- the steps
def discover(genre: str, skip_countries: set[str], workers: int = 6) -> dict:
    """Find, read and decide the genre's smaller acts; rewrites that genre's rows in data/small_acts.csv and
    review/small_acts_review.csv. skip_countries: countries whose list is already full from kworb (no graph crawl,
    no Deezer reads there). Returns counts for the log."""
    from .. import genre as genre_rule, origin
    from ..run import latest_listeners, load_artists
    from .deezer_genres import load as dz_load
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
    # who is left: not on kworb, not in the registry, with a country, from a country still short of 100
    todo = []
    for q, d in items.items():
        sps = sorted(d["spotify_ids"])
        if any(s in on_kworb or s in reg for s in sps) or (d["deezer_ids"] and d["deezer_ids"] <= known_dz):
            continue
        c = country_of.get(q, ("", ""))[0]
        if not c or any(x.strip() in skip_countries for x in c.split(" / ")):
            continue
        todo.append((q, d, c))
    print(f"  {len(todo)} candidates; reading their Deezer pages", flush=True)
    reads: dict[str, dict] = {}
    all_dz = sorted({dz for _, d, _c in todo for dz in d["deezer_ids"] if dz not in known_dz})
    with ThreadPoolExecutor(workers) as pool:
        for dz, r in zip(all_dz, pool.map(lambda x: deezer_read(x, today), all_dz)):
            reads[dz] = r
    _save_cache()
    wd_genres = wikidata_genres([q for q, _d, _c in todo])
    links = sitelinks([q for q, _d, _c in todo], {LANG[c] for _q, _d, c in todo if c in LANG})
    rows, review = [], []
    for q, d, c in todo:
        dzs = sorted((x for x in d["deezer_ids"] if reads.get(x)), key=lambda x: -int(reads[x].get("fans") or 0))
        dz = dzs[0] if dzs else ""
        rd = reads.get(dz, {})
        sp = sorted(d["spotify_ids"])
        import re
        label = "" if re.fullmatch(r"Q\d+", d["name"] or "") else d["name"]  # no English label: Deezer's name
        row = {"genre": genre, "qid": q, "name": label or rd.get("name", "") or q, "country": c,
               "spotify_id": sp[0] if len(sp) == 1 else "", "deezer_id": dz, "found_via": d["via"],
               "youtube_channel": next(iter(d["youtube"])) if len(d["youtube"]) == 1 else "",
               "mbid": next(iter(d["mbid"])) if len(d["mbid"]) == 1 else "", "checked": today.isoformat(),
               **{k: rd.get(k, "") for k in ("fans", "releases", "rap_share", "latin_share", "country_share", "latest",
                                             "rank_sum", "top_n", "fresh_n", "dated_n", "fresh_title")}}
        dzrow = {"match": "links", "releases": rd.get("releases") or 0, "rap_share": rd.get("rap_share", ""),
                 "latin_share": rd.get("latin_share", ""), "country_share": rd.get("country_share", "")} if rd else None
        dec, basis = genre_rule.decide([], wd_genres.get(q, []), dzrow, wikidata=True, country=c)
        if dec in ("other", "review"):
            cd = genre_rule.decide_country([], wd_genres.get(q, []), dzrow, wikidata=True)
            if cd:
                dec, basis = cd if cd[0] == "review" or dec != "review" else ("review", basis + "; " + cd[1])
        want = "hip_hop" if genre == "hip_hop" else "country"
        row["decision"] = "include" if dec == want else "review" if dec == "review" else "other"
        row["basis"] = basis + ("" if dz else "; no Deezer page on Wikidata")
        if len(sp) > 1:
            row["decision"], row["basis"] = "review", row["basis"] + f"; Wikidata lists {len(sp)} Spotify IDs"
        rows.append(row)
        if row["decision"] == "review":
            review.append({**row, "issue": "genre unclear"})
    # Wikipedia and ListenBrainz for the included ones
    inc = [r for r in rows if r["decision"] == "include"]
    for r in inc:
        r.update(wiki_signal(links.get(r["qid"], {}), r["country"], today))
    lb = lb_users([r["mbid"] for r in inc if r["mbid"]])
    for r in inc:
        r["lb_users"] = lb.get(r["mbid"], "")
    # related artists with no Wikidata item: no country source, so review only (counted)
    orphans = sorted(set(fresh) - linked_dz)
    keep = [r for r in load() if r["genre"] != genre]
    _write(CSV, FIELDS, keep + sorted(rows, key=lambda r: (r["country"], r["name"].casefold())))
    old = [r for r in _read(REVIEW_CSV) if r.get("genre") != genre]
    # related artists with no Wikidata item are counted, not listed for review: nothing says where they are from
    _write(REVIEW_CSV, ["genre", "issue", "decision", "basis", "name", "country", "qid", "spotify_id", "deezer_id",
                        "found_via", "checked"], old + review)
    return {"wikidata items": len(items), "seeds": len(seeds), "related read": len(rel), "related with item": len(found),
            "candidates": len(todo), "included": len(inc), "review": sum(r["decision"] == "review" for r in rows),
            "other": sum(r["decision"] == "other" for r in rows), "no country source": len(orphans)}


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
