"""Country names as the registry holds them (Wikidata's English labels) -> ISO 3166-1 alpha-2 codes, for the flags in
the site's lists. A name not listed here gets no flag; the name itself is still shown on the artist page."""

ISO2 = {
    "United States": "us", "France": "fr", "Germany": "de", "United Kingdom": "gb", "Italy": "it", "Canada": "ca",
    "Poland": "pl", "Russia": "ru", "Turkey": "tr", "Netherlands": "nl", "Brazil": "br", "Australia": "au",
    "Sweden": "se", "Belgium": "be", "Japan": "jp", "India": "in", "Philippines": "ph", "Morocco": "ma",
    "Czech Republic": "cz", "Indonesia": "id", "South Korea": "kr", "Nigeria": "ng", "South Africa": "za",
    "Spain": "es", "Greece": "gr", "Democratic Republic of the Congo": "cd", "Serbia": "rs", "Kosovo": "xk",
    "Denmark": "dk", "Norway": "no", "Vietnam": "vn", "Algeria": "dz", "Switzerland": "ch", "Ukraine": "ua",
    "Egypt": "eg", "Israel": "il", "Mexico": "mx", "Azerbaijan": "az", "Albania": "al", "Finland": "fi",
    "Bosnia and Herzegovina": "ba", "Ireland": "ie", "Ivory Coast": "ci", "Kazakhstan": "kz", "Armenia": "am",
    "New Zealand": "nz", "Thailand": "th", "Belarus": "by", "Romania": "ro", "Guatemala": "gt", "Madagascar": "mg",
    "Slovenia": "si", "Argentina": "ar", "Venezuela": "ve", "Northern Ireland": "gb", "Chad": "td", "Georgia": "ge",
    "Trinidad and Tobago": "tt", "The Gambia": "gm", "Portugal": "pt", "Austria": "at", "Palestine": "ps",
    "Zambia": "zm", "East Germany": "de", "China": "cn", "Jamaica": "jm", "Pakistan": "pk", "Estonia": "ee",
    "Kyrgyzstan": "kg", "Haiti": "ht", "Iran": "ir", "Malaysia": "my", "Latvia": "lv", "Colombia": "co",
    "Puerto Rico": "pr", "Dominican Republic": "do", "Cuba": "cu", "Ghana": "gh", "Senegal": "sn", "Cameroon": "cm",
    "Lithuania": "lt", "Croatia": "hr", "Hungary": "hu", "Slovakia": "sk", "Bulgaria": "bg", "Chile": "cl",
    "Peru": "pe", "Tunisia": "tn", "Lebanon": "lb", "Iraq": "iq", "Syria": "sy", "Somalia": "so", "Ethiopia": "et",
    "Kenya": "ke", "Uganda": "ug", "Tanzania": "tz", "Angola": "ao", "Mali": "ml", "Guinea": "gn", "Barbados": "bb",
    "Bahamas": "bs", "Iceland": "is", "Luxembourg": "lu", "Moldova": "md", "North Macedonia": "mk",
    "Montenegro": "me", "Uzbekistan": "uz", "Mongolia": "mn", "Taiwan": "tw", "Hong Kong": "hk", "Singapore": "sg",
}
# a place entered instead of a country (see wikidata.COUNTRY_NAMES)
FIX = {"Karachi": "Pakistan", "Cina": ""}


def name(country: str) -> str:
    return FIX.get(country, country)


def codes(country: str) -> list[str]:
    """'Canada / United States' -> ['ca', 'us']; unknown names are skipped."""
    out = []
    for c in (country or "").split(" / "):
        cc = ISO2.get(name(c.strip()))
        if cc and cc not in out:
            out.append(cc)
    return out
