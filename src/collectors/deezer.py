"""Deezer public API (no key): fans per artist, matched by exact name; uncertain matches are flagged for review."""
import unicodedata

from ..http import get

API = "https://api.deezer.com"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    return "".join(c for c in s if c.isalnum())


def match(name: str) -> dict:
    """{'deezer_id', 'deezer_fans', 'deezer_match'}: match is exact, ambiguous (a second exact name with more than
    10% of the fans) or none."""
    r = get(f"{API}/search/artist", params={"q": name, "limit": 25})
    if r.status_code != 200:
        return {"deezer_match": "error"}
    hits = [a for a in r.json().get("data", []) if _norm(a["name"]) == _norm(name)]
    if not hits:
        return {"deezer_match": "none"}
    hits.sort(key=lambda a: -a.get("nb_fan", 0))
    best = hits[0]
    ambiguous = len(hits) > 1 and hits[1].get("nb_fan", 0) > 0.1 * best.get("nb_fan", 0)
    return {"deezer_id": best["id"], "deezer_fans": best.get("nb_fan"),
            "deezer_match": "ambiguous" if ambiguous else "exact"}


CONFIRMED = ("exact", "isrc")  # matches whose Deezer ID is trusted: one artist of that name, or confirmed by ISRC


def by_isrc(name: str, isrcs: list[str], need: int = 2) -> dict | None:
    """The Deezer artist credited on the artist's own songs, looked up by ISRC (track/isrc:<code>): the contributor
    with the same name on at least `need` of the songs (or the one song, if only one has an ISRC). For names that
    several Deezer artists share. None when the songs disagree or are not found."""
    votes: dict[int, int] = {}
    seen = 0
    for code in isrcs:
        r = get(f"{API}/track/isrc:{code}")
        j = r.json() if r.status_code == 200 else {}
        if not isinstance(j, dict) or "error" in j or not j.get("id"):
            continue
        seen += 1
        for c in {c["id"]: c for c in j.get("contributors", []) or [j.get("artist", {})]}.values():
            if c.get("id") and _norm(c.get("name", "")) == _norm(name):
                votes[c["id"]] = votes.get(c["id"], 0) + 1
    if not votes:
        return None
    best = max(votes, key=votes.get)
    if votes[best] < min(need, seen) or sum(1 for v in votes.values() if v == votes[best]) > 1:
        return None
    a = get(f"{API}/artist/{best}")
    fans = a.json().get("nb_fan") if a.status_code == 200 else None
    return {"deezer_id": best, "deezer_fans": fans, "deezer_match": "isrc"}


def _title(t: str) -> str:
    """A song title without its featured artists or version note, for matching across services."""
    import re
    return _norm(re.split(r"\s[\(\[-]|\s(?:feat|ft|with)\.?\s", t, maxsplit=1, flags=re.I)[0])


def by_titles(deezer_id, titles: list[str]) -> bool:
    """Whether the Deezer artist is the same act as a Spotify artist: at least two of the artist's biggest Spotify
    songs (titles from kworb) are among the Deezer artist's 50 top tracks (one, when only one title is given). For a
    name that matches a single Deezer artist but has no Wikidata entry to confirm it."""
    import time
    for wait in (5, 10, None):
        r = get(f"{API}/artist/{deezer_id}/top", params={"limit": 50})
        j = r.json() if r.status_code == 200 else {}
        if isinstance(j, dict) and j.get("error", {}).get("code") == 4 and wait:  # quota: wait and retry
            time.sleep(wait)
            continue
        break
    theirs = {_title(t.get("title", "")) for t in (j.get("data") or [])} - {""}
    ours = [x for x in (_title(t) for t in titles) if x]
    hits = sum(1 for t in ours if t in theirs)
    return bool(ours) and hits >= min(2, len(ours))
