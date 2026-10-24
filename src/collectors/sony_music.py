"""Sony's Music segment, split out of Sony Group's results (Form 6-K on SEC EDGAR; sony.com refuses automated access).

Sony reports Music as one segment and breaks its sales to customers into Recorded Music (streaming and other), Music
Publishing, and Visual Media and Platform. Its operating income is in the segment profit table. Both are plain HTML tables in each results release, so they are read
by rule, no Claude call:
- a table headed "Three months / Six months / Nine months / Fiscal year ended <Month> <day>", with years as columns
  ("2025 | 2026 | Change"): the earlier year first;
- sales: the rows after a "Music" line up to its "Total";
- operating income: the "Music |" row under "Operating income (loss):".
Documents: every Form 6-K Sony filed since SINCE whose text holds the music sales table (its results releases);
each filing is checked once (data/sony_6k_checked.csv) and parsed. Each release also carries the year before, so
the series runs a year further back.
Writes data/sony_music.csv (yen; reported, grade A).
"""
import csv
import re
from datetime import date

from ..config import DATA
from ..extract.report_pdf import html_pages
from ..http import get
from .financials import CONTACT_UA

OUT = DATA / "sony_music.csv"
CHECKED = DATA / "sony_6k_checked.csv"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK0000313838.json"
SINCE = "2023-01-01"
FIELDS = ["period_type", "period_end", "item", "value", "currency", "source"]
ITEMS = {"Recorded Music - Streaming": "recorded_streaming", "Recorded Music - Others": "recorded_other",
         "Music Publishing": "publishing", "Visual Media and Platform": "visual_media", "Total": "sales"}
SPAN = {"three months": "Q", "six months": "H", "nine months": "9M", "fiscal year": "FY"}
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}

_num = lambda s: -float(s.strip("( ").replace(",", "")) if s.strip().startswith("(") else float(s.replace(",", ""))


def parse(pages: list[str], source: str) -> list[dict]:
    out = []
    for page in pages:
        head = re.search(r"(Three months|Six months|Nine months|Fiscal year) ended (\w+) (\d{1,2})", page)
        years = re.search(r"^(?:Sales:? \| )?(\d{4}) \| (\d{4}) \| Change", page, re.M)
        if not head or not years or head.group(2) not in MONTHS:
            continue
        ptype = SPAN[head.group(1).lower()]
        ends = [date(int(y), MONTHS[head.group(2)], int(head.group(3))).isoformat() for y in years.groups()]
        lines = page.split("\n")
        rows = {}
        if "Operating income (loss):" in page:
            m = re.search(r"^Music \| ([\d,()]+) \| ([\d,()]+)", page, re.M)
            if m:
                rows["operating_income"] = m.groups()
        if "Music" in lines and "Recorded Music - Streaming" in page:
            for line in lines[lines.index("Music") + 1:]:
                name, *vals = [c.strip() for c in line.split("|")]
                if name in ITEMS and len(vals) >= 2:
                    rows[ITEMS[name]] = vals[:2]
                if name == "Total" or name not in ITEMS:
                    break
        for item, vals in rows.items():
            for end, v in zip(ends, vals):
                out.append({"period_type": ptype, "period_end": end, "item": item, "value": _num(v) * 1e6,
                            "currency": "JPY", "source": source})
    return out


def update() -> int:
    checked = {}
    if CHECKED.exists():
        with CHECKED.open() as f:
            checked = {r["accession"]: r for r in csv.DictReader(f)}
    sub = get(SUBMISSIONS, headers=CONTACT_UA, timeout=60).json()["filings"]["recent"]
    for form, filed, acc, doc in zip(sub["form"], sub["filingDate"], sub["accessionNumber"], sub["primaryDocument"]):
        if form != "6-K" or filed < SINCE or acc in checked:
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/313838/{acc.replace('-', '')}/{doc}"
        r = get(url, headers=CONTACT_UA, timeout=120)
        if r.status_code != 200:
            continue
        checked[acc] = {"accession": acc, "filed": filed, "url": url, "music": int(b"Recorded Music - Streaming" in r.content)}
    with CHECKED.open("w", newline="") as f:
        w = csv.DictWriter(f, ["accession", "filed", "url", "music"])
        w.writeheader()
        w.writerows(sorted(checked.values(), key=lambda r: r["filed"]))
    rows = {}
    # newest release first: a restated figure in a later release replaces the earlier one
    for c in sorted((c for c in checked.values() if str(c["music"]) == "1"), key=lambda c: c["filed"], reverse=True):
        r = get(c["url"], headers=CONTACT_UA, timeout=120)
        if r.status_code == 200:
            for x in parse(html_pages(r.content), c["url"]):
                rows.setdefault((x["period_type"], x["period_end"], x["item"]), x)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda x: (x["period_end"], x["period_type"], x["item"])))
    return len(rows)


def load() -> dict:
    """{"periods": [{period_type, period_end, values: {item: yen}, source}]} newest last, for the site."""
    if not OUT.exists():
        return {}
    per: dict[tuple, dict] = {}
    with OUT.open() as f:
        for r in csv.DictReader(f):
            p = per.setdefault((r["period_end"], r["period_type"]), {"period_type": r["period_type"],
                                                                     "period_end": r["period_end"], "values": {},
                                                                     "source": r["source"]})
            p["values"][r["item"]] = float(r["value"])
    return {"currency": "JPY", "periods": [per[k] for k in sorted(per)]}
