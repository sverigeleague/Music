"""Apply the owner's decisions from the Review desk (claude.ai page, collections `genre` and `label`) to the registry.

The decisions are exported by Claude with the ArtifactData tool into review/decisions.json:
  {"genre": {spotify_id: {"decision", "name", "at"}}, "label": {spotify_id: {"status", "owner", "name", "at"}}}
Genre decisions go to registry/genre_overrides.csv and take effect at once in registry/artists.csv; label decisions
go to registry/label_overrides.csv (read by site_build). "Can't tell" (status unknown) is recorded as reviewed only.
"""
import csv
import json

from .config import REGISTRY, REVIEW
from .run import load_artists, save_artists

DECISIONS = REVIEW / "decisions.json"
GENRES = ("hip_hop", "latin", "other")


def _write(path, fields, rows: dict[str, dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fields, extrasaction="ignore")
        w.writeheader()
        for k in sorted(rows, key=lambda k: rows[k].get("name", "").casefold()):
            w.writerow(rows[k])


def apply() -> tuple[int, int]:
    d = json.loads(DECISIONS.read_text())
    gpath, lpath = REGISTRY / "genre_overrides.csv", REGISTRY / "label_overrides.csv"
    genre = {r["spotify_id"]: r for r in csv.DictReader(gpath.open())}
    label = {r["spotify_id"]: r for r in csv.DictReader(lpath.open())}
    artists = load_artists()
    for sid, x in d.get("genre", {}).items():
        if x.get("decision") not in GENRES:
            continue
        genre[sid] = {"spotify_id": sid, "name": x.get("name", ""), "decision": x["decision"], "note": "Review desk",
                      "decided_by": "owner", "date": x.get("at", "")}
        if sid in artists:
            artists[sid].update({"genre": x["decision"], "genre_basis": "owner: Review desk", "reviewed": x.get("at", "")})
    for sid, x in d.get("label", {}).items():
        if x.get("status") in ("major", "independent", "self_released"):
            label[sid] = {"spotify_id": sid, "name": x.get("name", ""), "status": x["status"], "owner": x.get("owner", ""),
                          "note": "owner: Review desk", "date": x.get("at", "")}
    _write(gpath, ["spotify_id", "name", "decision", "note", "decided_by", "date"], genre)
    _write(lpath, ["spotify_id", "name", "status", "owner", "note", "date"], label)
    save_artists(artists)
    return len(d.get("genre", {})), len(d.get("label", {}))


def queue(path: str) -> None:
    """The Review desk's queue file (queue.json), from review/genre_review.csv and review/label_review.csv."""
    from datetime import date
    from .collectors import deezer_releases
    artists, rels = load_artists(), deezer_releases.load()
    out = {"built": date.today().isoformat(), "genre": [], "label": []}
    for r in csv.DictReader((REVIEW / "genre_review.csv").open()):
        out["genre"].append({"id": r["spotify_id"], "n": r["name"], "ml": int(r["monthly_listeners"] or 0), "s": r["suggested"],
                             "b": r["basis"], "mb": r["musicbrainz_top_genres"], "wd": r["wikidata_genres"],
                             "c": artists.get(r["spotify_id"], {}).get("country", "")})
    for r in csv.DictReader((REVIEW / "label_review.csv").open()):
        a = artists.get(r["spotify_id"], {})
        out["label"].append({"id": r["spotify_id"], "n": r["name"], "ml": int(r["monthly_listeners"] or 0),
                             "st": r["status_now"], "lab": r["latest_label"], "note": r["codes_note"], "c": a.get("country", ""),
                             "rel": [f'{x["label"]} ({x["release_date"][:4]})' for x in rels.get(a.get("deezer_id", ""), [])[:6]]})
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["queue"]:
        queue(sys.argv[2])
    else:
        g, l = apply()
        print(f"Review desk: {g} genre and {l} label decisions applied")
