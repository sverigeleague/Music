"""Smaller acts' ranking for Scout's country view (2026-10-26): a size estimate triangulated from several free
sources, calibrated per country on the artists that do have Spotify monthly listeners, and a provisional score.

Size. Each source (Deezer fans, Deezer's top-10 track rank, Wikipedia views in English and the home language,
ListenBrainz listeners, YouTube subscribers once the daily step has them) is put on one scale: log10 Spotify monthly
listeners. Per source, on the registry artists of the genre with kworb counts, fit log10(source) = c[country] +
d * log10(listeners) (the source regressed on listeners, not the other way: the calibration set is cut at kworb's
500k floor, a cut on listeners, which leaves this slope unbiased; the reverse fit would be flattened by it). The
country term is shrunk toward the genre's pooled term by n / (n + K), so a country with few calibration artists leans
on the pool. Each source's reading becomes an estimate (x - c) / d, weighted by how well the source orders artists within a country (its
pooled within-country Spearman r: weight r² / (1 - r²)). The combined estimate: the weighted median of the sources'
estimates (no source above half the weight), then the
weighted mean of the estimates clipped to within CLIP of that median. A source more than AGREE (a factor of about 3) from the
combined estimate does not agree; when fewer than half the sources agree, the artist is flagged and ranked after the
others. On the hold-out set that flag marks 6% of artists, whose median miss is 2.9x against 1.7x for the rest.

Validation: 10-fold hold-out on the calibration set, the Spearman rank correlation of the combined estimate with true
listeners within each country. All of these artists sit above the floor, so the figure says how well the method
orders artists of 500k+; below the floor it is an extrapolation (said on the page).
"""
import csv
import math
import random
from datetime import date

from .collectors import small_acts as src

SIGNALS = {"fans": "Deezer fans", "rank": "Deezer top-track rank", "wiki": "Wikipedia views (English + home language)",
           "lb": "ListenBrainz listeners", "yt": "YouTube subscribers"}
K, CLIP, AGREE, MAX_SHARE = 10, 0.5, 0.5, 0.5
RECENT_YEARS = 3
MIN_SLOPE = 0.1  # a source that barely moves with listeners is left out
VALID_RHO, VALID_N = 0.4, 8  # a country's list is shown when its hold-out Spearman is 0.4+ on 8+ artists
SCORE = {"size": (0.40, "Size estimate (triangulated, percentile)"), "fresh": (0.25, "Deezer top tracks out in the last 90 days"),
         "charts": (0.15, "Home-country charts (Spotify weekly, Apple Music daily, Shazam)"),
         "attention": (0.10, "Wikipedia views, last 3 months against the 3 before"),
         "growth": (0.10, "Deezer fan growth (weekly snapshots)")}


def home(country: str) -> str:
    return (country or "").split(" / ")[0].strip()


def _pos(v) -> float | None:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return math.log10(v) if v > 0 else None


def values(r: dict, yt: dict | None = None) -> dict[str, float]:
    """The sources' readings on a log10 scale; a source with no reading (no page, no article, zero) is left out."""
    out = {"fans": _pos(r.get("fans")), "rank": _pos(r.get("rank_sum")), "wiki": _pos(r.get("wiki_3m")),
           "lb": _pos(r.get("lb_users")), "yt": _pos((yt or {}).get(r.get("spotify_id") or "", ""))}
    return {k: v for k, v in out.items() if v is not None}


def fit(cal: list[dict]) -> dict:
    """{signal: {"d", "c": {country: c}, "c0", "err", "n"}} from rows {"y": log10 listeners, "country", "x": {sig: v}}."""
    model = {}
    for s in SIGNALS:
        pts = [(r["country"], r["y"], r["x"][s]) for r in cal if s in r["x"]]
        if len(pts) < 20:
            continue
        by: dict[str, list] = {}
        for c, y, x in pts:
            by.setdefault(c, []).append((y, x))
        mean = {c: (sum(y for y, _ in v) / len(v), sum(x for _, x in v) / len(v)) for c, v in by.items()}
        sxy = sum((y - mean[c][0]) * (x - mean[c][1]) for c, y, x in pts)
        syy = sum((y - mean[c][0]) ** 2 for c, y, x in pts)
        if not syy:
            continue
        d = sxy / syy  # within-country slope of the source on listeners
        if d < MIN_SLOPE:
            continue
        ybar, xbar = sum(p[1] for p in pts) / len(pts), sum(p[2] for p in pts) / len(pts)
        c0 = xbar - d * ybar
        cc = {c: (len(v) * (mean[c][1] - d * mean[c][0]) + K * c0) / (len(v) + K) for c, v in by.items()}
        # weight: the source's rank agreement with listeners within countries (8+ artists), pooled; err is the
        # matching noise-to-signal, sqrt((1 - r^2) / r^2). Tested against 1 / residual variance: this orders the
        # held-out artists better (Spearman 0.69 against 0.65 for hip-hop, 2026-10-26), since Deezer's rank is
        # monotonic with listeners but not linear in log terms
        num = den = 0
        for c, v in by.items():
            if len(v) >= VALID_N and (rho := spearman([x for _, x in v], [y for y, _ in v])) is not None:
                num, den = num + rho * len(v), den + len(v)
        r = min(0.95, max(0.05, num / den if den else 0.05))
        model[s] = {"d": d, "c": cc, "c0": c0, "err": math.sqrt((1 - r * r) / (r * r)), "rho": round(r, 3), "n": len(pts)}
    return model


def _wmedian(pairs: list[tuple[float, float]]) -> float:
    pairs = sorted(pairs)
    half, acc = sum(w for _, w in pairs) / 2, 0.0
    for i, (v, w) in enumerate(pairs):
        acc += w
        if abs(acc - half) < 1e-9 * half and i + 1 < len(pairs):
            return (v + pairs[i + 1][0]) / 2  # exactly half the weight on each side
        if acc >= half:
            return v
    return pairs[-1][0]


def estimate(x: dict[str, float], country: str, model: dict) -> dict | None:
    """{"y": combined log10 listeners, "each": {sig: y}, "agree", "n", "spread", "disagree"}; None with no source."""
    each = {s: (v - model[s]["c"].get(country, model[s]["c0"])) / model[s]["d"] for s, v in x.items() if s in model}
    if not each:
        return None
    w = {s: 1 / model[s]["err"] ** 2 for s in each}
    if len(w) > 1:  # no source above half the weight: only the largest can exceed it, capped at the others' sum
        big = max(w, key=w.get)
        w[big] = min(w[big], MAX_SHARE / (1 - MAX_SHARE) * (sum(w.values()) - w[big]))
    m = _wmedian([(each[s], w[s]) for s in each])
    y = sum(w[s] * min(max(each[s], m - CLIP), m + CLIP) for s in each) / sum(w.values())
    spread = max(each.values()) - min(each.values())
    agree = sum(1 for v in each.values() if abs(v - y) <= AGREE)
    return {"y": y, "each": each, "n": len(each), "agree": agree,
            "spread": spread, "disagree": len(each) > 1 and 2 * agree < len(each)}


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3:
        return None

    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return round(num / den, 3) if den else None


def calibration_rows(genre: str, yt: dict | None = None) -> list[dict]:
    out = []
    for r in src.load_calibration():
        if r["genre"] == genre and r.get("ml"):
            out.append({"id": r["spotify_id"], "name": r["name"], "country": home(r["country"]),
                        "y": math.log10(float(r["ml"])), "x": values(r, yt)})
    return out


def validate(cal: list[dict], folds: int = 10, seed: int = 7) -> dict:
    """10-fold hold-out: each artist estimated by a model fitted without its fold. Per country (8+ artists with an
    estimate) and overall: the Spearman of the estimate with true listeners, per source the Spearman of its raw
    reading, and the median miss in listeners (x times)."""
    idx = list(range(len(cal)))
    random.Random(seed).shuffle(idx)
    est: dict[int, float] = {}
    for f in range(folds):
        test = set(idx[f::folds])
        model = fit([r for i, r in enumerate(cal) if i not in test])
        for i in test:
            e = estimate(cal[i]["x"], cal[i]["country"], model)
            if e:
                est[i] = e["y"]
    by: dict[str, list[int]] = {}
    for i in est:
        by.setdefault(cal[i]["country"], []).append(i)

    def stats(ids):
        out = {"n": len(ids), "rho": spearman([est[i] for i in ids], [cal[i]["y"] for i in ids]),
               "miss": round(10 ** sorted(abs(est[i] - cal[i]["y"]) for i in ids)[len(ids) // 2], 1) if ids else None}
        for s in SIGNALS:
            pts = [(cal[i]["x"][s], cal[i]["y"]) for i in ids if s in cal[i]["x"]]
            out[s] = {"n": len(pts), "rho": spearman([p[0] for p in pts], [p[1] for p in pts]) if len(pts) >= VALID_N else None}
        return out
    return {"all": stats(list(est)), "countries": {c: stats(v) for c, v in by.items() if len(v) >= 3},
            "calibration": len(cal)}


def chart_presence(rows: list[dict], registry_names: set[str]) -> dict[str, dict]:
    """key -> {"spotify": best position, "apple": best, "shazam": best} in the artist's home country (key: the row's
    QID). Spotify: the latest archived weekly top 200 per country (kworb pages, by Spotify ID). Apple Music (last 7
    days) and Shazam (archived days) by exact folded name, only when no registry artist or other smaller act shares
    the name."""
    import glob
    import gzip
    from .collectors import kworb_countries, shazam
    from .collectors.apple_charts import CSV as APPLE, fold, split_names
    from .config import RAW
    from .countries import ISO2
    out: dict[str, dict] = {}
    cc_of = {r["qid"]: ISO2.get(home(r["country"]), "") for r in rows}
    by_sp = {r["spotify_id"]: r["qid"] for r in rows if r.get("spotify_id")}
    names: dict[str, list[str]] = {}
    for r in rows:
        names.setdefault(fold(r["name"]), []).append(r["qid"])
    names = {k: v[0] for k, v in names.items() if len(v) == 1 and k and k not in registry_names}
    weeks = sorted(glob.glob(str(RAW / "kworb" / "country" / "*")))
    if weeks:
        for p in glob.glob(weeks[-1] + "/*.html.gz"):
            cc = p.split("/")[-1].split(".")[0]
            with gzip.open(p, "rt") as f:
                _w, data = kworb_countries.parse(f.read())
            for sp, (_streams, _songs, pos) in data.items():
                q = by_sp.get(sp)
                if q and cc_of[q] == cc:
                    d = out.setdefault(q, {})
                    d["spotify"] = min(d.get("spotify", 999), pos)
    if APPLE.exists():
        with APPLE.open() as f:
            ap = list(csv.DictReader(f))
        days = sorted({r["date"] for r in ap})[-7:]
        for r in ap:
            if r["date"] in days:
                for nm in split_names(r["artist_name"]):
                    q = names.get(fold(nm))
                    if q and cc_of[q] == r["country"]:
                        d = out.setdefault(q, {})
                        d["apple"] = min(d.get("apple", 999), int(r["position"]))
    country_slug = {v: k for k, v in ISO2.items()}
    base = RAW / "shazam"
    if base.exists():
        for day in sorted(p for p in base.iterdir() if p.is_dir()):
            for p in day.glob("*.csv.gz"):
                kind, place = p.name.split("-", 1)[0], p.name.split("-", 1)[1][:-7]
                with gzip.open(p, "rt", encoding="utf-8-sig") as f:
                    rws = shazam.parse(f.read())
                for r in rws:
                    for nm in shazam.split_artists(r["artist"], set(names) | registry_names):
                        q = names.get(fold(nm))
                        if not q:
                            continue
                        c = country_slug.get(cc_of[q], "").lower().replace(" ", "-")
                        if c and place.startswith(c):
                            d = out.setdefault(q, {})
                            d["shazam"] = min(d.get("shazam", 999), int(r["rank"]))
    return out


def _pct(vals: dict[str, float]) -> dict[str, int]:
    """Mid-rank percentiles (ties share a value), as insights.scout."""
    from bisect import bisect_right
    s = sorted(vals.values())
    if len(s) < 2:
        return {}
    return {k: round(100 * ((bisect_right(s, v - 1e-12) + bisect_right(s, v)) / 2) / len(s)) for k, v in vals.items()}


def rank(genre: str, today: date | None = None) -> dict:
    """{"model": per-source fit summary, "validation", "rows": [scored smaller acts]} for the genre."""
    from .collectors import youtube_api
    from .run import load_artists
    today = today or date.today()
    yt = {r["spotify_id"]: r.get("subscribers") for r in youtube_api.load().values()} if hasattr(youtube_api, "load") else {}
    cal = calibration_rows(genre, yt)
    model = fit(cal)
    val = validate(cal)
    # as site_build.below_floor: no release in RECENT_YEARS years is a past act (reissues), not a smaller act to watch
    cutoff = date(today.year - RECENT_YEARS, today.month, min(today.day, 28)).isoformat()
    rows = [r for r in src.load() if r["genre"] == genre and r["decision"] == "include" and (r.get("latest") or "") >= cutoff]
    from .collectors.apple_charts import fold
    charts = chart_presence(rows, {fold(a["name"]) for a in load_artists().values()})
    growth = src.fan_growth()
    est, comp = {}, {k: {} for k in SCORE}
    for r in rows:
        e = estimate(values(r, yt), home(r["country"]), model)
        if not e:
            continue
        est[r["qid"]] = e
        comp["size"][r["qid"]] = e["y"]
        if int(r.get("dated_n") or 0) >= 3:
            comp["fresh"][r["qid"]] = int(r["fresh_n"]) / int(r["dated_n"])
        comp["charts"][r["qid"]] = len(charts.get(r["qid"], {}))
        if r.get("wiki_prev3m") and int(r["wiki_prev3m"]) >= 30:
            comp["attention"][r["qid"]] = int(r["wiki_3m"]) / int(r["wiki_prev3m"]) - 1
        if r.get("deezer_id") in growth:
            comp["growth"][r["qid"]] = growth[r["deezer_id"]]
    pct = {k: _pct(v) for k, v in comp.items()}
    out = []
    for r in rows:
        q = r["qid"]
        if q not in est:
            continue
        p = {k: pct[k][q] for k in SCORE if q in pct[k]}
        if len(p) < 2:
            continue
        w = sum(SCORE[k][0] for k in p)
        e = est[q]
        out.append({"qid": q, "name": r["name"], "country": r["country"], "sp": r["spotify_id"] or None,
                    "dz": r["deezer_id"] or None, "score": round(sum(SCORE[k][0] * v for k, v in p.items()) / w),
                    "parts": p, "sources": e["n"], "agree": e["agree"], "disagree": e["disagree"],
                    "size_pct": p["size"], "fans": int(r["fans"]) if r.get("fans") else None,
                    "wiki": int(r["wiki_3m"]) if r.get("wiki_3m") else None, "fresh": comp["fresh"].get(q),
                    "fresh_title": r.get("fresh_title") or None, "charts": charts.get(q) or None,
                    "latest": r.get("latest") or None, "growth": comp["growth"].get(q),
                    "yt": bool(r.get("youtube_channel")), "used": sorted(e["each"])})
    return {"model": {s: {"n": m["n"], "slope": round(m["d"], 3), "rho": m["rho"]} for s, m in model.items()},
            "validation": val, "rows": out, "growth_ready": bool(growth), "yt_ready": bool(yt)}
