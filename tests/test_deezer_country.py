import csv

from src.collectors import deezer_country as dc

ALBUMS = {"1": [84, 84, 84, 116], "2": [84, 116, 116, 116], "3": [84, 84], "4": [84, 84, 84]}
RELATED = {"1": ["2", "3", "4"], "4": ["1"]}
FANS = {"1": 900, "2": 800, "3": 700, "4": 50}


def fake(path, **params):
    parts = path.split("/")
    if parts[0] in ("chart", "genre"):
        return {"data": [{"id": 1, "name": "A1", "nb_fan": FANS["1"]}]} if parts[0] == "chart" else {}
    aid = parts[1]
    if parts[-1] == "albums":
        return {"data": [{"genre_id": g, "release_date": f"2026-0{i + 1}-01"} for i, g in enumerate(ALBUMS[aid])]}
    if parts[-1] == "top":
        return {"data": [{"rank": 1000 * int(aid)}, {"rank": 10}]}
    if parts[-1] == "related":
        return {"data": [{"id": int(b), "name": f"A{b}", "nb_fan": FANS[b]} for b in RELATED.get(aid, [])]}
    return {}


def test_crawl_admits_country_only_and_orders_by_top_tracks(tmp_path, monkeypatch):
    monkeypatch.setattr(dc, "_json", fake)
    monkeypatch.setattr(dc, "CSV", tmp_path / "c.csv")
    monkeypatch.setattr(dc, "wikidata_deezer", lambda: {"4": {"qid": "Q4", "spotify_id": "sp4"}})
    monkeypatch.setattr(dc.deezer_genres, "load", lambda: {})
    assert dc.crawl() == 2  # 2 is mostly rap, 3 has too few releases
    rows = list(csv.DictReader((tmp_path / "c.csv").open()))
    assert [r["deezer_id"] for r in rows] == ["4", "1"]
    assert rows[0]["spotify_id"] == "sp4" and rows[0]["top10_rank_sum"] == "4010"
    assert rows[1]["country_share"] == "0.75" and rows[1]["latest"] == "2026-04-01"
