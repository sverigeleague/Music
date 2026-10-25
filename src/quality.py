"""Data quality page (site #/quality): open review queues, the latest date in each source file, the corrections log and
the ranking method's versions. Read from files already in the repository; nothing is fetched and nothing new is claimed.
"""
import csv
import json
import re
from pathlib import Path

from .config import DATA, REGISTRY, REVIEW, ROOT

# [what, file in data/, date column, source, how often it is read]
SOURCES = [
    ("Monthly listeners", "spotify_listeners.csv", "date", "kworb.net (Spotify's public counts)", "daily"),
    ("Spotify streams", "spotify_streams.csv", "date", "kworb.net artist pages", "daily, small artists irregularly"),
    ("Listener history", "listener_history.csv", "date", "our daily log and the Internet Archive", "daily"),
    ("Scout score log", "scout_history.csv", "date", "our daily log", "daily"),
    ("YouTube views", "youtube.csv", "date", "kworb.net YouTube pages", "daily"),
    ("Wikipedia page views", "wikipedia_pageviews.csv", "month", "Wikimedia API", "monthly"),
    ("Apple Music charts", "apple_charts.csv", "date", "Apple's public RSS feed", "daily"),
    ("Spotify country charts", "spotify_country_charts.csv", "week", "kworb.net (Spotify weekly top 200)", "weekly"),
    ("Shazam charts", "shazam.csv", "date", "Shazam's public charts", "daily"),
    ("US radio", "radio.csv", "date", "kworb.net (US airplay)", "daily"),
    ("Release labels", "release_labels.csv", "checked", "Deezer", "monthly"),
    ("Song release dates", "track_dates.csv", "checked", "Deezer and MusicBrainz", "monthly"),
    ("Song credits", "credits.csv", "checked", "MusicBrainz", "monthly"),
    ("Company financials", "financials.csv", "filed", "SEC, Companies House and company reports", "quarterly"),
]

# [file in review/, genre, what it holds, how a row is settled: "genre" or "label" override, or None (all open)]
QUEUES = [
    ("genre_review.csv", "hip_hop", "Borderline genre: is the artist hip-hop? Outside the list until decided", "genre"),
    ("hiphop_deezer_disagree.csv", "hip_hop", "Hip-hop by our rule, not by Deezer's release genres", "genre"),
    ("label_review.csv", "hip_hop", "Label owner unknown, or resting on the label name only", "label"),
    ("country_review_batch1.csv", "country", "Borderline genre: is the artist country? (batch 1)", "genre"),
    ("country_review_batch2.csv", "country", "Borderline genre: is the artist country? (batch 2)", "genre"),
    ("youtube_review.csv", None, "YouTube page that could not be matched by an identifier", None),
]


def _ids(path: Path) -> set[str]:
    return {r["spotify_id"] for r in csv.DictReader(path.open())} if path.exists() else set()


def queues(genre: str, review: Path = REVIEW, registry: Path = REGISTRY) -> list[dict]:
    """Rows per review file for this genre, and how many are still open (no owner override yet)."""
    settled = {"genre": _ids(registry / "genre_overrides.csv"), "label": _ids(registry / "label_overrides.csv")}
    out = []
    for name, g, what, by in QUEUES:
        path = review / name
        if not path.exists() or (g and g != genre):
            continue
        rows = [r for r in csv.DictReader(path.open()) if g or r.get("genre", genre) == genre]
        done = sum(1 for r in rows if by and r.get("spotify_id") in settled[by])
        out.append({"file": f"review/{name}", "what": what, "rows": len(rows), "open": len(rows) - done})
    return out


def latest(path: Path, column: str) -> dict | None:
    """First and latest value of a date column (ISO dates sort as text); None when the file or column is missing."""
    if not path.exists():
        return None
    vals = [v[:10] for r in csv.DictReader(path.open()) if re.match(r"\d{4}-\d{2}", v := (r.get(column) or ""))]
    return {"first": min(vals), "latest": max(vals), "rows": len(vals)} if vals else None


def sources(data: Path = DATA) -> list[dict]:
    out = []
    for what, name, col, src, cadence in SOURCES:
        d = latest(data / name, col)
        if d:
            out.append({"what": what, "source": src, "cadence": cadence, **d})
    return out


def corrections(genre: str, registry: Path = REGISTRY) -> list[dict]:
    """The corrections log (registry/corrections.csv), this genre's rows and those for all genres, newest first."""
    path = registry / "corrections.csv"
    rows = [r for r in csv.DictReader(path.open()) if r["genre"] in (genre, "all")] if path.exists() else []
    return sorted(rows, key=lambda r: r["date"], reverse=True)


def method_versions(path: Path = ROOT / "docs" / "METHODOLOGY.md") -> list[dict]:
    """The ranking method's change log: lines "- 1.2 (2026-10-24): text" under "## Change log"."""
    if not path.exists():
        return []
    text = path.read_text().split("## Change log", 1)[-1]
    out = []
    for m in re.finditer(r"^- (\d+\.\d+) \((\d{4}-\d{2}-\d{2})\): (.+?)(?=^- |\Z|^#)", text, re.M | re.S):
        out.append({"version": m.group(1), "date": m.group(2), "change": " ".join(m.group(3).split())})
    return out


def summary(genre: str) -> dict:
    return {"queues": queues(genre), "sources": sources(), "corrections": corrections(genre), "method": method_versions()}


if __name__ == "__main__":
    print(json.dumps(summary("hip_hop"), indent=1)[:3000])
