"""Who owns a label we cannot place: the parent-label chain in Discogs' monthly labels dump (CC0, data.discogs.com).

The dump (~90 MB gz, every label on Discogs) is read once, offline, from a local copy: label id, name, parentLabel.
For a label string on a release: its parts (as in musicbrainz_labels.parts), then the Discogs labels whose name
normalises to the same key (Discogs' "(2)" suffixes and company suffixes dropped; if none, also "Records", "Music" ...
dropped), then label -> parentLabel -> ... up to the top. The nearest link that registry/label_owners.csv or the
built-in map below places decides. Several Discogs labels with the same key whose chains end at different owners
(or one placed and one with an unplaced parent) make the name ambiguous: not mapped; a same-named label with no
parent at all says nothing and is ignored. Discogs keeps one parent per label, which is sometimes
a past owner; a label with no parent is not proof of independence.

Only the names we need are saved, to data/discogs_label_parents.csv (label_name, discogs_id, parent_chain, owner,
status, match), so the dump stays out of the repository. Images and marketplace data are not used.
"""
import csv
import gzip
import re
import unicodedata
import xml.etree.ElementTree as ET

from .. import labels
from ..config import DATA
from .musicbrainz_labels import parts

LIST = "https://data.discogs.com/?prefix=data/{year}/"
DOWNLOAD = "https://data.discogs.com/?download=data%2F{year}%2Fdiscogs_{date}_labels.xml.gz"
CSV = DATA / "discogs_label_parents.csv"
FIELDS = ["label_name", "discogs_id", "parent_chain", "owner", "status", "match"]
URL = "https://www.discogs.com/label/{id}"
DEPTH = 10

# Majors' sub-companies and big distributors as Discogs names them, for chain links the registry does not place.
# Keys are normalised names (see key()).
BUILTIN = {
    **{k: ("Universal Music Group", "major") for k in (
        "universalmusicgroup", "universalmusicgroupinternational", "universalmusic", "umg", "umgrecordings",
        "republic", "interscope", "interscopegeffenam", "defjam", "defjamrecordings", "islanddefjammusicgroup",
        "capitol", "capitolmusicgroup", "motown", "island", "polydor", "geffen", "mercury", "emi", "decca",
        "verve", "universalmusicenterprises", "10kprojects", "umgnashville")},
    **{k: ("Sony Music", "major") for k in (
        "sonymusic", "sonymusicentertainment", "sonymusicentertainmentinc", "sonybmgmusicentertainment",
        "sonymusicgroup", "columbia", "rca", "rcarecordsla", "epic", "arista", "legacy", "sonymusiclatin",
        "sonymusicnashville")},
    **{k: ("Warner Music Group", "major") for k in (
        "warnermusicgroup", "warnermusic", "warnerrecords", "warnerbrosrecords", "atlantic",
        "atlanticrecordinggroup", "elektra", "parlophone", "300", "300entertainment", "asylum", "rhino",
        "warnermusiclatina", "warnermusicnashville")},
    "virginmusicgroup": ("Universal Music Group", "major_distributed"),
    "virginmusic": ("Universal Music Group", "major_distributed"),
    "ingrooves": ("Universal Music Group", "major_distributed"),
    "caroline": ("Universal Music Group", "major_distributed"),
    "theorchard": ("Sony Music", "major_distributed"),
    "orchard": ("Sony Music", "major_distributed"),
    "awal": ("Sony Music", "major_distributed"),
    "ada": ("Warner Music Group", "major_distributed"),
    "alternativedistributionalliance": ("Warner Music Group", "major_distributed"),
    **{k: (o, "independent") for k, o in (
        ("empire", "EMPIRE"), ("empiredistribution", "EMPIRE"), ("believe", "Believe"),
        ("believedigital", "Believe"), ("bmg", "BMG"), ("bmgrightsmanagement", "BMG"), ("stem", "Stem"),
        ("onerpm", "ONErpm"), ("gamma", "gamma."), ("concord", "Concord"), ("concordmusicgroup", "Concord"),
        ("secretlygroup", "Secretly Group"), ("beggarsgroup", "Beggars Group"))},
}
GENERIC = {"independent", "independiente", "selfreleased", "none", "unknown", "records", "music", "entertainment",
           "notonlabel", "various", "label"}

_PUBLISHING = re.compile(r"publishing|\bedition|verlag", re.I)
_NUMBERED = re.compile(r"\s\(\d+\)$")
_CORP = re.compile(r",?\s*\b(llc|inc|ltd|gmbh|corp|co|l\.l\.c|s\.?a\.?s?|bv|limited)\b\.?", re.I)
_GENERIC_WORDS = re.compile(r"\b(the|records?|recordings?|music|musik|entertainment|ent|group|label|media)\b", re.I)


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()


def key(name: str) -> str:
    """'Planet E (4)' / 'Planet E, Inc.' -> 'planete'."""
    s = re.sub(r"\s*\(\d+\)$", "", name)
    return re.sub(r"[^a-z0-9]", "", _ascii(_CORP.sub("", s)))


def loose_key(name: str) -> str:
    """key() without the words every label name shares ('SODMG Records' -> 'sodmg')."""
    s = _CORP.sub("", re.sub(r"\s*\(\d+\)$", "", name))
    return re.sub(r"[^a-z0-9]", "", _ascii(_GENERIC_WORDS.sub("", s)))


def build_index(dump_path) -> dict:
    """{"by_id": id -> {"name", "parent"}, "by_key": key -> [ids], "by_loose": loose key -> [ids]} from the dump."""
    by_id, by_key, by_loose = {}, {}, {}
    opener = gzip.open if str(dump_path).endswith(".gz") else open
    with opener(dump_path, "rb") as f:
        depth = 0
        for ev, el in ET.iterparse(f, events=("start", "end")):
            if ev == "start":
                depth += el.tag == "label"
                continue
            if el.tag != "label":
                continue
            depth -= 1
            if depth:  # a <label> inside <sublabels>
                continue
            lid, name = el.findtext("id"), (el.findtext("name") or "").strip()
            p = el.find("parentLabel")
            parent = p.get("id") if p is not None else None
            el.clear()
            if not name:  # placeholders ("DO NOT USE", id 212) that thousands of labels point to: no parent
                continue
            by_id[lid] = {"name": name, "parent": parent}
            by_key.setdefault(key(name), []).append(lid)
            by_loose.setdefault(loose_key(name), []).append(lid)
    global _INDEX
    _INDEX = {"by_id": by_id, "by_key": by_key, "by_loose": by_loose}
    return _INDEX


_INDEX: dict | None = None


def _chain_ids(lid: str, index: dict) -> list[str]:
    out = [lid]
    while len(out) < DEPTH:
        p = index["by_id"].get(out[-1], {}).get("parent")
        if not p or p in out or p not in index["by_id"]:
            break
        out.append(p)
    return out


def _candidates(name: str, index: dict) -> tuple[list[str], str]:
    ids = index["by_key"].get(key(name), [])
    if ids:
        return ids, "exact"
    lk = loose_key(name)
    return (index["by_loose"].get(lk, []), "loose") if len(lk) >= 3 else ([], "")


def chain(name: str, index: dict | None = None, table: list[dict] | None = None) -> list[str]:
    """Label -> parent -> ... -> top (up to a publisher), as Discogs names them; [] when not found or ambiguous."""
    return lookup(name, index, table)["chain"]


def place(name: str, table: list[dict]) -> tuple[str, str]:
    """(owner, status) of one Discogs label name: our registry's patterns first, then the built-in map."""
    st, owner = labels.classify_label(name, "", table, use_musicbrainz=False)
    if st != "unknown":  # with no artist name, self_released only comes from a registry pattern (DistroKid ...)
        return owner, st
    return BUILTIN.get(key(name), ("", "unknown"))


def _resolve(lid: str, index: dict, table: list[dict]) -> tuple[str, str, list[str]]:
    names = [index["by_id"][i]["name"] for i in _chain_ids(lid, index)]
    pub = next((n for n, x in enumerate(names) if _PUBLISHING.search(x)), None)
    names = names[:max(pub, 1)] if pub is not None else names  # a publisher owns songs, not recordings: the chain stops there
    for n in names[1:] + names[:1]:  # the parents decide; the label's own name only when none is placed
        owner, st = place(n, table)
        if st != "unknown":
            return owner, st, names
    return "", "unknown", names


def lookup(name: str, index: dict | None = None, table: list[dict] | None = None) -> dict:
    """{owner, status, chain, discogs_id, match} for one label name (one part, not 'A / B'). status 'ambiguous' when
    the Discogs labels with that name end at different owners."""
    index, table = index or _INDEX, table if table is not None else labels.owners()
    ids, match = _candidates(name, index)
    if not ids:
        return {"owner": "", "status": "not_found", "chain": [], "discogs_id": "", "match": "", "namesakes": 0}
    res = [(i, *_resolve(i, index, table)) for i in ids]
    # a same-named label with no parent says nothing about owners; parented ones must agree
    told = [r for r in res if len(r[3]) > 1 or r[2] != "unknown"] or res
    if len({(o, s) for _i, o, s, _c in told}) > 1:
        return {"owner": "", "status": "ambiguous", "chain": [], "discogs_id": "|".join(r[0] for r in told[:10]),
                "match": match, "namesakes": len(ids)}
    lid, owner, st, ch = min(told, key=lambda r: int(r[0]))  # the oldest such label as evidence
    # Discogs numbers distinct labels that share a name ("Urban (2)"): the name alone may be another label
    namesakes = len({index["by_id"][i]["name"] for i in ids if _NUMBERED.search(index["by_id"][i]["name"])})
    if len(ch) == 1 and key(ch[0]) in BUILTIN:
        namesakes = 0  # the string names a major or distributor itself ("Believe")
    return {"owner": owner, "status": st, "chain": ch, "discogs_id": lid, "match": match, "namesakes": namesakes}


def owner_of(name: str, index: dict | None = None, table: list[dict] | None = None) -> tuple[str, str, list[str]]:
    """(owner, status, chain) of a release's label string: the first part ('A / B', 'X under license to Y') that
    Discogs places. Without an index in memory, read from data/discogs_label_parents.csv."""
    if index is None and _INDEX is None:
        r = load().get(name)
        if not r or r["status"] in ("unknown", "ambiguous", "not_found"):
            return "", (r or {}).get("status", "not_found"), []
        return r["owner"], r["status"], r["parent_chain"].split(" > ")
    first = None
    for p in parts(name) or [name]:
        res = lookup(p, index, table)
        if res["status"] not in ("unknown", "ambiguous", "not_found"):
            return res["owner"], res["status"], res["chain"]
        first = first or res
    return "", (first or {}).get("status", "not_found"), (first or {}).get("chain", [])


def rows_for(names, index: dict | None = None, table: list[dict] | None = None) -> list[dict]:
    """One saved row per label string: the first part Discogs places, else the first part's result."""
    index, table = index or _INDEX, table if table is not None else labels.owners()
    out = []
    for name in sorted(set(names)):
        best = None
        for p in parts(name) or [name]:
            res = lookup(p, index, table)
            if best is None or (best["status"] in ("unknown", "ambiguous", "not_found")
                                and res["status"] not in ("unknown", "ambiguous", "not_found")):
                best = res
        out.append({"label_name": name, "discogs_id": best["discogs_id"], "parent_chain": " > ".join(best["chain"]),
                    "owner": best["owner"], "status": best["status"], "match": best["match"]})
    return out


def save(rows: list[dict]) -> None:
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["label_name"]: r for r in csv.DictReader(f)}


def low_confidence(label: str, artist: str, match: str = "", namesakes: int = 0) -> str:
    """Why a placement is shaky, or '' (generic one-word names, the artist's own name, a loose name match, other
    Discogs labels with the same name)."""
    k = key(label)
    if k in GENERIC or loose_key(label) in GENERIC:
        return "generic name"
    if labels._norm(artist) and labels._norm(artist) in labels._norm(label):
        return "artist's own name"
    if len(label.split()) == 1 and len(k) <= 4:
        return "short one-word name"
    if match == "loose":
        return "loose name match"
    if namesakes:
        return f"{namesakes} other Discogs labels share the name"
    return ""


def place_artist(releases: list[dict], artist: str, table: list[dict] | None = None,
                 index: dict | None = None) -> dict:
    """labels.artist_status with Discogs as a further source for release labels it leaves unknown: the status most
    placed releases share, with the deciding release's Discogs chain as evidence."""
    table = table if table is not None else labels.owners()
    seen = []
    for r in releases:
        st, owner = labels.classify_label(r["label"], artist, table)
        ev = {}
        if st == "unknown":
            res = None
            for p in parts(r["label"]) or [r["label"]]:
                res = lookup(p, index, table) if (index or _INDEX) else None
                if res and res["status"] not in ("unknown", "ambiguous", "not_found"):
                    break
            if res and res["status"] not in ("unknown", "ambiguous", "not_found"):
                st, owner = res["status"], res["owner"]
                ev = {"chain": res["chain"], "discogs_id": res["discogs_id"], "match": res["match"],
                      "low": low_confidence(p, artist, res["match"], res["namesakes"])}
        seen.append({"label": r["label"], "date": r["release_date"], "status": st, "owner": owner, **ev})
    known = [x for x in seen if x["status"] != "unknown"]
    if not known or not any("chain" in x for x in known):
        return {"status": "unknown", "owner": "", "basis": None, "releases": seen}
    count = {}
    for x in known:
        count[x["status"]] = count.get(x["status"], 0) + 1
    status = max(count, key=lambda k: (count[k], -labels.RANK[k]))
    owners_ = [x["owner"] for x in known if x["status"] == status]
    owner = max(dict.fromkeys(owners_), key=owners_.count)
    basis = next((x for x in known if x["status"] == status and x["owner"] == owner and "chain" in x),
                 next(x for x in known if x["status"] == status and x["owner"] == owner))
    return {"status": status, "owner": owner, "basis": basis, "releases": seen,
            "agree": f"{count[status]} of {len(seen)} recent releases"}
