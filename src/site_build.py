"""Builds site/data/index.json: every number the pages show, computed once; the browser only reads and sorts."""
import csv
import json
from datetime import date, datetime, timedelta, timezone

from . import current, insights, labels, money, revenue
from .collectors import apple_charts, deezer_releases, wayback, wikipedia, kworb, kworb_countries, kworb_youtube, release_dates, youtube_api
from .config import REGISTRY, SITE
from .run import PHOTOS, TOP_N, _json, latest_listeners, load_artists

OUT = SITE / "data" / "index.json"
# fields only the artist page needs: written to site/data/a/<id>.json, so the index stays small at 1,000 artists
DETAIL_ONLY = ("genre_basis", "links", "label_basis", "label_isrc_note", "label_confidence", "label_override",
               "labels", "born", "since", "streams", "lead_streams", "feature_streams", "lead_daily", "feature_daily",
               "tracks", "top_track", "top_track_streams", "streams_date", "yt_total", "yt_subs", "yt_channel_views",
               "peak_rank", "attention_series", "worth")


def latest_streams() -> dict[str, dict]:
    out = {}
    if kworb.STREAMS_CSV.exists():
        with kworb.STREAMS_CSV.open() as f:
            for r in csv.DictReader(f):
                if r["spotify_id"] not in out or r["date"] >= out[r["spotify_id"]]["date"]:
                    out[r["spotify_id"]] = r
    return out


num = lambda v: int(v) if v not in (None, "") else None


def geography(by_country: dict[str, dict]) -> dict | None:
    """Chart presence: the countries where the artist has a song in Spotify's weekly top 200, best position first.
    Streams are kept for the combined top-100 view only: per artist they mislead, because a small country's chart
    needs far fewer streams than the US one."""
    if not by_country:
        return None
    top = sorted(by_country.items(), key=lambda x: (x[1]["best_pos"], -x[1]["streams"]))
    return {"chart_streams": sum(v["streams"] for v in by_country.values()), "countries": len(top),
            "in_us": "us" in by_country, "charts": [[cc, v["best_pos"], v["streams"]] for cc, v in top]}


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
    (geo, geo_weeks), ych = kworb_countries.load_recent(), youtube_api.load()
    rels, table, lab_over = deezer_releases.load(), labels.owners(), labels.overrides()
    views, history = wikipedia.load(), wayback.load()
    apple, apple_day = apple_charts.presence({s: a["name"] for s, a in artists.items() if a["genre"] == "hip_hop"})
    # recording codes of each artist's songs released in the last 2 years: a second check on the label status
    cutoff = date(today.year - 2, today.month, min(today.day, 28)).isoformat()
    lead = {}  # track IDs where the artist is the lead (not a guest), from the latest kworb page
    for sid in artists:
        pg = current.pages(sid)
        if pg:
            lead[sid] = {x["track_id"] for x in current.songs(pg[-1][1]) if not x["feature"]}
    isrcs: dict[str, list[str]] = {}
    for tid, tr in dates.items():
        if tr.get("isrc") and tr.get("deezer_date", "") >= cutoff and tid in lead.get(tr["artist_id"], ()):
            isrcs.setdefault(tr["artist_id"], []).append(tr["isrc"][:5])
    first = {a["spotify_id"]: labels.artist_status(rels.get(a.get("deezer_id", ""), []), a["name"], table)
             for a in artists.values() if a["genre"] == "hip_hop" and a.get("deezer_match") == "exact"}
    registrants = labels.learn_registrants(first, isrcs)
    rows = []
    for t in top:
        a = artists.get(t["spotify_id"])
        if not a or a["genre"] != "hip_hop":
            continue
        s = streams.get(t["spotify_id"], {})
        majors = [m for m in a["major"].split("|") if m]
        wd_labels = [l for l in a["labels"].split("|") if l]
        status = first.get(t["spotify_id"]) or {"status": "unknown", "owner": "", "basis": None, "releases": []}
        status = labels.check_with_isrcs(status, isrcs.get(t["spotify_id"], []), registrants)
        if t["spotify_id"] in lab_over:
            o = lab_over[t["spotify_id"]]
            status = {**status, "status": o["status"], "owner": o.get("owner", ""), "override": o.get("note") or "owner"}
        # deal type: the current label status when known, else Wikidata's career-long label list
        deal = labels.DEAL_OF_STATUS.get(status["status"]) or money.deal_type(majors, wd_labels)
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
            "labels": wd_labels, "major": majors[0] if len(majors) == 1 else ("several majors" if majors else None),
            "deal_type": deal, "label_status": status["status"], "label_owner": status["owner"] or None,
            "label_basis": status["basis"], "label_override": status.get("override"),
            "label_isrc_note": status.get("isrc_note") or None, "label_confidence": status.get("confidence"),
            "money": money.estimate(num(s.get("lead_daily")), deal),
            "photo": pics.get(t["spotify_id"]) or None, "genre_basis": a["genre_basis"],
            "cur_share": round(cur["current_share"], 4) if cur.get("current_share") is not None else None,
            "coverage": round(cur.get("coverage", 0), 3), "cl": round(ml * cur["current_share"]) if cur.get("ok") else None,
            "revivals": cur.get("revivals", []),
            "fresh_share": round(cur["fresh_share"], 4) if cur.get("fresh_share") is not None and cur.get("ok") else None,
            "fresh_daily": cur.get("fresh_daily"), "top_fresh": cur.get("top_fresh"),
            "latest_release": cur.get("latest_release"),
            "attention": insights.attention(views.get(t["spotify_id"], [])),
            "apple": apple.get(t["spotify_id"]),
            "growth90": insights.growth(history.get(t["spotify_id"], []), today.isoformat()),
            "yt_total": num(yt.get(t["spotify_id"], {}).get("total_views")),
            "yt_daily": num(yt.get(t["spotify_id"], {}).get("daily_views")),
            "yt_subs": num(ych.get(t["spotify_id"], {}).get("subscribers")),
            "yt_channel_views": num(ych.get(t["spotify_id"], {}).get("views")),
            "geo": geography(geo.get(t["spotify_id"], {})),
            "links": {"spotify": f"https://open.spotify.com/artist/{t['spotify_id']}",
                      "wikidata": a["wikidata_id"] and f"https://www.wikidata.org/wiki/{a['wikidata_id']}",
                      "youtube": a["youtube_channel"] and f"https://www.youtube.com/channel/{a['youtube_channel']}",
                      "instagram": a["instagram"] and f"https://www.instagram.com/{a['instagram']}",
                      "tiktok": a["tiktok"] and f"https://www.tiktok.com/@{a['tiktok']}",
                      "x": a["x"] and f"https://x.com/{a['x']}"},
        })
    for r in rows:
        sh = shares[r["deal_type"]]
        r["revenue"] = revenue.estimate(r, today, {k: float(sh[k]) for k in ("low", "mid", "high")})
    rows = rows[:TOP_N]  # the site covers the top 1,000 hip-hop artists by monthly listeners
    insights.scout(rows)
    mult = insights.multiples()
    for r in rows:
        r["worth"] = insights.worth(r, r["revenue"], mult)
        r["worth_mid"] = round(r["worth"]["recordings"]["mid"] + r["worth"]["publishing"]["mid"])
        r["level"] = insights.level(r)
        att = r.pop("attention")
        r["attention"] = {"trend": round(att["trend"], 3) if att["trend"] else None, "last3": att["last3"]} if att else None
        r["attention_series"] = att and {"start": att["start"], "views": att["series"]}
    for i, r in enumerate(rows, 1):
        r["rank"] = i  # by monthly listeners
    for i, r in enumerate(sorted((r for r in rows if r["cl"] is not None), key=lambda r: -r["cl"]), 1):
        r["cl_rank"] = i  # our ranking: current listeners
    unsigned = benchmark(rows, shares)
    write_label_review(rows)
    with (REGISTRY / "rates.csv").open() as f:
        rates = list(csv.DictReader(f))
    with (REGISTRY / "deal_shares.csv").open() as f:
        deals = list(csv.DictReader(f))
    day = max((r["date"] for r in csv.DictReader(kworb.LISTENERS_CSV.open())), default=None)
    return {"built": datetime.now(timezone.utc).isoformat(timespec="minutes"), "as_of": day,
            "universe": len(top), "artists": rows, "rates": rates, "deals": deals,
            "platforms": revenue.platforms(), "multipliers": revenue.multipliers(), "tours": tour_table(rows),
            "countries": {r["code"]: r["name"] for r in csv.DictReader((REGISTRY / "countries.csv").open())},
            "chart_weeks": kworb_countries.load_recent()[1],  # {"weeks": n, "latest": week}
            "registrants": registrants, "unsigned": unsigned, "market": insights.market(rows),
            "scout_factors": {k: {"weight": w, "label": l} for k, (w, l) in insights.FACTORS.items()},
            "multiples": mult, "apple_day": apple_day, "apple_countries": len(apple_charts.COUNTRIES)}


SIGNED = ("major", "major_distributed", "independent")


def benchmark(rows: list[dict], shares: dict) -> list[dict]:
    """Each unsigned (self-released) artist against the 5 growing signed artists closest in monthly listeners (within a
    factor of 1.67 either way, else 2.5) and share of listening on recent releases. All money is yearly at today's
    pace, mid estimate."""
    import math
    gen = lambda r: sum(l["generated"]["mid"] for l in r["revenue"]["lines"] if l["group"] == "Streaming") or None
    spl = lambda r: r["daily"] / r["ml"] if r.get("daily") and r.get("ml") else None  # streams a day per listener
    signed = [r for r in rows if r["label_status"] in SIGNED and gen(r)]
    out = []
    for u in rows:
        if u["label_status"] != "self_released" or not gen(u):
            continue
        def dist(p):
            d = abs(math.log(p["ml"] / u["ml"]))
            if p.get("cur_share") is not None and u.get("cur_share") is not None:
                d += abs(p["cur_share"] - u["cur_share"])
            return d
        # "growing" peers: active, with at least 20% of their listening on recent releases (until 28-day listener
        # growth is available); the listener band widens when fewer than 3 qualify
        active = [p for p in signed if (p.get("cur_share") or 0) >= 0.2]
        peers = sorted([p for p in active if 0.6 <= p["ml"] / u["ml"] <= 1.67], key=dist)[:5]
        if len(peers) < 3:
            peers = sorted([p for p in active if 0.4 <= p["ml"] / u["ml"] <= 2.5], key=dist)[:5]
        if not peers:
            continue
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
        g_u, peer_gen = gen(u), med([gen(p) for p in peers])
        peer_spl, u_spl = med([spl(p) for p in peers if spl(p)]), spl(u)
        diy, keep = float(shares["diy"]["mid"]), {k: float(shares[k]["mid"]) for k in ("major", "services", "independent")}
        out.append({
            "id": u["id"], "name": u["name"], "ml": u["ml"], "cl": u.get("cl"), "cur_share": u.get("cur_share"),
            "confidence": u.get("label_confidence"), "label": (u.get("label_basis") or {}).get("label"),
            "generated": round(g_u), "keeps_now": round(g_u * diy), "spl": u_spl,
            "peers": [{"id": p["id"], "name": p["name"], "ml": p["ml"], "status": p["label_status"],
                       "owner": p.get("label_owner"), "generated": round(gen(p)),
                       "artist_slice": round(gen(p) * float(shares[p["deal_type"]]["mid"])), "spl": spl(p)} for p in peers],
            "peer_generated": round(peer_gen), "peer_spl": peer_spl,
            # what the artist would generate with the peers' streams per listener
            "at_peer_engagement": round(g_u * peer_spl / u_spl) if peer_spl and u_spl else None,
            # the artist's slice of today's royalties under each deal, and the growth a deal needs to beat staying DIY
            "if_signed": {k: round(g_u * v) for k, v in keep.items()},
            "break_even": {k: round(diy / v, 2) for k, v in keep.items()},
        })
    return sorted(out, key=lambda x: (-(x["cl"] or 0), -x["ml"]))  # our ranking first, then monthly listeners


def write_label_review(rows: list[dict]) -> None:
    """Artists whose label status is unknown, or rests on the label name only, for the owner to settle in
    registry/label_overrides.csv. Biggest audience first."""
    from .config import REVIEW
    items = [r for r in rows if r["label_status"] == "unknown" or r.get("label_confidence") == "label name only"]
    with (REVIEW / "label_review.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["spotify_id", "name", "monthly_listeners", "status_now", "latest_label", "codes_note", "spotify_url"])
        for r in sorted(items, key=lambda r: -r["ml"]):
            w.writerow([r["id"], r["name"], r["ml"], r["label_status"] + (" (label name only)" if r.get("label_confidence") == "label name only" else ""),
                        (r.get("label_basis") or {}).get("label", ""), r.get("label_isrc_note") or "", r["links"]["spotify"]])


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
    # per-artist detail in 32 shard files, site/data/a/<n>.json with n = second character's code % 32 (app.js uses the
    # same rule): a few dozen files instead of one per artist
    shard_dir = OUT.parent / "a"
    shard_dir.mkdir(exist_ok=True)
    for old in shard_dir.glob("*.json"):
        old.unlink()
    shards: dict[int, dict] = {}
    for r in data["artists"]:
        rev = r.pop("revenue")
        detail = {**{k: r.pop(k) for k in DETAIL_ONLY if k in r}, "photo": r.get("photo")}  # full photo credit
        shards.setdefault(ord(r["id"][1]) % 32, {})[r["id"]] = {**rev, "artist": detail}
        r["rev_total"] = {k: round(v) for k, v in rev["artist_total"].items()} if rev["artist_total"] else None
        r["rev_lines"] = {l["key"]: round(l["generated"]["mid"]) for l in rev["lines"]}
        if r.get("money"):
            r["money"] = {"generated": {k: round(v) for k, v in r["money"]["generated"].items()}, "deal_label": r["money"]["deal_label"]}
        if r.get("photo"):
            r["photo"] = {"file": r["photo"]["file"]}
    for n, d in shards.items():
        (shard_dir / f"{n}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"{OUT.relative_to(SITE.parent)}: {len(data['artists'])} hip-hop artists, {OUT.stat().st_size // 1024} KB")
