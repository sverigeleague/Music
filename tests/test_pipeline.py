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
