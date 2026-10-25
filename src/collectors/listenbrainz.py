"""ListenBrainz (MetaBrainz): how many of its users played each artist, last full month and all time. Free, no key.

What it is: an open scrobble panel (people who send their plays to ListenBrainz from Spotify, Apple, players...). The
counts are of its users only, a small panel that leans to rock and indie, so they are a measure of reach in that
panel, not a market figure: Drake 3,497 listeners in September 2026 against about 95m on Spotify. Tested 2026-10-25
(docs/research/2026-10-26-new-data-sources.md): it separates big from small (r 0.58 hip-hop, 0.76 country, log
scale) but orders artists of similar size poorly (Spearman 0.14-0.23, below Deezer's), so it is internal only: kept
for the Scout back-test of month-on-month change, not shown and not used to rank.

Terms: "User listen data and text is made public under the Creative Commons Zero (CC0) license" (ListenBrainz page
footer, frontend/js/src/components/Footer.tsx in metabrainz/listenbrainz-server); "All of our data is available for
commercial use" (the server README), with MetaBrainz asking companies with revenue to take a support tier
(metabrainz.org/supporters/account-type; $0 for non-commercial and small non-profit use). Rate limit: "never make more
than ONE call per second" (API docs, Rate limiting); the server also sends X-RateLimit headers (30 per 10 s seen).

Method, per artist (registry musicbrainz_id, looked up at the source, never by name here):
1. POST /1/popularity/artist, 500 MBIDs a call: all-time listens and distinct users.
2. An MBID ListenBrainz does not know (null counts) is often a merged MusicBrainz ID (the registry's Drake ID is one):
   MusicBrainz' lookup answers with the current ID, which is asked again. Redirects are cached in REDIRECTS.
3. GET /1/stats/artist/<mbid>/listeners?range=month for artists with any all-time users: listeners and listens in
   the last full calendar month. HTTP 204 means ListenBrainz has no listener stats computed for the artist (it
   answers 204 for every range, even all_time): left blank, never read as zero. The response also lists the top users by name; those names are personal data and
   are removed before the raw response is archived (raw/listenbrainz/<month>/...).
Saved to data/listenbrainz.csv, one row per artist and month (history builds up month by month).
"""
import csv
import hashlib
import json
from datetime import datetime, timezone

from .. import storage
from ..config import DATA
from ..http import get

API = "https://api.listenbrainz.org/1"
MB = "https://musicbrainz.org/ws/2/artist/"
CSV = DATA / "listenbrainz.csv"
from .musicbrainz import REDIRECTS  # registry MBID -> current MBID ("" when MusicBrainz has none), shared
FIELDS = ["month", "spotify_id", "mbid", "users_all", "listens_all", "users_month", "listens_month", "from", "to",
          "fetched"]
BATCH = 500


def parse_popularity(rows: list[dict]) -> dict[str, tuple[int, int] | None]:
    """mbid -> (all-time users, all-time listens), None when ListenBrainz has no data for it."""
    out = {}
    for r in rows:
        u, n = r.get("total_user_count"), r.get("total_listen_count")
        out[r["artist_mbid"]] = None if u is None else (int(u), int(n or 0))
    return out


def parse_listeners(payload: dict) -> dict:
    """The month's figures from a /stats/artist/<mbid>/listeners payload; the window as ISO dates (UTC)."""
    day = lambda ts: datetime.fromtimestamp(int(ts), timezone.utc).date().isoformat()
    return {"users_month": int(payload.get("total_user_count") or 0),
            "listens_month": int(payload.get("total_listen_count") or 0),
            "from": day(payload["from_ts"]), "to": day(payload["to_ts"])}


def strip_users(body: dict) -> dict:
    """The response without the per-user list (user names are personal data; only totals are kept)."""
    p = dict(body.get("payload") or {})
    p.pop("listeners", None)
    return {**body, "payload": p}


def popularity(mbids: list[str], month: str) -> dict[str, tuple[int, int] | None]:
    out = {}
    for i in range(0, len(mbids), BATCH):
        chunk = mbids[i:i + BATCH]
        url = f"{API}/popularity/artist"
        r = get(url, data=json.dumps({"artist_mbids": chunk}), headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            raise RuntimeError(f"ListenBrainz popularity: HTTP {r.status_code}")
        key = hashlib.sha1(" ".join(chunk).encode()).hexdigest()[:10]  # one file per distinct request
        storage.archive(f"listenbrainz/{month}/popularity-{key}.json", url, r.content)
        out.update(parse_popularity(r.json()))
    return out


def current_mbid(mbid: str, cache: dict[str, str]) -> str:
    """The MBID MusicBrainz now uses for `mbid` (merged IDs redirect), "" when it has none."""
    if mbid not in cache:
        r = get(MB + mbid, params={"fmt": "json"})
        cache[mbid] = r.json().get("id", "") if r.status_code == 200 else ("" if r.status_code == 404 else None)
        if cache[mbid] is None:  # throttled or down: ask again next run
            del cache[mbid]
            return ""
    return cache[mbid]


def update(mbids: dict[str, str], limit: int | None = None) -> dict[str, int]:
    """spotify_id -> registry MBID. Reads the last full month for artists not yet stored for it; returns counts."""
    month = datetime.now(timezone.utc).strftime("%Y-%m")  # fetch month; the stats window is the month before
    have = _read()
    done = {r["spotify_id"] for r in have if r["fetched"][:7] == month}
    todo = {s: m for s, m in mbids.items() if m and s not in done}
    redirects = json.loads(REDIRECTS.read_text()) if REDIRECTS.exists() else {}
    pop = popularity(sorted(set(todo.values())), month)
    moved = {}
    for s, m in todo.items():
        if pop.get(m) is None:
            new = current_mbid(m, redirects)
            if new and new != m:
                moved[s] = new
    REDIRECTS.write_text(json.dumps(redirects, indent=0, sort_keys=True))
    if moved:
        pop.update(popularity(sorted(set(moved.values())), month))
    rows, n_month = [], 0
    for s, m in list(todo.items())[:limit]:
        mbid = moved.get(s, m)
        p = pop.get(mbid)
        row = {"month": "", "spotify_id": s, "mbid": mbid, "users_all": "", "listens_all": "", "users_month": "",
               "listens_month": "", "from": "", "to": "", "fetched": datetime.now(timezone.utc).date().isoformat()}
        if p:
            row["users_all"], row["listens_all"] = p
            url = f"{API}/stats/artist/{mbid}/listeners"
            r = get(url, params={"range": "month"})
            if r.status_code == 200:
                body = r.json()
                storage.archive(f"listenbrainz/{month}/listeners/{mbid}.json", url + "?range=month",
                                json.dumps(strip_users(body), sort_keys=True).encode())
                row.update(parse_listeners(body["payload"]))
                row["month"] = row["from"][:7]
                n_month += 1
            # 204: ListenBrainz has not computed this artist's listener stats (it answers 204 for every range, even
            # all_time, for artists its popularity table counts, e.g. will.i.am): unknown, not zero, so left blank
        rows.append(row)
        if len(rows) % 100 == 0:
            _write(have, rows)
    _write(have, rows)
    return {"asked": len(todo), "known": sum(1 for s, m in todo.items() if pop.get(moved.get(s, m))),
            "redirected": len(moved), "with_month": n_month}


def _read() -> list[dict]:
    if not CSV.exists():
        return []
    with CSV.open() as f:
        return list(csv.DictReader(f))


def _write(have: list[dict], new: list[dict]) -> None:
    keys = {(r["spotify_id"], r["fetched"][:7]) for r in new}
    rows = [r for r in have if (r["spotify_id"], r["fetched"][:7]) not in keys] + new
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["spotify_id"], r["fetched"])))


def load() -> dict[str, dict]:
    """spotify_id -> the latest row, with ints and `history` [(month, users_month)] oldest first."""
    out: dict[str, dict] = {}
    for r in _read():
        r = {**r, **{k: int(r[k]) if r[k] not in ("", None) else None
                     for k in ("users_all", "listens_all", "users_month", "listens_month")}}
        prev = out.get(r["spotify_id"])
        hist = (prev or {}).get("history", [])
        if r["month"] and r["users_month"] is not None:
            hist = sorted({*hist, (r["month"], r["users_month"])})
        out[r["spotify_id"]] = {**r, "history": hist} if not prev or r["fetched"] >= prev["fetched"] else {**prev, "history": hist}
    return out
