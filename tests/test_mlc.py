from src.collectors import mlc

# Built from the MLC Public Search API's OpenAPI schema (public-api.themlc.com/api/doc, v1.2.0); not yet checked
# against a live response (the API needs an account).
WORK = {"mlcSongCode": "AB1234", "iswc": "T9300000001", "primaryTitle": "TEST SONG",
        "writers": [{"writerFirstName": "JANE", "writerLastName": "DOE", "writerIPI": "00123456789"},
                    {"writerFirstName": None, "writerLastName": "SMITH"}],
        "publishers": [{"publisherName": "SONGS OF X", "publisherIpiNumber": "00999", "collectionShare": 37.5,
                        "publisherRoleCode": "E", "administrators": [{"publisherName": "ADMIN CO"}],
                        "parentPublishers": [{"publisherName": "MID PUB", "parentPublishers": [{"publisherName": "SONY MUSIC PUBLISHING"}]}]},
                       {"publisherName": "SELF PUB", "collectionShare": None}]}


def test_parse_work_rows_per_publisher():
    rows = mlc.parse_work(WORK, "XX0000000001", "2026-10-26")
    assert [r["publisher"] for r in rows] == ["SONGS OF X", "SELF PUB"]
    a = rows[0]
    assert a["share"] == 37.5 and a["role"] == "E" and a["administrator"] == "ADMIN CO"
    assert a["top_parent"] == "SONY MUSIC PUBLISHING" and a["song_code"] == "AB1234" and a["iswc"] == "T9300000001"
    assert a["writers"] == "JANE DOE (00123456789); SMITH"
    assert rows[1]["share"] == "" and rows[1]["top_parent"] == ""


def test_parse_work_without_publishers_keeps_one_row():
    rows = mlc.parse_work({"mlcSongCode": "Z1", "primaryTitle": "T"}, "I", "2026-10-26")
    assert len(rows) == 1 and rows[0]["publisher"] == "" and rows[0]["song_code"] == "Z1"


def test_update_skips_without_login(monkeypatch):
    monkeypatch.delenv("MLC_USERNAME", raising=False)
    monkeypatch.delenv("MLC_PASSWORD", raising=False)
    assert mlc.update(["XX0000000001"]) is None
