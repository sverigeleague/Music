"""Pipeline steps. python -m src.run <step>

  snapshot  kworb top 2,500 by monthly listeners: raw page archived; rows for tracked artists kept (daily)
  registry  candidates (Wikidata hip-hop genre + Spotify ID) in the top 2,500 -> details, MusicBrainz votes, genre
            decision -> registry/artists.csv and review/genre_review.csv
  streams   kworb artist pages (total and daily streams, lead vs feature) for hip-hop and review artists
  deezer    Deezer fans for hip-hop artists not yet matched
  photos    Wikimedia Commons photos for hip-hop artists not yet tried
  youtube   YouTube total and daily views (kworb.net), for hip-hop artists not yet fetched this month
  ytapi     YouTube channel subscribers and views (YouTube Data API; needs the secret YOUTUBE_API_KEY)
  small-acts  smaller acts below kworb's floor for Scout's country view, and their calibration set (--genre=country too)
  natcharts   official national charts whose terms allow reading (SE, DK, FI): new weeks, data/national_charts.csv
  smallfans   weekly Deezer fans snapshot of the smaller acts (data/deezer_fans_history.csv)
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
  credits   producer and songwriter credits, publishers on record and ISWC of each artist's 3 biggest songs from
            MusicBrainz -> data/credits.csv
  radio     US radio airplay audience per song (kworb.net/radio; today and the last 30 archived days) -> data/radio.csv
  shazam-reparse  data/shazam.csv rebuilt from the archived charts against today's registry
  shazam    Shazam's charts (world, 15 countries, 10 hip-hop, 31 cities) -> data/shazam.csv; an internal Scout signal (daily)
  wikidata-from-mb  Wikidata items linked from MusicBrainz for artists Wikidata has no Spotify ID for (monthly)
  deezer-audit re-check name-only Deezer matches by song titles, then ISRC; corrects wrong ones (monthly)
  deezer-isrc  confirm Deezer IDs of shared or unmatched names from the artist's own songs' ISRCs
  countrycrawl    country artists below the 500k floor from Deezer's related-artists graph -> data/country_deezer.csv (monthly)
  country-ids     Spotify IDs for those artists from MusicBrainz (Deezer and Spotify pages linked on one artist; monthly)
  country-floor   kworb pages for those artists, identity confirmed from their songs -> Deezer genre rows (monthly)
  certifications  RIAA, BPI and other certifications and US chart peaks from English Wikipedia discographies -> data/certifications.json (monthly)
  descriptions  one- or two-sentence artist descriptions from English Wikipedia -> data/descriptions.json (monthly)
  awards    award wins and nominations from Wikidata (Grammy, BET, AMA, MTV, BRIT...) -> data/awards.json (monthly)
  pageviews English Wikipedia page views, 24 months, for hip-hop artists with a Wikidata item (monthly)
  listenbrainz  ListenBrainz listeners last month and all time (open CC0 panel, by MusicBrainz ID) for the hip-hop
            and country top 1,000 -> data/listenbrainz.csv (monthly)
  confirm-name-only  review artists held only for a name-only Deezer match: confirmed from the songs, decided again
  mb-discover  Scout by country: artists MusicBrainz tags hip-hop or country in each listed country, on kworb's
            listener pages but not in the registry (Spotify ID from their MusicBrainz url relations)
  registry-add-pages, registry-add  Scout by country: candidates on kworb's listener pages the registry does not hold
            yet, decided by the registry's rules; existing rows unchanged (kworb pages first, then the decision)
  depth-streams, depth-dates, depth-views  Scout by country: kworb pages, Deezer release dates and Wikipedia views for
            the genre's listed artists below the top 1,000 (monthly)
  origin    country of origin where Wikidata's Spotify-ID query gives none: Wikidata by QID, then MusicBrainz's
            area (src/origin.py) -> data/country_of_origin.csv (monthly, new artists only)
  mlc       publishers and their shares of each artist's 3 biggest songs from The MLC's Public Search API ->
            data/mlc_works.csv (monthly; needs the secrets MLC_USERNAME and MLC_PASSWORD, else skipped)
"""
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone

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


def decide_artist(s: str, d: dict, prev: dict, mbrow: dict, dzrow: dict | None, over: dict, sure: bool, name: str,
                  moved: dict, origin_fill: dict) -> dict:
    """One registry row: the genre decision (hip-hop rule, then country; the owner's override wins) and the details
    from Wikidata (d), MusicBrainz (mbrow) and Deezer (dzrow). Shared by `registry` and `registry-add`."""
    votes = musicbrainz.genres_of(mbrow)
    country = d.get("country", "") or origin_fill.get(s, {}).get("country", "")
    decision, basis = genre.decide(votes, d.get("genres", []), dzrow, wikidata=bool(d.get("qid")) or sure, country=country)
    if decision in ("other", "review"):  # a second genre: country (owner, 2026-10-24)
        c = genre.decide_country(votes, d.get("genres", []), dzrow, wikidata=bool(d.get("qid")) or sure)
        if c and not (decision == "review" and c[0] == "review"):
            decision, basis = c[0], f"{c[1]}; hip-hop rule: {decision}"
        elif c:
            basis = f"{basis}; also country? {c[1]}"
    reviewed = ""
    if s in over:
        decision, basis, reviewed = over[s]["decision"], f"owner: {over[s]['note'] or over[s]['decision']}", over[s]["date"]
    row = {**prev, "spotify_id": s, "name": name, "genre": decision,
           "genre_basis": basis, "reviewed": reviewed, "wikidata_id": d.get("qid") or prev.get("wikidata_id", ""),
           "musicbrainz_id": musicbrainz.current_id(d.get("musicbrainz_id") or mbrow.get("musicbrainz_id", ""), moved),
           "country": country, "born": d.get("born", ""), "active_since": d.get("active_since", ""),
           "labels": "|".join(d.get("labels", [])), "major": "|".join(sorted(d.get("majors", []))),
           "youtube_channel": d.get("youtube_channel", ""), "instagram": d.get("instagram", ""),
           "tiktok": d.get("tiktok", ""), "x": d.get("x", ""), "image": d.get("image") or prev.get("image", "")}
    if not row.get("deezer_match") and dzrow and dzrow.get("deezer_id"):
        row.update(deezer_id=dzrow["deezer_id"], deezer_fans=dzrow["fans"], deezer_match=dzrow["match"])
    return row


def registry(mb_limit: int | None = None) -> None:
    from .collectors import deezer_genres
    top = {r["spotify_id"]: r for r in latest_listeners()}
    cands = wikidata.hip_hop_spotify_ids()
    country_cands = wikidata.country_spotify_ids()
    known = load_artists()
    dz = deezer_genres.load()
    # candidates: in kworb's listener pages (about 25,000 artists), tagged hip-hop on Wikidata or with most releases
    # filed under Rap/Hip Hop on Deezer; plus every artist already in the registry
    dz_rap = {s for s, r in dz.items() if r.get("match") in deezer.CONFIRMED and r.get("rap_share") not in ("", None)
              and float(r["rap_share"]) >= 0.5}
    dz_country = {s for s, r in dz.items() if r.get("match") in deezer.CONFIRMED and r.get("country_share") not in ("", None)
                  and float(r["country_share"]) >= 0.3}
    # below kworb's listener floor: country artists from the Deezer crawl, confirmed from their songs (country-floor)
    from .collectors import deezer_country
    crawl = {c["spotify_id"] for c in deezer_country.load().values() if c.get("spotify_id")}
    ids = sorted({s for s in cands if s in top} | {s for s in dz_rap if s in top} | set(known)
                 | {s for s in country_cands if s in top} | {s for s in dz_country if s in top or s in crawl})
    CANDIDATES.write_text(json.dumps(ids))
    wd = wikidata.details(ids)
    WIKIDATA_CACHE.write_text(json.dumps({k: {**v, "majors": sorted(v["majors"])} for k, v in wd.items()},
                                         ensure_ascii=False, indent=0))
    mb = musicbrainz.update({s: wd.get(s, {}).get("musicbrainz_id") for s in ids}, limit=mb_limit)
    moved = musicbrainz.redirects()  # merged MusicBrainz IDs (Wikidata often keeps the old one): stored as the current
    over = genre.overrides()
    from . import origin
    origin_fill = origin.load()  # countries Wikidata's Spotify-ID query gives none for (src/origin.py)
    # Deezer matches confirmed from the artist's own songs (ISRCs or titles) count like a Wikidata identity
    sure = {s for s, a in known.items() if a.get("deezer_match") in deezer.SURE
            and str(a.get("deezer_id")) == str(dz.get(s, {}).get("deezer_id"))} | {s for s, r in dz.items() if r.get("match") in deezer.SURE}
    out = {s: decide_artist(s, wd.get(s, {}), known.get(s, {}), mb.get(s, {}), dz.get(s), over, s in sure,
                            (top.get(s) or known.get(s) or dz.get(s) or {}).get("name", ""), moved, origin_fill)
           for s in ids}
    save_artists(out)
    write_review(out, top, mb, wd)
    counts = {}
    for r in out.values():
        counts[r["genre"]] = counts.get(r["genre"], 0) + 1
    print(f"{len(out)} artists: {counts}")


ADDED = REVIEW / "scout_depth_added.csv"  # every artist registry-add decided on, with how it was found


def new_candidates() -> list[tuple[str, str]]:
    """Artists on kworb's listener pages not in the registry yet that the registry's own rule would take as
    candidates: a Wikidata hip-hop or country genre with this Spotify ID, or a confirmed Deezer match with most
    releases under Rap/Hip Hop (or 30%+ under Country). (spotify_id, how found), biggest first."""
    from .collectors import deezer_genres
    known, dz = load_artists(), deezer_genres.load()
    wd_hh, wd_c = set(wikidata.hip_hop_spotify_ids()), set(wikidata.country_spotify_ids())
    mbf = _json(MB_FOUND, {})
    num = lambda r, k: float(r[k]) if r.get(k) not in ("", None) else 0.0
    out = []
    for t in latest_listeners():
        s, d = t["spotify_id"], dz.get(t["spotify_id"], {})
        if s in known:
            continue
        how = [w for w, ok in (("Wikidata hip-hop genre", s in wd_hh), ("Wikidata country genre", s in wd_c), (mbf.get(s, ""), s in mbf),
                               ("Deezer: most releases Rap/Hip Hop", d.get("match") in deezer.CONFIRMED and num(d, "rap_share") >= 0.5),
                               ("Deezer: 30%+ of releases Country", d.get("match") in deezer.CONFIRMED and num(d, "country_share") >= 0.3)) if ok]
        if how:
            out.append((s, "; ".join(how)))
    return out


MB_FOUND = DATA / "musicbrainz_discovered.json"  # spotify_id -> how MusicBrainz's tag search found it (mb-discover)
DISCOVER = {"hip_hop": ("us gb fr de ca it es nl se pl br tr ru jp kr au ng za be no dk fi mx ar cl co at ch ie nz pt "
                        "gh ke cz gr ro"),
            "country": "us ca au gb ie nz"}


def mb_discover_step() -> None:
    """Scout by country: artists MusicBrainz tags hip-hop (or country) with a main country, whose name matches an
    artist on kworb's listener pages that the registry does not hold: the Spotify ID is read from the MusicBrainz
    artist's own url relations, and kept only when it is that listed artist. Saved for registry-add to decide."""
    from .collectors import deezer as dzm
    listed: dict[str, list[str]] = {}
    for r in latest_listeners():
        listed.setdefault(dzm._norm(r["name"]), []).append(r["spotify_id"])
    known, found = load_artists(), _json(MB_FOUND, {})
    tags = {"hip_hop": musicbrainz.HIP_HOP_TAGS, "country": musicbrainz.COUNTRY_TAGS}
    for g, ccs in DISCOVER.items():
        for cc in ccs.split():
            hits = musicbrainz.search_tagged(tags[g], cc)
            n = 0
            for a in hits:
                ids = [s for s in listed.get(dzm._norm(a["name"]), []) if s not in known and s not in found]
                if not ids:
                    continue
                sid = musicbrainz.spotify_of(a["id"])
                if sid in ids:
                    found[sid] = f"MusicBrainz {'hip-hop' if g == 'hip_hop' else 'country'} tag, country {cc.upper()}"
                    n += 1
            MB_FOUND.write_text(json.dumps(found, indent=0, sort_keys=True))
            print(f"  {g} {cc}: {len(hits)} tagged on MusicBrainz, {n} new on kworb's listener pages", flush=True)
    print(f"MusicBrainz discovery: {len(found)} candidates")


def features_led(sid: str) -> str:
    """The owner's hold-back test (2026-10-26): 5 lead songs or fewer on kworb and more than half of the daily streams
    as a featured guest. Returns the note, or ""."""
    p = current.pages(sid)
    if not p:
        return ""
    songs = current.songs(p[-1][1])
    lead, daily = [x for x in songs if not x["feature"]], sum(x["daily"] for x in songs)
    feat = sum(x["daily"] for x in songs if x["feature"])
    if len(lead) <= 5 and daily and feat / daily > 0.5:
        return f"held back: listeners mostly from features; {len(lead)} lead songs of {len(songs)}"
    return ""


def depth_hold(r: dict, how: str, mbrow: dict, dzrow: dict | None, ml: int, floor: int) -> str:
    """Two more checks on a new hip-hop decision (2026-10-26), else "": (1) found only through MusicBrainz's tags (not a
    Wikidata genre or Deezer's releases, the registry's own candidate rule): kept only with 80%+ of the MusicBrainz
    votes on hip-hop and Deezer not filing most releases elsewhere; (2) big enough to enter the global top 1,000:
    held for the owner, so the main list does not change without a look."""
    if r["genre"] != "hip_hop":
        return ""
    if "Deezer" not in how and "Wikidata" not in how:
        votes = musicbrainz.genres_of(mbrow)
        tot = sum(n for _, n in votes)
        hh = sum(n for g, n in votes if genre.family(g) == "hip_hop") / tot if tot else 0
        rap = float(dzrow["rap_share"]) if dzrow and dzrow.get("rap_share") not in ("", None) and dzrow.get("match") in deezer.CONFIRMED else None
        if hh < 0.8 or (rap is not None and rap < 0.5):
            return (f"held for review: found through MusicBrainz's tags only, {hh:.0%} of {tot} votes hip-hop"
                    + (f", Deezer files {rap:.0%} of releases under Rap/Hip Hop" if rap is not None else ""))
    if ml >= floor:
        return f"held for review: {ml:,} monthly listeners would enter the top {TOP_N:,}; for the owner to check first"
    return ""


def registry_add_step(part: str, limit: int | None = None) -> None:
    """Scout by country (2026-10-26): add the candidates on kworb's listener pages the registry does not hold yet,
    by the registry's own rules (decide_artist), leaving every existing row as it is. part "pages": their kworb
    artist pages (streams and songs, for the checks below and for Scout); part "decide": Wikidata details,
    MusicBrainz votes, country of origin (src/origin.py), the genre decision; a Deezer match by name only is then
    confirmed from the songs (2 of the 5 biggest lead songs among the Deezer artist's top tracks) and decided again;
    a hip-hop act that is features-led goes to review. Uncertain cases land in review/genre_review.csv."""
    from .collectors import deezer_genres
    from . import origin
    cands = new_candidates()[:limit]
    ids = [s for s, _ in cands]
    if part == "pages":
        month = today()[:7]
        todo, rows = [s for s in ids if not any(d[:7] == month for d, _ in current.pages(s))], []
        for s in todo:
            try:
                rows.append(kworb.fetch_artist(s))
            except Exception as e:
                print(f"  kworb page {s} failed: {e}")
            if len(rows) % 25 == 0:
                kworb.save_streams(rows)
                rows = []
        kworb.save_streams(rows)
        print(f"registry-add: kworb pages read for {len(todo)} of {len(ids)} candidates")
        return
    top = {r["spotify_id"]: r for r in latest_listeners()}
    known, dz = load_artists(), deezer_genres.load()
    wd = wikidata.details(ids)
    mb = musicbrainz.update({s: wd.get(s, {}).get("musicbrainz_id") for s in ids})
    moved, over = musicbrainz.redirects(), genre.overrides()
    mbid = lambda s: musicbrainz.current_id(wd.get(s, {}).get("musicbrainz_id") or mb.get(s, {}).get("musicbrainz_id", ""), moved)
    origin.fill({s: {"spotify_id": s, "name": top[s]["name"], "genre": "new", "country": wd.get(s, {}).get("country", ""),
                     "wikidata_id": wd.get(s, {}).get("qid", ""), "musicbrainz_id": mbid(s)} for s in ids}, genres=None)
    fill = origin.load()
    decide = lambda s, dzrow, sure: decide_artist(s, wd.get(s, {}), {}, mb.get(s, {}), dzrow, over, sure,
                                                  top[s]["name"], moved, fill)
    rows = {s: decide(s, dz.get(s), dz.get(s, {}).get("match") in deezer.SURE) for s in ids}
    confirmed = 0
    for s, r in rows.items():
        d = dz.get(s, {})
        if r["genre"] == "review" and "name only" in r["genre_basis"] and d.get("deezer_id") and s not in over:
            if not current.pages(s):  # registry-add-pages not run (or the page failed): read it now
                try:
                    kworb.save_streams([kworb.fetch_artist(s)])
                except Exception as e:
                    print(f"  kworb page {s} failed: {e}")
            p = current.pages(s)
            songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:5] if p else []
            if songs and deezer.by_titles(d["deezer_id"], [x["title"] for x in songs]):
                row = deezer_genres.add_confirmed(s, r["name"], d["deezer_id"], d.get("fans"))
                rows[s] = decide(s, row, True)
                confirmed += 1
    held, how = 0, dict(cands)
    floor = min((top.get(a["spotify_id"], {}).get("monthly_listeners") or 0 for a in tracked(("hip_hop",))), default=0)
    for s, r in rows.items():
        note = features_led(s) if r["genre"] == "hip_hop" and s not in over else ""
        note = note or (depth_hold(r, how[s], mb.get(s, {}), dz.get(s), top[s]["monthly_listeners"] or 0, floor) if s not in over else "")
        if note:
            r.update(genre="review", genre_basis=f"{r['genre_basis']}; {note}")
            held += 1
    known.update(rows)
    save_artists(known)
    cache = _json(WIKIDATA_CACHE, {})
    cache.update({k: {**v, "majors": sorted(v["majors"])} for k, v in wd.items()})
    WIKIDATA_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    CANDIDATES.write_text(json.dumps(sorted(set(_json(CANDIDATES, [])) | set(ids))))
    write_review(known, top, musicbrainz.load(), cache)
    old = {r["spotify_id"]: r for r in csv.DictReader(ADDED.open())} if ADDED.exists() else {}
    for s, r in rows.items():
        old[s] = {"date": today(), "spotify_id": s, "name": r["name"], "monthly_listeners": top[s]["monthly_listeners"],
                  "found_by": how[s], "genre": r["genre"], "basis": r["genre_basis"], "country": r["country"],
                  "country_source": "wikidata" if wd.get(s, {}).get("country") else (fill.get(s) or {}).get("source", "")}
    with ADDED.open("w", newline="") as f:
        w = csv.DictWriter(f, ["date", "spotify_id", "name", "monthly_listeners", "found_by", "genre", "basis", "country", "country_source"])
        w.writeheader()
        w.writerows(sorted(old.values(), key=lambda r: -int(r["monthly_listeners"] or 0)))
    counts = {}
    for r in rows.values():
        counts[r["genre"]] = counts.get(r["genre"], 0) + 1
    print(f"registry-add: {len(rows)} candidates decided {counts}; {confirmed} Deezer matches confirmed from the songs, "
          f"{held} features-led acts held back")


def confirm_name_only_step(limit: int | None = None) -> None:
    """Artists held in review only because their Deezer match rests on the name (no Wikidata item, no owner
    decision): confirm the Deezer artist from the songs, as registry-add does, and decide again by the registry's
    rules (decide_artist), with the features-led and top-1,000 holds. Changes: review/name_only_confirmed.csv."""
    from .collectors import deezer_genres
    top = {r["spotify_id"]: r for r in latest_listeners()}
    known, dz, mb, over = load_artists(), deezer_genres.load(), musicbrainz.load(), genre.overrides()
    wd, moved = _json(WIKIDATA_CACHE, {}), musicbrainz.redirects()
    from . import origin
    fill = origin.load()
    floor = min((top.get(a["spotify_id"], {}).get("monthly_listeners") or 0 for a in tracked(("hip_hop",))), default=0)
    kept = set()  # left in review by a hand check (review/genre_quality_check_*.csv "KEEP IN REVIEW"): not re-decided
    for path in REVIEW.glob("genre_quality_check_*.csv"):
        kept |= {r["spotify_id"] for r in csv.DictReader(path.open()) if r.get("verdict", "").upper().startswith("KEEP")}
    todo = [a for a in known.values() if a["genre"] == "review" and "name only" in a["genre_basis"] and not a["reviewed"]
            and a["spotify_id"] not in over and a["spotify_id"] not in kept and dz.get(a["spotify_id"], {}).get("deezer_id") and a["spotify_id"] in top][:limit]
    changed = []
    for a in todo:
        s, d = a["spotify_id"], dz[a["spotify_id"]]
        p = current.pages(s)
        songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:5] if p else []
        if not songs or not deezer.by_titles(d["deezer_id"], [x["title"] for x in songs]):
            continue
        row = deezer_genres.add_confirmed(s, a["name"], d["deezer_id"], d.get("fans"))
        new = decide_artist(s, {**wd.get(s, {}), "majors": set(wd.get(s, {}).get("majors", []))}, a, mb.get(s, {}), row,
                            over, True, a["name"], moved, fill)
        new.update(deezer_id=d["deezer_id"], deezer_match="titles")
        note = features_led(s) if new["genre"] == "hip_hop" else ""
        if not note and new["genre"] == "hip_hop" and (top[s]["monthly_listeners"] or 0) >= floor:
            note = f"held for review: {top[s]['monthly_listeners']:,} monthly listeners would enter the top {TOP_N:,}; for the owner to check first"
        if note:
            new.update(genre="review", genre_basis=f"{new['genre_basis']}; {note}")
        known[s] = new
        changed.append({"date": today(), "spotify_id": s, "name": a["name"], "monthly_listeners": top[s]["monthly_listeners"],
                        "before": a["genre"], "after": new["genre"], "basis": new["genre_basis"], "country": new["country"]})
    save_artists(known)
    write_review(known, top, mb, wd)
    path = REVIEW / "name_only_confirmed.csv"
    old = list(csv.DictReader(path.open())) if path.exists() else []
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, ["date", "spotify_id", "name", "monthly_listeners", "before", "after", "basis", "country"])
        w.writeheader()
        w.writerows(old + changed)
    from collections import Counter
    print(f"name-only Deezer matches: {len(changed)} of {len(todo)} confirmed from the songs; now {dict(Counter(c['after'] for c in changed))}")


def write_review(rows, top, mb, wd) -> None:
    """Borderline and Latin artists for the owner, biggest first. Approving: a row in registry/genre_overrides.csv."""
    REVIEW.mkdir(exist_ok=True)
    # an owner decision "review" (held back, e.g. listeners mostly from features) stays listed with its note
    items = [r for r in rows.values() if r["genre"] == "review" or (r["genre"] == "latin" and not r["reviewed"])]
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
    """Artists of these genres, biggest first by today's monthly listeners, then (below kworb's listener floor) by daily
    streams; the per-artist steps take the top 1,000."""
    genres = genres or (GENRE,)
    ml = {r["spotify_id"]: r["monthly_listeners"] or 0 for r in latest_listeners()}
    daily = {}  # below kworb's listener floor (country), artists rank by their measured daily streams
    if kworb.STREAMS_CSV.exists():
        with kworb.STREAMS_CSV.open() as f:
            fresh = (date.today() - timedelta(days=60)).isoformat()  # as site_build.FLOOR_FRESH_DAYS
            for r in csv.DictReader(f):
                daily[r["spotify_id"]] = int(r["total_daily"] or 0) if r["date"] >= fresh else 0
    from .collectors import deezer_country  # then the rest of the crawl in Deezer's order
    crawl: dict[str, int] = {}  # an artist with two Deezer pages takes the bigger
    for c in deezer_country.load().values():
        if c.get("spotify_id"):
            crawl[c["spotify_id"]] = max(crawl.get(c["spotify_id"], 0), int(c.get("top10_rank_sum") or 0))
    rows = sorted((a for a in load_artists().values() if a["genre"] in genres),
                  key=lambda a: (-ml.get(a["spotify_id"], 0), -daily.get(a["spotify_id"], 0), -crawl.get(a["spotify_id"], 0)))
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


def scout_depth_step(part: str, limit: int | None = None) -> None:
    """Scout by country (2026-10-26): the free inputs of the Scout score for the genre's registry artists below the top
    1,000 that kworb's listener pages list (the country view scores them all). part: "streams" (kworb artist pages:
    streams and songs), "dates" (Deezer first release dates of the songs behind 90% of the daily streams) or "views"
    (English Wikipedia page views). MusicBrainz release dates (mbdates) are not run for them: too slow."""
    listed = {r["spotify_id"]: r["rank"] for r in latest_listeners()}
    rest = [a for a in tracked(top_n=None)[TOP_N:] if a["spotify_id"] in listed]
    if part == "streams":
        have = set()
        if kworb.STREAMS_CSV.exists():
            with kworb.STREAMS_CSV.open() as f:
                have = {r["spotify_id"] for r in csv.DictReader(f) if r["date"][:7] == today()[:7]}
        todo, rows = [a["spotify_id"] for a in rest if a["spotify_id"] not in have][:limit], []
        for s in todo:
            try:
                rows.append(kworb.fetch_artist(s))
            except Exception as e:  # one failed page must not lose the others
                print(f"  kworb page {s} failed: {e}")
            if len(rows) % 25 == 0:
                kworb.save_streams(rows)
                rows = []
        kworb.save_streams(rows)
        print(f"Scout depth: stream totals fetched for {len(todo)} of {len(rest)} artists below the top {TOP_N}")
    elif part == "dates":
        todo = []
        for a in sorted(rest, key=lambda a: listed[a["spotify_id"]]):
            p = current.pages(a["spotify_id"])
            if p:
                todo += [(a["spotify_id"], a["name"], x["track_id"], x["title"]) for x in current.to_date(current.songs(p[-1][1]))]
        cache = release_dates.update(todo, limit=limit)
        print(f"Scout depth: {sum(1 for _a, _n, t, _ in todo if cache.get(t, {}).get('first_release'))} of {len(todo)} songs dated")
    elif part == "views":
        qids = {a["spotify_id"]: a["wikidata_id"] for a in tracked(top_n=None) if a.get("wikidata_id")}
        print(f"Scout depth: Wikipedia page views, {wikipedia.update(qids)} artists have an English article")


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
    for i, (a, isrcs) in enumerate(todo[:limit], 1):
        if i % 25 == 0:
            save_artists(rows)
        found = deezer.by_isrc(a["name"], isrcs)
        if found:
            rows[a["spotify_id"]].update(found)
            n += 1
            from .collectors import deezer_genres  # genre shares from the confirmed artist, not the name match
            deezer_genres.add_confirmed(a["spotify_id"], a["name"], found["deezer_id"], found["deezer_fans"], "isrc")
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
                and a.get("deezer_match") not in deezer.SURE):
            todo.append((a, d["deezer_id"]))
    for i, (a, did) in enumerate(todo[:limit], 1):
        p = current.pages(a["spotify_id"])
        if not p:
            try:
                kworb.fetch_artist(a["spotify_id"])  # archives the page
            except Exception as e:  # one failed page must not lose the confirmations so far
                print(f"  kworb page for {a['name']} failed: {e}")
            p = current.pages(a["spotify_id"])
        if i % 25 == 0:
            save_artists(rows)
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
            try:
                kworb.fetch_artist(k["spotify_id"])
            except Exception as e:
                print(f"  kworb page for {k['name']} failed: {e}")
            p = current.pages(k["spotify_id"])
        songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:5] if p else []
        if songs and deezer.by_titles(c["deezer_id"], [x["title"] for x in songs]):
            deezer_genres.add_confirmed(k["spotify_id"], k["name"], c["deezer_id"], c.get("fans"))
            n += 1
    print(f"country artists from the Deezer crawl confirmed on kworb's listener pages: {n} of {len(todo[:limit])}")


def country_floor_step(limit: int | None = None) -> None:
    """Country artists below kworb's 500k-listener floor (owner, 2026-10-25: "top 1,000 country ... same depth as the
    1,000 for hip hop"): for each crawled artist with a Spotify ID looked up at the source (Wikidata or MusicBrainz;
    `country-ids`) that the registry does not hold yet, read kworb's artist page (stream totals and songs) and confirm
    the identity a second way, by its biggest songs among the Deezer artist's top tracks; where kworb has no page, the
    link at the source confirms it alone (match "links"), and songs that contradict it reject it. Confirmed artists
    get a Deezer genre row, so the next registry run decides on them by the usual rules; daily streams, where kworb
    has them, rank them after the measured list."""
    from .collectors import deezer_country, deezer_genres
    known, dz = load_artists(), deezer_genres.load()
    todo = [c for c in deezer_country.load().values() if c.get("spotify_id") and c["spotify_id"] not in known
            and c["spotify_id"] not in dz][:limit]
    n, rows, failed = 0, [], []
    for c in todo:
        try:
            row = kworb.fetch_artist(c["spotify_id"])
        except Exception as e:
            print(f"  kworb page for {c['name']} failed: {e}")
            continue
        if not row:  # kworb has no page (it does not track most small artists): the link alone confirms it
            failed.append(c["name"])
            deezer_genres.add_confirmed(c["spotify_id"], c["name"], c["deezer_id"], c.get("fans"), match="links")
            n += 1
            continue
        rows.append(row)
        p = current.pages(c["spotify_id"])
        songs = sorted((x for x in current.songs(p[-1][1]) if not x["feature"]), key=lambda x: -x["daily"])[:5] if p else []
        if songs and deezer.by_titles(c["deezer_id"], [x["title"] for x in songs]):  # else the songs contradict the link
            deezer_genres.add_confirmed(c["spotify_id"], c["name"], c["deezer_id"], c.get("fans"))
            n += 1
        if len(rows) % 25 == 0:
            kworb.save_streams(rows)
            rows = []
    kworb.save_streams(rows)
    print(f"below-floor country artists confirmed: {n} of {len(todo)} ({len(failed)} on the link alone, no kworb page)")


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
            from .collectors import deezer_genres  # the genre shares must come from the corrected artist too
            deezer_genres.add_confirmed(a["spotify_id"], a["name"], found["deezer_id"], found["deezer_fans"], "isrc")
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


def origin_step(limit: int | None = None) -> None:
    """Country of origin where Wikidata's Spotify-ID query gives none: Wikidata by QID, then MusicBrainz (src/origin.py)."""
    from . import origin
    rows = load_artists()
    n = origin.fill(rows, limit)
    k = origin.apply(rows)
    save_artists(rows)
    print(f"country of origin: {n}; {k} registry rows filled")


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


YOUTUBE_REVIEW = REVIEW / "youtube_review.csv"
YOUTUBE_REVIEW_FIELDS = ["date", "genre", "spotify_id", "name", "slug", "kworb_name", "page_spotify_id", "reason", "evidence"]


def youtube_matches(todo: list[dict], idx: dict[str, dict], day: str) -> tuple[dict, list[dict]]:
    """kworb pages matched by identifiers before the per-artist fetch: the page's link back to the Spotify ID, or a
    video from the artist's own channel (Wikidata P2397, else MusicBrainz url relations) that the page lists as the
    artist's own. Returns (spotify_id -> (slug, match)) and the conflicts and name-only candidates for review."""
    from . import storage
    from .collectors import youtube_feed
    back = {r["spotify_id"]: r["slug"] for r in idx.values() if r["spotify_id"]}
    linked = {r["slug"] for r in idx.values() if r["spotify_id"]}
    pages = {s: kworb_youtube.own_videos(storage.read(kworb_youtube.page_path(r)).decode("utf-8", "replace")) for s, r in idx.items()}
    names = {kworb_youtube.slug_guess(r["name"]): s for s, r in idx.items()}
    mb = musicbrainz.youtube_channels([a["musicbrainz_id"] for a in todo if a["spotify_id"] not in back and not a["youtube_channel"]])
    known, review = {}, []
    note = lambda a, slug, reason, evidence="": review.append({
        "date": day, "genre": a["genre"], "spotify_id": a["spotify_id"], "name": a["name"], "slug": slug,
        "kworb_name": idx[slug]["name"], "page_spotify_id": idx[slug]["spotify_id"], "reason": reason, "evidence": evidence})
    for a in todo:
        sid = a["spotify_id"]
        if sid in back:
            known[sid] = (back[sid], "backlink")
            continue
        link = kworb_youtube.slug_from_spotify_page(sid)
        if link in idx and idx[link]["spotify_id"]:
            note(a, link, "kworb's Spotify page links this YouTube page, which links back to another Spotify ID")
        chans = [a["youtube_channel"]] if a["youtube_channel"] else mb.get(a["musicbrainz_id"], [])
        match, hits = kworb_youtube.channel_match({c: youtube_feed.video_ids(c, day) for c in chans}, pages, linked)
        if match:
            known[sid] = match
        for slug, ev in ({} if match else hits).items():
            note(a, slug, "the channel's video is on a page that links back to another Spotify ID" if slug in linked
                 else "the channel's videos are on several kworb pages", ev)
        guess = names.get(kworb_youtube.slug_guess(a["name"]))
        if not hits and guess and not idx[guess]["spotify_id"] and guess != link:
            note(a, guess, "same name only: the page has no link back to Spotify and no video from a known channel")
    return known, review


def youtube_step(limit: int | None = None) -> None:
    from collections import Counter
    have = {s for s, r in kworb_youtube.load_latest().items() if r["date"][:7] == today()[:7]}
    todo = [a for a in tracked() if a["spotify_id"] not in have][:limit]
    known, review = youtube_matches(todo, kworb_youtube.update_index(today()), today())
    rows = [r for r in (kworb_youtube.fetch(a["spotify_id"], a["name"], today(), known.get(a["spotify_id"])) for a in todo) if r]
    kworb_youtube.save(rows)
    found = {r["spotify_id"] for r in rows} | have
    old = list(csv.DictReader(YOUTUBE_REVIEW.open())) if YOUTUBE_REVIEW.exists() else []
    tried = {a["spotify_id"] for a in todo}  # their rows are replaced by this run's
    keep = [r for r in old if r["spotify_id"] not in tried | found] + [r for r in review if r["spotify_id"] not in found]
    with YOUTUBE_REVIEW.open("w", newline="") as f:
        w = csv.DictWriter(f, YOUTUBE_REVIEW_FIELDS)
        w.writeheader()
        w.writerows(sorted(keep, key=lambda r: (r["genre"], r["name"].casefold())))
    print(f"YouTube: {len(rows)} of {len(todo)} artists found ({', '.join(f'{m}: {n}' for m, n in sorted(Counter(r['match'].split(' ')[0] for r in rows).items()))}); "
          f"{len(keep)} in {YOUTUBE_REVIEW.relative_to(REVIEW.parent)}")


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
    songs = sorted(top_songs(), key=lambda s: -s["daily"])  # biggest songs first, so a cut-off run covers the hits
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


def country_ids_step(limit: int | None = None) -> None:
    from .collectors import deezer_country
    n = deezer_country.spotify_ids(limit)
    rows = deezer_country.load().values()
    print(f"country crawl: {n} Spotify IDs found on MusicBrainz; {sum(1 for r in rows if r.get('spotify_id'))} of "
          f"{len(rows)} artists have one")


def countrycrawl_step(limit: int | None = None) -> None:
    from .collectors import deezer_country
    print(f"country artists on Deezer's related graph: {deezer_country.crawl(limit)}")


def descriptions_step() -> None:
    """One- or two-sentence descriptions from each artist's English Wikipedia article (both genres' top 1,000)."""
    from .collectors import descriptions
    arts = tracked(("hip_hop",)) + tracked(("country",))
    titles = wikipedia.articles({a["spotify_id"]: a.get("wikidata_id", "") for a in arts})
    n = descriptions.update(titles)
    print(f"descriptions: {n} of {len(arts)} artists have one from Wikipedia ({len(titles)} articles)")


def awards_step() -> None:
    from .collectors import awards
    print(f"awards and nominations (Wikidata): {awards.update({a['spotify_id']: a.get('wikidata_id', '') for a in tracked()})} artists with at least one")


def youtube_channels() -> dict[str, str]:
    """spotify_id -> the artist's own YouTube channel ID: Wikidata P2397, else the one youtube.com/channel/UC... link on
    their MusicBrainz page (data/musicbrainz_youtube.csv). Two or more MusicBrainz channels: none taken (ambiguous)."""
    mb = {}
    p = DATA / "musicbrainz_youtube.csv"
    if p.exists():
        with p.open() as f:
            mb = {r["musicbrainz_id"]: [c for c in r["channels"].split("|") if c.startswith("UC")] for r in csv.DictReader(f)}
    out = {}
    for a in tracked():
        c = a["youtube_channel"] or (lambda cs: cs[0] if len(cs) == 1 else "")(mb.get(a.get("musicbrainz_id", ""), []))
        if c:
            out[a["spotify_id"]] = c
    from .collectors import small_acts  # smaller acts with an official channel on Wikidata (P2397), 2026-10-26
    for r in small_acts.load():
        if r["genre"] == GENRE and r["decision"] == "include" and r["spotify_id"] and r["youtube_channel"].startswith("UC"):
            out.setdefault(r["spotify_id"], r["youtube_channel"])
    return out


def full_countries(genre: str) -> set[str]:
    """Countries whose Scout country view already has 100 scored artists (the last build's scout.json)."""
    from .config import SITE
    p = SITE / "data" / ("" if genre == "hip_hop" else genre) / "scout.json"
    if not p.exists():
        return set()
    from .origin import name_of
    return {name_of(c["cc"]) for c in json.loads(p.read_text())["scout_country_list"]["countries"] if c["scored"] >= 100}


def small_acts_step() -> None:
    """Smaller acts below kworb's floor for the genre's Scout country view (src/collectors/small_acts.py)."""
    from .collectors import small_acts
    print("smaller acts:", small_acts.discover(GENRE, full_countries(GENRE)))
    print(f"calibration set: {small_acts.calibrate(GENRE)} artists with kworb listeners")


def small_acts_mb_step() -> None:
    """MusicBrainz url relations for smaller acts with no Deezer page on Wikidata (then run small-acts again)."""
    from .collectors import small_acts
    todo = [r["mbid"] for r in small_acts.load() if r["genre"] == GENRE and not r["deezer_id"] and r["mbid"]]
    print(f"MusicBrainz url relations read for {small_acts.mb_links(todo)} of {len(todo)} smaller acts")


def ytapi_step() -> None:
    n = youtube_api.update(youtube_channels())
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


def mlc_step(limit: int | None = None) -> None:
    from .collectors import mlc
    songs = top_songs()
    n = mlc.update([s["isrc"] for s in songs], limit)
    print("MLC: no MLC_USERNAME / MLC_PASSWORD, skipped" if n is None else f"MLC: {n} recordings looked up; "
          f"{sum(1 for s in songs if s['isrc'] in mlc.load())} of {len(songs)} top songs have publishers")


def listenbrainz_step(limit: int | None = None) -> None:
    from .collectors import listenbrainz
    arts = tracked(("hip_hop",)) + tracked(("country",))
    n = listenbrainz.update({a["spotify_id"]: a["musicbrainz_id"] for a in arts if a.get("musicbrainz_id")}, limit)
    print(f"ListenBrainz: {n['known']} of {n['asked']} artists asked are known ({n['redirected']} by a merged "
          f"MusicBrainz ID), {n['with_month']} with last month's listeners; {len(arts)} tracked")


def pageviews_step() -> None:
    n = wikipedia.update({a["spotify_id"]: a["wikidata_id"] for a in tracked() if a.get("wikidata_id")})
    print(f"Wikipedia page views: {n} artists have an English article")


if __name__ == "__main__":
    step, args = sys.argv[1], [a for a in sys.argv[2:] if not a.startswith("--genre=")]
    GENRE = next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("--genre=")), GENRE)
    lim = int(args[0]) if args else None
    {"snapshot": snapshot, "registry": lambda: registry(lim), "streams": lambda: streams(lim),
     "deezer": deezer_step, "youtube": lambda: youtube_step(lim),
     "ytapi": ytapi_step, "small-acts": small_acts_step, "small-acts-mb": small_acts_mb_step, "natcharts": lambda: print(f"national charts, pages fetched: {__import__('src.collectors.national_charts', fromlist=['x']).update()}"), "smallfans": lambda: print(f"Deezer fans snapshot: {__import__('src.collectors.small_acts', fromlist=['x']).fans_snapshot()} smaller acts"), "videos": lambda: videos_step(lim), "awards": awards_step, "descriptions": descriptions_step, "certifications": certifications_step, "countrycrawl": lambda: countrycrawl_step(lim), "country-ids": lambda: country_ids_step(lim), "country-floor": lambda: country_floor_step(lim), "deezer-isrc": lambda: deezer_isrc_step(lim), "confirm-country": lambda: confirm_country_step(lim), "country-from-crawl": lambda: country_from_crawl_step(lim), "deezer-audit": deezer_audit_step, "wikidata-from-mb": lambda: wikidata_from_mb_step(lim), "shazam": shazam_step, "shazam-reparse": lambda: print(f"Shazam rows rebuilt from the archive: {__import__('src.collectors.shazam', fromlist=['x']).reparse()}"), "radio": radio_step, "credits": lambda: credits_step(lim), "pageviews": pageviews_step, "listenbrainz": lambda: listenbrainz_step(lim), "mlc": lambda: mlc_step(lim), "apple": apple_step, "financials": financials_step, "reports": lambda: reports_step(lim), "scoutlog": scoutlog_step, "mblabels": lambda: mblabels_step(lim), "mblabels-refresh": lambda: mblabels_step(lim, refresh=True), "backfill": lambda: backfill_step(lim), "backfill-refetch": lambda: backfill_step(lim, refetch=True), "labels": labels_step, "countries": countries_step, "countries-reparse": countries_reparse, "photos": lambda: photos_step(lim), "origin": lambda: origin_step(lim), "registry-add-pages": lambda: registry_add_step("pages", lim), "registry-add": lambda: registry_add_step("decide", lim), "mb-discover": mb_discover_step, "confirm-name-only": lambda: confirm_name_only_step(lim), "depth-streams": lambda: scout_depth_step("streams", lim), "depth-dates": lambda: scout_depth_step("dates", lim), "depth-views": lambda: scout_depth_step("views"), "dates": lambda: dates_step(lim), "dates-retry": lambda: dates_step(lim, retry=True),
     # the title search first: it adds coverage; the ISRC lookups then correct dates already found
     "mbdates": lambda: print(f"MusicBrainz: {release_dates.update_musicbrainz_search(lim)} undated songs searched, "
                              f"{release_dates.update_musicbrainz(lim)} ISRCs looked up")}[step]()
