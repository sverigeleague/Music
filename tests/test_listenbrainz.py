from src.collectors import listenbrainz as lb

# Shapes as returned by api.listenbrainz.org on 2026-10-25 (user names replaced).
POPULARITY = [{"artist_mbid": "9a1e8681-e3da-4fa7-aadf-f6a05b567fd5", "total_listen_count": None, "total_user_count": None},
              {"artist_mbid": "22623346-988f-46ac-8d5f-c6bd9c723329", "total_listen_count": 5439, "total_user_count": 717}]
LISTENERS = {"payload": {"artist_mbid": "9fff2f8a-21e6-47de-a2b8-7f449929d43f", "artist_name": "Drake",
                         "from_ts": 1788220800, "to_ts": 1790812800, "last_updated": 1792921698, "range": "month",
                         "listeners": [{"listen_count": 675, "user_name": "someone"}],
                         "total_listen_count": 44743, "total_user_count": 3497}}


def test_parse_popularity_keeps_unknown_as_none():
    p = lb.parse_popularity(POPULARITY)
    assert p == {"9a1e8681-e3da-4fa7-aadf-f6a05b567fd5": None, "22623346-988f-46ac-8d5f-c6bd9c723329": (717, 5439)}


def test_parse_listeners_window_and_counts():
    assert lb.parse_listeners(LISTENERS["payload"]) == {"users_month": 3497, "listens_month": 44743,
                                                        "from": "2026-09-01", "to": "2026-10-01"}


def test_strip_users_drops_names_only():
    s = lb.strip_users(LISTENERS)
    assert "listeners" not in s["payload"] and s["payload"]["total_user_count"] == 3497
    assert "listeners" in LISTENERS["payload"]  # the original is untouched


def test_last_month():
    assert lb.last_month("2026-10") == "2026-09" and lb.last_month("2027-01") == "2026-12"


def test_load_history(tmp_path, monkeypatch):
    p = tmp_path / "lb.csv"
    p.write_text(",".join(lb.FIELDS) + "\n"
                 "2026-09,x,m,10,100,4,40,2026-09-01,2026-10-01,2026-10-25\n"
                 "2026-10,x,m,12,130,6,60,2026-10-01,2026-11-01,2026-11-02\n"
                 ",y,m2,,,,,,,2026-10-25\n")
    monkeypatch.setattr(lb, "CSV", p)
    d = lb.load()
    assert d["x"]["users_month"] == 6 and d["x"]["history"] == [("2026-09", 4), ("2026-10", 6)]
    assert d["y"]["users_all"] is None and d["y"]["history"] == []
