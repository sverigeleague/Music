"""Who owns a label we cannot place: MusicBrainz label relationships (CC0 data; one request a second).

For each label name: the MusicBrainz label with exactly that name (skipped when two labels share it), then its owners
and parents ("label ownership" and "imprint", looking backward) up to DEPTH levels, and its distributors ("label
distribution"). The first ancestor whose name registry/label_owners.csv places decides. A label with no placed
ancestor stays unknown: a missing parent on MusicBrainz is not proof of independence.
Cached in data/musicbrainz_labels.json (name -> result), so each name is looked up once.
"""
import json
import re

from ..config import DATA
from ..http import get

API = "https://musicbrainz.org/ws/2"
CACHE = DATA / "musicbrainz_labels.json"
DEPTH = 4
OWNER_TYPES = ("label ownership", "imprint")


def _load() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.casefold())


def parts(label: str) -> list[str]:
    """'A / B / C', 'X, under exclusive license to Y', 'Imperia, by Yellowcake' -> the names worth looking up."""
    text = re.sub(r"\b(llc|inc|ltd|gmbh|s\.?a\.?s?|bv)\b\.?", "", label, flags=re.I)
    out = [p.strip(" ,.") for p in re.split(r"\s*/\s*|,\s*(?:under (?:exclusive )?licen[cs]e to|by|distributed by)\s+|\s+x\s+", text)]
    return [p for p in out if len(p) >= 2]


def find(name: str) -> str | None:
    r = get(f"{API}/label", params={"query": f'label:"{name}"', "fmt": "json", "limit": 5})
    if r.status_code != 200:
        return None
    exact = [l for l in r.json().get("labels", []) if norm(l["name"]) == norm(name)]
    return exact[0]["id"] if len(exact) == 1 else None


def relations(mbid: str) -> tuple[str, list[dict]]:
    r = get(f"{API}/label/{mbid}", params={"inc": "label-rels", "fmt": "json"})
    if r.status_code != 200:
        return "", []
    d = r.json()
    return d.get("name", ""), d.get("relations", [])


def ancestors(mbid: str) -> tuple[list[str], list[str]]:
    """(owner/parent names nearest first, distributor names)."""
    seen, chain, distributors = {mbid}, [], []
    frontier = [mbid]
    for _ in range(DEPTH):
        nxt = []
        for m in frontier:
            _name, rels = relations(m)
            for x in rels:
                if x.get("direction") != "backward":
                    continue
                lab = x.get("label") or {}
                if x["type"] in OWNER_TYPES and lab.get("id") not in seen:
                    seen.add(lab["id"])
                    chain.append(lab["name"])
                    nxt.append(lab["id"])
                elif x["type"] == "label distribution" and frontier == [mbid]:
                    distributors.append(lab.get("name", ""))
        frontier = nxt
        if not frontier:
            break
    return chain, distributors


def update(names: list[str]) -> int:
    """Look up the names not yet cached. Saves after each name."""
    cache = _load()
    n = 0
    for label in names:
        if label in cache:
            continue
        res = {"looked_up": [], "chain": [], "distributors": []}
        for p in parts(label):
            mbid = find(p)
            if mbid:
                chain, dist = ancestors(mbid)
                res = {"looked_up": [p], "mbid": mbid, "chain": chain, "distributors": dist}
                break
        cache[label] = res
        n += 1
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    return n


def load() -> dict:
    return _load()
