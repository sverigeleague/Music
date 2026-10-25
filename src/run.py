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
  apple     Apple Music's daily top 100 songs in 25 countries (public RSS feed)
  backfill  weekly listener history since 2023 from the Internet Archive's copies of kworb's page (one-off; Actions)
  mblabels  owners of the label names we cannot place, from MusicBrainz label relationships (monthly, new names only)
  scoutlog  today's Scout scores and monthly listeners for the top 1,000 -> data/scout_history.csv (daily; the
            back-test reads it after 90 days)
  reports   report PDFs with no XBRL (registry/report_pdfs.csv) read by Claude: Haiku, checks, Opus fallback (needs
            the ANTHROPIC_API_KEY secret)
  financials label groups' income statement, balance sheet and cash flow from XBRL filings (SEC, ESEF; quarterly)
            and the list of the majors' UK accounts at Companies House (data/uk_accounts.csv, read by `reports`)
            and Sony's Music segment from its results releases on EDGAR (data/sony_music.csv)
  videos    the busiest YouTube videos of Scout's risers from kworb's YouTube pages -> data/videos.json (weekly)
  credits   producer and songwriter credits of each artist's 3 biggest songs from MusicBrainz -> data/credits.csv
  radio     US radio airplay audience per song (kworb.net/radio; today and the last 30 archived days) -> data/radio.csv
  shazam    Shazam's charts (world, 15 countries, 10 hip-hop, 31 cities) -> data/shazam.csv; an internal Scout signal (daily)
  wikidata-from-mb  Wikidata items linked from MusicBrainz for artists Wikidata has no Spotify ID for (monthly)
  deezer-audit re-check name-only Deezer matches by song titles, then ISRC; corrects wrong ones (monthly)
  deezer-isrc  confirm Deezer IDs of shared or unmatched names from the artist's own songs' ISRCs
  countrycrawl    country artists below the 500k floor from Deezer's related-artists graph -> data/country_deezer.csv (monthly)
  certifications  RIAA, BPI and other certifications and US chart peaks from English Wikipedia discographies -> data/certifications.json (monthly)
  awards    award wins and nominations from Wikidata (Grammy, BET, AMA, MTV, BRIT...) -> data/awards.json (monthly)
  pageviews English Wikipedia page views, 24 months, for hip-hop artists with a Wikidata item (monthly)
"""
import csv
import json
import sys
from datetime import datetime, timezone

from . import current, genre, photos
from .collectors import apple_charts, deezer, musicbrainz_labels, wayback, deezer_releases, kworb, kworb_countries, kworb_youtube, musicbrainz, release_dates, wikidata, wikipedia, youtube_api
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
    """The newest archived listener pages, parsed: page 1 from the latest day, pages 2-11 from the latest weekly
    archive (all rows, not only the tracked ones; an artist appears once, on its newest page)."""
    import gzip
    import re as _re
    from .config import RAW
    files = sorted((RAW / "kworb" / "listeners").glob("*.html.gz"))
    if not files:
        raise SystemExit("no listeners snapshot yet: run `python -m src.run snapshot` first")
    newest: dict[int, object] = {}
    for f in files:  # sorted by name: date first, so later files win
        m = _re.match(r"(\d{4}-\d{2}-\d{2})(?:-p(\d+))?\.html\.gz$", f.name)
        if m:
            newest[int(m[2] or 1)] = f
    rows: dict[str, dict] = {}
    for n in sorted(newest, reverse=True):  # page 1 last, so today's top 2,500 overrides last week's pages
        with gzip.open(newest[n], "rt") as fh:
            for r in kworb.parse_listeners(fh.read()):
                rows[r["spotify_id"]] = r
    return sorted(rows.values(), key=lambda r: r["monthly_listeners"] or 0, reverse=True)


def snapshot(archive_all: bool | None = None) -> None:
    """Daily: all listener pages (about 25,000 artists); rows kept for tracked artists. The raw pages 2-11 are archived
    on Mondays and whenever none is newer than 7 days."""
    from .config import RAW
    if archive_all is None:
        from datetime import timedelta
        now = datetime.now(timezone.utc).date()
        recent = sorted((RAW / "kworb" / "listeners").glob("*-p2.html.gz"))
        archive_all = now.weekday() == 0 or not recent or recent[-1].name[:10] < (now - timedelta(days=7)).isoformat()
    day, rows = kworb.fetch_listeners(today(), archive_all=archive_all)
    tracked = {s for s, a in load_artists().items() if a["genre"] != "other"} | set(_json(CANDIDATES, []))
    kept = [r for r in rows if r["spotify_id"] in tracked or not tracked]
    print(f"{day}: {len(rows)} artists on the pages, {kworb.save_listeners(day, kept)} rows stored"
          f"{' (all pages archived)' if archive_all else ''}")


def registry(mb_limit: int | None = None) -> None:
    from .collectors import deezer_genres
    top = {r["spotify_id"]: r for r in latest_listeners()}
    cands = wikidata.hip_hop_spotify_ids()
    country_cands = wikidata.country_spotify_ids()
    known = load_artists()
    dz = deezer_genres.load()
    # candidates: in kworb's listener pages (about 25,000 artists), tagged hip-hop on Wikidata or with most releases
    # filed under Rap/Hip Hop on Deezer; plus every artist already in the registry
    dz_rap = {s for s, r in dz.items() if r.get("match") in ("exact", "titles") and r.get("rap_share") not in ("", None)
              and float(r["rap_share"]) >= 0.5}
    dz_country = {s for s, r in dz.items() if r.get("match") in ("exact", "titles") and r.get("country_share") not in ("", None)
                  and float(r["country_share"]) >= 0.3}
    ids = sorted({s for s in cands if s in top} | {s for s in dz_rap if s in top} | set(known)
                 | {s for s in country_cands if s in top} | {s for s in dz_country if s in top})
    CANDIDATES.write_text(json.dumps(ids))
    wd = wikidata.details(ids)
    WIKIDATA_CACHE.write_text(json.dumps({k: {**v, "majors": sorted(v["majors"])} for k, v in wd.items()},
                                         ensure_ascii=False, indent=0))
    mb = musicbrainz.update({s: wd.get(s, {}).get("musicbrainz_id") for s in ids}, limit=mb_limit)
    over = genre.overrides()
    # Deezer matches confirmed from the artist's own songs (ISRCs or titles) count like a Wikidata identity
    sure = {s for s, a in known.items() if a.get("deezer_match") in ("isrc", "titles")
            and str(a.get("deezer_id")) == str(dz.get(s, {}).get("deezer_id"))} | {s for s, r in dz.items() if r.get("match") == "titles"}
    out = {}
    for s in ids:
        d, prev = wd.get(s, {}), known.get(s, {})
        votes = musicbrainz.genres_of(mb.get(s, {}))
        decision, basis = genre.decide(votes, d.get("genres", []), dz.get(s), wikidata=bool(d.get("qid")) or s in sure,
                                       country=d.get("country", ""))
        if decision in ("other", "review"):  # a second genre: country (owner, 2026-10-24)
            c = genre.decide_country(votes, d.get("genres", []), dz.get(s), wikidata=bool(d.get("qid")) or s in sure)
            if c and not (decision == "review" and c[0] == "review"):
                decision, basis = c[0], f"{c[1]}; hip-hop rule: {decision}"
            elif c:
                basis = f"{basis}; also country? {c[1]}"
        reviewed = ""
        if s in over:
            decision, basis, reviewed = over[s]["decision"], f"owner: {over[s]['note'] or over[s]['decision']}", over[s]["date"]
        out[s] = {**prev, "spotify_id": s, "name": (top.get(s) or prev).get("name", ""), "genre": decision,
                  "genre_basis": basis, "reviewed": reviewed, "wikidata_id": d.get("qid") or prev.get("wikidata_id", ""),
                  "musicbrainz_id": d.get("musicbrainz_id") or mb.get(s, {}).get("musicbrainz_id", ""),
                  "country": "" if "people" in d.get("country", "") else d.get("country", ""), "born": d.get("born", ""), "active_since": d.get("active_since", ""),
                  "labels": "|".join(d.get("labels", [])), "major": "|".join(sorted(d.get("majors", []))),
                  "youtube_channel": d.get("youtube_channel", ""), "instagram": d.get("instagram", ""),
                  "tiktok": d.get("tiktok", ""), "x": d.get("x", ""), "image": d.get("image") or prev.get("image", "")}
        if not out[s].get("deezer_match") and s in dz and dz[s].get("deezer_id"):
            out[s].update(deezer_id=dz[s]["deezer_id"], deezer_fans=dz[s]["fans"], deezer_match=dz[s]["match"])
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


TOP_N = 1000  # artists the per-artist steps cover: the top 1,000 hip-hop artists by monthly listeners


GENRE = "hip_hop"  # set with --genre=country: the per-artist steps then cover that genre's top artists


def tracked(genres=None, top_n: int | None = TOP_N) -> list[dict]:
    """Artists of these genres, biggest first by today's monthly listeners; the per-artist steps take the top 1,000."""
    genres = genres or (GENRE,)
    ml = {r["spotify_id"]: r["monthly_listeners"] or 0 for r in latest_listeners()}
    rows = sorted((a for a in load_artists().values() if a["genre"] in genres), key=lambda a: -ml.get(a["spotify_id"], 0))
    return rows[:top_n] if top_n else rows


def streams(limit: int | None = None) -> None:
    have = set()
    if kworb.STREAMS_CSV.exists():
        with kworb.STREAMS_CSV.open() as f:
            have = {r["spotify_id"] for r in csv.DictReader(f) if r["date"][:7] == today()[:7]}
    todo = [a["spotify_id"] for a in tracked() if a["spotify_id"] not in have][:limit]  # the top 1,000 hip-hop
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
        if a["genre"] == GENRE and not a.get("deezer_match"):
            a.update({k: v for k, v in deezer.match(a["name"]).items()})
            n += 1
    save_artists(rows)
    print(f"Deezer: {n} artists matched")


def deezer_isrc_step(limit: int | None = None) -> None:
    """Artists whose name several Deezer artists share (or none matched): confirm the Deezer ID from their own songs'
    ISRCs (the 5 biggest songs as lead with a known ISRC)."""
    rows, dates, n, todo = load_artists(), release_dates.load(), 0, []
    for a in tracked(("hip_hop",)) + tracked(("country",)):
        if a.get("deezer_match") in deezer.CONFIRMED:
            continue
        p = current.pages(a["spotify_id"])
        songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"]) if p else []
        isrcs = [c for x in songs if (c := dates.get(x["track_id"], {}).get("isrc"))][:5]
        if isrcs:
            todo.append((a, isrcs))
    for a, isrcs in todo[:limit]:
        found = deezer.by_isrc(a["name"], isrcs)
        if found:
            rows[a["spotify_id"]].update(found)
            n += 1
    save_artists(rows)
    print(f"Deezer IDs confirmed by ISRC: {n} of {len(todo[:limit])} unconfirmed artists")


def confirm_country_step(limit: int | None = None) -> None:
    """Country candidates held for review only because their Deezer match is by name alone (no Wikidata entry):
    confirm the Deezer artist from the songs (the artist's 5 biggest songs as lead on kworb against Deezer's top
    tracks). A confirmed match counts like a Wikidata one at the next registry run."""
    from .collectors import deezer_genres
    rows, dz, n, todo = load_artists(), deezer_genres.load(), 0, []
    for a in rows.values():
        d = dz.get(a["spotify_id"], {})
        if (a["genre"] == "review" and "name only" in a["genre_basis"] and d.get("deezer_id")
                and d.get("country_share") not in ("", None) and float(d["country_share"]) >= genre.COUNTRY_REVIEW
                and a.get("deezer_match") not in ("isrc", "titles")):
            todo.append((a, d["deezer_id"]))
    for a, did in todo[:limit]:
        p = current.pages(a["spotify_id"])
        if not p:
            kworb.fetch_artist(a["spotify_id"])  # archives the page
            p = current.pages(a["spotify_id"])
        songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:5] if p else []
        if songs and deezer.by_titles(did, [x["title"] for x in songs]):
            rows[a["spotify_id"]].update(deezer_id=did, deezer_match="titles")
            n += 1
    save_artists(rows)
    print(f"country candidates confirmed on Deezer by their songs: {n} of {len(todo[:limit])}")


def country_from_crawl_step(limit: int | None = None) -> None:
    """Country artists the Deezer crawl found whose name matches exactly one artist on kworb's listener pages that the
    registry does not hold yet (no Wikidata country tag, so they were never candidates): confirm the match from the
    songs, then add a Deezer genre row so the next registry run decides on them."""
    from .collectors import deezer_country, deezer_genres
    listed: dict[str, list[dict]] = {}
    for r in latest_listeners():
        listed.setdefault(deezer._norm(r["name"]), []).append(r)
    known, dz = load_artists(), deezer_genres.load()
    todo = []
    for c in deezer_country.load().values():
        m = listed.get(deezer._norm(c["name"]), [])
        if len(m) == 1 and m[0]["spotify_id"] not in known and m[0]["spotify_id"] not in dz:
            todo.append((m[0], c))
    n = 0
    for k, c in todo[:limit]:
        p = current.pages(k["spotify_id"])
        if not p:
            kworb.fetch_artist(k["spotify_id"])
            p = current.pages(k["spotify_id"])
        songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:5] if p else []
        if songs and deezer.by_titles(c["deezer_id"], [x["title"] for x in songs]):
            deezer_genres.add_confirmed(k["spotify_id"], k["name"], c["deezer_id"], c.get("fans"))
            n += 1
    print(f"country artists from the Deezer crawl confirmed on kworb's listener pages: {n} of {len(todo[:limit])}")


def deezer_audit_step() -> None:
    """Name-only Deezer matches (match "exact") whose biggest songs are not among the Deezer artist's top tracks are
    re-checked by ISRC; when the songs' ISRCs name a different Deezer artist, that one replaces the match (match
    "isrc") and its release labels are read. Nothing changes when the ISRCs agree or say nothing."""
    rows, dates, fixed = load_artists(), release_dates.load(), []
    for a in tracked(("hip_hop",)) + tracked(("country",)):
        if a.get("deezer_match") != "exact" or not a.get("deezer_id"):
            continue
        p = current.pages(a["spotify_id"])
        songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:5] if p else []
        if not songs or deezer.by_titles(a["deezer_id"], [x["title"] for x in songs]):
            continue
        isrcs = [c for x in songs if (c := dates.get(x["track_id"], {}).get("isrc"))]
        found = deezer.by_isrc(a["name"], isrcs) if isrcs else None
        if found and str(found["deezer_id"]) != str(a["deezer_id"]):
            rows[a["spotify_id"]].update(found)
            fixed.append(str(found["deezer_id"]))
    save_artists(rows)
    n = deezer_releases.update(fixed, workers=1) if fixed else 0
    print(f"Deezer audit: {len(fixed)} matches corrected by ISRC ({n} releases read)")


def wikidata_from_mb_step(limit: int | None = None) -> None:
    """Artists with no Wikidata item found by their Spotify ID (P1902 missing on Wikidata) but with a MusicBrainz ID:
    take the Wikidata item MusicBrainz links (a curated relation). Kept by later registry runs; awards,
    certifications, page views and photos then reach these artists."""
    rows, n = load_artists(), 0
    todo = [a for a in tracked(("hip_hop",)) + tracked(("country",)) if not a["wikidata_id"] and a["musicbrainz_id"]]
    for a in todo[:limit]:
        q = musicbrainz.wikidata_of(a["musicbrainz_id"])
        if q:
            rows[a["spotify_id"]]["wikidata_id"] = q
            n += 1
    save_artists(rows)
    print(f"Wikidata items from MusicBrainz: {n} of {len(todo[:limit])}")


def photos_step(limit: int | None = None) -> None:
    rows = load_artists()
    # artists whose Wikidata item came from MusicBrainz have no image read yet: take the item's P18
    missing = {a["wikidata_id"]: a["spotify_id"] for a in tracked() if a.get("wikidata_id") and not a.get("image")}
    for q, img in wikidata.images(sorted(missing)).items():
        rows[missing[q]]["image"] = img
    save_artists(rows)
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


def videos_step(limit: int | None = None) -> None:
    """Weekly: the busiest YouTube videos of Scout's Breaking and Rising artists and the unsigned prospects."""
    log = DATA / "scout_history.csv"
    rows = list(csv.DictReader(log.open())) if log.exists() else []
    day = max((r["date"] for r in rows), default="")
    risers = {r["spotify_id"] for r in rows if r["date"] == day and r["tier"] in ("Breaking", "Rising")}
    risers |= {r["spotify_id"] for r in rows if r["date"] == day and r["label_status"] == "self_released"
               and r["tier"] == "Watch"}
    slugs = {s: r["slug"] for s, r in kworb_youtube.load_latest().items() if s in risers and r["slug"]}
    artists = load_artists()
    todo = dict(list(slugs.items())[:limit])
    print(f"YouTube videos: {kworb_youtube.update_videos(todo, today())} of {len(todo)} risers with a kworb page")
    # the rest: the channel's latest uploads from YouTube's public feed (channel IDs from Wikidata)
    from .collectors import youtube_feed
    vids = json.loads(kworb_youtube.VIDEOS.read_text()) if kworb_youtube.VIDEOS.exists() else {}
    n = 0
    for s in [s for s in risers if s not in slugs and artists.get(s, {}).get("youtube_channel")][:limit]:
        latest = youtube_feed.latest(artists[s]["youtube_channel"])[:kworb_youtube.KEEP]
        if latest:
            vids[s] = {"date": today(), "source": "feed", "videos": latest}
            n += 1
    kworb_youtube.VIDEOS.write_text(json.dumps(vids, ensure_ascii=False, indent=0))
    print(f"YouTube videos: {n} more risers from their channel's feed")


def top_songs(per_artist: int = 3) -> list[dict]:
    """Each tracked artist's biggest songs as lead artist on their latest kworb page, with recording codes."""
    from . import current
    from .collectors import release_dates
    dates, out = release_dates.load(), []
    for a in tracked():
        pg = current.pages(a["spotify_id"])
        if not pg:
            continue
        lead = sorted((x for x in current.songs(pg[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:per_artist]
        out += [{"isrc": dates.get(x["track_id"], {}).get("isrc", ""), "title": x["title"], "daily": x["daily"],
                 "artist_id": a["spotify_id"], "artist": a["name"]} for x in lead]
    return out


def credits_step(limit: int | None = None) -> None:
    from .collectors import credits
    songs = top_songs()
    print(f"credits (MusicBrainz): {credits.update([s['isrc'] for s in songs], limit)} recordings looked up")


def radio_step() -> None:
    from datetime import date, timedelta
    from .collectors import radio
    t = date.fromisoformat(today())
    days = [(t - timedelta(days=i)).isoformat() for i in range(1, 31)]
    print(f"US radio (kworb): {radio.update(today(), days)} song-days stored")


def shazam_step() -> None:
    from .collectors import shazam
    print("Shazam charts (charts read, rows kept, failures):", shazam.update(today()))


def certifications_step() -> None:
    from .collectors import certifications
    n = certifications.update({a["spotify_id"]: a["name"] for a in tracked()})
    print(f"certifications (Wikipedia discographies): {n} artists with at least one")


def countrycrawl_step(limit: int | None = None) -> None:
    from .collectors import deezer_country
    print(f"country artists on Deezer's related graph: {deezer_country.crawl(limit)}")


def awards_step() -> None:
    from .collectors import awards
    print(f"awards and nominations (Wikidata): {awards.update({a['spotify_id']: a.get('wikidata_id', '') for a in tracked()})} artists with at least one")


def ytapi_step() -> None:
    n = youtube_api.update({a["spotify_id"]: a["youtube_channel"] for a in tracked() if a["youtube_channel"]})
    print("YouTube API: no YOUTUBE_API_KEY, skipped" if n is None else f"YouTube API: {n} channels")


def countries_reparse() -> None:
    n = kworb_countries.reparse_archived({a["spotify_id"] for a in tracked(("hip_hop", "review", "country"), top_n=None)})
    print(f"country charts rebuilt from the archived pages: {n} rows")


def countries_step() -> None:
    week, n = kworb_countries.update({a["spotify_id"] for a in tracked(("hip_hop", "review", "country"), top_n=None)})
    print(f"country charts, week ending {week}: {n} rows for tracked artists")


def labels_step() -> None:
    ids = [a["deezer_id"] for a in tracked() if a.get("deezer_id") and a.get("deezer_match") in deezer.CONFIRMED]
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


def backfill_step(limit: int | None = None, refetch: bool = False) -> None:
    keep = {a["spotify_id"] for a in load_artists().values() if a["genre"] in ("hip_hop", "review", "country")}
    done, bad = wayback.update(keep, limit=limit, refetch=refetch)
    print(f"Wayback: {done} weekly snapshots read, {bad} unreadable")


def mblabels_step(limit: int | None = None, refresh: bool = False) -> None:
    from . import labels
    table, rels = labels.owners(), deezer_releases.load()
    names = {}
    for a in tracked():
        for r in rels.get(a.get("deezer_id", ""), []):
            if labels.classify_label(r["label"], a["name"], table, use_musicbrainz=False)[0] == "unknown":
                names[r["label"]] = names.get(r["label"], 0) + 1
    todo = sorted(names, key=lambda n: -names[n])[:limit]
    print(f"MusicBrainz labels: {musicbrainz_labels.update(todo, refresh)} label names looked up ({len(todo)} unplaced)")


def scoutlog_step() -> None:
    """Today's Scout scores for each genre (hip-hop, and country since 2026-10-24), one row per artist and day."""
    from .site_build import build
    path = DATA / "scout_history.csv"
    new = not path.exists()
    logged = set()
    if not new:
        with path.open() as f:
            logged = {(r["date"], r["spotify_id"]) for r in csv.DictReader(f)}
    for g in ("hip_hop", "country"):
        if g != "hip_hop" and not any(a["genre"] == g for a in load_artists().values()):
            continue
        data = build(g)
        day = data["as_of"]
        with path.open("a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "spotify_id", "score", "tier", "monthly_listeners", "label_status"])
                new = False
            n = 0
            for a in data["artists"]:
                if a.get("scout") and (day, a["id"]) not in logged:
                    w.writerow([day, a["id"], a["scout"]["score"], a["scout"]["tier"] or "", a["ml"], a["label_status"]])
                    n += 1
        print(f"Scout log ({g}): {n} artists for {day}")


def reports_step(limit: int | None = None) -> None:
    from .extract import report_pdf
    print("report PDFs:", report_pdf.update(limit))


def financials_step() -> None:
    from .collectors import financials
    print("financial statements:", financials.update())
    from .collectors import companies_house
    print("UK accounts at Companies House:", companies_house.update())
    from .collectors import sony_music
    print("Sony Music segment figures:", sony_music.update())


def apple_step() -> None:
    print(f"Apple Music charts: {apple_charts.update(today())} rows for {today()}")


def pageviews_step() -> None:
    n = wikipedia.update({a["spotify_id"]: a["wikidata_id"] for a in tracked() if a.get("wikidata_id")})
    print(f"Wikipedia page views: {n} artists have an English article")


if __name__ == "__main__":
    step, args = sys.argv[1], [a for a in sys.argv[2:] if not a.startswith("--genre=")]
    GENRE = next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("--genre=")), GENRE)
    lim = int(args[0]) if args else None
    {"snapshot": snapshot, "registry": lambda: registry(lim), "streams": lambda: streams(lim),
     "deezer": deezer_step, "youtube": lambda: youtube_step(lim),
     "ytapi": ytapi_step, "videos": lambda: videos_step(lim), "awards": awards_step, "certifications": certifications_step, "countrycrawl": lambda: countrycrawl_step(lim), "deezer-isrc": lambda: deezer_isrc_step(lim), "confirm-country": lambda: confirm_country_step(lim), "country-from-crawl": lambda: country_from_crawl_step(lim), "deezer-audit": deezer_audit_step, "wikidata-from-mb": lambda: wikidata_from_mb_step(lim), "shazam": shazam_step, "radio": radio_step, "credits": lambda: credits_step(lim), "pageviews": pageviews_step, "apple": apple_step, "financials": financials_step, "reports": lambda: reports_step(lim), "scoutlog": scoutlog_step, "mblabels": lambda: mblabels_step(lim), "mblabels-refresh": lambda: mblabels_step(lim, refresh=True), "backfill": lambda: backfill_step(lim), "backfill-refetch": lambda: backfill_step(lim, refetch=True), "labels": labels_step, "countries": countries_step, "countries-reparse": countries_reparse, "photos": lambda: photos_step(lim), "dates": lambda: dates_step(lim), "dates-retry": lambda: dates_step(lim, retry=True),
     # the title search first: it adds coverage; the ISRC lookups then correct dates already found
     "mbdates": lambda: print(f"MusicBrainz: {release_dates.update_musicbrainz_search(lim)} undated songs searched, "
                              f"{release_dates.update_musicbrainz(lim)} ISRCs looked up")}[step]()
