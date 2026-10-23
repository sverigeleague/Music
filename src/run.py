"""Pipeline steps. python -m src.run <step>

  snapshot  kworb top 2,500 by monthly listeners: raw page archived; rows for tracked artists kept (daily)
  registry  candidates (Wikidata hip-hop genre + Spotify ID) in the top 2,500 -> details, MusicBrainz votes, genre
            decision -> registry/artists.csv and review/genre_review.csv
  streams   kworb artist pages (total and daily streams, lead vs feature) for hip-hop and review artists
  deezer    Deezer fans for hip-hop artists not yet matched
  photos    Wikimedia Commons photos for hip-hop artists not yet tried
"""
import csv
import json
import sys
from datetime import datetime, timezone

from . import genre, photos
from .collectors import deezer, kworb, musicbrainz, wikidata
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
                  "country": d.get("country", ""), "born": d.get("born", ""), "active_since": d.get("active_since", ""),
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


if __name__ == "__main__":
    step, args = sys.argv[1], sys.argv[2:]
    lim = int(args[0]) if args else None
    {"snapshot": snapshot, "registry": lambda: registry(lim), "streams": lambda: streams(lim),
     "deezer": deezer_step, "photos": lambda: photos_step(lim)}[step]()
