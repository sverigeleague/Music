"""Label groups' financial statements (income statement, balance sheet, cash flow) from structured filings, no Claude
cost. The same approach as the Public-Registry project: machine-readable XBRL first, PDFs only where none exists.

- SEC filers (Warner Music Group, Reservoir Media, Sony Group): the SEC's companyfacts API, every 10-K, 10-Q and
  20-F figure as data (data.sec.gov; User-Agent with contact address, 10 requests a second at most).
- ESEF filers (Universal Music Group, Believe): the annual reports' inline XBRL as xBRL-JSON from filings.xbrl.org.
- Not covered here: Bertelsmann (BMG's owner) files no XBRL; half-year and quarterly PDFs (UMG, Sony's quarterly
  music segment) are read by the PDF route (src/extract/report_pdf.py) when the owner enables it.

Only figures without dimensions are kept (the group's own totals, not segments). Durations of about 3, 6, 9 and 12
months give the period types Q, H, 9M and FY; balance-sheet instants carry the filing's type. Saved to
data/financials.csv: one row per company, standard item and period.
"""
import csv
from datetime import date, timedelta

from ..config import DATA
from ..http import get

CSV = DATA / "financials.csv"
FIELDS = ["company", "item", "statement", "period_type", "period_start", "period_end", "value", "currency", "concept",
          "form", "filed", "source"]
CONTACT_UA = {"User-Agent": "music-ledger research hello@tventy.se"}

COMPANIES = [
    {"company": "Warner Music Group", "source": "sec", "cik": "0001319161"},
    {"company": "Reservoir Media", "source": "sec", "cik": "0001824403"},
    {"company": "Sony Group", "source": "sec", "cik": "0000313838",
     "note": "The whole Sony group (games, pictures, music, electronics); its music segment is shown separately in the Sony Music panel. FY2026-03: the financial-services business was spun off (October 2025), so assets, liabilities and net income fall against the prior year"},
    {"company": "Universal Music Group", "source": "esef", "lei": "724500GJBUL3D9TW9Y18"},
    {"company": "Believe", "source": "esef", "lei": "969500WGEAZ8YE4UAI86"},
    {"company": "Bertelsmann", "source": "pdf",
     "note": "BMG's owner; the whole Bertelsmann group (BMG is one division), read from its report PDFs"},
]

# standard item -> (statement, concepts in order of preference); the first concept with a value for a period wins.
# Revenue to cash flow from src/extract/xbrl.py of the Public-Registry project; debt, capex, catalogue purchases,
# interest, tax and dividends added for the health ratios. Company extensions (umg:, BEL:) where the group tags a
# standard line under its own name (UMG's catalogue investments, Believe's borrowings).
STANDARD = {
    "revenue": ("IS", ["us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                       "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax", "us-gaap:SalesRevenueNet",
                       "ifrs-full:Revenue", "ifrs-full:RevenueFromContractsWithCustomers"]),
    "direct_costs": ("IS", ["us-gaap:CostOfRevenue", "us-gaap:CostOfGoodsAndServicesSold", "us-gaap:DirectOperatingCosts",
                            "ifrs-full:CostOfSales"]),
    "sga": ("IS", ["us-gaap:SellingGeneralAndAdministrativeExpense", "ifrs-full:SellingGeneralAndAdministrativeExpense"]),
    "da": ("IS", ["us-gaap:DepreciationDepletionAndAmortization", "us-gaap:DepreciationAndAmortization",
                  "us-gaap:DepreciationAmortizationAndAccretionNet", "ifrs-full:DepreciationAndAmortisationExpense",
                  "ifrs-full:AdjustmentsForDepreciationAndAmortisationExpenseAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss",
                  # UMG tags only amortisation and impairment of intangibles (catalogues): D&A without depreciation
                  "umg:AmortisationAndImpairmentLossesOnIntangibleAssets"]),
    "operating_income": ("IS", ["us-gaap:OperatingIncomeLoss", "ifrs-full:ProfitLossFromOperatingActivities"]),
    "interest_expense": ("IS", ["us-gaap:InterestExpense", "us-gaap:InterestExpenseNonoperating", "us-gaap:InterestExpenseDebt",
                                  "us-gaap:InterestPaidNet", "ifrs-full:FinanceCosts",
                                  "BEL:CostOfDebt"]),
    "pretax_income": ("IS", ["us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                             "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
                             "ifrs-full:ProfitLossBeforeTax"]),
    "income_tax": ("IS", ["us-gaap:IncomeTaxExpenseBenefit", "ifrs-full:IncomeTaxExpenseContinuingOperations"]),
    "net_income": ("IS", ["us-gaap:NetIncomeLoss", "us-gaap:ProfitLoss", "ifrs-full:ProfitLossAttributableToOwnersOfParent",
                          "ifrs-full:ProfitLoss"]),
    "cash": ("BS", ["us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Cash", "ifrs-full:CashAndCashEquivalents"]),
    "current_assets": ("BS", ["us-gaap:AssetsCurrent", "ifrs-full:CurrentAssets"]),
    "total_assets": ("BS", ["us-gaap:Assets", "ifrs-full:Assets"]),
    "current_liabilities": ("BS", ["us-gaap:LiabilitiesCurrent", "ifrs-full:CurrentLiabilities"]),
    "total_liabilities": ("BS", ["us-gaap:Liabilities", "ifrs-full:Liabilities"]),
    "long_term_debt": ("BS", ["us-gaap:LongTermDebtNoncurrent", "us-gaap:LongTermDebt",
                              "ifrs-full:NoncurrentPortionOfNoncurrentBorrowings", "ifrs-full:LongtermBorrowings",
                              "ifrs-full:NoncurrentFinancialLiabilities", "BEL:LongTermBorrowingsAndDebt"]),
    "short_term_debt": ("BS", ["us-gaap:LongTermDebtCurrent", "us-gaap:DebtCurrent", "us-gaap:ShortTermBorrowings",
                               "ifrs-full:CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings",
                               "ifrs-full:CurrentPortionOfLongtermBorrowings", "ifrs-full:ShorttermBorrowings",
                               "BEL:ShortTermBorrowingsAndDebt"]),
    "total_liabilities_and_equity": ("BS", ["us-gaap:LiabilitiesAndStockholdersEquity", "ifrs-full:EquityAndLiabilities"]),
    "equity": ("BS", ["us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                      "us-gaap:StockholdersEquity", "ifrs-full:Equity"]),
    "cfo": ("CF", ["us-gaap:NetCashProvidedByUsedInOperatingActivities",
                   "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
                   "ifrs-full:CashFlowsFromUsedInOperatingActivities"]),
    "capex": ("CF", ["us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
                     "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
                     "BEL:AcquisitionsOfPropertyPlantAndEquipmentAndIntangibleAssets"]),
    "catalog_purchases": ("CF", ["us-gaap:PaymentsToAcquireIntangibleAssets", "us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired",
                                 "ifrs-full:PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities",
                                 "umg:CatalogueInvestmentsClassifiedAsInvestingActivities"]),
    "cfi": ("CF", ["us-gaap:NetCashProvidedByUsedInInvestingActivities",
                   "us-gaap:NetCashProvidedByUsedInInvestingActivitiesContinuingOperations",
                   "ifrs-full:CashFlowsFromUsedInInvestingActivities"]),
    "dividends_paid": ("CF", ["us-gaap:PaymentsOfDividends", "us-gaap:PaymentsOfDividendsCommonStock",
                              "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
                              "ifrs-full:DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities", "ifrs-full:DividendsPaid"]),
    "cff": ("CF", ["us-gaap:NetCashProvidedByUsedInFinancingActivities",
                   "us-gaap:NetCashProvidedByUsedInFinancingActivitiesContinuingOperations",
                   "ifrs-full:CashFlowsFromUsedInFinancingActivities"]),
}
FORMS = {"10-K": "FY", "10-K/A": "FY", "20-F": "FY", "20-F/A": "FY", "10-Q": "Q", "10-Q/A": "Q", "ESEF": "FY"}


def period_type(start: str | None, end: str) -> str:
    if not start:
        return ""
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    for lo, hi, t in ((80, 100, "Q"), (170, 195, "H"), (260, 285, "9M"), (350, 380, "FY")):
        if lo <= days <= hi:
            return t
    return ""


def _pick(rows: list[dict]) -> list[dict]:
    """Per item and period: the first concept in the preference order, from the latest filing that reports it."""
    best: dict[tuple, dict] = {}
    rank = lambda r: (STANDARD[r["item"]][1].index(r["concept"]), "~" if not r["filed"] else "", [-ord(ch) for ch in r["filed"]])
    for r in rows:
        key = (r["item"], r["period_type"], r["period_start"], r["period_end"])
        if key not in best or rank(r) < rank(best[key]):
            best[key] = r
    return list(best.values())


def sec(c: dict) -> list[dict]:
    r = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{c['cik']}.json", headers=CONTACT_UA)
    r.raise_for_status()
    facts = r.json().get("facts", {})
    out = []
    for item, (stmt, concepts) in STANDARD.items():
        for concept in concepts:
            tax, name = concept.split(":")
            for unit, vals in facts.get(tax, {}).get(name, {}).get("units", {}).items():
                if "/" in unit:
                    continue  # per-share units
                for v in vals:
                    if v.get("form") not in FORMS:
                        continue
                    pt = period_type(v.get("start"), v["end"]) if stmt != "BS" else FORMS[v["form"]]
                    if stmt != "BS" and not pt:
                        continue
                    out.append({"company": c["company"], "item": item, "statement": stmt, "period_type": pt,
                                "period_start": v.get("start", ""), "period_end": v["end"], "value": v["val"],
                                "currency": unit, "concept": concept, "form": v["form"], "filed": v.get("filed", ""),
                                "source": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={c['cik']}"
                                          f"&type={v['form']}"})
    return _pick(out)


def _esef_period(p: str) -> tuple[str, str]:
    """xBRL-JSON periods are instants or start/end with an exclusive end at midnight: 2025-01-01T00:00:00 means
    the end of 2024-12-31."""
    fix = lambda s: (date.fromisoformat(s[:10]) - timedelta(days=1)).isoformat() if s[11:19] in ("00:00:00", "") and "T" in s else s[:10]
    if "/" in p:
        a, b = p.split("/")
        return a[:10], fix(b)
    return "", fix(p)


def esef(c: dict) -> list[dict]:
    lst = get(f"https://filings.xbrl.org/api/entities/{c['lei']}/filings").json().get("data", [])
    out = []
    for f in lst:
        a = f["attributes"]
        if not a.get("json_url"):
            continue
        url = "https://filings.xbrl.org" + a["json_url"]
        data = get(url, timeout=120).json()
        for fact in data.get("facts", {}).values():
            dims = fact.get("dimensions", {})
            if set(dims) - {"concept", "entity", "period", "unit", "language"}:
                continue  # a segment or other breakdown
            concept = dims.get("concept", "")
            for item, (stmt, concepts) in STANDARD.items():
                if concept not in concepts:
                    continue
                try:
                    val = float(fact["value"])
                except (TypeError, ValueError):
                    continue
                start, end = _esef_period(dims.get("period", ""))
                pt = "FY" if stmt == "BS" else period_type(start, end)
                if not pt:
                    continue
                out.append({"company": c["company"], "item": item, "statement": stmt, "period_type": pt,
                            "period_start": start, "period_end": end, "value": val,
                            "currency": dims.get("unit", "").replace("iso4217:", ""), "concept": concept,
                            "form": "ESEF", "filed": a.get("date_added", "")[:10] if a.get("date_added") else a.get("period_end", ""),
                            "source": "https://filings.xbrl.org" + (a.get("report_url") or a["json_url"])})
    return _pick(out)


def update() -> dict[str, int]:
    rows, counts = [], {}
    for c in COMPANIES:
        if c["source"] == "pdf":
            continue  # read from report PDFs (src/extract/report_pdf.py)
        got = sec(c) if c["source"] == "sec" else esef(c)
        counts[c["company"]] = len(got)
        rows += got
    rows.sort(key=lambda r: (r["company"], r["period_end"], r["statement"], r["item"]))
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    return counts


def load() -> list[dict]:
    """XBRL figures, plus figures read from report PDFs (data/financials_pdf.csv) for periods XBRL does not cover."""
    rows = []
    if CSV.exists():
        with CSV.open() as f:
            rows = list(csv.DictReader(f))
    pdf = DATA / "financials_pdf.csv"
    if pdf.exists():
        have = {(r["company"], r["item"], r["period_type"], r["period_end"]) for r in rows}
        with pdf.open() as f:
            rows += [r for r in csv.DictReader(f) if (r["company"], r["item"], r["period_type"], r["period_end"]) not in have]
    return rows
