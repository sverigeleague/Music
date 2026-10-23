"""kworb.net: Spotify monthly listeners (top 2,500, daily) and per-artist stream totals.

kworb compiles these from Spotify's public pages; it publishes no terms and its robots.txt allows all. Use is
private and credited (DECISIONS.md, 2026-10-23); its tables are not republished as they are.
"""
import csv
import re
from datetime import date

from .. import storage
from ..config import DATA
from ..http import get

LISTENERS_URL = "https://kworb.net/spotify/listeners.html"
ARTIST_URL = "https://kworb.net/spotify/artist/{id}_songs.html"

LISTENERS_CSV = DATA / "spotify_listeners.csv"
LISTENER_FIELDS = ["date", "spotify_id", "name", "rank", "monthly_listeners", "daily_change", "peak_rank",
                   "peak_listeners"]
STREAMS_CSV = DATA / "spotify_streams.csv"
STREAM_FIELDS = ["date", "spotify_id", "total_streams", "lead_streams", "solo_streams", "feature_streams",
                 "total_daily", "lead_daily", "solo_daily", "feature_daily", "tracks", "lead_tracks",
                 "feature_tracks", "top_track", "top_track_streams"]

_int = lambda s: int(s.replace(",", "")) if s and s.strip().lstrip("-+").replace(",", "").isdigit() else None
_text = lambda s: re.sub(r"<[^>]+>", "", s).strip()


def parse_updated(html: str) -> str | None:
    m = re.search(r"Last updated:\s*(\d{4})/(\d{2})/(\d{2})", html)
    return f"{m[1]}-{m[2]}-{m[3]}" if m else None


def parse_listeners(html: str) -> list[dict]:
    """Rows of listeners.html: rank, artist (link holds the Spotify ID), listeners, daily change, peak, peak listeners."""
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        link = re.search(r'artist/([0-9A-Za-z]{22})_songs\.html">(.*?)</a>', row, re.S)
        if not link or len(cells) < 5:
            continue
        # page 1 has a peak-rank column; pages 2-11 (ranks 2,501 on) do not
        peak_rank, peak = (_int(_text(cells[4])), _int(_text(cells[5]))) if len(cells) >= 6 else (None, _int(_text(cells[4])))
        out.append({"spotify_id": link[1], "name": _unescape(_text(link[2])), "rank": _int(_text(cells[0])),
                    "monthly_listeners": _int(_text(cells[2])), "daily_change": _int(_text(cells[3])),
                    "peak_rank": peak_rank, "peak_listeners": peak})
    return out


def parse_artist(html: str) -> dict:
    """The summary table of an artist page (Total / As lead / Solo / As feature) and the top track."""
    names = {"Streams": ["total_streams", "lead_streams", "solo_streams", "feature_streams"],
             "Daily": ["total_daily", "lead_daily", "solo_daily", "feature_daily"],
             "Tracks": ["tracks", "lead_tracks", "solo_tracks", "feature_tracks"]}
    out = {}
    rows = re.findall(r"<tr>(.*?)</tr>", html, re.S)
    for row in rows:
        cells = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) == 5 and cells[0] in names:
            out.update(zip(names[cells[0]], [_int(c) for c in cells[1:]]))
    out.pop("solo_tracks", None)
    # first song row (its title cell holds a link)
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) >= 2 and "<a" in cells[0]:
            out["top_track"] = _unescape(_text(cells[0])).lstrip("* ").strip()
            out["top_track_streams"] = _int(_text(cells[1]))
            break
    return out


def parse_songs(html: str) -> list[dict]:
    """Every song row of an artist page: Spotify track ID, title, lifetime and daily streams; `feature` when the
    artist is a featured guest (kworb marks those rows with *)."""
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        m = re.search(r'<td class="text"><div>(\*?\s*)<a href="https://open\.spotify\.com/track/([0-9A-Za-z]{22})"'
                      r'[^>]*>(.*?)</a></div></td><td>([\d,]+)</td><td>([\d,]+|--)</td>', row, re.S)
        if m:
            out.append({"track_id": m[2], "title": _unescape(_text(m[3])), "total": _int(m[4]),
                        "daily": _int(m[5]) or 0, "feature": "*" in m[1]})
    return out


def _unescape(s: str) -> str:
    import html
    return html.unescape(s)


PAGES = 11  # listeners.html, listeners2.html ... listeners11.html: ranks 1 to about 25,000 (500,000+ listeners)


def page_url(n: int) -> str:
    return LISTENERS_URL if n == 1 else LISTENERS_URL.replace(".html", f"{n}.html")


def fetch_listeners(today: str | None = None, archive_all: bool = False) -> tuple[str, list[dict]]:
    """All listener pages. Page 1 (top 2,500) is archived every day; pages 2-11 only when archive_all (weekly), to
    keep the raw archive near 50 MB a year."""
    day, rows = None, []
    for n in range(1, PAGES + 1):
        r = get(page_url(n))
        if r.status_code == 404:
            break
        r.raise_for_status()
        page = parse_listeners(r.text)
        if n == 1:
            day = parse_updated(r.text) or today or date.today().isoformat()
            if len(page) < 2000:
                raise RuntimeError(f"kworb listeners page parsed only {len(page)} rows: layout changed?")
        if n == 1 or archive_all:
            storage.archive(f"kworb/listeners/{day}.html" if n == 1 else f"kworb/listeners/{day}-p{n}.html",
                            page_url(n), r.content)
        rows += page
        if len(page) < 2500:
            break
    return day, rows


def save_listeners(day: str, rows: list[dict]) -> int:
    """Append a day's rows for artists not yet stored for that day. Returns rows written."""
    seen = set()
    if LISTENERS_CSV.exists():
        with LISTENERS_CSV.open() as f:
            seen = {r["spotify_id"] for r in csv.DictReader(f) if r["date"] == day}
    new = not LISTENERS_CSV.exists()
    n = 0
    with LISTENERS_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, LISTENER_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            if r["spotify_id"] not in seen:
                w.writerow({"date": day, **r})
                n += 1
    return n


def fetch_artist(spotify_id: str) -> dict:
    url = ARTIST_URL.format(id=spotify_id)
    r = get(url)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    day = parse_updated(r.text) or date.today().isoformat()
    storage.archive(f"kworb/artist/{day}/{spotify_id}.html", url, r.content)
    return {"date": day, "spotify_id": spotify_id, **parse_artist(r.text)}


def save_streams(rows: list[dict]) -> None:
    have = set()
    if STREAMS_CSV.exists():
        with STREAMS_CSV.open() as f:
            have = {(r["date"], r["spotify_id"]) for r in csv.DictReader(f)}
    new = not STREAMS_CSV.exists()
    with STREAMS_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, STREAM_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in rows:
            if r and (r["date"], r["spotify_id"]) not in have:
                w.writerow(r)
