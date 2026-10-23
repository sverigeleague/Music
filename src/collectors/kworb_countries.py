"""Where each artist's songs are streamed: kworb.net's weekly Spotify top 200 in 76 countries (Spotify's own weekly
charts, compiled by kworb). Saved to data/spotify_country_charts.csv: week, country, artist, chart streams, songs.

Every artist linked on a chart row (lead and featured) is credited with that song's streams in that country. Only
songs in a country's top 200 count, so this measures where an artist's hits are played; long-tail listening and
countries without a Spotify chart (China, most of Africa) are not covered.
"""
import csv
import re

from .. import storage
from ..config import DATA
from ..http import get

INDEX = "https://kworb.net/spotify/"
PAGE = "https://kworb.net/spotify/country/{cc}_weekly.html"
CSV = DATA / "spotify_country_charts.csv"
FIELDS = ["week", "country", "spotify_id", "streams", "songs", "best_pos"]
_int = lambda s: int(re.sub(r"[^\d]", "", s)) if re.sub(r"[^\d]", "", s) else 0


def countries() -> list[str]:
    r = get(INDEX)
    r.raise_for_status()
    return sorted({cc for cc in re.findall(r'href="country/([a-z]{2})_weekly\.html"', r.text)})


def parse(html: str) -> tuple[str | None, dict[str, list[int]]]:
    """(week ending, {spotify_id: [streams, songs, best position]}) for one country's weekly chart."""
    m = re.search(r"Week ending (\d{4})/(\d{2})/(\d{2})", html) or re.search(r"(\d{4})/(\d{2})/(\d{2})", html)
    week = f"{m[1]}-{m[2]}-{m[3]}" if m else None
    out: dict[str, list[int]] = {}
    for row in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ids = re.findall(r'\.\./artist/([0-9A-Za-z]{22})\.html', row)
        if len(cells) < 6 or not ids:
            continue
        streams, pos = _int(cells[-3]), _int(cells[0])  # columns: position, ..., streams, change, total
        for a in dict.fromkeys(ids):
            out.setdefault(a, [0, 0, 999])
            out[a][0] += streams
            out[a][1] += 1
            out[a][2] = min(out[a][2], pos or 999)
    return week, out


def update(tracked: set[str]) -> tuple[str | None, int]:
    """Fetch every country's latest weekly chart; append rows for tracked artists unless that week is stored."""
    have = set()
    if CSV.exists():
        with CSV.open() as f:
            have = {(r["week"], r["country"]) for r in csv.DictReader(f)}
    new = not CSV.exists()
    n, last_week = 0, None
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for cc in countries():
            r = get(PAGE.format(cc=cc))
            if r.status_code != 200:
                continue
            week, data = parse(r.text)
            if not week or (week, cc) in have:
                continue
            storage.archive(f"kworb/country/{week}/{cc}.html", PAGE.format(cc=cc), r.content)
            last_week = week
            for a, (streams, songs, best) in data.items():
                if a in tracked:
                    w.writerow({"week": week, "country": cc, "spotify_id": a, "streams": streams, "songs": songs,
                                "best_pos": best})
                    n += 1
    return last_week, n


def load_recent(weeks: int = 4) -> tuple[dict[str, dict[str, dict]], dict]:
    """({spotify_id: {country: {streams, best_pos, weeks}}} over each country's last `weeks` stored weeks,
    {"weeks": most weeks any country has, "latest": latest week})."""
    if not CSV.exists():
        return {}, {"weeks": 0, "latest": None}
    rows = list(csv.DictReader(CSV.open()))
    by_country: dict[str, set] = {}
    for r in rows:
        by_country.setdefault(r["country"], set()).add(r["week"])
    keep = {c: set(sorted(w)[-weeks:]) for c, w in by_country.items()}
    out: dict[str, dict[str, dict]] = {}
    for r in rows:
        if r["week"] in keep[r["country"]]:
            d = out.setdefault(r["spotify_id"], {}).setdefault(r["country"], {"streams": 0, "best_pos": 999, "weeks": 0})
            d["streams"] += int(r["streams"])
            d["best_pos"] = min(d["best_pos"], int(r.get("best_pos") or 999))
            d["weeks"] += 1
    return out, {"weeks": max((len(w) for w in keep.values()), default=0),
                 "latest": max((r["week"] for r in rows), default=None)}


def reparse_archived() -> int:
    """Rebuild data/spotify_country_charts.csv from the archived pages (after a parser change), tracked artists only."""
    import glob
    import gzip
    from ..config import RAW
    tracked = {r["spotify_id"] for r in csv.DictReader(CSV.open())} if CSV.exists() else set()
    rows = []
    for p in sorted(glob.glob(str(RAW / "kworb" / "country" / "*" / "*.html.gz"))):
        with gzip.open(p, "rt") as f:
            week, data = parse(f.read())
        cc = p.split("/")[-1].split(".")[0]
        rows += [{"week": week, "country": cc, "spotify_id": a, "streams": v[0], "songs": v[1], "best_pos": v[2]}
                 for a, v in data.items() if a in tracked]
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)
