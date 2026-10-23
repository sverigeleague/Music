"""Wikipedia attention: monthly page views of each artist's English Wikipedia article (Wikimedia REST API, free,
no key; the API asks for a User-Agent with contact details). Saved to data/wikipedia_pageviews.csv.

The article is the one Wikidata links to the artist's item (sitelink), so no name matching is involved. Views count
people only (agent=user), every device. Monthly totals, the last MONTHS full months.
"""
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import quote

from ..config import DATA
from ..http import get
from .wikidata import query

API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
CSV = DATA / "wikipedia_pageviews.csv"
FIELDS = ["spotify_id", "qid", "article", "month", "views"]
MONTHS = 24


def articles(qids: dict[str, str]) -> dict[str, str]:
    """spotify_id -> English Wikipedia article title, from Wikidata sitelinks."""
    by_qid = {q: s for s, q in qids.items() if q}
    out = {}
    keys = list(by_qid)
    for chunk in [keys[i:i + 400] for i in range(0, len(keys), 400)]:
        for r in query(f"""
SELECT ?item ?title WHERE {{ VALUES ?item {{ {' '.join('wd:' + q for q in chunk)} }}
  ?a schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title . }}"""):
            out[by_qid[r["item"].rsplit("/", 1)[-1]]] = r["title"]
    return out


def month_range(today: date, months: int = MONTHS) -> tuple[str, str]:
    """First day of the month `months` full months ago, and the first day of the current month."""
    y, m = today.year, today.month - months
    while m <= 0:
        y, m = y - 1, m + 12
    return f"{y}{m:02d}0100", f"{today.year}{today.month:02d}0100"


def views(title: str, start: str, end: str) -> list[tuple[str, int]] | None:
    """Monthly views, or None when the API refused (throttled) so the artist is tried again next run."""
    r = get(f"{API}/{quote(title.replace(' ', '_'), safe='')}/monthly/{start}/{end}")
    if r.status_code == 404:
        return []  # no views recorded
    if r.status_code != 200:
        return None
    return [(i["timestamp"][:4] + "-" + i["timestamp"][4:6], i["views"]) for i in r.json().get("items", [])]


def update(qids: dict[str, str], today: date | None = None, workers: int = 1) -> int:
    """Fetch the artists (spotify_id -> QID) not yet up to the last full month; saves every 25 artists, so a run cut
    short by throttling keeps what it got. Returns the number of artists with an English article."""
    today = today or date.today()
    start, end = month_range(today)
    last_month = month_range(today, 1)[0][:4] + "-" + month_range(today, 1)[0][4:6]
    have = load()
    titles = articles(qids)
    todo = [s for s in titles if not have.get(s) or have[s][-1][0] < last_month]
    got: dict[str, list] = {}

    def save():
        rows = {**have, **got}
        with CSV.open("w", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            for s in sorted(rows):
                for month, n in rows[s]:
                    w.writerow({"spotify_id": s, "qid": qids.get(s, ""), "article": titles.get(s, ""), "month": month,
                                "views": n})

    with ThreadPoolExecutor(workers) as pool:
        for i, (s, v) in enumerate(pool.map(lambda s: (s, views(titles[s], start, end)), todo), 1):
            if v:
                got[s] = v
            if i % 25 == 0:
                save()
    save()
    return len(titles)


def load() -> dict[str, list[tuple[str, int]]]:
    """spotify_id -> [(YYYY-MM, views)], oldest first."""
    out: dict[str, list] = {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                out.setdefault(r["spotify_id"], []).append((r["month"], int(r["views"])))
    for v in out.values():
        v.sort()
    return out
