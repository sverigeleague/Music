"""Scout by country (2026-10-26): the country fill (src/origin.py) and the per-country top 100 (site_build)."""
from src import origin, run, site_build
from src.collectors import musicbrainz


def test_pick_follows_the_registry_rule():
    assert origin.pick({"Canada"}, set()) == "Canada"
    assert origin.pick({"Canada", "United States"}, {"Canada"}) == "Canada"  # birth country breaks the tie
    assert origin.pick({"Canada", "United States"}, set()) == "Canada / United States"
    assert origin.pick({"Kingdom of the Netherlands"}, set()) == "Netherlands"
    assert origin.name_of("SE") == "Sweden" and origin.name_of("XW") == ""


def test_area_walks_up_to_the_country():
    cache = {"city": {"name": "Malmö", "type": "City", "code": "", "parent": "mun"},
             "mun": {"name": "Malmö Municipality", "type": "Municipality", "code": "", "parent": "skane"},
             "skane": {"name": "Skåne", "type": "Subdivision", "code": "SE", "parent": "se"}}
    assert origin.area_country("city", cache) == "SE"
    assert origin.musicbrainz_country("x", "CA", cache) == ("Canada", "MusicBrainz: artist country")


def test_fill_wikidata_first_conflicts_to_review(tmp_path, monkeypatch):
    monkeypatch.setattr(origin, "CSV", tmp_path / "o.csv")
    monkeypatch.setattr(origin, "AREAS", tmp_path / "a.json")
    monkeypatch.setattr(origin, "REVIEW_CSV", tmp_path / "r.csv")
    monkeypatch.setattr(origin, "wikidata_by_qid", lambda q: {"Q1": ("Sweden", "Wikidata"), "Q3": ("France", "Wikidata")})
    monkeypatch.setattr(musicbrainz, "load", lambda: {"b": {"country": "NO"}, "c": {"country": "BE"}})
    arts = {"a": {"spotify_id": "a", "name": "A", "genre": "hip_hop", "country": "", "wikidata_id": "Q1", "musicbrainz_id": ""},
            "b": {"spotify_id": "b", "name": "B", "genre": "hip_hop", "country": "", "wikidata_id": "", "musicbrainz_id": "m"},
            "c": {"spotify_id": "c", "name": "C", "genre": "hip_hop", "country": "", "wikidata_id": "Q3", "musicbrainz_id": "m"},
            "d": {"spotify_id": "d", "name": "D", "genre": "other", "country": "", "wikidata_id": "Q1", "musicbrainz_id": ""},
            "e": {"spotify_id": "e", "name": "E", "genre": "hip_hop", "country": "Japan", "wikidata_id": "Q1", "musicbrainz_id": ""}}
    n = origin.fill(arts)
    assert n == {"wikidata": 1, "musicbrainz": 1, "none": 0, "conflict": 1}
    got = origin.load()
    assert got["a"]["country"] == "Sweden" and got["a"]["source"] == "wikidata"
    assert got["b"]["country"] == "Norway" and got["b"]["source"] == "musicbrainz"
    assert got["c"]["country"] == "" and "disagree" in got["c"]["basis"]  # France vs Belgium: left blank, in review
    assert "d" not in got and "e" not in got  # other genres, and countries already known, are not asked
    assert (tmp_path / "r.csv").read_text().count("\n") == 2
    assert origin.apply(arts) == 2 and arts["a"]["country"] == "Sweden" and arts["e"]["country"] == "Japan"


def _row(i, cc, ml, fresh, cur):
    return {"id": f"id{i}", "name": f"A{i}", "cc": cc, "country": " / ".join(cc), "ml": ml, "daily": ml // 10,
            "chg_pct": 0.1 * (i % 7), "fresh_share": fresh, "cur_share": cur, "growth90": None, "attention": None,
            "geo": None, "apple": None, "floor": None, "label_status": "unknown"}


def test_country_top_100_and_whole_set_percentiles(monkeypatch):
    monkeypatch.setattr(origin, "load", lambda: {"sx": {"country": "Sweden", "source": "musicbrainz"}})
    monkeypatch.setattr(site_build, "TOP_N", 100)  # rows past it have no artist page
    rows = [_row(i, ["us"], 2_000_000 + i, (i % 50) / 50, (i % 30) / 30) for i in range(150)]
    rows += [_row(150 + i, ["se"], 1_000_000 + i, 0.9, 0.9) for i in range(5)]
    rows += [_row(3, ["se"], 900_000, 0.5, 0.5) | {"id": "sx", "country": "Sweden"}]
    rows += [_row(200, ["ca", "us"], 600_000, 0.2, 0.2), _row(201, [], 700_000, 0.1, 0.1)]
    rows += [{**_row(202, ["se"], 650_000, None, None), "daily": None, "chg_pct": None}]  # too few signals
    before = [dict(r) for r in rows]
    out = site_build.scout_by_country(rows, {k: v for k, v in site_build.insights.FACTORS.items()})
    assert rows == before  # copies: the top 1,000's own rows are not touched
    c = {x["cc"]: x for x in out["countries"]}
    assert [x["cc"] for x in out["countries"]][:2] == ["us", "se"]  # biggest first
    assert c["us"]["scored"] == 151 and len(c["us"]["rows"]) == 100  # the dual-country artist counts in both
    assert c["se"]["listed"] == 7 and c["se"]["scored"] == 6 and len(c["se"]["rows"]) == 6
    assert c["ca"]["scored"] == 1 and out["no_country"] == 1
    scores = [r["scout"]["score"] for r in c["us"]["rows"]]
    assert scores == sorted(scores, reverse=True)
    se = {r["id"]: r for r in c["se"]["rows"]}
    assert se["sx"]["csrc"] == "musicbrainz" and se["id150"]["csrc"] == "wikidata"
    assert se["id150"]["page"] is False and any(r["page"] for r in c["us"]["rows"])


def test_features_led_hold_back(monkeypatch, tmp_path):
    songs = [{"feature": False, "daily": 10}] * 3 + [{"feature": True, "daily": 100}] * 4
    monkeypatch.setattr(run.current, "pages", lambda s: [("2026-10-26", "p")])
    monkeypatch.setattr(run.current, "songs", lambda p: songs)
    assert run.features_led("x").startswith("held back") and "3 lead songs of 7" in run.features_led("x")
    monkeypatch.setattr(run.current, "songs", lambda p: [{"feature": False, "daily": 100}] * 3 + [{"feature": True, "daily": 50}] * 4)
    assert run.features_led("x") == ""  # most daily streams on the artist's own songs


def test_depth_hold_mb_tag_only_and_top_1000_entry():
    r = {"genre": "hip_hop"}
    thin = {"genres": "hip hop:2|pop:2"}
    assert "MusicBrainz's tags only" in run.depth_hold(r, "MusicBrainz hip-hop tag, country AU", thin, None, 900_000, 1_700_000)
    strong = {"genres": "hip hop:8"}
    dz_pop = {"match": "exact", "rap_share": "0.1"}
    assert "Deezer files 10%" in run.depth_hold(r, "MusicBrainz hip-hop tag, country GB", strong, dz_pop, 900_000, 1_700_000)
    assert run.depth_hold(r, "MusicBrainz hip-hop tag, country US", strong, None, 900_000, 1_700_000) == ""
    # found by the registry's own rule (Deezer): only the top-1,000 check applies
    assert run.depth_hold(r, "Deezer: most releases Rap/Hip Hop", thin, None, 900_000, 1_700_000) == ""
    assert "top 1,000" in run.depth_hold(r, "Deezer: most releases Rap/Hip Hop", thin, None, 2_000_000, 1_700_000)
    assert run.depth_hold({"genre": "review"}, "MusicBrainz hip-hop tag, country US", thin, None, 2_000_000, 1) == ""
