from src.collectors import shazam as s
from src.collectors.apple_charts import fold

CSV_TEXT = '﻿\n"Saturday, 24 October 2026 [performance over the past 7 days]"\nRank,Artist,Title\n' \
           '1,"KAROL G, Judeline & rusowsky","BbY WOW"\n' \
           '2,"French Montana","Unforgettable (feat. Swae Lee)"\n' \
           '3,"Tyler, The Creator & Kali Uchis","See You Again"\n' \
           'x,"bad","row"\n'

KNOWN = {fold(n): [f"id_{i}"] for i, n in enumerate(
    ["Tyler, The Creator", "Earth, Wind & Fire", "Kali Uchis", "French Montana", "Swae Lee", "Dave", "Tems"])}
KNOWN[fold("Twin")] = ["a", "b"]  # ambiguous name


def test_parse_skips_title_lines_and_bad_rows():
    rows = s.parse(CSV_TEXT)
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert rows[0] == {"rank": 1, "artist": "KAROL G, Judeline & rusowsky", "title": "BbY WOW"}
    assert s.parse("no header here") == []


def test_split_artists_separators():
    assert s.split_artists("KAROL G, Judeline & rusowsky", KNOWN) == ["KAROL G", "Judeline", "rusowsky"]
    assert s.split_artists("A feat. B", KNOWN) == ["A", "B"]
    assert s.split_artists("A x B", KNOWN) == ["A", "B"]
    assert s.split_artists("A ft B & C", KNOWN) == ["A", "B", "C"]
    assert s.split_artists("Lil Nas X", KNOWN) == ["Lil Nas X"]


def test_split_artists_keeps_known_names_whole():
    assert s.split_artists("Tyler, The Creator", KNOWN) == ["Tyler, The Creator"]
    assert s.split_artists("Earth, Wind & Fire", KNOWN) == ["Earth, Wind & Fire"]
    assert s.split_artists("Tyler, The Creator & Kali Uchis", KNOWN) == ["Tyler, The Creator", "Kali Uchis"]
    assert s.split_artists("Dave & Tems, Earth, Wind & Fire", KNOWN) == ["Dave", "Tems", "Earth, Wind & Fire"]


def test_match_main_featured_and_ambiguous():
    assert s.match("French Montana", "Unforgettable (feat. Swae Lee)", KNOWN) == [KNOWN[fold("French Montana")][0],
                                                                               KNOWN[fold("Swae Lee")][0]]
    assert s.match("TYLER, THE CREATOR & Kali Uchis", "x", KNOWN) == [KNOWN[fold("Tyler, The Creator")][0],
                                                                     KNOWN[fold("Kali Uchis")][0]]
    assert s.match("Twin & Nobody", "x", KNOWN) == []


def test_presence(tmp_path, monkeypatch):
    p = tmp_path / "shazam.csv"
    p.write_text("date,chart_kind,place,rank,artist_raw,title,spotify_id\n"
                 "2026-10-23,top,world,1,A,T,old\n"
                 "2026-10-24,top,united-states,40,A,T,x\n"
                 "2026-10-24,city,united-states/atlanta,3,A,T,x\n"
                 "2026-10-24,hiphop,world,3,A,T,x\n")
    monkeypatch.setattr(s, "CSV", p)
    pr = s.presence()
    assert set(pr) == {"x"}
    assert pr["x"]["charts"] == 3 and pr["x"]["cities"] == ["atlanta"] and pr["x"]["countries"] == ["united-states"]
    assert pr["x"]["best"] == {"place": "world", "rank": 3, "kind": "hiphop"}
    assert pr["x"]["url"] == "https://www.shazam.com/charts/genre/world/hip-hop-rap"
    assert set(s.presence(days=7)) == {"x", "old"}


def test_charts_urls():
    urls = {(k, p): u for k, p, u in s.CHARTS}
    assert urls[("top", "world")] == "https://www.shazam.com/services/charts/csv/top-200/world"
    assert urls[("city", "brazil/são-paulo")].endswith("/top-50/brazil/s%C3%A3o-paulo")
    assert len(urls) == len(s.CHARTS)
