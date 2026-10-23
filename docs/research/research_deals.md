# Non-streaming income research: method and gaps

File: `research_deals.csv` (68 rows, 29 artists). Research done 2026-10-23.

## Method
- Web searches, artist by artist and topic by topic: record deals, publishing and catalog sales, brands, show and feature fees, merch, Forbes lists. Where I could, I opened the articles themselves (MBW, Music Week, Billboard FR, RTBF, Complex, Revolt) to confirm dates and wording.
- Forbes.com refuses automated fetches (HTTP 403). Forbes figures therefore come from search-indexed Forbes snippets and a full repost of the 2025 list. The `source_url` field still points at the Forbes article.
- One primary document was read directly: the Starco Brands FY2024 10-K on SEC EDGAR (the Cardi B / Whipshots terms).
- **Grades:**
  - **A:** the figure or term comes from a primary document, such as a court filing, an SEC filing or a company statement. When the URL is an outlet's write-up of that document, `source_note` says so.
  - **B:** a named reputable outlet reporting the figure. This includes Forbes estimates relayed by Complex or PC Gamer.
  - **C:** the artist's own claim, a TMZ report, or an unconfirmed trade rumor.
- **Exclusions:**
  - No net-worth figures and no Celebrity Net Worth or SEO sites.
  - Figures that only appeared on content-farm pages were dropped. Examples: Ice Spice "$3M deal", Lil Baby "$4M deal" and Nike/Adidas numbers, OVO "$50M sales", Kendrick "Amex" numbers.
- `amount_usd` is left blank wherever no USD figure was reported. Euro amounts stay in `amount_note` and are not converted. Ranges and "high eight figures" wording are not turned into a number.

## Caveats
- **Forbes:**
  - Forbes published no musician earnings lists for 2023 or 2024. Its Feb-2023 "highest-paid entertainers" top 10, covering 2022 earnings, has no artist from this roster.
  - The only in-scope list is the 2025 one (published 2025-12-30): Kendrick $109M, Drake $78M, Post Malone $62M, Tyler $53M. Travis Scott is not in its top 25.
  - Rank numbers differ by 1 between secondary reprints.
  - No 2026 list had been published as of this research.
- **Headline figures that are not confirmed:** Drake/UMG ($400M) and Drake/Stake ($100M/yr) are both estimates. The first comes from anonymous Variety sources and the second from FT sources. Neither was confirmed by the parties.
- **Not artist income** (kept as context rows, labeled in `amount_note`):
  - Adidas Yeezy inventory revenue
  - Gap sales projections
  - Lil Wayne's sale of the Young Money masters to UMG
  - Dr. Dre's catalog sale to Shamrock
- **Super Bowl halftime:** performers get no fee, only union scale (about $1,000). This is noted for Kendrick (2022 and 2025) and Eminem (2022).
- **Court rows** (Megan v. 1501, Offset v. QC, Drake v. UMG, Cardi B v. KSR) are allegations or claimed damages, not income received. I did not pull the dockets themselves.

## Gaps (nothing citable found, 2020-2026)
- **No credible deal, brand or fee items found:** Don Toliver, Playboi Carti, The Kid LAROI, BIA, Aitch, Yung Lean, Yeat, DaBaby, bbno$, Quavo, Cardi-era Atlantic terms, Latto, Lil Tecca, Theodora.
  - Most have only label credits or fan-wiki claims.
  - Don Toliver's Cactus Jack/Atlantic JV dates from 2018, before the window.
  - Theodora runs her own Boss Lady Records (2024), but I found no reputable trade report on it.
- **Brands with no reported figure:** Drake/Nike NOCTA, Tyler/Converse, Post Malone/Bud Light, Cardi B/Reebok, Ice Spice/Dunkin'.
- **Tour merch totals:** none found for Drake, Kendrick, Tyler or Carti. The only merch figures are Travis Scott's per-night records and Kanye's Donda and Vultures numbers.
- **Documented show fees:** none in court records for these artists in 2020-2026. The only fee figures are self-reported: Kanye's $8M per show and Lil Baby's verse rate.
- **Publishing and catalog:**
  - Future's 2022 sale is the only verified catalog sale by an artist on this roster.
  - Ty Dolla $ign's PULSE publishing deal is undated.
  - Gunna's Kobalt renewal appeared only on ROSTR, so it was excluded.
- **Suggested next steps:**
  - Read the court dockets directly through PACER and Harris County records.
  - Check the Starco FY2025 10-K for updated Whipshots terms.
  - Retrieve the Billboard Pro article on Alemán and Homegrown Mafia to get its date.
