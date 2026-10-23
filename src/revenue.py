"""Revenue streams per artist, per year at the current pace, as low/mid/high ranges with a grade and basis per line.

Two amounts per line, never mixed:
- generated: the money the activity brings in before anyone's cut (royalties paid to the label or distributor, a
  tour's box office, merch sales);
- artist: the artist's estimated slice before their own manager, lawyer and tax.

Lines (each with its grade: A primary, B reputable secondary, C our estimate):
1. Spotify recordings: measured lead-artist streams x rate per 1,000 (registry/platforms.csv).
2. YouTube: measured daily views x 365 x rate per 1,000.
3. Other streaming services (Apple Music, Amazon, Deezer, TIDAL, others): Spotify recordings x each service's
   multiplier (registry/platform_multipliers.csv, sourced market shares).
4. Publishing: about a quarter of recording royalties again, for the songwriters (shown as generated only: the
   artist's writer share needs song credits).
5. Touring: reported box office (registry/tours.csv: Billboard Boxscore / Pollstar) in the last 12 months; artist
   net 15-35% of gross (rule of thumb, C).
6. Merch at shows: tickets x spend per fan ($10.24 all concerts, $13.29-15.16 hip-hop: ATVENU), less the venue's
   cut (0-25%) and costs (40-60%).
Brand deals and record deals are listed as reported (registry/deals.csv), not annualised.
"""
import csv
from datetime import date

from .config import REGISTRY

DAYS = 365
MERCH_PER_FAN = (10.24, 13.29, 15.16)       # ATVENU 2024-2025 (B)
MERCH_VENUE_CUT = (0.25, 0.20, 0.0)          # low artist case = highest cut
MERCH_COSTS = (0.60, 0.50, 0.40)             # cost of goods and merch company
TOUR_ARTIST_NET = (0.15, 0.20, 0.35)         # artist's net share of tour gross (C)
PUBLISHING_TO_MASTER = (0.20, 0.25, 0.25)    # Spotify royalties guide: about 4/5 recordings, 1/5 publishing (A)
K = ("low", "mid", "high")


def _csv(name):
    p = REGISTRY / name
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f))


def platforms() -> dict[str, dict]:
    return {r["platform"]: r for r in _csv("platforms.csv")}


def multipliers() -> list[dict]:
    """Other services as a ratio of Spotify recording royalties: platform, low, mid, high, grade, source."""
    return _csv("platform_multipliers.csv")


def tours() -> list[dict]:
    return _csv("tours.csv")


def deals() -> list[dict]:
    return _csv("deals.csv")


def _rng(lo, mid, hi):
    return {"low": lo, "mid": mid, "high": hi}


def _rate(p: dict) -> tuple[float, float, float] | None:
    try:
        return tuple(float(p[f"per_1000_{k}"]) for k in K)
    except (KeyError, ValueError):
        return None


def tour_last_12_months(artist: str, today: date) -> dict | None:
    """Reported box office in the 12 months to `today`. A tour that spans the window counts pro rata by days."""
    gross = tickets = 0.0
    used, grades = [], []
    start_window = date(today.year - 1, today.month, min(today.day, 28))
    for t in tours():
        if t.get("artist", "").casefold() != artist.casefold() or not t.get("gross_usd"):
            continue
        try:
            s = date.fromisoformat(t["start"][:10])
            e = date.fromisoformat((t.get("end") or t["start"])[:10])
        except ValueError:
            continue
        lo, hi = max(s, start_window), min(e, today)
        if hi < lo:
            continue
        share = 1.0 if e == s else ((hi - lo).days + 1) / ((e - s).days + 1)
        gross += float(t["gross_usd"]) * share
        tickets += float(t["tickets"] or 0) * share
        used.append({"tour": t["tour"], "start": t["start"], "end": t.get("end"), "gross": float(t["gross_usd"]),
                     "tickets": float(t["tickets"]) if t.get("tickets") else None, "share": round(share, 2),
                     "grade": t.get("grade"), "source": t.get("source_url")})
        grades.append(t.get("grade") or "C")
    if not used:
        return None
    return {"gross": gross, "tickets": tickets or None, "tours": used, "grade": max(grades)}


def estimate(a: dict, today: date, deal_share: dict) -> dict:
    """a: an artist row from the site build (lead_daily, yt_daily, name). deal_share: artist's share of recordings."""
    pf, lines = platforms(), []
    sp = _rate(pf["spotify"])
    spotify = None
    if a.get("lead_daily") and sp:
        spotify = _rng(*(a["lead_daily"] * DAYS * r / 1000 for r in sp))
        lines.append({"key": "spotify", "label": "Spotify", "group": "Streaming", "generated": spotify,
                      "grade": "C", "basis": "measured streams × $2.50–4.40 per 1,000"})
    yt = _rate(pf["youtube"])
    if a.get("yt_daily") and yt:
        lines.append({"key": "youtube", "label": "YouTube", "group": "Streaming",
                      "generated": _rng(*(a["yt_daily"] * DAYS * r / 1000 for r in yt)),
                      "grade": "C", "basis": "measured views × $1.00–6.00 per 1,000"})
    if spotify:
        for m in multipliers():
            lines.append({"key": m["platform"], "label": pf.get(m["platform"], {}).get("name", m["platform"]),
                          "group": "Streaming",
                          "generated": {k: spotify[k] * float(m[k]) for k in K}, "grade": "C",
                          "basis": f"Spotify × {float(m['mid']):.2f} (market share, {m['grade']}-grade source)"})
    streaming = {k: sum(l["generated"][k] for l in lines) for k in K}
    for l in lines:
        l["artist"] = {k: l["generated"][k] * deal_share[k] for k in K}
    if spotify:
        lines.append({"key": "publishing", "label": "Publishing (songwriters)", "group": "Publishing",
                      "generated": {k: streaming[k] * PUBLISHING_TO_MASTER[i] for i, k in enumerate(K)},
                      "artist": None, "grade": "C",
                      "basis": "about a quarter of recording royalties, shared among the writers"})
    tour = tour_last_12_months(a["name"], today)
    if tour:
        g = tour["gross"]
        lines.append({"key": "touring", "label": "Touring (box office)", "group": "Live",
                      "generated": _rng(g, g, g), "artist": {k: g * TOUR_ARTIST_NET[i] for i, k in enumerate(K)},
                      "grade": tour["grade"], "basis": "reported gross, last 12 months; artist net 15–35% (C)",
                      "tours": tour["tours"]})
        if tour["tickets"]:
            gen = {k: tour["tickets"] * MERCH_PER_FAN[i] for i, k in enumerate(K)}
            net = {k: gen[k] * (1 - MERCH_VENUE_CUT[i]) * (1 - MERCH_COSTS[i]) for i, k in enumerate(K)}
            lines.append({"key": "merch", "label": "Merch at shows", "group": "Live", "generated": gen, "artist": net,
                          "grade": "C", "basis": "tickets × $10–15 a fan (ATVENU), less venue cut and costs"})
    reported = [d for d in deals() if d.get("artist", "").casefold() == a["name"].casefold()]
    total = {k: sum((l["artist"] or {}).get(k, 0) for l in lines) for k in K}
    return {"lines": lines, "artist_total": total, "deals": reported}
