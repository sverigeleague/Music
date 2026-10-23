"""Genre decision: is an artist hip-hop/rap? Three inputs, one rule, the owner's overrides win.

1. MusicBrainz community votes (used internally only): share of votes on hip-hop genres.
2. Wikidata genres (CC0): share of the artist's genres under hip-hop.
3. Deezer: share of the artist's releases filed under Rap/Hip Hop (and under Latin genres). It settles MusicBrainz's
   borderline cases and decides when votes are thin, if the name match is exact and there are 5+ releases.
4. registry/genre_overrides.csv: the owner's decisions from the review list.

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
# Deezer files much Latin urbano under Rap/Hip Hop: an artist from these countries decided on Deezer alone goes to the
# Latin list (owner's default: Latin trap and reggaeton apart; Brazilian and other rap stays in)
SPANISH_SPEAKING = {"Argentina", "Bolivia", "Chile", "Colombia", "Costa Rica", "Cuba", "Dominican Republic", "Ecuador",
                    "El Salvador", "Guatemala", "Honduras", "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru",
                    "Puerto Rico", "Spain", "Uruguay", "Venezuela"}
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


def _deezer(dz: dict | None) -> tuple[float, float] | None:
    if not dz or dz.get("match") != "exact" or int(dz.get("releases") or 0) < 5 or dz.get("rap_share") in ("", None):
        return None
    return float(dz["rap_share"]), float(dz["latin_share"] or 0)


def decide(mb_votes: list[tuple[str, int]], wd_genres: list[tuple[str, bool, bool]],
           dz: dict | None = None, wikidata: bool = True, country: str = "") -> tuple[str, str]:
    """Returns (decision, basis). decision: hip_hop | latin | review | other."""
    d = _deezer(dz)
    dz_note = f"; Deezer: {d[0]:.0%} of {dz['releases']} releases Rap/Hip Hop" if d else ""
    total = sum(n for _, n in mb_votes)
    if total >= 3:
        share = {"hip_hop": 0, "latin": 0, "other": 0}
        for g, n in mb_votes:
            share[family(g)] += n / total
        basis = f"MusicBrainz votes: hip-hop {share['hip_hop']:.0%}, Latin {share['latin']:.0%} of {total}" + dz_note
        if share["latin"] >= 0.4 and share["latin"] >= share["hip_hop"]:
            return "latin", basis
        if share["hip_hop"] >= INCLUDE:
            return "hip_hop", basis
        if share["hip_hop"] >= REVIEW_LOW:
            if d and d[0] >= 0.7:
                return "hip_hop", basis
            if d and d[0] <= 0.3:
                return "other", basis
            return "review", basis
        return "other", basis
    # thin or no votes: Deezer decides when it can, else Wikidata, and a weak case goes to review
    if d:
        basis = f"Deezer: {d[0]:.0%} of {dz['releases']} releases Rap/Hip Hop, {d[1]:.0%} Latin (MusicBrainz votes: {total})"
        if not wikidata:
            # no Wikidata entry tying the Spotify ID to a person: the Deezer match rests on the name alone
            return "review", basis + "; matched to Deezer by name only"
        if d[1] >= 0.5 or country in SPANISH_SPEAKING:
            return "latin", basis + (f"; {country}" if country in SPANISH_SPEAKING else "")
        if d[0] >= 0.7:
            return "hip_hop", basis
        if d[0] <= 0.2:
            return "other", basis
        return "review", basis
    if not wd_genres:
        return "review", "no genre data"
    hh = sum(1 for _, h, _l in wd_genres if h) / len(wd_genres)
    lat = sum(1 for _, _h, l in wd_genres if l) / len(wd_genres)
    basis = f"Wikidata genres: hip-hop {hh:.0%}, Latin {lat:.0%} of {len(wd_genres)} (MusicBrainz votes: {total})"
    if lat >= 0.5:
        return "latin", basis
    return ("hip_hop" if hh >= 0.67 and total else "review"), basis
