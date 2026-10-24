"""UK Companies House: the annual accounts of the majors' UK record companies (registry/uk_companies.csv), for label
health below group level. The route is Public-Registry's (src/collectors/registers/companies_house.py there): the
public website, which needs no key or login: the filing history lists each set of accounts with its PDF.

The majors file their full accounts as scanned paper (no text layer, no iXBRL), so each PDF is read whole by Claude in
src/extract/report_pdf.py, with the same checks and correction ladder as the groups' reports. BMG's UK company also
files iXBRL; one company a year does not pay for a second parser, so its PDF goes the same way.

Writes data/uk_accounts.csv in the columns of registry/report_pdfs.csv: the latest YEARS full accounts per company.
UK accounts are annual only (no quarters or half-years).
"""
import csv
import html as htmllib
import re
from datetime import datetime

from ..config import DATA, REGISTRY
from ..http import get

WEB = "https://find-and-update.company-information.service.gov.uk"
LIST = REGISTRY / "uk_companies.csv"
OUT = DATA / "uk_accounts.csv"
YEARS = 5
FIELDS = ["company", "document", "period_end", "period_type", "url", "statements_included", "pages_hint", "note", "basis"]


def companies() -> list[dict]:
    with LIST.open() as f:
        return list(csv.DictReader(f))


def _text(fragment: str) -> str:
    return htmllib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def accounts(number: str, pages: int = 5) -> list[dict]:
    """Full annual accounts on the filing history, newest first: {made_up, filed, url, description}."""
    out = []
    for page_no in range(1, pages + 1):
        r = get(f"{WEB}/company/{number}/filing-history", params={"page": page_no})
        if r.status_code != 200:
            break
        rows = re.findall(r"<tr>(.*?)</tr>", r.text, re.S)[1:]
        if not rows:
            break
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            if len(cells) < 4 or _text(cells[1]) != "AA":
                continue
            desc = _text(cells[2])
            m = re.search(r"made up to (\d{1,2} \w+ \d{4})", desc)
            pdf = re.search(r'href="([^"]*/document\?format=pdf[^"]*)"', cells[3])
            # full accounts only: dormant, small or abridged accounts hold no income statement
            if not m or not pdf or not re.match(r"(?:Full|Group) accounts", desc):
                continue
            out.append({"made_up": datetime.strptime(m.group(1), "%d %B %Y").date().isoformat(),
                        "filed": datetime.strptime(_text(cells[0]), "%d %b %Y").date().isoformat(),
                        "url": WEB + htmllib.unescape(pdf.group(1)).replace("download=0", "download=1"),
                        "description": desc})
        if len(out) >= YEARS:
            break
    return out


def update() -> dict[str, int]:
    rows, counts = [], {}
    for c in companies():
        got = accounts(c["company_number"])[:YEARS]
        counts[c["company"]] = len(got)
        rows += [{"company": c["company"], "document": f"Annual accounts made up to {a['made_up']} (Companies House "
                  f"{c['company_number']}, filed {a['filed']})", "period_end": a["made_up"], "period_type": "FY",
                  "url": a["url"], "statements_included": "IS,BS,CF", "pages_hint": "",
                  "note": a["description"], "basis": "company"} for a in got]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    return counts
