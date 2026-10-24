"""Pages search engines can find and link previews can show (owner, 2026-10-24, D2 and D3).

The site itself is one page with hash routes (#/a/<id>), which search engines do not index and which unfurl with the
site's generic preview. At each build this writes, beside it:
- site/a/<slug>/index.html for every artist and site/label/<slug>/index.html for every label: the page's own title,
  description, canonical address, Open Graph and Twitter tags, JSON-LD (MusicGroup / Organization) and a short
  readable summary. The full app loads on top and opens that artist or label (window.BOOT), so a visitor sees the same
  page as on the site;
- site/cards/<slug>.png: a 1200x630 card per artist (rank, listeners, Scout tier, label, earnings range, date), used as
  the link-preview image and offered as a download;
- site/sitemap.xml and site/robots.txt.
All of it is generated at deploy (gitignored), like site/data.
"""
import html
import json
import re
from pathlib import Path

from .config import SITE

BASE = "https://tventy.se/music/"
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
esc = lambda s: html.escape(str(s or ""), quote=True)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"[$]", "s", (name or "").casefold())).strip("-") or "artist"


def assign_slugs(artists: list[dict]) -> None:
    seen: dict[str, int] = {}
    for a in sorted(artists, key=lambda a: -(a.get("ml") or 0)):  # the bigger artist keeps the plain name
        s = slugify(a["name"])
        if s in seen:
            s = f"{s}-{a['id'][:6].lower()}"
        seen[s] = 1
        a["slug"] = s


def _count(n) -> str:
    if n is None:
        return "–"
    n = float(n)
    return f"{n / 1e9:.2f}bn" if n >= 1e9 else f"{n / 1e6:.1f}m" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else f"{n:.0f}"


def _usd(n) -> str:
    return "$" + _count(n) if n is not None else "–"


def _shell(title: str, desc: str, url: str, image: str | None, ld: dict, boot: str, body: str) -> str:
    img = f'<meta property="og:image" content="{esc(image)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{esc(image)}">' if image else '<meta name="twitter:card" content="summary">'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<base href="../../">
<title>{esc(title)} · tventy music</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:site_name" content="tventy music"><meta property="og:type" content="profile">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}">
{img}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<link rel="stylesheet" href="styles.css">
<script>window.BOOT = {json.dumps(boot)};</script>
</head>
<body>
<header><div class="wrap bar">
  <span class="brandbox"><a class="brand" href="#/">tventy</a><a class="section" href="https://tventy.se/sport/" title="Go to tventy sport">music</a></span>
  <div class="search" role="search"><input id="q" type="search" placeholder="Search artists and labels" autocomplete="off" aria-label="Search" aria-controls="q-results" aria-expanded="false"><div class="results" id="q-results" role="listbox" hidden></div></div>
  <nav class="seg main mainnav" aria-label="Section"><a class="segbtn" href="#/" id="nav-artists">Artists</a><a class="segbtn" href="#/scout" id="nav-scout">Scout</a><a class="segbtn" href="#/worth" id="nav-money">Money</a><a class="segbtn" href="#/labels" id="nav-labels">Labels</a></nav>
</div></header>
<div class="wrap"><nav class="crumbs" id="crumbs" aria-label="Breadcrumb"></nav><main id="app">{body}</main></div>
<footer class="wrap note" id="foot"></footer>
<script type="module" src="app.js"></script>
</body>
</html>
"""


def artist_page(a: dict, as_of: str) -> tuple[str, str]:
    url = f"{BASE}a/{a['slug']}/"
    tier = (a.get("scout") or {}).get("tier")
    rank = f"#{a['cl_rank']} in hip-hop by current listeners" if a.get("cl_rank") else f"#{a['rank']} in hip-hop by monthly listeners"
    label = a.get("label_name") or ""
    keeps = a.get("rev_total") or {}
    desc = (f"{a['name']}: {_count(a['ml'])} monthly listeners on Spotify, {rank}"
            f"{f', on {label}' if label else ''}{f', Scout tier {tier}' if tier else ''}. What the music earns, who owns it "
            f"and how the artist is moving, every figure sourced. Data as of {as_of}.")
    facts = [f"<li>Monthly listeners: {_count(a['ml'])}</li>", f"<li>{esc(rank)}</li>"]
    if label:
        facts.append(f"<li>Label: {esc(label)}{' (' + esc(a.get('label_owner')) + ')' if a.get('label_owner') and a.get('label_owner') != label else ''}</li>")
    if a.get("scout"):
        facts.append(f"<li>Scout score: {a['scout']['score']}{' (' + esc(tier) + ')' if tier else ''}</li>")
    if keeps.get("mid"):
        facts.append(f"<li>Keeps from streaming: about {_usd(keeps['mid'])} a year ({_usd(keeps.get('low'))}–{_usd(keeps.get('high'))}, estimate)</li>")
    if (a.get("top_fresh") or {}).get("title"):
        facts.append(f"<li>Newest hit: {esc(a['top_fresh']['title'])}</li>")
    if a.get("awards"):
        facts.append(f"<li>Awards listed on Wikidata: {a['awards']['wins']} won</li>")
    body = f"""<article class="static"><h1>{esc(a['name'])}</h1><p class="sub">{esc(desc)}</p><ul>{''.join(facts)}</ul>
<p><a href="#/a/{esc(a['id'])}">Open the full page</a></p></article>"""
    ld = {"@context": "https://schema.org", "@type": "MusicGroup", "name": a["name"], "url": url, "genre": "Hip hop",
          "sameAs": [f"https://open.spotify.com/artist/{a['id']}"]}
    return url, _shell(f"{a['name']}: listeners, earnings and label", desc, url, f"{BASE}cards/{a['slug']}.png", ld, f"#/a/{a['id']}", body)


def label_page(L: dict, as_of: str) -> tuple[str, str]:
    url = f"{BASE}label/{L['slug']}/"
    n = len(L.get("artists", []))
    desc = (f"{L['name']}{', owned by ' + L['parent'] if L.get('parent') and L['parent'] != L['name'] else ''}: {n} artists in "
            f"hip-hop's top 1,000 with {_count(L.get('ml'))} combined monthly listeners. Roster, momentum and finances, every "
            f"figure sourced. Data as of {as_of}.")
    body = f"""<article class="static"><h1>{esc(L['name'])}</h1><p class="sub">{esc(desc)}</p>
<p><a href="#/label/{esc(L['slug'])}">Open the full page</a></p></article>"""
    ld = {"@context": "https://schema.org", "@type": "Organization", "name": L["name"], "url": url}
    if L.get("parent") and L["parent"] != L["name"]:
        ld["parentOrganization"] = {"@type": "Organization", "name": L["parent"]}
    return url, _shell(f"{L['name']}: roster, momentum and finances", desc, url, None, ld, f"#/label/{L['slug']}", body)


def card(a: dict, as_of: str, path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(im)
    bold, reg = str(FONTS / "Bricolage-Bold.ttf"), str(FONTS / "Bricolage-Regular.ttf")
    f = lambda path, size: ImageFont.truetype(path, size)
    d.text((64, 52), "tventy", font=f(bold, 40), fill="white")
    d.text((64, 96), "music", font=f(reg, 22), fill=(163, 168, 177))
    name = a["name"]
    size = 104
    while size > 48 and d.textlength(name, font=f(bold, size)) > W - 128:
        size -= 6
    d.text((64, 170), name, font=f(bold, size), fill="white")
    rank = f"#{a['cl_rank']} in hip-hop by current listeners" if a.get("cl_rank") else f"#{a['rank']} in hip-hop by monthly listeners"
    d.text((64, 170 + size + 18), rank, font=f(reg, 34), fill=(163, 168, 177))
    tier = (a.get("scout") or {}).get("tier")
    keeps = (a.get("rev_total") or {}).get("mid")
    stats = [("Monthly listeners", _count(a["ml"])), ("Scout", f"{a['scout']['score']}{' ' + tier if tier else ''}" if a.get("scout") else "–"),
             ("Keeps / year, est.", f"~{_usd(keeps)}" if keeps else "–"), ("Label", a.get("label_name") or "–")]
    x, y, colw = 64, 430, (W - 128) // 4
    for i, (k, v) in enumerate(stats):
        cx = x + i * colw
        d.rectangle([cx, y, cx + colw - 16, y + 120], outline=(42, 45, 51), width=2)
        d.text((cx + 18, y + 16), k.upper(), font=f(reg, 18), fill=(163, 168, 177))
        vs = 40
        while vs > 20 and d.textlength(v, font=f(bold, vs)) > colw - 52:
            vs -= 2
        d.text((cx + 18, y + 54), v, font=f(bold, vs), fill="white")
    d.text((64, H - 52), f"Data as of {as_of} · estimates are ranges · tventy.se/music", font=f(reg, 20), fill=(163, 168, 177))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG", optimize=True)


def build(data: dict, cards: bool = True) -> dict:
    as_of = data.get("as_of") or ""
    urls = [BASE]
    for sub in ("a", "label"):
        root = SITE / sub
        if root.exists():
            for old in root.glob("*/index.html"):
                old.unlink()
    for a in data["artists"]:
        url, page = artist_page(a, as_of)
        out = SITE / "a" / a["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)
        urls.append(url)
        if cards:
            card(a, as_of, SITE / "cards" / f"{a['slug']}.png")
    for L in data.get("labels", []):
        url, page = label_page(L, as_of)
        out = SITE / "label" / L["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)
        urls.append(url)
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{esc(u)}</loc><lastmod>{esc(as_of)}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n")
    return {"pages": len(urls), "cards": len(data["artists"]) if cards else 0}
