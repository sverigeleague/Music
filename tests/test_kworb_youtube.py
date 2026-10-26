from src.collectors import kworb_youtube as ky

PAGE = ('<span class="pagetitle">X YouTube Statistics | <a href="/spotify/artist/AAAAAAAAAAAAAAAAAAAAAA_songs.html">Spotify stats</a></span>'
        '<tr><td class="text"><div><a href="../video/own000000a1.html">X - Song</a></div></td>'
        '<tr><td class="text"><div>* <a href="../video/feat00000b2.html">Y ft. X</a></div></td>')


def test_own_videos_leave_out_features():
    assert ky.own_videos(PAGE) == {"own000000a1"}
    assert ky.parse(PAGE)["spotify_id"] == "AAAAAAAAAAAAAAAAAAAAAA"


def test_accept_needs_an_identifier():
    sid = "AAAAAAAAAAAAAAAAAAAAAA"
    assert ky.accept(sid, sid, "") == "backlink"
    assert ky.accept("BBBBBBBBBBBBBBBBBBBBBB", sid, "kworb_spotify_link") is None  # links to another artist
    assert ky.accept(None, sid, "") is None  # name only
    assert ky.accept(None, sid, "kworb_spotify_link") == "kworb_spotify_link"


def test_channel_match_one_unlinked_page_only():
    pages = {"x": {"v1", "v2"}, "y": {"v3"}, "z": {"v4"}}
    assert ky.channel_match({"UC1": {"v2", "v9"}}, pages, set()) == (("x", "channel UC1 video v2"), {"x": "channel UC1 video v2"})
    assert ky.channel_match({"UC1": {"v9"}}, pages, set()) == (None, {})
    match, hits = ky.channel_match({"UC1": {"v1", "v3"}}, pages, set())  # two pages: review, not data
    assert match is None and set(hits) == {"x", "y"}
    match, hits = ky.channel_match({"UC1": {"v4"}}, pages, {"z"})  # the page links back to another Spotify ID
    assert match is None and set(hits) == {"z"}
