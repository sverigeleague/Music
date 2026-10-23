"""Builds site/data/index.json: every number the pages show, computed once; the browser only reads and sorts."""
import csv
import json
from datetime import date, datetime, timedelta, timezone

from . import current, money, revenue
from .collectors import kworb, kworb_youtube, release_dates
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


def current_of(spotify_id: str, dates: dict, today: date) -> dict | None:
    """Current share, coverage and revivals from the artist's latest page (and one 28+ days older, if any)."""
    pages = current.pages(spotify_id)
    if not pages:
        return None
    latest_day, latest = pages[-1]
    cutoff = (date.fromisoformat(latest_day) - timedelta(days=current.REVIVAL_GAP_DAYS)).isoformat()
    older = [p for d, p in pages if d <= cutoff]
    return current.score(current.songs(latest), dates, today, current.songs(older[-1]) if older else None)


def build() -> dict:
    artists = load_artists()
    top = latest_listeners()
    streams, pics = latest_streams(), _json(PHOTOS, {})
    dates, today = release_dates.load(), datetime.now(timezone.utc).date()
    yt, shares = kworb_youtube.load_latest(), money.deal_shares()
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
        cur = current_of(t["spotify_id"], dates, today) or {}
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
            "cur_share": round(cur["current_share"], 4) if cur.get("current_share") is not None else None,
            "coverage": round(cur.get("coverage", 0), 3), "cl": round(ml * cur["current_share"]) if cur.get("ok") else None,
            "revivals": cur.get("revivals", []),
            "yt_total": num(yt.get(t["spotify_id"], {}).get("total_views")),
            "yt_daily": num(yt.get(t["spotify_id"], {}).get("daily_views")),
            "links": {"spotify": f"https://open.spotify.com/artist/{t['spotify_id']}",
                      "wikidata": a["wikidata_id"] and f"https://www.wikidata.org/wiki/{a['wikidata_id']}",
                      "youtube": a["youtube_channel"] and f"https://www.youtube.com/channel/{a['youtube_channel']}",
                      "instagram": a["instagram"] and f"https://www.instagram.com/{a['instagram']}",
                      "tiktok": a["tiktok"] and f"https://www.tiktok.com/@{a['tiktok']}",
                      "x": a["x"] and f"https://x.com/{a['x']}"},
        })
    for r in rows:
        sh = shares[r["money"]["deal_type"] if r["money"] else money.deal_type(
            [r["major"]] if r["major"] else [], r["labels"])]
        r["revenue"] = revenue.estimate(r, today, {k: float(sh[k]) for k in ("low", "mid", "high")})
    for i, r in enumerate(rows, 1):
        r["rank"] = i  # by monthly listeners
    for i, r in enumerate(sorted((r for r in rows if r["cl"] is not None), key=lambda r: -r["cl"]), 1):
        r["cl_rank"] = i  # our ranking: current listeners
    with (REGISTRY / "rates.csv").open() as f:
        rates = list(csv.DictReader(f))
    with (REGISTRY / "deal_shares.csv").open() as f:
        deals = list(csv.DictReader(f))
    day = max((r["date"] for r in csv.DictReader(kworb.LISTENERS_CSV.open())), default=None)
    return {"built": datetime.now(timezone.utc).isoformat(timespec="minutes"), "as_of": day,
            "universe": len(top), "artists": rows, "rates": rates, "deals": deals,
            "platforms": revenue.platforms(), "multipliers": revenue.multipliers(), "tours": tour_table(rows)}


def tour_table(rows: list[dict]) -> list[dict]:
    """Every counted tour (registry/tours.csv, use=Y, grade A/B) with per-show and per-fan figures and the artist's
    estimated slice (rule-of-thumb shares, C)."""
    ids = {r["name"].casefold(): r["id"] for r in rows}
    out = []
    for t in revenue.tours():
        if t.get("use") != "Y" or not t.get("gross_usd"):
            continue
        g, n, k = float(t["gross_usd"]), float(t["shows"] or 0), float(t["tickets"] or 0)
        share = float(t.get("artist_share") or 1)
        out.append({"artist": t["artist"], "id": ids.get(t["artist"].casefold()), "tour": t["tour"], "start": t["start"],
                    "end": t.get("end"), "shows": int(n) or None, "tickets": int(k) or None, "gross": g,
                    "per_show": g / n if n else None, "per_fan": g / k if k else None,
                    "co": t.get("co_headliner") or None, "share": share, "grade": t["grade"],
                    "artist_net": {kk: g * share * v for kk, v in zip(("low", "mid", "high"), revenue.TOUR_ARTIST_NET)},
                    "merch": {kk: k * share * v for kk, v in zip(("low", "mid", "high"), revenue.MERCH_PER_FAN)} if k else None,
                    "source": t["source_url"], "note": t["source_note"], "partial": bool(t.get("gross_through"))})
    return sorted(out, key=lambda x: -x["gross"])


if __name__ == "__main__":
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # revenue detail per artist in its own file (site/data/a/<id>.json), loaded when the artist page opens; the index
    # keeps the totals and each streaming line's mid estimate for the tables
    (OUT.parent / "a").mkdir(exist_ok=True)
    for r in data["artists"]:
        rev = r.pop("revenue")
        (OUT.parent / "a" / f"{r['id']}.json").write_text(json.dumps(rev, ensure_ascii=False, separators=(",", ":")))
        r["rev_total"] = rev["artist_total"]
        r["rev_lines"] = {l["key"]: round(l["generated"]["mid"]) for l in rev["lines"]}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"{OUT.relative_to(SITE.parent)}: {len(data['artists'])} hip-hop artists, {OUT.stat().st_size // 1024} KB")
