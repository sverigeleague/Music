"""kworb.net YouTube artist pages: total views and current daily views of the artist's videos (official channel and
Content ID-tracked uploads that kworb counts). Saved to data/youtube.csv.

The page is found from the link on the artist's kworb Spotify page, from kworb's archive of YouTube artists (each
page's link back to Spotify, data/kworb_youtube_index.csv), from the artist's own YouTube channel (a video uploaded
there that the page lists as the artist's own), or from the name. A page that links back to another Spotify ID is
never taken; a page with no link back is taken only on an identifier (kworb's Spotify page link or the channel's
video), never on the name. Conflicts go to review/youtube_review.csv.
"""
import csv
import glob
import gzip
import html as htmllib
import re
import unicodedata

from .. import storage
from ..config import DATA, RAW
from ..http import get

URL = "https://kworb.net/youtube/artist/{slug}.html"
CSV = DATA / "youtube.csv"
FIELDS = ["date", "spotify_id", "slug", "total_views", "daily_views", "videos", "match"]
# match: backlink (the page links to this Spotify ID), kworb_spotify_link (kworb's page for this Spotify ID links to it;
# the page has no link back), or "channel <ID> video <ID>" (the page lists a video from the artist's own channel)
_int = lambda s: int(s.replace(",", "")) if s and s.replace(",", "").isdigit() else None


def slug_from_spotify_page(spotify_id: str) -> str | None:
    pages = sorted(glob.glob(str(RAW / "kworb" / "artist" / "*" / f"{spotify_id}.html.gz")))
    if not pages:
        return None
    with gzip.open(pages[-1], "rt") as f:
        m = re.search(r'href="[./]*/?youtube/artist/([^"/]+)\.html"', f.read())
    return m[1] if m else None


def slug_guess(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def parse(html: str) -> dict:
    total = re.search(r"Total views:</td><td[^>]*>([\d,]+)<", html)
    daily = re.search(r"Current daily avg:</td><td[^>]*>([\d,]+)<", html)
    videos = len(re.findall(r'href="\.\./video/[^"]+\.html"', html))
    back = re.search(r'spotify/artist/([0-9A-Za-z]{22})_songs\.html', html)
    return {"total_views": _int(total[1]) if total else None, "daily_views": _int(daily[1]) if daily else None,
            "videos": videos, "spotify_id": back[1] if back else None}


_links: list[tuple[str, str]] | None = None


def archive_links() -> list[tuple[str, str]]:
    """kworb's list of the YouTube artists it tracks: (page address, name)."""
    global _links
    if _links is None:
        r = get("https://kworb.net/youtube/archive.html")
        _links = re.findall(r'href="(?:\.\./)?(?:/youtube/)?artist/([^"]+)\.html"[^>]*>(.*?)</a>',
                            r.content.decode("utf-8", "replace")) if r.status_code == 200 else []  # no charset in the header
    return _links


def slug_from_archive(name: str) -> str | None:
    """The archive's page address for this name (names whose address is not the plain name: "jay-z")."""
    return {slug_guess(htmllib.unescape(n)): s for s, n in archive_links()}.get(slug_guess(name))


INDEX = DATA / "kworb_youtube_index.csv"  # every page in kworb's archive: the Spotify ID it links back to, if any
INDEX_FIELDS = ["slug", "name", "spotify_id", "fetched"]


def own_videos(html: str) -> set[str]:
    """IDs of the page's videos that are the artist's own (kworb marks features with "* ")."""
    return set(re.findall(r'<div>(?!\* )<a href="\.\./video/([\w-]{11})\.html"', html))


def page_path(row: dict) -> str:
    return f"kworb/youtube/pages/{row['fetched']}/{row['slug']}.html"


def load_index() -> dict[str, dict]:
    if not INDEX.exists():
        return {}
    with INDEX.open() as f:
        return {r["slug"]: r for r in csv.DictReader(f)}


def update_index(day: str, limit: int | None = None) -> dict[str, dict]:
    """Reads each archive page not yet indexed (once: the link back to Spotify rarely changes) and keeps it in raw/."""
    idx = load_index()
    todo = [(s, n) for s, n in archive_links() if s not in idx][:limit]
    for i, (slug, name) in enumerate(todo):
        row = {"slug": slug, "name": htmllib.unescape(name), "spotify_id": "", "fetched": day}
        try:
            html = storage.read(page_path(row)).decode("utf-8", "replace")  # read today already
        except FileNotFoundError:
            r = get(URL.format(slug=slug))
            html = r.content.decode("utf-8", "replace") if r.status_code == 200 else None
            if html:
                storage.archive(page_path(row), URL.format(slug=slug), r.content)
        if html:
            idx[slug] = {**row, "spotify_id": parse(html)["spotify_id"] or ""}
        if i % 50 == 49 or i == len(todo) - 1:
            with INDEX.open("w", newline="") as f:
                w = csv.DictWriter(f, INDEX_FIELDS)
                w.writeheader()
                w.writerows(sorted(idx.values(), key=lambda x: x["slug"]))
    return idx


def match_by_channel(channel_videos: dict[str, set[str]], pages: dict[str, set[str]]) -> dict[str, list[str]]:
    """spotify_id -> the kworb pages that list one of the videos uploaded to the artist's own channel (channel ID
    from Wikidata or MusicBrainz, video IDs from the channel's public feed) as the artist's own video."""
    out = {}
    for sid, vids in channel_videos.items():
        hits = [slug for slug, own in pages.items() if vids & own]
        if hits:
            out[sid] = hits
    return out


def fetch(spotify_id: str, name: str, day: str, known: tuple[str, str] | None = None) -> dict | None:
    """known: (page address, how it was matched) when the step matched the page by an identifier (the channel's
    videos). A page that links back to another Spotify ID is never taken; one with no link back is taken only from
    kworb's own Spotify page link or a known match, never from the name alone."""
    cands = [known] if known else []
    cands += [(slug_from_spotify_page(spotify_id), "kworb_spotify_link"), (slug_guess(name), ""), (slug_from_archive(name), "")]
    pages: dict[str, str] = {}
    for s, h in cands:
        if s and s not in pages:
            pages[s] = h  # each page once, with the first reason
    for slug, how in pages.items():
        r = get(URL.format(slug=slug))
        if r.status_code != 200:
            continue
        p = parse(r.text)
        if p["total_views"] is None or (p["spotify_id"] or "") not in (spotify_id, "") or not (p["spotify_id"] or how):
            continue  # not this artist's page, or nothing but the name ties it to the artist
        storage.archive(f"kworb/youtube/{day}/{spotify_id}.html", URL.format(slug=slug), r.content)
        return {"date": day, "spotify_id": spotify_id, "slug": slug, **{k: p[k] for k in ("total_views", "daily_views", "videos")},
                "match": "backlink" if p["spotify_id"] == spotify_id else how}
    return None


VIDEOS = DATA / "videos.json"
KEEP = 6


def videos(html: str) -> list[dict]:
    """The page's video table: YouTube video ID, title, total views, yesterday's views, month published."""
    out = []
    for vid, title, views, yday, pub in re.findall(
            r'href="\.\./video/([\w-]{11})\.html">(.*?)</a>.*?<td>([\d,]+)</td>\s*<td>([\d,]*)</td>\s*<td>(\d{4}/\d{2})</td>', html, re.S):
        out.append({"id": vid, "title": htmllib.unescape(re.sub(r"<[^>]+>", "", title)).strip(), "views": _int(views),
                    "yesterday": _int(yday) or 0, "published": pub.replace("/", "-")})
    return out


def update_videos(artists: dict[str, str], day: str) -> int:
    """For Scout's risers (spotify_id -> kworb slug, from data/youtube.csv): the KEEP videos with the most views
    yesterday, saved to data/videos.json. The page must link back to the same Spotify ID. Videos play on the site
    in YouTube's privacy-enhanced player, only on a click."""
    import json
    have = json.loads(VIDEOS.read_text()) if VIDEOS.exists() else {}
    n = 0
    for sid, slug in artists.items():
        r = get(URL.format(slug=slug))
        if r.status_code != 200:
            continue
        html = r.content.decode("utf-8", "replace")
        if parse(html)["spotify_id"] != sid:
            continue
        vids = sorted(videos(html), key=lambda v: -v["yesterday"])[:KEEP]
        if vids:
            have[sid] = {"date": day, "source": "kworb", "slug": slug, "videos": vids}
            n += 1
    VIDEOS.write_text(json.dumps(have, ensure_ascii=False, indent=0))
    return n


def save(rows: list[dict]) -> None:
    if CSV.exists() and CSV.open().readline().strip().split(",") != FIELDS:  # rows from before the match column
        with CSV.open() as f:
            old = list(csv.DictReader(f))
        with CSV.open("w", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows({**r, "match": r.get("match") or "backlink"} for r in old)  # only backlinks were taken then
    new = not CSV.exists()
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def load_latest() -> dict[str, dict]:
    out = {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                if r["spotify_id"] not in out or r["date"] >= out[r["spotify_id"]]["date"]:
                    out[r["spotify_id"]] = r
    return out
