"""Shazam: the daily chart CSVs (world, countries, hip-hop genre, cities) as an INTERNAL Scout signal.

Owner decision K3 (2026-10-24): the site shows only a badge linking to Shazam's chart page, never Shazam's chart
tables. Shazam publishes no reuse licence for these CSVs; they are a public download (robots allow /services/charts).
One request every 2 s, once a day; each CSV is archived raw (raw/shazam/<day>/...csv.gz) and reused on a re-run.

Each CSV: a BOM/blank line, a title line ("Saturday, 24 October 2026 [performance over the past 7 days]"), then
"Rank,Artist,Title". Artists come as "A, B & C"; featured artists sit in the title ("Song (feat. X)"). Names are
matched to registry/artists.csv by their folded name (apple_charts.fold); a name shared by two artists is skipped.
Slugs come from https://www.shazam.com/services/charts/locations (checked 2026-10-24); a city or country genre chart
that Shazam does not have returns 404 (e.g. no hip-hop chart for Nigeria).
"""
import csv
import io
import re
from datetime import date, timedelta
from urllib.parse import quote

from .. import http, storage
from ..config import DATA, REGISTRY
from .apple_charts import fold

http.PAUSE.setdefault("www.shazam.com", 2.0)

BASE = "https://www.shazam.com/services/charts/csv/"
PAGE = "https://www.shazam.com/charts/"
CSV = DATA / "shazam.csv"
FIELDS = ["date", "chart_kind", "place", "rank", "artist_raw", "title", "spotify_id"]

COUNTRIES = ("united-states", "united-kingdom", "france", "germany", "canada", "nigeria", "south-africa", "brazil",
             "netherlands", "sweden", "australia", "spain", "italy", "japan", "ghana")
HIPHOP_COUNTRIES = ("united-states", "united-kingdom", "france", "germany", "canada", "south-africa", "brazil",
                    "australia", "spain", "italy")  # the countries Shazam has a hip-hop-rap chart for
CITIES = (("united-states", c) for c in ("atlanta", "new-york-city", "los-angeles", "chicago", "houston", "miami",
                                         "detroit", "memphis", "philadelphia", "new-orleans", "dallas",
                                         "washington-d.c.", "baltimore", "st.-louis", "charlotte", "san-francisco"))
CITIES = (*CITIES, ("united-kingdom", "london"), ("united-kingdom", "manchester"), ("united-kingdom", "birmingham"),
          ("france", "paris"), ("france", "marseille"), ("france", "lyon"), ("germany", "berlin"),
          ("germany", "hamburg"), ("canada", "toronto"), ("canada", "montréal"), ("nigeria", "lagos"),
          ("south-africa", "johannesburg"), ("brazil", "são-paulo"), ("netherlands", "amsterdam"),
          ("sweden", "stockholm"))


def _path(kind: str, place: str) -> str:
    """URL path of a chart (shared by the CSV and the chart page): top-200/world, genre/x/hip-hop-rap, top-50/x/y."""
    if kind == "top":
        return f"top-200/{quote(place)}"
    if kind == "hiphop":
        return f"genre/{quote(place)}/hip-hop-rap"
    return f"top-50/{quote(place)}"  # city: place is "<country>/<city>"


def page_url(kind: str, place: str) -> str:
    """Shazam's own chart page (the badge's link)."""
    return PAGE + _path(kind, place)


CHARTS: list[tuple[str, str, str]] = (
    [("top", "world", BASE + _path("top", "world")), ("hiphop", "world", BASE + _path("hiphop", "world"))]
    + [("top", c, BASE + _path("top", c)) for c in COUNTRIES]
    + [("hiphop", c, BASE + _path("hiphop", c)) for c in HIPHOP_COUNTRIES]
    + [("city", f"{c}/{t}", BASE + _path("city", f"{c}/{t}")) for c, t in CITIES])


def _raw_path(day: str, kind: str, place: str) -> str:
    return f"shazam/{day}/{kind}-{place.replace('/', '-')}.csv"


def fetch_all(day: str) -> tuple[dict[tuple[str, str], str], list[tuple[str, str, int]]]:
    """Every chart's CSV text for `day` (archived raw; an archived copy is reused) and the failures (kind, place, status)."""
    out, failed = {}, []
    for kind, place, url in CHARTS:
        rel = _raw_path(day, kind, place)
        if (storage.RAW / (rel + ".gz")).exists():
            out[(kind, place)] = storage.read(rel).decode("utf-8-sig")
            continue
        try:
            r = http.get(url, tries=2)
        except Exception:  # network error after retries
            failed.append((kind, place, 0))
            continue
        if r.status_code != 200 or b"Rank," not in r.content[:400]:
            failed.append((kind, place, r.status_code))
            continue
        storage.archive(rel, url, r.content)
        out[(kind, place)] = r.content.decode("utf-8-sig")
    return out, failed


def parse(csv_text: str) -> list[dict]:
    """Rows of one chart CSV: [{rank, artist, title}]; the title lines before "Rank,Artist,Title" are skipped."""
    lines = csv_text.lstrip("﻿").splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip().lower().startswith("rank,")), None)
    if start is None:
        return []
    rows = []
    for r in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        try:
            rank = int(r.get("Rank") or "")
        except ValueError:
            continue
        rows.append({"rank": rank, "artist": (r.get("Artist") or "").strip(), "title": (r.get("Title") or "").strip()})
    return rows


_SEP = re.compile(r"(\s*,\s*|\s+&\s+|\s+(?:feat\.?|ft\.?|featuring|with|x|×|X)\s+)", re.IGNORECASE)
_FEAT = re.compile(r"[(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+([^)\]]+)[)\]]", re.IGNORECASE)
_names: dict[str, list[str]] | None = None


def registry_names() -> dict[str, list[str]]:
    """Folded registry name -> spotify_ids (cached)."""
    global _names
    if _names is None:
        _names = {}
        with (REGISTRY / "artists.csv").open() as f:
            for a in csv.DictReader(f):
                _names.setdefault(fold(a["name"]), []).append(a["spotify_id"])
    return _names


def split_artists(s: str, known=None) -> list[str]:
    """'A, B & C' / 'A feat. B' / 'A x B' -> names. Runs of pieces that together form a known name stay whole
    ('Tyler, The Creator', 'Earth, Wind & Fire'); known: folded names (default: registry/artists.csv)."""
    known = registry_names() if known is None else known
    s = s.strip()
    if not s:
        return []
    if fold(s) in known:
        return [s]
    pieces = _SEP.split(s)  # name, sep, name, sep, name...
    names, seps = pieces[0::2], pieces[1::2]
    out, i = [], 0
    while i < len(names):
        best = i  # longest run names[i..j] whose joined text is a known name
        for j in range(len(names) - 1, i, -1):
            if fold("".join(p for k in range(i, j + 1) for p in (names[k], seps[k] if k < j else ""))) in known:
                best = j
                break
        text = "".join(p for k in range(i, best + 1) for p in (names[k], seps[k] if k < best else "")).strip()
        if text:
            out.append(text)
        i = best + 1
    return out


def featured(title: str, known=None) -> list[str]:
    """Names in a title's '(feat. X & Y)'."""
    return [n for m in _FEAT.findall(title) for n in split_artists(m, known)]


def match(artist: str, title: str, names=None) -> list[str]:
    """spotify_ids credited on a chart row (main and featured artists); unknown or ambiguous names are skipped."""
    names = registry_names() if names is None else names
    ids = []
    for n in split_artists(artist, names) + featured(title, names):
        hit = names.get(fold(n), [])
        if len(hit) == 1 and hit[0] not in ids:
            ids.append(hit[0])
    return ids


def update(day: str) -> tuple[int, int, list[tuple[str, str, int]]]:
    """Fetch the day's charts and append matched rows to data/shazam.csv (charts already stored for the day are
    skipped). Returns (charts fetched, rows written, failures)."""
    have = set()
    if CSV.exists():
        with CSV.open() as f:
            have = {(r["date"], r["chart_kind"], r["place"]) for r in csv.DictReader(f)}
    texts, failed = fetch_all(day)
    new = not CSV.exists()
    n = 0
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for (kind, place), text in texts.items():
            if (day, kind, place) in have:
                continue
            for r in parse(text):
                for sid in match(r["artist"], r["title"]):
                    w.writerow({"date": day, "chart_kind": kind, "place": place, "rank": r["rank"],
                                "artist_raw": r["artist"], "title": r["title"], "spotify_id": sid})
                    n += 1
    return len(texts), n, failed


_KIND_ORDER = {"top": 0, "hiphop": 1, "city": 2}


def presence(day: str | None = None, days: int = 1) -> dict[str, dict]:
    """Chart presence per spotify_id over `days` days ending on `day` (default: the latest stored day):
    {charts, best: {place, rank, kind}, cities, countries, url (Shazam's page of the best chart)}."""
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        rows = list(csv.DictReader(f))
    day = day or max((r["date"] for r in rows), default=None)
    if not day:
        return {}
    first = (date.fromisoformat(day) - timedelta(days=days - 1)).isoformat()
    acc: dict[str, dict] = {}
    for r in rows:
        if not first <= r["date"] <= day:
            continue
        p = acc.setdefault(r["spotify_id"], {"charts": set(), "best": None, "cities": set(), "countries": set()})
        kind, place, rank = r["chart_kind"], r["place"], int(r["rank"])
        p["charts"].add((kind, place))
        if kind == "city":
            p["cities"].add(place.split("/")[-1])
        elif place != "world":
            p["countries"].add(place)
        key = (rank, place != "world", _KIND_ORDER.get(kind, 9))  # ties: a world chart, then country, then city
        if p["best"] is None or key < p["best"][0]:
            p["best"] = (key, {"place": place, "rank": rank, "kind": kind})
    return {sid: {"charts": len(p["charts"]), "best": p["best"][1], "cities": sorted(p["cities"]),
                  "countries": sorted(p["countries"]), "url": page_url(p["best"][1]["kind"], p["best"][1]["place"])}
            for sid, p in acc.items()}
