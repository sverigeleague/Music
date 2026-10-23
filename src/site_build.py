"""Builds site/data/index.json: every number the pages show, computed once; the browser only reads and sorts."""
import csv
import json
from datetime import datetime, timezone

from . import money
from .collectors import kworb
from .config import REGISTRY, SITE
from .run import PHOTOS, _json, latest_listeners, load_artists

OUT = SITE / "data" / "index.json"


def latest_streams() -> dict[str, dict]:
    out = {}
    if kworb.STREAMS_CSV.exists():
        with kworb.STREAMS_CSV.open() as f:
            for r in csv.DictReader(f):
                if r["spotify_id"] not in out or r["date"] >= out[r["spotify_id"]]["date"]:
                    out[r["spotify_id"]] = r
    return out


num = lambda v: int(v) if v not in (None, "") else None


def build() -> dict:
    artists = load_artists()
    top = latest_listeners()
    streams, pics = latest_streams(), _json(PHOTOS, {})
    rows = []
    for t in top:
        a = artists.get(t["spotify_id"])
        if not a or a["genre"] != "hip_hop":
            continue
        s = streams.get(t["spotify_id"], {})
        majors = [m for m in a["major"].split("|") if m]
        labels = [l for l in a["labels"].split("|") if l]
        deal = money.deal_type(majors, labels)
        ml, chg = t["monthly_listeners"], t["daily_change"]
        rows.append({
            "id": t["spotify_id"], "name": t["name"], "rank_all": t["rank"], "ml": ml, "chg": chg,
            "chg_pct": round(chg / (ml - chg) * 100, 3) if ml and chg is not None and ml != chg else None,
            "peak_rank": t["peak_rank"], "peak_ml": t["peak_listeners"],
            "streams": num(s.get("total_streams")), "lead_streams": num(s.get("lead_streams")),
            "feature_streams": num(s.get("feature_streams")), "daily": num(s.get("total_daily")),
            "lead_daily": num(s.get("lead_daily")), "feature_daily": num(s.get("feature_daily")),
            "tracks": num(s.get("tracks")), "top_track": s.get("top_track") or None,
            "top_track_streams": num(s.get("top_track_streams")), "streams_date": s.get("date"),
            "deezer_fans": num(a.get("deezer_fans")) if a.get("deezer_match") == "exact" else None,
            "country": a["country"] or None, "born": a["born"] or None, "since": a["active_since"][:4] or None,
            "labels": labels, "major": majors[0] if len(majors) == 1 else ("several majors" if majors else None),
            "money": money.estimate(num(s.get("lead_daily")), deal),
            "photo": pics.get(t["spotify_id"]) or None, "genre_basis": a["genre_basis"],
            "links": {"spotify": f"https://open.spotify.com/artist/{t['spotify_id']}",
                      "wikidata": a["wikidata_id"] and f"https://www.wikidata.org/wiki/{a['wikidata_id']}",
                      "youtube": a["youtube_channel"] and f"https://www.youtube.com/channel/{a['youtube_channel']}",
                      "instagram": a["instagram"] and f"https://www.instagram.com/{a['instagram']}",
                      "tiktok": a["tiktok"] and f"https://www.tiktok.com/@{a['tiktok']}",
                      "x": a["x"] and f"https://x.com/{a['x']}"},
        })
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    with (REGISTRY / "rates.csv").open() as f:
        rates = list(csv.DictReader(f))
    with (REGISTRY / "deal_shares.csv").open() as f:
        deals = list(csv.DictReader(f))
    day = max((r["date"] for r in csv.DictReader(kworb.LISTENERS_CSV.open())), default=None)
    return {"built": datetime.now(timezone.utc).isoformat(timespec="minutes"), "as_of": day,
            "universe": len(top), "artists": rows, "rates": rates, "deals": deals}


if __name__ == "__main__":
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"{OUT.relative_to(SITE.parent)}: {len(data['artists'])} hip-hop artists, {OUT.stat().st_size // 1024} KB")
