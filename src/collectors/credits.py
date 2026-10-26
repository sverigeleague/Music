"""Producer and songwriter credits from MusicBrainz (core data CC0), for each tracked artist's biggest songs.

Song -> recording code (ISRC, from data/track_dates.csv) -> MusicBrainz recording (GET /isrc/<isrc>) -> its relations
(GET /recording/<id>?inc=artist-rels+work-rels+work-level-rels): producers on the recording, writers on the work.
Two requests per song at MusicBrainz's 1 a second; each recording code is looked up once (data/credits.csv) and
retried after RETRY_DAYS if MusicBrainz had nothing then. Coverage is partial: MusicBrainz volunteers have entered
producer credits for about a third of the hip-hop hits tested (2026-10-24), and the site says so.

Publishers on record (2026-10-26): the same recording call also asks for label-rels, so each work comes with its
"publishing" links to MusicBrainz labels (name, label ID, the "sub" flag for a sub-publisher) and its ISWC (the song's
ID code). No shares: MusicBrainz has none. Rows looked up before then have no pub_checked date and are looked up again
once (resumable: saved every 50). Names are grouped to their publishing group by group() below; record companies
entered as publishers (Sony Music Entertainment, Universal Music Group, ... Records) are dropped by record_company().
"""
import csv
import re
import unicodedata
from datetime import date, timedelta

from ..config import DATA
from ..http import get

API = "https://musicbrainz.org/ws/2"
CSV = DATA / "credits.csv"
FIELDS = ["isrc", "recording", "title", "producers", "writers", "checked", "work", "iswc", "publishers", "pub_checked"]
PER_ARTIST, RETRY_DAYS = 3, 90
_join = lambda people: ";".join(f"{n}~{m}" for n, m in people)


def split(cell: str) -> list[tuple[str, str]]:
    """'Mustard~<mbid>;Sounwave~<mbid>' -> [('Mustard', '<mbid>'), ...]"""
    return [tuple(p.split("~", 1)) for p in filter(None, (cell or "").split(";"))]


def load() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    with CSV.open() as f:
        return {r["isrc"]: r for r in csv.DictReader(f)}


def lookup(isrc: str, recording: str = "") -> dict:
    """One song; a recording already found (the publisher re-check) is asked for directly, one request instead of two."""
    today = date.today().isoformat()
    row = {"isrc": isrc, "recording": "", "title": "", "producers": "", "writers": "", "checked": today,
           "work": "", "iswc": "", "publishers": "", "pub_checked": today}
    if recording:
        recs = [{"id": recording}]
    else:
        r = get(f"{API}/isrc/{isrc}", params={"fmt": "json"})
        recs = r.json().get("recordings", []) if r.status_code == 200 else []
    if not recs:
        return row
    rec = recs[0]
    d = get(f"{API}/recording/{rec['id']}", params={"fmt": "json", "inc": "artist-rels+work-rels+work-level-rels+label-rels"})
    if d.status_code != 200:
        return {**row, "pub_checked": ""}
    return {**row, **parse(d.json()), "recording": rec["id"]}


def parse(j: dict) -> dict:
    """A recording reply (inc artist-rels+work-rels+work-level-rels+label-rels) -> producers, writers, work, ISWCs and
    publishers ('Name~<label mbid>' or 'Name~<label mbid>~sub' for a sub-publisher)."""
    rels = j.get("relations", [])
    works = [x["work"] for x in rels if x.get("work")]
    prod = {(x["artist"]["name"], x["artist"]["id"]) for x in rels if x.get("artist") and x.get("type") == "producer"}
    writers = {(y["artist"]["name"], y["artist"]["id"]) for w in works
               for y in w.get("relations", []) if y.get("artist") and y.get("type") in ("writer", "composer", "lyricist")}
    pubs = {}
    for w in works:
        for y in w.get("relations", []):
            if y.get("label") and y.get("type") == "publishing":
                lab = y["label"]
                sub = "sub" in (y.get("attributes") or []) and pubs.get(lab["id"], (0, "~sub"))[1].endswith("~sub")
                pubs[lab["id"]] = (lab["name"], lab["id"] + "~sub" * sub)  # sub-publisher only if every link says so
    iswcs = dict.fromkeys(i for w in works for i in w.get("iswcs") or [])
    return {"title": j.get("title", ""), "producers": _join(sorted(prod)), "writers": _join(sorted(writers)),
            "work": next((w["id"] for w in works if any(y.get("label") for y in w.get("relations", []))), works[0]["id"] if works else ""),
            "iswc": ";".join(iswcs), "publishers": _join(sorted(pubs.values(), key=lambda p: p[0].lower())),
            "pub_checked": date.today().isoformat()}


def _norm(name: str) -> str:
    """Lower case, accents off, dashes and slashes as spaces: 'Warner–Tamerlane', 'Sony/ATV' -> 'warner tamerlane', 'sony atv'."""
    s = unicodedata.normalize("NFC", re.sub("[\u0300-\u036f]", "", unicodedata.normalize("NFKD", name)))  # Latin accents only
    return " ".join(re.sub(r"[-‐‑‒–—/]", " ", s.lower()).split())


# Publishing groups by name (normalised as _norm). First match wins; everything else is "Independent and other".
# EMI Music Publishing (EMI April, EMI Blackwood) has been Sony's since 2018, Sony/ATV renamed Sony Music Publishing in
# 2021; Warner-Tamerlane, WB Music and WC Music are Warner Chappell's US companies; Songs of Universal, Universal Music
# Corp. and PolyGram publishing are Universal's, as are Zomba, Rondor, Almo and Careers-BMG (the old BMG Music
# Publishing, bought by Universal in 2007; today's BMG is the later BMG Rights Management); Imagem joined Concord in 2017; Songtrust and Sentric are Downtown's.
GROUPS = [
    ("Sony Music Publishing", r"^sony (music publishing|atv)|^emi\b|ソニー・ミュージックパブリッシング"),
    ("Universal Music Publishing Group", r"^universal (music|musica|songs|polygram|mca)\b|^songs of universal|^polygram|^zomba\b|^rondor\b|^almo music|^careers bmg"),
    ("Warner Chappell", r"warner chappell|^warner tamerlane|^(wb|wc) music\b|^(uni)?chappell\b|^warner bros\b.*music|ワーナー・チャペル"),
    ("Kobalt", r"kobalt"),
    ("BMG", r"^bmg\b"),
    ("Concord", r"^concord\b|imagem"),
    ("Reservoir", r"^reservoir\b"),
    ("Downtown / Songtrust", r"^downtown\b|songtrust|^sentric\b"),
]
OTHER = "Independent and other"
# Record companies, not publishers: the majors' recorded-music companies by name, and any "... Records" or
# "... Recordings" name without a publishing word. Entered as publishers by mistake (One Dance, God's Plan); dropped.
RECORD_COMPANIES = {"sony music entertainment", "sony music", "sony bmg music entertainment", "universal music group",
                    "universal music", "umg recordings", "umg recordings inc.", "warner music group", "warner music group corp.",
                    "warner music", "warner records", "warner records inc.", "warner bros. records", "emi records"}
# Entries that say there is no publisher ("Copyright Control": the writer holds the rights): not shown either.
NO_PUBLISHER = {"copyright control", "unpublished", "public domain", "not published", "self published"}
_PUB_WORD = re.compile(r"publish|songs|tunes|edition|verlag|editora|edizioni|chappell")


def record_company(name: str) -> bool:
    """A record company (or a 'no publisher' entry), which is never shown as a publisher."""
    n = _norm(name)
    return n in RECORD_COMPANIES or n in NO_PUBLISHER or (bool(re.search(r"\b(records|recordings)\b", n)) and not _PUB_WORD.search(n))


def group(name: str) -> str:
    n = _norm(name)
    return next((g for g, rx in GROUPS if re.search(rx, n)), OTHER)


def publishers(cell: str) -> tuple[list[dict], list[str]]:
    """A publishers cell -> ([{group, names}] in GROUPS order, other last; record companies dropped), dropped names."""
    by, dropped = {}, []
    for p in filter(None, (cell or "").split(";")):
        name = p.split("~", 1)[0]
        if record_company(name):
            dropped.append(name)
        else:
            by.setdefault(group(name), []).append(name)
    order = [g for g, _ in GROUPS] + [OTHER]
    return [{"group": g, "names": by[g]} for g in order if g in by], dropped


def update(isrcs: list[str], limit: int | None = None) -> int:
    have = load()
    stale = (date.today() - timedelta(days=RETRY_DAYS)).isoformat()
    todo = [i for i in dict.fromkeys(isrcs) if i and (i not in have or (not have[i]["recording"] and have[i]["checked"] < stale)
                                                     or (have[i]["recording"] and not have[i].get("pub_checked")))]
    n = 0
    for isrc in todo[:limit]:
        old = have.get(isrc) or {}
        row = lookup(isrc, old.get("recording", ""))
        have[isrc] = row if row["recording"] or not old.get("recording") else old  # a failed re-check keeps the old row
        n += 1
        if n % 50 == 0:
            _save(have)
    _save(have)
    return n


def _save(rows: dict) -> None:
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: r["isrc"]))


def leaderboard(songs: list[dict], role: str = "producers", top: int = 50) -> list[dict]:
    """songs: [{isrc, title, daily, artist_id, artist}] -> people ranked by the daily streams of the songs they are
    credited on, with how many songs and artists."""
    cred, people = load(), {}
    for s in songs:
        c = cred.get(s.get("isrc") or "")
        for name, mbid in split(c[role]) if c else []:
            p = people.setdefault(mbid, {"name": name, "mbid": mbid, "daily": 0, "songs": [], "artists": set(), "isrcs": set()})
            if s["isrc"] in p["isrcs"]:  # one song on several artists' pages (a duo and its members) counts once
                continue
            p["isrcs"].add(s["isrc"])
            p["daily"] += s["daily"]
            p["songs"].append({"title": s["title"], "artist": s["artist"], "artist_id": s["artist_id"], "daily": s["daily"]})
            p["artists"].add(s["artist_id"])
    out = sorted(people.values(), key=lambda p: -p["daily"])[:top]
    for p in out:
        p["songs"] = sorted(p["songs"], key=lambda s: -s["daily"])[:5]
        p["artists"] = len(p["artists"])
        del p["isrcs"]
    return out
