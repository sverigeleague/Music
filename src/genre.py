"""Genre decision: is an artist hip-hop/rap? Three inputs, one rule, the owner's overrides win.

1. MusicBrainz community votes (used internally only): share of votes on hip-hop genres.
2. Wikidata genres (CC0): share of the artist's genres under hip-hop.
3. registry/genre_overrides.csv: the owner's decisions from the review list.

Latin trap and reggaeton are a separate bucket ("latin") until the owner decides how to treat them.
"""
import csv

from .config import REGISTRY

HIP_HOP_WORDS = ("hip hop", "hip-hop", "rap", "trap", "drill", "grime", "boom bap", "g-funk", "crunk", "plugg",
                 "rage", "phonk", "horrorcore", "dirty south", "bounce", "hyphy", "jerk", "snap", "chopped and screwed")
NOT_HIP_HOP = ("rap rock", "rap metal", "nu metal", "trap latino", "latin trap", "trip hop", "trap (edm)", "trapstep")
LATIN_WORDS = ("reggaeton", "trap latino", "latin trap", "latin hip hop", "latin hip-hop", "latin", "dembow",
               "urbano latino", "corrido", "regional mexicano")

INCLUDE, REVIEW_LOW = 0.5, 0.3
OVERRIDES = REGISTRY / "genre_overrides.csv"


def family(genre: str) -> str:
    g = genre.casefold()
    if any(w in g for w in LATIN_WORDS):
        return "latin"
    if any(w in g for w in NOT_HIP_HOP):
        return "other"
    return "hip_hop" if any(w in g for w in HIP_HOP_WORDS) else "other"


def overrides() -> dict[str, dict]:
    if not OVERRIDES.exists():
        return {}
    with OVERRIDES.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}


def decide(mb_votes: list[tuple[str, int]], wd_genres: list[tuple[str, bool, bool]]) -> tuple[str, str]:
    """Returns (decision, basis). decision: hip_hop | latin | review | other."""
    total = sum(n for _, n in mb_votes)
    if total >= 3:
        share = {"hip_hop": 0, "latin": 0, "other": 0}
        for g, n in mb_votes:
            share[family(g)] += n / total
        basis = f"MusicBrainz votes: hip-hop {share['hip_hop']:.0%}, Latin {share['latin']:.0%} of {total}"
        if share["latin"] >= 0.4 and share["latin"] >= share["hip_hop"]:
            return "latin", basis
        if share["hip_hop"] >= INCLUDE:
            return "hip_hop", basis
        return ("review" if share["hip_hop"] >= REVIEW_LOW else "other"), basis
    # thin or no votes: Wikidata decides, and a weak case goes to review
    if not wd_genres:
        return "review", "no genre data"
    hh = sum(1 for _, h, _l in wd_genres if h) / len(wd_genres)
    lat = sum(1 for _, _h, l in wd_genres if l) / len(wd_genres)
    basis = f"Wikidata genres: hip-hop {hh:.0%}, Latin {lat:.0%} of {len(wd_genres)} (MusicBrainz votes: {total})"
    if lat >= 0.5:
        return "latin", basis
    return ("hip_hop" if hh >= 0.67 and total else "review"), basis
