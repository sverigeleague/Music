"""Scout back-test (ROADMAP 8.2): did artists that would have scored highest grow more over the next 90 days?

Only two of Scout's factors have an archived history, so only they can be scored in the past:
- listener growth: monthly listeners against 90 days earlier (kworb's listeners page in the Wayback Machine, weekly,
  since 2023: data/listener_history.csv);
- Wikipedia attention: page views of the last 3 full months against the 9 before (data/wikipedia_pageviews.csv,
  24 months, so from 12 months back).
Together they carry 35% of today's weight (growth 20, attention 15). New-release pull, current share, engagement,
chart reach and daily momentum have no history before our own daily log (data/scout_history.csv, since
2026-10-23); the full score is back-tested from that log once it is 90 days old.

Method, per test date T (one a month): artists in the archived page at T, T-90 days and T+90 days, under 15m monthly
listeners at T (Scout gives no tier above that). Each factor is a percentile within the listener band at T, as on the
site; the score is their weighted mean. Outcome: monthly listeners at T+90 against T. A "pick" is a top-fifth
score within its band (about the share Scout tiers today); a hit is a pick that outgrew its band's median.
Chance is 50%.

Bias to keep in mind: the artists are today's registry (hip-hop artists in today's top lists), so artists who rose
and then fell away are missing. That flatters growth for everyone; it does not favour the picks by itself.
"""
from bisect import bisect_right
from datetime import date, timedelta

from . import insights

DAYS, SLACK, PICK = 90, 10, 0.2
WEIGHTS = {"growth": insights.FACTORS["growth"][0], "attention": insights.FACTORS["attention"][0]}


def _pct(vals: list[float], v: float) -> float:
    lo, hi = bisect_right(vals, v - 1e-12), bisect_right(vals, v)
    return 100 * ((lo + hi) / 2) / len(vals)


def _near(series: dict[str, int], days: list[str], target: date) -> int | None:
    """The value at the snapshot day nearest the target, within SLACK days."""
    best = min(days, key=lambda d: abs((date.fromisoformat(d) - target).days), default=None)
    if best is None or abs((date.fromisoformat(best) - target).days) > SLACK:
        return None
    return series.get(best)


def _attention(months: list[tuple[str, int]], t: date) -> float | None:
    before = [x for x in months if x[0] < t.isoformat()[:7]]
    return (insights.attention(before) or {}).get("trend") if len(before) >= 12 else None


def run(history: dict[str, list[tuple[str, int]]], views: dict[str, list[tuple[str, int]]]) -> dict:
    weekly = {k: {d: v for d, v in s} for k, s in history.items()}
    days = sorted({d for s in weekly.values() for d in s})
    if not days:
        return {}
    first, last = date.fromisoformat(days[0]), date.fromisoformat(days[-1])
    tests = []
    t = date(first.year, first.month, 1) + timedelta(days=DAYS + 31)
    while t + timedelta(days=DAYS) <= last:
        t_day = min(days, key=lambda d: abs((date.fromisoformat(d) - t).days))
        T = date.fromisoformat(t_day)
        rows = []
        for k, s in weekly.items():
            now = s.get(t_day)
            if not now or now >= insights.SCOUTED_BELOW:
                continue
            ds = sorted(s)
            past, fut = _near(s, ds, T - timedelta(days=DAYS)), _near(s, ds, T + timedelta(days=DAYS))
            if not past or not fut:
                continue
            rows.append({"id": k, "ml": now, "growth": now / past, "attention": _attention(views.get(k, []), T),
                         "forward": fut / now})
        if len(rows) >= 50:
            tests.append(_score(t_day, rows))
        t = (t.replace(day=1) + timedelta(days=32)).replace(day=1)
    picks = [p for x in tests for p in x["picks"]]
    hits = sum(p["hit"] for p in picks)
    with_att = [x for x in tests if x["with_attention"]]
    return {"tests": [{k: v for k, v in x.items() if k != "picks"} for x in tests], "picks": len(picks), "hits": hits,
            "hit_rate": round(hits / len(picks), 3) if picks else None,
            "hit_rate_with_attention": (lambda ps: round(sum(p["hit"] for p in ps) / len(ps), 3) if ps else None)(
                [p for x in with_att for p in x["picks"]]),
            "from": tests[0]["date"] if tests else None, "to": tests[-1]["date"] if tests else None}


def _score(day: str, rows: list[dict]) -> dict:
    by_band: dict[int, list[dict]] = {}
    for r in rows:
        by_band.setdefault(insights.band(r["ml"]), []).append(r)
    picks, n_att = [], 0
    pick_fwd, rest_fwd = [], []
    for members in by_band.values():
        fac = {f: sorted(r[f] for r in members if r[f] is not None) for f in WEIGHTS}
        for r in members:
            p = {f: _pct(fac[f], r[f]) for f in WEIGHTS if r[f] is not None and len(fac[f]) > 1}
            r["score"] = sum(WEIGHTS[f] * v for f, v in p.items()) / sum(WEIGHTS[f] for f in p) if p else None
            n_att += "attention" in p
        scored = sorted((r for r in members if r["score"] is not None), key=lambda r: -r["score"])
        if len(scored) < 10:
            continue
        median = sorted(r["forward"] for r in scored)[len(scored) // 2]
        top = scored[:max(1, round(PICK * len(scored)))]
        for r in scored:
            (pick_fwd if r in top else rest_fwd).append(r["forward"])
        picks += [{"id": r["id"], "hit": r["forward"] > median} for r in top]
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
    return {"date": day, "artists": len(rows), "with_attention": n_att > len(rows) / 2, "picks": picks,
            "hit_rate": round(sum(p["hit"] for p in picks) / len(picks), 3) if picks else None,
            "pick_growth": round(med(pick_fwd) - 1, 4) if pick_fwd else None,
            "rest_growth": round(med(rest_fwd) - 1, 4) if rest_fwd else None}
