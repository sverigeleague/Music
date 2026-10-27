"""Official national charts whose terms allow reading (owner 2026-10-27, "yea": "use the official national charts where
their terms allow"). Each site's terms and robots.txt, with the verdict and a link: docs/research/2026-10-27-national-
charts.md. Allowed and read here:
  se  Sverigetopplistan (IFPI Sverige): singles top 100, albums top 60, the hip-hop albums top 20. robots.txt allows
      all; no terms of use restrict reading. Credited "© IFPI Sverige".
  dk  Hitlisten.NU (IFPI Danmark and M&I Service): tracks top 40, albums top 40. No robots.txt, no terms of use.
      Credited "© IFPI Danmark og M&I Service".
  fi  Suomen virallinen lista (IFPI Finland): singles top 50, albums top 50. robots.txt allows all; the chart rules
      (Säännöt 2026, 2.1) say even a partial publication of the list must be agreed with IFPI Finland, so it is an
      internal signal and a discovery source only: no position is shown on the site (SHOW False).
Refused (terms or robots.txt): VG-lista (NO), Dutch Top 40 and Single Top 100 (NL), Ultratop (BE), Ö3 Austria Top 40,
Schweizer Hitparade, Offizielle Deutsche Charts, SNEP, PROMUSICAE, ARIA, Billboard Canadian Hot 100; FIMI not used.

Each weekly page is archived once under raw/national_charts/<cc>-<chart>/<year>-W<week>.html.gz and never fetched
again (a week not yet published has no rows and is not kept). One request every 2 seconds per site. Rows go to
data/national_charts.csv: one row per chart entry (country, chart, year, week, position, artist, title, the site's own
weeks-on-chart and peak where it prints them). Step `natcharts` (daily workflow; only the newest weeks are new).
"""
import csv
import gzip
import html
import re
from datetime import date, timedelta

from ..config import DATA, RAW
from ..http import PAUSE, get

CSV = DATA / "national_charts.csv"
ARCHIVE = RAW / "national_charts"
FIELDS = ["country", "chart", "year", "week", "position", "artist", "title", "weeks", "peak"]
CHARTS = {
    ("se", "singles"): {"url": "https://sverigetopplistan.se/chart/41/?dspy={y}&dspp={w}", "size": 100,
                        "name": "Sverigetopplistan singles", "credit": "© IFPI Sverige", "show": True},
    ("se", "albums"): {"url": "https://sverigetopplistan.se/chart/54/?dspy={y}&dspp={w}", "size": 60,
                       "name": "Sverigetopplistan albums", "credit": "© IFPI Sverige", "show": True},
    ("se", "hiphop"): {"url": "https://sverigetopplistan.se/chart/94/?dspy={y}&dspp={w}", "size": 20,
                       "name": "Sverigetopplistan hip-hop albums", "credit": "© IFPI Sverige", "show": True},
    ("dk", "tracks"): {"url": "https://www.hitlisten.nu/default.asp?w={w}&y={y}&list=t40", "size": 40,
                       "name": "Hitlisten tracks", "credit": "© IFPI Danmark og M&I Service", "show": True},
    ("dk", "albums"): {"url": "https://www.hitlisten.nu/default.asp?w={w}&y={y}&list=a40", "size": 40,
                       "name": "Hitlisten albums", "credit": "© IFPI Danmark og M&I Service", "show": True},
    ("fi", "singles"): {"url": "https://ifpi.fi/lista/singlet/{y}/{w}/", "size": 50,
                        "name": "Suomen virallinen lista singles", "credit": "IFPI Finland", "show": False},
    ("fi", "albums"): {"url": "https://ifpi.fi/lista/albumit/{y}/{w}/", "size": 50,
                       "name": "Suomen virallinen lista albums", "credit": "IFPI Finland", "show": False},
}
WEEKS = 52  # recent history read once: a year of weekly charts
for _h in ("sverigetopplistan.se", "www.hitlisten.nu", "ifpi.fi"):
    PAUSE.setdefault(_h, 2.0)


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse(cc: str, page: str) -> list[dict]:
    """[{position, artist, title, weeks, peak}] from one weekly page ([] when the week has no list yet)."""
    out = []
    if cc == "se":
        for i, b in enumerate(re.split(r'<li class="charts-list__item', page)[1:], 1):
            t = re.search(r'<span class="title-inner">(.*?)</span>', b, re.S) or re.search(r'<h2 class="title"[^>]*>(.*?)</h2>', b, re.S)
            a = re.search(r'<p class="artist[^"]*">(.*?)</p>', b, re.S)
            if t and a:
                out.append({"position": i, "artist": _text(a.group(1)), "title": _text(t.group(1)), "weeks": "", "peak": ""})
    elif cc == "dk":
        for b in page.split('<div id="linien">')[1:]:
            pos = re.search(r'<div id="denneuge(?:ny)?">\s*(\d+)', b)
            a, t = re.search(r'<div id="artistnavn">(.*?)</div>', b, re.S), re.search(r'<div id="titel">(.*?)</div>', b, re.S)
            wk = re.search(r'<div id="ugerialt"[^>]*>\s*<div id="listeikon">4</div>\s*(\d+)', b)
            pk = re.search(r'<div id="peak"[^>]*>\s*<div id="listeikon">5</div>\s*(\d+)', b)
            if pos and a and t:
                out.append({"position": int(pos.group(1)), "artist": _text(a.group(1)), "title": _text(t.group(1)),
                            "weeks": int(wk.group(1)) if wk else "", "peak": int(pk.group(1)) if pk else ""})
    elif cc == "fi":
        for b in page.split('<div class="chart-row">')[1:]:
            pos = re.search(r'<strong class="chart-position">\s*(\d+)', b)
            a, t = re.search(r'<div class="chart-artist">(.*?)</div>', b, re.S), re.search(r'<div class="chart-title">(.*?)</div>', b, re.S)
            wk = re.search(r'<div class="chart-woc"[^>]*>\s*(\d+)', b)
            if pos and a and t:
                out.append({"position": int(pos.group(1)), "artist": _text(a.group(1)), "title": _text(t.group(1)),
                            "weeks": int(wk.group(1)) if wk else "", "peak": ""})
    return out


def names(artist: str) -> list[str]:
    """'A & B', 'A, B', 'A FEAT. B', 'A x B' -> the whole credit, then each name."""
    parts = [x.strip() for x in re.split(r",\s*|\s+&\s+|\s+x\s+|\s+(?:feat\.?|ft\.?|featuring)\s+", artist, flags=re.I) if x.strip()]
    return [artist.strip()] + parts if len(parts) > 1 else parts


def _weeks(today: date, n: int) -> list[tuple[int, int]]:
    return list(dict.fromkeys((today - timedelta(days=7 * i)).isocalendar()[:2] for i in range(n)))


def update(today: date | None = None, weeks: int = WEEKS) -> dict:
    """Fetch each allowed chart's weeks not yet archived (the last `weeks` ISO weeks), then rewrite the CSV from the
    whole archive. Returns {chart: pages fetched}."""
    today = today or date.today()
    got = {}
    for (cc, ch), c in CHARTS.items():
        d = ARCHIVE / f"{cc}-{ch}"
        d.mkdir(parents=True, exist_ok=True)
        n = 0
        for y, w in _weeks(today, weeks):
            p = d / f"{y}-W{w:02d}.html.gz"
            if p.exists():
                continue
            r = get(c["url"].format(y=y, w=w), tries=2, timeout=30)
            n += 1
            if r.status_code == 200 and parse(cc, r.text):
                with gzip.open(p, "wt", encoding="utf-8") as f:
                    f.write(r.text)
        got[f"{cc}-{ch}"] = n
    rows = []
    for (cc, ch) in CHARTS:
        for p in sorted((ARCHIVE / f"{cc}-{ch}").glob("*.html.gz")):
            y, w = p.name[:-8].split("-W")
            with gzip.open(p, "rt", encoding="utf-8") as f:
                rows += [{"country": cc, "chart": ch, "year": int(y), "week": int(w), **r} for r in parse(cc, f.read())]
    with CSV.open("w", newline="") as f:
        wr = csv.DictWriter(f, FIELDS)
        wr.writeheader()
        wr.writerows(rows)
    return got


def load() -> list[dict]:
    if not CSV.exists():
        return []
    with CSV.open() as f:
        return list(csv.DictReader(f))


def runs(rows: list[dict], today: date | None = None, weeks: int = WEEKS) -> dict[tuple[str, str, str], dict]:
    """(country, chart, folded artist name) -> {"peak", "weeks", "last": (year, week), "size"} over the last `weeks`
    ISO weeks. The artist field is split into its credited names (as the Apple Music charts are), so a featured
    guest counts too. Peak and weeks are counted from the archive, not the site's own all-time figures."""
    from .apple_charts import fold
    keep = set(_weeks(today or date.today(), weeks))
    out: dict = {}
    for r in rows:
        yw = (int(r["year"]), int(r["week"]))
        if yw not in keep:
            continue
        for nm in names(r["artist"]):
            k = (r["country"], r["chart"], fold(nm))
            d = out.setdefault(k, {"peak": 999, "weeks": set(), "last": yw, "size": CHARTS[(r["country"], r["chart"])]["size"]})
            d["peak"] = min(d["peak"], int(r["position"]))
            d["weeks"].add(yw)
            d["last"] = max(d["last"], yw)
    for d in out.values():
        d["weeks"] = len(d["weeks"])
    return out
