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


def test_country_chart_row():
    from src.collectors.kworb_countries import parse
    row = ('<tr><td class="np">7</td><td class="np">+1</td><td class="text mp"><div>'
           '<a href="../artist/3TVXtAsR1Inumwj472S9r4.html">Drake</a> - <a href="../track/x.html">Song</a> (w/ '
           '<a href="../artist/2hlmm7s2ICUX0LVIhVFlZQ.html">Gunna</a>)</div></td><td>3</td><td>2</td>'
           '<td class="np mini text"></td><td>1,234,567</td><td>-5</td><td>9,999,999</td></tr>')
    week, d = parse("Week ending 2026/10/15" + row + row.replace(">7<", ">40<", 1))
    assert week == "2026-10-15"
    assert d["3TVXtAsR1Inumwj472S9r4"] == [2469134, 2, 7]       # both rows, best position 7
    assert d["2hlmm7s2ICUX0LVIhVFlZQ"][0] == 2469134             # the featured artist is credited too


def test_youtube_api_parse():
    from src.collectors.youtube_api import parse
    p = parse([{"id": "UC1", "statistics": {"subscriberCount": "1230000", "viewCount": "5", "videoCount": "9"}},
               {"id": "UC2", "statistics": {"hiddenSubscriberCount": True, "viewCount": "7", "videoCount": "1"}}])
    assert p["UC1"] == {"subscribers": 1230000, "views": 5, "videos": 9} and p["UC2"]["subscribers"] is None


def test_label_classification():
    from src.labels import classify_label as c
    assert c("OVO/Republic", "Drake") == ("major", "Universal Music Group")
    assert c("BigXthaPlug under exclusive license to UnitedMasters LLC", "BigXthaPlug")[0] == "self_released"
    assert c("Maybach Music Group under exclusive license to gamma.", "Rick Ross") == ("independent", "gamma.")
    assert c("bbno$$", "bbno$") == ("self_released", "the artist's own name")
    assert c("Canada Dry Music", "x")[0] == "unknown"      # "ada" (ADA) is matched as a word only
    assert c("Volume Records", "x")[0] == "unknown"        # nor "ume" (UME)
    assert c("BBR Music Group/Jelly Roll", "Jelly Roll") == ("independent", "BMG")
    # a longer pattern containing a shorter one wins; separate labels in one string still rank by status
    assert c("Universal Music Distribution Deal", "x")[0] == "major_distributed"
    assert c("10K Projects/Capitol Records", "x")[0] == "major"
    assert c("Universal Music Distribution / Universal Music", "x")[0] == "major"  # a second, separate label


def test_label_status_and_codes():
    from src.labels import artist_status, check_with_isrcs, learn_registrants
    rel = [{"title": "Collab", "release_date": "2026-09-01", "label": "Some Label/Atlantic"},
           {"title": "A", "release_date": "2026-05-01", "label": "Columbia"},
           {"title": "B", "release_date": "2025-11-01", "label": "Columbia"}]
    st = artist_status(rel, "X")
    assert (st["status"], st["owner"]) == ("major", "Sony Music")     # the majority, not the latest collab
    statuses = {f"a{i}": {"status": "major", "owner": "Universal Music Group"} for i in range(3)}
    reg = learn_registrants(statuses, {f"a{i}": ["USUG1"] * 4 for i in range(3)})
    assert reg == {"USUG1": "Universal Music Group"}
    own = {"status": "self_released", "owner": "the artist's own name", "basis": None, "releases": []}
    assert check_with_isrcs(own, ["USUG1", "USUG1", "QZAB1"], reg)["status"] == "major"
    ok = check_with_isrcs(own, ["QZAB1", "QZAB1", "USXX1"], reg)
    assert ok["status"] == "self_released" and ok["confidence"] == "confirmed"
    assert check_with_isrcs(own, [], reg)["confidence"] == "label name only"


def test_genre_with_deezer():
    dz = lambda rap, lat=0.0, n=20, m="exact": {"match": m, "releases": n, "rap_share": rap, "latin_share": lat}
    assert genre.decide([], [], dz(0.98))[0] == "hip_hop"                      # thin votes: Deezer decides
    assert genre.decide([], [], dz(0.98), wikidata=False)[0] == "review"      # not on a name-only match
    assert genre.decide([], [], dz(0.82), country="Colombia")[0] == "latin"   # Latin urbano filed as rap
    assert genre.decide([], [], dz(0.65))[0] == "review"
    assert genre.decide([], [], dz(0.25, 0.67))[0] == "latin"
    assert genre.decide([], [], dz(0.16))[0] == "other"
    assert genre.decide([], [], dz(0.98, m="ambiguous"))[0] == "review"       # never on an ambiguous match
    assert genre.decide([], [], dz(0.98, n=3))[0] == "review"                 # nor on fewer than 5 releases
    border = [("hip hop", 8), ("pop", 6), ("electronic", 4), ("pop rap", 4), ("dance", 4)]
    assert genre.decide(border, [], dz(0.8))[0] == "hip_hop"                  # settles MusicBrainz's review zone
    assert genre.decide(border, [], dz(0.2))[0] == "other"


# ---------- Phase 7: scout, worth, levels, Apple charts, Wayback history

def test_scout_ranks_within_size_band_and_tiers():
    from src import insights
    rows = []
    for i in range(10):  # ten small artists: the last has the strongest signals
        rows.append({"id": f"s{i}", "ml": 1_000_000, "fresh_share": i / 10, "cur_share": i / 10, "daily": 100_000 + i,
                     "chg_pct": i / 100, "geo": None, "attention": None})
    rows.append({"id": "big", "ml": 50_000_000, "fresh_share": 0.9, "cur_share": 0.9, "daily": 1, "chg_pct": 1,
                 "geo": None, "attention": None})
    insights.scout(rows)
    top = rows[9]["scout"]
    assert top["score"] > rows[0]["scout"]["score"] and top["tier"] == "Breaking"
    assert rows[10]["scout"] is None  # alone in its band: no percentile, no score


def test_breaking_needs_an_absolute_signal_and_big_artists_get_no_tier():
    from src import insights
    rows = [{"id": f"s{i}", "ml": 1_000_000, "fresh_share": i / 100, "cur_share": i / 10, "daily": 1000 * i,
             "chg_pct": i, "geo": None, "attention": None} for i in range(10)]
    insights.scout(rows)
    assert rows[9]["scout"]["score"] >= 80 and rows[9]["scout"]["tier"] == "Rising"  # new songs only 9% of streams
    big = [{"id": f"b{i}", "ml": 20_000_000, "fresh_share": i / 10, "cur_share": i / 10, "daily": i, "chg_pct": i,
            "geo": None, "attention": None} for i in range(5)]
    insights.scout(big)
    assert all(r["scout"]["tier"] is None for r in big)


def test_growth_uses_the_snapshot_nearest_90_days():
    from src import insights
    h = [("2026-07-20", 1_000_000), ("2026-08-30", 1_200_000), ("2026-10-23", 1_500_000)]
    assert abs(insights.growth(h, "2026-10-23") - 1.5) < 1e-9
    assert insights.growth([("2026-10-01", 1), ("2026-10-23", 2)], "2026-10-23") is None  # nothing near 90 days


def test_worth_multiple_follows_how_new_the_music_is():
    from src import insights
    table = insights.multiples()
    assert insights.vintage(0.8, table)["vintage"] == "new"
    assert insights.vintage(0.1, table)["vintage"] == "evergreen"
    assert insights.vintage(None, table)["vintage"] == "mixed"
    rev = {"lines": [{"group": "Streaming", "generated": {"low": 100, "mid": 200, "high": 300},
                      "artist": {"low": 10, "mid": 20, "high": 30}},
                     {"group": "Publishing", "generated": {"low": 20, "mid": 50, "high": 75}}]}
    w = insights.worth({"cur_share": 0.8}, rev, table)
    assert w["recordings"]["low"] == 100 * 5 and w["recordings"]["high"] == 300 * 10 and w["publishing"]["mid"] == 50 * 7.5


def test_apple_names_split_and_fold():
    from src.collectors import apple_charts as a
    assert a.split_names("KAROL G, Judeline & rusowsky") == ["KAROL G, Judeline & rusowsky", "KAROL G", "Judeline", "rusowsky"]
    assert a.split_names("Drake") == ["Drake"]
    assert a.fold("Beyoncé") == a.fold("BEYONCE") and a.fold("bbno$") == "bbno$"


def test_wayback_parser_reads_old_and_new_link_formats():
    from src.collectors import wayback
    html = ('<tr><td>1</td><td class="text"><div><a href="artist/0du5cEVh5yTK9QJze8zA0C_songs.html">Bruno Mars</a></div></td>'
            '<td>128,438,090</td><td>-134,036</td></tr>'
            '<tr><td>2</td><td><a href="artist/5pKCCKE2ajJHZ9KAiaK11H.html">X</a></td><td>99,000</td></tr>')
    rows = wayback.parse(html)
    assert rows == [{"spotify_id": "0du5cEVh5yTK9QJze8zA0C", "monthly_listeners": 128438090, "rank": 1},
                    {"spotify_id": "5pKCCKE2ajJHZ9KAiaK11H", "monthly_listeners": 99000, "rank": 2}]


def test_feature_guests_from_titles_and_network_both_ways():
    from src import insights
    from src.collectors.apple_charts import fold
    assert insights.guests("Knife Talk (with 21 Savage ft. Project Pat)") == ["21 Savage", "Project Pat"]
    assert insights.guests("Rich Baby Daddy (feat. Sexyy Red & SZA)") == ["Sexyy Red", "SZA"]
    assert insights.guests("With You") == [] and insights.guests("HYFR (Hell Ya Fucking Right)") == []
    songs = {"d": [{"title": "Jimmy Cooks (feat. 21 Savage)", "daily": 900, "feature": False},
                   {"title": "MIA (feat. Drake)", "daily": 500, "feature": True}]}
    net = insights.collabs(songs, {"d": "Drake", "s": "21 Savage"}, fold)
    assert net["d"][0]["id"] == "s" and net["s"][0]["id"] == "d" and net["s"][0]["daily"] == 900


def test_musicbrainz_label_parts_and_owner_chain(monkeypatch):
    from src import labels
    from src.collectors import musicbrainz_labels as mbl
    assert mbl.parts("Lutèce Music / Mirage Records Music / AllPoints") == ["Lutèce Music", "Mirage Records Music", "AllPoints"]
    assert mbl.parts("Eardrummer Entertainment LLC, under exclusive license to Giant Music") == ["Eardrummer Entertainment", "Giant Music"]
    table = [{"pattern": "universal music", "owner": "Universal Music Group", "status": "major"}]
    monkeypatch.setattr(labels, "_MB", {"Urban": {"chain": ["Motor Music GmbH", "Universal Music GmbH"], "distributors": []}})
    assert labels.classify_label("Urban", "Someone", table) == ("major", "Universal Music Group")
    assert labels.classify_label("Urban", "Someone", table, use_musicbrainz=False) == ("unknown", "")


def test_provisional_rank_between_half_and_eighty_percent_dated():
    from datetime import date
    from src import current
    rows = [{"track_id": "a", "title": "A", "daily": 60, "feature": False},
            {"track_id": "b", "title": "B", "daily": 40, "feature": False}]
    dates = {"a": {"first_release": "2026-09-01"}}  # 60% of streams dated, all new
    s = current.score(rows, dates, date(2026, 10, 24))
    assert not s["ok"] and s["provisional"] and s["share_range"] == (0.6, 1.0)
    s = current.score(rows, {}, date(2026, 10, 24))
    assert not s["provisional"]


def test_label_display_names_follow_the_licensee():
    from src import labels
    assert labels.label_name("OVO/Republic") == "Republic Records"
    assert labels.label_name("X LLC, under exclusive license to Atlantic Recording Corporation") == "Atlantic Records"
    assert labels.label_name("Death Note Music, LLC") == "Death Note Music"


def test_report_pdf_checks_and_rows():
    from src.extract import report_pdf as r
    read = {"currency": "EUR", "unit_multiplier": 1000000,
            "columns": [{"column": 1, "statement": "IS", "period_end": "2026-06-30", "months": 6},
                        {"column": 2, "statement": "BS", "period_end": "2026-06-30", "months": 0}],
            "lines": [{"item": "revenue", "label": "Revenue", "column": 1, "value": 6000, "page": 3},
                      {"item": "net_income", "label": "Profit", "column": 1, "value": 800, "page": 3},
                      {"item": "total_assets", "label": "Total assets", "column": 2, "value": 100, "page": 4},
                      {"item": "total_liabilities", "label": "Total liabilities", "column": 2, "value": 70, "page": 4},
                      {"item": "equity", "label": "Equity", "column": 2, "value": 30, "page": 4},
                      {"item": "capex", "label": "Capex", "column": 1, "value": -5, "page": 5}],
            "absent": [{"item": "cfo", "reason": "no cash flow statement in a trading update"}]}
    fails = r.checks(read)
    assert fails == ["column 1: capex should be a positive amount"]
    rows = r.rows_of({"company": "UMG", "period_type": "H", "url": "https://x"}, {"read": read, "model": "m"})
    rev = next(x for x in rows if x["item"] == "revenue")
    assert rev["period_type"] == "H" and rev["value"] == 6000 * 1000000
    assert next(x for x in rows if x["item"] == "total_assets")["period_type"] == "Q"


def test_health_ratios():
    from src import health
    p = {"revenue": 1000, "operating_income": 150, "da": 50, "net_income": 100, "cash": 100, "long_term_debt": 500,
         "short_term_debt": 0, "cfo": 200, "capex": 20, "current_assets": 400, "current_liabilities": 500,
         "equity": 300, "total_assets": 1000, "interest_expense": 25}
    r = health._ratios(p, {"revenue": 800})
    assert r["revenue_growth"] == 0.25 and r["net_debt"] == 400 and r["leverage"] == 2.0 and r["fcf"] == 180
    assert health._reading("leverage", 2.0) == "good" and health._reading("current_ratio", 0.8) == "watch"


def test_report_pdf_locates_interim_statement_headings():
    from src.extract import report_pdf as r
    filler = "Our strategy and our people. " * 40
    nums = " ".join(f"{i},{i:03d}" for i in range(100, 130))
    pages = [filler,
             # UMG's half-year layout: few thousands separators on the statement pages
             "Condensed Consolidated Interim Statements of Profit or Loss Six months ended June 30 Revenues 6,194 5,881 "
             "Cost of revenues (3,622) (3,341) Operating profit 1,021 947 Net income 812 701 Total 2,410 1,977",
             filler,
             "Condensed Consolidated Interim Statements of Financial Position " + nums,
             "Notes to the Condensed Consolidated Interim Financial Statements " + nums,
             "Main aggregates of the Statement of profit or loss " + nums]
    assert r.locate(pages) == [1, 3]


def test_report_html_tables_become_pages():
    from src.extract import report_pdf as r
    nums = "".join(f"<tr><td>Line {i}</td><td>{i},{i:03d}</td><td>{i},{i + 1:03d}</td></tr>" for i in range(100, 115))
    html = (f"<html><body><p>Overview of the quarter</p><p>Condensed Quarterly Consolidated Statements of Income</p>"
            f"<table>{nums}</table><p>Notes to the Condensed Consolidated Financial Statements</p><table>{nums}</table>"
            f"</body></html>").encode()
    pages = r.html_pages(html)
    assert len(pages) == 2 and r.locate(pages) == [0]


def test_report_check_catches_a_wrong_unit():
    from src.extract import report_pdf as r
    read = {"currency": "EUR", "unit_multiplier": 1,
            "columns": [{"column": 1, "statement": "BS", "period_end": "2025-12-31", "months": 0}],
            "lines": [{"item": "total_assets", "label": "Total assets", "column": 1, "value": 31300, "page": 2}],
            "absent": [{"item": i, "reason": "x"} for i in ("revenue", "net_income", "cfo")]}
    assert any("under one million" in f for f in r.checks(read))
    read["unit_multiplier"] = 1000000
    assert r.checks(read) == []


def test_scanned_uk_accounts_go_whole_with_the_uk_notes(monkeypatch):
    import io
    from pypdf import PdfWriter
    from src.extract import report_pdf as r
    w = PdfWriter()
    for _ in range(30):
        w.add_blank_page(595, 842)  # a scan: pages without a text layer
    buf = io.BytesIO()
    w.write(buf)
    sent = {}
    ok = {"currency": "GBP", "unit_multiplier": 1000, "columns": [{"column": 1, "statement": "IS", "period_end": "2025-12-31", "months": 12}],
          "lines": [{"item": "revenue", "label": "Turnover", "column": 1, "value": 900000, "page": 20}],
          "absent": [{"item": i, "reason": "x"} for i in ("net_income", "total_assets", "cfo")], "labels_named": ["Polydor"]}

    def call(content, model, effort):
        sent["pages"] = len(__import__("pypdf").PdfReader(io.BytesIO(__import__("base64").b64decode(content[0]["source"]["data"]))).pages)
        sent["prompt"] = content[1]["text"]
        return {"read": ok, "model": model, "usage": {}}
    monkeypatch.setattr(r, "call", call)
    row = {"company": "Universal Music Operations Ltd", "document": "Annual accounts", "period_end": "2025-12-31",
           "url": "https://example.org/x", "basis": "company"}
    res = r.read_report(row, buf.getvalue())
    assert sent["pages"] == 30 and res["status"] == "passed"
    assert "company's own" in sent["prompt"] and "turnover is revenue" in sent["prompt"] and "scan without a text layer" in sent["prompt"]


def test_companies_house_filing_history_keeps_full_accounts(monkeypatch):
    from src.collectors import companies_house as ch
    page = ('<table><tr><th>Date</th></tr>'
            '<tr><td>12 Oct 2026</td><td>AA</td><td>Full accounts made up to 31 December 2025</td>'
            '<td><a href="/company/00950138/filing-history/AbC/document?format=pdf&amp;download=0">View PDF</a></td></tr>'
            '<tr><td>22 Dec 2025</td><td>CS01</td><td>Confirmation statement</td><td><a href="/x/document?format=pdf&amp;download=0">PDF</a></td></tr>'
            '<tr><td>01 Jan 2025</td><td>AA</td><td>Dormant company accounts made up to 31 March 2024</td><td><a href="/y/document?format=pdf">PDF</a></td></tr></table>')
    calls = []

    class R:
        status_code, text = 200, page
    monkeypatch.setattr(ch, "get", lambda url, params=None: calls.append(params) or (R if params["page"] == 1 else type("E", (), {"status_code": 404})))
    got = ch.accounts("00950138")
    assert [a["made_up"] for a in got] == ["2025-12-31"]
    assert got[0]["url"].endswith("/company/00950138/filing-history/AbC/document?format=pdf&download=1")


def test_backtest_finds_a_signal_that_persists():
    from datetime import date, timedelta
    from src import backtest
    hist = {}
    start = date(2024, 1, 1)
    for i in range(120):  # each artist keeps its own weekly growth rate: past growth predicts future growth
        rate = 1 + (i % 20 - 9.5) / 1000
        ml = 2_000_000 + i * 1000
        hist[f"a{i}"] = [((start + timedelta(weeks=w)).isoformat(), int(ml * rate ** w)) for w in range(60)]
    r = backtest.run(hist, {})
    assert r["picks"] > 0 and r["hit_rate"] > 0.9


def test_this_month_movers_and_short_log(monkeypatch, tmp_path):
    from src import monthly
    monkeypatch.setattr(monthly, "SCOUT_LOG", tmp_path / "log.csv")
    (tmp_path / "log.csv").write_text("date,spotify_id,score,tier,monthly_listeners,label_status\n2026-10-20,a,90,Breaking,100,major\n")
    rows = [{"id": "a", "ml": 150, "label_status": "major", "scout": {"score": 90, "tier": "Breaking"}},
            {"id": "b", "ml": 50, "label_status": "self_released", "indie_kind": "prospect", "scout": {"score": 70, "tier": "Rising"}},
            # mostly a featured guest: not a pick
            {"id": "c", "ml": 40, "label_status": "self_released", "indie_kind": "prospect", "feat": 0.95, "scout": {"score": 95, "tier": "Rising"}}]
    hist = {"a": [("2026-09-23", 100), ("2026-10-24", 150)], "b": [("2026-10-10", 60)]}
    m = monthly.build(rows, hist, "2026-10-24")
    assert [x["id"] for x in m["up"]] == ["a"] and m["up"][0]["pct"] == 50.0  # b has no value near 30 days ago
    assert m["log_start"] is None and m["new_breaking"] == [] and m["prospects"] == ["b"]
    assert all(x["then"] is None for x in m["shares"])


def test_sony_music_segment_tables():
    from src.collectors import sony_music as s
    pages = ["Segment profit\nYen in millions\nThree months ended June 30\n2025 | 2026 | Change\nOperating income (loss):\n"
             "Game & Network Services | 147,957 | 202,014 | 54,057\nMusic | 92,807 | 105,882 | 13,075\nTotal | 1 | 2 | 1",
             "Sales by product category\nYen in millions\nThree months ended June 30\nSales: | 2025 | 2026 | Change\nMusic\n"
             "Recorded Music - Streaming | 196,016 | 237,066 | 41,050\nRecorded Music - Others | 105,473 | 143,885 | 38,412\n"
             "Music Publishing | 98,685 | 116,002 | 17,317\nVisual Media and Platform | 58,778 | 60,913 | 2,135\n"
             "Total | 458,952 | 557,866 | 98,914\nPictures\nMotion Pictures | 107,133 | 102,718 | (4,415"]
    rows = {(r["period_end"], r["item"]): r["value"] for r in s.parse(pages, "u")}
    assert rows[("2026-06-30", "operating_income")] == 105_882e6 and rows[("2025-06-30", "sales")] == 458_952e6
    assert rows[("2026-06-30", "recorded_streaming")] == 237_066e6 and ("2026-06-30", "Motion Pictures") not in rows


def test_risers_video_pick_and_parsers(monkeypatch):
    from src.site_build import pick_video
    from src.collectors import kworb_youtube, youtube_feed
    html = ('<tr><td class="text"><div><a href="../video/AAAAAAAAAAA.html">Post Malone - rockstar ft. 21 Savage</a></div></td>'
            '<td>1,000</td> <td>900</td> <td>2017/11</td></tr><tr><td class="text"><div><a href="../video/BBBBBBBBBBB.html">'
            '21 Savage - a lot</a></div></td><td>500</td> <td>100</td> <td>2019/02</td></tr>')
    vids = kworb_youtube.videos(html)
    assert [v["id"] for v in vids] == ["AAAAAAAAAAA", "BBBBBBBBBBB"] and vids[0]["yesterday"] == 900
    assert pick_video({"source": "kworb", "videos": vids}, "21 Savage", None)["id"] == "BBBBBBBBBBB"  # own video first
    assert pick_video({"source": "kworb", "videos": vids}, "21 Savage", "rockstar")["why"] == "newest hit"
    feed = ('<entry><yt:videoId>CCCCCCCCCCC</yt:videoId><title>Short</title><link rel="alternate" href="https://www.youtube.com/shorts/CCCCCCCCCCC"/>'
            '<published>2026-10-20T00:00:00+00:00</published></entry><entry><yt:videoId>DDDDDDDDDDD</yt:videoId><title>New &amp; video</title>'
            '<link rel="alternate" href="https://www.youtube.com/watch?v=DDDDDDDDDDD"/><published>2026-10-18T00:00:00+00:00</published>'
            '<media:statistics views="42"/></entry>')
    monkeypatch.setattr(youtube_feed, "get", lambda url, params=None: type("R", (), {"status_code": 200, "text": feed}))
    assert youtube_feed.latest("x") == [{"id": "DDDDDDDDDDD", "title": "New & video", "published": "2026-10-18", "views": 42}]


def test_credits_leaderboard(monkeypatch):
    from src.collectors import credits
    monkeypatch.setattr(credits, "load", lambda: {
        "A1": {"isrc": "A1", "recording": "r1", "producers": "Mustard~m1;Sounwave~m2", "writers": "K~w1"},
        "B1": {"isrc": "B1", "recording": "r2", "producers": "Mustard~m1", "writers": ""}})
    songs = [{"isrc": "A1", "title": "Not Like Us", "daily": 100, "artist_id": "k", "artist": "Kendrick"},
             {"isrc": "B1", "title": "Other", "daily": 50, "artist_id": "y", "artist": "YG"},
             {"isrc": "", "title": "No code", "daily": 999, "artist_id": "z", "artist": "Z"}]
    top = credits.leaderboard(songs)
    assert [(p["name"], p["daily"], p["artists"]) for p in top] == [("Mustard", 150, 2), ("Sounwave", 100, 1)]
    assert credits.split("Mustard~m1;Sounwave~m2") == [("Mustard", "m1"), ("Sounwave", "m2")]


def test_radio_parse_and_presence(monkeypatch, tmp_path):
    from src.collectors import radio
    page = ('<table><tr><th>Pos</th></tr><tr><td>1</td><td>=</td><td><a>Morgan Wallen - Just In Case</a></td><td>90</td>'
            '<td>1</td><td>(x5)</td><td>45.10</td><td>+0.30</td><td>2</td><td>46.0</td></tr>'
            '<tr><td>2</td><td>+1</td><td><a>Shaboozey - Good News (feat. Jelly Roll)</a></td><td>40</td><td>2</td><td></td>'
            '<td>30.00</td><td>-0.10</td><td>3</td><td>31.0</td></tr></table>')
    rows = radio.parse(page)
    assert [(r["pos"], r["artist_raw"], r["aud"]) for r in rows] == [(1, "Morgan Wallen", 45.1), (2, "Shaboozey", 30.0)]
    monkeypatch.setattr(radio, "CSV", tmp_path / "radio.csv")
    import csv
    with radio.CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, radio.FIELDS); w.writeheader()
        for r in rows:
            w.writerow({"date": "2026-10-24", **r})
    p = radio.presence({"mw": "Morgan Wallen", "jr": "Jelly Roll"})
    assert p["mw"]["aud"] == 45.1 and p["jr"]["best_pos"] == 2


def test_country_rule():
    from src.genre import decide_country, is_country
    assert is_country("red dirt") and is_country("Country pop") and not is_country("country blues")
    assert decide_country([("country", 8), ("pop", 2)], [])[0] == "country"
    assert decide_country([("country", 4), ("hip hop", 6)], [])[0] == "review"
    dz = {"match": "exact", "releases": "12", "country_share": "0.9"}
    assert decide_country([], [], dz, wikidata=True)[0] == "country"
    assert decide_country([], [], dz, wikidata=False)[0] == "review"  # name-only Deezer match never decides
    assert decide_country([("pop", 5)], [("pop", False, False)]) is None


def test_scout_weights_sum_to_one_per_genre():
    from src import insights
    for factors in insights.FACTORS_BY_GENRE.values():
        assert abs(sum(w for w, _ in factors.values()) - 1) < 1e-9


def test_label_rows_by_release_date():
    from src import labels
    t = labels.owners()
    assert labels.classify_label("Big Machine Records, LLC", "", t, False, "2023-05-01") == ("major_distributed", "Universal Music Group")  # HYBE-owned, grouped under its distributor
    assert labels.classify_label("Big Machine Records", "", t, False, "2026-06-01") == ("independent", "Big Machine Records (Scott Borchetta)")
    assert labels.classify_label("Blue Highway Records", "", t, False, "2026-06-01")[1] == "Universal Music Group"


def test_country_revenue_has_pandora_and_radio_songwriting():
    from datetime import date
    from src import revenue
    a = {"name": "X", "lead_daily": 1_000_000, "yt_daily": 0, "radio_week": 48.65}
    share = {"low": 0.2, "mid": 0.2, "high": 0.2}
    hh = {l["key"]: l for l in revenue.estimate(a, date(2026, 10, 24), share)["lines"]}
    cy = {l["key"]: l for l in revenue.estimate(a, date(2026, 10, 24), share, "country")["lines"]}
    assert "pandora" not in hh and "pandora" in cy
    assert cy["amazon"]["generated"]["mid"] > hh["amazon"]["generated"]["mid"]
    r = cy["radio"]
    assert r["artist"] is None and r["group"] == "Publishing"
    assert round(r["generated"]["mid"]) == round(48.65e6 * 52 * 0.25 / 1000)  # about $632k


def test_deezer_by_isrc_takes_the_artist_credited_on_most_songs(monkeypatch):
    from src.collectors import deezer

    class R:
        status_code = 200

        def __init__(self, j):
            self.j = j

        def json(self):
            return self.j
    songs = {"A": [{"id": 1, "name": "Eve"}], "B": [{"id": 1, "name": "Eve"}, {"id": 9, "name": "Swizz"}],
             "C": [{"id": 2, "name": "Eve"}]}

    def fake(url, params=None):
        if "isrc:" in url:
            return R({"id": 5, "contributors": songs[url.split(":")[-1]]})
        return R({"nb_fan": 77})
    monkeypatch.setattr(deezer, "get", fake)
    assert deezer.by_isrc("Eve", ["A", "B", "C"]) == {"deezer_id": 1, "deezer_fans": 77, "deezer_match": "isrc"}
    assert deezer.by_isrc("Eve", ["A", "C"]) is None  # one song each: no majority


def test_deezer_by_titles_needs_two_of_the_biggest_songs(monkeypatch):
    from src.collectors import deezer

    class R:
        status_code = 200

        def json(self):
            return {"data": [{"title": "Whiskey Glasses"}, {"title": "Chasin' You (Live)"}, {"title": "Sand In My Boots"}]}
    monkeypatch.setattr(deezer, "get", lambda url, params=None: R())
    assert deezer._title("Chasin' You - Acoustic") == deezer._title("Chasin' You (Live)") == "chasinyou"
    assert deezer.by_titles(1, ["Whiskey Glasses", "Chasin' You (feat. X)", "Other"])
    assert not deezer.by_titles(1, ["Whiskey Glasses", "Nope", "Other"])
    assert deezer.by_titles(1, ["Sand In My Boots"])


def test_credits_leaderboard_counts_a_shared_song_once(monkeypatch):
    from src.collectors import credits
    monkeypatch.setattr(credits, "load", lambda: {"US1": {"producers": "Ryan Lewis|mb1", "writers": ""}})
    monkeypatch.setattr(credits, "split", lambda v: [tuple(v.split("|"))] if v else [])
    songs = [{"isrc": "US1", "title": "Thrift Shop", "daily": 100, "artist_id": a, "artist": a} for a in ("m", "rl", "m&rl")]
    (p,) = credits.leaderboard(songs)
    assert p["daily"] == 100 and len(p["songs"]) == 1


def test_deezer_country_alone_does_not_override_wikidata_genres():
    from src import genre
    dz = {"match": "exact", "releases": "10", "country_share": "0.9"}
    assert genre.decide_country([], [("arabesque", False, False)], dz, wikidata=True)[0] == "review"
    assert genre.decide_country([], [], dz, wikidata=True)[0] == "country"


def test_label_name_follows_dated_rows_and_titles_keep_with():
    from src import labels
    from src.collectors import deezer
    t = labels.owners()
    assert labels.label_name("Big Machine Records", t, "2024-01-01") == "Big Machine Label Group"
    assert labels.label_name("Big Machine Records", t, "2026-05-01") == "Big Machine Records"
    assert deezer._title("Stay With Me") != deezer._title("Stay")
    assert deezer._title("Song (with X)") == deezer._title("Song")


def test_one_wikidata_genre_does_not_override_deezer_releases():
    from src.genre import decide_country
    wd = [("alternative country", False, False)]
    rock = {"match": "exact", "releases": "49", "country_share": "0.0"}
    assert decide_country([("rock", 1)], wd, rock)[0] == "review"
    assert decide_country([("rock", 1)], wd)[0] == "country"  # no Deezer match: Wikidata decides as before


def test_below_floor_artists_compare_by_streams_and_band_apart():
    from src import insights
    floor = {"id": "f", "ml": None, "daily": 20_000, "floor": True}
    listed = {"id": "m", "ml": 800_000, "daily": 90_000}
    assert insights.size(floor) == 200_000 and insights.size(listed) == 800_000
    assert insights.band_of(floor) == insights.FLOOR_BAND and insights.band_of(listed) == 0
    assert insights.band_label(insights.FLOOR_BAND).startswith("under 500k")


def test_ids_for_deezer_needs_one_artist_and_one_spotify_link(monkeypatch):
    from src.collectors import musicbrainz as mb

    class R:
        def __init__(self, j): self.status_code, self._j = 200, j
        def json(self): return self._j
    pages = {
        "url": {"relations": [{"artist": {"id": "mb1"}}]},
        "artist/mb1": {"relations": [{"url": {"resource": "https://open.spotify.com/artist/SP1"}},
                                     {"type": "wikidata", "url": {"resource": "https://www.wikidata.org/wiki/Q1"}}]},
    }
    monkeypatch.setattr(mb, "get", lambda url, params=None: R(pages[url.split("/ws/2/")[1]]))
    assert mb.ids_for_deezer("1") == {"mbid": "mb1", "spotify_id": "SP1", "qid": "Q1"}
    pages["url"] = {"relations": [{"artist": {"id": "mb1"}}, {"artist": {"id": "mb2"}}]}  # shared URL: no match
    assert mb.ids_for_deezer("1")["spotify_id"] == ""


def test_description_sentences_and_fallback():
    from src.collectors.descriptions import first_sentences
    from src.site_build import about_of
    t = "J. Cole (born 1985) is an American rapper. He grew up in St. Louis. He founded Dreamville."
    assert first_sentences(t) == "J. Cole is an American rapper. He grew up in St. Louis."
    assert first_sentences("One sentence only") == "One sentence only"
    r = {"name": "X", "country": "United States", "since": "2019", "label_status": "major",
         "label_name": "Capitol Records", "label_owner": "Universal Music Group"}
    assert about_of(r, None, "country")["text"] == (
        "X is a country artist from the United States, active since 2019, signed to Capitol Records (Universal Music Group).")
    assert about_of(r, {"text": "W.", "url": "u"}, "country") == {"text": "W.", "source": "wikipedia", "url": "u"}


def test_description_sentence_edge_cases():
    from src.collectors.descriptions import first_sentences as f
    assert f("S is a rapper from Washington, D.C. He is known for his mixtapes. Third.") == \
        "S is a rapper from Washington, D.C. He is known for his mixtapes."
    assert f("M rose in the 2010s. He founded a label. Third.") == "M rose in the 2010s. He founded a label."
    assert f("She served in the U.S. Army. She sings. Third.") == "She served in the U.S. Army. She sings."
    assert f("Mac Miller (born Malcolm (Mac) McCormick) was a rapper.") == "Mac Miller was a rapper."


def test_independent_kind_established_or_prospect():
    from src import labels
    t = labels.owners()
    reg = {"USUM7": "Universal Music Group"}
    # a past label deal on Wikidata
    assert labels.independent_kind("Jeezy", ["Def Jam Recordings"], [], {}, "", 2026, t)[0] == "established"
    # own recordings registered by a major
    k, why = labels.independent_kind("X", [], [{"isrc": "USUM71900001", "deezer_date": "2019-05-01"}], reg, "", 2026, t)
    assert k == "established" and "Universal Music Group" in why[0]
    # a long career
    assert labels.independent_kind("X", [], [{"isrc": "QZAAA1800001", "deezer_date": "2016-01-01"}], reg, "", 2026, t)[0] == "established"
    # none of these: an unsigned prospect (a distributor on Wikidata is not a label deal)
    assert labels.independent_kind("X", ["UnitedMasters"], [{"isrc": "QZAAA2400001", "deezer_date": "2023-03-01"}], reg, "", 2026, t) == ("prospect", [])


def test_worth_multiple_blends_by_release_age():
    from src import insights
    t = insights.multiples()
    m = {x["vintage"]: (float(x["multiple_low"]), float(x["multiple_high"])) for x in t}
    # all streams on songs 10+ years old: the evergreen multiple
    lo, hi, band, mix = insights.blended({"evergreen": 1.0, "coverage": 0.9}, t)
    assert (lo, hi, band) == (*m["evergreen"], "evergreen")
    # half new, half evergreen: the average of the two bands
    lo, hi, band, _ = insights.blended({"new": 0.5, "evergreen": 0.5, "coverage": 0.8}, t)
    assert lo == round((m["new"][0] + m["evergreen"][0]) / 2, 2) and hi == round((m["new"][1] + m["evergreen"][1]) / 2, 2)
    # too few streams dated: no age-based multiple (the current-share vintage is used instead)
    assert insights.blended({"new": 1.0, "coverage": 0.3}, t) is None


def test_youtube_api_daily_rate_within_30_days():
    from datetime import date
    from src.collectors.youtube_api import daily_rate
    now = {"views": 1_700_000}
    # first run: nothing earlier
    assert daily_rate(now, None, date(2026, 11, 1)) == {"prev_date": "", "prev_views": "", "views_per_day": ""}
    # one day later: the earlier snapshot becomes the base, too young for a rate
    prev = {"date": "2026-11-01", "views": "1000000", "prev_date": "", "prev_views": "", "views_per_day": ""}
    out = daily_rate(now, prev, date(2026, 11, 2))
    assert out["prev_date"] == "2026-11-01" and out["views_per_day"] == ""
    # ten days after the base: views a day over those ten days
    prev = {"date": "2026-11-10", "views": "1600000", "prev_date": "2026-11-01", "prev_views": "1000000", "views_per_day": ""}
    assert daily_rate(now, prev, date(2026, 11, 11))["views_per_day"] == 70_000
    # base over 30 days old: dropped (API terms); the last rate is kept while the new base matures
    prev = {"date": "2026-12-01", "views": "1650000", "prev_date": "2026-11-01", "prev_views": "1000000", "views_per_day": "21000"}
    out = daily_rate(now, prev, date(2026, 12, 2))
    assert out["prev_date"] == "2026-12-01" and out["views_per_day"] == 21000


def test_spotify_rate_one_source():
    # the revenue lines (platforms.csv) and the list figure (rates.csv) must use the same Spotify rate
    from src import money, revenue
    r = money.rates()["master_per_1000"]
    p = revenue.platforms()["spotify"]
    assert [p[f"per_1000_{k}"] for k in ("low", "mid", "high")] == [r["low"], r["mid"], r["high"]]


def test_independent_kind_size_and_activity():
    """Review 5 (2026-10-25): 10m+ listeners is established; a prospect needs current listeners and a recent song."""
    from datetime import date
    from src import labels
    t, today = labels.owners(), date(2026, 10, 25)
    new = [{"isrc": "QZAAA2500001", "first_release": "2025-06-01"}]
    k, why = labels.independent_kind("X", [], new, {}, "", 2026, t, ml=19_700_000, cl=10_000_000, today=today)
    assert k == "established" and why == ["10m+ monthly listeners"]
    assert labels.independent_kind("X", [], new, {}, "", 2026, t, ml=2_000_000, cl=900_000, today=today) == ("prospect", [])
    # no current listeners: catalog only
    k, why = labels.independent_kind("X", [], new, {}, "", 2026, t, ml=5_000_000, cl=0, today=today)
    assert k == "inactive" and why[0].startswith("catalog only")
    # newest song of their own over 2 years old (the kworb date counts too)
    old = [{"isrc": "QZAAA2000001", "first_release": "2020-03-01"}]
    k, why = labels.independent_kind("X", [], old, {}, "", 2026, t, ml=3_000_000, cl=500_000, today=today)
    assert k == "inactive" and "from 2020" in why[0]
    assert labels.independent_kind("X", [], old, {}, "", 2026, t, ml=3_000_000, cl=500_000, latest_lead="2026-01-10",
                                   today=today)[0] == "prospect"
    # below the 500k floor with no stream figure
    assert "below 500k" in labels.independent_kind("X", [], new, {}, "", 2026, t, today=today, floor=True)[1][0]
    # without `today` (older callers) only the established test applies
    assert labels.independent_kind("X", [], old, {}, "", 2026, t, cl=0)[0] == "prospect"


def test_second_profiles_share_wikidata_deezer_or_name():
    from src import site_build
    rows = [{"id": "bob", "name": "B.o.B", "ml": 27_000_000}, {"id": "b2", "name": "Bob", "ml": 2_200_000},
            {"id": "pac", "name": "2Pac", "ml": 28_000_000}, {"id": "mak", "name": "Makaveli", "ml": 1_600_000},
            {"id": "m1", "name": "Macklemore & Ryan Lewis", "ml": 5_000_000}, {"id": "m2", "name": "Macklemore & Ryan Lewis", "ml": 900_000},
            {"id": "x", "name": "Someone", "ml": 3_000_000}, {"id": "y", "name": "Other", "ml": 2_000_000}]
    artists = {"bob": {"deezer_id": "280294", "deezer_match": "isrc"}, "b2": {"deezer_id": "280294", "deezer_match": "isrc"},
               "pac": {"wikidata_id": "Q6107"}, "mak": {"wikidata_id": "Q6107"},
               # an unconfirmed Deezer match is not evidence
               "x": {"deezer_id": "5", "deezer_match": ""}, "y": {"deezer_id": "5", "deezer_match": ""}}
    from src.collectors import deezer
    if "isrc" not in deezer.CONFIRMED:
        for k in ("bob", "b2"):
            artists[k]["deezer_match"] = next(iter(deezer.CONFIRMED))
    assert site_build.second_profiles(rows, artists) == {"b2": "bob", "mak": "pac", "m2": "m1"}


def test_scout_absent_signal_scores_zero_and_tier_needs_weight():
    from src import insights
    rows = [{"id": f"s{i}", "ml": 1_000_000, "fresh_share": 0.0 if i < 5 else i / 10, "cur_share": i / 10,
             "daily": 100_000 + i, "chg_pct": i / 100, "geo": None, "attention": None} for i in range(10)]
    insights.scout(rows)
    assert rows[0]["scout"]["factors"]["velocity"] == 0 and rows[0]["scout"]["factors"]["breadth"] == 0
    assert rows[9]["scout"]["factors"]["velocity"] > 50 and rows[9]["scout"]["weight"] >= 0.6
    # current share, engagement and momentum measured, new-release pull and growth missing: 41 of 81 points of
    # weight, so a provisional score with no tier
    thin = [{"id": f"t{i}", "ml": 1_000_000, "cur_share": i / 10, "daily": 100_000 + i, "chg_pct": i / 100,
             "fresh_share": None, "attention": None} for i in range(10)]
    insights.scout(thin, {k: insights.FACTORS[k] for k in ("current", "engagement", "momentum", "velocity", "growth")})
    sc = thin[9]["scout"]
    assert sc["provisional"] and sc["tier"] is None and sc["weight"] == round(0.41 / 0.81, 2) and sc["score"] >= 80


def test_picks_leave_out_featured_guests_and_non_prospects():
    from src import insights
    base = {"label_status": "self_released", "indie_kind": "prospect", "feat": 0.2}
    assert insights.is_pick(base)
    assert not insights.is_pick({**base, "feat": 0.97})               # SRNO: mostly a featured guest
    assert insights.is_prospect({**base, "feat": 0.97})
    assert not insights.is_prospect({**base, "indie_kind": "inactive"})  # Knust: catalog only
    assert not insights.is_prospect({**base, "indie_kind": "established"})
    assert not insights.is_prospect({**base, "second_of": "x"})


def test_labels_index_sums_royalty_and_value_ranges():
    from src import insights
    line = lambda lo, hi: {"group": "Streaming", "generated": {"low": lo, "mid": (lo + hi) / 2, "high": hi}}
    rows = [{"id": "a", "label_name": "L", "label_status": "independent", "label_owner": "L", "ml": 10, "cl": 5,
             "streaming_mid": 150, "revenue": {"lines": [line(100, 200), {"group": "Publishing", "generated": {"low": 9, "mid": 9, "high": 9}}]},
             "worth_range": [1000, 3000], "worth_mid": 1800, "scout": {"tier": "Rising", "score": 70}},
            {"id": "b", "label_name": "L", "label_status": "independent", "label_owner": "L", "ml": 5, "cl": 1,
             "streaming_mid": 15, "revenue": {"lines": [line(10, 20)]}, "worth_range": [100, 300], "worth_mid": 180},
            {"id": "c", "label_name": "L", "label_status": "independent", "label_owner": "L", "ml": 99, "second_of": "a",
             "revenue": {"lines": [line(1e6, 2e6)]}, "worth_range": [1e6, 2e6], "worth_mid": 1.5e6}]
    L = insights.labels_index(rows, {"L": 4})[0]
    assert L["artists"] == ["a", "b", "c"] and L["ml"] == 15  # a second profile is listed, not summed
    assert (L["roy_low"], L["roy_high"]) == (110, 220)  # streaming lines only, low ends and high ends added
    assert (L["value_low"], L["value_mid"], L["value_high"]) == (1100, 1980, 3300)
    assert L["rising"] == 1 and L["scout_avg"] == 70 and L["releases_2y"] == 4


def test_second_profiles_checked_different_never_joined(monkeypatch):
    from src import site_build
    rows = [{"id": "bob", "name": "B.o.B", "ml": 27_000_000}, {"id": "b2", "name": "Bob", "ml": 2_200_000}]
    artists = {k: {"deezer_id": "280294", "deezer_match": "exact"} for k in ("bob", "b2")}
    assert site_build.second_profiles(rows, artists) == {"b2": "bob"}
    monkeypatch.setattr(site_build, "profile_pairs", lambda: {frozenset(("b2", "bob")): {
        "second_id": "b2", "main_id": "bob", "verdict": "different"}})
    assert site_build.second_profiles(rows, artists) == {}


def test_musicbrainz_follows_merged_ids(monkeypatch):
    from src.collectors import musicbrainz as mb
    old, new = "9a1e8681-e3da-4fa7-aadf-f6a05b567fd5", "9fff2f8a-21e6-47de-a2b8-7f449929d43f"
    assert mb.current_id(old, {old: new}) == new
    assert mb.current_id(old, {old: "a", "a": new}) == new  # two merges
    assert mb.current_id(old, {old: ""}) == old  # MusicBrainz no longer knows it: kept for the owner
    assert mb.current_id("", {}) == "" and mb.current_id(new, {}) == new

    class R:
        status_code = 200

        def json(self):
            return {"id": new, "genres": [{"name": "hip hop", "count": 3}], "country": "CA"}
    monkeypatch.setattr(mb, "get", lambda *a, **k: R())
    table = {}
    row = mb.fetch("3TVXtAsR1Inumwj472S9r4", old, table)
    assert row["musicbrainz_id"] == new and table == {old: new} and row["genres"] == "hip hop:3"


def test_deezer_dates_undated_own_songs_but_not_reissues():
    from src import labels
    songs = [{"track_id": "t1", "title": "SHAGANSSS", "feature": False},
             {"track_id": "t2", "title": "Hail Mary", "feature": False},
             {"track_id": "t3", "title": "Guest Spot", "feature": True},
             {"track_id": "t4", "title": "Old Song", "feature": False},
             {"track_id": "t5", "title": "Dated", "feature": False},
             {"track_id": "t6", "title": "Para Sa Sarili - Live at the Hills Studio", "feature": False},
             {"track_id": "t7", "title": "New One (feat. Someone)", "feature": False}]
    dates = {"t4": {"isrc": "USUM70100001"}, "t5": {"first_release": "2020-01-01", "deezer_date": "2020-01-01"}}
    rel = lambda t, d, k="single": {"title": t, "release_date": d, "record_type": k}
    releases = [rel("SHAGANSSS", "2026-03-25"), rel("Hail Mary (Remastered 2026)", "2026-05-01"),
                rel("Guest Spot", "2026-01-01"), rel("Old Song", "2026-02-01"), rel("Dated", "2026-02-01"),
                rel("Para Sa Sarili (Live at the Hills Studio)", "2026-02-01"), rel("New One", "2025-11-01"),
                rel("Storm", "2026-05-26"), rel("Greatest Hits", "2026-01-01", "compile")]
    got = labels.deezer_dated_songs(releases, songs, dates)
    # a new single dated; a remaster, a guest song, an old recording (ISRC 2001), an already dated song, a live
    # version and a release with no song of that title on Spotify (another artist of the name) are not
    assert [(g["title"], g["deezer_date"]) for g in got] == [("SHAGANSSS", "2026-03-25"), ("New One (feat. Someone)", "2025-11-01")]
    from datetime import date
    t = [{"name": "Def Jam", "pattern": "Def Jam", "status": "major", "owner": "UMG"}]
    old = [{"isrc": "QZAAA2200001", "deezer_date": "2022-05-01", "first_release": "2022-05-01"}]
    kw = dict(ml=2_000_000, cl=300_000, today=date(2026, 10, 25))
    assert labels.independent_kind("X", [], old, {}, "", 2026, t, **kw)[0] == "inactive"
    assert labels.independent_kind("X", [], old, {}, "", 2026, t, deezer_dated=got, **kw) == ("prospect", [])


def test_independent_kind_featured_guest_not_prospect():
    """Danny Chung (100% of streams as a guest) and SRNO (97%): not prospects, even with a recent song."""
    from datetime import date
    from src import labels
    t, kw = labels.owners(), dict(ml=2_000_000, cl=300_000, today=date(2026, 10, 25))
    new = [{"isrc": "QZAAA2500001", "first_release": "2025-06-01"}]
    assert labels.independent_kind("X", [], new, {}, "", 2026, t, feat=0.89, **kw) == ("prospect", [])
    k, why = labels.independent_kind("X", [], new, {}, "", 2026, t, feat=0.97, **kw)
    assert k == "inactive" and why == ["mostly a featured guest on others' songs"]
