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

## Board

"Music Build Board": https://claude.ai/artifact/MdBgbsM31Any2J6FjBVnQn (claude.ai page with its own database,
collection `tasks`; editable from the phone).
