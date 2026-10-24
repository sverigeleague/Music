"""Financial health of the label groups, from their filed statements (data/financials.csv, src/collectors/financials.py).

Per company: the three statements for the last five fiscal years and the latest quarters (where the company reports
quarters in XBRL), and ratios, each with a plain reading:
- growth and margins: revenue growth, operating margin, net margin;
- cash: free cash flow = operating cash flow - capital expenditure; after catalogue investment where tagged;
- debt: net debt = long- and short-term borrowings - cash; leverage = net debt / (operating income + D&A), an
  EBITDA proxy (lease liabilities are not included);
- liquidity and solvency: current ratio, equity ratio, interest cover (operating income / interest expense).
Thresholds for the readings are rules of thumb used in credit analysis, not ratings (HEALTH_RULES).
"""
from .collectors import financials

YEARS, QUARTERS = 5, 4
# label-page parent name -> company in the statements
COMPANY_OF = {"Universal Music Group": "Universal Music Group", "Warner Music Group": "Warner Music Group",
              "Sony Music": "Sony Group", "Believe": "Believe", "Reservoir Media": "Reservoir Media",
              "BMG": "Bertelsmann", "Bertelsmann": "Bertelsmann"}
# ratio -> (good when, watch when) as (comparison, value); anything else reads "weak"
HEALTH_RULES = {
    "leverage": (("<=", 2.5), ("<=", 4.0)),
    # music groups owe artists and songwriters royalties within the year, so current ratios sit below 1 across the
    # industry (UMG 0.6, WMG 0.7, Believe 0.7 in their latest years): the bands are set for the industry
    "current_ratio": ((">=", 0.9), (">=", 0.6)),
    "equity_ratio": ((">=", 0.30), (">=", 0.15)),
    "interest_cover": ((">=", 6.0), (">=", 3.0)),
    "operating_margin": ((">=", 0.15), (">=", 0.05)),
    "fcf_margin": ((">=", 0.08), (">=", 0.0)),
}


def _reading(name: str, v: float | None) -> str | None:
    if v is None or name not in HEALTH_RULES:
        return None
    ok = lambda rule: v <= rule[1] if rule[0] == "<=" else v >= rule[1]
    good, watch = HEALTH_RULES[name]
    return "good" if ok(good) else "watch" if ok(watch) else "weak"


def _ratios(p: dict, prev: dict | None) -> dict:
    g = lambda k: p.get(k)
    div = lambda a, b: a / b if a is not None and b not in (None, 0) else None
    debt = None if g("long_term_debt") is None and g("short_term_debt") is None else (g("long_term_debt") or 0) + (g("short_term_debt") or 0)
    net_debt = debt - g("cash") if debt is not None and g("cash") is not None else None
    ebitda = g("operating_income") + g("da") if g("operating_income") is not None and g("da") is not None else None
    fcf = g("cfo") - (g("capex") or 0) if g("cfo") is not None else None
    liabilities = g("total_liabilities")
    if liabilities is None and g("total_liabilities_and_equity") is not None and g("equity") is not None:
        liabilities = g("total_liabilities_and_equity") - g("equity")
    r = {
        "revenue_growth": div(g("revenue") - prev["revenue"], prev["revenue"]) if prev and g("revenue") is not None and prev.get("revenue") else None,
        "operating_margin": div(g("operating_income"), g("revenue")),
        "net_margin": div(g("net_income"), g("revenue")),
        "fcf": fcf,
        "fcf_margin": div(fcf, g("revenue")),
        "fcf_after_catalogue": fcf - (g("catalog_purchases") or 0) if fcf is not None and g("catalog_purchases") is not None else None,
        "net_debt": net_debt,
        "leverage": div(net_debt, ebitda) if ebitda and ebitda > 0 else None,
        "current_ratio": div(g("current_assets"), g("current_liabilities")),
        "equity_ratio": div(g("equity"), g("total_assets")),
        "interest_cover": div(g("operating_income"), abs(g("interest_expense"))) if g("interest_expense") else None,
        "total_liabilities": liabilities,
    }
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}


def build() -> dict:
    rows = financials.load()
    out = {}
    for c in financials.COMPANIES:
        name = c["company"]
        mine = [r for r in rows if r["company"] == name]
        if not mine:
            continue
        per: dict[tuple, dict] = {}
        src: dict[tuple, str] = {}
        for r in mine:
            key = (r["period_type"], r["period_end"])
            per.setdefault(key, {})[r["item"]] = float(r["value"])
            src.setdefault(key, r["source"])
        fys = sorted(k for k in per if k[0] == "FY" and "revenue" in per[k])[-YEARS:]
        qs = sorted(k for k in per if k[0] == "Q" and "revenue" in per[k])[-QUARTERS:]
        years = []
        for i, k in enumerate(fys):
            prev = per[fys[i - 1]] if i else None
            years.append({"period": k[1], "type": "FY", "values": per[k], "ratios": _ratios(per[k], prev),
                          "source": src[k]})
        quarters = [{"period": k[1], "type": "Q", "values": per[k], "ratios": _ratios(per[k], None), "source": src[k]}
                    for k in qs]
        latest = years[-1] if years else None
        out[name] = {
            "currency": next((r["currency"] for r in mine if r["item"] == "revenue"), ""),
            "note": c.get("note", ""), "source_kind": {"sec": "SEC XBRL", "esef": "ESEF annual report (XBRL)", "pdf": "report PDFs read by Claude, checked"}[c["source"]],
            "years": years, "quarters": quarters,
            "health": {k: {"value": v, "reading": _reading(k, v)} for k, v in (latest["ratios"].items() if latest else [])
                       if k in HEALTH_RULES or k in ("net_debt", "fcf", "revenue_growth")},
        }
    return out
