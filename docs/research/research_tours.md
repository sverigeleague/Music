# Hip-hop touring dataset: method and caveats (as of 2026-10-23)

Companion to `research_tours.csv` (116 rows, all 100 artists, at least one row each).

## Method
- **Grade A sources (primary):** Billboard Boxscore and Pollstar.
  - Billboard year-end 2025 "Year in Touring" PDF and Midyear 2026 PDF.
  - Billboard year-end rap, country and R&B lists for 2023, 2024 and 2025.
  - Billboard monthly Boxscore reports from Jan to Aug 2026.
  - Billboard tour-wrap articles (Travis Scott, Cardi B, Post Malone/Jelly Roll, $uicideboy$).
  - Billboard's all-time top-25 rap touring acts list (2026-09-10), used for context only.
  - Pollstar year-end and mid-year pieces, including the Top-10 profiles and the Ye Soldier Field report.
- **Grade B:** Reputable press citing those sources. The only B figure is Touring Data via XXL, which appears in the Kendrick Lamar note.
- **Grade C:** Social-media or uncited figures, included only where nothing better exists, and labelled as such:
  - Drake $320.5M, which comes from a Genius Instagram post.
  - Drake Anita Max Win and Ice Spice Y2K!, which are uncited Wikipedia infobox figures.
  - Ye Istanbul, which is an organizer claim relayed by The Source.
- **Blank cells mean not reported.** `avg_ticket_usd` is computed as gross/tickets unless the source reported it (Pollstar), and every computed value says so in `source_note`.
- **Two sums of Billboard windows are my calculations and are flagged:**
  - Kendrick Lamar: YE2025 + midyear 2026.
  - YoungBoy: YE2025 + midyear 2026. It cross-checks against Wikipedia ($69.8M, 42 shows).
- **Search coverage.** I used about 60 web searches and many direct page reads, plus Wikipedia raw text for dates and show counts. Wikipedia numbers were used only when they cite Billboard or Pollstar.

## Key caveats
- **Window figures vs. full tours.** Billboard year-end charts cover Oct 1 to Sep 30, and 2023 covers Nov 1, 2022 to Sep 30, 2023. Many rows are window totals, not full-tour totals, and the note always says which. Overlapping rows are marked "do not sum": Jelly Roll 2024 and 2025, and the $uicideboy$ 2024 window.
- **Billboard and Pollstar disagree on several tours.** They use different chart years and different estimates:
  - Kendrick & SZA: $392.8M by my Billboard sum, $358.7M from Pollstar, $390.7M from Touring Data.
  - Post Malone 2025: $231.1M from Billboard, $197.8M from Pollstar.
  - Drake 2023: $184.9M from Pollstar, $140.9M from Billboard reported shows.
- **Co-headline tours:** Kendrick/SZA, Drake/21 Savage (and J. Cole in 2024), Future/Metro Boomin, and Wiz Khalifa/Snoop Dogg. The gross is listed once under the first artist, with `co_headliner` filled. The other artists' rows point back to it, so tours aren't double-counted. Splits are unknown.
- **Reporting is voluntary.** "None reported" means no reported box office was found. It does not mean the artist did not tour. Many artists' absence from Billboard's year-end rap top 10 sets an upper bound if they reported at all: $14.9M for 2025, $23.4M for 2024, and $16.9M for the midyear 2026 top 5. Examples are Playboi Carti, GloRilla, Doechii, Gunna, Lil Baby's WHAM tour, 21 Savage and the Kid LAROI. These thresholds are in the notes and are not used as figures.

## Gaps
- **Drake's 2024 "Big as the What?" leg with J. Cole** has no reported gross. Only the 2023 leg has A-grade data, and the full-tour $320.5M is grade C.
- **In-progress 2026 tours with no totals yet:**
  - J. Cole, The Fall-Off Tour. Billboard gives only an August 2026 range of $33–40M.
  - Don Toliver, Octane/Nitrous.
  - A$AP Rocky, Don't Be Dumb.
  - Doja Cat, Tour Ma Vie.
  - Post Malone, Big Ass Stadium Tour Part 2.
  - The Kid LAROI.
  - Ye's 2026 stadium run, where only the SoFi and Soldier Field pairs have figures.
- **Tails left out of partial totals:** the last ~8 Chromakopia shows, the last ~10 Central Cee shows, and Jelly Roll's 2025 international leg as a separate figure.
- **Non-US artists:** GIMS, Ninho, Jul, PLK, SDM, Damso, Gazo, Werenoi, Sfera Ebbasta, Morad, Matuê, Alemán, Aitch, Skepta, Baby Gang and Beny Jr. None appear in Billboard Boxscore, and French, Italian, Spanish and Brazilian press report sell-outs or ticket counts only, never gross. They are all marked "none reported", with attendance claims noted where found.
- **Pollstar's full Top-100/200 charts are subscriber-only.** Only the Top-10 profiles and analysis pieces were readable.

## Unverifiable or contested claims (not used as A/B)
- **Drake "It's All a Blur" $320.5M, 1.3M tickets, 80 shows.** It is presented as the highest-grossing rap tour, but the source is Genius on Instagram, with no Billboard or Pollstar confirmation.
- **Drake Anita Max Win $30.3M from 12 shows.** Uncited on Wikipedia.
- **Ice Spice Y2K! $7.5M.** Uncited on Wikipedia.
- **Ye Istanbul ~$44M and 118K attendance.** Organizer claim only.
- **Wikipedia's Big Ass Stadium Tour total ($169.7M, 80 shows)** is uncited and conflicts with Billboard and Pollstar, so it was not used.
