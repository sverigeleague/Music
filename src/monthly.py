"""This month (ROADMAP 8.5): what changed over the last 30 days, for the "This month" page and the monthly summary.

- Movers: monthly listeners now against the snapshot nearest 30 days ago (within a week). Our daily snapshots began
  on 2026-10-23; before 30 of them exist, only the artists in the Wayback copies of kworb's listeners page (about
  300 of the 1,000) have a month-ago value.
- New on Scout's list: tier now against the first day of the window in our daily Scout log (data/scout_history.csv),
  shown only once the log covers MIN_LOG days (the score's method changed in its first days).
- Unsigned prospects: self-released artists with a Breaking or Rising tier, else the best-scored unsigned.
- Label shares: monthly listeners of the 1,000 by label status, at the window's start (Scout log) and now. Both use
  today's label status, so a share moves only with listening, not with our relabelling.
Every list says the dates it compares; while the log is younger than 30 days the window is shorter, and the page says
so.
"""
import csv
from datetime import date, timedelta

from .config import DATA

WINDOW, NEAR, MIN_LOG = 30, 7, 28
SCOUT_LOG = DATA / "scout_history.csv"


def _at(series: list[tuple[str, int]], target: date) -> tuple[str, int] | None:
    best = min(series, key=lambda x: abs((date.fromisoformat(x[0]) - target).days), default=None)
    return best if best and abs((date.fromisoformat(best[0]) - target).days) <= NEAR else None


def build(rows: list[dict], history: dict[str, list[tuple[str, int]]], today: str, n: int = 10) -> dict:
    t = date.fromisoformat(today)
    moves = []
    for r in rows:
        then = _at(history.get(r["id"], []), t - timedelta(days=WINDOW))
        if then and then[1] and r.get("ml"):
            moves.append({"id": r["id"], "from": then[0], "then": then[1], "now": r["ml"],
                          "change": r["ml"] - then[1], "pct": round(100 * (r["ml"] / then[1] - 1), 2)})
    log = []
    if SCOUT_LOG.exists():
        with SCOUT_LOG.open() as f:
            log = list(csv.DictReader(f))
    start = min((x["date"] for x in log if x["date"] >= (t - timedelta(days=WINDOW)).isoformat()), default=None)
    first = {x["spotify_id"]: x for x in log if x["date"] == start}
    if start and (t - date.fromisoformat(start)).days < MIN_LOG:
        first, start = {}, None  # too short to tell a change from a method change
    tier = lambda r: (r.get("scout") or {}).get("tier")
    new = {k: [r["id"] for r in rows if tier(r) == k and start and first.get(r["id"], {}).get("tier") != k]
           for k in ("Breaking", "Rising")}
    unsigned = sorted((r for r in rows if r.get("label_status") == "self_released" and r.get("indie_kind") != "established" and r.get("scout")),
                      key=lambda r: -r["scout"]["score"])
    prospects = [r["id"] for r in unsigned if tier(r) in ("Breaking", "Rising")] or [r["id"] for r in unsigned[:n]]
    share = lambda pairs: {k: sum(v for s, v in pairs if s == k) / max(1, sum(v for _, v in pairs))
                           for k in {s for s, _ in pairs}}
    status = {r["id"]: r.get("label_status") or "unknown" for r in rows}
    shares_then = share([(status[k], int(x["monthly_listeners"] or 0)) for k, x in first.items() if k in status])
    shares_now = share([(r.get("label_status") or "unknown", r.get("ml") or 0) for r in rows])
    moves.sort(key=lambda m: -m["pct"])
    return {"today": today, "movers_from": min((m["from"] for m in moves), default=None), "movers_n": len(moves),
            "up": moves[:n], "down": moves[::-1][:n], "biggest_gain": sorted(moves, key=lambda m: -m["change"])[:n],
            "log_start": start, "log_from": min((x["date"] for x in log), default=None), "min_log": MIN_LOG, "new_breaking": new["Breaking"], "new_rising": new["Rising"],
            "prospects": prospects[:15],
            "shares": [{"status": k, "then": round(shares_then.get(k, 0), 4) if shares_then else None, "now": round(v, 4)}
                       for k, v in sorted(shares_now.items(), key=lambda x: -x[1])]}
