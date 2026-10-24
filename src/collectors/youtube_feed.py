"""A YouTube channel's latest uploads from its public feed (https://www.youtube.com/feeds/videos.xml?channel_id=...):
no key, no login, the last 15 uploads with title, date and view count. Used for Scout's risers that kworb's YouTube
pages do not cover (kworb tracks only artists big on YouTube). Channel IDs come from Wikidata (artists.csv
youtube_channel). Shorts are left out.
"""
import re
import html as htmllib

from ..http import get

FEED = "https://www.youtube.com/feeds/videos.xml"


def latest(channel_id: str) -> list[dict]:
    r = get(FEED, params={"channel_id": channel_id})
    if r.status_code != 200:
        return []
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", r.text, re.S):
        vid = re.search(r"<yt:videoId>([\w-]{11})</yt:videoId>", entry)
        link = re.search(r'<link rel="alternate" href="([^"]+)"', entry)
        if not vid or (link and "/shorts/" in link[1]):
            continue
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        published = re.search(r"<published>(\d{4}-\d{2}-\d{2})", entry)
        views = re.search(r'<media:statistics views="(\d+)"', entry)
        out.append({"id": vid[1], "title": htmllib.unescape(title[1]).strip() if title else "",
                    "published": published[1] if published else "", "views": int(views[1]) if views else None})
    return out
