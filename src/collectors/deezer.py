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
