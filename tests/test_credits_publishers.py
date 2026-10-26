"""Publishers on record (MusicBrainz works): grouping to publishing groups by name, record companies left out."""
from src.collectors import credits as c


def test_groups_by_name():
    cases = {
        "Sony Music Publishing": ["Sony/ATV Songs LLC", "Sony Music Publishing (Japan) Inc.", "EMI April Music Inc.",
                                  "EMI Blackwood Music Inc.", "EMI", "ソニー・ミュージックパブリッシング A事業部"],
        "Universal Music Publishing Group": ["Songs of Universal, Inc.", "Universal Music Corp.", "Universal Music Publishing Ltd.",
                                             "Universal/MCA Music Publishing GmbH", "Universal Música Unica Publishing",
                                             "Universal–Songs of PolyGram International, Inc.", "PolyGram International Publishing, Inc.",
                                             "Zomba Songs", "Careers–BMG Music Publishing, Inc.", "Almo Music Corp."],
        "Warner Chappell": ["Warner–Tamerlane Publishing Corp.", "WB Music Corp.", "WC Music Corp.", "Warner/Chappell Music, Inc.",
                            "Warner Chappell Music France", "Warner Bros., Inc. (Warner Bros. Music Division)"],
        "Kobalt": ["Kobalt Music Publishing Ltd.", "Songs of Kobalt Music Publishing"],
        "BMG": ["BMG", "BMG Platinum Songs US", "BMG Rights Management GmbH"],
        "Concord": ["Concord Music Publishing", "Imagem", "Songs of Imagem Music"],
        "Reservoir": ["Reservoir Media Management"],
        "Downtown / Songtrust": ["Downtown Music Publishing", "Songtrust Ave", "Sentric Music"],
        c.OTHER: ["Top Dawg Music", "Universal Pictures Music", "Peer Music Publishing", "Eardrummers Music Publishing",
                  "フジパシフィックミュージック BMG事業部"],
    }
    for g, names in cases.items():
        for n in names:
            assert c.group(n) == g, (n, c.group(n))


def test_record_company_is_not_a_publisher():
    for n in ["Sony Music Entertainment", "Universal Music Group", "Warner Records", "Warner Music Group Corp.",
              "Ultra Records", "UMG Recordings, Inc.", "Cash Money Records", "Copyright Control"]:
        assert c.record_company(n), n
    for n in ["Sony Music Publishing", "Universal Music Publishing Group", "Warner Chappell Music",
              "Diamon Cut Flawless Recordings Publishing", "Young Money Publishing Inc.", "BMG"]:
        assert not c.record_company(n), n
    groups, dropped = c.publishers("Sony Music Entertainment~m1;EMI April Music Inc.~m2;Universal Music Group~m3;"
                                   "Kobalt Music~m4~sub;Top Dawg Music~m5")
    assert dropped == ["Sony Music Entertainment", "Universal Music Group"]
    assert groups == [{"group": "Sony Music Publishing", "names": ["EMI April Music Inc."]},
                      {"group": "Kobalt", "names": ["Kobalt Music"]},
                      {"group": c.OTHER, "names": ["Top Dawg Music"]}]
    assert c.publishers("") == ([], [])


def test_parse_reads_publishers_and_iswc():
    lab = lambda n, i, sub=False: {"type": "publishing", "target-type": "label", "attributes": ["sub"] if sub else [],
                                   "label": {"name": n, "id": i}}
    j = {"title": "Song", "relations": [
        {"type": "producer", "artist": {"name": "P", "id": "p1"}},
        {"type": "performance", "work": {"id": "w1", "iswcs": ["T-1"], "relations": [
            {"type": "writer", "artist": {"name": "W", "id": "a1"}}, lab("Kobalt Music", "k1"), lab("Fuji", "f1", True)]}}]}
    r = c.parse(j)
    assert r["work"] == "w1" and r["iswc"] == "T-1" and r["writers"] == "W~a1" and r["producers"] == "P~p1"
    assert r["publishers"] == "Fuji~f1~sub;Kobalt Music~k1"
    assert [g["group"] for g in c.publishers(r["publishers"])[0]] == ["Kobalt", c.OTHER]
