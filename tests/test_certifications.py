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
! scope="col" | [[UK Albums Chart|UK]]<br /><ref name="UK"/>
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
    assert lv("UK: 100,000") == []  # a sales figure, not a certification


def test_summary():
    s = c.summary({"works": c.parse(DISCOGRAPHY)})
    assert s["certified_works"] == 4  # Small Song has none
    assert s["riaa_platinum_units"] == 3 + 10 + 1  # Gold is not counted
    assert s["by_country"]["US"] == 4 and s["by_country"]["UK"] == 2
