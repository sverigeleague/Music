"""Awards and nominations from Wikidata (CC0): P166 award received and P1411 nominated for, with the date (P585) and
the work honoured (P1686). Keeps the music awards people know: Grammy, BET, American Music, Billboard Music, MTV
(VMA, EMA), BRIT, Juno, ARIA, Latin Grammy, Victoires, Echo/Polaris and the like, grouped by family. Saved to
data/awards.json. Wikidata's coverage is uneven (big US awards are well entered, smaller ones less so): the site says
"as listed on Wikidata" and links the artist's item.
"""
import json
import re

from ..config import DATA
from .wikidata import query, qid

OUT = DATA / "awards.json"
FAMILIES = [("Grammy", r"\bgrammy\b(?!.*latin)"), ("Latin Grammy", r"latin grammy"), ("BET", r"\bbet\b"),
            ("American Music Awards", r"american music award"), ("Billboard Music Awards", r"billboard music award"),
            ("MTV", r"\bmtv\b"), ("BRIT", r"\bbrit award"), ("MOBO", r"\bmobo\b"), ("Juno", r"\bjuno award"),
            ("ARIA", r"\baria (music )?award"), ("Victoires de la musique", r"victoires? de la musique"),
            ("Polaris", r"polaris"), ("Mercury Prize", r"mercury prize"), ("Soul Train", r"soul train"),
            ("iHeartRadio", r"iheartradio"), ("NAACP Image", r"naacp image"), ("Pulitzer", r"pulitzer")]


def family(label: str) -> str | None:
    low = (label or "").lower()
    return next((f for f, pat in FAMILIES if re.search(pat, low)), None)


def update(spotify_ids: list[str]) -> int:
    out: dict[str, dict] = {}
    for chunk in [spotify_ids[i:i + 200] for i in range(0, len(spotify_ids), 200)]:
        v = " ".join(f'"{s}"' for s in chunk)
        rows = query(f"""
SELECT ?sp ?item ?kind ?award ?awardLabel ?date ?work ?workLabel WHERE {{
  VALUES ?sp {{ {v} }} ?item wdt:P1902 ?sp .
  {{ ?item p:P166 ?st . ?st ps:P166 ?award . BIND("win" AS ?kind) }} UNION
  {{ ?item p:P1411 ?st . ?st ps:P1411 ?award . BIND("nomination" AS ?kind) }}
  OPTIONAL {{ ?st pq:P585 ?date }} OPTIONAL {{ ?st pq:P1686 ?work }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")
        for r in rows:
            fam = family(r.get("awardLabel", ""))
            if not fam:
                continue
            d = out.setdefault(r["sp"], {"qid": qid(r["item"]), "wins": [], "nominations": []})
            e = {"award": r["awardLabel"], "family": fam, "year": (r.get("date") or "")[:4],
                 "work": r.get("workLabel") if r.get("work") else ""}
            lst = d["wins" if r["kind"] == "win" else "nominations"]
            if e not in lst:
                lst.append(e)
    for d in out.values():
        for k in ("wins", "nominations"):
            d[k].sort(key=lambda e: (e["year"] or "0"), reverse=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    return len(out)


def load() -> dict:
    return json.loads(OUT.read_text()) if OUT.exists() else {}
