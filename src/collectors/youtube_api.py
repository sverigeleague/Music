"""YouTube Data API v3: subscribers, total views and video count of each artist's channel (channel IDs from Wikidata
P2397). Needs the secret YOUTUBE_API_KEY; without it the step is skipped.

Quota: channels.list costs 1 unit per call of up to 50 channels (10,000 units a day free).
Terms: statistics may be kept for at most 30 days unless refreshed, and no history may be built without YouTube's
audited-analytics approval (III.L). So data/youtube_channels.csv holds only the latest snapshot, replaced each run.
Subscriber counts are rounded by YouTube to 3 significant figures.
"""
import csv
import os
from datetime import date

from ..config import DATA
from ..http import get

API = "https://www.googleapis.com/youtube/v3/channels"
CSV = DATA / "youtube_channels.csv"
FIELDS = ["date", "spotify_id", "channel_id", "subscribers", "views", "videos"]


def parse(items: list[dict]) -> dict[str, dict]:
    out = {}
    for it in items:
        st = it.get("statistics", {})
        out[it["id"]] = {"subscribers": None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0)),
                         "views": int(st.get("viewCount", 0)), "videos": int(st.get("videoCount", 0))}
    return out


def update(channels: dict[str, str]) -> int | None:
    """channels: spotify_id -> channel ID. Returns rows written, or None when no key is set."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return None
    ids = sorted(set(channels.values()))
    stats = {}
    for i in range(0, len(ids), 50):
        r = get(API, params={"part": "statistics", "id": ",".join(ids[i:i + 50]), "key": key, "maxResults": 50})
        if r.status_code != 200:
            raise RuntimeError(f"YouTube API error {r.status_code}")  # the key is never printed
        stats.update(parse(r.json().get("items", [])))
    today = date.today().isoformat()
    rows = [{"date": today, "spotify_id": s, "channel_id": c, **stats[c]} for s, c in channels.items() if c in stats]
    with CSV.open("w", newline="") as f:  # latest snapshot only (API terms)
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["spotify_id"]: r for r in csv.DictReader(f)}
