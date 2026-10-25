"""Listener history before our own daily snapshots: kworb's listeners page as saved by the Internet Archive's Wayback
Machine, one snapshot a week since SINCE. Saved to data/listener_history.csv for artists in our registry.

web.archive.org is blocked in the build container; this runs in GitHub Actions (workflow "backfill"). The archive asks
for gentle use: one request every PAUSE seconds. Old pages may differ in layout, so the parser only relies on the
artist link and the number right after it; a snapshot it cannot read is skipped and counted.
"""
import csv
import re
from datetime import date

from ..config import DATA
from ..http import get

CDX = "https://web.archive.org/cdx/search/cdx"
PAGE = "https://web.archive.org/web/{ts}id_/https://kworb.net/spotify/listeners.html"
CSV = DATA / "listener_history.csv"
FIELDS = ["date", "spotify_id", "monthly_listeners", "rank", "source"]
SINCE = "20230101"

_int = lambda s: int(re.sub(r"[^\d]", "", s)) if re.search(r"\d", s or "") else None


def snapshots(since: str = SINCE) -> list[str]:
    """Timestamps of archived copies, at most one per ISO week."""
    r = get(CDX, params={"url": "kworb.net/spotify/listeners.html", "output": "json", "fl": "timestamp,statuscode",
                         "filter": "statuscode:200", "from": since, "collapse": "timestamp:8"}, timeout=120)
    if r.status_code != 200:
        return []
    rows = r.json()[1:]
    out, weeks = [], set()
    for ts, _code in rows:
        d = date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
        wk = d.isocalendar()[:2]
        if wk not in weeks:
            weeks.add(wk)
            out.append(ts)
    return out


def parse(html: str) -> list[dict]:
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        for i, c in enumerate(cells):
            m = re.search(r"artist/([0-9A-Za-z]{22})(?:_songs)?\.html", c)
            if m and i + 1 < len(cells):
                out.append({"spotify_id": m[1], "monthly_listeners": _int(re.sub(r"<[^>]+>", "", cells[i + 1])),
                            "rank": _int(re.sub(r"<[^>]+>", "", cells[0])) if i > 0 else None})
                break
    return [r for r in out if r["monthly_listeners"]]


def update(keep: set[str], since: str = SINCE, limit: int | None = None, refetch: bool = False) -> tuple[int, int]:
    """Fetch the weeks not yet stored (every week with refetch, e.g. when a genre is added); keep rows of the given
    Spotify IDs that are not stored for that week yet. Returns (snapshots read, unreadable)."""
    have, stored = set(), set()
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                if r["source"] == "wayback":
                    have.add(r["date"])
                    stored.add((r["date"], r["spotify_id"]))
    todo = [ts for ts in snapshots(since) if refetch or f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" not in have][:limit]
    new = not CSV.exists()
    done = bad = 0
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for ts in todo:
            r = get(PAGE.format(ts=ts), timeout=120)
            rows = parse(r.text) if r.status_code == 200 else []
            if len(rows) < 100:
                bad += 1
                continue
            day = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
            for x in rows:
                if x["spotify_id"] in keep and (day, x["spotify_id"]) not in stored:
                    w.writerow({"date": day, **x, "source": "wayback"})
            f.flush()
            done += 1
    return done, bad


def load() -> dict[str, list[tuple[str, int]]]:
    """spotify_id -> [(date, monthly listeners)], oldest first: the Wayback weeks plus our own daily snapshots."""
    from .kworb import LISTENERS_CSV
    out: dict[str, dict[str, int]] = {}
    for path in (CSV, LISTENERS_CSV):
        if path.exists():
            with path.open() as f:
                for r in csv.DictReader(f):
                    if r.get("monthly_listeners"):
                        out.setdefault(r["spotify_id"], {})[r["date"]] = int(r["monthly_listeners"])
    return {k: sorted(v.items()) for k, v in out.items()}
