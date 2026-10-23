"""Pipeline steps. python -m src.run <step>

  snapshot  kworb top 2,500 by monthly listeners: raw page archived; rows for tracked artists kept (daily)
  registry  candidates (Wikidata hip-hop genre + Spotify ID) in the top 2,500 -> details, MusicBrainz votes, genre
            decision -> registry/artists.csv and review/genre_review.csv
  streams   kworb artist pages (total and daily streams, lead vs feature) for hip-hop and review artists
  deezer    Deezer fans for hip-hop artists not yet matched
  photos    Wikimedia Commons photos for hip-hop artists not yet tried
  youtube   YouTube total and daily views (kworb.net), for hip-hop artists not yet fetched this month
  ytapi     YouTube channel subscribers and views (YouTube Data API; needs the secret YOUTUBE_API_KEY)
  countries kworb's weekly Spotify top 200 in 76 countries: where each hip-hop artist's songs are streamed
  labels    the label on each hip-hop artist's releases of the last 2 years (Deezer), for the signed/unsigned status
  dates     first release dates from Deezer for the songs behind 90% of each hip-hop artist's daily streams
  dates-retry  the same, and looks up again the songs that found no date
  mbdates   MusicBrainz first release dates for the ISRCs Deezer found, and a title search for songs it did not
            match (can run alongside `dates`)
"""
import csv
import json
import sys
from datetime import datetime, timezone

from . import current, genre, photos
from .collectors import deezer, deezer_releases, kworb, kworb_countries, kworb_youtube, musicbrainz, release_dates, wikidata, youtube_api
from .config import DATA, REGISTRY, REVIEW

ARTISTS = REGISTRY / "artists.csv"
ARTIST_FIELDS = ["spotify_id", "name", "genre", "genre_basis", "reviewed", "wikidata_id", "musicbrainz_id",
                 "country", "born", "active_since", "labels", "major", "youtube_channel", "instagram", "tiktok", "x",
                 "deezer_id", "deezer_fans", "deezer_match", "image"]
WIKIDATA_CACHE = DATA / "wikidata.json"
CANDIDATES = DATA / "wikidata_candidates.json"
PHOTOS = DATA / "photos.json"
GENRE_REVIEW = REVIEW / "genre_review.csv"


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_artists() -> dict[str, dict]:
    if not ARTISTS.exists():
        return {}
    with ARTISTS.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}


def save_artists(rows: dict[str, dict]) -> None:
    with ARTISTS.open("w", newline="") as f:
        w = csv.DictWriter(f, ARTIST_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: r["name"].casefold()):
            w.writerow(r)


def _json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def latest_listeners() -> list[dict]:
    """The newest archived top-2,500 page, parsed (all rows, not only the tracked ones)."""
    import gzip
    from .config import RAW
    files = sorted((RAW / "kworb" / "listeners").glob("*.html.gz"))
    if not files:
        raise SystemExit("no listeners snapshot yet: run `python -m src.run snapshot` first")
    with gzip.open(files[-1], "rt") as f:
        return kworb.parse_listeners(f.read())


def snapshot() -> None:
    day, rows = kworb.fetch_listeners(today())
    tracked = {s for s, a in load_artists().items() if a["genre"] != "other"} | set(_json(CANDIDATES, []))
    kept = [r for r in rows if r["spotify_id"] in tracked or not tracked]
    print(f"{day}: {len(rows)} artists on the page, {kworb.save_listeners(day, kept)} rows stored")


def registry(mb_limit: int | None = None) -> None:
    top = {r["spotify_id"]: r for r in latest_listeners()}
    cands = wikidata.hip_hop_spotify_ids()
    known = load_artists()
    # candidates: Wikidata hip-hop artists in today's top 2,500, plus every artist already in the registry
    ids = sorted({s for s in cands if s in top} | set(known))
    CANDIDATES.write_text(json.dumps(ids))
    wd = wikidata.details(ids)
    WIKIDATA_CACHE.write_text(json.dumps({k: {**v, "majors": sorted(v["majors"])} for k, v in wd.items()},
                                         ensure_ascii=False, indent=0))
    mb = musicbrainz.update({s: wd.get(s, {}).get("musicbrainz_id") for s in ids}, limit=mb_limit)
    over = genre.overrides()
    out = {}
    for s in ids:
        d, prev = wd.get(s, {}), known.get(s, {})
        votes = musicbrainz.genres_of(mb.get(s, {}))
        decision, basis = genre.decide(votes, d.get("genres", []))
        reviewed = ""
        if s in over:
            decision, basis, reviewed = over[s]["decision"], f"owner: {over[s]['note'] or over[s]['decision']}", over[s]["date"]
        out[s] = {**prev, "spotify_id": s, "name": (top.get(s) or prev).get("name", ""), "genre": decision,
                  "genre_basis": basis, "reviewed": reviewed, "wikidata_id": d.get("qid", ""),
                  "musicbrainz_id": d.get("musicbrainz_id") or mb.get(s, {}).get("musicbrainz_id", ""),
                  "country": "" if "people" in d.get("country", "") else d.get("country", ""), "born": d.get("born", ""), "active_since": d.get("active_since", ""),
                  "labels": "|".join(d.get("labels", [])), "major": "|".join(sorted(d.get("majors", []))),
                  "youtube_channel": d.get("youtube_channel", ""), "instagram": d.get("instagram", ""),
                  "tiktok": d.get("tiktok", ""), "x": d.get("x", ""), "image": d.get("image", "")}
    save_artists(out)
    write_review(out, top, mb, wd)
    counts = {}
    for r in out.values():
        counts[r["genre"]] = counts.get(r["genre"], 0) + 1
    print(f"{len(out)} artists: {counts}")


def write_review(rows, top, mb, wd) -> None:
    """Borderline and Latin artists for the owner, biggest first. Approving: a row in registry/genre_overrides.csv."""
    REVIEW.mkdir(exist_ok=True)
    items = [r for r in rows.values() if r["genre"] in ("review", "latin") and not r["reviewed"]]
    items.sort(key=lambda r: -(top.get(r["spotify_id"], {}).get("monthly_listeners") or 0))
    with GENRE_REVIEW.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["spotify_id", "name", "monthly_listeners", "suggested", "basis", "musicbrainz_top_genres",
                    "wikidata_genres", "spotify_url"])
        for r in items:
            s = r["spotify_id"]
            w.writerow([s, r["name"], top.get(s, {}).get("monthly_listeners", ""), r["genre"], r["genre_basis"],
                        ", ".join(f"{g} ({n})" for g, n in musicbrainz.genres_of(mb.get(s, {}))[:5]),
                        ", ".join(g for g, _h, _l in wd.get(s, {}).get("genres", [])),
                        f"https://open.spotify.com/artist/{s}"])
    print(f"{len(items)} artists in {GENRE_REVIEW.relative_to(REVIEW.parent)}")


def tracked(genres=("hip_hop",)) -> list[dict]:
    return [a for a in load_artists().values() if a["genre"] in genres]


def streams(limit: int | None = None) -> None:
    have = set()
    if kworb.STREAMS_CSV.exists():
        with kworb.STREAMS_CSV.open() as f:
            have = {r["spotify_id"] for r in csv.DictReader(f) if r["date"][:7] == today()[:7]}
    todo = [a["spotify_id"] for a in tracked(("hip_hop", "review")) if a["spotify_id"] not in have][:limit]
    rows = []
    for s in todo:
        rows.append(kworb.fetch_artist(s))
        if len(rows) % 25 == 0:
            kworb.save_streams(rows)
            rows = []
    kworb.save_streams(rows)
    print(f"stream totals fetched for {len(todo)} artists")


def deezer_step() -> None:
    rows = load_artists()
    n = 0
    for a in rows.values():
        if a["genre"] == "hip_hop" and not a.get("deezer_match"):
            a.update({k: v for k, v in deezer.match(a["name"]).items()})
            n += 1
    save_artists(rows)
    print(f"Deezer: {n} artists matched")


def photos_step(limit: int | None = None) -> None:
    done = _json(PHOTOS, {})
    todo = [a for a in tracked() if a.get("image") and a["spotify_id"] not in done][:limit]
    for a in todo:
        done[a["spotify_id"]] = photos.fetch(a["spotify_id"], a["image"]) or {}
        PHOTOS.write_text(json.dumps(done, ensure_ascii=False, indent=0))
    print(f"photos: {sum(1 for v in done.values() if v)} of {len(done)} tried have a free-licence photo")


def youtube_step(limit: int | None = None) -> None:
    have = {s for s, r in kworb_youtube.load_latest().items() if r["date"][:7] == today()[:7]}
    todo = [a for a in tracked() if a["spotify_id"] not in have][:limit]
    rows = [r for r in (kworb_youtube.fetch(a["spotify_id"], a["name"], today()) for a in todo) if r]
    kworb_youtube.save(rows)
    print(f"YouTube: {len(rows)} of {len(todo)} artists found")


def ytapi_step() -> None:
    n = youtube_api.update({a["spotify_id"]: a["youtube_channel"] for a in tracked() if a["youtube_channel"]})
    print("YouTube API: no YOUTUBE_API_KEY, skipped" if n is None else f"YouTube API: {n} channels")


def countries_step() -> None:
    week, n = kworb_countries.update({a["spotify_id"] for a in tracked(("hip_hop", "review"))})
    print(f"country charts, week ending {week}: {n} rows for tracked artists")


def labels_step() -> None:
    ids = [a["deezer_id"] for a in tracked() if a.get("deezer_id") and a.get("deezer_match") == "exact"]
    print(f"release labels: {deezer_releases.update(ids)} new releases read for {len(ids)} artists")


def dates_step(limit: int | None = None, retry: bool = False) -> None:
    order = {r["spotify_id"]: r["rank"] for r in latest_listeners()}
    todo = []
    for a in sorted(tracked(), key=lambda a: order.get(a["spotify_id"], 1e9)):
        p = current.pages(a["spotify_id"])
        if p:
            todo += [(a["spotify_id"], a["name"], s["track_id"], s["title"]) for s in current.to_date(current.songs(p[-1][1]))]
    cache = release_dates.update(todo, limit=limit, retry=retry)
    have = sum(1 for _a, _n, t, _ in todo if cache.get(t, {}).get("first_release"))
    print(f"release dates: {have} of {len(todo)} songs dated")


if __name__ == "__main__":
    step, args = sys.argv[1], sys.argv[2:]
    lim = int(args[0]) if args else None
    {"snapshot": snapshot, "registry": lambda: registry(lim), "streams": lambda: streams(lim),
     "deezer": deezer_step, "youtube": lambda: youtube_step(lim),
     "ytapi": ytapi_step, "labels": labels_step, "countries": countries_step, "photos": lambda: photos_step(lim), "dates": lambda: dates_step(lim), "dates-retry": lambda: dates_step(lim, retry=True),
     # the title search first: it adds coverage; the ISRC lookups then correct dates already found
     "mbdates": lambda: print(f"MusicBrainz: {release_dates.update_musicbrainz_search(lim)} undated songs searched, "
                              f"{release_dates.update_musicbrainz(lim)} ISRCs looked up")}[step]()
