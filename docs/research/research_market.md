# Hip-Hop Analytics Site: Market and Product Research (as of 2026-10-23)

Confidence tags: **[V]** means checked against a 2025-2026 source in this research. **[K]** means it comes from prior knowledge and should be re-checked before publishing it as a fact.

## 0. Bottom line

- **Positioning:** the "Pay-transparent A&R desk for independents." It joins three things that today sit in separate tools: (a) discovery signals of the Chartmetric/Soundcharts kind, (b) a label/distributor ownership graph that nobody publishes as clean data, and (c) plain-language revenue estimates with stated confidence ranges. Price it under Chartmetric's Premium tier. Give artists a free view of their own economics.
- **The gaps worth taking:** (1) the "who owns whom" label graph, (2) clear, published methodology for revenue estimates, (3) monthly written summaries that a small-label owner can read in 5 minutes, (4) breakout alerts tuned to hip-hop and scoped to smaller artists.
- **Biggest risk is data access.** Spotify closed off much of its Web API in 2025-26, and scraping breaks its terms. Plan to license data (for example the Soundcharts API from $50/month) rather than scrape.

---

## 1. Label market map

### 1.1 Market size and share
- IFPI's Global Music Report 2026 puts 2025 global recorded-music revenue (wholesale) at **US$31.7B, up 6.4%**. Streaming was 69.6% of that and paid subscription 52.4%, with 837M paid subscription users [V]. Sources: https://www.musicbusinessworldwide.com/global-recorded-music-revenues-hit-31-7bn-in-2025-up-6-4-yoy-users-of-paid-music-subscriptions-reach-837m , https://www.ifpi.org/global-music-report-2026-global-recorded-music-revenues-grow-6-4-as-record-companies-drive-innovation/
- MIDiA's estimate is broader: **$39.5B in 2025, up 9.4%**. It includes "expanded rights" (labels' share of merch, live and brand income), which grew 21.5%. Non-major labels gained share only when expanded rights are counted, and self-releasing artists' share fell [V]. Source: https://www.midiaresearch.com/blog/global-recorded-music-revenues-up-94-in-2025 . MIDiA's per-major split for 2025 is paywalled (https://midiaresearch.com/reports/recorded-music-market-shares-2025-expanded-rights-growing-impact). The most recent public figure: independents held **46.7% by ownership and 34.2% by distribution** of 2023 revenue (https://routenote.com/blog/?p=101806) [V].
- On Spotify, the three majors plus Merlin took **72% of global plays in 2025** (https://www.musicbusinessworldwide.com/the-empire-strikes-back-the-majors-and-merlin-gained-a-bit-of-market-share-on-spotify-last-year/) [V].
- US current-album share in 2025 (Billboard/Luminate, summarized from search results because the article is paywalled): **Republic 16.04%** was the top imprint and Interscope second at 9.62%. The whole indie sector by distribution was 20.17%. In Q4, Republic reached 22.5% against Sony's 23.94% (https://www.billboard.com/pro/record-label-market-share-2025-republic-taylor-swift/) [V, secondary].
- **Hip-hop share:** In the US, R&B/hip-hop was **25.3% of on-demand audio streams in 2024**, down 1.7 points (https://luminatedata.com/blog/how-rb-hip-hop-streaming-share-could-get-its-groove-back). In 2025 it had 349.9B streams out of about 1.4T total, roughly **25%**, still #1 but losing share to rock (+6.4%) and Latin (+5.2%) (AP coverage of Luminate's 2025 year-end report: https://wtop.com/national/2026/01/music-streams-hit-5-trillion-in-2025-christian-rock-and-latin-lead-growth-in-the-us/) [V]. No public source gives major-vs-indie share *within* hip-hop. That gap is itself a product opportunity: compute it from your own label graph combined with chart data.

### 1.2 Structure (hip-hop-relevant nodes)
**Universal Music Group** (2025 revenue €12.5B, https://tools.prnewswire.com/en-us/live/20823/release/20260305EN02412 [V])
- UMG consolidated its US labels in 2024: East Coast labels under **Republic** (Republic Corps: Republic, Def Jam, Island) and West Coast labels under **Interscope** (Interscope Capitol Labels Group: Interscope, Capitol, Motown, Geffen) [V for the consolidation, K for the exact names]. Source: https://ca.billboard.com/business/record-labels/universal-music-layoffs-interscope-republic-capitol-def-jam-1235619417
- Republic: Young Money and Cash Money, OVO Sound [K].
- Interscope: TDE, Dreamville, LVRN, Aftermath, Shady. pgLang/Kendrick Lamar is distributed via Interscope [K].
- Motown/Capitol: Quality Control. HYBE America has owned QC since 2023 (about $300M) and its roster stays affiliated with UMG (https://www.rollingstone.com/music/music-news/hybe-aquires-quality-control-deal-1234676368/) [V].
- Def Jam: Tunji Balogun is reported to be leaving by the end of 2026 in UMG's latest cuts, which also include Interscope A&R presidents (https://musicbusinessworldwide.com/multiple-layoffs-at-universal-cutting-program-continues/ , https://nairametrics.com/2026/10/15/universal-music-group-announces-fresh-layoffs-amid-270-million-cost-cutting-programme/) [V]. **Implication:** label hierarchies change often, so the dataset needs dated edges.
- **Virgin Music Group** (UMG's indie distribution arm) includes Ingrooves [K]. It closed its **$775M purchase of Downtown on 2026-02-20**, which brings in FUGA, CD Baby, Downtown Artist & Label Services and Songtrust. Under the EU approval it must divest Curve (https://au.variety.com/2026/music/news/universal-virgin-music-complete-775-million-acquisition-downtown-33349 , https://www.musicbusinessworldwide.com/universa-music-downtown-acquisition-cleared-by-eu-competition-regulator/) [V].

**Sony Music**
- Columbia, RCA, Epic. Cactus Jack is via Epic (https://en.wikipedia.org/wiki/Cactus_Jack_Records, low certainty). **Alamo Records** is majority Sony since 2021; Sony bought UMG's stake (https://musicbusinessworldwide.com/sony-music-buys-majority-stake-in-todd-moscowitzs-alamo-records) [V].
- Distribution arms: **The Orchard**, and **AWAL**, acquired 2022 [K].
- Rich Music: affiliation not verified. Treat it as a research item.

**Warner Music Group**
- **Atlantic Music Group**, run by CEO Elliot Grainge since Oct 2024, includes Atlantic, 300 Elektra Entertainment (300 + Elektra) and 10K Projects (https://www.musicbusinessworldwide.com/atlantic-music-group-makes-around-two-dozen-layoffs-to-achieve-maximum-impact-for-its-artists1 ; 300 was acquired in 2021 for about $400M, https://variety.com/2021/music/news/warner-music-group-acquires-300-entertainment-megan-thee-stallion-1235134996) [V]. YSL is via 300 [K].
- Distribution arm: **ADA** [K]. WMG owns **Sodatone**, its A&R data tool, acquired in 2018 (https://musicbusinessworldwide.com/warner-buys-ar-scouting-tool-sodatone-to-boost-its-search-for-the-superstars-of-tomorrow) [V].

**Independent distributors (not major-owned):** EMPIRE (founder Ghazi says he will not sell, https://trapital.com/episodes/ghazi-on-why-he-will-never-sell-empire [V]), UnitedMasters, DistroKid, Stem, Believe/TuneCore (taken private in 2024 by a founder-led consortium [K]). **Major-owned:** Virgin/Ingrooves/Downtown/FUGA/CD Baby (UMG), The Orchard/AWAL (Sony), ADA (WMG). Flagging "indie-looking but major-owned" distribution is a strong feature for indie artists.

### 1.3 Sources for building the hierarchy
- **Wikidata:** P749 *parent organization*, P355 *subsidiary*, P264 *record label* (on artists), P31 instance-of Q18127 *record label*. The SPARQL endpoint is CC0-licensed, which is the cleanest license for republishing.
- **MusicBrainz:** "label ownership" relationships link to the immediate parent only (https://musicbrainz.org/relationship/ab7a9be0-c060-4852-8f2e-4faf5b33231e). Label types include *imprint* and *distributor* (https://musicbrainz.org/doc/Label) [V]. The core data is CC0, and the database dumps are free.
- **Discogs:** label/sublabel and "parent label" data plus monthly CC0 data dumps. Good for older imprints.
- **Release-level truth:** the ℗/© lines and the "label" field on DSP releases, and distributor info from ISRC prefixes and UPC. These matter more than the corporate org chart because deals are per artist or per project.
- **Trade press for deal edges** (MBW, Billboard, HITS). Human-curate them with a source URL on every edge.

---

## 2. Competitor landscape

| Product | What it does | Price (verified where noted) | Gap for this product |
|---|---|---|---|
| **Chartmetric** | Cross-platform artist data. Artist Score/Rank from 50+ metrics across 16 platforms. Career Stage (median of the last 360 days) and Momentum (45-day vs prior 45-day, relative within each stage). Flow AI. | Manager $40/mo, Premium $117/mo, Ultra $150/mo (billed yearly). Flow AI $60/mo. MCP included. https://chartmetric.com/pricing [V]. Method: https://hmc.chartmetric.com/chartmetric-artist-career-stage-growth/ [V] | Dense UI, no revenue estimates, no ownership graph |
| **Soundcharts** | Charts, playlists, radio, TikTok, alerts, API | Artist $10, 10 artists $49, PRO $129/mo; API from $50/mo; data shares from $2,000/mo; 2 months free on annual. https://soundcharts.com/en/pricing [V] | Best **data supplier** candidate |
| **Songstats** | Artist/label tracking, playlist and radio stats | About €6.99-€11.99/mo for artists; label tiers higher (third-party sources, https://resources.onestowatch.com/songstats-pricing-plans-independent-musicians/) | Mostly tracking, weak on discovery |
| **Viberate** | 20+ sources, label and festival analytics | $75/mo or $899/yr (https://viberate.com/artist-stats/pricing) [V] | General, not built for hip-hop |
| **Luminate** | Official US consumption data behind Billboard charts | Enterprise only | Expensive; the data is the industry's reference point |
| **Kworb** | Free Spotify/YouTube chart and stream tables | Free | Raw tables, no analysis; collection method undocumented |
| **HITS Daily Double** | Trade news; weekly label market share from Top 100 placement | Subscription/trade | Not a tool |
| **Instrumental** | AI A&R (TalentAI) plus a £10M artist fund. Tencent and WMG UK are investors (https://musicbusinessworldwide.com/online-talent-scouting-platform-instrumental-raises-4m-for-aggressive-growth-plan) | Mostly B2B | Mostly captive or in-house |
| **Sodatone** | WMG-internal A&R | Not for sale | Not available to small labels |
| **HITLAB** | Hit-prediction ("DNA" audio analysis) | Not verified | Audio-based, opaque |
| **Music Tomorrow** | Recommender/algorithm audits, audience-cluster analysis (https://music-tomorrow.com/blog) | Consultancy | Consultancy, not self-serve |
| **Spotify for Artists** | Each artist's own first-party data | Free | Siloed to one artist; no money view, no peers |
| **stats.fm** | Consumer listening stats (not affiliated with Spotify) | Freemium | Consumer use, not market data |

**Differentiation:** (1) Revenue estimates broken down by source and shown as ranges with published assumptions, framed like Spotify's own Loud & Clear (2025: about 13,800 artists generated $100k+ on Spotify, about 1,500 passed $1M, the top 80 passed $10M; https://newsroom.spotify.com/2026-03-11/loud-and-clear-music-economics-highlights/ [V]). (2) A "Who really owns this?" label graph. (3) A monthly narrative report. (4) Peer benchmarks for artists ("artists at your listener level typically earn X-Y"). (5) Price around $29-79/mo for small labels, well under Chartmetric Premium and Ultra.

---

## 3. Gamification

**Examples:**
- **Stream League**: weekly picks from New Music Friday, scored on Spotify streams (https://interspacemusic.com/blog/stream-league-launches-fantasy-draft-based-on-spotifys-new-music-friday/).
- **FanLabel**: a fantasy record label scored on cross-DSP plays, with points redeemable for merch.
- **Vault's Fantasy Record Label** (from FanDuel's founders): scored on change in monthly listeners, and you must own a track by an artist to sign them (https://navgtr.org/2023/11/21/fanduel-founders-launch-the-first-ever-fantasy-record-label-game/).
- **MFL**: real-money music fantasy leagues through Lucra (https://www.startupresearcher.com/news/lucra-and-mfl-partner-to-launch-real-money-music-fantasy-leagues).
- **Kalshi/Polymarket**: run real-money Spotify markets, for example "Top artist on Spotify 2026" and daily US top artist (https://next.io/prediction-markets/trending/who-will-be-the-top-artist-on-spotify-in-2026/) [V].
- **SongVest**: sells SEC-qualified Reg A+ royalty shares (https://songvest.com/how-it-works) [V], which shows that "artist stock" with real money is a securities product.

**Recommended:**
- Free play only, with no cash value: "Scout Leagues" where users draft 5 sub-100k-listener artists per month and score on *growth percentage*, not absolute numbers.
- Public **Scout Track Record** (an accuracy leaderboard), which doubles as a credibility signal for A&R users.
- Artist badges for milestones, such as "First 10k monthly listeners" and "Cross-platform confirmed."
- A "Commercial Value" score from 0-100 with a visible breakdown of its inputs.

**Pitfalls:**
- (a) Any cash prizes, buy-ins or tradable value can become gambling or securities regulation.
- (b) Scoring on raw streams rewards superstars and invites manipulation. Score on percentage growth and require cross-platform confirmation.
- (c) Monthly-listener scoring is very volatile.
- (d) Artists may see "scores" as a public judgment of them. Keep the language positive and give artists a right to reply.
- (e) Engagement often drops after the novelty wears off. Tie leagues to monthly report cycles.

---

## 4. Breakout detection

What the tools use:
- Chartmetric Momentum compares 45-day windows, normalized within each career stage [V].
- Chartmetric also has growth-velocity filters and TikTok velocity tracking.
- Sodatone looks at fan loyalty and engagement and the virality of demos [V].
- Spotify holds a 2022 patent on predicting breakout artists from early-adopter listening patterns (https://midnightrebels.com/the-new-spotify-technology-turns-your-listening-data-into-prediction-algorithm-for-new-artists/, secondary source).
- A&R practitioners cite Shazam spikes as a lead indicator ahead of radio (https://www.headlinerhub.com/shazam-tiktok-new-rules-a-and-r-spinnin’-records’-jorn-heringa-finding-hits-before-they-happen.html).
- Published, peer-reviewed label methods are rare, so treat vendor claims, such as "TikTok leads NMF by 1-2 weeks," as unverified.

**Proposed method (transparent and publishable):**
1. Per artist and platform, compute log growth over 7, 28 and 90 days (velocity) and the change in 28-day velocity (acceleration).
2. Turn these into z-scores against a **peer cohort**: same listener band and same genre.
3. **Cross-platform confirmation:** require 2 or more independent signals above threshold, for example Spotify listeners, YouTube views, TikTok sound creates, Shazam counts, playlist adds and Genius pageviews.
4. Apply **quality filters**:
   - save-to-listener and follower-to-listener ratios
   - playlist concentration (a spike from a single playlist means low conviction)
   - city or country spread
   - bot heuristics (sudden listeners with no followers or saves)
5. Add **change-point detection** (for example Twitter's E-Divisive with Medians, https://github.com/twitter/BreakoutDetection) to date when a breakout started.
6. Output a "Breakout Watch" tier (Emerging / Accelerating / Confirmed). Back-test it monthly against artists who later charted or signed, and publish precision and recall.

---

## 5. Hip-hop audience demographics (what is citable)

- **Streaming share:** about 25% of US on-demand audio streams in 2025, the #1 genre, but share has been falling since 2020 (Luminate, sources above) [V].
- **Engagement:** Edison Research Share of Ear (Q2 2025) found that people who call Hip-Hop/R&B their main genre spend the most time with music, **3h48m per day, almost an hour above the average American 13+** (https://www.insideradio.com/free/edison-listeners-spending-most-daily-time-with-music-are-hip-hop-r-b-fans/article_798aa000-6358-483a-9f41-b8204aff6bcb.html) [V].
- **Age:** YouGov (Apr-May 2023, n=1,000) gave rap/hip-hop a net favorability of **+61 among adults under 45 and -33 among those 45+**, the widest age gap of any genre. 13% of younger adults named it their favorite genre, also the highest of any genre (https://yougov.com/en-us/articles/45699-americans-opinions-different-music-genres-poll) [V].
- **Gen Z:** Gen Z is 35% of Spotify's audience and streams about 2 hours a day (Spotify Culture Next; https://interspacemusic.com/blog/spotify-culture-next-report-gen-z-streams-2-hours-daily-drives-trends/). Luminate (2022) found Gen Z more likely than average to prefer hip-hop/rap.
- **Gap:** I found **no reputable 2025-26 public breakdown** of hip-hop listeners by gender or ethnicity. The often-quoted figures are about 20 years old (Interep: median age 26.2, 54% female) or come from unsourced aggregator sites. Do not publish those. Use per-artist audience data from licensed providers instead, since Chartmetric and Soundcharts expose age and gender splits per artist.

---

## 6. Legal and risk

- **Scraping:** Spotify's User Guidelines prohibit crawling and scraping (as reported at https://thetrichordist.com/tag/scraping/). In addition, Spotify:
  - restricted **extended Web API access from 2025-05-15** to organizations with **250k+ MAU** (https://developer.spotify.com/blog/2025-04-15-updating-the-criteria-for-web-api-extended-access) [V];
  - reportedly stripped popularity and follower fields and some endpoints in 2026 (secondary source).
  The majors and Spotify are also aggressive litigants: the Anna's Archive suit over scraping includes CFAA and breach-of-contract claims (https://www.musicbusinessworldwide.com/record-labels-spotify-sue-pirate-group-annas-archive-over-scraping-and-brazen-theft-of-86m-tracks) [V]. That case is about piracy, but it shows the legal theories available. **Do not copy kworb tables.** Its compilation and collection method is undocumented and redistributing it raises the same issues. **Do** license data (Soundcharts or Chartmetric API) and use official charts with attribution, YouTube Data API within its terms, and Wikidata/MusicBrainz (CC0). Facts themselves are not copyrightable in the US, but the terms of service and contracts still apply.
- **Names and photos:** Using artist names to identify them in factual rankings and editorial content generally falls under the newsworthiness/public-interest exception to right of publicity. That protection weakens when the use becomes advertising or a commercial product, and in *Titan Sports* posters inside a magazine were analyzed separately (https://www.thefashionlaw.com/resource-center/right-of-publicity/ , https://www.lexplug.com/casebrief/titan_sports_inc_v_comics_world_corp__66f9be7b2e37c66db3f80dbd). The law varies by state. **Do not use artist photos without a license.** Photos carry *photographer copyright* even when the use is editorial. Use licensed images (Getty/AP), Wikimedia Commons images with attribution, or artist-supplied images, and never imply endorsement. Do not sell "artist cards" or other merch-like items.
- **Earnings estimates and defamation:** Estimates of wealth or earnings have been litigated (Trump v. O'Brien over a net-worth estimate; Pippen over false bankruptcy reports, https://abajournal.com/news/article/former_bulls_star_files_defamation_suit_claiming_websites_falsely_labeled_h). The risk comes from statements that read as **verifiable facts** and that imply something damaging, such as insolvency. To lower it:
  - Label figures as estimates and give **ranges** ("est. $1.2M-$2.0M gross recording royalties generated").
  - Separate royalties generated for rights holders from the artist's take-home pay. Spotify itself makes this distinction.
  - Publish the methodology and per-stream assumptions.
  - Provide a correction and dispute channel, and fix errors quickly.
  - Avoid words like "broke," "in debt" or "net worth."
  - Get media-liability (E&O) insurance and confirm the anti-SLAPP position in your home state.
- **How Forbes and Billboard caveat:** Forbes' Cash Kings estimates **pretax** income before fees for managers, agents and lawyers. It cites its data sources (Luminate/SoundScan, Pollstar, RIAA) and interviews with industry insiders (https://www.rollingstone.com/music/music-news/diddy-jay-z-top-highest-paid-rappers-of-2015-69392). Billboard's Money Makers counts only certain revenue streams (US recorded music, publishing royalties and touring, based on Luminate and Billboard Boxscore data) and excludes others [K, not verified this session]. Copy the pattern: define the scope, name the sources, say what is excluded, use pre-fee figures, and call them estimates.
- **Gamification law:** keep games free with no tradable value. Real-money play is regulated (Kalshi under the CFTC; SongVest under SEC Reg A+).
- **Trademarks:** label logos are trademarks. Use text names, not logos, in the market map.

---

## 7. Feature ideas ranked (value ÷ effort)

| # | Feature | Value | Effort | Notes |
|---|---|---|---|---|
| 1 | Monthly hip-hop Top 100 with cross-platform metrics and month-over-month change | High | Low | SEO driver; needs licensed data |
| 2 | Auto-generated monthly summary (LLM over computed deltas) | High | Low | "5-minute read" for label owners; email |
| 3 | Label/distributor ownership graph and market map (dated edges, sources) | High | Medium | Unique asset; seed from Wikidata/MusicBrainz plus manual curation |
| 4 | Breakout Watch (cohort z-scores, cross-platform confirmation, back-tested) | Very high (paid) | Medium | Core paid feature for A&R |
| 5 | Revenue estimate ranges by source (streaming/publishing/touring/sync), with methodology page | High (artists) | Medium | Differentiator; legal care required |
| 6 | Artist "Know your numbers" free page: payout calculator, peer benchmarks | High (growth) | Low-Medium | Top of the funnel |
| 7 | Commercial Value Score (0-100) with transparent factor breakdown | Medium | Low | Shareable; avoid "worth" language |
| 8 | Alerts and watchlists (Slack/email) for scouts | High (paid) | Low | Table stakes |
| 9 | Scout Leagues and accuracy leaderboard | Medium | Medium | Retention; free only |
| 10 | Indie-vs-major share within hip-hop (computed) | Medium | Medium | Original research, PR value |
| 11 | Expand to all genres | High | High | After the data pipeline is proven |

---

## 8. Label dataset schema (proposal)

```sql
entity(id, type ENUM('conglomerate','label_group','label','imprint','distributor','artist_services','publisher','joint_venture'),
       name, aliases[], country, founded, defunct, website,
       wikidata_qid, musicbrainz_id, discogs_id, isni, notes)

entity_relation(id, parent_id, child_id,
       rel_type ENUM('owns','majority_stake','minority_stake','jv','imprint_of','distributed_by','licensed_to','services_deal'),
       ownership_pct NULL, start_date, end_date NULL,
       territory NULL, confidence ENUM('confirmed','reported','inferred'),
       source_url, source_date, last_verified)

artist(id, name, aliases[], spotify_id, apple_id, youtube_channel, tiktok_handle,
       musicbrainz_id, wikidata_qid, primary_genre, home_market)

artist_deal(id, artist_id, entity_id,
       deal_type ENUM('label','distribution','jv','360','publishing','management'),
       start_date, end_date NULL, scope ENUM('all','project','territory'),
       evidence ENUM('p_line','press','label_site','inferred'), source_url)

release(id, upc, title, release_date, p_line, c_line, label_text,
        distributor_entity_id NULL, artist_ids[])

metric_snapshot(artist_id, platform, metric, value, as_of_date, source)   -- monthly/daily
revenue_estimate(artist_id, period, stream ENUM('recorded','publishing','touring','sync','merch'),
                 low, mid, high, method_version, assumptions_json)
breakout_signal(artist_id, as_of_date, velocity_7d, velocity_28d, accel, cohort_z,
                platforms_confirmed, tier, model_version)
```

Design rules:
- Every edge is **time-bound and sourced**.
- Keep corporate ownership (`entity_relation`) separate from artist deals (`artist_deal`).
- Compute "ultimate parent" with a recursive query as of a given date.
- Store `confidence` so the UI can show "reported" versus "confirmed."

---

## 9. Key risks

1. **Data access/licensing.** Spotify API restrictions and anti-scraping terms; vendor dependency (Soundcharts API from $50/mo; data shares from $2,000/mo). *Mitigation:* license from two vendors and add first-party opt-in connections for artists.
2. **Estimate accuracy and defamation.** Use ranges, publish methodology, run a dispute process, carry E&O insurance.
3. **Incumbents copy features.** Chartmetric already has AI and MCP. The defense is the ownership graph, a hip-hop editorial voice, and explaining the economics.
4. **Label graph churn.** UMG cuts in 2026, Virgin/Downtown in 2026, and exec turnover. This needs ongoing curation, which a trade-press monitor plus human review can handle.
5. **Genre headwind.** Hip-hop's US streaming share is falling, which argues for a multi-genre roadmap.
6. **Gamification drift into regulated territory.** No money, no tradable assets.
7. **Image and trademark IP.** License photos; use text-only label names.
8. **Thin demographic data.** Do not publish unsourced genre demographics.
