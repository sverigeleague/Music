"""One- or two-sentence artist descriptions for the artist page (owner, 2026-10-25): the opening of the artist's English
Wikipedia article, from Wikipedia's page summary API (free, no key). The article is the one Wikidata links to the
artist (wikipedia.articles, cached in data/wikipedia_pageviews.csv), so no name matching is involved. Wikipedia text
is CC BY-SA 4.0: shown with the article's link and the licence. Saved to data/descriptions.json.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import quote

from ..config import DATA
from ..http import get

API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
OUT = DATA / "descriptions.json"
MAX_CHARS = 320
# a full stop after these is not the end of a sentence ("Sr.", "St. Louis", "J. Cole", "U.S.")
ABBREV = {"jr", "sr", "st", "mr", "mrs", "ms", "dr", "inc", "ltd", "co", "vs", "no", "feat", "ft", "mt", "ave"}


def load() -> dict[str, dict]:
    return json.loads(OUT.read_text()) if OUT.exists() else {}


def first_sentences(text: str, n: int = 2, max_chars: int = MAX_CHARS) -> str:
    """The first n sentences, or fewer when two would run past max_chars (always at least one)."""
    text = re.sub(r"\s+", " ", re.sub(r"\s*\([^()]*\)", "", text or "")).strip()  # drop "(born ...)" asides
    out, start = [], 0
    for m in re.finditer(r"[.!?](?=\s+[\"“A-Z0-9])", text):
        word = re.findall(r"([A-Za-z.]+)$", text[start:m.start()])
        prev = word[0].lower().rstrip(".") if word else ""
        if prev in ABBREV or len(prev) == 1 or "." in prev:  # an abbreviation or an initial
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
        if len(out) == n:
            break
    else:
        if len(out) < n and text[start:].strip():
            out.append(text[start:].strip())
    while len(out) > 1 and len(" ".join(out)) > max_chars:
        out.pop()
    return " ".join(out)


def summary(title: str) -> dict | None:
    r = get(API + quote(title.replace(" ", "_"), safe=""), params={"redirect": "true"})
    if r.status_code != 200:
        return None
    j = r.json()
    if j.get("type") == "disambiguation" or not j.get("extract"):
        return None
    return {"text": first_sentences(j["extract"]), "article": j.get("title") or title,
            "url": (j.get("content_urls") or {}).get("desktop", {}).get("page")
            or "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")),
            "source": "wikipedia", "fetched": date.today().isoformat()}


def update(articles: dict[str, str], refresh: bool = False, workers: int = 2) -> int:
    """articles: spotify_id -> English Wikipedia title. Fetches the ones not stored yet. Returns the count stored."""
    out = load()
    todo = [(s, t) for s, t in articles.items() if refresh or s not in out]
    with ThreadPoolExecutor(workers) as pool:
        for i, ((s, _), d) in enumerate(zip(todo, pool.map(lambda st: summary(st[1]), todo)), 1):
            if d and d["text"]:
                out[s] = d
            if i % 100 == 0:  # progress survives an interrupted run
                OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    return sum(1 for s in articles if s in out)
