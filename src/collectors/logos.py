"""Label and label-group logos from Wikimedia Commons (Wikidata's logo image, P154): free files only, mostly simple
text logos in the public domain (PD-textlogo). Kept small in site/logos/ with the licence and a link to the file
page for credit. registry/label_logos.csv lists name, Wikidata ID, Commons file and licence (researched).
"""
import csv
import json
from urllib.parse import quote

from ..config import DATA, REGISTRY, SITE
from ..http import get

LIST = REGISTRY / "label_logos.csv"
OUT = SITE / "logos"
INDEX = DATA / "label_logos.json"
WIDTH = 240


def slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def update() -> int:
    """Download the listed logos not yet stored; returns how many are stored."""
    if not LIST.exists():
        return 0
    OUT.mkdir(exist_ok=True)
    idx = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    with LIST.open() as f:
        for r in csv.DictReader(f):
            name, file = r["name"].strip(), (r.get("commons_file") or "").strip()
            if not file or name in idx:
                continue
            file = file.removeprefix("File:")
            ext = ".png"  # Commons renders SVG and other formats to PNG thumbnails
            url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(file)}?width={WIDTH}"
            resp = get(url)
            if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
                continue
            path = OUT / f"{slug(name)}{ext}"
            path.write_bytes(resp.content)
            idx[name] = {"file": f"logos/{path.name}", "licence": r.get("licence", ""), "qid": r.get("qid", ""),
                         "page": f"https://commons.wikimedia.org/wiki/File:{quote(file)}"}
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=0))
    return len(idx)


def load() -> dict:
    return json.loads(INDEX.read_text()) if INDEX.exists() else {}
