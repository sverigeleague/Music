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


def update(spotify_ids: list[str] | dict[str, str]) -> int:
    """Re-reads these artists; other artists' stored entries (another genre's run) are kept. Given {spotify_id: qid},
    the stored Wikidata item is used (it may come from MusicBrainz when Wikidata lacks the Spotify ID); otherwise
    the item is found by its Spotify ID (P1902)."""
    qids = spotify_ids if isinstance(spotify_ids, dict) else {}
    spotify_ids = list(spotify_ids)
    out: dict[str, dict] = {k: v for k, v in load().items() if k not in set(spotify_ids)}
    for chunk in [spotify_ids[i:i + 200] for i in range(0, len(spotify_ids), 200)]:
        by_q = {qids[s]: s for s in chunk if qids.get(s)}
        v = " ".join(f'"{s}"' for s in chunk if not qids.get(s))
        known = " ".join(f'(wd:{q} "{s}")' for q, s in by_q.items())
        rows = query(f"""
SELECT ?sp ?item ?st ?kind ?award ?awardLabel ?date ?work ?workLabel WHERE {{
  {{ VALUES (?item ?sp) {{ {known} }} }} UNION {{ VALUES ?sp {{ {v} }} ?item wdt:P1902 ?sp . }}
  {{ ?item p:P166 ?st . ?st ps:P166 ?award . BIND("win" AS ?kind) }} UNION
  {{ ?item p:P1411 ?st . ?st ps:P1411 ?award . BIND("nomination" AS ?kind) }}
  OPTIONAL {{ ?st pq:P585 ?date }} OPTIONAL {{ ?st pq:P1686 ?work }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")
        # one statement can carry several dates and several works with nothing pairing them; the query returns every
        # date x work combination (Jay-Z: 7 x 7 rows for one Grammy statement), so rows are grouped per statement
        stmts: dict[str, dict] = {}
        for r in rows:
            fam = family(r.get("awardLabel", ""))
            if not fam:
                continue
            g = stmts.setdefault(r["st"], {"sp": r["sp"], "item": r["item"], "kind": r["kind"], "award": r["awardLabel"],
                                           "family": fam, "years": set(), "works": set()})
            if r.get("date"):
                g["years"].add(r["date"][:4])
            if r.get("work"):
                g["works"].add(r.get("workLabel") or "")
        for g in stmts.values():
            d = out.setdefault(g["sp"], {"qid": qid(g["item"]), "wins": [], "nominations": []})
            years, works = sorted(g["years"]), sorted(g["works"])
            if len(years) > 1 and len(works) > 1:  # unpaired: one entry per year, the works named together
                entries = [(y, "") for y in years]
            elif len(years) > 1:
                entries = [(y, works[0] if works else "") for y in years]
            else:
                entries = [(years[0] if years else "", w) for w in (works or [""])]
            lst = d["wins" if g["kind"] == "win" else "nominations"]
            for y, w in entries:
                e = {"award": g["award"], "family": g["family"], "year": y, "work": w}
                if e not in lst:
                    lst.append(e)
    for d in out.values():
        for k in ("wins", "nominations"):
            d[k].sort(key=lambda e: (e["year"] or "0"), reverse=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    return sum(1 for k in out if k in set(spotify_ids))


def load() -> dict:
    return json.loads(OUT.read_text()) if OUT.exists() else {}
