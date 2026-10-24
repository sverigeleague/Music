"""Preview: current (frontline) share of each top-100 hip-hop artist's daily Spotify streams, from Deezer release dates."""
import csv, glob, gzip, html, json, re, sys, time, unicodedata
from datetime import date
import requests
ROOT, OUT = sys.argv[1], sys.argv[2]
S = requests.Session(); S.headers["User-Agent"] = "music-ledger/0.1 (swedenrocked@gmail.com)"
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    s = re.sub(r"\s*[\(\[].*?[\)\]]", "", s); s = re.sub(r"\s-\s.*$", "", s)
    return re.sub(r"[^a-z0-9]", "", s)
def get(url, **p):
    for i in range(4):
        try:
            r = S.get(url, params=p, timeout=30); time.sleep(0.12)
            j = r.json()
            if "error" in j and j["error"].get("code") == 4: time.sleep(5); continue
            return j
        except Exception: time.sleep(2)
    return {}
alb = {}
def first_date(name, title):
    q = re.sub(r"[(\[].*?[)\]]", "", title)
    ds = []
    for t in get("https://api.deezer.com/search", q=f"{name} {q}", limit=15).get("data", []):
        if norm(t["title"]) == norm(title) and norm(name) in norm(t["artist"]["name"]):
            a = t["album"]["id"]
            if a not in alb: alb[a] = get(f"https://api.deezer.com/album/{a}").get("release_date")
            if alb[a] and alb[a] > "1900": ds.append(alb[a])
    return min(ds) if ds else None
def songs(sp):
    f = sorted(glob.glob(f"{ROOT}/raw/kworb/artist/*/{sp}.html.gz"))[-1]
    h = gzip.open(f, "rt").read(); out = []
    for r in re.findall(r"<tr>(.*?)</tr>", h, re.S):
        m = re.search(r'track/(\w+)"[^>]*>(.*?)</a>.*?<td>([\d,]+)</td><td>([\d,]+)</td>', r, re.S)
        if m: out.append({"id": m[1], "title": html.unescape(m[2]), "total": int(m[3].replace(",", "")),
                          "daily": int(m[4].replace(",", "")), "feat": "*" in r.split("<a")[0]})
    return out
idx = json.load(open(f"{ROOT}/site/data/index.json")) if False else None
sys.path.insert(0, ROOT)
from src.run import latest_listeners, load_artists
arts = load_artists(); top = [t for t in latest_listeners() if arts.get(t["spotify_id"], {}).get("genre") == "hip_hop"][:100]
done = set()
try: done = {json.loads(l)["id"] for l in open(OUT)}
except FileNotFoundError: pass
with open(OUT, "a") as f:
    for t in top:
        if t["spotify_id"] in done: continue
        s = sorted(songs(t["spotify_id"]), key=lambda x: -x["daily"])
        for x in s[:20]:
            x["date"] = None if x["feat"] else first_date(t["name"], x["title"])
        f.write(json.dumps({"id": t["spotify_id"], "name": t["name"], "ml": t["monthly_listeners"], "songs": s}) + "\n"); f.flush()
