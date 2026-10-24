"""Scout, Worth, levels and the labels market map: computed from the site rows (site_build.py) once per build.

Scout score (0-100): a ranking signal for labels, not a prediction. Each factor is turned into a percentile among
artists of a similar size (monthly-listener band), so a 2m-listener artist is compared with other 2m-listener artists.
The score is the weighted mean of the factors the artist has (at least 3); weights below. Tiers: Breaking 80+,
Rising 65+, Watch 50+. Back-test once 90 days of listener history exist (ROADMAP 7.10).

Worth: the value of an income stream = yearly income x a sale multiple. The multiple depends on how new the music is
(registry/catalog_multiples.csv, sourced): new music decays faster, so buyers pay fewer years of income for it.
Shown as a range (low income x low multiple to high income x high multiple), grade C.
"""
import csv
import re
from bisect import bisect_right

from .config import REGISTRY

BANDS = (1_500_000, 3_000_000, 6_000_000, 15_000_000)  # monthly-listener bands, about the top 1,000's quartiles
BAND_LABELS = ("under 1.5m", "1.5-3m", "3-6m", "6-15m", "15m+")
# factor: (weight, label shown on the site)
# Listener growth counts where 90 days of history exist (our snapshots since 2026-10-23, or the Wayback backfill);
# where it is missing the other weights are scaled up to 100%.
# Owner, 2026-10-24 ("S1: 5%"): listener growth cut from 20% to 5% after the back-test (src/backtest.py: fast 90-day
# growth cooled off over the next 90 days, 44% of picks beat their peers). The 15 points go to the other factors in
# proportion, rounded: until the full back-test from our daily log in January 2027.
# Owner, same day: "Don't put so much weight on Wikipedia attention" (43% of picks in the back-test): 18% -> 5%, the
# freed points to new-release pull, current share, engagement and chart reach in proportion.
FACTORS = {
    "velocity": (0.35, "New-release pull: share of daily streams from songs out 90 days or less"),
    "growth": (0.05, "Listener growth: monthly listeners against 90 days ago"),
    "current": (0.22, "Current share: listening on releases of the last 18-36 months"),
    "attention": (0.05, "Wikipedia attention: page views of the last 3 months against the 9 before"),
    "engagement": (0.14, "Streams a day per monthly listener"),
    "breadth": (0.14, "Chart reach: countries with a song in Spotify's weekly top 200, plus Apple Music's daily top 100"),
    "momentum": (0.05, "Monthly listeners, change today"),
}
# Country (owner C4, 2026-10-24): US AM/FM radio is the genre's biggest audience outside streaming, so its audience is
# a factor; our percentile is shown, kworb's audience figures are not. Chart reach weighs less (country charts are
# mostly US, CA, AU). A starting point until a country back-test exists.
COUNTRY_FACTORS = {
    "velocity": (0.30, FACTORS["velocity"][1]),
    "growth": FACTORS["growth"],
    "current": (0.20, FACTORS["current"][1]),
    "attention": FACTORS["attention"],
    "engagement": (0.12, FACTORS["engagement"][1]),
    "breadth": (0.08, FACTORS["breadth"][1]),
    "momentum": FACTORS["momentum"],
    "radio": (0.15, "US radio: AM/FM airplay audience of the artist's current songs (0 when not on the airplay chart)"),
}
FACTORS_BY_GENRE = {"hip_hop": FACTORS, "country": COUNTRY_FACTORS}
TIERS = ((80, "Breaking"), (65, "Rising"), (50, "Watch"))
SCOUTED_BELOW = 15_000_000  # artists this big are established: scored, but given no tier
# Breaking also needs a measured absolute signal, not only a high rank among peers: new songs pulling at least a
# quarter of the streams, or Wikipedia attention up 30%+
BREAKING_FRESH, BREAKING_ATTENTION = 0.25, 1.3
LEVELS = ((40_000_000, "Icon"), (15_000_000, "Headliner"), (5_000_000, "Rising star"), (0, "Rookie"))


def band(ml: int) -> int:
    return bisect_right(BANDS, ml or 0)


def attention(months: list[tuple[str, int]]) -> dict | None:
    """Last 3 full months against the average of the 9 before, plus the 24-month series for the sparkline."""
    if len(months) < 12:
        return None
    vals = [v for _m, v in months]
    last3, prior = sum(vals[-3:]), sum(vals[-12:-3]) / 3
    return {"trend": last3 / prior if prior else None, "last3": last3, "series": vals[-24:],
            "start": months[-24:][0][0] if months else None}


def growth(history: list[tuple[str, int]], today: str, days: int = 90, slack: int = 10) -> float | None:
    """Monthly listeners now against `days` ago (the snapshot closest to that day, within `slack` days)."""
    from datetime import date
    if not history:
        return None
    t = date.fromisoformat(today)
    best = min(history, key=lambda x: abs((t - date.fromisoformat(x[0])).days - days))
    if abs((t - date.fromisoformat(best[0])).days - days) > slack or not best[1]:
        return None
    return history[-1][1] / best[1]


def raw_factors(r: dict) -> dict:
    att = r.get("attention") or {}
    return {
        "velocity": r.get("fresh_share"),
        "growth": r.get("growth90"),
        "current": r.get("cur_share"),
        "attention": att.get("trend"),
        "engagement": r["daily"] / r["ml"] if r.get("daily") and r.get("ml") else None,
        "breadth": (r.get("geo") or {}).get("countries", 0) + len((r.get("apple") or {}).get("countries", [])),
        "momentum": r.get("chg_pct"),
        "radio": r.get("radio_week"),
    }


def scout(rows: list[dict], factors: dict = FACTORS) -> None:
    """Adds r["scout"] = {score, tier, factors: {name: percentile}} to every row with 3+ factors."""
    raw = {r["id"]: raw_factors(r) for r in rows}
    by_band: dict[int, list[dict]] = {}
    for r in rows:
        by_band.setdefault(band(r["ml"]), []).append(r)
    for members in by_band.values():
        pct: dict[str, dict[str, float]] = {}
        for f in factors:
            vals = sorted(v for r in members if (v := raw[r["id"]][f]) is not None)
            for r in members:
                v = raw[r["id"]][f]
                if v is not None and len(vals) > 1:
                    # mid-rank percentile: ties share a value
                    lo, hi = bisect_right(vals, v - 1e-12), bisect_right(vals, v)
                    pct.setdefault(r["id"], {})[f] = round(100 * ((lo + hi) / 2) / len(vals))
        for r in members:
            p = pct.get(r["id"], {})
            if len(p) < 3:
                r["scout"] = None
                continue
            w = sum(factors[f][0] for f in p)
            score = round(sum(factors[f][0] * v for f, v in p.items()) / w)
            tier = next((t for m, t in TIERS if score >= m), None)
            if tier == "Breaking" and not ((r.get("fresh_share") or 0) >= BREAKING_FRESH
                                           or ((r.get("attention") or {}).get("trend") or 0) >= BREAKING_ATTENTION):
                tier = "Rising"
            if (r["ml"] or 0) >= SCOUTED_BELOW:
                tier = None
            r["scout"] = {"score": score, "tier": tier, "factors": p, "band": BAND_LABELS[band(r["ml"])]}


def multiples() -> list[dict]:
    with (REGISTRY / "catalog_multiples.csv").open() as f:
        return list(csv.DictReader(f))


def vintage(cur_share: float | None, table: list[dict]) -> dict:
    s = 0.45 if cur_share is None else cur_share  # unknown: treated as mixed
    return next(m for m in table if float(m["current_share_min"]) <= s < float(m["current_share_max"]))


def worth(r: dict, rev: dict, table: list[dict]) -> dict:
    """Yearly income and what each income stream would sell for. rev: revenue.estimate() output."""
    streaming = [l for l in rev["lines"] if l["group"] == "Streaming"]
    pub = [l for l in rev["lines"] if l["group"] == "Publishing"]
    tot = lambda ls, part, k: sum((l.get(part) or {}).get(k, 0) or 0 for l in ls)
    m = vintage(r.get("cur_share"), table)
    lo, hi = float(m["multiple_low"]), float(m["multiple_high"])
    mid = (lo + hi) / 2
    val = lambda ls, part: {"low": tot(ls, part, "low") * lo, "mid": tot(ls, part, "mid") * mid,
                            "high": tot(ls, part, "high") * hi}
    return {"vintage": m["vintage"], "multiple": [lo, hi], "multiple_source": m["source_url"],
            "multiple_note": m["source_note"], "grade": "C",
            "recordings": val(streaming, "generated"), "artist_royalties": val(streaming, "artist"),
            "publishing": val(pub, "generated")}


def level(r: dict) -> dict:
    """Level from today's monthly listeners; badges from the measured signals."""
    name = next(n for m, n in LEVELS if (r["ml"] or 0) >= m)
    badges = []
    sc = r.get("scout") or {}
    if sc.get("tier") == "Breaking":
        badges.append("Breaking")
    if r.get("label_status") == "self_released" and (sc.get("score") or 0) >= 65:
        badges.append("Unsigned and rising")
    if r.get("feature_daily") and r.get("daily") and r["feature_daily"] / r["daily"] >= 0.8:
        badges.append("Feature magnet")
    if ((r.get("geo") or {}).get("countries") or 0) + len((r.get("apple") or {}).get("countries", [])) >= 20:
        badges.append("Global")
    if r.get("revivals"):
        badges.append("Revival")
    if (r.get("fresh_share") or 0) >= 0.5:
        badges.append("Hot release")
    return {"name": name, "badges": badges}


def group_of(r: dict) -> str:
    """The market-map group: the major behind the label or distributor, else independent / self-released."""
    s = r.get("label_status")
    if s in ("major", "major_distributed"):
        return r.get("label_owner") or "Major (unnamed)"
    return {"independent": "Independent labels", "self_released": "Self-released", "catalog": "Catalog"}.get(s, "Not yet known")


def market(rows: list[dict]) -> dict:
    """Share of the top 1,000 by group: artists, monthly listeners, current listeners; overall and per size band.
    Independent labels are also listed one by one."""
    groups: dict[str, dict] = {}
    catalog = [r for r in rows if r.get("label_status") == "catalog"]  # no new releases: left out of the shares
    for r in (r for r in rows if r.get("label_status") != "catalog"):
        g = groups.setdefault(group_of(r), {"artists": 0, "ml": 0, "cl": 0, "bands": [0] * len(BAND_LABELS),
                                            "top": [], "labels": {}})
        g["artists"] += 1
        g["ml"] += r["ml"] or 0
        g["cl"] += r.get("cl") or 0
        g["bands"][band(r["ml"])] += 1
        if len(g["top"]) < 12:
            g["top"].append(r["id"])  # rows arrive biggest first
        if r.get("label_status") == "independent" and r.get("label_owner"):
            lab = g["labels"].setdefault(r["label_owner"], {"artists": 0, "ml": 0})
            lab["artists"] += 1
            lab["ml"] += r["ml"] or 0
    band_totals = [sum(g["bands"][i] for g in groups.values()) for i in range(len(BAND_LABELS))]
    return {"groups": groups, "catalog": len(catalog), "band_labels": list(BAND_LABELS), "band_totals": band_totals,
            "total_ml": sum(g["ml"] for g in groups.values()), "total_cl": sum(g["cl"] for g in groups.values())}


# ---------- feature network: who features whom, from song titles on the artist's own songs
import re as _re

_GUEST = _re.compile(r"\(([^)]*)\)")
_KEY = _re.compile(r"\b(?:feat\.?|ft\.?|featuring|with)\s+", _re.I)
_SPLIT = _re.compile(r"\s*(?:,|&|\bx\b|\band\b|\b(?:feat\.?|ft\.?)\s)\s*", _re.I)


def guests(title: str) -> list[str]:
    """'Knife Talk (with 21 Savage ft. Project Pat)' -> ['21 Savage', 'Project Pat']."""
    out = []
    for inner in _GUEST.findall(title):
        m = _KEY.search(inner)
        if m:
            out += [g.strip() for g in _SPLIT.split(inner[m.end():]) if g.strip()]
    return out


def collabs(songs_by_artist: dict[str, list[dict]], names: dict[str, str], fold) -> dict[str, list[dict]]:
    """Per artist: collaborators matched to our registry by exact folded name, with the shared songs' daily streams.
    Edges come from the lead artist's own songs, and count for both sides."""
    by_fold: dict[str, list[str]] = {}
    for sid, n in names.items():
        by_fold.setdefault(fold(n), []).append(sid)
    edges: dict[str, dict[str, dict]] = {}
    for sid, songs in songs_by_artist.items():
        for s in songs:
            if s["feature"]:
                continue
            for g in guests(s["title"]):
                ids = by_fold.get(fold(g), [])
                if len(ids) != 1 or ids[0] == sid:
                    continue
                for a, b in ((sid, ids[0]), (ids[0], sid)):
                    e = edges.setdefault(a, {}).setdefault(b, {"daily": 0, "songs": 0, "top": None, "top_daily": -1})
                    e["daily"] += s["daily"] or 0
                    e["songs"] += 1
                    if (s["daily"] or 0) > e["top_daily"]:
                        e["top"], e["top_daily"] = s["title"], s["daily"] or 0
    return {a: sorted(({"id": b, "name": names[b], "daily": v["daily"], "songs": v["songs"], "top": v["top"]}
                       for b, v in es.items()), key=lambda x: -x["daily"]) for a, es in edges.items()}


# ---------- label pages: one entry per label (the imprint on the release), with its parent company
PARENT_OF = {"BMG": "Bertelsmann", "BBR Music Group": "BMG", "Concord": "Concord", "Loma Vista Recordings": "Concord"}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "label"


def labels_index(rows: list[dict], release_counts: dict[str, int]) -> list[dict]:
    """Every label with at least one top-1,000 artist: roster (biggest first), combined audience, momentum and the
    royalties its roster's recordings generate (mid estimate, all streaming services)."""
    by: dict[str, dict] = {}
    for r in rows:
        name = r.get("label_name")
        if not name:
            continue
        group = r.get("label_owner") or ""
        L = by.setdefault(name, {"name": name, "slug": slug(name), "status": r["label_status"], "group": group,
                                 "parent": group if r["label_status"] != "independent" else PARENT_OF.get(group, group),
                                 "artists": [], "ml": 0, "cl": 0, "royalties": 0, "breaking": 0, "rising": 0,
                                 "scores": []})
        L["artists"].append(r["id"])
        L["ml"] += r["ml"] or 0
        L["cl"] += r.get("cl") or 0
        L["royalties"] += r.get("streaming_mid") or 0
        tier = (r.get("scout") or {}).get("tier")
        L["breaking"] += tier == "Breaking"
        L["rising"] += tier == "Rising"
        if (r.get("scout") or {}).get("score") is not None:
            L["scores"].append(r["scout"]["score"])
    out = []
    for L in by.values():
        sc = L.pop("scores")
        L["scout_avg"] = round(sum(sc) / len(sc)) if sc else None
        L["releases_2y"] = release_counts.get(L["name"], 0)
        out.append(L)
    return sorted(out, key=lambda L: -L["ml"])
