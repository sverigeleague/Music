from src.collectors import certifications as c

DISCOGRAPHY = """The discography of American rapper [[Test Rapper]].
==Albums==
===Studio albums===
{| class="wikitable plainrowheaders" style="text-align:center;"
|+ List of studio albums
! scope="col" rowspan="2" | Title
! scope="col" rowspan="2" | Album details
! scope="col" colspan="3" | Peak chart positions
! scope="col" rowspan="2" | [[List of music recording certifications|Certifications]]
|-
! scope="col" | [[Billboard 200|US]]<br /><ref name="US">{{cite web|url=https://example.org
|title=Chart history}}</ref>
! scope="col" | [[UK Albums Chart|UK]]<br /><ref name="UK R&B/Hip-Hop"/>
! scope="col" | [[Canadian Albums Chart|CAN]]
|-
! scope="row" | ''[[First Album]]''
|
* Released: March 3, 2015
* Label: Test
| 1 || 4 || —
|
* [[Recording Industry Association of America|RIAA]]: 3× Platinum<ref name="RIAA">{{cite certification|region=United States|artist=Test Rapper|title=First Album}}</ref>
* [[British Phonographic Industry|BPI]]: Gold<ref>{{cite certification|region=United Kingdom|artist=Test Rapper}}</ref>
* [[Music Canada|MC]]: Platinum ×2
|-
! scope="row" | ''Second Album''
|
* Released: 2019
| 12 || — || 30{{efn|Charted on the [[Canadian Albums Chart]] only.}}
| RIAA: Gold<br />ARIA: 2x Platinum<br />IFPI DEN: Platinum<br />XYZ: Gold
|}

==Singles==
{| class="wikitable plainrowheaders"
! scope="col" rowspan="2" | Title
! scope="col" rowspan="2" | Year
! scope="col" colspan="2" | Peak chart positions
! scope="col" rowspan="2" | Certifications
! scope="col" rowspan="2" | Album
|-
! scope="col" | [[Billboard Hot 100|US]]
! scope="col" | [[UK Singles Chart|UK]]
|-
! scope="row" | "Big Song"<br />{{small|(featuring [[Someone]])}}
| rowspan="2" | 2016
| 2 || 7
|
* RIAA: Diamond<ref name="RIAA"/>
* BPI: 2× Platinum
* [[SNEP]]: Gold
| rowspan="2" | ''First Album''
|-
! scope="row" | "Small Song"
| 50 || 40
|
|-
! scope="row" | "Old Song"
| 1987
| 5 || —
| RIAA: Platinum
| Non-album single
|}
"""

ENTRIES = """{{Certification Table Top}}
{{Certification Table Entry|region=United States|type=single|title=Big Song|artist=Test Rapper|award=Platinum
|number=4|relyear=2016|certyear=2020}}
{{Certification Table Entry|region=Australia|type=album|title=First Album|award=Gold|relyear=2015}}
{{Certification Table Bottom}}"""


def _works(text):
    return {w["title"]: w for w in c.parse(text)}


def test_table_cells_with_refs_bullets_and_br():
    w = _works(DISCOGRAPHY)
    first = w["First Album"]
    assert first["type"] == "album" and first["year"] == "2015" and first["us_peak"] == 1
    assert first["certs"] == [
        {"body": "RIAA", "country": "US", "level": "Platinum", "multiplier": 3, "units": 3_000_000},
        {"body": "BPI", "country": "UK", "level": "Gold", "multiplier": 1, "units": 100_000},
        {"body": "MC", "country": "Canada", "level": "Platinum", "multiplier": 2, "units": None}]
    second = w["Second Album"]
    assert second["us_peak"] == 12 and second["year"] == "2019"
    assert [(x["body"], x["level"], x["multiplier"]) for x in second["certs"]] == [
        ("RIAA", "Gold", 1), ("ARIA", "Platinum", 2), ("IFPI Danmark", "Platinum", 1)]  # unknown XYZ dropped


def test_singles_rowspan_titles_and_units():
    w = _works(DISCOGRAPHY)
    big = w["Big Song"]
    assert big["type"] == "single" and big["year"] == "2016" and big["us_peak"] == 2
    assert [(x["body"], x["level"], x["multiplier"], x["units"]) for x in big["certs"]] == [
        ("RIAA", "Diamond", 1, 10_000_000), ("BPI", "Platinum", 2, 1_200_000), ("SNEP", "Gold", 1, None)]
    small = w["Small Song"]  # rowspan year carried; the album column did not shift into certifications
    assert small["year"] == "2016" and small["certs"] == [] and small["us_peak"] == 50
    old = w["Old Song"]  # singles before 1989 had other RIAA thresholds: no units
    assert old["certs"][0]["units"] is None and old["us_peak"] == 5


def test_certification_table_entry():
    w = c.parse(ENTRIES)
    assert {(x["title"], x["type"], x["certs"][0]["body"], x["certs"][0]["multiplier"], x["certs"][0]["units"])
            for x in w} == {("Big Song", "single", "RIAA", 4, 4_000_000), ("First Album", "album", "ARIA", 1, None)}


def test_level_forms():
    lv = lambda s: [(x["body"], x["level"], x["multiplier"]) for x in c.parse_certs(s, "single", "2020")]
    assert lv("RIAA: 3x Platinum") == [("RIAA", "Platinum", 3)]
    assert lv("RIAA: Platinum ×2") == [("RIAA", "Platinum", 2)]
    assert lv("[[RMNZ]]: 2&times; Platinum") == [("RMNZ", "Platinum", 2)]
    assert lv("BPI: Silver") == [("BPI", "Silver", 1)]
    assert lv("FRA: Diamond") == [("SNEP", "Diamond", 1)]  # a country code in place of the body
    assert lv("UK: 100,000") == []  # a sales figure, not a certification


def test_summary():
    s = c.summary({"works": c.parse(DISCOGRAPHY)})
    assert s["certified_works"] == 4  # Small Song has none
    assert s["riaa_platinum_units"] == 3 + 10 + 1  # Gold is not counted
    assert s["by_country"]["US"] == 4 and s["by_country"]["UK"] == 2


# ---------- French and German Wikipedia ----------

from src.collectors import certifications_frde as f

FR_TEMPLATES = """== Albums ==
{{Discographie des albums
| pays1 = {{drapeau|France}} [[Syndicat national de l'édition phonographique|FRA]]
| titre1 = ''[[Comme prévu]]''
| détails1 = * Sortie : 8 septembre 2017
* Label : Rec.118
| position1 = 78;3
| certif1 = {{Drapeau|France}}{{Certification|Diamant}}<ref name="SNEP">{{Lien web|url=http://snepmusique.com|titre=SNEP}}</ref>
| titre2 = ''[[Destin (album)|Destin]]''
| détails2 = * Sortie : {{date|22|mars|2019|en musique}}
| certif2 = {{Drapeau|France}} {{certification|Diamant|2}}<ref name="SNEP"/><br>{{Drapeau|Belgique}} {{certification|or}}
| titre3 = ''Sans certif''
| certif3 = —
| titre4 = ''Seul''
| détails4 = * Sortie : 2023
| certif4 = {{Certification|Platine|3}}<ref>{{Lien web|url=https://snepmusique.com}}</ref>
}}
== Chansons ==
=== Singles ===
{{Discographie des chansons
| pays1 = [[France|FR]]
| titre1 = ''Miroir''
| année1 = 2015
| annéen1 = 2
| titre2 = ''Malcolm''
| certif2 = {{Drapeau|France}} {{Certification|Platine}}
| titre3 = ''Roro''
| année3 = 2017
| certif3 = {{Drapeau|France}} {{Certification|Or}}
}}
"""

FR_TABLE = """=== Singles ===
{| class="wikitable"
! rowspan="2" |Année
! rowspan="2" |Titre
! colspan="2" |Meilleure position
! rowspan="2" |[[Disque de certification#France|Certifications]]
|-
! {{Drapeau|France}} FRA
! {{Drapeau|Suisse}} SUI
|-
| rowspan="2" | 2018
| style="text-align:left;"|''Sapés comme jamais'' <small>(feat. [[Niska]])</small>
| 2 || 30
|
* {{France}} ([[Syndicat national de l'édition phonographique|SNEP]]) : {{Certification|Diamant}}<ref name="SNEP"/>
* {{Suisse}} : {{Certification|Or}}
|-
| style="text-align:left;"|''Bella''
| 1 || 5
| FRA : {{Certification|platine|2}}
|}

=== Titres certifiés ===
* ''Ocho''
** ''Yakalelo'' : {{drapeau|France}}  {{Certification|Diamant}}
** ''Titulaires'' <small>(feat. [[Koba LaD]])</small> : {{drapeau|France}} {{Certification|Or}}
"""

DE_CHARTS = """== Alben ==
=== Studioalben ===
{{Charttabelle
|DE|AT|CH|US
| Art = Alben
| INHALT =
{{Charteintrag
|DE|AT|CH|US
| Jahr = 2017
| Titel = [[Makarov Komplex]]
| POS_DE = 2 | WO_DE = 8 | A_DE = G
| POS_AT = 1 | WO_AT = 3
| Titel2 = [[Blyat]]
| POS_DE2 = 3 | A_DE2 = 3P
| POS_AT2 = 3 | A_AT2 = D+5P
| POS_US2 = 40
}}
}}
== Singles ==
=== Als Leadmusiker ===
{{Charttabelle
|DE|AT|CH
| Art = Singles
| INHALT =
{{Charteintrag
|DE|AT|CH
| Jahr = 2018
| Titel = Spielplatz <sup>A, P</sup>
| POS_DE = 51 | A_DE = G (Single) + G (Streaming)
| POS_CH = 70 | A_CH = P
| Titel2 = Ohne Auszeichnung
| POS_DE2 = 90
}}
{{Charteintrag
|DE|FR
| Jahr = 2020
| Titel = Ciao
| POS_FR = 1 | A_FR = D
| A_BEW = G
}}
}}
"""


def _fr(text):
    return {w["title"]: w for w in f.parse("fr", text)}


def _lv(w):
    return [(x["body"], x["multiplier"], x["level"]) for x in w["certs"]]


def test_fr_discographie_templates():
    w = _fr(FR_TEMPLATES)
    assert set(w) == {"Comme prévu", "Destin", "Seul", "Malcolm", "Roro"}  # uncertified and "—" left out
    assert w["Comme prévu"]["type"] == "album" and w["Comme prévu"]["year"] == "2017"
    assert w["Comme prévu"]["certs"] == [
        {"body": "SNEP", "country": "France", "level": "Diamond", "multiplier": 1, "units": None}]
    assert _lv(w["Destin"]) == [("SNEP", 2, "Diamond"), ("BEA", 1, "Gold")] and w["Destin"]["year"] == "2019"
    assert _lv(w["Seul"]) == [("SNEP", 3, "Platinum")]  # a certification without a flag is SNEP's
    assert w["Malcolm"]["type"] == "single" and w["Malcolm"]["year"] == "2015"  # année1 carried down
    assert w["Roro"]["year"] == "2017" and _lv(w["Roro"]) == [("SNEP", 1, "Gold")]
    assert all(x["us_peak"] is None for x in w.values())


def test_fr_wikitable_year_first_and_lists():
    w = _fr(FR_TABLE)
    s = w["Sapés comme jamais (feat. Niska)"]  # the title column, not the year column; the rowspan year carried
    assert s["type"] == "single" and s["year"] == "2018"
    assert _lv(s) == [("SNEP", 1, "Diamond"), ("IFPI Switzerland", 1, "Gold")]
    assert _lv(w["Bella"]) == [("SNEP", 2, "Platinum")] and w["Bella"]["year"] == "2018"  # "FRA :" code kept
    assert _lv(w["Yakalelo"]) == [("SNEP", 1, "Diamond")] and w["Yakalelo"]["type"] == "single"
    assert "Titulaires" in w


def test_de_charteintrag():
    w = {(x["title"], x["type"]): x for x in f.parse("de", DE_CHARTS)}
    assert set(w) == {("Makarov Komplex", "album"), ("Blyat", "album"), ("Spielplatz", "single"),
                      ("Ciao", "single")}
    assert _lv(w["Makarov Komplex", "album"]) == [("BVMI", 1, "Gold")] and w["Makarov Komplex", "album"]["year"] == "2017"
    b = w["Blyat", "album"]
    assert _lv(b) == [("BVMI", 3, "Platinum"), ("IFPI Austria", 1, "Diamond"), ("IFPI Austria", 5, "Platinum")]
    assert b["us_peak"] == 40 and b["certs"][0]["units"] is None
    assert _lv(w["Spielplatz", "single"]) == [("BVMI", 1, "Gold"), ("IFPI Switzerland", 1, "Platinum")]
    assert _lv(w["Ciao", "single"]) == [("SNEP", 1, "Diamond"), ("BEA", 1, "Gold")]


def test_de_award_codes():
    assert f.de_award("G") == [("Gold", 1)]
    assert f.de_award("8P") == [("Platinum", 8)]
    assert f.de_award("D+5P") == [("Diamond", 1), ("Platinum", 5)]
    assert f.de_award("S") == [("Silver", 1)]
    assert f.de_award("") == [] and f.de_award("—") == []


def test_entries_pick_the_wiki_and_record_it(monkeypatch):
    pages = {("fr", "Ninho"): FR_TEMPLATES, ("de", "Ninho/Diskografie"): DE_CHARTS,
             ("de", "Ninho"): "{{Eingebundene Diskografie|Ninho/Diskografie|Überschrift=Alben}}"}
    monkeypatch.setattr(f, "wikidata_pages", lambda qids, lang: ({"Q1": "Ninho"}, {}))
    monkeypatch.setattr(c, "page", lambda t, refresh=False, lang="en": (t, pages[lang, t]) if (lang, t) in pages
                        else None)
    e = f.entries({"sp1": "Q1"}, "2026-10-25")["sp1"]
    assert e["lang"] == "de" and e["page"] == "Ninho/Diskografie"  # 8 certifications against 6: German
    assert e["url"] == "https://de.wikipedia.org/wiki/Ninho/Diskografie"
    pages["fr", "Ninho"] = FR_TEMPLATES + FR_TABLE  # now more on the French page
    e = f.entries({"sp1": "Q1"}, "2026-10-25")["sp1"]
    assert e["lang"] == "fr" and e["url"] == "https://fr.wikipedia.org/wiki/Ninho" and e["fetched"] == "2026-10-25"


def test_riaa_latin_awards_are_kept_apart():
    from src.collectors import certifications as c
    latin = c.parse_certs("* RIAA: 96× Platinum {{small|(Latin)}}", "single", "2018")[0]
    linked = c.parse_certs("RIAA: 34× Platinum ([[RIAA certification#Singles|Latin]])", "single", "2014")[0]
    assert latin["latin"] and linked["latin"] and latin["units"] is None
    main = c.parse_certs("RIAA: 3× Platinum", "single", "2014")[0]
    assert "latin" not in main and main["units"] == 3_000_000
    entry = {"works": [{"certs": [latin]}, {"certs": [main]}]}
    assert c.summary(entry)["riaa_platinum_units"] == 3
