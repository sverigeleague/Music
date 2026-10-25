"""Wikidata (CC0): the hip-hop candidate list, platform IDs, record labels and their major-label parent, photos.

One batched SPARQL query per property group per run; Wikimedia rate-limits busy clients.
"""
import csv
import io

from ..http import get

SPARQL = "https://query.wikidata.org/sparql"
HIP_HOP = "Q11401"
# Latin trap, reggaeton, Latin hip-hop: kept apart until the owner decides (DECISIONS.md, question 2).
LATIN = ("Q54329757", "Q202930", "Q3827483")  # looked up on Wikidata 2026-10-23
# Majors by Wikidata ID, matched along record label -> parent organisation / owned by.
MAJORS = {"Q38903": "Universal Music Group", "Q21077": "Warner Music Group",
          "Q11315210": "Sony Music", "Q330629": "Sony Music", "Q56760250": "Sony Music"}


def query(q: str) -> list[dict]:
    r = get(SPARQL, data={"query": q}, headers={"Accept": "text/csv"}, timeout=180)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


qid = lambda uri: uri.rsplit("/", 1)[-1] if uri else ""


def hip_hop_spotify_ids() -> dict[str, dict]:
    """Every item with a Spotify artist ID and at least one genre under hip-hop (P136 / P279*)."""
    rows = query(f"""
SELECT ?sp ?item WHERE {{ ?item wdt:P1902 ?sp ; wdt:P136 ?g . ?g wdt:P279* wd:{HIP_HOP} . }}""")
    return {r["sp"]: {"qid": qid(r["item"])} for r in rows}


COUNTRY = "Q83440"  # country music


def country_spotify_ids() -> dict[str, dict]:
    """Every item with a Spotify artist ID and at least one genre under country music (P136 / P279*)."""
    rows = query(f"""
SELECT ?sp ?item WHERE {{ ?item wdt:P1902 ?sp ; wdt:P136 ?g . ?g wdt:P279* wd:{COUNTRY} . }}""")
    return {r["sp"]: {"qid": qid(r["item"])} for r in rows}


def _values(spotify_ids) -> str:
    return " ".join(f'"{s}"' for s in spotify_ids)


def details(spotify_ids: list[str]) -> dict[str, dict]:
    """Per Spotify ID: QID, genres (with hip-hop/Latin flags), IDs on other platforms, labels, photo, country."""
    out: dict[str, dict] = {}
    for chunk in [spotify_ids[i:i + 300] for i in range(0, len(spotify_ids), 300)]:
        v = _values(chunk)
        for r in query(f"""
SELECT ?sp ?item ?g ?gLabel ?hh ?latin WHERE {{
  VALUES ?sp {{ {v} }} ?item wdt:P1902 ?sp . OPTIONAL {{ ?item wdt:P136 ?g .
  BIND(EXISTS {{ ?g wdt:P279* wd:{HIP_HOP} }} AS ?hh)
  BIND(EXISTS {{ VALUES ?l {{ {' '.join('wd:' + x for x in LATIN)} }} ?g wdt:P279* ?l }} AS ?latin) }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""):
            d = out.setdefault(r["sp"], {"qid": qid(r["item"]), "genres": [], "labels": [], "majors": set()})
            if r.get("g"):
                d["genres"].append((r["gLabel"], r["hh"] == "true", r["latin"] == "true"))
        for r in query(f"""
SELECT ?sp ?mbid ?yt ?ig ?tt ?x ?img ?country ?countryLabel ?born ?start WHERE {{
  VALUES ?sp {{ {v} }} ?item wdt:P1902 ?sp .
  OPTIONAL {{ ?item wdt:P434 ?mbid }} OPTIONAL {{ ?item wdt:P2397 ?yt }} OPTIONAL {{ ?item wdt:P2003 ?ig }}
  OPTIONAL {{ ?item wdt:P7085 ?tt }} OPTIONAL {{ ?item wdt:P2002 ?x }} OPTIONAL {{ ?item wdt:P18 ?img }}
  OPTIONAL {{ ?item wdt:P27|wdt:P495 ?country }} OPTIONAL {{ ?item wdt:P569 ?born }}
  OPTIONAL {{ ?item wdt:P2031|wdt:P571 ?start }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""):
            d = out.get(r["sp"])
            if not d:
                continue
            for k, src in (("musicbrainz_id", "mbid"), ("youtube_channel", "yt"), ("instagram", "ig"),
                           ("tiktok", "tt"), ("x", "x"), ("image", "img"), ("country", "countryLabel"),
                           ("born", "born"), ("active_since", "start")):
                if r.get(src) and not d.get(k):
                    d[k] = r[src][:10] if k in ("born", "active_since") else r[src]
        for r in query(f"""
SELECT ?sp ?lab ?labLabel ?major WHERE {{
  VALUES ?sp {{ {v} }} ?item wdt:P1902 ?sp ; wdt:P264 ?lab .
  OPTIONAL {{ VALUES ?major {{ {' '.join('wd:' + x for x in MAJORS)} }} ?lab (wdt:P749|wdt:P127)* ?major . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""):
            d = out.get(r["sp"])
            if not d:
                continue
            if r["labLabel"] not in d["labels"]:
                d["labels"].append(r["labLabel"])
            if r.get("major"):
                d["majors"].add(MAJORS[qid(r["major"])])
    return out


def images(qids: list[str]) -> dict[str, str]:
    """QID -> its image (P18, a Wikimedia Commons file URL)."""
    out: dict[str, str] = {}
    for chunk in [qids[i:i + 300] for i in range(0, len(qids), 300)]:
        for r in query(f"""SELECT ?item ?img WHERE {{ VALUES ?item {{ {' '.join('wd:' + q for q in chunk)} }} ?item wdt:P18 ?img . }}"""):
            out.setdefault(qid(r["item"]), r["img"])
    return out
