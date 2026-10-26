"""State of hip-hop (owner, 2026-10-24, D5): a dated monthly page of quotable headline numbers, each with a citation.

Each build writes the current month's numbers to data/state/<YYYY-MM>.json (committed by the data workflows), so a
month keeps its permanent address and its figures once it ends; the current month refreshes until then. The site
shows every stored month at #/state/<YYYY-MM> and as a static page, site/state/<YYYY-MM>/.
"""
import json
from datetime import date

from . import insights
from .config import DATA

DIR = DATA / "state"
MAJORS = ("Universal Music Group", "Sony Music", "Warner Music Group")


def _pct(x: float) -> str:
    return f"{round(100 * x)}%"


def _count(n) -> str:
    n = float(n or 0)
    return f"{n / 1e9:.2f}bn" if n >= 1e9 else f"{n / 1e6:.1f}m" if n >= 1e6 else f"{n / 1e3:.0f}k"


def build(data: dict, extra: dict) -> dict:
    A = data["artists"]
    word = "country" if data.get("genre") == "country" else "hip-hop"
    by = {a["id"]: a for a in A}
    as_of = data.get("as_of") or ""
    m = extra.get("market") or {}
    groups = m.get("groups", {})
    # among artists whose label is known, as on the Labels page (catalog acts are already left out of the market)
    known = {g: v for g, v in groups.items() if g != "Not yet known"}
    total = sum(v.get("ml", 0) for v in known.values()) or 1
    major_ml = sum(groups.get(g, {}).get("ml", 0) for g in MAJORS)
    items = [{"key": "majors", "label": f"Majors' share of the top {len(A):,}'s listeners",
              "value": _pct(major_ml / total),
              "detail": f"Universal, Sony and Warner, by monthly listeners added per artist, among the {sum(v.get('artists', 0) for v in known.values()):,} of {len(A):,} artists whose label is known (catalog acts left out)",
              "link": "#/labels"}]
    ranked = sorted((a for a in A if a.get("cl_rank")), key=lambda a: a["cl_rank"])
    if ranked:
        a = ranked[0]
        items.append({"key": "top", "label": "No. 1 by current listeners", "value": a["name"],
                      "detail": f"{_count(a['cl'])} current listeners, {_count(a['ml'])} monthly", "link": f"#/a/{a['id']}"})
    up = ((extra.get("month") or {}).get("up") or [None])[0]
    if up and up["id"] in by:
        days = (date.fromisoformat(as_of) - date.fromisoformat(up["from"])).days if as_of and up.get("from") else None
        items.append({"key": "mover", "label": "Biggest riser over about a month", "value": by[up["id"]]["name"],
                      "detail": f"+{up['pct']:.0f}% monthly listeners, {_count(up['then'])} to {_count(up['now'])} since {up['from']}{f' ({days} days)' if days else ''}",
                      "link": f"#/a/{up['id']}"})
    tiers = {t: [a for a in A if (a.get("scout") or {}).get("tier") == t] for t in ("Breaking", "Rising")}
    if tiers["Breaking"]:
        best = max(tiers["Breaking"], key=lambda a: a["scout"]["score"])
        items.append({"key": "breaking", "label": "Breaking now", "value": str(len(tiers["Breaking"])),
                      "detail": f"artists Scout rates Breaking; top: {best['name']} ({best['scout']['score']})", "link": "#/scout"})
    # an unsigned prospect, not mostly a featured guest (insights.is_pick)
    unsigned = sorted((a for a in A if insights.is_pick(a) and a.get("scout")), key=lambda a: -a["scout"]["score"])
    if unsigned:
        u = unsigned[0]
        items.append({"key": "unsigned", "label": "Top unsigned prospect", "value": u["name"],
                      "detail": f"Scout {u['scout']['score']}, {'under 500k' if u.get('floor') else _count(u['ml'])} monthly listeners, releasing without a label", "link": f"#/a/{u['id']}"})
    top100 = ranked[:100]
    # the yearly Spotify line, as the Platforms page adds it up (site_build keeps that line unrounded for this)
    gen = sum((a.get("rev_lines") or {}).get("spotify") or (a.get("money") or {}).get("generated", {}).get("mid", 0) * 12 for a in top100)
    if gen:
        items.append({"key": "royalties", "label": "What the top 100 earn on Spotify", "value": f"${_count(gen)} a year",
                      "detail": "royalties paid to the rights holders for their own songs, mid estimate (grade C)", "link": "#/worth"})
    prod = ((extra.get("credits") or {}).get("producers") or [None])[0]
    if prod:
        items.append({"key": "producer", "label": "Producer behind the most streams", "value": prod["name"],
                      "detail": f"credited on songs with {_count(prod['daily'])} Spotify streams a day (credits partial)", "link": "#/producers"})
    shz = max((a for a in A if a.get("shazam")), key=lambda a: a["shazam"]["charts"], default=None)
    if shz:
        items.append({"key": "shazam", "label": f"Most Shazamed {word} artist", "value": shz["name"],
                      "detail": f"on {shz['shazam']['charts']} Shazam charts in the last 7 days", "link": f"#/a/{shz['id']}"})
    items.append({"key": "size", "label": f"{word.capitalize()} artists tracked", "value": f"{len(A):,}",
                  "detail": f"{_count(sum(a['ml'] or 0 for a in A if not a.get('second_of')))} combined monthly listeners (second Spotify profiles left out), from Spotify's top {data.get('universe', 0):,}", "link": "#/"})
    return {"month": as_of[:7], "as_of": as_of, "items": items}


def update(data: dict, extra: dict) -> list[dict]:
    """Saves this month's state and returns every stored month, newest first. Country (since 2026-10-24) is kept in
    data/state/country/."""
    d = DIR if data.get("genre", "hip_hop") == "hip_hop" else DIR / data["genre"]
    d.mkdir(parents=True, exist_ok=True)
    cur = build(data, extra)
    if cur["month"]:
        (d / f"{cur['month']}.json").write_text(json.dumps(cur, ensure_ascii=False, indent=1))
    return [json.loads(p.read_text()) for p in sorted(d.glob("*.json"), reverse=True)]
