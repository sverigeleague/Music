from src import quality


def _csv(path, text):
    path.write_text(text.strip() + "\n")


def test_queues_count_open_rows_by_genre(tmp_path):
    rev, reg = tmp_path / "review", tmp_path / "registry"
    rev.mkdir(), reg.mkdir()
    _csv(rev / "genre_review.csv", "spotify_id,name\na,A\nb,B\nc,C")
    _csv(rev / "label_review.csv", "spotify_id,name\nd,D")
    _csv(rev / "country_review_batch1.csv", "spotify_id,name\ne,E")
    _csv(rev / "youtube_review.csv", "date,genre,spotify_id\n2026-10-25,hip_hop,f\n2026-10-25,country,g")
    _csv(reg / "genre_overrides.csv", "spotify_id,decision\nb,hip_hop\ne,country")
    _csv(reg / "label_overrides.csv", "spotify_id,status\nd,major")
    hh = {q["file"]: q for q in quality.queues("hip_hop", rev, reg)}
    assert hh["review/genre_review.csv"] == {"file": "review/genre_review.csv", "what": quality.QUEUES[0][2], "rows": 3, "open": 2}
    assert hh["review/label_review.csv"]["open"] == 0
    assert hh["review/youtube_review.csv"]["rows"] == 1  # only the hip-hop row
    assert "review/country_review_batch1.csv" not in hh
    co = {q["file"]: q for q in quality.queues("country", rev, reg)}
    assert co["review/country_review_batch1.csv"]["open"] == 0 and co["review/youtube_review.csv"]["rows"] == 1


def test_latest_reads_first_and_last_date(tmp_path):
    p = tmp_path / "x.csv"
    _csv(p, "date,v\n2026-10-24,1\n2026-10-23,2\n,3\nn/a,4\n2026-10-25T10:00,5")
    assert quality.latest(p, "date") == {"first": "2026-10-23", "latest": "2026-10-25", "rows": 3}
    assert quality.latest(p, "missing") is None
    assert quality.latest(tmp_path / "none.csv", "date") is None


def test_corrections_filter_and_order(tmp_path):
    _csv(tmp_path / "corrections.csv", "date,genre,kind,subject,field,was,now,basis,source\n"
         "2026-10-24,hip_hop,data,A,label,x,y,b,s\n2026-10-25,all,method,R,rate,1,2,b,s\n2026-10-25,country,data,C,genre,x,y,b,s")
    rows = quality.corrections("hip_hop", tmp_path)
    assert [r["subject"] for r in rows] == ["R", "A"]


def test_method_versions_parsed(tmp_path):
    p = tmp_path / "m.md"
    p.write_text("# M\n\n## Change log\n\n- 1.1 (2026-10-23): second,\n  wrapped line.\n- 1.0 (2026-10-23): first.\n")
    assert quality.method_versions(p) == [{"version": "1.1", "date": "2026-10-23", "change": "second, wrapped line."},
                                          {"version": "1.0", "date": "2026-10-23", "change": "first."}]


def test_repository_files_parse():
    # the real corrections log and change log: every row complete, versions found
    rows = quality.corrections("hip_hop") + quality.corrections("country")
    assert rows and all(r["date"] and r["subject"] and r["now"] and r["kind"] in ("data", "method") for r in rows)
    assert quality.method_versions()
