"""Smaller acts (2026-10-26): the triangulated size estimate, its hold-out check, and the Deezer reads."""
import math
import random
from datetime import date

from src import small_acts
from src.collectors import small_acts as col


def _cal(n=300, seed=1):
    """Synthetic calibration rows: two countries; Deezer fans 30x higher per listener in FR than in SE."""
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        c = "France" if i % 2 else "Sweden"
        y = rnd.uniform(5.7, 7.5)
        x = {"fans": y - (1.5 if c == "France" else 3.0) + rnd.gauss(0, 0.2), "wiki": 0.8 * y - 1 + rnd.gauss(0, 0.4)}
        if i % 3 == 0:
            x["lb"] = rnd.uniform(0, 4)  # unrelated to listeners
        out.append({"id": str(i), "name": str(i), "country": c, "y": y, "x": x})
    return out


def test_fit_learns_the_country_offset_and_drops_a_flat_source():
    m = small_acts.fit(_cal())
    assert set(m) >= {"fans", "wiki"} and "lb" not in m  # a source that does not move with listeners is left out
    assert abs(m["fans"]["d"] - 1) < 0.1
    assert abs((m["fans"]["c"]["Sweden"] - m["fans"]["c"]["France"]) + 1.5) < 0.2  # Sweden: fewer fans per listener


def test_estimate_combines_and_flags_disagreement():
    m = small_acts.fit(_cal())
    e = small_acts.estimate({"fans": 3.0, "wiki": 0.8 * 6.0 - 1}, "Sweden", m)
    assert abs(e["y"] - 6.0) < 0.2 and e["n"] == 2 and e["agree"] == 2 and not e["disagree"]
    far = small_acts.estimate({"fans": 3.0, "wiki": 0.8 * 8.5 - 1}, "Sweden", m)
    assert far["disagree"] and far["spread"] > 1 and far["agree"] == 0  # neither within 3x of the combined estimate
    assert small_acts.estimate({}, "Sweden", m) is None
    # an unknown country uses the pooled term
    assert small_acts.estimate({"fans": 3.0}, "Norway", m)["y"] is not None


def test_no_source_above_half_the_weight():
    m = {"a": {"d": 1, "c": {}, "c0": 0, "err": 0.01}, "b": {"d": 1, "c": {}, "c0": 0, "err": 1}}
    e = small_acts.estimate({"a": 5.0, "b": 6.0}, "X", m)
    assert 5.0 < e["y"] < 6.0 and abs(e["y"] - 5.5) < 0.01  # capped at half: the two count equally here


def test_validate_reports_per_country_rank_correlation():
    v = small_acts.validate(_cal(400))
    assert v["all"]["rho"] > 0.8 and v["countries"]["Sweden"]["rho"] > 0.8
    assert v["countries"]["France"]["fans"]["rho"] > 0.8
    assert v["calibration"] == 400


def test_spearman_handles_ties():
    assert small_acts.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert small_acts.spearman([1, 1, 2], [1, 2, 3]) > 0.8
    assert small_acts.spearman([1, 2], [1, 2]) is None


def test_values_leave_out_missing_and_zero():
    v = small_acts.values({"fans": "1000", "rank_sum": "0", "wiki_3m": "", "lb_users": "10", "spotify_id": "s"}, {"s": "500"})
    assert v == {"fans": 3.0, "lb": 1.0, "yt": math.log10(500)}


def test_deezer_read_counts_fresh_top_tracks(monkeypatch):
    pages = {"artist/1": {"name": "A", "nb_fan": 1200},
             "artist/1/albums": {"data": [{"id": 10, "genre_id": 116, "release_date": "2026-10-01"},
                                          {"id": 11, "genre_id": 116, "release_date": "2024-01-01"},
                                          {"id": 12, "genre_id": 132, "release_date": "2023-01-01"}]},
             "artist/1/top": {"data": [{"title": "New", "rank": 500, "album": {"id": 10}},
                                       {"title": "Old", "rank": 300, "album": {"id": 11}},
                                       {"title": "Guest", "rank": 100, "album": {"id": 99}}]}}
    monkeypatch.setattr(col, "_json", lambda path, **p: pages.get(path, {}))
    r = col.deezer_read("1", date(2026, 10, 26))
    assert r["fans"] == 1200 and r["releases"] == 3 and r["rap_share"] == 0.667
    assert r["rank_sum"] == 900 and r["fresh_n"] == 1 and r["dated_n"] == 2 and r["fresh_title"] == "New"
    assert r["latest"] == "2026-10-01"


def test_fan_growth_needs_a_week(tmp_path, monkeypatch):
    p = tmp_path / "f.csv"
    p.write_text("date,deezer_id,fans\n2026-10-19,1,100\n2026-10-26,1,150\n2026-10-25,2,10\n2026-10-26,2,20\n")
    monkeypatch.setattr(col, "FANS", p)
    assert col.fan_growth() == {"1": 0.5}


def test_add_smaller_fills_to_100_and_respects_the_check(monkeypatch):
    from src import site_build
    from src.collectors import small_acts as col2
    row = lambda q, c, score, dis=False: {"qid": q, "name": q, "country": c, "sp": None, "dz": "1", "score": score,
                                         "sources": 2, "agree": 2, "disagree": dis, "size_pct": 50, "fans": 10,
                                         "wiki": None, "fresh": None, "fresh_title": None, "charts": None,
                                         "latest": "2026-01-01", "growth": None, "used": ["fans", "rank"]}
    rows = [row("Q1", "Sweden", 40), row("Q2", "Sweden", 90, dis=True), row("Q3", "Sweden", 60),
            row("Q4", "Belgium", 70), row("Q5", "Norway", 50)]
    val = {"all": {"n": 100, "rho": 0.7, "miss": 1.7, **{s: {"n": 1, "rho": None} for s in small_acts.SIGNALS}},
           "countries": {"Sweden": {"n": 15, "rho": 0.7, **{s: {"n": 1, "rho": None} for s in small_acts.SIGNALS}},
                         "Belgium": {"n": 11, "rho": 0.3, **{s: {"n": 1, "rho": None} for s in small_acts.SIGNALS}}},
           "calibration": 100}
    monkeypatch.setattr(small_acts, "rank", lambda g: {"validation": val, "rows": rows, "model": {}, "growth_ready": False, "yt_ready": False})
    monkeypatch.setattr(col2, "load", lambda: [{"genre": "hip_hop", "decision": "include", "country": r["country"]} for r in rows])
    by = {"countries": [{"cc": "se", "name": "Sweden", "listed": 99, "scored": 98, "rows": []},
                        {"cc": "be", "name": "Belgium", "listed": 11, "scored": 11, "rows": []}]}
    site_build.add_smaller(by, "hip_hop")
    c = {x["cc"]: x for x in by["countries"]}
    assert [r["name"] for r in c["se"]["small"]["rows"]] == ["Q3", "Q1"]  # room for 2; the flagged one ranks last
    assert c["be"]["small"]["status"] == "weak" and c["be"]["small"]["rows"] == []  # tested and too weak: not listed
    assert c["no"]["small"]["status"] == "pooled" and c["no"]["scored"] == 0  # a country with only smaller acts
    assert by["small"]["rho"] == 0.7
