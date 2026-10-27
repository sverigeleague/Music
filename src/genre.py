"""Genre decision: is an artist hip-hop/rap? Three inputs, one rule, the owner's overrides win.

1. MusicBrainz community votes (used internally only): share of votes on hip-hop genres.
2. Wikidata genres (CC0): share of the artist's genres under hip-hop.
3. Deezer: share of the artist's releases filed under Rap/Hip Hop (and under Latin genres). It settles MusicBrainz's
   borderline cases and decides when votes are thin, if the name match is exact and there are 5+ releases.
4. registry/genre_overrides.csv: the owner's decisions from the review list.

Latin (owner 2026-10-26): reggaeton, dembow, Cuban reparto, corridos and the Latin trap/urbano that sits in the
reggaeton orbit are a separate bucket ("latin", left out). Spanish-language rap in the hip-hop tradition (boom bap,
conscious, battle/freestyle, drill) is hip-hop, as Kase.O, Trueno and MC Davo. Where an artist mixes, most of their
lead songs decide; the hand decisions are in genre_overrides.csv.

Smaller acts (owner 2026-10-27, "yes", `decide_small`): for the smaller-acts candidates below kworb's floor only, a
Wikidata hip-hop genre (half or more of the item's genres) or the occupation rapper (P106) is enough evidence without
MusicBrainz votes; for country music, a Wikidata country genre (half or more). The identity rule is unchanged (the
Spotify or Deezer page must be linked at the source), and so are the other rules: Deezer filing most releases as Latin
or few as Rap still decides first; Wikidata naming any Latin genre, or Deezer filing 30%+ of the releases or of the top
songs' releases as Latin, goes to review (Wikidata calls many reggaeton and urbano singers rappers), as does Deezer
filing 20% or less as Rap; from a Spanish-speaking country it takes the songs too (3+ of the Deezer top tracks dated
on the artist's own releases, none filed Latin, and under 10% of the releases Latin), else review. The registry's own
decisions do not use this.

Lo-fi (owner 2026-10-27, "don't count lo-fi as hip-hop", `decide_small`): an act tagged lo-fi, chillhop or
instrumental hip-hop (a Wikidata genre or MusicBrainz tag; one MusicBrainz editor tagged whole lo-fi labels with
"lo-fi hip hop, instrumental hip hop, boom bap, hip hop", found on Deezer's lo-fi playlists) with no sign of vocal rap
(neither the occupation rapper on Wikidata nor a Wikidata hip-hop genre other than the lo-fi ones) is an instrumental
beatmaker: "other", not listed. Tagged and with that sign (a rapper over lo-fi beats), it stays in review.

Hand decisions (`small_overrides`, registry/small_acts_overrides.csv): the smaller-acts checks done by hand with their
evidence (the Spain and Spanish-speaking check of 2026-10-27, owner: "run the Spain check"); they replace the rule's
genre decision, while the identity and features-led holds still apply.
"""
import csv

from .collectors.deezer import CONFIRMED
from .config import REGISTRY

HIP_HOP_WORDS = ("hip hop", "hip-hop", "rap", "trap", "drill", "grime", "boom bap", "g-funk", "crunk", "plugg",
                 "rage", "phonk", "horrorcore", "dirty south", "bounce", "hyphy", "jerk", "snap", "chopped and screwed")
NOT_HIP_HOP = ("rap rock", "rap metal", "nu metal", "trap latino", "latin trap", "trip hop", "trap (edm)", "trapstep")
LATIN_WORDS = ("reggaeton", "trap latino", "latin trap", "latin hip hop", "latin hip-hop", "latin", "dembow",
               "urbano latino", "corrido", "regional mexicano")

INCLUDE, REVIEW_LOW = 0.5, 0.3
# Deezer files much Latin urbano under Rap/Hip Hop, so an artist from these countries decided on Deezer alone goes to
# review: Spanish-language rap is hip-hop, reggaeton/urbano is Latin, and only their songs tell them apart (owner
# 2026-10-26; until then, 2026-10-24, they went to the Latin list)
SPANISH_SPEAKING = {"Argentina", "Bolivia", "Chile", "Colombia", "Costa Rica", "Cuba", "Dominican Republic", "Ecuador",
                    "El Salvador", "Guatemala", "Honduras", "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru",
                    "Puerto Rico", "Spain", "Uruguay", "Venezuela"}
OVERRIDES = REGISTRY / "genre_overrides.csv"
SMALL_OVERRIDES = REGISTRY / "small_acts_overrides.csv"


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


def small_overrides() -> dict[tuple[str, str], dict]:
    """(genre, smaller act's key: QID or "mb:<MBID>") -> the hand decision row (decision hip_hop | latin | country |
    other | review, reason, evidence, decided)."""
    if not SMALL_OVERRIDES.exists():
        return {}
    with SMALL_OVERRIDES.open() as f:
        return {(r["genre"], r["key"]): r for r in csv.DictReader(f)}


def _deezer(dz: dict | None) -> tuple[float, float] | None:
    if not dz or dz.get("match") not in CONFIRMED or int(dz.get("releases") or 0) < 5 or dz.get("rap_share") in ("", None):
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
        if d[1] >= 0.5:
            return "latin", basis
        if country in SPANISH_SPEAKING:
            return "review", basis + f"; {country}: Spanish-language rap or Latin urbano? decided from the songs"
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


SMALL_WD, SMALL_LATIN = 0.5, 0.3
BEATS = ("lo-fi", "lofi", "chillhop", "instrumental hip hop", "beat tape")  # beatmakers met on Deezer's lo-fi playlists


def decide_small(mb_votes: list[tuple[str, int]], wd_genres: list[tuple[str, bool, bool]], dz: dict | None = None,
                 country: str = "", rapper: bool = False) -> tuple[str, str]:
    """The registry's rule, then the owner's smaller-acts rule (2026-10-27, module docstring) for what it leaves in
    review. dz may carry "top_latin" and "top_dated" (the Deezer top tracks' own releases filed Latin, and dated)."""
    dec, basis = decide(mb_votes, wd_genres, dz, wikidata=True, country=country)
    beats = [g for g in [g for g, _n in mb_votes] + [g for g, _h, _l in wd_genres] if any(w in g.casefold() for w in BEATS)]
    vocal = rapper or any(h and not any(w in g.casefold() for w in BEATS) for g, h, _l in wd_genres)
    if beats and not vocal and dec != "latin":  # owner 2026-10-27: lo-fi and instrumental beatmakers are not hip-hop
        return "other", basis + f"; tagged {beats[0]}, no sign of vocal rap: an instrumental beatmaker (owner 2026-10-27: not hip-hop)"
    if dec == "hip_hop" and beats:
        return "review", basis + f"; tagged {beats[0]}: an instrumental beatmaker rather than a rap act?"
    if dec != "review":
        return dec, basis
    hh = sum(1 for _, h, _l in wd_genres if h) / len(wd_genres) if wd_genres else 0
    if hh < SMALL_WD and not rapper:
        return dec, basis
    ev = " and ".join(x for x in ("a Wikidata hip-hop genre" if hh >= SMALL_WD else "",
                                  "the occupation rapper on Wikidata" if rapper else "") if x)
    d = _deezer(dz)
    tl = float(dz["top_latin"]) if dz and dz.get("top_latin") not in ("", None) else None
    td = int(dz.get("top_dated") or 0) if dz else 0
    if beats:
        return "review", basis + f"; {ev}, but tagged {beats[0]} (an instrumental beatmaker?)"
    if d and d[0] <= 0.2:
        return "review", basis + f"; {ev}, but Deezer files few of the releases as Rap/Hip Hop"
    if any(l for _, _h, l in wd_genres):
        return "review", basis + f"; {ev}, but Wikidata also names a Latin genre"
    if (d and d[1] >= SMALL_LATIN) or (tl is not None and td >= 3 and tl >= SMALL_LATIN):
        return "review", basis + f"; {ev}, but Deezer files Latin releases (reggaeton or urbano?)"
    if country in SPANISH_SPEAKING and not (td >= 3 and tl == 0 and (d is None or d[1] < 0.1)):
        return "review", basis + f"; {ev}; {country}: the songs do not settle Spanish-language rap or Latin urbano"
    return "hip_hop", basis + f"; {ev} (owner 2026-10-27: enough without MusicBrainz votes)"


# Country (owner, 2026-10-24: a second genre). Checked only when the hip-hop rule says "other" or "review", so no
# hip-hop decision changes; the owner settles crossovers (Jelly Roll: country).
COUNTRY_WORDS = ("country", "americana", "bluegrass", "red dirt", "outlaw", "honky-tonk", "honky tonk", "western swing",
                 "nashville sound", "bakersfield sound", "alt-country", "alternative country", "southern rock")
NOT_COUNTRY = ("country house", "country blues", "uk garage")
COUNTRY_IN, COUNTRY_REVIEW = 0.6, 0.3


def is_country(genre: str) -> bool:
    g = genre.casefold()
    return any(w in g for w in COUNTRY_WORDS) and not any(w in g for w in NOT_COUNTRY)


def decide_country(mb_votes: list[tuple[str, int]], wd_genres: list[tuple], dz: dict | None = None,
                   wikidata: bool = True, small: bool = False) -> tuple[str, str] | None:
    """("country" | "review", basis) when the artist looks country; None otherwise. small: the smaller-acts rule (owner
    2026-10-27): a Wikidata country genre (half or more of the item's genres) is enough without MusicBrainz votes."""
    total = sum(n for _, n in mb_votes)
    if total >= 3:
        share = sum(n for g, n in mb_votes if is_country(g)) / total
        if share >= COUNTRY_IN:
            return "country", f"MusicBrainz votes: country {share:.0%} of {total}"
        if share >= COUNTRY_REVIEW:
            return "review", f"MusicBrainz votes: country {share:.0%} of {total} (borderline)"
    if dz and dz.get("match") in CONFIRMED and int(dz.get("releases") or 0) >= 5 and dz.get("country_share") not in ("", None):
        c = float(dz["country_share"])
        basis = f"Deezer: {c:.0%} of {dz['releases']} releases Country"
        if c >= COUNTRY_REVIEW and wd_genres and not any(is_country(g[0]) for g in wd_genres):
            # Deezer files some Turkish arabesque and folk under Country; Wikidata's genres say otherwise
            return "review", basis + "; Wikidata genres name no country genre"
        if c >= COUNTRY_IN and wikidata:
            return "country", basis
        if c >= COUNTRY_REVIEW:
            return "review", basis + ("" if wikidata else "; matched to Deezer by name only")
    if wd_genres:
        share = sum(1 for g in wd_genres if is_country(g[0])) / len(wd_genres)
        basis = f"Wikidata genres: country {share:.0%} of {len(wd_genres)}"
        if share >= 0.5 and dz and dz.get("match") in CONFIRMED and int(dz.get("releases") or 0) >= 5 \
                and dz.get("country_share") not in ("", None) and float(dz["country_share"]) < COUNTRY_REVIEW:
            # Wikidata's genre list can be one entry ("alternative country" for Wilco); Deezer's releases say otherwise
            return "review", basis + f"; Deezer files {float(dz['country_share']):.0%} of {dz['releases']} releases under Country"
        if share >= 0.67 and total:
            return "country", basis
        if share >= SMALL_WD and small:
            return "country", basis + " (owner 2026-10-27: enough without MusicBrainz votes)"
        if share >= 0.5:
            return "review", basis
    return None

