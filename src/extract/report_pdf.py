"""Read a label group's report PDF (half-year report, quarterly results, annual report) with the Claude API: the
consolidated income statement, balance sheet and cash flow statement, mapped to the standard items of
src/collectors/financials.py. Used only where no XBRL exists (UMG's half-year reports, Sony's quarterly results,
Bertelsmann/BMG); everything else comes from XBRL at no cost.

The approach of the Public-Registry project (its DECISIONS.md, 2026-10-15 to 10-21):
- **Page selection:** only the pages that open a primary statement, and up to two continuation pages, are sent. A
  report of 100+ pages goes as about 4-8 pages.
- **Cheap first read:** FIRST_MODEL (Haiku) reads them, at medium effort.
- **Checks in code:** the balance sheet balances; the cash flow's parts add up to the change in cash where both are
  printed; every column has a period; revenue, net income, total assets and operating cash flow are given or
  declared absent.
- **Correction:** a read that fails a check is read again by FALLBACK (Opus, high), shown the failures.
- **Review:** a read that still fails goes to review/report_reads/ and is not loaded.
- **Audit:** AUDIT_SHARE of passing reads are re-read by FALLBACK to measure the error the checks cannot see.

Cost (Public-Registry benchmark): about $1.30 per 100 documents with Haiku plus fallback, against $8 with Opus alone.
Needs the ANTHROPIC_API_KEY secret; without it nothing is sent.
"""
import base64
import csv
import io
import json
import os
import random
import re
from pathlib import Path

from ..collectors.financials import STANDARD
from ..config import DATA, REGISTRY, REVIEW

LIST = REGISTRY / "report_pdfs.csv"
OUT = DATA / "financials_pdf.csv"
READS = REVIEW / "report_reads"
FIRST_MODEL = os.environ.get("REPORT_MODEL") or "claude-haiku-5-5"
FALLBACK = ("claude-opus-5-5", "high")
AUDIT_SHARE = float(os.environ.get("REPORT_AUDIT_SHARE") or 0.1)
MAX_PAGES = 14
HEAD = 350
TITLES = {
    "BS": r"statements? of financial position|balance sheets?|statements? of financial condition",
    "IS": r"statements? of (?:consolidated )?(?:profit or loss|income|operations)|income statements?",
    "CF": r"statements? of cash flows?|cash flows? statements?",
}
EXCLUDE = re.compile(r"(?i:notes to|independent auditor|table of contents|parent company|five[- ]year|"
                     r"financial highlights|management.s discussion)")

ITEM_HELP = {k: f"{k} ({stmt})" for k, (stmt, _) in STANDARD.items()}
PROMPT = """These pages are from {company}'s {document} (period ending {period_end}). Read the CONSOLIDATED income
statement, balance sheet (statement of financial position) and cash flow statement, for every period column printed
(current and comparative; quarter, half-year, nine months or full year).

For each column give the period end (YYYY-MM-DD) and its length in months (balance sheets: 0). For each standard item
below give the value printed in that column, exactly as printed and before any unit multiplier, with the page it is
on. Costs, capital expenditure, catalogue purchases, dividends and interest are positive amounts; losses and cash
outflows of the cash-flow totals (cfo, cfi, cff) are negative. Never add up lines to make a total that is not printed;
leave it out. If one of revenue, net_income, total_assets or cfo is not printed, list it under absent with a reason.

Standard items: {items}"""


def _schema() -> dict:
    obj = lambda props, req=None: {"type": "object", "properties": props, "required": req or list(props),
                                   "additionalProperties": False}
    return obj({
        "currency": {"type": "string"},
        "unit_multiplier": {"type": "number", "description": "1, 1000 (thousands) or 1000000 (millions)"},
        "columns": {"type": "array", "items": obj({"column": {"type": "integer"}, "statement": {"type": "string", "enum": ["IS", "BS", "CF"]},
                                                   "period_end": {"type": "string"}, "months": {"type": "integer"}})},
        "lines": {"type": "array", "items": obj({"item": {"type": "string", "enum": list(STANDARD)},
                                                 "label": {"type": "string"}, "column": {"type": "integer"},
                                                 "value": {"type": "number"}, "page": {"type": "integer"}})},
        "absent": {"type": "array", "items": obj({"item": {"type": "string"}, "reason": {"type": "string"}})},
    })


def locate(pages: list[str]) -> list[int]:
    """Indexes of the pages that open a primary statement (heading near the top, many numbers), with up to two
    continuation pages each."""
    nums = lambda t: len(re.findall(r"\d{1,3}(?:[,.]\d{3})+|\d+\.\d\b|\(\d", t))
    keep = set()
    for title in TITLES.values():
        for i, p in enumerate(pages):
            head = " ".join(p[:HEAD].split())
            if re.search(title, head, re.I) and not EXCLUDE.search(head) and nums(p) >= 10:
                keep |= {j for j in (i, i + 1, i + 2) if j < len(pages) and nums(pages[j]) >= 10}
    return sorted(keep)[:MAX_PAGES]


def subset(body: bytes, keep: list[int]) -> bytes:
    from pypdf import PdfReader, PdfWriter
    reader, writer = PdfReader(io.BytesIO(body)), PdfWriter()
    for i in keep:
        writer.add_page(reader.pages[i])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def checks(read: dict) -> list[str]:
    """Failures of a read, in words the correction prompt can use."""
    fails = []
    cols = {c["column"]: c for c in read.get("columns", [])}
    by = {}
    for l in read.get("lines", []):
        if l["column"] not in cols:
            fails.append(f"line {l['item']} refers to column {l['column']}, which has no period")
            continue
        by.setdefault(l["column"], {})[l["item"]] = l["value"]
    absent = {a["item"] for a in read.get("absent", [])}
    have = {i for v in by.values() for i in v}
    for core in ("revenue", "net_income", "total_assets", "cfo"):
        if core not in have and core not in absent:
            fails.append(f"{core} is neither given nor declared absent")
    for col, v in by.items():
        if {"total_assets", "total_liabilities", "equity"} <= set(v):
            diff = v["total_assets"] - v["total_liabilities"] - v["equity"]
            if abs(diff) > 0.005 * abs(v["total_assets"]):
                fails.append(f"column {col}: total assets {v['total_assets']} differ from liabilities + equity by {diff}")
        if {"total_assets", "total_liabilities_and_equity"} <= set(v) and \
                abs(v["total_assets"] - v["total_liabilities_and_equity"]) > 0.005 * abs(v["total_assets"]):
            fails.append(f"column {col}: total assets differ from total liabilities and equity")
        for k in ("capex", "catalog_purchases", "dividends_paid", "interest_expense", "direct_costs", "sga", "da"):
            if v.get(k, 0) < 0:
                fails.append(f"column {col}: {k} should be a positive amount")
    if read.get("unit_multiplier") not in (1, 1000, 1000000):
        fails.append("unit_multiplier must be 1, 1000 or 1000000")
    return fails


def call(content: list[dict], model: str, effort: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=5)
    msg = client.messages.create(model=model, max_tokens=32000, messages=[{"role": "user", "content": content}],
                                 output_config={"effort": effort, "format": {"type": "json_schema", "schema": _schema()}})
    text = next((b.text for b in msg.content if b.type == "text"), "")
    return {"read": json.loads(text), "model": msg.model, "usage": msg.usage.to_dict()}


def read_report(row: dict, body: bytes) -> dict:
    """Select pages, read, check, correct. Returns {"read", "model", "fails", "pages", "status"}."""
    from pypdf import PdfReader
    pages = [(p.extract_text() or "") for p in PdfReader(io.BytesIO(body)).pages]
    keep = locate(pages) or list(range(min(len(pages), MAX_PAGES)))
    doc = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                          "data": base64.b64encode(subset(body, keep)).decode()}}
    prompt = PROMPT.format(company=row["company"], document=row["document"], period_end=row["period_end"],
                           items="; ".join(ITEM_HELP.values()))
    first = call([doc, {"type": "text", "text": prompt}], FIRST_MODEL, "medium")
    fails = checks(first["read"])
    result = {**first, "fails": fails, "pages": [i + 1 for i in keep], "status": "passed"}
    if fails:
        fixed = call([doc, {"type": "text", "text": prompt + "\n\nA first read failed these checks; correct them:\n- "
                            + "\n- ".join(fails)}], *FALLBACK)
        result = {**fixed, "fails": checks(fixed["read"]), "pages": result["pages"], "first_fails": fails,
                  "status": "corrected" if not checks(fixed["read"]) else "review"}
    elif random.random() < AUDIT_SHARE:
        audit = call([doc, {"type": "text", "text": prompt}], *FALLBACK)
        result["audit"] = {"model": audit["model"], "agrees": _agree(first["read"], audit["read"])}
        if not result["audit"]["agrees"]:
            result["status"] = "review"
    return result


def _agree(a: dict, b: dict) -> bool:
    core = ("revenue", "net_income", "total_assets", "cfo")
    va = {(l["item"], l["column"]): l["value"] for l in a.get("lines", []) if l["item"] in core}
    vb = {(l["item"], l["column"]): l["value"] for l in b.get("lines", []) if l["item"] in core}
    return all(abs(va[k] - vb[k]) <= 0.001 * max(1, abs(va[k])) for k in va.keys() & vb.keys())


def rows_of(row: dict, result: dict) -> list[dict]:
    """The read as rows of data/financials_pdf.csv (same fields as data/financials.csv)."""
    from datetime import date
    read = result["read"]
    mult = read.get("unit_multiplier") or 1
    cols = {c["column"]: c for c in read["columns"]}
    out = []
    for l in read["lines"]:
        c = cols.get(l["column"])
        if not c:
            continue
        stmt = STANDARD[l["item"]][0]
        months = c["months"]
        ptype = "FY" if stmt == "BS" and row["period_type"] == "FY" else \
            {3: "Q", 6: "H", 9: "9M", 12: "FY"}.get(months, "Q" if stmt == "BS" else "")
        if not ptype:
            continue
        out.append({"company": row["company"], "item": l["item"], "statement": stmt, "period_type": ptype,
                    "period_start": "", "period_end": c["period_end"], "value": l["value"] * mult,
                    "currency": read.get("currency", ""), "concept": f"pdf:{l['label']} (p. {l['page']})",
                    "form": f"PDF read by {result['model']}", "filed": date.today().isoformat(), "source": row["url"]})
    return out


def update(limit: int | None = None) -> dict:
    """Read the listed reports not yet read. Without ANTHROPIC_API_KEY nothing is sent."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"skipped": "no ANTHROPIC_API_KEY"}
    from ..http import get
    from ..collectors.financials import FIELDS
    READS.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in READS.glob("*.json")}
    todo = [r for r in csv.DictReader(LIST.open()) if r.get("url")] if LIST.exists() else []
    stats = {"read": 0, "passed": 0, "corrected": 0, "review": 0}
    new_rows = []
    for row in todo[:limit]:
        key = re.sub(r"[^a-z0-9]+", "-", f"{row['company']}-{row['document']}-{row['period_end']}".lower()).strip("-")
        if key in done:
            continue
        resp = get(row["url"], timeout=120)
        if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
            continue
        result = read_report(row, resp.content)
        (READS / f"{key}.json").write_text(json.dumps({"report": row, **result}, indent=1, ensure_ascii=False))
        stats["read"] += 1
        stats[result["status"]] += 1
        if result["status"] != "review":
            new_rows += rows_of(row, result)
    if new_rows:
        old = list(csv.DictReader(OUT.open())) if OUT.exists() else []
        with OUT.open("w", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows(old + new_rows)
    return stats
