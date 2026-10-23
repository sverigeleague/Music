"""Streaming money v0: Spotify recordings only, as ranges.

- Royalties generated: lead-artist streams in a month x the rate per 1,000 (registry/rates.csv). This is what the
  rights holders (label or distributor) receive, not the artist's pay.
- Publishing generated: about a quarter of that again, for the songwriters and publishers (shown, not split).
- Artist take-home from recordings: royalties generated x the artist's share for the assumed deal type
  (registry/deal_shares.csv), before recoupment of advances, which is unknown.
"""
import csv

from .config import REGISTRY

DAYS_PER_MONTH = 30.44


def _load(name, key):
    with (REGISTRY / name).open() as f:
        return {r[key]: r for r in csv.DictReader(f)}


def rates():
    return {r["item"]: r for r in _load("rates.csv", "item").values() if r["platform"] == "spotify"}


def deal_shares():
    return _load("deal_shares.csv", "deal_type")


def deal_type(majors: list[str], labels: list[str]) -> str:
    """Fallback from Wikidata's record labels (whole career) when the current label status is unknown."""
    return "major" if majors else "independent" if labels else "unknown"


def estimate(lead_daily: int | None, deal: str) -> dict | None:
    if not lead_daily:
        return None
    r, s = rates(), deal_shares()[deal]
    m = r["master_per_1000"]
    streams = lead_daily * DAYS_PER_MONTH
    gen = {k: streams * float(m[k]) / 1000 for k in ("low", "mid", "high")}
    pub = {k: gen[k] * float(r["publishing_to_master"][k]) for k in ("low", "mid", "high")}
    take = {"low": gen["low"] * float(s["low"]), "mid": gen["mid"] * float(s["mid"]),
            "high": gen["high"] * float(s["high"])}
    return {"streams_month": round(streams), "generated": gen, "publishing": pub, "take_home": take,
            "deal_type": deal, "deal_label": s["label"], "grade": "C"}
