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
    # 2026-10-27: a weak check no longer withholds the list; the page carries the warning (status "weak")
    assert c["be"]["small"]["status"] == "weak" and [r["name"] for r in c["be"]["small"]["rows"]] == ["Q4"]
    assert c["no"]["small"]["status"] == "pooled" and c["no"]["scored"] == 0  # a country with only smaller acts
    assert by["small"]["rho"] == 0.7


def test_add_smaller_keeps_unranked_and_marks_old_and_single(monkeypatch):
    from src import site_build
    from src.collectors import small_acts as col2
    base = {"sp": None, "dz": "1", "sources": 1, "agree": 1, "disagree": False, "size_pct": 50, "fans": 10, "wiki": None,
            "fresh": None, "fresh_title": None, "latest": "2019-01-01", "growth": None, "used": ["fans"], "csrc": "",
            "via": "", "old": True, "single": True,
            "charts": {"spotify": 40, "national": {"chart": "singles", "name": "Suomen virallinen lista singles", "peak": 3,
                                                   "weeks": 5, "size": 50, "show": False}}}
    rows = [{**base, "qid": "Q1", "name": "Old", "country": "Finland", "score": 55},
            {**base, "qid": "mb:x", "name": "Unsized", "country": "Finland", "score": None, "size_pct": None,
             "sources": 0, "agree": 0, "single": False, "old": False, "charts": None}]
    val = {"all": {"n": 100, "rho": 0.7, "miss": 1.7, **{s: {"n": 1, "rho": None} for s in small_acts.SIGNALS}},
           "countries": {}, "calibration": 100}
    monkeypatch.setattr(small_acts, "rank", lambda g: {"validation": val, "rows": rows, "model": {}, "growth_ready": False, "yt_ready": False})
    monkeypatch.setattr(col2, "load", lambda: [{"genre": "hip_hop", "decision": "include", "country": "Finland"}] * 2)
    by = {"countries": []}
    site_build.add_smaller(by, "hip_hop")
    fi = by["countries"][0]["small"]
    assert [r["name"] for r in fi["rows"]] == ["Old", "Unsized"] and fi["unranked"] == 1 and fi["scored"] == 1
    old = fi["rows"][0]
    assert old["old"] and old["single"] and old["year"] == "2019"
    assert old["charts"] == {"spotify": 40}  # the Finnish list's rules: its position is never shown
    assert "size" not in fi["rows"][1] and "score" not in fi["rows"][1]


# ---------- 2026-10-27: the owner's smaller-acts genre rule, the national charts, wider discovery
def test_decide_small_takes_wikidata_genre_or_rapper_without_votes():
    from src import genre
    hh = [("hip-hop", True, False), ("trap", True, False)]
    assert genre.decide([], hh, None)[0] == "review"  # the registry's rule still asks for votes
    assert genre.decide_small([], hh, None, country="Sweden")[0] == "hip_hop"
    assert genre.decide_small([], [], None, country="Norway", rapper=True)[0] == "hip_hop"
    assert genre.decide_small([], [("pop", False, False)], None, country="Norway")[0] == "review"  # no evidence


def test_decide_small_catches_latin_singers_called_rappers():
    from src import genre
    dz = {"match": "links", "releases": 8, "rap_share": "0.5", "latin_share": "0.375", "top_latin": "0.6", "top_dated": 5}
    assert genre.decide_small([], [], dz, country="United States", rapper=True)[0] == "review"
    assert genre.decide_small([], [("reggaeton", False, True), ("hip-hop", True, False), ("rap", True, False)], None,
                              country="Sweden")[0] == "review"  # any Latin genre on Wikidata
    # Spanish-speaking: the songs must settle it
    clean = {"match": "links", "releases": 2, "rap_share": "1", "latin_share": "0", "top_latin": "0", "top_dated": 4}
    assert genre.decide_small([], [], clean, country="Spain", rapper=True)[0] == "hip_hop"
    assert genre.decide_small([], [], None, country="Spain", rapper=True)[0] == "review"
    # Deezer filing most releases as Latin still decides first
    latin = {"match": "links", "releases": 9, "rap_share": "0.4", "latin_share": "0.6"}
    assert genre.decide_small([], [], latin, country="Chile", rapper=True)[0] == "latin"


def test_decide_country_small_takes_a_wikidata_country_genre():
    from src import genre
    wd = [("country music", False, False), ("americana", False, False)]
    assert genre.decide_country([], wd)[0] == "review"
    assert genre.decide_country([], wd, small=True)[0] == "country"
    dz = {"match": "links", "releases": 6, "country_share": "0.1"}
    assert genre.decide_country([], wd, dz, small=True)[0] == "review"  # Deezer's releases say otherwise


SE_PAGE = """<ol class="charts-list"><li class="charts-list__item first" data-liid="41"><article><h2 class="title">
<span class="title-inner">SONG A</span></h2><p class="artist uk-hidden-visually">YASIN &#38; DREE LOW</p></article></li>
<li class="charts-list__item " data-liid="41"><article><h2 class="title">SONG B</h2><p class="artist">Z.E</p></article></li></ol>"""
DK_PAGE = """<div id="linien"><div id="datal"><div id="denneugeny">1</div><div id="ugerialt" title="Uger i alt">
<div id="listeikon">4</div>3</div><div id="peak" title="H"><div id="listeikon">5</div>1</div></div>
<div id="artistnavn">\n NOAH CARTER</div><div id="titel">\n NOAHS ARK II</div></div>"""
FI_PAGE = """<div class="chart-row"><strong class="chart-position">2.</strong><div class="chart-artist"><a>VIIVI</a>, <a>Elastinen</a></div>
<div class="chart-title"><a>Sydän (feat. Elastinen)</a></div><div class="chart-woc" aria-label="x">3</div></div>"""


def test_national_chart_parsers():
    from src.collectors import national_charts as nc
    se = nc.parse("se", SE_PAGE)
    assert [(r["position"], r["artist"], r["title"]) for r in se] == [(1, "YASIN & DREE LOW", "SONG A"), (2, "Z.E", "SONG B")]
    assert nc.parse("dk", DK_PAGE) == [{"position": 1, "artist": "NOAH CARTER", "title": "NOAHS ARK II", "weeks": 3, "peak": 1}]
    fi = nc.parse("fi", FI_PAGE)[0]
    assert fi["position"] == 2 and fi["artist"] == "VIIVI , Elastinen" and fi["weeks"] == 3
    assert nc.parse("se", "<html>no list yet</html>") == []
    assert nc.names("YASIN & DREE LOW") == ["YASIN & DREE LOW", "YASIN", "DREE LOW"]
    assert nc.names("A FEAT. B") == ["A FEAT. B", "A", "B"]


def test_national_runs_count_peak_and_weeks_over_the_last_year():
    from src.collectors import national_charts as nc
    rows = [{"country": "se", "chart": "singles", "year": 2026, "week": w, "position": p, "artist": "Yasin & Dree Low", "title": "x"}
            for w, p in ((40, 30), (41, 12), (42, 50))] + \
           [{"country": "se", "chart": "singles", "year": 2024, "week": 1, "position": 1, "artist": "Yasin", "title": "old"}]
    r = nc.runs(rows, date(2026, 10, 27))
    assert r[("se", "singles", "yasin")] == {"peak": 12, "weeks": 3, "last": (2026, 42), "size": 100}
    assert ("se", "singles", "dreelow") in r


def test_chart_points_reward_peak_and_weeks():
    assert small_acts.chart_points(None) == 0
    assert small_acts.chart_points({"spotify": 3, "shazam": 9}) == 2
    top = small_acts.chart_points({"national": {"peak": 1, "weeks": 52, "size": 100}})
    low = small_acts.chart_points({"national": {"peak": 100, "weeks": 1, "size": 100}})
    assert top == 3 and 1 < low < 1.1


def test_identify_needs_title_and_a_credited_name(tmp_path, monkeypatch):
    monkeypatch.setattr(col, "IDS", tmp_path / "ids.csv")
    pages = {"search": {"data": [{"id": 5, "title": "Other", "title_short": "Other", "artist": {"id": 1, "name": "Yasin"}},
                                 {"id": 6, "title": "Song A (feat. Dree Low)", "title_short": "Song A", "artist": {"id": 1, "name": "Yasin"}}]},
             "track/6": {"contributors": [{"id": 1, "name": "Yasin"}, {"id": 2, "name": "Dree Low"}, {"id": 3, "name": "Producer"}]}}
    monkeypatch.setattr(col, "_json", lambda path, **p: pages.get(path, {}))
    got = col.identify([("track", "YASIN & DREE LOW", "SONG A"), ("track", "NOBODY", "SONG A")])
    assert got[("track", "YASIN & DREE LOW", "SONG A")] == ["1", "2"]  # the producer is not credited on the chart
    assert got[("track", "NOBODY", "SONG A")] == []
    assert len(col._read(col.IDS)) == 2  # both cached, the miss too


def test_wide_finds_need_some_genre_evidence():
    assert not col._evidence("hip_hop", [], [], {"rap_share": "0.1"}, False)
    assert col._evidence("hip_hop", [], [("trap", 2)], {}, False)
    assert col._evidence("hip_hop", [], [], {"rap_share": "0.25"}, False)
    assert col._evidence("country", [("americana", False, False)], [], {}, False)


def test_key_falls_back_to_musicbrainz():
    assert col.key({"qid": "Q1", "mbid": "m"}) == "Q1"
    assert col.key({"qid": "", "mbid": "m"}) == "mb:m"


def test_deezer_read_counts_lead_and_latin_top_songs(monkeypatch):
    pages = {"artist/1": {"name": "A", "nb_fan": 5},
             "artist/1/albums": {"data": [{"id": 10, "genre_id": 197, "release_date": "2026-01-01"},
                                          {"id": 11, "genre_id": 116, "release_date": "2025-01-01"}]},
             "artist/1/top": {"data": [{"title": "a", "rank": 1, "album": {"id": 10}, "artist": {"id": 1}},
                                       {"title": "b", "rank": 1, "album": {"id": 11}, "artist": {"id": 1}},
                                       {"title": "c", "rank": 1, "album": {"id": 99}, "artist": {"id": 7}}]}}
    monkeypatch.setattr(col, "_json", lambda path, **p: pages.get(path, {}))
    r = col.deezer_read("1", date(2026, 10, 26))
    assert r["lead_n"] == 2 and r["top_dated"] == 2 and r["top_latin"] == 0.5


def test_decide_small_holds_beatmakers_and_deezer_contradictions():
    from src import genre
    lofi = [("boom bap", 1), ("lo-fi hip hop", 1), ("hip hop", 1), ("chillwave", 1)]
    assert genre.decide_small(lofi, [], None, country="Austria")[0] == "other"  # 2026-10-27: lo-fi is not hip-hop
    few = {"match": "links", "releases": 17, "rap_share": "0.06", "latin_share": "0", "top_latin": "0", "top_dated": 9}
    assert genre.decide_small([], [("hip-hop", True, False)], few, country="Argentina")[0] == "review"


# ---------- 2026-10-27 (owner): single-source acts rank after the agreeing ones; lo-fi is not hip-hop; the Spain check
def test_add_smaller_orders_agreeing_then_single_then_disagree_then_unranked(monkeypatch):
    from src import site_build
    from src.collectors import small_acts as col2
    base = {"sp": None, "dz": "1", "sources": 3, "agree": 3, "disagree": False, "single": False, "size_pct": 50,
            "fans": 10, "wiki": None, "fresh": None, "fresh_title": None, "charts": None, "latest": "2026-01-01",
            "growth": None, "used": ["fans"], "country": "Spain"}
    rows = [{**base, "qid": "Q1", "name": "Disagree", "score": 95, "disagree": True},
            {**base, "qid": "Q2", "name": "Single", "score": 90, "sources": 1, "agree": 1, "single": True},
            {**base, "qid": "Q3", "name": "Agree low", "score": 30},
            {**base, "qid": "Q4", "name": "Unranked", "score": None, "size_pct": None, "sources": 0, "agree": 0},
            {**base, "qid": "Q5", "name": "Agree high", "score": 60},
            {**base, "qid": "Q6", "name": "Single low", "score": 20, "sources": 1, "agree": 1, "single": True}]
    val = {"all": {"n": 100, "rho": 0.7, "miss": 1.7, **{s: {"n": 1, "rho": None} for s in small_acts.SIGNALS}},
           "countries": {}, "calibration": 100}
    monkeypatch.setattr(small_acts, "rank", lambda g: {"validation": val, "rows": rows, "model": {}, "growth_ready": False, "yt_ready": False})
    monkeypatch.setattr(col2, "load", lambda: [{"genre": "hip_hop", "decision": "include", "country": "Spain"}] * 6)
    by = {"countries": []}
    site_build.add_smaller(by, "hip_hop")
    names = [r["name"] for r in by["countries"][0]["small"]["rows"]]
    assert names == ["Agree high", "Agree low", "Single", "Single low", "Disagree", "Unranked"]
    assert site_build.small_tier({"disagree": False, "single": True}) == 1


def test_lofi_beatmakers_are_other_but_rappers_over_lofi_beats_are_not():
    from src import genre
    label_wide = [("boom bap", 1), ("chillwave", 1), ("downtempo", 1), ("hip hop", 1), ("instrumental", 1),
                  ("instrumental hip hop", 1), ("lo-fi", 1), ("lo-fi hip hop", 1)]
    dz = {"match": "links", "releases": 40, "rap_share": "0.9", "latin_share": "0", "top_latin": "0", "top_dated": 8}
    dec, basis = genre.decide_small(label_wide, [], dz, country="Sweden")
    assert dec == "other" and "no sign of vocal rap" in basis
    assert genre.decide_small([], [("lofi hip-hop", True, False)], dz, country="Japan")[0] == "other"  # Wikidata lo-fi only
    assert genre.decide_small([], [("chillhop", True, False)], None, country="Norway")[0] == "other"
    # a rapper on lo-fi beats: the occupation rapper, or a Wikidata hip-hop genre beside the lo-fi one, keeps them
    assert genre.decide_small(label_wide, [], dz, country="Hungary", rapper=True)[0] == "review"
    assert genre.decide_small(label_wide, [("abstract hip-hop", True, False), ("lo-fi music", False, False)], dz,
                              country="Russia")[0] == "review"
    # untagged acts are untouched, and a Latin decision stays Latin
    assert genre.decide_small([], [("hip-hop", True, False)], dz, country="Sweden")[0] == "hip_hop"
    assert genre.decide_small([("reggaeton", 5), ("lo-fi", 1)], [], None, country="Sweden")[0] == "latin"


def test_hand_decisions_replace_the_rule_and_keep_its_basis():
    hand = {("hip_hop", "Q1"): {"decision": "hip_hop", "reason": "Spanish rapper", "decided": "2026-10-27"},
            ("hip_hop", "mb:x"): {"decision": "latin", "reason": "reggaeton", "decided": "2026-10-27"}}
    dec, basis = col._hand(hand, "hip_hop", "Q1", "review", "Spain: the songs do not settle it")
    assert dec == "hip_hop" and basis.startswith("hand check 2026-10-27: Spanish rapper") and "rule: review" in basis
    assert col._hand(hand, "hip_hop", "mb:x", "review", "b")[0] == "latin"
    assert col._hand(hand, "country", "Q1", "other", "b") == ("other", "b")  # per genre
    assert col._hand(hand, "hip_hop", "Q2", "review", "b") == ("review", "b")


def test_spain_check_overrides_file():
    from src import genre
    o = genre.small_overrides()
    assert len(o) >= 260
    for (g, k), r in o.items():
        assert g == "hip_hop" and (k.startswith("Q") or k.startswith("mb:")), k
        assert r["decision"] in ("hip_hop", "latin", "other", "review") and r["reason"] and r["evidence"] and r["decided"]
    by_name = {r["name"]: r["decision"] for r in o.values()}
    assert by_name["Tote King"] == "hip_hop" and by_name["Los Chikos del Maíz"] == "hip_hop"  # Spanish rap
    assert by_name["Mushkaa"] == "latin" and by_name["Sky Rompiendo"] == "latin"  # urbano / reggaeton
    assert by_name["Boikot"] == "other" and by_name["Resorte"] == "other"  # rock; rap metal
    assert o[("hip_hop", "mb:5c1b9ce3-88f0-40cb-8cb2-fe46dd561981")]["decision"] == "hip_hop"  # Krisy: a rapper the lo-fi tags took
