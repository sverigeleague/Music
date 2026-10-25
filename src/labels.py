"""Signed or unsigned: each artist's current label status from the labels printed on their recent releases (Deezer),
matched against registry/label_owners.csv. registry/label_overrides.csv (the owner's decisions) wins.

Statuses:
- major: a label owned by Universal, Sony or Warner (or a joint venture with one);
- major_distributed: distributed or label-serviced by a major's arm (Virgin, The Orchard, AWAL, ADA);
- independent: an independent label (EMPIRE, gamma., BMG, Roc Nation ...);
- self_released: the artist's own name, "Independent", or a distributor that leaves the artist owning the masters
  (UnitedMasters, DistroKid, TuneCore ...). These are the unsigned;
- unknown: a label name we cannot place (often a small label or an artist's own imprint); goes to the review list.
"""
import csv
import re
import unicodedata

from .config import REGISTRY

OWNERS = REGISTRY / "label_owners.csv"
OVERRIDES = REGISTRY / "label_overrides.csv"
RANK = {"major": 0, "major_distributed": 1, "independent": 2, "self_released": 3}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", s)


def owners() -> list[dict]:
    with OWNERS.open() as f:
        return list(csv.DictReader(f))


def _matches(pattern: str, text: str) -> bool:
    if pattern.startswith("="):  # the whole label string, for generic names ("=urban": Universal Music Germany's label)
        return text.strip() == pattern[1:]
    if re.fullmatch(r"[a-z0-9 ]+", pattern):
        return re.search(r"\b" + re.escape(pattern) + r"\b", text) is not None
    return pattern in text


_MB: dict | None = None


def musicbrainz_owner(label: str, table: list[dict]) -> tuple[str, str] | None:
    """The label's nearest owner or parent on MusicBrainz that our table places, else a major distributor."""
    global _MB
    if _MB is None:
        from .collectors import musicbrainz_labels
        _MB = musicbrainz_labels.load()
    res = _MB.get(label) or {}
    for name in res.get("chain", []):
        st, owner = classify_label(name, "", table, use_musicbrainz=False)
        if st != "unknown":
            return st, owner
    for name in res.get("distributors", []):
        st, owner = classify_label(name, "", table, use_musicbrainz=False)
        if st in ("major", "major_distributed"):
            return "major_distributed", owner
    return None


def _in_force(row: dict, released: str) -> bool:
    """A row with a from/until date (a label that changed hands, e.g. Big Machine in February 2026) applies only to
    releases dated inside it; without a release date, only rows with no dates apply."""
    lo, hi = row.get("from") or "", row.get("until") or ""
    if not (lo or hi):
        return True
    return bool(released) and (not lo or released[:10] >= lo) and (not hi or released[:10] <= hi)


def classify_label(label: str, artist: str, table: list[dict] | None = None, use_musicbrainz: bool = True,
                   released: str = "") -> tuple[str, str]:
    """(status, owner) of one release's label string: our table first, then the label's owners on MusicBrainz."""
    table = [r for r in (table or owners()) if _in_force(r, released)]
    text = label.casefold()
    m = re.search(r"under (?:exclusive )?licen[cs]e to (.+)$", text)
    parts = [m[1], text] if m else [text]  # the licensee decides
    for part in parts:
        hits = [r for r in table if _matches(r["pattern"], part)]
        if hits:
            best = min(hits, key=lambda r: RANK[r["status"]])
            return best["status"], best["owner"]
    if use_musicbrainz:
        found = musicbrainz_owner(label, table)
        if found:
            return found
    if _norm(artist) and _norm(artist) in _norm(label):
        return "self_released", "the artist's own name"
    return "unknown", ""


def label_name(label: str, table: list[dict] | None = None, released: str = "") -> str:
    """The label a release string names, as shown on the site: our table's display name for the matched pattern
    (the licensee first), else the release string without company suffixes. Dated rows apply as in classify_label."""
    table = [r for r in (table or owners()) if _in_force(r, released)]
    text = label.casefold()
    m = re.search(r"under (?:exclusive )?licen[cs]e to (.+)$", text)
    for part in ([m[1], text] if m else [text]):
        hits = [r for r in table if _matches(r["pattern"], part)]
        if hits:
            best = min(hits, key=lambda r: RANK[r["status"]])
            return best.get("label") or best["pattern"].title()
    raw = re.split(r",? under (?:exclusive )?licen[cs]e to ", label, flags=re.I)[-1]
    return re.sub(r",?\s*\b(LLC|Inc|Ltd|GmbH|LTD|INC)\b\.?", "", raw).strip(" ,.") or label


def overrides() -> dict[str, dict]:
    if not OVERRIDES.exists():
        return {}
    with OVERRIDES.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}


def artist_status(releases: list[dict], artist: str, table: list[dict] | None = None) -> dict:
    """The status most of the artist's recent releases share (releases newest first). Deezer lists collaborations
    under every artist on them, so one joint single on another label does not decide it."""
    table = table or owners()
    seen = []
    for r in releases:
        st, owner = classify_label(r["label"], artist, table, released=r.get("release_date", ""))
        seen.append({"title": r["title"], "date": r["release_date"], "label": r["label"], "status": st, "owner": owner})
    known = [x for x in seen if x["status"] != "unknown"]
    if not known:
        return {"status": "unknown", "owner": "", "basis": seen[0] if seen else None, "releases": seen}
    count = {}
    for x in known:
        count[x["status"]] = count.get(x["status"], 0) + 1
    status = max(count, key=lambda k: (count[k], -RANK[k]))  # a tie goes to the more signed status
    owners_ = [x["owner"] for x in known if x["status"] == status]
    owner = max(set(owners_), key=owners_.count)
    basis = next(x for x in known if x["status"] == status and x["owner"] == owner)
    return {"status": status, "owner": owner, "basis": basis, "releases": seen,
            "agree": f"{count[status]} of {len(seen)} recent releases"}


NEW_US = ("QM", "QZ", "QT")  # US registrant codes issued after 2010 (newer registrants: DIY distributors, small labels)


def learn_registrants(statuses: dict[str, dict], isrcs: dict[str, list[str]], min_tracks: int = 10) -> dict[str, str]:
    """ISRC prefix (country + registrant) -> major, learned from our own data: a prefix is a major's when at least
    `min_tracks` recent lead-artist songs carry it and 90% or more of them are by artists whose release labels are a
    major's; the owner is the major most of those songs belong to. No public list maps prefixes to companies."""
    seen: dict[str, list[str]] = {}
    for sid, st in statuses.items():
        if st["status"] == "unknown":
            continue  # only artists whose labels settle the question
        for p in isrcs.get(sid, []):
            seen.setdefault(p, []).append(st["owner"] if st["status"] == "major" else "-")
    out = {}
    for p, owners_ in seen.items():
        majors = [o for o in owners_ if o != "-"]
        if len(owners_) >= min_tracks and len(majors) / len(owners_) >= 0.9:
            out[p] = max(set(majors), key=majors.count)
    return out


def check_with_isrcs(status: dict, prefixes: list[str], registrants: dict[str, str]) -> dict:
    """Second check for own-name and unknown labels: the recording codes of the artist's recent songs.
    For the unsigned, `confidence` says what the status rests on: "confirmed" (a distributor named on the release, or
    most recent songs on newer independent registrant codes) or "label name only"."""
    status = dict(status)
    if status["status"] == "self_released":
        named = status["owner"] not in ("the artist's own name", "")
        new_share = sum(p.startswith(NEW_US) for p in prefixes) / len(prefixes) if prefixes else 0
        status["confidence"] = "confirmed" if named or new_share >= 0.5 else "label name only"
    if not prefixes or status["status"] not in ("self_released", "unknown"):
        return status
    major = [registrants[p] for p in prefixes if p in registrants]
    new_us = [p for p in prefixes if p.startswith(NEW_US)]
    if len(major) / len(prefixes) >= 0.5:
        owner = max(set(major), key=major.count)
        status.pop("confidence", None)
        return {**status, "status": "major", "owner": owner,
                "isrc_note": f"{len(major)} of {len(prefixes)} recent songs registered by {owner}"}
    if status["status"] == "unknown" and len(new_us) / len(prefixes) >= 0.5:
        return {**status, "isrc_note": "small or new registrant (QM/QZ/QT codes): a small label or self-release; review"}
    return {**status, "isrc_note": f"{len(new_us)} of {len(prefixes)} recent songs on newer US registrant codes" if new_us else ""}


DEAL_OF_STATUS = {"major": "major", "major_distributed": "services", "independent": "independent",
                  "self_released": "diy"}
