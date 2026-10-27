# Official national charts: what each site's terms allow

2026-10-27. Owner: "Yea": use the official national charts where their terms allow. Read for each site: its terms of
use (or legal notice, disclaimer, chart rules) and its robots.txt. Every page read is archived under
`raw/national_charts/terms/2026-10-27/` (gzip). Code: `src/collectors/national_charts.py`, step `natcharts`.

The rule applied: a chart is used only when robots.txt lets a general client read the chart pages, the site does not
turn our client away, and the published terms do not forbid automated reading or reuse beyond private use. Where a
site's robots.txt names Anthropic's or Claude's agents (ClaudeBot, Claude-Web, anthropic-ai) and disallows them, the
chart is refused too: this work is done with Claude.

## Verdicts

| Country | Chart | Verdict | Why (and where) |
|---|---|---|---|
| SE | Sverigetopplistan (IFPI Sverige) | **Allowed** | [robots.txt](https://sverigetopplistan.se/robots.txt) "Allow: /" for every agent; no terms of use on the site; the [rules page](https://sverigetopplistan.se/regler/) covers chart eligibility only. Credited "© IFPI Sverige". Singles top 100, albums top 60, hip-hop albums top 20, a year of weeks. |
| DK | Hitlisten.NU (IFPI Danmark, M&I Service) | **Allowed** | No robots.txt (404); no terms of use; the [about page](https://hitlisten.nu/default.asp?list=om) explains the method. Credited "© IFPI Danmark og M&I Service". Tracks top 40, albums top 40, a year of weeks. |
| FI | Suomen virallinen lista (IFPI Finland) | **Allowed to read; positions not shown** | [robots.txt](https://ifpi.fi/robots.txt) allows all. The [chart rules 2026](https://ifpi.fi/app/uploads/2026/08/Suomen-Virallinen-Lista-Saannot-heinakuu-2026_.pdf), 2.1: "Listan osittaisestakin julkaisusta on aina sovittava erikseen Musiikkituottajien kanssa" (even a partial publication of the list must be agreed with IFPI Finland). Used as an internal signal and a discovery source; no Finnish chart position appears on the site. Singles and albums top 50, a year of weeks. |
| NO | VG-lista (VG, IFPI Norge) | Refused | [VG's terms](https://www.vg.no/informasjon/brukervilkar) 7.1: no spiders, robots or crawling to collect information; 3.1: content for private, non-commercial use only. VG's robots.txt also blocks anthropic-ai. |
| NL | Dutch Top 40 (Stichting Nederlandse Top 40) | Refused | [Disclaimer](https://www.top40.nl/disclaimer): all published data are the Stichting's property (Databankenwet); no reproduction or publication without written permission. [robots.txt](https://www.top40.nl/robots.txt) disallows Claude-Web, ClaudeBot and anthropic-ai. |
| NL | Single Top 100 (dutchcharts.nl, Hung Medien) | Refused | The site answers 403 to our client; [robots.txt](https://dutchcharts.nl/robots.txt) disallows ClaudeBot and anthropic-ai and sets "ai-train=no". |
| BE | Ultratop (ultratop.be, Hung Medien) | Refused | Same as dutchcharts.nl: 403, and robots.txt disallows ClaudeBot and anthropic-ai. |
| AT | Ö3 Austria Top 40 (ORF) | Refused | [robots.txt](https://oe3.orf.at/robots.txt) disallows Claude-Web, ClaudeBot and anthropic-ai. austriancharts.at (Hung Medien): 403. |
| CH | Schweizer Hitparade (hitparade.ch, Hung Medien) | Refused | 403; robots.txt disallows ClaudeBot and anthropic-ai. |
| DE | Offizielle Deutsche Charts (GfK / MRC Data) | Refused | The site answers 403 ("Access Denied") even to robots.txt: it does not let our client read. |
| FR | SNEP | Refused | [Mentions légales](https://snepmusique.com/mentions-legales/) 5: any reproduction or publication of all or part of the site is forbidden without SNEP's prior written authorisation. robots.txt disallows ClaudeBot. |
| IT | FIMI | Not used | robots.txt allows all; the footer says "Tutti i diritti riservati" and forbids crawling for AI training. No permission to reuse is given, and Italy's list already reaches 100 from kworb, so it is not needed. |
| ES | PROMUSICAE (elportaldemusica.es) | Refused | [Aviso legal](https://www.elportaldemusica.es/site/aviso-legal) 10: any use other than strictly private needs PROMUSICAE's prior written authorisation; the top 100s are © Promusicae and AGEDI. |
| AU | ARIA | Refused | [Terms of use](https://www.aria.com.au/terms-of-use): no reproduction or publication without ARIA's written approval; the permission for statistical content expressly excludes "the ARIA Charts or any ARIA Charts data". |
| CA | Billboard Canadian Hot 100 | Refused | [Terms of use](https://www.pmc.com/terms-of-use) (PMC): no spidering, screen scraping or database scraping. Billboard's robots.txt disallows anthropic-ai and Claude-Web. |
| – | kworb.net mirrors | None to use | kworb mirrors iTunes, Apple Music, Shazam, Spotify, YouTube and Deezer charts per country, not the official national charts. |

## What is collected

- Each allowed chart's weekly page for the last 52 ISO weeks, archived once (`raw/national_charts/<cc>-<chart>/`,
  gzip) and never fetched again; a week not yet published has no rows and is not kept. One request every 2 seconds per
  site. The daily workflow runs `natcharts`: on most days nothing is new.
- `data/national_charts.csv`: country, chart, year, week, position, artist, title, and the site's own weeks-on-chart
  and peak where it prints them (Hitlisten; weeks only on the Finnish list).

## How it is used

1. **Signal** in the smaller-acts score (home charts, 15%): for an act from that country, on any of its official charts
   in the last 52 weeks: presence, best position (peak, against the chart's size) and the number of weeks. Matched by
   the Deezer artist IDs credited on the charted song (Deezer's own track credits, `data/chart_identities.csv`), else
   by exact folded name when no other artist shares it.
2. **Discovery**: every charted song is looked up on Deezer (artist and title must both match), and its credited
   artists' Deezer IDs go to Wikidata (P2722) and MusicBrainz (url relations). **A chart never gives a country**: the
   artist is kept only when Wikidata or MusicBrainz names one, and the genre rule decides the genre.
3. **On the page**: Sverigetopplistan and Hitlisten positions show in the "Home charts" column with their credit
   ("Sverigetopplistan #12, 8 wks"). Finnish chart presence counts in the score but is not shown.

## Follow-ups for the owner

- Ask IFPI Finland whether positions may be shown (credited, a few per artist).
- Ask Ultratop (Belgium) and the Stichting Nederlandse Top 40 for permission: Belgium and the Netherlands are short of
  100 and no other official chart covers them.
- Norway, Austria, Switzerland, Spain, Australia and Canada: no usable official chart. Spotify's weekly top 200 per
  country, Apple Music and Shazam stay the home-chart signal there.
