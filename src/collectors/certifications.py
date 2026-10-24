"""Record certifications (RIAA, BPI, Music Canada, ARIA, SNEP, BVMI, FIMI, IFPI ...) and US chart peaks, read from
each artist's English Wikipedia discography (CC BY-SA; RIAA's own site forbids scraping). Saved to
data/certifications.json; the site credits Wikipedia with a link to each page.

Page lookup, per artist: Wikidata P358 (discography) -> its enwiki sitelink; else "<name> discography" (also the
"albums"/"singles" split pages) when it exists and links the artist's own article; else the artist's own article.
Wikitext comes from index.php?action=raw, one page a request about a second apart, cached under .cache/wikitext:
the batched action API answered this project's shared address with HTTP 429 (2026-10-24), the cached raw route
did not.

Parsed: the "Certifications" column of discography tables ("RIAA: 2× Platinum", one per line or <br />), and
{{Certification Table Entry}} templates. The US peak is the chart column headed "US". Units only where the
threshold is certain: RIAA (albums and singles from 1989: Gold 500k, Platinum 1m, Diamond 10m) and BPI (albums
60k/100k/300k, singles from 1989 200k/400k/600k); everything else null.
"""
import csv
import json
import re
from datetime import date
from urllib.parse import quote

from .. import http
from ..config import DATA, REGISTRY, ROOT
from ..http import get
from .wikidata import query, qid

OUT = DATA / "certifications.json"
CACHE = ROOT / ".cache" / "wikitext"
INDEX = "https://en.wikipedia.org/w/index.php"
http.PAUSE.setdefault("en.wikipedia.org", 1.1)  # Wikimedia asks unauthenticated API clients to go slowly

# Abbreviation as written on Wikipedia -> (body, country)
BODIES = {
    "RIAA": ("RIAA", "US"), "BPI": ("BPI", "UK"), "MC": ("MC", "Canada"), "CRIA": ("MC", "Canada"),
    "ARIA": ("ARIA", "Australia"), "SNEP": ("SNEP", "France"), "BVMI": ("BVMI", "Germany"),
    "FIMI": ("FIMI", "Italy"), "PROMUSICAE": ("PROMUSICAE", "Spain"), "RMNZ": ("RMNZ", "New Zealand"),
    "RIANZ": ("RMNZ", "New Zealand"), "NVPI": ("NVPI", "Netherlands"), "BEA": ("BEA", "Belgium"),
    "BRMA": ("BEA", "Belgium"), "IRMA": ("IRMA", "Ireland"), "GLF": ("GLF", "Sweden"),
    "IFPI SWE": ("GLF", "Sweden"), "IFPI SVERIGE": ("GLF", "Sweden"), "IFPI DEN": ("IFPI Danmark", "Denmark"),
    "IFPI DANMARK": ("IFPI Danmark", "Denmark"), "IFPI DK": ("IFPI Danmark", "Denmark"),
    "IFPI NOR": ("IFPI Norway", "Norway"), "IFPI NORWAY": ("IFPI Norway", "Norway"),
    "IFPI SWI": ("IFPI Switzerland", "Switzerland"), "IFPI SWITZERLAND": ("IFPI Switzerland", "Switzerland"),
    "IFPI AUT": ("IFPI Austria", "Austria"), "IFPI AUSTRIA": ("IFPI Austria", "Austria"),
    "IFPI FIN": ("IFPI Finland", "Finland"), "MUSIIKKITUOTTAJAT": ("IFPI Finland", "Finland"),
    "IFPI GRE": ("IFPI Greece", "Greece"), "IFPI GREECE": ("IFPI Greece", "Greece"),
    "IFPI HK": ("IFPI Hong Kong", "Hong Kong"), "IFPI": ("IFPI", None),
    "ZPAV": ("ZPAV", "Poland"), "AFP": ("AFP", "Portugal"), "PRO-MÚSICA BRASIL": ("Pro-Música Brasil", "Brazil"),
    "PMB": ("Pro-Música Brasil", "Brazil"), "ABPD": ("Pro-Música Brasil", "Brazil"),
    "AMPROFON": ("AMPROFON", "Mexico"), "CAPIF": ("CAPIF", "Argentina"), "RIAJ": ("RIAJ", "Japan"),
    "KMCA": ("KMCA", "South Korea"), "IMI": ("IMI", "India"), "RISA": ("RISA", "South Africa"),
    "ČNS IFPI": ("ČNS IFPI", "Czech Republic"), "MAHASZ": ("MAHASZ", "Hungary"), "ZAMP": ("ZAMP", "Croatia"),
    "TONLIST": ("FHF", "Iceland"), "FHF": ("FHF", "Iceland"), "UNIMPRO": ("UNIMPRO", "Peru"),
    "CHL": ("IFPI Chile", "Chile"), "PROFOVI": ("PROFOVI", "Chile"), "RIM": ("RIM", "Malaysia"),
    "PARI": ("PARI", "Philippines"), "TMF": ("TMF", "Thailand"), "MÜ-YAP": ("MÜ-YAP", "Turkey"),
    "SNEP/IFPI": ("SNEP", "France"), "IFPI ICE": ("FHF", "Iceland"),
}
# {{cite certification}} / {{Certification Table Entry}} region -> body abbreviation
REGIONS = {"united states": "RIAA", "us": "RIAA", "united kingdom": "BPI", "uk": "BPI", "canada": "MC",
           "australia": "ARIA", "france": "SNEP", "germany": "BVMI", "italy": "FIMI", "spain": "PROMUSICAE",
           "new zealand": "RMNZ", "netherlands": "NVPI", "belgium": "BEA", "ireland": "IRMA", "sweden": "GLF",
           "denmark": "IFPI DEN", "norway": "IFPI NOR", "switzerland": "IFPI SWI", "austria": "IFPI AUT",
           "finland": "IFPI FIN", "poland": "ZPAV", "portugal": "AFP", "brazil": "PMB", "mexico": "AMPROFON",
           "japan": "RIAJ", "greece": "IFPI GRE", "argentina": "CAPIF", "south africa": "RISA",
           "hungary": "MAHASZ", "iceland": "FHF", "india": "IMI", "south korea": "KMCA", "turkey": "MÜ-YAP"}
LEVELS = ("Diamond", "Platinum", "Gold", "Silver")
# body -> type -> level -> units for one award (see the module note for the years these hold)
UNITS = {"RIAA": {"album": {"Gold": 500_000, "Platinum": 1_000_000, "Diamond": 10_000_000},
                  "single": {"Gold": 500_000, "Platinum": 1_000_000, "Diamond": 10_000_000}},
         "BPI": {"album": {"Silver": 60_000, "Gold": 100_000, "Platinum": 300_000},
                 "single": {"Silver": 200_000, "Gold": 400_000, "Platinum": 600_000}}}


# ---------- wikitext cleaning ----------

def _drop_templates(text: str, names: tuple[str, ...]) -> str:
    """Remove {{name ...}} templates (nested braces included)."""
    low = text.lower()
    out, i = [], 0
    pat = re.compile(r"\{\{\s*(" + "|".join(re.escape(n) for n in names) + r")\s*[|}]", re.I)
    while True:
        m = pat.search(text, i)
        if not m:
            out.append(text[i:])
            return "".join(out)
        out.append(text[i:m.start()])
        depth, j = 0, m.start()
        while j < len(text):
            if low.startswith("{{", j):
                depth, j = depth + 1, j + 2
            elif low.startswith("}}", j):
                depth, j = depth - 1, j + 2
                if depth == 0:
                    break
            else:
                j += 1
        i = j


def prepare(wikitext: str) -> str:
    """Comments, refs and footnote templates out; line breaks inside templates joined, so table lines stay whole."""
    t = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)
    t = re.sub(r"<ref[^>/]*/>", "", t, flags=re.I)
    t = re.sub(r"<ref[^>]*>.*?</ref\s*>", "", t, flags=re.I | re.S)
    t = _drop_templates(t, ("efn", "efn-ua", "efn-la", "efn-lr", "notetag", "refn", "sfn", "r", "#tag:ref",
                            "citation needed", "cn"))
    out, depth, i = [], 0, 0
    while i < len(t):
        two = t[i:i + 2]
        if two == "{{":
            depth += 1; out.append(two); i += 2; continue
        if two == "}}" and depth:
            depth -= 1; out.append(two); i += 2; continue
        c = t[i]
        out.append(" " if c == "\n" and depth else c)
        i += 1
    return "".join(out)


def plain(s: str) -> str:
    """Wiki markup to text: links to their label, simple templates dropped or unwrapped, tags and quotes removed."""
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"\{\{\s*(?:small|nowrap|nobr|sup|sub|lang\|[^|}]*)\|([^{}]*)\}\}", r"\1", s, flags=re.I)
    s = re.sub(r"\{\{\s*(?:abbr)\|([^|{}]*)\|[^{}]*\}\}", r"\1", s, flags=re.I)
    s = s.replace("{{!}}", "|").replace("&nbsp;", " ").replace("&times;", "×")
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()


# ---------- tables ----------

def _split_top(s: str, sep: str) -> list[str]:
    """Split on `sep` outside [[ ]] and {{ }}."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(s):
        two = s[i:i + 2]
        if two in ("[[", "{{"):
            depth += 1; cur.append(two); i += 2; continue
        if two in ("]]", "}}") and depth:
            depth -= 1; cur.append(two); i += 2; continue
        if depth == 0 and s.startswith(sep, i):
            parts.append("".join(cur)); cur = []; i += len(sep); continue
        cur.append(s[i]); i += 1
    parts.append("".join(cur))
    return parts


def _cell(raw: str, header: bool) -> dict:
    parts = _split_top(raw, "|")
    attrs, content = ("", raw) if len(parts) == 1 else (parts[0], "|".join(parts[1:]))
    if attrs and ("[[" in attrs or "{{" in attrs or "=" not in attrs):
        attrs, content = "", raw  # not an attribute block
    num = lambda k: int(m.group(1)) if (m := re.search(k + r'\s*=\s*"?(\d+)', attrs, re.I)) else 1
    return {"text": content.strip(), "header": header, "row": bool(re.search(r'scope\s*=\s*"?row\b', attrs, re.I)),
            "rowspan": num("rowspan"), "colspan": num("colspan")}


def tables(text: str) -> list[tuple[list[list[dict]], int]]:
    """Every wikitable in prepared text: (rows of cells, start offset). Nested tables are skipped."""
    found, stack, pos = [], [], 0
    for line in text.split("\n"):
        start = pos
        pos += len(line) + 1
        s = line.strip()
        if s.startswith("{|"):
            stack.append({"rows": [], "cur": None, "start": start})
            continue
        if not stack:
            continue
        tb = stack[-1]
        if s.startswith("|}"):
            stack.pop()
            if tb["cur"]:
                tb["rows"].append(tb["cur"])
            if not stack:
                found.append((tb["rows"], tb["start"]))
            continue
        if s.startswith("|-"):
            if tb["cur"]:
                tb["rows"].append(tb["cur"])
            tb["cur"] = []
            continue
        if s.startswith("|+"):
            continue
        if s[:1] in ("|", "!"):
            header = s[0] == "!"
            if tb["cur"] is None:
                tb["cur"] = []
            body = s[1:]
            cells = _split_top(body, "!!") if header else [body]
            cells = [c for part in cells for c in _split_top(part, "||")]
            tb["cur"].extend(_cell(c, header) for c in cells)
        elif tb["cur"]:
            tb["cur"][-1]["text"] += "\n" + line
    return found


def grid(rows: list[list[dict]]) -> tuple[list[list[str]], list[list[dict]]]:
    """Header labels per column (top to bottom) and the data rows laid out by column, rowspans/colspans applied."""
    heads: list[list[str]] = []
    data: list[list[dict]] = []
    carry: dict[int, list] = {}  # column -> [cell, rows left]
    in_head = True
    for row in rows:
        if in_head and row and (any(c["row"] for c in row) or not row[0]["header"]
                                or sum(c["header"] for c in row) * 2 <= len(row)):
            in_head = False  # a header row is mostly column headers (a stray data cell can trail the last one)
        laid: dict[int, dict] = {}
        for col, (c, left) in list(carry.items()):
            laid[col] = c
            carry[col][1] -= 1
            if carry[col][1] <= 0:
                del carry[col]
        col = 0
        for c in row:
            while col in laid:
                col += 1
            for k in range(c["colspan"]):
                laid[col + k] = c
                if c["rowspan"] > 1:
                    carry[col + k] = [c, c["rowspan"] - 1]
            col += c["colspan"]
        width = max(laid) + 1 if laid else 0
        cells = [laid.get(i) for i in range(width)]
        if in_head:
            for i, c in enumerate(cells):
                while len(heads) <= i:
                    heads.append([])
                label = plain(c["text"]) if c else ""
                if label and (not heads[i] or heads[i][-1] != label):
                    heads[i].append(label)
        else:
            data.append(cells)
    return heads, data


# ---------- certifications ----------

CERT_LINE = re.compile(
    r"^(?P<body>[A-Za-zÀ-ž][A-Za-zÀ-ž.\-/ ]{0,24}?)\s*:\s*(?:(?P<pre>\d+)\s*[×x✕]\s*)?(?:multi-)?"
    r"(?P<level>Diamond|Platinum|Gold|Silver)(?:\s*[×x✕]\s*(?P<post>\d+))?", re.I)


def unit(body: str, kind: str, level: str, mult: int, year: str) -> int | None:
    per = UNITS.get(body, {}).get(kind, {}).get(level)
    if not per:
        return None
    if kind == "single" and not (year.isdigit() and int(year) >= 1989):
        return None  # older single thresholds differed (and an unknown year might be one of them)
    if body == "RIAA" and kind == "album" and not (year.isdigit() and int(year) >= 1976):
        return None
    return per * mult


def cert(body_raw: str, level: str, mult: int, kind: str, year: str) -> dict | None:
    key = re.sub(r"\s+", " ", body_raw.strip().upper())
    body, country = BODIES.get(key, (None, None))
    if not body:
        return None
    level = level.capitalize()
    return {"body": body, "country": country, "level": level, "multiplier": mult,
            "units": unit(body, kind, level, mult, year)}


def parse_certs(cell: str, kind: str = "other", year: str = "") -> list[dict]:
    """Certifications from one table cell: "RIAA: 2× Platinum" lines, split by new lines, <br /> or bullets."""
    out = []
    for piece in re.split(r"<br\s*/?>|\n|^\*|\s\*\s", cell, flags=re.I | re.M):
        line = plain(piece).lstrip("*• ").strip()
        m = CERT_LINE.match(line)
        if not m:
            continue
        mult = int(m.group("pre") or m.group("post") or 1)
        c = cert(m.group("body"), m.group("level"), mult, kind, year)
        if c and c not in out:
            out.append(c)
    return out


def _kind(heading: str) -> str:
    h = heading.lower()
    single = re.search(r"single|song|featur|lead artist", h)
    if re.search(r"album|mixtape|extended play|\beps?\b|compilation|soundtrack", h) and not single:
        return "album"
    return "single" if single else "other"


def _heading_kind(headings: list[str]) -> str:
    for h in reversed(headings):  # nearest heading first
        k = _kind(h)
        if k != "other":
            return k
    return "other"


def _title(cell_text: str) -> str:
    t = re.split(r"<br\s*/?>", cell_text, flags=re.I)[0]
    t = plain(t).strip()
    m = re.match(r'^"([^"]+)"', t)
    return (m.group(1) if m else t).strip(' "')


def _year(cells: list[dict | None], heads: list[list[str]]) -> str:
    for i, c in enumerate(cells):
        label = " ".join(heads[i]).lower() if i < len(heads) else ""
        if c and ("year" in label or "detail" in label):
            if m := re.search(r"\b(19[5-9]\d|20\d\d)\b", plain(c["text"])):
                return m.group(1)
    return ""


def _us_column(heads: list[list[str]]) -> int | None:
    for i, labels in enumerate(heads):
        if labels and re.fullmatch(r"US", labels[-1]) and any("peak" in l.lower() or "chart" in l.lower()
                                                              for l in labels[:-1]):
            return i
    return None


def _peak(c: dict | None) -> int | None:
    if not c or "bubbling" in c["text"].lower():
        return None
    v = plain(c["text"])
    return int(v) if re.fullmatch(r"\d{1,3}", v) else None


def parse_tables(text: str) -> list[dict]:
    """Works with certifications or a US peak, from the discography tables of prepared wikitext."""
    heads_at = [(m.start(), len(m.group(1)), plain(m.group(2)))
                for m in re.finditer(r"^(={2,5})\s*(.+?)\s*\1\s*$", text, re.M)]
    works = []
    for rows, start in tables(text):
        heads, data = grid(rows)
        cert_col = next((i for i, l in enumerate(heads) if any("certification" in x.lower() for x in l)), None)
        us_col = _us_column(heads)
        year_col = next((i for i, l in enumerate(heads) if l and l[0].lower() in ("year", "release date")), None)
        if cert_col is None and us_col is None:
            continue
        stack: list[tuple[int, str]] = []
        for pos, lvl, h in heads_at:
            if pos > start:
                break
            stack = [x for x in stack if x[0] < lvl] + [(lvl, h)]
        kind = _heading_kind([h for _, h in stack])
        for cells in data:
            head = next((c for c in cells if c and c["row"]), None) or (cells[0] if cells and cells[0] else None)
            if not head:
                continue
            title = _title(head["text"])
            if not title:
                continue
            year = _year(cells, heads)
            # a gap before the last cell means the row lost a cell (a broken page): columns cannot be trusted
            last = min(max(i for i, c in enumerate(cells) if c), max(x for x in (us_col, cert_col) if x is not None))
            shifted = any(c is None for c in cells[:last + 1]) or (
                year_col is not None and year_col < len(cells) and cells[year_col] is not None
                and not re.search(r"\b(19|20)\d\d\b", cells[year_col]["text"]))
            cc = cells[cert_col] if cert_col is not None and cert_col < len(cells) else None
            certs = parse_certs(cc["text"], kind, year) if cc and cc is not head else []
            if not certs:  # cert lines name their body, so a cell in the wrong column still counts
                for c in {id(c): c for c in cells if c and c is not head}.values():
                    certs = certs or parse_certs(c["text"], kind, year)
            us = _peak(cells[us_col]) if us_col is not None and us_col < len(cells) and not shifted else None
            if certs or us:
                works.append({"title": title, "type": kind, "year": year, "certs": certs, "us_peak": us})
    return works


def _params(tpl: str) -> dict[str, str]:
    out = {}
    for p in _split_top(tpl, "|")[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def parse_entries(text: str) -> list[dict]:
    """{{Certification Table Entry|region=..|award=..|number=..|title=..|type=..}} templates."""
    works = []
    for m in re.finditer(r"\{\{\s*Certification Table Entry\b((?:[^{}]|\{\{[^{}]*\}\})*)\}\}", text, re.I):
        p = _params("x" + m.group(1))
        abbr = REGIONS.get(plain(p.get("region", "")).lower())
        level = plain(p.get("award", "")).capitalize()
        if not abbr or level not in LEVELS:
            continue
        kind = {"album": "album", "single": "single", "song": "single", "ep": "album", "mixtape": "album"}.get(
            plain(p.get("type", "")).lower(), "other")
        year = (re.search(r"\d{4}", p.get("relyear", "") or "") or [""])[0]
        mult = int(n) if (n := plain(p.get("number", ""))).isdigit() else 1
        c = cert(abbr, level, mult, kind, year)
        title = plain(p.get("title", ""))
        if c and title:
            works.append({"title": title, "type": kind, "year": year, "certs": [c], "us_peak": None})
    return works


def parse(wikitext: str) -> list[dict]:
    """All works from one page, the same title and type merged."""
    text = prepare(wikitext)
    merged: dict[tuple, dict] = {}
    for w in parse_tables(text) + parse_entries(text):
        key = (w["title"].lower(), w["type"])
        if key not in merged:
            merged[key] = w
            continue
        m = merged[key]
        m["certs"] += [c for c in w["certs"] if not any(x["body"] == c["body"] for x in m["certs"])]
        m["us_peak"] = m["us_peak"] or w["us_peak"]
        m["year"] = m["year"] or w["year"]
    return list(merged.values())


def summary(entry: dict) -> dict:
    """Certified works, RIAA platinum units (each Platinum multiplier, Diamond counted as 10), certs by country."""
    works = [w for w in entry.get("works", []) if w["certs"]]
    riaa, by_country = 0, {}
    for w in works:
        for c in w["certs"]:
            if c["body"] == "RIAA":
                riaa += c["multiplier"] * {"Platinum": 1, "Diamond": 10}.get(c["level"], 0)
            k = c["country"] or c["body"]
            by_country[k] = by_country.get(k, 0) + 1
    return {"certified_works": len(works), "riaa_platinum_units": riaa,
            "by_country": dict(sorted(by_country.items(), key=lambda kv: -kv[1]))}


# ---------- fetching ----------

def _norm(title: str) -> str:
    t = re.sub(r"[_\s]+", " ", title.split("#")[0]).strip()
    return t[:1].upper() + t[1:]


def _cache_path(title: str):
    return CACHE / (quote(_norm(title).replace(" ", "_"), safe="") + ".wt")


def raw(title: str, refresh: bool = False) -> str | None:
    """A page's wikitext (index.php?action=raw, served from Wikimedia's cache), or None when the page does not
    exist. Cached, misses included (as an empty file); a refused request is not cached and comes back None."""
    path = _cache_path(title)
    if path.exists() and not refresh:
        return path.read_text() or None
    CACHE.mkdir(parents=True, exist_ok=True)
    r = get(INDEX, params={"title": _norm(title), "action": "raw"})
    if r.status_code == 404:
        path.write_text("")
        return None
    if r.status_code != 200:
        return None
    path.write_text(r.text)
    return r.text or None


def page(title: str, refresh: bool = False) -> tuple[str, str] | None:
    """(the title it lands on, wikitext), redirects followed (two hops at most), or None when missing."""
    title = _norm(title)
    for _ in range(3):
        text = raw(title, refresh)
        if text is None:
            return None
        m = re.match(r"\s*#REDIRECT\s*:?\s*\[\[([^\]|]+)", text, re.I)
        if not m:
            return title, text
        title = _norm(m.group(1))
    return None


def wikidata_pages(qids: list[str]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """QID -> its enwiki article, and QID -> enwiki titles of its discography items (P358)."""
    article, disco = {}, {}
    for chunk in [qids[i:i + 300] for i in range(0, len(qids), 300)]:
        for r in query(f"""
SELECT ?item ?art ?dt WHERE {{ VALUES ?item {{ {' '.join('wd:' + q for q in chunk)} }}
  OPTIONAL {{ ?a schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?art . }}
  OPTIONAL {{ ?item wdt:P358 ?d . ?b schema:about ?d ; schema:isPartOf <https://en.wikipedia.org/> ;
                schema:name ?dt . }} }}"""):
            q = qid(r["item"])
            if r.get("art"):
                article[q] = r["art"]
            if r.get("dt") and r["dt"] not in disco.setdefault(q, []):
                disco[q].append(r["dt"])
    return article, disco


def _links_to(text: str, article: str) -> bool:
    for m in re.finditer(r"\[\[([^|\]#]+)", text):
        t = m.group(1).strip().replace("_", " ")
        if t[:1].upper() + t[1:] == _norm(article):
            return True
    return False


def find_pages(artists: dict[str, tuple[str, str]], refresh: bool = False) -> dict[str, list[str]]:
    """spotify_id -> the enwiki pages to read: Wikidata's discography page(s), else "<name> discography" (or the
    albums/singles split pages) when it links the artist's own article, else that article."""
    article, disco = wikidata_pages(sorted({q for _, q in artists.values() if q}))
    out = {}
    for s, (name, q) in artists.items():
        art = article.get(q)
        pages = []
        for t in disco.get(q, []):
            if (p := page(t, refresh)) and p[0] != art and p[0] not in pages:
                pages.append(p[0])
        if not pages and art:
            for guess in ([f"{name} discography"], [f"{name} albums discography", f"{name} singles discography"]):
                for t in guess:
                    p = page(t, refresh)
                    if p and p[0] != art and p[0] not in pages and "discography" in p[0].lower() \
                            and _links_to(p[1], art):  # a page about this artist, not a namesake
                        pages.append(p[0])
                if pages:
                    break
        if not pages and art and page(art, refresh):
            pages = [_norm(art)]
        if pages:
            out[s] = pages
    return out


def update(ids_and_names, refresh: bool = False) -> int:
    """ids_and_names: {spotify_id: name} or [(spotify_id, name)]. Writes data/certifications.json; returns the
    number of artists with at least one certification."""
    names = dict(ids_and_names.items() if isinstance(ids_and_names, dict) else ids_and_names)
    with (REGISTRY / "artists.csv").open() as f:
        qids = {r["spotify_id"]: r["wikidata_id"] for r in csv.DictReader(f)}
    artists = {s: (n, qids.get(s, "")) for s, n in names.items()}
    pages = find_pages(artists, refresh)
    texts = {p: (page(p) or ("", ""))[1] for ps in pages.values() for p in ps}
    today = date.today().isoformat()
    out = {}
    for s, ps in pages.items():
        works: list[dict] = []
        for p in ps:
            works += [w for w in parse(texts.get(p, "")) if (w["title"].lower(), w["type"]) not in
                      {(x["title"].lower(), x["type"]) for x in works}]
        out[s] = {"page": ps[0], "url": "https://en.wikipedia.org/wiki/" + quote(ps[0].replace(" ", "_")),
                  "fetched": today, "works": works}
        if len(ps) > 1:
            out[s]["pages"] = ps
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    return sum(1 for e in out.values() if any(w["certs"] for w in e["works"]))


def load() -> dict:
    return json.loads(OUT.read_text()) if OUT.exists() else {}
