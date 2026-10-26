"""Who owns the songs: publishers and their shares of each tracked artist's biggest songs, from The MLC (the US
Mechanical Licensing Collective's musical works database, the one US law requires to be public).

Terms: "You may use the data in the Database for any lawful purpose" (themlc.com/musical-works-database-terms-use,
section 1); the database is reached through "a bulk download and/or public API that any member of the public can
obtain or use" (section 2). The website itself bars robots without written permission (themlc.com/terms-use,
section 3), so only the Public Search API is used (public-api.themlc.com, OpenAPI 1.2.0, "BETA"). The MLC gives no
warranty of accuracy: publishers register their own shares, and shares can add up to under or over 100%.

Access: an MLC Data Access Hub account (dah.themlc.com, enrolled for the Public Search API). Its login goes in the
GitHub secrets MLC_USERNAME and MLC_PASSWORD; without them the step is skipped with a log line. No rate limit is
published: one request a second.

Method, per song (ISRC from data/track_dates.csv, as credits.py):
1. POST /oauth/token -> bearer token.
2. POST /search/recordings {"isrc"} -> the MLC song code(s) the recording is matched to.
3. POST /works [{"mlcsongCode"}] -> the work: ISWC, writers, publishers with collectionShare (the share of US
   mechanical royalties the MLC pays that publisher), their administrators and parent publishers (the chain up to
   e.g. Sony Music Publishing). Each response is archived raw (raw/mlc/...).
Saved to data/mlc_works.csv, one row per song and publisher (one empty row when the MLC has no match, retried after
RETRY_DAYS).
"""
import csv
import json
import os
from datetime import date, timedelta

from .. import storage
from ..config import DATA
from ..http import get

API = "https://public-api.themlc.com"
CSV = DATA / "mlc_works.csv"
FIELDS = ["isrc", "song_code", "iswc", "title", "publisher", "publisher_ipi", "share", "role", "administrator",
          "top_parent", "writers", "checked"]
RETRY_DAYS = 90


def _names(pubs: list[dict] | None) -> list[str]:
    return [p.get("publisherName", "") for p in pubs or [] if p.get("publisherName")]


def top_parent(p: dict) -> str:
    """The last publisher up the parentPublishers chain (the group that owns the publisher), else ""."""
    name, cur = "", p
    for _ in range(10):  # chains are short; a guard against a loop in bad data
        parents = cur.get("parentPublishers") or []
        if not parents:
            break
        cur = parents[0]
        name = cur.get("publisherName", "") or name
    return name


def parse_work(work: dict, isrc: str, today: str) -> list[dict]:
    """A Work object -> one row per original publisher (role code as the MLC gives it, e.g. "E" original publisher)."""
    writers = "; ".join(" ".join(filter(None, (w.get("writerFirstName"), w.get("writerLastName")))) +
                        (f" ({w['writerIPI']})" if w.get("writerIPI") else "") for w in work.get("writers") or [])
    base = {"isrc": isrc, "song_code": work.get("mlcSongCode", ""), "iswc": work.get("iswc") or "",
            "title": work.get("primaryTitle", ""), "writers": writers, "checked": today}
    rows = [{**base, "publisher": p.get("publisherName", ""), "publisher_ipi": p.get("publisherIpiNumber") or "",
             "share": "" if p.get("collectionShare") is None else float(p["collectionShare"]),
             "role": p.get("publisherRoleCode") or "", "administrator": "; ".join(_names(p.get("administrators"))),
             "top_parent": top_parent(p)} for p in work.get("publishers") or []]
    return rows or [{**base, **{k: "" for k in ("publisher", "publisher_ipi", "share", "role", "administrator", "top_parent")}}]


def token(username: str, password: str) -> str:
    r = get(f"{API}/oauth/token", data=json.dumps({"username": username, "password": password}),
            headers={"Content-Type": "application/json"}, tries=2)
    if r.status_code != 200 or not r.json().get("accessToken"):
        raise RuntimeError(f"MLC login refused: HTTP {r.status_code}")
    return r.json()["accessToken"]


def _post(path: str, body, auth: str):
    return get(API + path, data=json.dumps(body), headers={"Content-Type": "application/json", "Authorization": auth})


def lookup(isrc: str, auth: str, today: str) -> list[dict] | None:
    """Rows for one ISRC; None when the API failed (tried again next run)."""
    r = _post("/search/recordings", {"isrc": isrc}, auth)
    if r.status_code == 404:
        return [{"isrc": isrc, **{k: "" for k in FIELDS if k not in ("isrc", "checked")}, "checked": today}]
    if r.status_code != 200:
        return None
    storage.archive(f"mlc/isrc/{isrc}.json", f"{API}/search/recordings isrc={isrc}", r.content)
    codes = sorted({x["mlcsongCode"] for x in r.json() or [] if x.get("mlcsongCode")})
    if not codes:
        return [{"isrc": isrc, **{k: "" for k in FIELDS if k not in ("isrc", "checked")}, "checked": today}]
    w = _post("/works", [{"mlcsongCode": c} for c in codes], auth)
    if w.status_code != 200:
        return None
    storage.archive(f"mlc/works/{'-'.join(codes)}.json", f"{API}/works", w.content)
    return [row for work in w.json() or [] for row in parse_work(work, isrc, today)]


def update(isrcs: list[str], limit: int | None = None) -> int | None:
    """Looks up ISRCs not yet seen (and misses older than RETRY_DAYS). None when the MLC login is not set."""
    user, pw = os.environ.get("MLC_USERNAME"), os.environ.get("MLC_PASSWORD")
    if not (user and pw):
        return None
    auth = "Bearer " + token(user, pw)
    have = _read()
    today = date.today().isoformat()
    stale = (date.today() - timedelta(days=RETRY_DAYS)).isoformat()
    done = {i for i, rows in have.items() if any(r["song_code"] for r in rows) or rows[0]["checked"] >= stale}
    todo = [i for i in dict.fromkeys(isrcs) if i and i not in done]
    n = 0
    for isrc in todo[:limit]:
        rows = lookup(isrc, auth, today)
        if rows is None:
            continue
        have[isrc] = rows
        n += 1
        if n % 50 == 0:
            _save(have)
    _save(have)
    return n


def _read() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    if CSV.exists():
        with CSV.open() as f:
            for r in csv.DictReader(f):
                out.setdefault(r["isrc"], []).append(r)
    return out


def _save(rows: dict[str, list[dict]]) -> None:
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for isrc in sorted(rows):
            w.writerows(rows[isrc])


def load() -> dict[str, list[dict]]:
    """isrc -> publisher rows (share as float or None); ISRCs the MLC has no match for are left out."""
    return {i: [{**r, "share": float(r["share"]) if r["share"] else None} for r in rows]
            for i, rows in _read().items() if any(r["song_code"] for r in rows)}
