from pathlib import Path

from src import genre, money
from src.collectors import deezer, kworb

FIX = Path(__file__).parent / "fixtures"


def test_listeners_page():
    rows = kworb.parse_listeners((FIX / "listeners_head.html").read_text())
    assert rows[0] == {"spotify_id": "0du5cEVh5yTK9QJze8zA0C", "name": "Bruno Mars", "rank": 1,
                       "monthly_listeners": 128438090, "daily_change": -134036, "peak_rank": 1,
                       "peak_listeners": 151079821}
    assert len(rows) == 3  # the header row has no artist link


def test_artist_page():
    html = (FIX / "artist_drake.html").read_text()
    a = kworb.parse_artist(html)
    assert kworb.parse_updated(html) == "2026-10-22"
    assert a["total_streams"] == 143332619836 and a["lead_daily"] == 44624979 and a["feature_tracks"] == 200
    assert a["total_streams"] == a["lead_streams"] + a["feature_streams"]
    assert a["top_track"] == "One Dance"


def test_genre_families():
    assert genre.family("southern hip hop") == "hip_hop"
    assert genre.family("trap latino") == "latin"
    assert genre.family("rap rock") == "other"
    assert genre.family("trip hop") == "other"


def test_genre_decision():
    assert genre.decide([("hip hop", 21), ("r&b", 10), ("pop rap", 8)], [])[0] == "hip_hop"     # Drake
    assert genre.decide([("pop", 14), ("funk", 6), ("r&b", 5)], [])[0] == "other"              # Bruno Mars
    assert genre.decide([("reggaeton", 7), ("trap latino", 5), ("hip hop", 1)], [])[0] == "latin"  # Bad Bunny
    assert genre.decide([("hip hop", 8), ("pop", 6), ("electronic", 4), ("pop rap", 4), ("dance", 4)], [])[0] == "review"
    assert genre.decide([], [])[0] == "review"
    # thin votes: Wikidata alone never includes without a vote
    assert genre.decide([], [("hip-hop", True, False)])[0] == "review"


def test_money_ranges():
    e = money.estimate(1_000_000, "major")
    assert e["streams_month"] == 30_440_000
    g, t = e["generated"], e["take_home"]
    assert round(g["mid"]) == 91_320  # 30.44m streams x $3.00 per 1,000
    assert g["low"] < g["mid"] < g["high"] and t["low"] < t["mid"] < t["high"]
    assert t["high"] <= g["high"] * 0.30 + 1e-6
    assert money.estimate(None, "major") is None
    assert money.deal_type(["Universal Music Group"], ["Interscope"]) == "major"
    assert money.deal_type([], []) == "unknown"


def test_deezer_names():
    assert deezer._norm("JAŸ-Z") == deezer._norm("Jay-Z")
    assert deezer._norm("Tyler, The Creator") == "tylerthecreator"


def test_song_rows():
    songs = kworb.parse_songs((FIX / "artist_drake.html").read_text())
    one = songs[0]
    assert one == {"track_id": "1zi7xx7UVEFkmKfv06H8x0", "title": "One Dance", "total": 4529127344,
                   "daily": 1631893, "feature": False}
    assert any(s["feature"] and s["title"] == "Work" for s in songs)  # kworb marks guest spots with *


def test_age_weight():
    from datetime import date
    from src.current import age_weight
    today = date(2026, 10, 23)
    assert age_weight(date(2026, 5, 1), today) == 1.0              # 6 months: current
    assert age_weight(date(2025, 4, 30), today) == 1.0              # just under 18 months
    assert 0.45 < age_weight(date(2024, 7, 23), today) < 0.55       # 27 months: halfway down
    assert age_weight(date(2023, 1, 1), today) == 0.0               # 46 months: catalog


def test_current_share_and_coverage():
    from datetime import date
    from src.current import score
    today = date(2026, 10, 23)
    rows = [{"track_id": "new", "title": "New", "daily": 600, "feature": False},
            {"track_id": "old", "title": "Old", "daily": 300, "feature": False},
            {"track_id": "guest", "title": "Guest", "daily": 200, "feature": True},   # counts 100
            {"track_id": "undated", "title": "?", "daily": 50, "feature": False}]
    dates = {"new": {"first_release": "2026-09-01"}, "old": {"first_release": "2015"},
             "guest": {"first_release": "2026-01-10"}}
    s = score(rows, dates, today)
    assert round(s["current_share"], 4) == round(700 / 1000, 4)  # (600 + 100) / (600 + 300 + 100)
    assert round(s["coverage"], 4) == round(1000 / 1050, 4) and s["ok"]
    assert score(rows, {"new": dates["new"]}, today)["ok"] is False  # 600 / 1050 dated: below 80%


def test_revival():
    from datetime import date
    from src.current import score
    today = date(2026, 10, 23)
    rows = [{"track_id": "old", "title": "Old", "daily": 400, "feature": False},
            {"track_id": "new", "title": "New", "daily": 600, "feature": False}]
    earlier = [{"track_id": "old", "title": "Old", "daily": 200, "feature": False}]
    dates = {"old": {"first_release": "2012-06-01"}, "new": {"first_release": "2026-08-01"}}
    s = score(rows, dates, today, earlier)
    assert s["revivals"] == [{"title": "Old", "year": 2012, "rise": 1.0}]
    assert s["current_share"] == 0.6  # the revived song stays out of the current share


def test_release_date_keys():
    from src.collectors.release_dates import _key, norm
    assert min(["2016-05-06", "2016"], key=_key) == "2016-05-06"   # a year-only date never wins by being short
    assert min(["2018-06-29", "2018-01-19"], key=_key) == "2018-01-19"
    assert norm("All The Stars (with SZA) - From \"Black Panther\"") == "allthestars"
    assert norm("LOVE. FEAT. ZACARI.") == norm("LOVE.") == "love"
    assert norm("Bitch, Don’t Kill My Vibe") == norm("Bitch, Don't Kill My Vibe")


def test_revenue_lines(monkeypatch):
    from datetime import date
    from src import revenue
    monkeypatch.setattr(revenue, "tours", lambda: [
        {"artist": "Test", "tour": "Old", "start": "2024-01-01", "end": "2024-06-01", "gross_usd": "50000000", "tickets": "400000", "grade": "A"},
        {"artist": "Test", "tour": "Now", "start": "2026-04-23", "end": "2026-12-31", "gross_usd": "100000000", "tickets": "500000", "grade": "A"}])
    monkeypatch.setattr(revenue, "deals", lambda: [])
    today = date(2026, 10, 23)
    t = revenue.tour_last_12_months("Test", today)
    assert [x["tour"] for x in t["tours"]] == ["Now"]           # the 2024 tour is outside the 12 months
    assert 0.72 < t["tours"][0]["share"] < 0.74                  # 184 of 253 days so far
    est = revenue.estimate({"name": "Test", "lead_daily": 1_000_000, "yt_daily": 100_000}, today,
                           {"low": 0.15, "mid": 0.2, "high": 0.3})
    by = {l["key"]: l for l in est["lines"]}
    assert round(by["spotify"]["generated"]["mid"]) == 1_095_000   # 365m streams x $3.00 per 1,000
    assert by["spotify"]["artist"]["mid"] == by["spotify"]["generated"]["mid"] * 0.2
    assert by["publishing"]["artist"] is None                       # writer share unknown: generated only
    assert by["touring"]["grade"] == "A" and by["merch"]["grade"] == "C"
    assert by["merch"]["artist"]["mid"] < by["merch"]["generated"]["mid"]
    assert est["artist_total"]["low"] < est["artist_total"]["mid"] < est["artist_total"]["high"]
