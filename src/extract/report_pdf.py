"""Read a label group's report PDF (half-year report, quarterly results, annual report) with the Claude API: the
consolidated income statement, balance sheet and cash flow statement, mapped to the standard items of
src/collectors/financials.py. Used only where no XBRL exists (UMG's half-year reports, Sony's quarterly results,
Bertelsmann/BMG); everything else comes from XBRL at no cost.

The setup of the Public-Registry project (its DECISIONS.md 2026-10-15 to 10-21 and daily workflow), kept the same:
- **Page selection:** the page finder is its `locate`. Only the pages that open the consolidated income statement,
  balance sheet and cash flow statement go to Claude, with their continuation pages, at most 14. A report of 100+
  pages goes as about 4-8 pages.
- **HTML filings (Sony's results on SEC Form 6-K; sony.com refuses automated access):** split into tables as
  Public-Registry does; only the statement tables go, as text (about 2,500 tokens for Sony's quarter).
- **PDF input, not the text layer:** the text layer saved nothing there and once produced an invented figure.
- **First read:** FIRST_MODEL (Haiku 5.5) at medium effort, structured JSON output.
- **Checks in code:** the period of every column; the core items given or declared absent; the balance sheet
  balances; positive costs; a sane unit multiplier.
- **Correction ladder:** a failed read is corrected by the same model at high effort, shown the failures. What still
  fails is corrected by FALLBACK (Opus 5.5, high, with the server-side fallback for refusals). What fails after that
  is excluded and listed in review/report_reads/excluded.csv, never loaded.
- **Audit:** a fixed 2% of passing reads (chosen by the document's ID) are read again by Opus. A disagreement on a
  core figure sends the read to review instead of loading it.
- **Not taken over:** the Message Batches API (half price, answers next day). It pays at Public-Registry's hundreds of
  documents a month; here about 5 a month would save under $0.05. Direct calls keep it simple.

Cost there: about $1.30 per 100 documents with Haiku plus corrections, against $8 with Opus alone.
Needs the ANTHROPIC_API_KEY secret; without it nothing is sent.
"""
import base64
import csv
import io
import json
import os
import re
import zlib
from pathlib import Path

from ..collectors.financials import STANDARD
from ..config import DATA, REGISTRY, REVIEW

LIST = REGISTRY / "report_pdfs.csv"
OUT = DATA / "financials_pdf.csv"
READS = REVIEW / "report_reads"
FIRST_MODEL = os.environ.get("REPORT_MODEL") or "claude-haiku-5-5"
FALLBACK = ("claude-opus-5-5", "high")
RETRY_EFFORT = "high"  # the first correction: the same model, shown the failures
AUDIT_SHARE = float(os.environ.get("REPORT_AUDIT_SHARE") or 0.02)
MAX_PAGES = 14
HEAD = 350  # characters of a page searched for a statement heading
# Statement headings and exclusions: src/extract/pdf_claude.py of the Public-Registry project, with interim-report
# headings ("Consolidated Interim Statements of ...") added
TITLES = {
    "BS": r"statements? of financial position|balance sheets?|statements? of financial condition",
    "IS": r"statements? of (?:consolidated )?(?:profit or loss|income|operations|comprehensive (?:income|loss))|income statements?",
    "CF": r"statements? of cash flows?|cash flows? statements?",
}
GROUP = r"(?:CONSOLIDATED|COMBINED|GROUP|Consolidated|Combined|Group)"
EXCLUDE = re.compile(r"NOTES TO|Notes to (?:the )?(?:Consolidated|Combined|Financial|Interim|Condensed)|"
                     r"(?i:independent auditor|table of contents|parent company(?:.s)? (?:only|statements?|balance|financial)|"
                     r"company[- ]only|separate (?:statements?|financial)|pro forma|"
                     r"management.s discussion|five[- ]year|financial highlights|summary of|"
                     r"increase\s*\(decrease\)|horizontal analysis|vertical analysis)")
OTHER_STATEMENTS = r"changes in (?:equity|net assets|shareholders|stockholders)|divisional (?:deficit|equity)|" \
                   r"stockholders.? (?:equity|deficit)|shareholders.? (?:equity|deficit)"

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


def _numbers(text: str) -> int:
    return len(re.findall(r"\d{1,3}(?:[,.]\d{3})+(?:\.\d+)?|\d+\.\d{1,2}\b|\d{4,}", text))


def locate(pages: list[str]) -> list[int]:
    """Indexes of the pages to send: per statement, the best heading page (a group-basis heading first, then the page
    with the most numbers) and up to two continuation pages. Public-Registry's locate, returning the union."""
    heads = [" ".join(p[:HEAD].split()) for p in pages]
    any_title = "|".join(TITLES.values()) + "|" + OTHER_STATEMENTS
    keep = set()
    for statement, title in TITLES.items():
        scored = []
        for i, head in enumerate(heads):
            if not any(m.group(0)[0].isupper() for m in re.finditer(title, head, re.I)) or EXCLUDE.search(head):
                continue
            # "Consolidated Interim Statements of ..." (interim reports put Interim/Condensed after Consolidated)
            grouped = any(m.group(1)[0].isupper() for m in re.finditer(
                GROUP + r"\s+(?:(?:Interim|INTERIM|Condensed|CONDENSED)\s+)*((?i:" + title + "))", head))
            # a group-basis heading needs fewer separated numbers: interim statements print "947", not "1,947"
            if _numbers(pages[i]) < (5 if grouped else 10):
                continue
            continued = bool(re.search(r"continued|cont'd", head, re.I))
            scored.append((grouped, not continued, _numbers(pages[i]), i))
        if not scored:
            continue
        best = max(scored)[3]
        other = [t for s2, t in TITLES.items() if s2 != statement] + [OTHER_STATEMENTS]

        def same(i):
            return bool(re.search(title, heads[i], re.I)) and not any(re.search(t, heads[i], re.I) for t in other) \
                and not EXCLUDE.search(heads[i]) and _numbers(pages[i]) >= 10

        chosen = [best]
        while chosen[0] > 0 and best - chosen[0] < 2 and same(chosen[0] - 1):
            chosen.insert(0, chosen[0] - 1)
        for nxt in range(best + 1, min(best + 3, len(pages))):
            head = heads[nxt]
            untitled = not re.search(any_title, head, re.I) and not EXCLUDE.search(head) and _numbers(pages[nxt]) >= 20 \
                and not re.search(r"^\W*(?:\d+\s+)?\d{1,2}\.\s", head)
            if not (same(nxt) or (untitled and statement != "IS")):
                break
            chosen.append(nxt)
        keep |= set(chosen)
    return sorted(keep)[:MAX_PAGES]


def html_pages(body: bytes) -> list[str]:
    """An HTML filing (Sony's results on SEC Form 6-K) as pseudo-pages: each table, rendered as `cell | cell` rows,
    with the text before it. Public-Registry's html_pages."""
    from lxml import html as lhtml
    doc = lhtml.fromstring(body)
    pages, before = [], []
    for el in doc.iter("table", "p", "div"):
        if el.tag == "table":
            rows = []
            for tr in el.iter("tr"):
                cells = [" ".join(td.text_content().split()) for td in tr.iter("td", "th")]
                cells = [c for c in cells if c not in ("", "$", ")", "%")]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                pages.append(" ".join(before)[-HEAD:] + "\n" + "\n".join(rows))
                before = []
        elif not el.xpath("ancestor::table") and not el.xpath(".//table|.//p|.//div"):
            text = " ".join(el.text_content().split())
            if text:
                before.append(text)
    return pages


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
    # the groups read here are large: total assets below one million (after the multiplier) means a wrong unit
    # (Bertelsmann's 2025 annual report, first read 2026-10-24: "EUR millions" read with a multiplier of 1)
    mult = read.get("unit_multiplier") or 1
    for col, v in by.items():
        for k in ("total_assets", "revenue"):
            if v.get(k) is not None and 0 < abs(v[k]) * mult < 1_000_000:
                fails.append(f"column {col}: {k} {v[k]} x {mult} is under one million; the statements are probably "
                             "in thousands or millions (check the unit printed in the heading, e.g. 'EUR millions')")
                break
    return fails


def call(content: list[dict], model: str, effort: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=5)
    params = {"model": model, "max_tokens": 32000, "messages": [{"role": "user", "content": content}],
              "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": _schema()}}}
    # a refusal by a safety classifier is re-run on another model server-side (Haiku has no such fallback)
    fallback = {} if "haiku" in model else {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    with client.beta.messages.stream(**fallback, **params) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"Claude API stopped with {msg.stop_reason} ({msg.model})")
    text = next((b.text for b in msg.content if b.type == "text"), "")
    return {"read": json.loads(text), "model": msg.model, "usage": msg.usage.to_dict()}


def read_report(row: dict, body: bytes) -> dict:
    """Select pages, read, check, correct. Returns {"read", "model", "fails", "pages", "status"}."""
    if body.startswith(b"%PDF"):
        from pypdf import PdfReader
        pages = [(p.extract_text() or "") for p in PdfReader(io.BytesIO(body)).pages]
        keep = locate(pages) or list(range(min(len(pages), MAX_PAGES)))
        doc = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                              "data": base64.b64encode(subset(body, keep)).decode()}}
    else:  # an HTML filing: the statement tables go as text, as Public-Registry sends HTML filings
        pages = html_pages(body)
        keep = locate(pages)
        if not keep:
            raise RuntimeError("no statement tables found in the HTML filing")
        text = "\n\n".join(f"--- page {n} ---\n{pages[i]}" for n, i in enumerate(keep, 1))
        doc = {"type": "document", "source": {"type": "text", "media_type": "text/plain", "data": text}}
    prompt = PROMPT.format(company=row["company"], document=row["document"], period_end=row["period_end"],
                           items="; ".join(ITEM_HELP.values()))
    first = call([doc, {"type": "text", "text": prompt}], FIRST_MODEL, "medium")
    result = {**first, "fails": checks(first["read"]), "pages": [i + 1 for i in keep], "status": "passed", "ladder": [first["model"]]}
    for model, effort in ((FIRST_MODEL, RETRY_EFFORT), FALLBACK):
        if not result["fails"]:
            break
        fix = call([doc, {"type": "text", "text": prompt + "\n\nA first read failed these checks; read the pages again and "
                          "correct them:\n- " + "\n- ".join(result["fails"])}], model, effort)
        result = {**fix, "fails": checks(fix["read"]), "pages": result["pages"], "status": "corrected",
                  "ladder": result["ladder"] + [fix["model"]], "first_fails": result.get("first_fails") or result["fails"]}
    if result["fails"]:
        result["status"] = "excluded"
    elif result["status"] == "passed" and zlib.crc32(row["url"].encode()) % 1000 < AUDIT_SHARE * 1000:
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
    from ..collectors.financials import CONTACT_UA, FIELDS
    READS.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in READS.glob("*.json")}
    todo = [r for r in csv.DictReader(LIST.open()) if r.get("url")] if LIST.exists() else []
    stats = {"read": 0, "passed": 0, "corrected": 0, "review": 0, "excluded": 0}
    new_rows = []
    for row in todo[:limit]:
        key = re.sub(r"[^a-z0-9]+", "-", f"{row['company']}-{row['document']}-{row['period_end']}".lower()).strip("-")
        if key in done:
            continue
        resp = get(row["url"], timeout=120, headers=CONTACT_UA if "sec.gov" in row["url"] else None)
        if resp.status_code != 200 or not (resp.content.startswith(b"%PDF") or b"<html" in resp.content[:2000].lower()):
            continue
        result = read_report(row, resp.content)
        (READS / f"{key}.json").write_text(json.dumps({"report": row, **result}, indent=1, ensure_ascii=False))
        stats["read"] += 1
        stats[result["status"]] += 1
        if result["status"] in ("passed", "corrected"):
            new_rows += rows_of(row, result)
        else:  # never loaded: listed for the owner
            with (READS / "excluded.csv").open("a", newline="") as f:
                csv.writer(f).writerow([row["company"], row["document"], row["period_end"], result["status"],
                                        "; ".join(result["fails"]) or "audit disagreed", row["url"]])
    if new_rows:
        old = list(csv.DictReader(OUT.open())) if OUT.exists() else []
        with OUT.open("w", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows(old + new_rows)
    return stats
