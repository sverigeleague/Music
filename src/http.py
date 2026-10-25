"""HTTP with a User-Agent, a pause between requests to the same host and a few retries."""
import threading
import time
from urllib.parse import urlparse

import requests

from .config import USER_AGENT

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last: dict[str, float] = {}
_lock = threading.Lock()  # pacing is shared by threads, so a worker pool still keeps each site's limit
# Seconds between requests per host: each site's published limit or a polite default.
PAUSE = {"musicbrainz.org": 1.1, "query.wikidata.org": 2.0, "kworb.net": 1.0, "api.deezer.com": 0.11, "wikimedia.org": 0.2, "en.wikipedia.org": 0.5, "web.archive.org": 3.0, "data.sec.gov": 0.2, "filings.xbrl.org": 0.5, "www.youtube.com": 1.0}


def get(url, params=None, headers=None, tries=4, timeout=60, data=None):
    """GET, or POST when `data` is given (long SPARQL queries)."""
    host = urlparse(url).hostname
    for attempt in range(tries):
        with _lock:
            slot = max(time.monotonic(), _last.get(host, 0) + PAUSE.get(host, 0.5))
            _last[host] = slot
        if slot > time.monotonic():
            time.sleep(slot - time.monotonic())
        try:
            r = (_session.post(url, data=data, headers=headers, timeout=timeout) if data is not None
                 else _session.get(url, params=params, headers=headers, timeout=timeout))
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt * 2)
            continue
        if r.status_code in (429, 500, 502, 503, 504) and attempt < tries - 1:
            time.sleep(int(r.headers.get("Retry-After") or 2 ** attempt * 2))
            continue
        return r
    return r
