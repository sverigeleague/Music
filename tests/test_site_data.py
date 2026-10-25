"""Smoke tests of a built site (site/data/, written by `python -m src.site_build`; gitignored).

They check what every page relies on: ids, ranks, ranges, the split data files (index, extra and its parts, shards)
agreeing with each other, flags and photos on disk, no NaN, a static page per artist and label, the sitemap. They skip
when the site is not built (tests.yml does not build it; site.yml runs them after its build, before the deploy).
"""
import json
import math
import re
from pathlib import Path

import pytest

from src.site_build import PARTS

SITE = Path(__file__).resolve().parent.parent / "site"
GENRES = {"hip_hop": SITE / "data", "country": SITE / "data" / "country"}


def _strict(path: Path):
    """JSON as the browser reads it: NaN and Infinity are not JSON (JSON.parse fails on them)."""
    def bad(c):
        raise ValueError(f"{path}: {c} is not valid JSON")
    return json.loads(path.read_text(), parse_constant=bad)


def _genre(name: str) -> dict:
    d = GENRES[name]
    if not (d / "index.json").exists():
        pytest.skip(f"site not built ({d}/index.json missing)")
    ix = _strict(d / "index.json")
    files = {"extra": _strict(d / "extra.json"), **{p: _strict(d / f"{p}.json") for p in PARTS}}
    shards = {int(f.stem): _strict(f) for f in (d / "a").glob("*.json")}
    return {"dir": d, "index": ix, "files": files, "shards": shards}


@pytest.fixture(scope="module", params=list(GENRES))
def g(request):
    return _genre(request.param) | {"name": request.param}


def _merged(g) -> list[dict]:
    """The artist rows as app.js has them once every file has loaded (artist_more merged in index order)."""
    rows = [dict(a) for a in g["index"]["artists"]]
    for f in g["files"].values():
        for k, col in f.get("artist_more", {}).items():
            for a, v in zip(rows, col):
                a[k] = v
    return rows


def _ranges(obj, where=""):
    """Every {low, mid, high} (or {low, high}) inside obj, with its path."""
    if isinstance(obj, dict):
        if {"low", "high"} <= obj.keys() and all(isinstance(obj.get(k), (int, float)) or obj.get(k) is None for k in ("low", "mid", "high")):
            yield where, obj
        for k, v in obj.items():
            yield from _ranges(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _ranges(v, f"{where}[{i}]")


def test_ids_unique_and_ranks_contiguous(g):
    A = g["index"]["artists"]
    ids = [a["id"] for a in A]
    assert len(ids) == len(set(ids)), "duplicate artist ids"
    assert all(re.fullmatch(r"[0-9A-Za-z]{22}", i) for i in ids), "an id is not a Spotify artist id"
    assert [a["rank"] for a in A] == list(range(1, len(A) + 1)), "ranks not 1..n in list order"
    cl = sorted(a["cl_rank"] for a in A if a.get("cl_rank"))
    assert cl == list(range(1, len(cl) + 1)), "current-listener ranks not contiguous"
    slugs = [a["slug"] for a in A]
    assert len(slugs) == len(set(slugs)), "duplicate page addresses"


def test_split_files_line_up(g):
    n = len(g["index"]["artists"])
    seen = set(g["index"])
    for name, f in g["files"].items():
        for k, col in f.get("artist_more", {}).items():
            assert len(col) == n, f"{name}.json artist_more.{k}: {len(col)} values for {n} artists"
        top = set(f) - {"artist_more"}
        assert not top & seen, f"{name}.json repeats {top & seen}"  # app.js merges them all into one object
        seen |= top
    cols = [k for f in g["files"].values() for k in f.get("artist_more", {})]
    assert len(cols) == len(set(cols)), "an artist field is in two files"
    assert not set(cols) & set(g["index"]["artists"][0]), "an artist field is in both the index and a later file"


def test_ranges_ordered(g):
    bad = []
    for a in _merged(g):
        for where, r in _ranges({k: a.get(k) for k in ("money", "rev_total")}):
            vals = [r[k] for k in ("low", "mid", "high") if r.get(k) is not None]
            if vals != sorted(vals):
                bad.append((a["name"], where, r))
        if a.get("worth_range") and a.get("worth_mid") is not None:
            lo, hi = a["worth_range"]
            if not lo <= a["worth_mid"] <= hi:
                bad.append((a["name"], "worth", a["worth_range"], a["worth_mid"]))
    for L in g["index"].get("labels", []):
        if not (L.get("roy_low") or 0) <= (L.get("royalties") or 0) <= (L.get("roy_high") or 0) + 1:
            bad.append((L["name"], "label royalties"))
        if not (L.get("value_low") or 0) <= (L.get("value_mid") or 0) <= (L.get("value_high") or 0) + 1:
            bad.append((L["name"], "label value"))
    for sh in g["shards"].values():
        for i, rev in sh.items():
            for where, r in _ranges({k: rev.get(k) for k in ("lines", "artist_total")}):
                vals = [r[k] for k in ("low", "mid", "high") if r.get(k) is not None]
                if vals != sorted(vals):
                    bad.append((i, where, r))
            w = rev["artist"].get("worth") or {}
            for where, r in _ranges({k: w.get(k) for k in ("recordings", "publishing", "artist_royalties")}):
                if not r["low"] <= r["mid"] <= r["high"]:
                    bad.append((i, "worth" + where, r))
    assert not bad, f"{len(bad)} ranges out of order, e.g. {bad[:3]}"


def test_shards_match_index(g):
    rows = {a["id"]: a for a in _merged(g)}
    in_shards = {}
    for n, sh in g["shards"].items():
        for i in sh:
            assert i in rows, f"shard {n}: {i} is not in the index"
            assert ord(i[1]) % 32 == n, f"{i} is in shard {n}; app.js looks in {ord(i[1]) % 32}"
            in_shards[i] = sh[i]
    assert set(in_shards) == set(rows), f"{len(set(rows) - set(in_shards))} artists have no detail shard"
    bad = []
    for i, rev in in_shards.items():
        a, w = rows[i], rev["artist"].get("worth")
        if w and a.get("worth_mid") is not None and abs(a["worth_mid"] - (w["recordings"]["mid"] + w["publishing"]["mid"])) > 1:
            bad.append((a["name"], "worth_mid", a["worth_mid"]))
        mids = {l["key"]: l["generated"]["mid"] for l in rev["lines"]}
        for k, v in (a.get("rev_lines") or {}).items():  # Spotify to the dollar, the rest to 3 significant figures
            if k not in mids or abs(v - mids[k]) > (1 if k == "spotify" else max(1, 0.006 * abs(mids[k]))):
                bad.append((a["name"], f"rev_lines.{k}", v, mids.get(k)))
        stream = sum(l["generated"]["mid"] for l in rev["lines"] if l["group"] == "Streaming")
        if a.get("streaming_mid") is not None and abs(a["streaming_mid"] - stream) > 1:
            bad.append((a["name"], "streaming_mid", a["streaming_mid"], stream))
        if rev.get("artist_total") and a.get("rev_total") and abs(a["rev_total"]["mid"] - rev["artist_total"]["mid"]) > 1:
            bad.append((a["name"], "rev_total", a["rev_total"]["mid"], rev["artist_total"]["mid"]))
    assert not bad, f"{len(bad)} index figures differ from the artist page's, e.g. {bad[:3]}"


def test_labels_rosters_in_index(g):
    ids = {a["id"] for a in g["index"]["artists"]}
    slugs = [L["slug"] for L in g["index"].get("labels", [])]
    assert len(slugs) == len(set(slugs)), "duplicate label addresses"
    for L in g["index"].get("labels", []):
        roster = [x if isinstance(x, str) else x.get("id") for x in L.get("artists", [])]
        assert set(roster) <= ids, f"{L['name']}: roster ids not in the index"


def test_flags_and_photos_on_disk(g):
    missing = set()
    for a in g["index"]["artists"]:
        for c in a.get("cc") or []:
            if not (SITE / "flags" / f"{c}.svg").exists():
                missing.add(f"flags/{c}.svg")
        if a.get("photo") and not (SITE / a["photo"]["file"]).exists():
            missing.add(a["photo"]["file"])
    assert not missing, f"{len(missing)} files missing, e.g. {sorted(missing)[:5]}"


def test_no_nan_or_bad_numbers(g):
    """_strict already refuses NaN/Infinity; this also catches negative listener counts and None ranks."""
    for a in g["index"]["artists"]:
        for k in ("ml", "cl", "daily"):
            v = a.get(k)
            assert v is None or (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0), f"{a['name']}: {k}={v}"


def test_static_pages_and_sitemap(g):
    prefix = "" if g["name"] == "hip_hop" else f"{g['name']}/"
    root = SITE / prefix if prefix else SITE
    sitemap = (SITE / "sitemap.xml").read_text() if (SITE / "sitemap.xml").exists() else ""
    as_of = g["index"].get("as_of")
    for a in g["index"]["artists"]:
        page = root / "a" / a["slug"] / "index.html"
        assert page.exists(), f"no static page for {a['name']}"
        assert f"https://tventy.se/music/{prefix}a/{a['slug']}/" in sitemap, f"{a['name']} not in the sitemap"
    for L in g["index"].get("labels", []):
        assert (root / "label" / L["slug"] / "index.html").exists(), f"no static page for {L['name']}"
    # one page in full: same title as the app's, the figures of the day, the data date
    a = g["index"]["artists"][0]
    html = (root / "a" / a["slug"] / "index.html").read_text()
    from src.static_pages import esc
    assert f"<title>{esc(a['name'])}: listeners, earnings and label · tventy music</title>" in html
    assert f"Data as of {as_of}" in html
    assert f'window.BOOT = "#/{prefix}a/{a["id"]}"' in html
    assert re.search(r'<script type="application/ld\+json">\{.*"@type": "MusicGroup"', html)
