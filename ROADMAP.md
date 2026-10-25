# Roadmap: artist economics and audience tracker

Working name: **Rap Ledger** (owner to choose; see question 4). Built the same way as Public-Registry: discovery first,
one real pass per step, every figure sourced, decisions in `DECISIONS.md`, checkpoints are hard stops.

Research behind this plan (with a URL for every claim): `docs/research/research_data_sources.md`,
`docs/research/research_economics.md`, `docs/research/research_market.md`.

## Plan memo

**Situation.** Nothing is built yet. The free sources that can be reached today are:
- kworb.net: daily top 2,500 Spotify artists by monthly listeners, plus total and daily streams per artist (lead
  and feature);
- Wikidata (CC0): genres, platform IDs (Spotify, YouTube, Instagram, TikTok, X), record labels, photos on
  Wikimedia Commons;
- MusicBrainz: IDs and genre votes;
- Deezer: fan counts, with no key;
- YouTube Data API: free;
- Pollstar/Billboard Boxscore: reported tour grosses;
- Spotify Loud & Clear, IFPI, RIAA, CMA and court records: the economics.

**Complication.**
1. **Spotify closed its door.** The official API no longer gives followers or popularity to new apps (February 2026).
   Monthly listeners were never in it. Its developer policy bans derived listener metrics, and its user guidelines
   ban scraping. Every free route to Spotify numbers is a grey zone. The clean route is a licensed aggregator
   (Soundcharts from $50/month, Chartmetric $350+/month), and showing their data publicly needs a negotiated
   licence.
2. **Nobody knows what an artist is paid; it can only be estimated.** Payouts per stream are known by platform
   (about $3 per 1,000 Spotify streams to the master owner). What reaches the artist depends on the deal: about 20%
   on a major label, 80-100% independent. Deals are rarely public. Publishing earnings estimates as facts invites
   defamation claims.
3. **Fan demographics for other artists** exist only from paid aggregators, built from Instagram, TikTok and YouTube
   data. There is no reliable public survey of hip-hop listeners by age or gender newer than about 20 years.
4. **"Labels that pay x per stream" cannot be measured from public data.** What can be shown is the deal type (from the
   ℗ line and press), the known contract terms (court filings, published contracts), and the take-home range each
   deal type implies.

**Question.** How do we get a reliable, monthly, useful site live fast without building on data we cannot keep
using or show publicly?

**Answer.** Build a **private prototype now on free data**, behind an email login like Hoop Ledger, with every
source behind one replaceable collector. Licensed data is a decision gate before anything goes public or paid.
Every number carries a grade:
- **A:** primary (filings, Boxscore, Spotify's own disclosures);
- **B:** reputable secondary;
- **C:** our estimate, always shown as a range.

The edge for customers is in four places:
- **Breakouts:** artists ranked 101-2,500 who moved most this month.
- **Pay transparency:** the gap between royalties generated and take-home under each deal type.
- **The label ownership map:** who owns which label and distributor, with dates and sources.
- **A 5-minute monthly summary.**

## Phases

Effort labels follow the working agreement: high for APIs with many edge cases, identity matching and money
estimates; low or medium for UI and routine work.

### Phase 0: Top 100 hip-hop on Spotify (prototype, private)

| # | Step | Effort | Why |
| --- | --- | --- | --- |
| 0.1 | Universe: daily snapshot of kworb's top 2,500. Raw page kept unchanged with its SHA-256; parsed to `data/spotify_daily.csv` | medium | One page, but it only shows today: a missed day is lost |
| 0.2 | Genre: is the artist hip-hop/rap? Wikidata genres, MusicBrainz votes and a name list vote, and the borderline cases go to the owner's review list. Result: `registry/artists.csv` with `genre_primary`, `genre_basis`, `reviewed` | high | Wikidata alone tags Bruno Mars and Ed Sheeran as hip-hop; Latin trap needs an owner rule |
| 0.3 | Identity: Spotify ID → Wikidata QID → MusicBrainz ID, YouTube channel, Instagram, TikTok, X handles (Wikidata properties); Deezer by name with a check | high | Wrong IDs poison every later number; uncertain matches go to review |
| 0.4 | Metrics: monthly listeners, daily and total streams (lead and feature), Deezer fans, YouTube subscribers and views | medium | Each source has its own quirks (YouTube rounds to 3 digits, 30-day storage rule) |
| 0.5 | Photos: Wikimedia Commons (Wikidata P18), credit on every image, monogram where there is none | low | Only clearly safe free source |
| 0.6 | Streaming money v0: estimated Spotify royalties generated a month (streams × rate range, grade C) and the artist's take-home range by deal type (label from Wikidata P264, flagged as assumed) | high | First money figure on the site: must be labelled right from day one |
| 0.7 | Site: ranking table (filters, sort), artist page, methodology page; same plain-file setup and black-and-white look as Hoop Ledger | medium | Reuses Hoop Ledger's patterns |

**Checkpoint 0:** the owner reviews the top-100 list and the genre review list, looks at the site, and takes the quiz.

### Phase 1: The monthly engine

- 1.1 Daily snapshots run by a scheduled workflow, with month-end close on the 1st and the archive tagged as a release (medium).
- 1.2 Month-on-month movers: rank change, listener change, stream velocity; lead vs feature share (medium).
- 1.3 **Breakout Watch** for hip-hop artists ranked 101-2,500 (high):
  - growth over 7, 28 and 90 days, compared with peers of the same size;
  - acceleration;
  - confirmed on a second platform (Deezer, YouTube);
  - tiers: Emerging / Accelerating / Confirmed;
  - back-tested each month, with the hit rate published.
- 1.4 **Monthly summary:** written by Claude from the computed changes only (no new facts), held for the owner's approval, then
  published as a page and an email. Cost: under $1 a month (low-medium).
- **Checkpoint 1:** the first monthly issue is approved.

### Phase 2: Audience on every platform (licensing gate)

- 2.1 **Decision gate:** run a Soundcharts trial ($50/month) on the top 100. Compare it with the free numbers, then ask
  for a public-display licence and a quote. Chartmetric is the second quote (high).
- 2.2 Platforms:
  - YouTube: apply for audited analytics approval (III.L) before keeping history;
  - Instagram: follower counts via Business Discovery;
  - TikTok: through the licensed feed;
  - X: pay-per-use;
  - SoundCloud and Audiomack: where reachable (medium-high).
- 2.3 Demographics: age, gender and top cities per artist from the licensed feed only, labelled "modelled by <vendor>".
  Genre-level context comes from Edison and Luminate (medium).
- 2.4 Platform split: each artist's audience and estimated royalties by platform (high).

### Phase 3: Economics (the core value for artists)

- 3.1 Rate card (`registry/rates.csv`): per-platform payout per 1,000 streams, low/mid/high, each with a grade, source,
  and date; reviewed every March when Loud & Clear, IFPI and RIAA publish (medium).
- 3.2 Revenue model per artist per year: recorded, publishing, touring, merch, brand deals (only those publicly
  reported) (high).
  - Each line shows royalties generated and the artist's take-home range.
  - A confidence chip goes on each line.
- 3.3 Tours: Boxscore-reported grosses (high). Each tour shows:
  - gross per show;
  - **revenue per fan** (gross ÷ tickets);
  - a waterfall from gross to the artist's slice: promoter and venue, production, agent 10%, manager 15-20%,
    business manager 5%.
  - A league table ranks tours by revenue per fan.
- 3.4 "**Am I paid enough?**" calculator for artists, free (medium):
  - inputs: streams, deal type, royalty rate;
  - output: take-home compared with 10 peers of a similar size and an explanation of the gap.
- 3.5 Methodology page, public corrections log, dispute form (low).

### Phase 4: Labels and the market map

- 4.1 Label registry: majors → label groups → labels → imprints; distributors. Every link dated and sourced (Wikidata
  P749/P355, MusicBrainz, trade press); text names only, no logos (high).
- 4.2 Artist → label → ultimate parent, as of a date: ℗ lines where reachable, Wikidata P264, press. Each link
  marked confirmed / reported / inferred (high).
- 4.3 Label pages and comparison (medium):
  - roster size, combined listeners, breakouts signed;
  - deal types seen;
  - known contract terms from court filings or published contracts;
  - the take-home range those terms imply per 1m streams.
- 4.4 Market map: share of the hip-hop top 100/1,000 by parent (UMG, Sony, WMG, independent) and by distributor,
  month by month (medium).

### Phase 5: Gamified value and the products

- 5.1 **Commercial Value Score** 0-100: audience, growth, engagement, touring draw and catalog depth. Factors shown as
  stats on an artist card, with levels (Rookie → Rising → Headliner → Icon) and badges (Breakout of the month, 3-month
  streak, Feature magnet). Never called "worth" (low-medium).
- 5.2 Watchlists and alerts for labels: follow artists, get an email when one breaks out (medium).
- 5.3 **Scout League** (free, no money): pick 5 artists outside the top 100 each month and score on their growth, with a
  leaderboard of the best scouts (medium).
- 5.4 Artist view (free): my numbers, my peers, my level, what would move it (medium).
- 5.5 Pricing test for small labels: around $29-79 a month for breakouts, alerts, label pages and exports (owner's
  call later).

### Phase 6: Scale

- Top 1,000 hip-hop, then other genres (R&B, Latin, pop, Afrobeats, country), each with its own review of the genre
  rule.
- Countries and city-level charts.
- Public launch (domain, licence in place, E&O insurance checked).

## Phase 7: Worth and Scout (owner, 2026-10-23: "insights for artists to understand their worth and labels to find new talent")

The site gets two clear doors instead of eight tabs:
- **Worth**, for artists: what their music earns, what they keep, and what the catalog would sell for.
- **Scout**, for labels: who is rising, who is unsigned, and who is signed to whom.

| # | Step | Effort | Why |
| --- | --- | --- | --- |
| 7.1 | Wikipedia attention: monthly page views for 24 months per artist (Wikimedia API, free, no key) | medium | The only free trend history we can read today. Our own listener history starts 2026-10-23 |
| 7.2 | Fresh-release velocity: daily streams of songs out 90 days or less, from the song pages we already read | medium | The strongest free breakout signal; uses existing data |
| 7.3 | Scout score 0-100. Factors: velocity, current share, today's listener change, attention trend, chart breadth, Deezer and YouTube pull. Each is ranked against artists of a similar size. Tiers: Watch / Rising / Breaking. Every factor is shown | high | A ranking labels will act on, so each input has to be visible and checkable |
| 7.4 | Scout page: filters (unsigned only, size band, country, label status), sortable columns, CSV export | medium | The page a small label would pay for |
| 7.5 | Worth: catalog value range (yearly net royalties × published sale multiples), a per-artist worth card, and an "Am I paid enough?" calculator (inputs: listeners or streams, deal type) | high | Money figures: ranges, grade C, sources |
| 7.6 | Labels market map: share of the top 1,000 by label group and distributor (listeners and current listeners), indie share by size band, and a roster per label group | medium | Original research; uses existing label status |
| 7.7 | Navigation and design: home with the two doors; nav Charts / Scout / Worth / Labels / Method; artist page opens on a summary card; phone tables keep the name column fixed and hide minor columns; sortable headers | medium | Clarity for both audiences |
| 7.8 | Apple Music charts: daily most-played top 100 songs in 20+ countries (Apple's public RSS feed); presence per artist on a second platform | low-medium | A free second platform to confirm Spotify signals |
| 7.9 | Levels and badges: Rookie → Rising → Headliner → Icon; badges such as Breakout, Feature magnet, Unsigned and rising | low | Gamification from the scores above |
| 7.10 | Workflows: monthly page views, daily Apple charts, and a one-off Wayback backfill of kworb listener pages (2019 onwards) for real listener history | medium | web.archive.org is blocked in the build container; reachable from GitHub Actions |

Built on 2026-10-23: all of 7.1-7.10 (7.10's backfill waits for the merge to main and one manual run), plus a
feature network (collaborations per artist, "Co-signed" badge) and a "Right now" strip on the home page.

## Phase 8: Deeper signals (queued 2026-10-23)

| # | Step | Effort | Why |
| --- | --- | --- | --- |
| 8.1 | Label coverage: MusicBrainz label relations (owned by, imprint of, distributed by) for the label names our table cannot place | high | 424 of the 1,000 have no known label; labels need this for the market map and for scouting |
| 8.2 | Scout back-test on the Wayback history: did the artists scoring highest 90 days ago grow more than the rest? Published hit rate | high | Turns the score from a judgement into evidence |
| 8.3 | Compare two artists side by side | medium | The most common question from both artists and labels |
| 8.4 | Scout watchlist (kept in the browser), then email alerts | medium | Makes Scout a daily tool |
| 8.5 | "This month": movers, new Breaking, unsigned prospects, change in label shares | medium | Needs 30 days of history; feeds the monthly summary (1.4) |
| 8.6 | Genre review: settle the 1,491 borderline artists with the owner | low (owner) | Each one settled can move an artist into or out of the 1,000 |

Further out:
- MusicBrainz label-contract dates for the market map over time;
- Last.fm listeners and setlist.fm show counts (each needs a free key as a GitHub secret);
- other genres.

## Phase 9: Second genre and data depth (owner, 2026-10-24: research journey; country as a second genre)

| # | Step | Status |
| --- | --- | --- |
| 9.1 | Four sections (Artists, Scout, Money, Labels), indexable static pages, share cards, lighter first load (D1-D6) | built |
| 9.2 | Country behind a header switch: 381 artists above the 500k floor, found by the genre rule and confirmed from their songs; Deezer-ordered list below the floor (grade C) | built; presentation pending the owner |
| 9.3 | Country money: Amazon/Pandora-weighted services and a radio songwriting line (C5); US radio as an internal Scout factor and our own radio rank (C4) | built |
| 9.4 | New data for both genres: certifications (English, French, German Wikipedia), awards, credits, Shazam (incl. country charts), US radio, Discogs label parents, tours (country, 2025-26 hip-hop) | built |
| 9.5 | Identity: Deezer IDs confirmed by ISRC or song titles; monthly Deezer audit; Wikidata items from MusicBrainz | built |
| 9.6 | Label research batches 4-7 and two country batches: unknown hip-hop labels 262 -> 191, country 207 -> 35 | built |
| 9.7 | Product pass: key numbers first, Scout table fits, phone tables stack, coverage table, search and compare across genres | built |

**Checkpoint (owner): passed 2026-10-25.** The owner took the suggested answer on all ten questions in PR #9
(DECISIONS.md, 2026-10-25 "Owner's answers").

Next candidates: Last.fm listeners as a second below-floor measure (needs a key, K1); YouTube Data API for views
(K1); the country back-test once 90 days of daily scores exist (January 2027).

## Phase 10: Depth and accounts (owner, 2026-10-25)

| # | Step | Status |
| --- | --- | --- |
| 10.1 | Country top 1,000 at hip-hop depth: Spotify IDs from MusicBrainz, kworb pages confirmed from songs, ranked by listeners, then streams a day, then Deezer's order | building |
| 10.2 | White page and black text, as tventy sport | built |
| 10.3 | Artist descriptions: one or two sentences from English Wikipedia (CC BY-SA), else from our own data | built |
| 10.4 | "How this ranking works" on each ranked page: metrics, what each measures, weights (Method kept) | built |
| 10.5 | **Later:** accounts, so a person can star and track artists across devices | queued |

10.5, to plan with the owner first (it adds personal data, so privacy terms and a deletion route come with it):
- Today the star list lives in the browser only (localStorage), so it is lost on another device.
- Sign-in without passwords: an emailed one-time link (or Google), on the same Cloudflare setup as the site (Pages
  Functions with D1 or KV for the lists); nothing stored but the email and the starred artist IDs.
- Tracking: a weekly email with what moved for the starred artists (listeners, Scout tier, new releases, label
  changes), off by default, unsubscribe in one click.
- Costs: Cloudflare's free tier covers the storage; email needs a sending service (cost to confirm first).

## Phase 11: Product ideas (overnight, 2026-10-26)

From the product pass in `docs/product/2026-10-26-ideas.md` (user, job, data, effort, value and risks for each). Built
that night: the catalog screener (`#/screener`), the artist one-pager (`#/sheet/<id>`) and the data quality and
corrections page (`#/quality`); see DECISIONS.md 2026-10-26. The rest, in ranked order:

| # | Idea | For | Effort | Value | Status |
| --- | --- | --- | --- | --- | --- |
| 11.1 | Deal comparison and advance recoupment for one artist (months to recoup at today's streams, per deal type) | artists, managers | S-M | 4 | built (2026-10-26: `#/worth/<id>`, "Deal comparison" panel) |
| 11.2 | Label one-pager and roster export (roster size, listeners, roster value range, age mix) | investors, analysts | S-M | 4 | built (2026-10-26: `#/label/<slug>/sheet`, roster CSV on the label page) |
| 11.3 | Saved screens in the address (Scout and screener filters in the URL, to send a colleague) | investors, A&R | S | 3 | built (2026-10-26: Scout, screener, Unsigned; "Copy link to this view") |
| 11.4 | Catalog age explorer per artist (streams by release year, implied decay) | investors | M | 4 | built (2026-10-26: artist page "Catalog age" panel, three age bands; per-song table not yet) |
| 11.5 | Watchlist digest: what moved for starred artists since the last visit (browser only) | A&R | M | 4 | idea (needs 7+ days of daily log) |
| 11.6 | Press page with quotable, dated figures and a citation line | press | S | 3 | built (2026-10-26: `#/press`, figures with method, date and a copyable citation line; estimates as ranges) |
| 11.7 | Method versions and changelog page for money and Scout (ranking versions are on #/quality) | analysts | S | 3 | built (2026-10-26: `#/changelog` from `registry/method_changes.csv`, tied to corrections.csv) |
| 11.8 | Embeddable artist widget (iframe) with source and date | press, artists | S | 3 | idea (licence question first, 2.1) |
| 11.9 | "What changed this week" digest from the daily logs (no new claims) | press, A&R | S-M | 3 | idea (needs 7+ days) |
| 11.10 | Market share over time by label group | analysts, investors | M | 4 | idea (needs months of log) |
| 11.11 | Country vs hip-hop comparison page | analysts, press | S | 3 | idea |
| 11.12 | Unsigned prospects export with official public links only (no personal contact data) | A&R | S | 4 | idea |
| 11.13 | Correction request form as a prefilled email (nothing stored) | artists, managers | S | 3 | built (2026-10-26: "Report a correction" on artist and label pages) |
| 11.14 | Label financials side by side, periods aligned | investors | S | 3 | idea |
| 11.15 | Peer benchmark card: percentile among the 10 nearest artists | artists | S | 3 | idea |
| 11.16 | Read-only JSON API with documentation | analysts, funds | S | 3 | idea (redistribution terms, 2.1) |
| 11.17 | Glossary page from config.js | all | S | 2 | built (2026-10-26: `#/glossary`, GLOSSARY + How-box metrics; footer and How boxes) |
| 11.18 | Tours league table v2 by size band | investors, managers | S | 2 | idea |
| 11.19 | Scout hit rate published on our own daily log | A&R, investors | M | 4 | idea (January 2027) |
| 11.20 | Paid tier: weekly CSV and alerts for labels and investors | labels, investors | M | 5 | idea (hard stop: accounts, cost, licence) |

## My own additions (beyond the brief)

- **Pay-gap explainer:** the same 100m streams under a DIY, distribution, joint-venture and major deal, side by side.
  It is the single most useful thing for an artist to understand.
- **Feature network:** who features whom, and how much of each artist's streams come as a featured guest (kworb
  splits lead and feature). A feature with a top-10 artist is an early breakout signal.
- **Catalog value range:** yearly royalties × published sale multiples (about 15-17×). Small labels can use it to
  price a catalog or a buy-out.
- **Honesty features as a selling point:** grade badges, data dates, a public back-test of Breakout Watch and a
  corrections log. Competitors do not publish these.
- **Indie vs major share of hip-hop, month by month:** original research that the trade press would quote.

## Costs (to confirm before each run that spends money)

| Item | Cost |
| --- | --- |
| Cloudflare Pages + Access (private, up to 50 users) | free |
| GitHub Actions (daily snapshot ~3 min, monthly close ~10 min) | ~100 min/month |
| Claude for the monthly summary | under $1/month |
| Soundcharts trial (Phase 2 gate) | from $50/month |
| Licence for public display | quote needed |

## Owner's decisions needed (Checkpoint −1)

See the questions in the session and `DECISIONS.md`. Phase 0 steps 0.1-0.5 are free and reversible; 0.6 onward wait
for the answers.

## Ranking method

Our top 100 is ranked by current listeners: `docs/METHODOLOGY.md` (version 1.1), also at
https://claude.ai/artifact/6jUwKAZx52ZVhgWbEt95ny.

## Board

"Music Build Board": https://claude.ai/artifact/MdBgbsM31Any2J6FjBVnQn (claude.ai page with its own database,
collection `tasks`; editable from the phone).
