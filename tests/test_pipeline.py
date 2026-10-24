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
            {"id": "b", "ml": 50, "label_status": "self_released", "scout": {"score": 70, "tier": "Rising"}}]
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
    assert labels.classify_label("Big Machine Records, LLC", "", t, False, "2023-05-01") == ("major_distributed", "HYBE America")
    assert labels.classify_label("Big Machine Records", "", t, False, "2026-06-01") == ("independent", "Big Machine Records (Scott Borchetta)")
    assert labels.classify_label("Blue Highway Records", "", t, False, "2026-06-01")[1] == "HYBE America"


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
