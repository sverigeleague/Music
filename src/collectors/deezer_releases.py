"""Deezer releases per artist: the label printed on each recent release (the ℗ line's owner as Deezer shows it) and
Deezer's genre for each release. Saved to data/release_labels.csv; refreshed monthly for releases not yet seen.

The artist's albums list gives every release with its date and Deezer genre (116 = Rap/Hip Hop); the label needs
one request per release, so labels are read only for the most recent releases (RECENT within YEARS years).

Lead releases only (owner, 2026-10-24, "L1: yes"): an artist's albums list also holds releases they only feature on,
whose label is the other artist's (8 of 20 researched unknowns had a collaborator's label). The album's own record
names its lead artist; `lead` stores whether that is this artist, and load() leaves out the others. RECENT counts lead
releases; an artist with only features in the window counts as having no recent release.
"""
import csv
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from ..config import DATA
from ..http import get

API = "https://api.deezer.com"
CSV = DATA / "release_labels.csv"
FIELDS = ["deezer_artist_id", "album_id", "title", "release_date", "record_type", "genre_id", "label", "checked", "lead"]
RECENT, YEARS = 6, 2
SCAN = 30  # releases in the window looked at, at most, to find RECENT lead releases
RAP = 116  # Deezer's Rap/Hip Hop genre


def load() -> dict[str, list[dict]]:
    """deezer_artist_id -> releases, newest first. An artist checked with no release in the window has an empty list."""
    out: dict[str, list[dict]] = {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                rows = out.setdefault(r["deezer_artist_id"], [])
                if r["record_type"] != "none" and r.get("lead") != "0":  # marker row, or a feature on another's release
                    rows.append(r)
    for v in out.values():
        v.sort(key=lambda r: r["release_date"], reverse=True)
    return out


def guest_releases() -> dict[str, list[dict]]:
    """deezer_artist_id -> the window's releases where the artist is not the lead (collaborations and features on
    another artist's record), newest first. An artist with these but no own release is active, not a catalog act."""
    out: dict[str, list[dict]] = {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                if r["record_type"] != "none" and r.get("lead") == "0":
                    out.setdefault(r["deezer_artist_id"], []).append(r)
    for v in out.values():
        v.sort(key=lambda r: r["release_date"], reverse=True)
    return out


def releases(deezer_id: str) -> list[dict]:
    r = get(f"{API}/artist/{deezer_id}/albums", params={"limit": 100})
    return r.json().get("data", []) if r.status_code == 200 else []


def fill_lead(workers: int = 6) -> int:
    """Rows stored before `lead` existed: read each album's lead artist once and rewrite the file with the column."""
    if not CSV.exists():
        return 0
    with CSV.open() as f:
        rows = list(csv.DictReader(f))
    todo = [r for r in rows if r["record_type"] != "none" and r.get("lead") in (None, "")]
    if not todo and all("lead" in r for r in rows):
        return 0

    def work(r):
        d = get(f"{API}/album/{r['album_id']}")
        if d.status_code == 200 and "artist" in d.json():
            r["lead"] = str(int(str(d.json()["artist"].get("id", "")) == r["deezer_artist_id"]))
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(work, todo))
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in FIELDS} for r in rows)
    return len(todo)


def update(deezer_ids: list[str], today: date | None = None, workers: int = 6) -> int:
    """Read the labels of each artist's recent releases not yet stored. Deezer answers slowly, so several workers
    overlap the waiting; src.http keeps the shared pace within Deezer's limit."""
    today = today or date.today()
    fill_lead(workers)
    cutoff = date(today.year - YEARS, today.month, min(today.day, 28)).isoformat()
    have, lead_of = set(), {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                have.add((r["deezer_artist_id"], r["album_id"]))
                lead_of[(r["deezer_artist_id"], r["album_id"])] = r.get("lead", "")
    new = not CSV.exists()
    lock, count = threading.Lock(), [0]
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()

        def work(did):
            rel = sorted(releases(did), key=lambda a: a.get("release_date", ""), reverse=True)
            recent = [a for a in rel if a.get("release_date", "") >= cutoff][:SCAN]
            if rel and not recent and (did, "none") not in have:
                with lock:  # checked: nothing in the window (a catalog act)
                    w.writerow({"deezer_artist_id": did, "album_id": "none", "title": "", "release_date": rel[0].get("release_date", ""),
                                "record_type": "none", "genre_id": "", "label": "", "checked": today.isoformat()})
            leads = sum(1 for a in recent if lead_of.get((did, str(a["id"]))) == "1")
            for a in recent:
                if leads >= RECENT:
                    break
                if (did, str(a["id"])) in have:
                    continue
                d = get(f"{API}/album/{a['id']}")
                info = d.json() if d.status_code == 200 else {}
                lead = str(int(str((info.get("artist") or {}).get("id", "")) == str(did))) if info else ""
                leads += lead == "1"
                with lock:
                    w.writerow({"deezer_artist_id": did, "album_id": a["id"], "title": a["title"],
                                "release_date": a["release_date"], "record_type": a.get("record_type", ""),
                                "genre_id": a.get("genre_id", ""), "label": info.get("label", ""),
                                "checked": today.isoformat(), "lead": lead})
                    f.flush()
                    count[0] += 1
        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(work, deezer_ids))
    return count[0]
