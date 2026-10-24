"""Current listeners: our own ranking, so that old songs still streamed a lot do not drive it. Full reference with a
worked example: docs/METHODOLOGY.md (keep it in step with the numbers here; a change is a new method version).

    current listeners = monthly listeners x current share
    current share     = sum(age weight x daily streams) / sum(daily streams), over the artist's dated songs
    age weight        = 1 up to 18 months after first release, falling straight to 0 at 36 months
    featured songs count at half weight

Shown only when at least 80% of the artist's (weighted) daily streams are on dated songs. The formula itself is not
shown on the site yet (owner, 2026-10-23); the site describes it in general terms.

Revival: a song over 36 months old whose daily streams rose by at least half against a snapshot 28+ days earlier and
that makes up at least 2% of the artist's daily streams. It stays out of the score and gets a badge.
"""
import glob
import gzip
from datetime import date

from .collectors import kworb
from .config import RAW

FULL_MONTHS, ZERO_MONTHS = 18, 36
FEATURE_WEIGHT = 0.5
MIN_COVERAGE = 0.8
PROVISIONAL_COVERAGE = 0.5  # 50-80% dated: a provisional rank with a range (method 1.2)
DATE_SHARE, DATE_MAX = 0.90, 300  # songs dated per artist: until 90% of daily streams are covered, at most 300
REVIVAL_RISE, REVIVAL_SHARE, REVIVAL_GAP_DAYS = 1.5, 0.02, 28
FRESH_DAYS = 90  # Scout's release velocity: songs out this many days or fewer (not part of current listeners)


def parse_date(s: str) -> date | None:
    """'2024-05-04', '2024-05' or '2024' (MusicBrainz may give only a year: taken as mid-year)."""
    if not s:
        return None
    parts = s.split("-")
    try:
        if len(parts) == 1:
            return date(int(parts[0]), 7, 1)
        if len(parts) == 2:
            return date(int(parts[0]), int(parts[1]), 15)
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def months(released: date, today: date) -> float:
    return (today - released).days / 30.44


def age_weight(released: date, today: date) -> float:
    m = months(released, today)
    if m <= FULL_MONTHS:
        return 1.0
    return max(0.0, 1 - (m - FULL_MONTHS) / (ZERO_MONTHS - FULL_MONTHS))


def pages(spotify_id: str) -> list[tuple[str, str]]:
    """(snapshot date, path) of every archived artist page, oldest first."""
    return sorted((p.split("/")[-2], p) for p in glob.glob(str(RAW / "kworb" / "artist" / "*" / f"{spotify_id}.html.gz")))


def songs(path: str) -> list[dict]:
    with gzip.open(path, "rt") as f:
        return kworb.parse_songs(f.read())


def to_date(rows: list[dict]) -> list[dict]:
    """The songs worth dating: biggest daily streams first, until 90% of the weighted daily total (max 300)."""
    wd = lambda r: r["daily"] * (FEATURE_WEIGHT if r["feature"] else 1)
    total = sum(wd(r) for r in rows) or 1
    out, acc = [], 0.0
    for r in sorted(rows, key=lambda r: -wd(r)):
        if acc / total >= DATE_SHARE or len(out) >= DATE_MAX or r["daily"] == 0:
            break
        out.append(r)
        acc += wd(r)
    return out


def score(rows: list[dict], dates: dict[str, dict], today: date, earlier: list[dict] | None = None) -> dict:
    """rows: the artist's songs on the latest page; dates: track_id -> cache row; earlier: songs on a page 28+ days
    before (for revivals)."""
    wd = lambda r: r["daily"] * (FEATURE_WEIGHT if r["feature"] else 1)
    total = sum(wd(r) for r in rows)
    dated = cur = fresh = 0.0
    revivals, top_fresh, latest = [], None, None
    before = {r["track_id"]: r["daily"] for r in earlier or []}
    for r in rows:
        d = parse_date(dates.get(r["track_id"], {}).get("first_release", ""))
        if not d:
            continue
        dated += wd(r)
        cur += wd(r) * age_weight(d, today)
        if 0 <= (today - d).days <= FRESH_DAYS:
            fresh += wd(r)
            if not top_fresh or r["daily"] > top_fresh["daily"]:
                top_fresh = {"title": r["title"], "daily": r["daily"], "released": d.isoformat(), "id": r["track_id"],
                             "dz": dates.get(r["track_id"], {}).get("deezer_id") or None}
        if not r["feature"] and d <= today and (not latest or d > latest):
            latest = d
        old = before.get(r["track_id"])
        if (months(d, today) > ZERO_MONTHS and old and r["daily"] >= REVIVAL_RISE * old
                and total and wd(r) / total >= REVIVAL_SHARE):
            revivals.append({"title": r["title"], "year": d.year, "rise": round(r["daily"] / old - 1, 2)})
    coverage = dated / total if total else 0.0
    share = cur / dated if dated else None
    return {"current_share": share, "coverage": coverage, "revivals": revivals,
            "ok": share is not None and coverage >= MIN_COVERAGE,
            "provisional": share is not None and PROVISIONAL_COVERAGE <= coverage < MIN_COVERAGE,
            # the range the undated songs could move the share: all old (weight 0) to all new (weight 1)
            "share_range": (round(share * coverage, 4), round(share * coverage + 1 - coverage, 4)) if share is not None else None,
            "fresh_daily": round(fresh), "fresh_share": fresh / total if total else 0.0, "top_fresh": top_fresh,
            "latest_release": latest.isoformat() if latest else None}
