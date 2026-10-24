import gzip

import pytest

from src.collectors import discogs_labels as d

XML = """<labels>
<label><id>1</id><name>Big Major Group</name><sublabels><label id="2">Capitol Records</label></sublabels></label>
<label><id>2</id><name>Capitol Records</name><parentLabel id="1">Big Major Group</parentLabel></label>
<label><id>3</id><name>Street Kings</name><parentLabel id="2">Capitol Records</parentLabel></label>
<label><id>4</id><name>Street Kings, LLC.</name></label>
<label><id>5</id><name>Urban</name><parentLabel id="1">Big Major Group</parentLabel></label>
<label><id>6</id><name>Urban (2)</name><parentLabel id="7">Beggars Group</parentLabel></label>
<label><id>7</id><name>Beggars Group</name></label>
<label><id>8</id><name>Lonely Imprint</name><parentLabel id="212">x</parentLabel></label>
<label><id>212</id><profile>DO NOT USE.</profile></label>
<label><id>9</id><name>Old Songs</name><parentLabel id="10">Grand Music Publishing Ltd.</parentLabel></label>
<label><id>10</id><name>Grand Music Publishing Ltd.</name><parentLabel id="1">Big Major Group</parentLabel></label>
<label><id>11</id><name>Allpoints</name><parentLabel id="12">Believe</parentLabel></label>
<label><id>12</id><name>Believe</name></label>
<label><id>13</id><name>Echo Hill</name><parentLabel id="1">Big Major Group</parentLabel></label>
<label><id>14</id><name>Echo Hill (2)</name></label>
</labels>"""

TABLE = [{"pattern": "big major", "label": "Big Major", "owner": "Universal Music Group", "status": "major",
          "note": "", "wikidata_check": ""}]


@pytest.fixture
def index(tmp_path):
    p = tmp_path / "labels.xml.gz"
    with gzip.open(p, "wt") as f:
        f.write(XML)
    return d.build_index(p)


def test_build_index(index):
    assert index["by_id"]["3"] == {"name": "Street Kings", "parent": "2"}
    assert "212" not in index["by_id"]  # nameless placeholder
    assert index["by_key"]["urban"] == ["5", "6"]  # "(2)" folds into the same name
    assert index["by_key"]["streetkings"] == ["3", "4"]  # so do company suffixes


def test_chain(index):
    assert d.chain("Street Kings Records LLC", index) == ["Street Kings", "Capitol Records", "Big Major Group"]
    assert d.chain("Lonely Imprint", index) == ["Lonely Imprint"]  # parent is the placeholder
    assert d.chain("Nothing Like It", index) == []


def test_owner_of(index):
    owner, status, ch = d.owner_of("Street Kings", index, TABLE)
    assert (owner, status) == ("Universal Music Group", "major") and ch[-1] == "Big Major Group"
    # a split string: the part Discogs places decides; Believe comes from the built-in map
    assert d.owner_of("Tiny Thing / AllPoints", index, TABLE)[:2] == ("Believe", "independent")
    assert d.owner_of("Lonely Imprint", index, TABLE)[:2] == ("", "unknown")


def test_ambiguous_and_namesakes(index):
    assert d.lookup("Urban", index, TABLE)["status"] == "ambiguous"  # two labels, different owners
    res = d.lookup("Echo Hill", index, TABLE)  # the namesake has no parent: says nothing, but is flagged
    assert res["status"] == "major" and res["namesakes"] == 1
    assert d.low_confidence("Echo Hill", "Someone", res["match"], res["namesakes"])


def test_publisher_stops_chain(index):
    assert d.lookup("Old Songs", index, TABLE)["status"] == "unknown"


def test_low_confidence():
    assert d.low_confidence("Independent", "X") == "generic name"
    assert d.low_confidence("Dalex Music", "Dalex") == "artist's own name"
    assert d.low_confidence("Rec. 118", "Soprano") == ""


def test_place_artist(index):
    rels = [{"label": "Street Kings", "release_date": "2026-01-01", "title": "a"},
            {"label": "Urban", "release_date": "2025-06-01", "title": "b"}]
    p = d.place_artist(rels, "Some Rapper", TABLE, index)
    assert p["status"] == "major" and p["basis"]["discogs_id"] == "3" and p["agree"] == "1 of 2 recent releases"
    assert d.place_artist([rels[1]], "Some Rapper", TABLE, index)["status"] == "unknown"


def test_saved_rows(index, tmp_path, monkeypatch):
    monkeypatch.setattr(d, "CSV", tmp_path / "parents.csv")
    d.save(d.rows_for(["Street Kings", "Urban", "Lonely Imprint"], index, TABLE))
    rows = d.load()
    assert rows["Street Kings"]["parent_chain"] == "Street Kings > Capitol Records > Big Major Group"
    assert rows["Urban"]["status"] == "ambiguous"
    monkeypatch.setattr(d, "_INDEX", None)  # no dump in memory: read the saved file
    assert d.owner_of("Street Kings")[:2] == ("Universal Music Group", "major")
    assert d.owner_of("Urban")[:2] == ("", "ambiguous")
