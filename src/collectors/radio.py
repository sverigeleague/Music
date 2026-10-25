"""US radio airplay audience per song, from kworb.net/radio: each song's US AM/FM audience in millions over the last
7 days (it matches Luminate's weekly Radio Songs impressions; docs/research/research_country_rates.md), updated daily.
Owner, 2026-10-24 (C4): an internal scoring signal for country (radio is the genre's biggest audience outside streaming); our own derived ranks may be shown, kworb's figures are not reproduced
until the owner has asked. Daily page and the archived days (kworb.net/radio/archives/YYYYMMDD.html) are stored raw.
Saved to data/radio.csv: date, pos, artist_raw, title, days, peak, aud (millions), aud_change, formats.
"""
import csv
import html as htmllib
import re

from .. import storage
from ..config import DATA
from ..http import get

URL = "https://kworb.net/radio/"
ARCHIVE = "https://kworb.net/radio/archives/{ymd}.html"
CSV = DATA / "radio.csv"
FIELDS = ["date", "pos", "artist_raw", "title", "days", "peak", "aud", "aud_change", "formats"]
_num = lambda s: float(s) if re.fullmatch(r"[+-]?\d+(\.\d+)?", s or "") else None


def parse(page: str) -> list[dict]:
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cells = [htmllib.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 10 or not cells[0].isdigit():
            continue
        artist, _, title = cells[2].partition(" - ")
        out.append({"pos": int(cells[0]), "artist_raw": artist.strip(), "title": title.strip(), "days": cells[3],
                    "peak": cells[4], "aud": _num(cells[6]), "aud_change": _num(cells[7]), "formats": cells[8]})
    return out


def update(day: str, archive_days: list[str] | None = None) -> int:
    """Today's page, plus any archived days given (YYYY-MM-DD) not yet stored."""
    have = set()
    if CSV.exists():
        with CSV.open() as f:
            have = {r["date"] for r in csv.DictReader(f)}
    jobs = [(day, URL)] if day not in have else []
    jobs += [(d, ARCHIVE.format(ymd=d.replace("-", ""))) for d in (archive_days or []) if d not in have and d != day]
    new = not CSV.exists()
    n = 0
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for d, url in jobs:
            r = get(url)
            if r.status_code != 200:
                continue
            storage.archive(f"kworb/radio/{d}.html", url, r.content)
            for x in parse(r.content.decode("utf-8", "replace")):
                w.writerow({"date": d, **x})
                n += 1
    return n


def presence(names: dict[str, str], day: str | None = None) -> dict[str, dict]:
    """Latest day's radio presence per spotify_id: {songs, aud (sum, millions), best_pos}. names: spotify_id -> name."""
    from .apple_charts import fold, split_names
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        rows = list(csv.DictReader(f))
    day = day or max((r["date"] for r in rows), default=None)
    by_fold: dict[str, list[str]] = {}
    for sid, n in names.items():
        by_fold.setdefault(fold(n), []).append(sid)
    out: dict[str, dict] = {}
    for r in rows:
        if r["date"] != day:
            continue
        credited = split_names(r["artist_raw"]) + [a or b for a, b in re.findall(
            r"\((?:feat\.|ft\.|with) ([^)]+)\)|\bf/\s*(.+)$", r["title"], re.I)]  # "Move On f/Shaboozey"
        for name in credited:
            sids = by_fold.get(fold(name), [])
            if len(sids) != 1:
                continue
            o = out.setdefault(sids[0], {"songs": 0, "aud": 0.0, "best_pos": 999})
            o["songs"] += 1
            o["aud"] += float(r["aud"] or 0)
            o["best_pos"] = min(o["best_pos"], int(r["pos"]))
    return out
