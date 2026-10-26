"""YouTube Data API v3: subscribers, total views and video count of each artist's own channel, and views a day.
Channel IDs: Wikidata P2397, else a youtube.com/channel/UC... link on the artist's MusicBrainz page (url relations,
data/musicbrainz_youtube.csv; only when exactly one channel is linked). Needs the secret YOUTUBE_API_KEY (GitHub
Actions); without it the step is skipped. Run daily (owner, 2026-10-25: "set up the YouTube data api").

Quota: channels.list costs 1 unit per call of up to 50 channels (10,000 units a day free; ~20 a day used here).
Terms (YouTube API Services Developer Policies): statistics may be kept for at most 30 days unless refreshed, and no
long history may be built without YouTube's audited-analytics approval (III.L). So data/youtube_channels.csv holds
the latest snapshot plus, per channel, one earlier snapshot 7-30 days old, used only to work out views a day over
that window; anything older than 30 days is dropped. Subscriber counts are rounded by YouTube to 3 significant
figures. Channel views count every video on the artist's own channel (not fan uploads or other channels).
"""
import csv
import os
from datetime import date

from ..config import DATA
from ..http import get

API = "https://www.googleapis.com/youtube/v3/channels"
CSV = DATA / "youtube_channels.csv"
FIELDS = ["date", "spotify_id", "channel_id", "subscribers", "views", "videos", "prev_date", "prev_views",
          "views_per_day"]
KEEP_DAYS, MIN_GAP_DAYS = 30, 7  # terms: at most 30 days; a week or more apart for a steady daily rate


def parse(items: list[dict]) -> dict[str, dict]:
    out = {}
    for it in items:
        st = it.get("statistics", {})
        out[it["id"]] = {"subscribers": None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0)),
                         "views": int(st.get("viewCount", 0)), "videos": int(st.get("videoCount", 0))}
    return out


def daily_rate(now: dict, prev: dict | None, today: date) -> dict:
    """Carry the earlier snapshot (7-30 days old) and the views a day since it; keep a younger earlier one until it
    is 7 days old; drop anything older than 30 days (API terms)."""
    out = {"prev_date": "", "prev_views": "", "views_per_day": ""}
    if not prev or not prev.get("date"):
        return out
    base = (prev["prev_date"], prev["prev_views"]) if prev.get("prev_date") else (prev["date"], prev["views"])
    if base[0] and (today - date.fromisoformat(base[0])).days > KEEP_DAYS:
        base = (prev["date"], prev["views"])  # too old to keep: the last snapshot becomes the base
    if not base[0] or (today - date.fromisoformat(base[0])).days > KEEP_DAYS:
        return out
    out["prev_date"], out["prev_views"] = base[0], base[1]
    days = (today - date.fromisoformat(base[0])).days
    if days >= MIN_GAP_DAYS and str(base[1]).isdigit() and now["views"] >= int(base[1]):
        out["views_per_day"] = round((now["views"] - int(base[1])) / days)
    elif str(prev.get("views_per_day", "")).isdigit():  # a new base is maturing: keep the last rate (under 30 days old)
        out["views_per_day"] = int(prev["views_per_day"])
    return out


def update(channels: dict[str, str], today: date | None = None) -> int | None:
    """channels: spotify_id -> channel ID. Returns rows written, or None when no key is set."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return None
    today = today or date.today()
    ids = sorted(set(channels.values()))
    stats = {}
    for i in range(0, len(ids), 50):
        r = get(API, params={"part": "statistics", "id": ",".join(ids[i:i + 50]), "key": key, "maxResults": 50})
        if r.status_code != 200:
            raise RuntimeError(f"YouTube API error {r.status_code}")  # the key is never printed
        stats.update(parse(r.json().get("items", [])))
    before = {(r["spotify_id"], r["channel_id"]): r for r in load().values()}
    rows = []
    for s, c in channels.items():
        if c in stats:
            now = {"date": today.isoformat(), "spotify_id": s, "channel_id": c, **stats[c]}
            rows.append({**now, **daily_rate(now, before.get((s, c)), today)})
    # the other genre's rows stay, if under 30 days old (the step runs once per genre)
    rows += [r for r in load().values() if r["spotify_id"] not in channels and r.get("date")
             and (today - date.fromisoformat(r["date"])).days <= KEEP_DAYS]
    with CSV.open("w", newline="") as f:  # latest snapshot plus one earlier base per channel (API terms)
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}
