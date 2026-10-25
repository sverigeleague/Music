"""Certifications from the French and German Wikipedia discographies, for artists the English pages miss.

Page lookup, per artist (registry wikidata_id): Wikidata P358 (discography) -> its frwiki/dewiki sitelink, plus the
artist's own article; pages the article points to ({{Eingebundene Diskografie|X/Diskografie}}, {{Hauptartikel}},
{{Article détaillé|Discographie de X}}) are followed. No titles are guessed.

fr: {{Discographie des albums}} / {{Discographie des chansons}} (titreN, certifN, annéeN, détailsN) and wikitables
with a "Certifications" column; a certification is a country flag ({{Drapeau|France}} or {{France}}) followed by
{{Certification|Or|2}} (Argent/Or/Platine/Diamant). The country gives the body (France -> SNEP, Belgique -> BEA ...);
a certification with no flag, first in its cell, is SNEP's. Also read: list items "** ''Title'' : <flag> <cert>".
Of the two wikis, the one with more certifications for the artist is kept (one wiki per entry, in "lang").
de: {{Charteintrag}} rows (Titel#, Jahr, A_DE# = "G", "3P", "D+5P" ...), the A_ suffix giving the country
(DE -> BVMI, AT -> IFPI Austria, CH -> IFPI Switzerland ...); the type from {{Charttabelle|Art=...}} or the heading.
Units stay null: SNEP and BVMI thresholds changed with year and format.
"""
import re

from .. import http
from . import certifications as c
from .wikidata import query, qid

LANGS = ("fr", "de")
for _l in LANGS:
    http.PAUSE.setdefault(f"{_l}.wikipedia.org", 0.2)

# French country names (flag templates) -> body abbreviation in certifications.BODIES
FR_COUNTRIES = {
    "france": "SNEP", "belgique": "BEA", "wallonie": "BEA", "flandre": "BEA", "suisse": "IFPI SWI",
    "canada": "MC", "québec": "MC", "allemagne": "BVMI", "autriche": "IFPI AUT", "royaume-uni": "BPI",
    "états-unis": "RIAA", "italie": "FIMI", "espagne": "PROMUSICAE", "pays-bas": "NVPI", "danemark": "IFPI DEN",
    "suède": "GLF", "norvège": "IFPI NOR", "finlande": "IFPI FIN", "pologne": "ZPAV", "portugal": "AFP",
    "brésil": "PMB", "mexique": "AMPROFON", "australie": "ARIA", "nouvelle-zélande": "RMNZ", "irlande": "IRMA",
    "grèce": "IFPI GRE", "turquie": "MÜ-YAP", "japon": "RIAJ", "argentine": "CAPIF",
}
FR_COUNTRIES.update({k + sfx: v for k, v in {"fra": "SNEP", "bel": "BEA", "sui": "IFPI SWI", "che": "IFPI SWI",
                                                 "can": "MC", "deu": "BVMI", "all": "BVMI", "aut": "IFPI AUT",
                                                 "usa": "RIAA", "gbr": "BPI", "ita": "FIMI"}.items()
                     for sfx in ("", "-d")})  # flag templates named by country code ({{FRA-d}})
FR_LEVELS = {"argent": "Silver", "or": "Gold", "platine": "Platinum", "diamant": "Diamond"}
# German chart-country codes (A_xy) -> body abbreviation
DE_COUNTRIES = {
    "DE": "BVMI", "AT": "IFPI AUT", "CH": "IFPI SWI", "UK": "BPI", "GB": "BPI", "US": "RIAA", "FR": "SNEP",
    "IT": "FIMI", "NL": "NVPI", "BE": "BEA", "BEF": "BEA", "BEW": "BEA", "SE": "GLF", "DK": "IFPI DEN",
    "NO": "IFPI NOR", "FI": "IFPI FIN", "PL": "ZPAV", "ES": "PROMUSICAE", "PT": "AFP", "AU": "ARIA",
    "NZ": "RMNZ", "CA": "MC", "IE": "IRMA", "BR": "PMB", "MX": "AMPROFON", "GR": "IFPI GRE", "TR": "MÜ-YAP",
}
DE_LEVELS = {"S": "Silver", "SILBER": "Silver", "G": "Gold", "GOLD": "Gold", "P": "Platinum", "PLATIN": "Platinum",
             "D": "Diamond", "DIAMANT": "Diamond"}


def templates(text: str, name: str):
    """(start, opening text, inner text) of each top-level {{name ...}} template, nested braces included."""
    pat = re.compile(r"\{\{\s*" + name + r"\s*(?=[|}\n])", re.I)
    i = 0
    while m := pat.search(text, i):
        depth, j = 0, m.start()
        while j < len(text):
            if text.startswith("{{", j):
                depth, j = depth + 1, j + 2
            elif text.startswith("}}", j):
                depth, j = depth - 1, j + 2
                if depth == 0:
                    break
            else:
                j += 1
        yield m.start(), m.group(0), text[m.end():j - 2]
        i = j


def params(inner: str) -> tuple[list[str], dict[str, str]]:
    """Positional and named parameters of a template's inner text (keys lower-cased)."""
    pos, named = [], {}
    for p in c._split_top(inner, "|")[1:]:
        k, eq, v = p.partition("=")
        if eq and re.fullmatch(r"\s*[\w\- ]+\s*", k):
            named[k.strip().lower()] = v.strip()
        else:
            pos.append(p.strip())
    return pos, named


def _headings(text: str):
    return [(m.start(), len(m.group(1)), c.plain(m.group(2)))
            for m in re.finditer(r"^(={2,5})\s*(.+?)\s*\1\s*$", text, re.M)]


def _kind_at(heads, pos: int) -> str:
    stack: list[tuple[int, str]] = []
    for p, lvl, h in heads:
        if p > pos:
            break
        stack = [x for x in stack if x[0] < lvl] + [(lvl, h)]
    return c._heading_kind([h for _, h in stack])


# ---------- French ----------

_FLAG = r"\{\{\s*(?:drapeau2?\s*\|\s*)?(?P<country>[^{}|]+?)\s*(?:\|[^{}]*)?\}\}"
_CERT = r"\{\{\s*certification\s*\|\s*(?P<level>[^{}|]+?)\s*(?:\|\s*(?P<n>\d*)\s*)?(?:\|[^{}]*)?\}\}"
_GAP = r"(?:\s|<br\s*/?>|'''|&nbsp;)*"
# a flag, then "(SNEP)" and a colon at most, then the certification
_FR_CERT = re.compile(_FLAG + _GAP + r"(?:\([^()\n]*\))?\s*:?" + _GAP + _CERT, re.I)
# a certification with no flag, first in its cell, line or template value: the French icon is SNEP's
_BARE = re.compile(r"(?P<pre>^\|(?:[^|\n{}\[\]]*\|(?!\|))?|^\s*\*|^|<br\s*/?>|\|\||=)(?P<sp>[ \t]*)" + _CERT,
                   re.I | re.M)
_CODED = re.compile(r"(?P<code>\b[A-Z]{2,5}\s*:\s*)(?i:" + _CERT + ")")  # "FRA : {{Certification|Or}}"


def _level(m) -> str | None:
    level = FR_LEVELS.get(m.group("level").strip().lower())
    n = m.group("n")
    return level and f"{n + '× ' if n and n != '1' else ''}{level}"


def fr_certs_text(s: str) -> str:
    """French certification markup rewritten to the English form the table parser reads ("SNEP: 2× Platinum"),
    one per line. A flag names the country ({{Drapeau|France}}, {{France}}); a certification with no flag first in
    its cell or value counts as SNEP; one after a written code ("FRA : {{Certification|Or}}") keeps that code.
    Unknown countries and levels are left as they were."""
    def flagged(m):
        abbr, level = FR_COUNTRIES.get(m.group("country").strip().lower()), _level(m)
        return f"\n{abbr}: {level}\n" if abbr and level else m.group(0)

    def bare(m):
        level = _level(m)
        return f"{m.group('pre')}{m.group('sp')}SNEP: {level}\n" if level else m.group(0)
    s = _FR_CERT.sub(flagged, s)
    s = _BARE.sub(bare, s)
    return _CODED.sub(lambda m: m.group("code") + (_level(m) or m.group(0)), s)


def _year_of(s: str) -> str:
    m = re.search(r"\b(19[5-9]\d|20\d\d)\b", c.plain(s))
    return m.group(1) if m else ""


def parse_fr(wikitext: str) -> list[dict]:
    """Works with certifications from a French Wikipedia page."""
    text = c.prepare(wikitext)
    text = re.sub(r"\{\{\s*date-?\s*\|([^{}]*)\}\}", lambda m: m.group(1).replace("|", " "), text, flags=re.I)
    works = []
    for start, name, inner in templates(text, r"Discographie des (?:albums|chansons)"):
        kind = "album" if "album" in name.lower() else "single"
        _, p = params("x" + inner)
        year = ""
        for i in sorted({int(k[5:]) for k in p if re.fullmatch(r"titre\d+", k)}):
            if p.get(f"année{i}"):
                year = _year_of(p[f"année{i}"])
            elif kind == "album":
                year = _year_of(p.get(f"détails{i}", "")) or _year_of(p.get(f"date{i}", ""))
            title = c._title(p[f"titre{i}"])
            certs = c.parse_certs(fr_certs_text(p.get(f"certif{i}", "")), kind, year)
            if title and certs:
                works.append({"title": title, "type": kind, "year": year, "certs": certs, "us_peak": None})
    # lists: "** ''Title'' (feat. X) : {{Drapeau|France}} {{Certification|Or}}"
    heads = _headings(text)
    for m in re.finditer(r"^\*+\s*(?:(?:\[\[[^\]]*\]\]|\d{4})\s*:\s*)?''(?P<t>[^'\n]+?)''(?P<rest>[^\n]*)$", text, re.M):
        if "{{" not in m.group("rest"):
            continue
        near = next((h for p_, _, h in reversed(heads) if p_ < m.start()), "")
        kind = "single" if re.search(r"titre|chanson|single|morceau", near, re.I) else _kind_at(heads, m.start())
        year = _year_of(m.group(0).split("''")[0])
        certs = c.parse_certs(fr_certs_text(m.group("rest")).replace("\n", "<br>"), kind, year)
        if certs and (title := c.plain(m.group("t")).strip()):
            works.append({"title": title, "type": kind, "year": year, "certs": certs, "us_peak": None})
    # wikitables ("Certifications" column); US peaks are not read from French tables
    works += [dict(w, us_peak=None) for w in c.parse_tables(fr_certs_text(text)) if w["certs"]]
    return works


# ---------- German ----------

def de_award(code: str) -> list[tuple[str, int]]:
    """"G" -> [(Gold, 1)], "3P" -> [(Platinum, 3)], "D+5P" -> [(Diamond, 1), (Platinum, 5)]; notes in brackets
    ("G (Streaming)") are dropped."""
    out = []
    for part in re.sub(r"\([^)]*\)", "", c.plain(code)).split("+"):
        m = re.fullmatch(r"\s*(\d*)\s*[×x]?\s*([A-Za-z]+)\s*", part)
        if m and (level := DE_LEVELS.get(m.group(2).upper())):
            out.append((level, int(m.group(1) or 1)))
    return out


def parse_de(wikitext: str) -> list[dict]:
    """Works with certifications from {{Charteintrag}} rows of a German Wikipedia page."""
    text = c.prepare(wikitext)
    heads = _headings(text)
    tables = []  # (start, end, kind) of each {{Charttabelle}}
    for start, _, inner in templates(text, "Charttabelle"):
        art = params("x" + inner)[1].get("art", "")
        k = c._kind(c.plain(art)) if art else "other"
        tables.append((start, start + len(inner), k))
    works = []
    for start, _, inner in templates(text, "Charteintrag"):
        _, p = params("x" + inner)
        kind = next((k for s, e, k in tables if s <= start <= e and k != "other"), None) or _kind_at(heads, start)
        year = _year_of(p.get("jahr", ""))
        for i in [""] + sorted({k[5:] for k in p if re.fullmatch(r"titel\d+", k)}, key=int):
            title = c.plain(re.sub(r"<sup>.*?</sup>", "", p.get(f"titel{i}", ""), flags=re.I | re.S))
            if not title:
                continue
            certs = []
            for k, v in p.items():
                m = re.fullmatch(r"a_([a-z]+)" + re.escape(i), k)
                if not m or not v or (i == "" and re.fullmatch(r"a_[a-z]+\d+", k)):
                    continue
                for level, mult in de_award(v):
                    x = c.cert(DE_COUNTRIES.get(m.group(1).upper(), ""), level, mult, kind, year)
                    if x and x not in certs:
                        certs.append(x)
            us = c.plain(p.get(f"pos_us{i}", ""))
            us = int(us) if re.fullmatch(r"\d{1,3}", us) else None
            if certs:
                works.append({"title": title, "type": kind, "year": year, "certs": certs, "us_peak": us})
    return works


def parse(lang: str, wikitext: str) -> list[dict]:
    """All works with certifications from one fr/de page, the same title and type merged."""
    merged: dict[tuple, dict] = {}
    for w in (parse_fr if lang == "fr" else parse_de)(wikitext):
        key = (w["title"].lower(), w["type"])
        if key not in merged:
            merged[key] = w
            continue
        m = merged[key]
        m["certs"] += [x for x in w["certs"] if not any(y["body"] == x["body"] for y in m["certs"])]
        m["year"] = m["year"] or w["year"]
        m["us_peak"] = m["us_peak"] or w["us_peak"]
    return list(merged.values())


# ---------- lookup ----------

def wikidata_pages(qids: list[str], lang: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    """QID -> its <lang>wiki article, and QID -> <lang>wiki titles of its discography items (P358)."""
    article, disco = {}, {}
    for chunk in [qids[i:i + 300] for i in range(0, len(qids), 300)]:
        for r in query(f"""
SELECT ?item ?art ?dt WHERE {{ VALUES ?item {{ {' '.join('wd:' + q for q in chunk)} }}
  OPTIONAL {{ ?a schema:about ?item ; schema:isPartOf <https://{lang}.wikipedia.org/> ; schema:name ?art . }}
  OPTIONAL {{ ?item wdt:P358 ?d . ?b schema:about ?d ; schema:isPartOf <https://{lang}.wikipedia.org/> ;
                schema:name ?dt . }} }}"""):
            q = qid(r["item"])
            if r.get("art"):
                article[q] = r["art"]
            if r.get("dt") and r["dt"] not in disco.setdefault(q, []):
                disco[q].append(r["dt"])
    return article, disco


# templates an artist article uses to point at (or transclude) its discography page
POINTERS = {"de": r"\{\{\s*(?:Eingebundene Diskografie|Hauptartikel)\s*\|\s*([^|}]*Diskografie[^|}]*)",
            "fr": r"\{\{\s*(?:Article détaillé|Loupe|Article principal)\s*\|\s*(Discographie [^|}]+)"}


def find_pages(qids: dict[str, str], lang: str, refresh: bool = False) -> dict[str, list[str]]:
    """spotify_id -> the <lang>wiki pages to read: Wikidata's discography page(s), the artist's article and the
    discography pages that article points to."""
    article, disco = wikidata_pages(sorted(set(qids.values())), lang)
    out = {}
    for s, q in qids.items():
        pages = []
        for t in disco.get(q, []) + ([article[q]] if q in article else []):
            if (p := c.page(t, refresh, lang)) and p[0] not in pages:
                pages.append(p[0])
                for m in re.finditer(POINTERS[lang], p[1], re.I):
                    if (sp := c.page(m.group(1).strip(), refresh, lang)) and sp[0] not in pages:
                        pages.append(sp[0])
        if pages:
            out[s] = pages
    return out


def entries(qids: dict[str, str], today: str, refresh: bool = False) -> dict[str, dict]:
    """spotify_id -> a certifications.json entry from the fr or de wiki (the one with more certifications),
    for the artists that have one with at least one certification."""
    best: dict[str, dict] = {}
    for lang in LANGS:
        for s, ps in find_pages(qids, lang, refresh).items():
            works: list[dict] = []
            used = []  # the pages works came from
            for p in ps:
                seen = {(x["title"].lower(), x["type"]) for x in works}
                new = [w for w in parse(lang, (c.page(p, False, lang) or ("", ""))[1])
                       if (w["title"].lower(), w["type"]) not in seen]
                if new:
                    works += new
                    used.append(p)
            n = sum(len(w["certs"]) for w in works)
            if n and n > sum(len(w["certs"]) for w in best.get(s, {}).get("works", [])):
                best[s] = {"page": used[0], "url": c.wiki_url(used[0], lang), "lang": lang, "fetched": today,
                           "works": works}
                if len(used) > 1:
                    best[s]["pages"] = used
    return best
