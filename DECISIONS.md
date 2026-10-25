# Decisions

What was chosen, what was considered and rejected, and why. Newest first.

## 2026-10-25 Review 5: prospects, second Spotify profiles, Scout zeros and tiers, status words (items 4-10, 13, 14)

- **Who is a prospect** (`labels.independent_kind`): 10m+ monthly listeners is now established evidence ("10m+
  monthly listeners": BigXthaPlug, Morad, Shubh, Veigh). Of the rest, a prospect also needs current listeners above
  0 and a song of their own (lead) released in the last 2 years (kworb's dated songs, the earlier of the Deezer and
  MusicBrainz dates); otherwise `indie_kind` is "inactive", with the reasons (Knust, Baviera: catalog only; Danny
  Chung: no song of his own). Below the 500k floor the current audience is read from daily streams × current share.
  The site shows "Self-released, catalog only" or "Self-released, no recent release", and "catalog only" for a 0
  current-listener figure (Unsigned page, label rosters, one-pager); the Unsigned page lists them apart, with the
  reasons. Rejected: Deezer's release list as the recent-release test: it lists reissues (Makaveli has 2026 entries).
- **Second Spotify profiles** (`site_build.second_profiles`): list members sharing a Wikidata item, a confirmed
  Deezer artist or a name are one artist; the biggest profile is the main one. The smaller is named "(second Spotify
  profile)" (page address unchanged), takes the main profile's label fields, deal type (so its money too), indie kind
  and level, and is left out of the Unsigned benchmark, the picks, `insights.market` (shares, catalog count),
  label totals (still listed on the roster), This month's shares, State's and the start page's summed listeners;
  the artist page and Method say so. Pairs are written to `review/second_profiles.csv` for the owner (both genres).
  Unconfirmed Deezer matches are not used. Rejected: merging the profiles (two real Spotify pages, two figures).
- **Picks** (start page "Top unsigned prospect", State, Scout "Unsigned and rising", This month, the "Unsigned and
  rising" badge): prospects with under 90% of their streams as a featured guest (`insights.is_pick`; SRNO 97%).
- **Scout**: a signal measured as absent (no chart country, no song out in 90 days, not on US radio) scores 0, not
  the mid-rank of the zeros (it gave 29-50/100). A tier needs 60%+ of the factor weight measured; below that the
  score shows as "provisional" with no tier (`scout.weight`, `scout.provisional`). The back-test was not re-run: it
  uses only listener growth and Wikipedia attention (`src/backtest.py`), which neither change touches.
- **Status words**: one helper in app.js (`statusWord`): "Unsigned prospect", "Independent (established)",
  "Self-released, catalog only / no recent release", else the label status; used in the top list, artist page
  Label status, Compare, the one-pager and both CSV exports. Rejected: "Self-released" for all three (the review
  found "Unsigned" and "Self-released" for the same artist on two pages).
- **Mostly-featured artists** (90%+ of streams as a guest) get a small "mostly as a featured guest" note under the
  name in the top list; the ranking method is unchanged (owner's choice: mark, don't reweight).
- **Below the floor** the missing current-listener reason reads "no listener count below 500k on Spotify" (it said
  "release dates missing").

## 2026-10-25 Site engineering: speed, accessibility, SEO, robustness (task: "engineering quality of the music site")

- **Measured** with Playwright + CDP (Chromium, 390px phone, Lighthouse "slow 4G": 150 ms RTT, 1.6 Mbps, 4x CPU),
  served with brotli as Cloudflare does. Biggest costs: `data/index.json` (~300 KB after brotli) before any list
  shows; the country start page also downloading the hip-hop index (the preload in index.html ignored the route);
  the Top 1,000 table (1.7 s of layout on the phone profile); 205 photos over 40 KB (up to 390 KB for a 250 px image,
  some PNGs named .jpg); seven flag SVGs of 35-184 KB shown at 16x12 px. Before/after numbers: __NUMBERS__
- **Index split** (`src/site_build.py`): artist fields that only the pages waiting for extra.json read (Scout, Money,
  Labels, Compare, Screener, Method...) moved to `extra.json` as `artist_more`, merged back into the artist rows by
  app.js when it arrives (`LATER`); those the artist page also shows are copied into its shard (`ALSO_SHARD`). The
  start page gets a precomputed `reach` (chart countries) instead of the per-country chart lists. Every use in app.js
  was grepped and mapped to its page before moving (re-checked just before the rebuild, as other sessions were adding
  pages). Rejected: dropping the fields no page read (age_profile, coverage, latest_release): new pages started
  reading them during this session, so they moved to `LATER` instead; one file per artist instead of 32 shards (more
  requests, little gain).
- **Top 1,000**: the first 200 rows render, a button shows the rest (sorting and the filter still use the full list).
  Rejected: content-visibility (does not apply to table rows) and drip-feeding rows (the table re-lays out each time).
- **Photos**: re-encoded in place when over 40 KB and at least a fifth smaller (JPEG q82; WebP with alpha when truly
  transparent): 43 MB to 26 MB; `src/photos.py optimise()` now runs on each new download. Commons licences allow it.
  The big artist photo loads eagerly at high priority; all photos carry width/height.
- **Flags**: svgo saved under 3%, so the seven largest (rs, mx, es, me, do, hr, gt) are now a 96x72 PNG inside an SVG
  of the same name (6x the display size; identical at 16x12): 557 KB to 23 KB. Other flags unchanged.
- **Caching**: `site/_headers` keeps fonts a week and flags, logos, photos a day in the browser; data, app.js and
  pages keep Pages' re-check on every visit (they change with each build).
- **Accessibility** (axe-core 4.10 on 13 routes at 1280 and 390): search box is now a combobox (aria-expanded was
  invalid on a search box); wide tables that scroll get focus and a name; empty table headings got hidden text;
  sortable headings take Tab and Enter/Space with focus kept; skip link; colour contrast passed.
- **SEO**: artist JSON-LD adds Wikidata/YouTube/Instagram/TikTok/X profiles we looked up, the Commons photo with
  credit and licence, the Wikipedia summary; label JSON-LD adds the Commons logo and its Wikidata item; labels are
  og:type website; static pages preload their data; sitemap has lastmod; `/country/` is now a real page (it was in
  the sitemap but had no file); `site/404.html` so Cloudflare Pages answers unknown addresses with a 404 instead of
  the start page with a 200. index.html: canonical and og:url.
- **Robustness**: a failed or broken data file shows "The data did not load" with a retry (it showed a raw JSON
  parse error, or nothing on in-site navigation); a failed extra.json is retried on the next page; unknown routes show
  "Page not found" (they showed the start page); an artist id from the other genre opens there; "Loading…" while a
  page waits for extra.json.

## 2026-10-26 New data sources: ListenBrainz built, MLC publishers built behind a login (task: "deep research on NEW data sources")

- **Research:** `docs/research/2026-10-26-new-data-sources.md`, about 25 candidates with terms quoted and live calls
  on ten of our artists, ranked.
- **Built: ListenBrainz** (`src/collectors/listenbrainz.py`, monthly step `listenbrainz`, both genres' top 1,000).
  - What it gives: listeners and plays per artist, for last month and all time, from ListenBrainz's open scrobble
    panel. Looked up by the registry's MusicBrainz ID, never by name.
  - Terms: CC0, commercial use allowed; one call a second.
  - Merged MusicBrainz IDs are followed to the current ID. The registry's Drake ID is one of them.
  - Top-listener user names are removed before a response is archived (personal data). Only totals are kept.
  - HTTP 204 means ListenBrainz has computed no listener stats for that artist (will.i.am gets 204 even for all
    time). It is stored blank, never as zero.
  - Coverage and fit with Spotify listeners: in the research note. It is an internal signal until the owner decides.
    The panel is small (Drake: 3,497 ListenBrainz listeners in September 2026), so only ranks and changes are useful,
    never the raw counts as an audience.
- **Built, not run: The MLC** (`src/collectors/mlc.py`, monthly step `mlc`).
  - What it gives: the publishers, their shares, administrators and parent publishers of each artist's 3 biggest
    songs, by ISRC.
  - Terms: "You may use the data in the Database for any lawful purpose".
  - Needs a free MLC Data Access Hub account, as the GitHub secrets `MLC_USERNAME` and `MLC_PASSWORD`. Without them
    the step logs "skipped".
  - The parser follows the published OpenAPI schema. It has not been checked against a live response; check it at
    the first run.
- **Workflow:** both steps are added to `monthly.yml`. The MLC step reads the two secrets.
- **Not built (owner):**
  - setlist.fm (free key, non-commercial, short caching only).
  - Ticketmaster Discovery (free key, no revenue from the API).
  - Last.fm (key plus Last.fm's written approval for public pages).
  - Audiomack (key issuance unclear).
  - Google Trends (alpha by application).
- **Rejected on terms or cost:**
  - Spotify city and viral charts (login).
  - YouTube Charts (robots.txt and ToS).
  - TikTok Creative Center (ToS 3.4).
  - Billboard (pay-per-crawl, HTTP 402).
  - ASCAP/BMI Songview (no API, terms unreadable to automated fetch; the MLC covers the same ground).
  - Apple Music API city charts ($99 a year).
  - Bandsintown and Songkick (as before).
- **Not wired into the site:** `src/site_build.py` and `site/app.js` are being edited by others. The research note
  says exactly what to show and where.

## 2026-10-25 YouTube Data API set up (owner: "Yes set up the YouTube data api")

- **What it gives:** for each artist's own YouTube channel, subscribers, total views and views a day. It covers 680
  of the 1,000 hip-hop artists with a known channel; kworb.net covers 255.
  - Channel IDs come from Wikidata, else the one youtube.com/channel/ link on the artist's MusicBrainz page (two or
    more: none taken).
  - Views a day: the change in channel views between today's reading and one 7–30 days old.
- **Where it shows:**
  - The artist page's YouTube tile, with source, method and window.
  - Compare, and Data coverage on Method.
  - The YouTube money line where kworb has no page: own-channel views × the YouTube rate (C). Fan uploads and other
    channels are not counted, so it understates.
- **Terms (YouTube API Services Developer Policies):** statistics are kept for 30 days at most and never as a history.
  - So `data/youtube_channels.csv` holds only the latest reading plus one earlier base per channel, and anything over
    30 days is dropped (`youtube_api.daily_rate`).
  - The file is not committed: this repository is public and git would keep every version, which would be a
    history. It lives in a GitHub Actions cache that the daily job writes and the site build reads.
- **Runs daily** in daily.yml (about 40 quota units a day of the free 10,000). The monthly step was moved there.
- **Needs from the owner:** a YouTube Data API v3 key added as the repository secret `YOUTUBE_API_KEY`. Without it the
  step is skipped with a log line, and the site shows kworb figures only. Views a day appear after a week of daily
  readings.
- **Rejected:** keeping a longer history for growth trends. It would need YouTube's audited-analytics approval
  (III.L).

## 2026-10-26 Product pass: 24 ideas, three built (task: "product development for the music site", overnight)

- **Ideas:** `docs/product/2026-10-26-ideas.md`: 24 ideas, each with its user, job, data, effort, value and risks,
  ranked, with notes on what is free and what a label or investor would pay for. The rest are in ROADMAP Phase 11 as
  "idea".
- **Chosen to build:** the three top-ranked ones that are small or medium, use data we already hold, and need no
  accounts and no money: a catalog screener, an artist one-pager and a data-quality page. One entry each below.
- **Rejected for now:**
  - "What changed this week": the daily log starts 2026-10-23, so a week has 3 days of data, and Movers already
    covers 30 days.
  - Watchlist digest: needs a week of log. The email version needs accounts (ROADMAP 10.5, a hard stop).
  - Embed widget: it widens the reach of Spotify-derived numbers before the licence gate (2.1). Owner's call.

## 2026-10-26 Catalog screener (`#/screener`, Money)

- **For:** investors and catalog buyers ("catalogs worth $X–Y, mostly evergreen, not with a major; export").
- **Shows:** the top 1,000 as catalogs.
  - Recordings + songs value: the mid, with the range under it.
  - The artist's multiple, and the age mix of the streams as a bar (new / 3–10 years / 10+ years).
  - Streaming royalties a year, what the artist keeps a year (range), monthly listeners and latest release.
  - Tiles for the selection: count, combined value with its range, median multiple, how many are mostly evergreen,
    how many are not with a major.
- **Filters:** value band, age mix (50%+ in a band), owner (incl. "not with a major"), royalties floor, country.
  Columns sort, with blanks last.
- **CSV:** every figure as low / mid / high, the multiple and its basis, the age shares and the dated share, then
  grade "C (estimate)", the data date and "indicative estimate, not a valuation".
- **Data:** everything was already in `index.json` except the value's low and high ends.
  - `src/site_build.py` now writes `worth_range` = recordings + publishing, low and high (two numbers per artist).
- **On the page:** a "How this works" panel with the multiples' sources and grades. It also says the owner shown is
  who releases the music now, not necessarily who owns older masters.
- **Rejected:**
  - Filtering on the multiple itself: the age mix is the input investors reason with.
  - A single "value" without the range: the house rule is that estimates are ranges.

## 2026-10-26 Artist one-pager (`#/sheet/<id>`, linked from every artist page)

- **For:** A&R and investors who attach a summary to a memo or signing note.
- **Shows:** one A4 page, in six blocks. Every row names its source and method, and money blocks carry grade C.
  - Audience;
  - label and deal;
  - earnings a year (streaming summed, other lines as on the artist page, artist keeps total);
  - catalog value (recordings, songs, both, multiple and age mix);
  - Scout factors with weights;
  - recognition.
  - At the foot: sources and grades, the data date and the page's address, so a printout keeps its caveats.
- **How:** "Print or save as PDF" uses the browser's print dialog. A new `@media print` block in `styles.css` hides the
  header, menus, buttons, player and "How this ranking works" on any page. Two columns on paper and on wide screens,
  one on phones.
- **Rejected:**
  - Generating PDFs in the build: 1,754 files, and the print dialog does the same for free.
  - Print styles on the full artist page alone: it runs to 4+ pages.

## 2026-10-26 Data quality and corrections page (`#/quality`, footer)

- **For:** everyone who has to trust a number (investors' diligence, press), and the ROADMAP's "honesty features as a
  selling point".
- **Shows:**
  - Coverage of eight main fields (count and share), plus the existing coverage table.
  - Open review queues per file: rows, and how many are still open after owner overrides.
  - First and latest date in each source file, with "late" when older than the source's usual cadence.
  - A corrections log.
  - The ranking method's versions.
- **New:**
  - `src/quality.py` (`queues`, `latest`, `sources`, `corrections`, `method_versions`, `summary`), written to
    `extra.json` as `quality` by `src/site_build.py`. Tests: `tests/test_quality.py`.
  - `registry/corrections.csv`: 17 corrections, each taken from an entry in this log (2026-10-25). Columns: date,
    genre, kind (data / method), subject, field, was, now, basis, source.
- **Rule from now on:** a correction to a published figure or classification, or a change to a money or Scout method,
  gets a row in `registry/corrections.csv` along with its entry here.
- **Rejected:** file modification times as "last updated": a fresh checkout resets them. The dates inside the files
  are used instead.

## 2026-10-25 YouTube: matching kworb pages by identifiers (task: "more artists with measured YouTube views")

- **Why most artists had no YouTube figure (top 1,000 hip-hop, 757 country):**
  - kworb has no YouTube page for them. Its archive lists 1,732 artists worldwide. All 1,732 pages were read once:
    1,559 link back to a Spotify ID, but only 253 of those are hip-hop and 31 country registry artists. A sample of
    missing hip-hop artists (A$AP Ferg, Sexyy Red, Vince Staples) returned 404 under their names too.
  - Pages that exist but have no link back to Spotify were never taken: 9 hip-hop artists.
  - Wikidata channel IDs were not used for matching (392 missing hip-hop and 202 missing country artists have one).
  - The archive was decoded as Latin-1 (no charset header), so accented names never matched (Maître Gims, L'Algérino).
- **Chosen:**
  - `data/kworb_youtube_index.csv`: every archive page with the Spotify ID it links back to. Each page is read once
    and kept in `raw/kworb/youtube/pages/`; only new archive entries are read on later runs.
  - Match on the artist's own channel. The channel ID comes from Wikidata P2397, else MusicBrainz url relations
    (`data/musicbrainz_youtube.csv`, `youtube.com/channel/` links only). The channel's public feed gives its latest
    uploads (kept in `raw/youtube/feeds/`). A match needs exactly one kworb page that lists one of those videos as
    the artist's own (not a feature) and links to no other Spotify ID.
  - Take a page with no link back when kworb's own page for the Spotify ID links to it.
  - The `match` column in `data/youtube.csv` records how each row was matched (`backlink`, `kworb_spotify_link`,
    `channel <ID> video <ID>`). Earlier rows are `backlink`.
  - Conflicts and name-only candidates go to `review/youtube_review.csv`, never into the data.
- **Result:** hip-hop 242 -> 255. 7 by channel (mgk, Fugees, Hungria Hip Hop, Maître Gims, Chris Jeday, Bad Meets
  Evil, JayDaYoungan), 3 by kworb's link, 3 by backlink. Country stays at 31: kworb has no page for the other 726.
  Six review rows: B.o.B, Macklemore, Macklemore & Ryan Lewis, Quavo (Migos page), and Ye (Kanye West page).
- **Rejected:**
  - Name matches without an identifier.
  - Filling `youtube_channel` in the registry from MusicBrainz. The registry column stays Wikidata P2397.
  - kworb video pages: they exist only for artists kworb tracks.
- **Left open:** the 745 hip-hop and 726 country artists still without a figure are not on kworb. 473 hip-hop and
  314 country have a channel ID. The YouTube Data API (key in Actions) gives their channel views and subscribers,
  but daily views need two snapshots, and keeping them is limited by the API's terms (no history without III.L).
  This is an owner decision.

## 2026-10-25 Country flags in every list (owner: "show the country flag each artist is from in all list formats / rankings")

- **Chosen:** a small flag after the artist's name in every list, ranking, search result, card and on the artist page.
  The country name shows on hover and is read out by screen readers. Up to two flags when an artist has two citizenships and
  neither matches the birthplace (Sleepy Hallow: Jamaica and the US).
- **Flags:** self-hosted SVGs from flag-icons 7.2.3 (MIT; licence in `site/flags/LICENSE`), 109 countries, 1.1 MB in
  all, loaded lazily. Emoji flags were rejected because Windows shows them as two letters.
- **Source:** the registry's country (Wikidata citizenship; with several, the one matching the birthplace). Names map
  to ISO codes in `src/countries.py`. Artists without a country on Wikidata get no flag, never a guess.
- **Fixed in the data:** two citizenships entered on Wikidata as places. "Karachi" becomes Pakistan (Talha Anjum).
  "Cina", an Indonesian subdistrict entered for Simba La Rue (an Italian rapper born in Tunis), is dropped rather
  than guessed.

## 2026-10-25 Money, artist, Scout and labels pages: the rest of the client review

Three parallel passes, one per section, on the reviewers' remaining findings.

- **Money:**
  - Sale-value tiles lead with the mid and name their base: recordings, songs, and recordings + songs. The last one
    ties to the tables (Drake $1.94bn on both).
  - The Pay page draws the same deal table, grades and sources as the calculator and artist pages. The joint-venture
    row is shown as a note, not a percentage.
  - The tours waterfall is defined before agent, manager and tax, as on the artist pages. Tour dates use one format;
    partial tours and co-headliners are named.
  - Platforms flags services whose totals are identical because they share a ratio to Spotify, and notes that
    YouTube is likely understated.
  - Label financials:
    - one money format;
    - outflows in brackets;
    - stale years flagged;
    - the latest period is picked by date, not by string sort.
- **Artist pages:**
  - Thousands separators in ranks.
  - YouTube says "not measured" rather than "no data".
  - Scout band wording.
  - Shazam places title-cased and the note built from the data.
  - Stale stream dates flagged.
  - A "Labels on record" fallback.
  - Phone layout: ranges on one line, each row's basis visible.
  - The Worth card says whether "Artist keeps" covers streaming only (no tour reported in 12 months) or streaming and
    touring.
- **Scout, unsigned and labels:**
  - One tier rule everywhere.
  - Blanks sort last.
  - "Signed" filter renamed "Any label deal".
  - The 15m+ band explains why it is empty under a tier filter.
  - The CSV export uses readable label statuses and names.
  - Unsigned peers are described as "active" rather than "growing".
  - Feature-only artists are greyed.
  - Month and labels shares are among artists whose label is known, as on the tiles. The State page uses the same
    basis (`src/state.py`).
  - Producers coverage is stated: 473 of 2,967 songs have a producer credit.
  - The "How this ranking works" box starts closed on phones.
- **Left for the owner (model or data changes):**
  - Valuing catalogues by release year instead of current share.
  - Re-grading the Spotify rate's high end ($4.40, unverified).
  - Better YouTube channel matching.
  - The catalog rule for acts with new hits only as features (Boef, Honaiser, Sidhu Moose Wala).

## 2026-10-25 Catalogue age, the Spotify rate, and the catalog rule (owner: "do all of the following")

- **Catalogue value by release age:**
  - **Before:** one multiple chosen from the artist's current share of listening.
  - **Now:** each of the artist's songs as lead is placed in an age band by its release date: new (under 3 years),
    mixed (3–10) or evergreen (10+). The multiple is the bands' sourced multiples (registry/catalog_multiples.csv),
    weighted by the songs' streams a day (`current.score` age_profile, `insights.blended`).
  - **Fallback:** under half the lead streams on dated songs uses the old current-share band (42 of 1,000 hip-hop
    artists).
  - **Effect:**
    - Drake: 28% new, 36% mixed, 36% evergreen gives 7.9–13.8×, was 10–17×. Recordings + songs mid $1.56bn, was $1.94bn.
    - Eminem: 87% evergreen, 9.6–16.4×.
    - Don Toliver: 65% new, 6.1–11.3×.
  - The worth calculator's "auto" uses the same blended multiple and shows the age mix. The band edges (3 and 10
    years) are our split; the multiples per band stay sourced. Method explains it.
- **Spotify rate:**
  - The high end drops from $4.40 to $3.60 per 1,000 streams. $4.40 was a US-only January 2026 blog figure and was
    not verified.
  - The middle stays at Duetti's 2024 figure for independent masters, $3.00, graded B; Spotify disputes per-stream
    figures. The source is now Duetti's own release, which says Amazon $8.80, Apple $6.20, YouTube $4.80, Spotify
    $3.00 per 1,000.
  - The $2.50–3.60 band around it is our estimate (C): lower for ad-supported-heavy listening, higher for US-heavy.
  - Every royalty high end falls about 18%, because the other services are set as ratios to Spotify. Method now reads
    the rate from the registry instead of hard-coding it.
- **Catalog rule:**
  - An artist with no release of their own in two years, but with collaborations or features on others' records in
    that window, is active. They are "not yet classified", with the reason, not "catalog". Boef and Honaiser: Deezer
    files all their recent releases as collaborations.
  - Sidhu Moose Wala's override goes from catalog to self-released (family/estate). Deezer lists posthumous singles
    on his own label: Kaali Hoodie 2026-10-16, Ghostface Killah 2026-09-21, Barota 2025-11-28.

## 2026-10-25 Who counts as unsigned: prospects and established independents (owner)

- **Owner's note:** "not sure if stem and independent should count as unsigned as it seems they are established
  artists and wouldn't bring any value to help understand if up and coming artists are unsigned ... need a better
  solution". An earlier answer that day ("count stem and independent as unsigned") is replaced by this entry.
- **Chosen:** self-released artists are split in two (`labels.independent_kind`).
  - **Established independent:** any one piece of evidence is enough.
    - a record label on Wikidata's career-long list (a label or a major, not a distributor or the artist's own name);
    - own recordings, as lead artist, registered by a major (ISRC prefix);
    - 8+ years of releases (Wikidata's "active since", or the earliest dated song as lead).
  - **Unsigned prospect:** the rest.
  - Hip-hop: 38 prospects and 101 established (Jeezy, Lil Pump, KYLE, Meek Mill, Russ, D-Block Europe, among
    others). Each established artist shows the evidence that placed them.
- **Where it applies:**
  - Only prospects appear on the Unsigned page (established independents are listed apart, at the end), under
    Scout's "Unsigned" filter ("Any self-released" keeps them all), and in the "Top unsigned prospect", "Unsigned and
    worth a look" and "Unsigned and rising" picks.
  - Market shares still count every self-released artist, because they measure who owns the listening.
- **Limits:**
  - Wikidata covers established acts better than new ones, and Deezer dates can be reissue dates.
  - So a prospect can be an older act with thin records. The evidence is shown so it can be checked.
  - 8 years is a judgement, set in one place (`labels.ESTABLISHED_YEARS`).
- **Licensed out (owner: "be clear about the licensed out method in the method tab"):** the licensee decides.
  - A record label (Atlantic, Ministry of Sound): signed to that label.
  - A distribution service that leaves the masters with the artist (UnitedMasters, Stem, DistroKid, TuneCore, CD
    Baby, Amuse, Too Lost): self-released.
  - ONErpm offers both distribution and label-services deals with advances, so a licence to it is flagged "licensed
    out", not decided.
  - Written out on Method, under Labels.
- **"Label Deal" (owner: "get clarity around the label deal language"):**
  - Found only on D-Block Europe's 2026 releases on Deezer ("D-Block Europe Label Deal"). It is not a company. No
    published definition was found, and Apple does not list the 2026 album.
  - Our reading: the artist's own imprint as set up in a distributor's or partner's system, so a deal sits behind it
    without the partner being named.
  - Evidence:
    - the 2026 recordings carry registrant US-A2P, also seen on Rostrum Records and BIGHIT MUSIC releases, so a
      third party registered them;
    - earlier own recordings were registered by Universal (2019);
    - "Prada" (2023) was released "under exclusive license to Ministry of Sound Recordings" (Apple);
    - Wikipedia lists D-Block Records, EGA Distro (distributed by Virgin Music Group) and Caroline as their labels.
  - So they are an established independent with a partner deal, not an unsigned prospect. Stated on Method.

## 2026-10-25 Lists, start page and compare: the rest of the client review

- **Search:** results say "#205 by monthly listeners" (or "by streams" below the floor), not a bare "#205". Label
  results say "in our list", which fits the 754-artist country list.
- **Start page:**
  - The "Right now" riser card names its scope: "1m+ listeners".
  - "387 of 1,000" has a thousands separator.
  - The list intro reads "We track the 1,000 biggest hip-hop and rap artists among Spotify's top 25,219" instead of
    implying exactly 1,000 qualify.
- **Status words:** "Self-released" everywhere (it was "Unsigned" in one list and "Self-released" in another). An
  unknown label reads "not yet classified" instead of "–". "Catalog" explains itself on hover.
- **Scout tier chips:** hovering a tier explains it, so "93 Rising" next to "90 Breaking" makes sense.
- **Movers, 30 days:**
  - Says it covers the 260 artists with a month-ago figure, not the whole 1,000.
  - Each row shows its own window in days.
  - The "30 days ago" share column is hidden until it has values.
- **Compare:** the same artist can't be picked twice. On phones the table fits the screen, so the names stay
  visible.
- **Two Spotify profiles named "Macklemore & Ryan Lewis":** the smaller one is labelled "(second Spotify profile)".
  Its page address is unchanged.
- **Country floor list:** the heading reads "Places 755–1,000: further artists below the 500k line, in Deezer's
  order".

## 2026-10-25 Review through a client's eyes: numbers that read right (owner: "scrutinize the entire site ... so all is clean and user friendly")

Four reviews read every page as an investment-banking client would. Fixes:

- **Facts:**
  - **Grammys:** an award won in several years for several works no longer multiplies into every year × work pair.
    Awards are grouped per Wikidata statement.
  - **Country of origin:** an artist with several citizenships shows the one matching their birthplace, else all of
    them. Drake shows Canada, his birthplace; Sleepy Hallow shows "Jamaica / United States". Names are normalised ("Kingdom of the Netherlands" -> "Netherlands").
  - **Duplicates:** a below-the-floor name matching an artist already listed is left out.
  - **Deals:** entries that are not the artist's own income (another artist's contract, a lawsuit) move to a
    "context" list under the artist's deals; legal filings are labelled as such.
  - **Certifications:** releases from "as featured artist" tables are marked "as featured guest". The US No. 1s
    tile counts lead releases only, with guest No. 1s noted beside it. 115 entries whose cached page no longer parses
    the same keep their stored works, without the mark.
  - **Labels:** HYBE America's Nashville labels (Big Machine / Blue Highway, Valory, Nashville Harbor) are grouped
    under Universal, their distributor, as every other major-distributed label is. The note keeps HYBE's ownership.
  - **Owner's genre notes:** internal notes (such as the "hip-hop rule:" ones) are no longer shown to visitors. An
    owner's decision reads "checked by our editors".
- **Numbers:**
  - **Spotify royalties:** under $1,000 a month shows as "<$1k". An artist whose streams are 90%+ as a featured guest
    is marked "own songs only".
  - **Zeros and ranges:** a missing estimate shows "–" or "not estimated", never "$0". A range whose ends round to
    the same figure shows once. Negative money reads "−$5.0m". A share under 1% shows "<1%". Margin changes are in
    percentage points.
  - **Pandora:** now counted in the country streaming total, where it is a large line.
  - **Chart countries:** a country where the artist charts on both Spotify and Apple counts once. This also changes
    the Scout "chart reach" signal and the "Global" badge (20+ countries), which had counted such countries twice.
  - **Majors' share:** taken among artists whose label is known, the same basis as the size-band tiles.
  - **Movers today:** "outside the top 100" means the top 100 by monthly listeners, whatever view the list is in.
  - **Summed listeners:** described as summed across artists (a fan of two counts twice), not "people counted once".
- **Wording:**
  - **Rankings:** "#N by current listeners" replaces "#N in our ranking".
  - **Catalog acts:** an artist with no current listeners is described as a catalog act, not shown as 0.
  - **Royalties:** "Spotify royalties / month" and "streaming royalties / year, all services" are named apart. The
    top-100 column "Artist keeps" says it includes tours.
  - **Worth calculator:** an artist whose deal is not on record gets "Deal unknown", whose range spans all four
    deal types, rather than the DIY share.
  - **Scout tier tiles:** say Breaking needs new songs or Wikipedia attention clearly up, and that Rising is 65+.
  - **Levels:** an artist under 5m listeners active for 15+ years is "Established", not "Rookie".
  - **Method page:**
    - The deal type follows the recent releases' label.
    - The back-test is described as done.
    - Archived listener pages are described as used for the back-test and growth only.
  - **Platform pay rates:** revenue basis strings print the registry's rates, not a hard-coded $1–6.
  - **Country pages:** the hip-hop listener-survey panel is no longer word-swapped into false country facts. It is
    hidden on country pages.
  - **Bertelsmann and Sony notes:** corrected.

## 2026-10-25 A change to requirements.txt redeploys the site

- **Asked:** "Yes add to package list" (owner). Merging the Pillow fix did not start a deploy, because the site
  workflow ran on pushes to site/, src/ and registry/ only.
- **Chosen:** `requirements.txt` is now one of the paths that start the site workflow.

## 2026-10-25 Pillow in requirements: the site deploy failed since this morning

- **What failed:** the site workflow, every run since 09:54 UTC. `src/static_pages.py` draws the share cards with
  Pillow, which `requirements.txt` did not list, so the build stopped and nothing deployed (the logo and header
  changes waited too).
- **Fix:** `pillow==11.0.0` in `requirements.txt`. The full build passes with it in a clean environment.

## 2026-10-25 The logo leads to tventy.se; the section word is a label

- **Asked:** "Don't make the music and sport words clickable anymore … Pressing tventy should bring you back to the
  sport or music choice page" (owner).
- **The logo** links to https://tventy.se/, the choice page; "music" under it is plain text. Artists, the first tab,
  is this site's home. The sport site has the same change.

## 2026-10-25 Logo and tab icon: the circled t of tventy

- **The logo: the wordmark with its first "t" white in a filled circle** (owner, 2026-10-25), drawn from the site's
  own font (Bricolage Grotesque, bold). The header shows it at the old wordmark's size and baseline, and the circled t
  takes the page colour.
- **The browser tab icon is that circled t.** It is a white t in a near-black circle, so it reads on light and dark
  tabs. Files: `site/favicon.svg`, `site/favicon.png` (32 px, for Safari) and `site/apple-touch-icon.png` (180 px, for
  phone home screens). They are the same files as the sport site's.

## 2026-10-25 Contact address hello@tventy.se

- **hello@tventy.se replaces swedenrocked@gmail.com** in the User-Agent of every collector, the site footer and the
  working agreement (owner set up tventy.se mail, 2026-10-25; the same change in the sport repository).

## 2026-10-25 Fixes from a second independent review

- **Wikipedia quotes:** the country pages' word swap ("hip-hop" -> "country") no longer touches the quoted
  descriptions. Shaboozey's "country, Americana, and hip-hop" had read "country, Americana, and country".
- **Sentence cutting:** "2010s.", "R&B." and "D.C. He ..." now end sentences; "the U.S. Army" does not; nested
  brackets are removed. The full opening paragraph is stored, so the cut is redone at every build without
  refetching.
- **Country top list, our ranking:** below-floor artists follow the ranked ones at their place (399 onwards),
  instead of being missing and listed as "missing release dates". The sentence under the title now counts only the
  398 artists on Spotify's public list, and names the 359 below it separately.
- **Worth calculator:** a below-floor artist is compared with artists of a similar size by daily streams / 0.10, the
  build's internal measure; the box shows "under 500k". Artists with no stream figure can't be picked.
- **Scout:** a size filter for "under 500k (by streams)".
- **Unsigned and compare pages:** below-floor artists show "under 500k" rather than "–".
- **Two Deezer pages, one Spotify artist** (Hank 3 / Hank Williams III, Bellamy Brothers, Charlie Daniels): the
  artist ranks by the bigger page, and the second page no longer shows in the names list.
- **Country links:** in-site links carry the genre prefix, so a link opened in a new tab or followed by a search
  engine reaches the country page. Found by a page crawl: 24 country label pages opened empty that way.
- Composed descriptions say "from the United States".

## 2026-10-25 Artist descriptions and "How this ranking works" (owner)

- **Descriptions:** each artist page opens with one or two sentences. Source: the opening of the artist's English
  Wikipedia article (page summary API; the article is the one Wikidata links, no name matching), cut at the second
  sentence or 320 characters, birth-date asides removed, credited "Wikipedia, CC BY-SA" with a link
  (`src/collectors/descriptions.py`, step `descriptions`, monthly). Artists without an article get one sentence
  composed from our own sourced fields (genre, Wikidata country and start year, the label on recent releases),
  marked by having no Wikipedia credit. Also on the static artist pages.
- **How this ranking works:** a box under the introduction of every ranked page (top list, movers, Scout, unsigned,
  producers, labels, tours) lists the metrics, what each measures and its weight; Method keeps the full detail.
  The current-listeners age cut-offs stay described in general terms ("older songs fade out as they age"), as
  decided on 2026-10-23; Scout's weights come from the data, so the box follows any change to them.
- **Later (ROADMAP 10.5):** accounts to star and track artists across devices; planned with the owner first.

## 2026-10-25 White page, black text, as tventy sport (owner)

- The owner asked for the same font and style as tventy.se/sport, with the white background and black text. The site
  already shared sport's font (Bricolage Grotesque), layout and square boxes; the tokens in `site/styles.css` now take
  sport's values (white page, black text, #5a5f68 secondary text, #e7e9ee lines, #f6f7f9 fills, green #15803d and red
  #b91c1c for up and down), and the page asks the browser for the light colour scheme. This replaces the inverse
  (black) theme of 2026-10-24.
- The labels share bars run dark to light on the white page; groups outside the fixed order (HYBE America in
  country) now get striped shades instead of a missing one. Share cards (PNG) are white with black text too.

## 2026-10-25 Country top 1,000 at the same depth as hip-hop (owner: "a list of top 1,000 country artists robust with all information possible")

- **Places 1 to ~395:** monthly listeners from kworb's public list, as before.
- **Below kworb's 500k-listener floor:** artists from the Deezer related-artists crawl now go through the full
  pipeline instead of being a Deezer-ordered name list (grade C):
  1. Spotify ID looked up at the source: Wikidata (P2722 -> P1902) or MusicBrainz, where one MusicBrainz artist links
     both the Deezer and the Spotify page (`country-ids`; `musicbrainz.ids_for_deezer`). Never guessed from a name.
  2. Identity confirmed a second way where possible: the artist's biggest songs on kworb must be among the Deezer
     artist's top tracks (`country-floor`), the same check `country-from-crawl` uses. kworb has no page for most of
     these artists (125 of the first 153), so there the link at the source confirms the identity alone (Deezer match
     type "links"); songs that contradict the link reject it.
  3. The registry decides the genre by the usual rules (Deezer release genres, Wikidata, MusicBrainz votes, owner
     overrides); nothing is let in on the crawl's word alone.
  4. Ranked by measured daily Spotify streams (kworb artist pages, the same figure behind the money estimates). kworb
     refreshes small artists' pages irregularly (some were last updated in December 2025), so a page counts for the
     ranking only if updated in the last 60 days; older ones wait in the name list for kworb's next update.
- **What these artists do not get:** a monthly-listener figure (none is public below the floor; shown as "under
  500k"), listener change, current listeners and listener history.
- **What they do get:** everything else hip-hop artists get (streams, labels, photos, release dates, certifications,
  awards, credits, money estimates, Scout).
- **Comparisons:** Scout compares them only with each other (a separate "under 500k (by streams)" band). Peer
  comparisons use daily streams / 0.10, the median streams a day per monthly listener of country artists between
  500k and 1.5m (167 artists; quartiles 0.087-0.123). That figure is internal and never shown.
- **Supersedes** this morning's answer 3 ("no money below the floor"): the money lines rest on measured streams, like
  everyone else's, so they are shown, as ranges.
- Order below the floor: first the artists kworb measures (daily streams), then the rest in the Deezer crawl's
  order (grade C, as before) but with the same data as everyone else apart from the stream-based figures (no money
  lines, no listener-based Scout signals). The 1,000 is complete only as far as crawl artists have a Spotify ID linked
  at the source; the remainder stays in the Deezer-ordered name list.
- Genre review of the new below-floor artists (owner: "carry on as suggested with the uncertainties"): 50 of 53
  decided as suggested, country except The Wild Feathers (Americana rock: other); country covers Americana,
  bluegrass, alt-country and country rap (Savannah Dexter) as before. Beauxmont (no genre data), Ceol and LEW stay in
  review.
- What would measure everyone: the Spotify Web API (followers, popularity) or Last.fm (listeners), both waiting on
  keys (K1).

## 2026-10-25 Owner's answers to the overnight questions ("go with suggested for all")

1. Country ranks below the 500k floor: shown as now (names in Deezer order, grade C, no figures).
2. Country scope: any nationality.
3. No money figures for the below-floor ranks.
4. Country review batches: the suggested answers are now owner overrides in `registry/genre_overrides.csv` (batch 1:
   47 rows; the 3 marked "look up": STELLA LEFTY country (owner); Buffalo Traffic Jam country (folk/country duo
   from Bozeman, ticketing lists Country, toured with Dylan Gossett:
   https://www.axs.com/fr/artists/1121645/buffalo-traffic-jam-tickets); Joseph Williams other (the Spotify profile is
   Toto's singer, top songs from The Lion King, per kworb). Batch 2: 6).
5. Hip-hop/Deezer disagreements: Lizzo, blackbear, August Alsina and Jackson Wang to other; the other 7 confirmed
   hip-hop.
6. Curb Records and Santa Anna stay "distributed by a major".
7. kworb radio and Country Aircheck figures stay internal.
8. The four low-confidence label leads (G-Unit, SODMG, Master of None, Blacktop) stay unapplied: unknown.
9. Oranj and UnitedMasters releases stay self-released.
10. Hayden Blount, Token and Aitch stay unsigned until a better source turns up.

Effect after the registry run: country 375 -> 395 artists (20 from review), 33 review artists to other, the hip-hop
list loses 4 and takes the next four by listeners. Streams, labels, photos and release dates were fetched for the new
country artists; unknown country labels are now 37 of 395 (three new ones among the 20).

## 2026-10-25 Fixes from an independent review of the overnight changes

- "based on:" and "newest release" only where the status rests on releases; with an override or an unknown or
  catalog status the note reads "latest:" as before (Yung Lean's override said "based on: Yung Lean").
- Nested label patterns: a shorter pattern is dropped only when it matched inside the longer one, so a string naming
  two labels ("Universal Music Distribution / Universal Music") keeps both. No label string we hold changes.
- Tours page: no crash when a genre has no counted tours.
- Dylan Gossett (was a pending owner question): the Mercury deal is now sourced (Big Loud Texas / Mercury Records,
  Nov 2023; UMPG's 2025 release names the label), so he gets an override like Tucker Wetmore's: major-distributed,
  UMG. He leaves the country Unsigned list.
- Same check on the rest of the country Unsigned list's own-name strings: Kip Moore (Virgin Music Group global deal,
  2024: major-distributed) and Cole Phillips (RECORDS Nashville / Columbia, 2024: major) get sourced overrides. Hayden
  Blount's reported Santa Anna distribution deal rests on venue bios only: for the owner. Will Dempsey is described
  as independent; Treaty Oak Revival stays self-released.
- Hip-hop Unsigned list, same check: Key Glock signed with Republic in March 2025 (Glockaveli via Paper Route Empire /
  Republic), so he gets a sourced override (major, UMG). Token stays: Atlantic distribution from 2020, but his recent
  releases credit his own imprint and a 2026 one Fenix Music; for the owner if wanted. Aitch stays too: his 2025 album
  is on his own Infinitum per Wikipedia, NQ Records / The Orchard (Sony's distributor) per Dork; for the owner.
- Deals notes starting with a quote mark are capitalised.
- Reproducible builds: ties between owners (`max(set(...))`) depended on Python's per-run string hashing; they now go
  to the first seen. Two builds with different hash seeds now differ only in the build time.

## 2026-10-25 Smaller fixes (overnight)

- Static country pages said "top 1,000" (the in-page word swap does not run on static pages): State of country now
  reads "top 375", label pages "the country list".
- Unsigned list: artists placed by a sourced override (Jeezy: self-released through Stem) showed a blank label; they
  show the override's distributor.
- Reported deals read as sentences with the amount in bold.
- `review/hiphop_deezer_disagree.csv`: 11 hip-hop artists whose MusicBrainz votes say hip-hop while a confirmed Deezer
  match files under 15% of releases as Rap/Hip Hop (Black Eyed Peas, Lil Nas X, Lizzo, blackbear...). Nobody moved:
  the hip-hop rule is the owner's; suggested answers are in the file (other: Lizzo, blackbear, August Alsina, Jackson
  Wang; the rest stay).

## 2026-10-25 RIAA Latin certifications kept apart; label batch 8

- Wikipedia's "RIAA: 96× Platinum (Latin)" was read as 96 main Platinum awards. Latin Platinum is 60,000 units, not
  1 million, so Bad Bunny's "Mía" (feat. Drake) topped Drake's list and his RIAA Platinum total read 705 instead of
  575. Latin awards are now marked `latin`, carry no units, are left out of the RIAA Platinum total, weigh 0.06 of a
  Platinum in the ordering, and show as "RIAA 96× Platinum (Latin)". 31 awards across 10 artists.
- Label batch 8 (40 of the biggest unknowns): added jungeratze (Ski Aggu; UMG partnership, medium) and Ollywoo
  (Oliver Anthony, self-released via DistroKid, medium). Not applied, low confidence, for the owner if wanted:
  G-Unit Records (Caroline/Capitol deal of 2014, nothing newer), SODMG (Virgin 2021, nothing newer), Zac Brown
  Band's Master of None (one 2025 mention of Warner Music Nashville), Clint Black's Blacktop (Thirty Tigers since
  2015). The rest name only the artist's own company on the ℗ line, with no distributor found.

## 2026-10-25 Newest release shown beside the label basis

- The artist page's "latest:" line showed the release the label status rests on, not the newest one (Charley
  Crockett: Island in April 2026, though his July album Clovis is on Atlantic Outpost). It now reads "based on: ...",
  plus "newest release: ..." when the newest lead release carries another label string.
- Considered: letting the newest release decide. Rejected: of 28 artists whose newest release disagrees with the
  majority, most are own-name imprints on a signed artist (Gunna Music, NF Real Music II), so the majority stays.

## 2026-10-25 One Wikidata genre no longer outweighs Deezer's releases

- 28 country artists rested on a single Wikidata genre ("alternative country" is Wilco's only P136 value). New guard,
  the mirror of the arabesque one: when Wikidata says country but a confirmed Deezer match files under 30% of 5+
  releases under Country, the artist goes to review. Moved to review: Wilco, Rusted Root, She & Him, The Avett
  Brothers, The Handsome Family. Tyler Farr also moved, on his MusicBrainz votes (50% of 4), not on this rule;
  both are in the owner's review queue. Country list: 381 -> 375.

## 2026-10-25 Distribution-deal strings and nested label patterns

- "Universal Music Distribution Deal", "Universal Music Distributed Deals", "Universal Music Division Virgin Records
  Distribution Deal" and "Universal Music MENA Distributed Labels" counted as UMG labels (major) because the generic
  `universal music` row matched first. The strings themselves say distribution deal, so they are now
  major_distributed (structural rows, no outside source needed). 87 releases change; no tracked artist's status or the majors' shares move.
- Rule change in `classify_label`: when one matching pattern contains another ("universal music distribution" contains
  "universal music"), the longer one wins. Different labels in one string ("10K Projects/Capitol Records") still
  rank by status as before; a full check of every label string we hold changed only the strings above.
- "Sony Music Nashville" gets its own row (it showed as "Sony Music (local)").

## 2026-10-25 Page fixes from a phone-width pass (overnight)

- Tours: the page listed both genres' tours (the country page led with Kendrick Lamar); now only artists in the
  genre's list. All 48 counted tours still appear on one of the two pages.
- Stacked tables: the `.stack` rule for the share bar also hit every `table.stack`, squashing those tables to 18px
  (tours, credits, certifications, collaborators, label tables, the audience questions). The bar rule is now `div.stack`.
- Artist page Peak tile: artists below kworb's top 2,500 have no peak rank (the 25k pages carry none); the tile said
  "best rank #null".
- Hidden panels: `.panel`'s display rule beat the `hidden` attribute, so the deals panel showed as an empty box on
  artists without deal figures. A global `[hidden] { display: none !important; }`.

## 2026-10-25 "PS/" label strings

- Some UMG releases name the artist, then "PS/", then the label ("Charley Crockett PS/ Island", "Wale Music PS/ Def
  Jam"). The "island records" pattern missed "PS/ Island", so the rule that the label string carries the artist's
  name won, and Charley Crockett showed as unsigned. New rows: `ps/ island` and `ps/ def jam` (UMG, major), sourced
  from the Deezer album pages and the 2025 Island signing. His 2026 album Clovis is on Atlantic Outpost (Warner),
  already in the table.

## 2026-10-24 Country labels (overnight research)

- 69 sourced rows in registry/label_owners.csv, mostly from the ℗ lines of 2025-26 releases on Deezer's public album
  pages, checked against press and Wikipedia. Each pattern was tested against every label string we hold and matches
  only its own label.
  - UMG: Lost Highway (revived 2025), UMG Nashville, Capitol Nashville codes, Keith Urban's and Miranda Lambert's
    imprints and Reba's Rockin' R (all licensed to UMG), Wyatt Flores's OEG/Island string, Dot.
  - Distributed by a major: Sun Records (Primary Wave via Virgin), 5&2 (Capitol CMG), Music Soup and Darkroom
    (Interscope), Back Blocks (UMG Nashville), Walk Off, Gaither and ATO (Virgin/Caroline); Triple Tigers, Black
    River, Fugitive, Quartz Hill, Riser House and Reviver (The Orchard / Sony RED); HEY NOW (Kenny Chesney's new
    label), Bigger Picture and Curb (Warner).
  - Independent: Thirty Tigers labels (Big & Rich, Bossier City, Southeastern, Velvet Rose...), Rounder and PULSE
    (Concord), New West, Firebird, Stem, Average Joes, Dualtone, Leo33, StarVista, Many Hats, catalog labels.
  - Self-released: DistroKid's numbered names ("12496410 Records DK", "...DK2"), which also places some hip-hop
    artists.
- Tucker Wetmore: label override (his releases name only himself; he signed with UMG Nashville through Back Blocks
  in May 2024, sourced).
- **Batch 2:** 12 more rows (Thirty Tigers: Ol' Buddy, Lock13, Love Big, 3 Legged; Stem: Bill Grease, Mom & Daddy's
  Money, Igniton, OurVinyl; Craft Recordings (Concord); Dreamcatcher Artists; Better Noise; Santa Anna Label Group,
  Sony's joint venture with Todd Moscowitz, read as distributed by a major like Triple Tigers). Don Williams:
  catalog override (his Deezer page mixes in unrelated uploads; his real releases are Craft reissues). The rest are
  own imprints with no distributor named (Brett Eldredge, Randy Houser, Conner Smith...).
- **For the owner:** Curb is Mike Curb's own label but Warner distributes it, so it reads "distributed by a major";
  say if ownership should decide instead (independent).
- Still unknown: imprints whose ℗ line names only the artist (Treaty Oak Revival's TOR, Zac Brown Band's Master of
  None, Kip Moore, Tenille Townes...). Two Turkish labels Deezer files under Country are not country.

## 2026-10-24 Country list built (overnight; owner C1-C5)

- **Who is in (above Spotify's public 500k floor): 386 artists.**
  - The registry's country rule (src/genre.py: 60%+ of MusicBrainz votes, 60%+ of Deezer releases filed under Country
    with the artist's identity confirmed, or two-thirds of Wikidata genres) placed 255, plus Jelly Roll by the owner.
  - 71 more were held for review only because Deezer matched them by name alone (no Wikidata entry). Their identity
    is now confirmed from the songs: at least two of the artist's five biggest songs on kworb are among the Deezer
    artist's top tracks (`confirm-country`). A confirmed match counts like a Wikidata one.
  - 68 more were never candidates: no Wikidata country tag and outside the hip-hop candidate set, so no Deezer genre
    row (Luke Grimes, LOCASH, Ian Noe, Lukas Nelson, Hailey Whitters...). The Deezer crawl found them; a crawl name
    that matches exactly one artist on kworb's listener pages is confirmed from the songs the same way
    (`country-from-crawl`, 73 of 73) and then decided by the same rule.
  - 88 borderline artists remain for the owner (review/country_review_batch1.csv has the 45 biggest with suggested
    answers: Taylor Swift, John Denver, Darius Rucker...). Turkish acts that Deezer files under Country (Ibrahim
    Tatlises, Ozcan Deniz...) stay out.
- **Below the floor:** 598-666 artists from the crawl, in Deezer track-popularity order, shown as names only
  (grade C); see the C1 entry. Presentation pending the owner (suggested: as now).
- **On US radio** (artist pages, both genres; hip-hop money unchanged): our own rank among the country artists on the week's airplay chart
  ("#2 of the 24"), from kworb's audience estimates; the audience figures themselves stay internal (C4).
- **Guard:** Deezer files some Turkish arabesque under Country (Müslüm Gürses, Ferdi Tayfur were in the list). A
  Deezer-only "country" now goes to review when the artist's Wikidata genres name no country genre. That also sent
  Ingrid Andress, Tenille Arts and Joseph Williams to review; all five are in the review batch (country: 381).
- **Listener history for country:** the Wayback backfill now keeps country artists and stores only artist-weeks it
  does not hold yet; `backfill-refetch` (workflow "backfill", input refetch) re-reads every archived week once so the
  country artists get the same 90-day growth history as hip-hop.
- **Shazam country charts:** the world and US country charts join the daily Shazam read (Canada, Australia and the UK
  have none). Country artists on a Shazam chart: 1% -> 19%. The badge now names the genre chart ("#1 country in
  world"); it never did for hip-hop because of a wrong key, fixed.
- **Kept fresh:** the monthly workflow runs every per-artist step for country too, plus `countrycrawl`,
  `country-from-crawl` and `confirm-country`; the daily Scout log records country scores.
- **MusicBrainz dates** were stopped for country tonight: the step works through every unlooked-up ISRC in the shared
  song cache (36,000 at one a second, about 10 hours). Deezer already dates 7,287 of the 7,526 country songs; the
  monthly workflow keeps working through the backlog within its 75-minute limit.
- **Copy:** on country pages "top 1,000" reads as the real list size and "hip-hop or rap" as "country".

## 2026-10-24 Country tours (overnight research)

- registry/tours.csv gains 52 country rows: 22 reported grosses (grade A: Billboard year-end 2025 and midyear 2026,
  Billboard's NFL-stadium list, Pollstar box office) and 30 context rows for tours with no reported total.
- Billboard's year-end 2025 figures end 2025-09-30, so they fall outside the last 12 months; what counts now:
  Luke Combs $86.5m (three reported runs), Chris Stapleton $73.5m (summer 2026 leg), George Strait $28.4m (Lubbock),
  Treaty Oak Revival $26.7m, Tim McGraw $13.5m, Lainey Wilson $12.4m, Zach Bryan $10.2m (one reported show), HARDY.
- Hip-hop, Oct 2025 to now: Billboard's midyear 2026 rap top five (Travis Scott, Cardi B, YoungBoy, Kendrick Lamar,
  Wu-Tang Clan) are already in existing rows except Wu-Tang ($16.9m, added). Billboard's monthly reports for
  April-August 2026 name no other rap tour; J. Cole, Post Malone, Don Toliver, A$AP Rocky and Playboi Carti have no
  reported 2026 gross yet (Pollstar per-city averages are not used).
- Not estimated: Morgan Wallen's 2025 and 2026 stadium tours and most of Zach Bryan's 2026 tour have no reported
  gross anywhere (projections and per-night averages are not reports). Billboard's year-end 2026 (about December)
  should fill most gaps.

## 2026-10-25 Bug review of the overnight changes (fixed)

An independent read of the branch found, and these were fixed:
- Country pages broke after a search on the hip-hop side had loaded the country list (its page data never loaded).
- Links to the monthly State page and Method from country pages went to the hip-hop versions; the share link and
  footer named hip-hop.
- Deezer corrections (audit, ISRC) changed the artist's Deezer ID but not the genre row read by the genre rules; the
  genre row is now re-read from the corrected artist (9 repaired; no genre decision changed).
- The country list below the 500k line repeated a few measured artists (a second Deezer profile, or an ID matched
  outside the genre table); it now excludes every registry Deezer ID and any name on kworb's listener pages.
- Label names ignored the dated rows (Big Machine after February 2026 showed as HYBE's group).
- Confirmation steps could lose all progress on one failed kworb page; a partial `countrycrawl N` replaced the whole
  file; an ISRC answer without an artist crashed; song titles were cut at " with " ("Stay With Me" = "Stay").
- Known and kept: the registry keeps a stored photo or Wikidata item when Wikidata later drops it (refreshed only
  when Wikidata gives a new one).

## 2026-10-25 Certifications from French and German Wikipedia (overnight)

- When an artist's English discography has no certifications, `src/collectors/certifications_frde.py` reads the
  French and German pages, found through Wikidata's sitelinks and the article's own links (never guessed titles).
  French: the discography templates, tables with a Certifications column and flagged list items (France -> SNEP,
  Belgique -> BEA, Suisse -> IFPI Switzerland...); an unflagged French certification first in its cell counts as SNEP.
  German: `{{Charteintrag}}` rows (A_DE, A_AT, A_CH, A_FR, A_IT... and codes like G, 3P, D+5P).
- One wiki per artist (the one with more certifications), so each entry has one credit; every entry stores its
  language and the panel credits "French/German/English Wikipedia" (CC BY-SA).
- Hip-hop top 1,000 with at least one certification: 503 -> 599 (85 from German pages, 11 from French).
  Spot checks matched the pages (Werenoi, Luciano, Salmo, Gazo, Tayc).
- The English parser read the year as the title in tables that put the year first (Booba, Damso, SCH, Ninho, Jul...);
  fixed, nothing lost (23,950 -> 24,420 certifications on the cached pages).
- Panel: where there is no RIAA Platinum, the headline tile is the main body ("SNEP: 81 certifications"); releases
  sort Diamond over Platinum over Gold for any body; the US peak column shows only when there are US peaks.
- **Wikidata items from MusicBrainz** (`wikidata-from-mb`, monthly): 296 artists in the two lists had no Wikidata item
  carrying their Spotify ID but had a MusicBrainz ID; MusicBrainz's curated Wikidata link gave 135 of them. The
  registry keeps these, and awards and photos now read the stored item (photos: hip-hop 615 -> 672, country
  206 -> 235). Artists with certifications: hip-hop 599 -> 646,
  country 195 -> 238; awards: hip-hop 102 -> 110.
- Kanye West's lookup followed Wikidata to his production discography (records he produced for others); production
  discographies and videographies are now skipped, and his entry reads his own albums discography (488
  certifications).

## 2026-10-24 Label research batch 4 (overnight) and Deezer IDs from ISRCs

- **Shared names:** 18 artists in the top 1,000 (Aminé, City Girls, Luciano, Eve...) had a Deezer name that several
  artists share, so their labels were never read. Their Deezer ID is now confirmed from their own songs: Deezer's
  `track/isrc:<code>` for their 5 biggest songs as lead; the same-named contributor on at least 2 of them
  (`python -m src.run deezer-isrc`, match "isrc"). No name guessing.
- **Batch 4:** the 45 biggest unknown label strings, read from the ℗ lines on Deezer's public album pages plus
  press and Wikipedia. 14 rows added (each sourced in registry/label_owners.csv): Capricarolesque, Just Woke Up and
  Groove Attack (Believe), broke (Create Music Group), Giant Music (Stem, from 2026-01-21), 187 Strassenbande and
  Teamwrk (Universal-distributed), Hall Access, Altafonte and A Quadrilha (Sony-distributed), WM Mexico (Warner),
  Viva Records and Cleopatra (independent). Just Woke Up was with Warner's ADA until 2025-06-19. Altafonte's
  start date (2024-01-01) is assumed: Sony's purchase was notified in November 2023 and done by August 2024.
- **Audit of name-only Deezer matches** (both genres): the 42 whose biggest songs were not among the Deezer artist's
  top tracks were re-checked by ISRC. Six were the wrong Deezer artist and now carry the ISRC-confirmed one, with
  their labels re-read: JACKBOYS, Run-D.M.C., FAVE, Flame, JADE, Garth Brooks. Most others were false alarms from
  title matching, which dropped non-Latin letters; titles now keep letters of any script.
- 34 stay unknown: the ℗ line names only the artist's own imprint, with no distributor (G-Unit, SODMG, Brick Squad
  Monopoly, Pineapple Storm and others). Not guessed.
- Unknown in the top 1,000: 262 -> 236.
- **Batch 5** (the next 48 strings): 13 rows, all with a distributor on the ℗ line: Plata o Plomo, Only Pro, Blue
  Magic, Carré Bleu (Sony France), Maison Baron Rouge (Warner France), Strange Music (Virgin), Verdansk, Indipendenza
  and Futura (Believe), Toreshi (Stem, from 2025-11-24), Twenty Nine (Tully), MORE VISION (Kakao), KOZ (HYBE). Left
  out though placeable as companies: LAIKA, COLORSxSTUDIOS, Big Noise (no distributor named). 32 stay unknown.
- **Batch 6** (60 more strings): 16 rows: Milan (Sony), Ambition Music, 3TR6AP2, 7th Magnitude, Boogie Naipe,
  G59 (Sony-distributed; Virgin until 2020), Psychopathic (ADA from 2019); Thaurus (Believe), MNRK, X-Ray (Cleopatra),
  Zef and Glizzy Gang (Stem), Stones Throw, Netflix Music, Rich Vagos (ONErpm). About 45 stay own-imprint only.
- **Batch 7:** 13 rows: AWA (Sony France bought it 2025-03-10: major from then, Sony-distributed before), Tanta Roba
  (Sony Italy from 2025-12-12), Pupila Dilatada (Altafonte), Black Money Records (EGA Distro, Virgin), Eklat (Warner
  Central Europe), GR6 (Virgin), Lyons Produções (ONErpm), Oranj (UnitedMasters, read as self-released like the
  existing UnitedMasters row), ALTER Music (Firebird), Ineffable, Carosello, Peermusic. About 32 stay unknown.

## 2026-10-24 Country money (owner C5): platform weights and radio songwriting

- Research in docs/research/research_country_rates.md (every figure sourced and graded).
- **Platform weights** (registry/platform_multipliers_country.csv, as a ratio of Spotify recording royalties):
  Amazon 0.55 mid (hip-hop 0.30), Apple 0.45 (0.55), a new Pandora line 0.50, "others" 0.10 without Pandora
  (0.30 with it). All C: platform-by-genre data are thin and from 2017-2022.
- **Radio airplay (songwriters):** US AM/FM audience x $0.15 / $0.25 / $0.40 per 1,000 listeners reached, from US
  radio revenue x the PROs' rates divided by music impressions; cross-checked against a 2014 per-spin study. Shown
  as money generated for the writers and publishers, with no artist slice (country hits are often staff-written).
  US radio pays recordings nothing.
- kworb's radio audience turned out to be a 7-day figure (it matches Luminate's weekly impressions), so a year is
  52 weeks of it. The audience figure itself stays internal (C4).

## 2026-10-24 Artist page: the numbers first (product review, overnight)

- The key figures (monthly and current listeners, peak, streams, YouTube, Deezer) now come straight after the name,
  before the Level/Scout/Worth card; certifications, awards, credits and Shazam follow the Streams panel instead of
  pushing the numbers below the first phone screen.
- External profiles are one line of text links ("On Spotify · YouTube · ..."); the buttons are for actions only
  (Compare, Worth on other deals, Share, Download card). The Level explainer is a hover.
- **Scout list:** 13 columns made the table nearly twice the page width, with the newest hit and its ▶ player
  off-screen. Now: rank, artist, score, label, newest hit (with ▶ and 🎬), monthly listeners and new-release pull;
  the other five signals sit behind "Show all signals". The CSV still has every column.
- **Top list:** the numbers come before the label group, and column headers wrap on phones, so the listener figure
  is on the first phone screen (it was cut off at the right edge).
- **Labels:** the "majors, under 1.5m" figure rested on 30 artists (the top 1,000 starts near 1.4m); it now
  covers everyone under 3m (about 380): 56% against 75% at 15m+.
- **Producers:** a song on several artists' pages (a duo and its members: Macklemore, Ryan Lewis, "Macklemore & Ryan
  Lewis") counted once per page; it now counts once per person (by ISRC).
- **Labels, across genres:** the majors' share tile adds the other genre's figure (hip-hop 59%, country 67% of
  listening); "rap" stands in for "hip-hop" there so the country pages' word swap leaves it alone.
- **Compare across genres:** Compare takes artists from either list ("Drake vs Morgan Wallen" is offered as a
  start); each links to their own genre's page, and a note says Scout scores and levels are within each genre.
- **Search across genres:** the header search also lists the other genre's artists (its list loads on the first
  search), marked "Country ·" or "Hip-hop ·" and linking to that genre's page.
- **Tables on phones:** the artist page's certifications, credits and collaborations, the tours list and the label
  directory stack each row with its column names (`table.stack`); comparison tables still scroll sideways.
- **Revenue table on phones:** the figures were scrolled off the right edge; each line now stacks the source over
  its generated amount, the artist's slice and the grade.
- Tiles fit one row on desktop (six tiles at 1280px) and no longer leave an empty slot when a page has fewer.

## 2026-10-24 Country: below-floor crawl, radio in Scout, Big Machine by date

- **Below kworb's 500k floor (C1):** kworb has nothing usable below
  500k listeners. Deezer's related-artists graph, seeded from its country chart, our matched artists and Wikidata,
  finds about 1,077 country artists, about 400 of them above the floor. `src/collectors/deezer_country.py`, monthly
  step `countrycrawl` -> data/country_deezer.csv. Ordered by the summed Deezer rank of the top 10 tracks (r 0.79 with
  log Spotify listeners on 240 country artists, but Spearman 0.22 among artists of similar size): grade C, an order
  only, never a converted listener figure. How to show ranks 401-1,000 goes to the owner.
- **Radio in country Scout (C4):** a factor of its own, 15%: the summed AM/FM audience of the artist's songs on
  kworb's airplay chart, 0 when none. Only our percentile reaches the site. Chart reach weighs 8% (country charts are
  mostly US, Canada, Australia), new-release pull 30%, current share 20%, engagement 12%. Hip-hop is unchanged.
  Credits like "Move On f/Shaboozey" now count for the featured artist.
- **Big Machine** (registry/label_owners.csv gains `from`/`until` columns): releases to 2026-02-17 are HYBE America's
  Big Machine Label Group (distributed by Universal: major-distributed); from 2026-02-18 Big Machine Records is
  Scott Borchetta's relaunched independent. Blue Highway Records, Nashville Harbor and Valory: HYBE America.
  Sources: Variety and Billboard (February 2026), Wikipedia.

## 2026-10-24 Certifications from Wikipedia discographies

- **Source** (`src/collectors/certifications.py`, monthly step `certifications`): the artist's English Wikipedia
  discography page (CC BY-SA, credited on the panel), which cites RIAA, BPI, ARIA, Music Canada and the other bodies.
  - Pages are read with `index.php?action=raw` because the action API answered 429 (rate limited) for this volume.
  - Top 1,000: 683 pages found, 503 artists with at least one certification, 18,874 certifications. Spot checks
    against the pages' wikitext matched (Drake, Kendrick Lamar, Lil Baby, GloRilla, Central Cee).
- **On the artist page:** certified releases, RIAA platinum total (Diamond = 10x), US No. 1s and the 12
  most-certified releases. Wikipedia can lag the bodies by weeks; the panel says so.
- **Rejected:** the RIAA's own search (no bulk access, terms against automated use).
- The country site build no longer rewrites review/label_review.csv (it emptied the hip-hop queue).

## 2026-10-24 Country groundwork (before the C1 research returns)

- **Nashville label map** (registry/label_owners.csv, each row sourced):
  - Universal: MCA Nashville, including its pre-2025 name UMG Nashville.
  - BMG (BBR Music Group): Broken Bow, Stoney Creek, Wheelhouse.
  - Big Loud: distributed by Mercury/Republic.
  - Belting Bronco: Zach Bryan, with Warner.
  - American Dogwood: Shaboozey, with EMPIRE.
  - Thirty Tigers: independent.
  - Already covered by existing patterns: Mercury, EMI and Capitol Nashville, Columbia and RCA Nashville, Warner.
  - **Left for research:** Big Machine / Blue Highway (HYBE renamed it in February 2026; Borchetta kept the name for a
    new independent label), so it must be read by release date.
- **US radio** (`src/collectors/radio.py`, daily step `radio`; owner C4):
  - kworb.net/radio's daily estimate of each song's US AM/FM audience (about 100 songs), plus the 30 archived days
    before: 3,100 song-days on the first run.
  - Used inside country scoring only. kworb's figures are not shown until the owner has asked them.

## 2026-10-24 Pages search engines can find, shareable cards (D2, D3), Shazam (K3)

- **D5: State of hip-hop** (`src/state.py`, #/state/<YYYY-MM> and a static page site/state/<YYYY-MM>/):
  - **Headline numbers:** majors' share of listening, No. 1 by current listeners, biggest 30-day riser, Breaking
    count, top unsigned prospect, what the top 100 earn on Spotify, the top producer, the most Shazamed artist, and
    the size of the list. Each links to the page it comes from.
  - **Citation:** a ready citation line and a Share button.
  - **Storage:** each month is stored in data/state/<YYYY-MM>.json. The current month refreshes with each build;
    past months keep their figures and their address.
  - **Links:** from the footer, and from the start page's value line ("This month in numbers").

- **D6: lighter first load:**
  - Page-specific data (unsigned peers, label and group finances, credits, tours, Sony Music, back-test, movers,
    market map) moved from data/index.json to data/extra.json. It is fetched in the background right after the
    core file, and pages that use it wait for it.
  - The start page and artist pages render from the core alone.
  - The core is 1.46 MB (about 330 KB compressed); extra is 364 KB. A per-page split of the artist list itself was
    rejected: search, Scout, labels and the start page all need it.

- **D2: static pages** (`src/static_pages.py`, generated at each build and deploy, gitignored):
  - **What:** site/a/<slug>/ for every artist (1,000) and site/label/<slug>/ for every label (116), each with its own
    title, description, canonical address (https://tventy.se/music/...), Open Graph and Twitter tags, structured
    data (schema.org MusicGroup / Organization) and a short readable summary.
  - **How it opens:** the full app loads on top and opens that artist or label (window.BOOT), so visitors see the
    usual page; navigating onward goes to the main site.
  - **Sitemap:** sitemap.xml lists all 1,117 addresses; robots.txt points to it.
  - **Rejected:** a server-rendered site. Static pages beside the app keep one codebase and the Cloudflare Pages
    deploy.
- **D3: artist cards** (1200×630 PNG per artist, site/cards/<slug>.png):
  - Shows the rank, monthly listeners, Scout score and tier, label, and what the artist keeps a year (marked
    "est."), with the data date and the address.
  - Used as each artist page's link preview and offered on the artist page as "Download card". Share now gives the
    artist's own page address.
  - Font: Bricolage Grotesque TTF (SIL Open Font Licence) in assets/fonts.
  - Build time: about 80 seconds for the cards, within the 10-minute deploy job.
- **K3: Shazam** (`src/collectors/shazam.py`, daily step `shazam`):
  - **Charts:** 58 of Shazam's public charts (world top 200, world hip-hop, 15 countries, 10 countries' hip-hop,
    31 cities), each covering the last 7 days.
  - **Matching:** to registry artists by name; featured artists in titles count. 321 hip-hop artists matched on
    the first day.
  - **Shown:** a "Shazam" column on the Scout list and a "Discovery" badge on artist pages, linking to Shazam's
    chart. Shazam's tables are not reproduced (owner, K3).
  - **Not in the Scout score yet:** it joins once our daily log can back-test it (from January 2027, as the other
    signals).
  - **Source note:** Shazam's own pages answer 403 to our client. The CSV service answers and is the documented
    download behind its "Download" button.

## 2026-10-24 Four sections (D1)

- **Header:** Artists · Scout · Money · Labels. Method moved to the footer, which already links it. On a phone the four
  fit on one row.
  - **Artists:** Top list, **Movers** and Compare. Movers merges Rising and This month into one page with a switch:
    Today (daily change outside the top 100) and Last 30 days (movers, new on Scout, unsigned prospects, listening
    shares). Compare moved here from Scout.
  - **Scout:** Scout list, Unsigned vs signed peers, Producers.
  - **Money** (was Worth): What is it worth?, Pay gap by deal, Platforms and Tours. These are money explainers, not
    charts.
  - **Labels:** Labels and market share, and Where it is streamed (was Audience, under Charts).
- **Old links keep working:** #/month, #/rising, #/audience and the rest. Breadcrumbs follow the new sections, and
  artist pages sit under Artists.
- **Kept, not merged:** Unsigned vs signed peers stays its own page, for its peer comparison. The Scout list already
  has an "Unsigned" filter, which acts as the preset.

## 2026-10-24 Owner's answers on country, sources and structure (the 12-hour research run)

- **Country:**
  - **C1 "c, dig deeper":** a country top 1,000. Research has started on ranking country artists below kworb's
    500,000-listener floor (Deezer fans, kworb's other lists, Wikidata, charts). Only about 340 sit above it.
  - **C2:** Jelly Roll moves to country (decision in review/decisions.json; `country` is now a genre value). He
    leaves the hip-hop top 1,000; the next artist takes his place.
  - **C3:** a genre switch in the header (hip-hop ↔ country), with Labels and Method shared.
  - **C4:** radio from kworb's radio estimates and Country Aircheck, used inside our scoring only. Ask before
    showing their figures.
  - **C5:** country platform weights (Pandora, Amazon) and a radio songwriting line, grade C.
- **Sources:**
  - **K1:** API keys (Ticketmaster and others) later; the owner adds them.
  - **K2:** the site is non-commercial for now. That keeps non-commercial-licensed sources open.
  - **K3:** Shazam charts as an internal Scout signal, shown only as a badge with a link.
- **Structure and growth, all as suggested:**
  - D1: four sections (Artists, Scout, Money, Labels); Method in the footer.
  - D2: indexable static pages per artist and label.
  - D3: shareable artist cards, after D2.
  - D4: email alerts later.
  - D5: a monthly "State of hip-hop" page.
  - D6: a lighter first load.
- **Labels:** R1 accepted. "Urban" means Universal Music Germany only when it is the whole label string (new
  "=" exact-match rule in registry/label_owners.csv). That places Sido, Capital Bra, Pashanim, MERO, Samra, Shindy,
  SSIO and Tom Hengst.

## 2026-10-24 New sources, step 2: credits (MusicBrainz) and label parents (Discogs)

- **Producer and songwriter credits** (`src/collectors/credits.py`, monthly step `credits`):
  - Each artist's 3 biggest songs as lead artist: recording code → MusicBrainz recording → producers (on the
    recording) and writers (on the work). Two requests per song at 1 a second; each code is looked up once.
  - Site: a "Who makes the hits" panel on artist pages, and a new Scout › Producers page ranking producers and
    songwriters by the daily streams of the songs they are credited on.
  - Partial coverage (volunteer-entered credits), said on both pages. The first full lookup of 2,745 songs runs
    about 1.5 hours.
- **Label parents from Discogs** (`src/collectors/discogs_labels.py`, CC0 dump of 1 October 2026,
  data/discogs_label_parents.csv for the 1,227 label names we need):
  - Discogs would place 29 of the 286 unknown artists. It keeps one parent per label, sometimes a past owner, so its
    chains are used as evidence, not applied blindly.
  - **Added to the owner table** (current and clear): AllPoints and Believe (Believe), 10K Projects (Warner,
    major-distributed), Rec. 118 in both spellings and Warner Music Spain (Warner), Affranchis Music (Universal,
    major-distributed). Each row carries its Discogs link.
  - **Result:** unknown fell from 286 to 269. Placed now include Franglish, RK, Bouss, Landy, Djadja & Dinaz and
    Yamê (Believe); Gambi, Soprano and Bello&Dallas (Rec. 118, Warner France); Rich Amiri and Pressure 9X19 (10K
    Projects); SFDK; and Sofiane.
  - **To the owner (review):** "Urban" as Universal Music Germany's hip-hop label for 8 German rappers (Sido,
    Capital Bra and others: the name is generic, so it needs a narrow rule). Also 50 Cent (G-Unit → Caroline/UMG),
    Waka Flocka Flame (1017 Brick Squad → Warner) and Jaden (Three Six Zero → Warner), where Discogs may show a past
    parent.

## 2026-10-24 New sources, step 1: awards from Wikidata

- **Research:** 30+ candidate sources, ranked by value and feasibility, with live tests (the 12-hour research run).
  - Free and open, buildable now: Wikidata awards, Wikipedia discographies (certifications and chart peaks), Discogs
    label data (CC0), MusicBrainz producer credits, kworb radio, GDELT news.
  - Need a key, or carry non-commercial terms: Ticketmaster, setlist.fm, Last.fm (public pages need written
    approval), Genius, SeatGeek. These go to the owner.
  - Grey (a public download with no reuse licence): Shazam charts. Goes to the owner.
  - Rejected on terms: RIAA's site (no scraping), Billboard, Official Charts/BPI, Bandsintown, Songkick, Tunefind,
    and Instagram/TikTok follower counts (no legitimate route).
- **Built: awards** (`src/collectors/awards.py`, monthly step `awards`):
  - Wins (P166) and nominations (P1411) with year and work, for the top 1,000, grouped into known families: Grammy,
    BET, AMA, Billboard, MTV, BRIT, MOBO, Juno, ARIA, Victoires, Polaris, Mercury, Soul Train, NAACP, Pulitzer.
  - Coverage: 102 artists, 378 wins, 367 nominations.
  - Grade B, and the page says it is a floor, not a total. Wikidata lists 10 of Kendrick Lamar's Grammy wins; he
    has more than twenty.
  - Shown as an "Awards" panel on the artist page.

## 2026-10-24 Product review: quick wins (owner: "scrutinize design and structure ... simple and logical to use and navigate but very insightful")

- **Review:** a product and marketing pass over all 16 pages on desktop and phone (64 screenshots).
  - Top problems found: no page can be found or shared on its own (one title for every page, no description or
    share); a start page that says nothing about what the site is for; two "biggest riser" tiles that disagree; a
    misleading money figure; prototype wording in public; four pages that answer "who is rising?"; jargon; buried
    labels on artist pages; phone overflow; very long pages.
- **Built now (no change of direction):**
  - **Titles and description per page,** including each artist's name ("Drake: listeners, earnings and label").
    Default share tags (Open Graph) in index.html.
  - **Start page:** a one-sentence value line replaces the second search box (the header search stays). The top-list
    tile reads "Biggest riser today in this top 100", so it no longer contradicts "Right now", which covers all 1,000.
    The table's box is labelled "Filter this list".
  - **Prototype wording removed:** "Prototype, private", the roadmap step numbers, and "the full method will be
    published here" (now: method version and date).
  - **Wayfinding:** "This month" now has a breadcrumb. Compare's empty page suggests three pairs.
  - **Artist header:** the label and its owner, with logo, under the name, plus a Share button (the phone's share
    sheet, or the link copied).
  - **Money honesty:** where more than 90% of an artist's streams come as a featured guest, the money figure is marked
    "own songs only", with the reason. Danny Chung shows $164 a year against 8.7m listeners because 99.99% of his
    streams are features on "Soda Pop".
  - **Long pages:** Scout and Unsigned show 50 rows, then "Show all": Scout falls from 18,000 to 5,500 px, Unsigned
    from 18,700 to 7,300.
  - **Phones:** This month no longer overflows sideways. Buttons are at least 44 px tall. Wide tables and sub-menus
    fade at the right edge to show they scroll.
- **Kept as decided:** the "music" word under the wordmark links to tventy sport (owner, earlier the same day), though
  the review suggested pointing it home.
- **For the owner (bigger changes):** a simpler structure in four sections, pages that search engines can index,
  shareable artist cards, alerts, and a lighter first load. These are put as decisions, not built.

## 2026-10-24 Label research batch 3, videos for the risers, Scout radio (owner: "Go with a, b and c in that order")

- **a) Label research on the 14 that moved from major to unknown:**
  - Applied (medium confidence): DYSTINCT (Avalon Music, in a Sony Music partnership: major-distributed), MF DOOM
    (Rhymesayers, a 2024 reissue: independent) and Teto (30PRAUM: independent). 30PRAUM was added to the owner
    table, so Matuê, WIU and Teto read the same.
  - Still unknown (low confidence: only the artist's own imprint on the ℗ line, no distributor named): Mauvais
    djo, Waka Flocka Flame, L7NNON, MC Cabelinho, Millonario, Vacra, Eypio, Djonga, Vegedream, Caio Luccas and
    Chris MC. Each could be independent, self-released or major-distributed. Guessing would put a wrong label on
    the site.
  - Unknown fell from 289 to 286.
- **b) Videos for the risers:**
  - **Sources:** kworb's YouTube artist pages (the busiest videos by yesterday's views) where kworb has a page, and
    otherwise the channel's public feed of its latest uploads (no key, no login; channel IDs from Wikidata). kworb
    tracks only artists big on YouTube: 22 of the 194 risers.
  - **Coverage:** 125 of the 194 risers have a video (25 from kworb, 100 from channel feeds). The rest have neither
    a kworb page nor a channel ID.
  - **Pick (`pick_video`):** the video titled after the newest hit (34); otherwise the artist's own most-watched video
    on kworb, skipping videos they only feature on (21); otherwise the latest upload (70). Shorts are left out.
  - **Site:** a 🎬 button beside ▶ on the Scout list, the unsigned prospects and the riser's page. It plays in
    YouTube's privacy-enhanced player (youtube-nocookie.com) in the same docked player, loaded only on a click.
  - **Schedule:** weekly on Fridays in the daily workflow (`python -m src.run videos`, about 4 minutes).
  - **Rejected:** the YouTube Data API. It needs a key and quota, and the free sources cover what kworb and the
    feeds can.
- **c) Scout radio:**
  - **What:** a "📻 Scout radio" button on the Scout list plays a 30-second Deezer preview of each artist's newest hit,
    one after another, in the order shown. It follows the list's filters, so "Unsigned" plus radio plays the unsigned
    risers only.
  - **Controls:** previous, pause, next, ☆ watchlist, and a link to the track on Deezer ("Preview: Deezer").
  - **Coverage:** 406 of the 1,000 have a newest hit with a Deezer track ID; 208 are on the default Breaking + Rising
    list.
  - **How:** Deezer's preview links expire within the hour, so each is fetched just before it plays, through Deezer's
    API in its documented JSONP form (the API sends no CORS headers). Nothing loads before the radio is started; a
    song without a preview is skipped after 2 seconds.
  - **Tested** in headless Chromium: Deezer answered and the previews streamed (HTTP 206), skipping works and the
    watchlist star toggles.
  - **Rejected:** Deezer's widget (no queue we can drive) and Apple's previews (found only by searching for the song
    by name, so less exact).


## 2026-10-24 Scout weights after the back-test, labels from lead releases, and a player for the risers

- **Scout weights (owner: "S1: 5%" and "Don't put so much weight on Wikipedia attention"):** listener growth 20% to
  5% and Wikipedia attention 18% to 5%, the two signals the back-test found below chance (44% and 43% of picks).
  - The freed points go to the other signals in proportion: new-release pull 35%, current share 22%, streams per
    listener 14%, chart reach 14%, today's change 5%.
  - Kept: attention's part in the Breaking rule (new songs pulling 25%+ of streams, or attention up 30%+).
  - Review again with the full back-test from our daily log, in January 2027.
- **Labels from lead releases only (owner: "L1: yes"):** Deezer's album record names its lead artist, and
  release_labels.csv now stores `lead`.
  - Releases the artist only features on are left out of the label and catalog decisions. Up to 30 releases in the
    window are looked at to find 6 lead ones.
  - The 7,100 stored releases were checked once (`fill_lead`): 4,483 lead releases and 2,548 features. A deeper read
    then added 2,197 lead releases.
  - Reading lead releases alone exposed the artists' own imprints, which the owner table did not know. Nicki Minaj's
    "Nicki Minaj/Cash Money", for example, read as self-released.
  - **L2 (owner: "go with suggested"):** the 30 most-listened imprints were researched from ℗ lines and press. The 19
    with high or medium confidence were added to registry/label_owners.csv: Cash Money, Taylor Gang, Boominati,
    Black Belt, Numinati, DJ Khaled Productions, Hitmaker, 4Hunnid, Lizzy Records, Virgin Music Group France, Trippy
    Music, BSB Productions, Tiger Turn, MNT, MSTT, Uptown and Coke Boys. Left out: 8 artist imprints with no named
    distributor, and the generic strings "Independent" and "2020".
  - **Review batch (owner: "All as suggested"):** of the 46 artists over 5m listeners whose status changed:
    - B1 (16 sourced moves), B2 (8 to catalog) and B5 (2 to Sony Music) were accepted.
    - B3: Chance the Rapper, G Herbo, BK and Hungria are self-released. Yung Lean (Young, a Beggars label) and
      Orochi (Believe Artist Services) are set to independent through review/decisions.json.
    - B4: 14 artists stay unknown and lead the next research batch: Mauvais djo, Waka Flocka Flame, L7NNON,
      DYSTINCT, MC Cabelinho, MF DOOM, Millonario, Vacra, Eypio, Djonga, Teto, Vegedream, Caio Luccas and Chris MC.
  - **Net, across the 1,000:** major 430 to 316, major-distributed 16 to 20, independent 86 to 88, self-released 138
    to 143, catalog 88 to 144, unknown 242 to 289. The old major count included artists counted only through labels
    of songs they featured on.
- **Player for the risers (owner: "links to the songs and be able to play audio ... only for the risers/scout";
  "Go with suggested"):**
  - **What:** a ▶ button beside the newest hit of every Breaking, Rising and Watch artist on the Scout list, on the
    unsigned prospects of "This month", and on tiered artists' pages. It opens Spotify's own player docked at the
    foot of the screen; the next ▶ switches the song.
  - **Spotify's embed:** full songs for listeners signed in to Spotify, 30-second previews for others. Nothing from
    Spotify loads before the first press, so no third-party code or cookies arrive unasked.
  - **The song:** the track ID of the newest hit, already in the ranking data (`top_fresh.id`). No new collector and
    no cost.
  - **Video, later:** YouTube video IDs from kworb's YouTube pages (free), played in YouTube's privacy-enhanced
    player on a click.
  - **Rejected for now:** a "Scout radio" queue of Deezer previews (built after the first version is used); the
    YouTube API (quota and a key).

## 2026-10-24 Label research, batch 2 (step a)

- **Researched:** the next 20 unknown artists by monthly listeners. 50 Cent, Soulja Boy and Eve were skipped (low
  confidence in batch 1).
  - Evidence: release ℗ lines from Apple's iTunes lookup first, then press, Wikipedia and Deezer.
  - The 2-year window counts releases where the artist is the lead name, not features.
- **Applied (11):** ScHoolboy Q, Travie McCoy, Lil' Kim and Twista as catalog: their recent Deezer labels came from
  features, and their last lead releases were in 2019-2024.
  - Also applied: Danny Chung (self-released: DistroKid's numbered label name), Matuê and WIU (independent,
    30PRAUM), Lithe (GSL/Atlantic), PLK (Panenka Music, distributed by Wagram), Baby Rasta y Gringo (Interscope)
    and Tinie Tempah (Imhotep Records licensed to Believe).
- **Not applied (9), still unknown:**
  - Low confidence: BLOK3, Logic (BMG until January 2025, own Boom.Records since), Connor Price, Baby Bash and BIN.
  - Medium on the label, but no distributor named, so the status could be independent, self-released or
    major-distributed: Pineapple StormTv, Kid Ink, Wyclef Jean and Niska.
- **Finding again:** in 8 of the 20, the Deezer label string belonged to another artist's release the artist only
  featured on.
  - Proposed fix, for a later step: read the latest *lead* release, not the latest release.
- **Result:** unknown fell from 253 to 242.

## 2026-10-24 Sony's music business split out (step d)

- **Source:** Sony Group's results releases as filed on EDGAR (Form 6-K, HTML), since sony.com refuses automated
  access.
  - Each release has a table of sales by product category, with Music split into Recorded Music (streaming and
    other), Music Publishing, and Visual Media and Platform.
  - A segment profit table gives Music's operating income.
- **Read by rule, not by Claude** (`src/collectors/sony_music.py`): plain tables with fixed row names, at no cost.
  - Every 6-K since 2023 is checked once for the music table (data/sony_6k_checked.csv): 16 results releases out of
    about 150 filings.
  - Each release carries the year before; a later release's figure replaces an earlier one.
  - In every period the four parts add up exactly to the Music total (checked).
- **Coverage:** the sales split from FY to March 2024 through the June 2026 quarter. Operating income from FY to
  March 2022 (older releases lay out the sales table differently and are not parsed).
- **Site:** Sony Music label pages (Columbia, RCA, Epic and the rest) show a "Sony Music: the music business on its
  own" panel above Sony Group's health panel: 3 fiscal years and the latest 4 quarters, with margin and growth.
  Latest year: FY to March 2026, music sales ¥2,091bn (+15%), operating income ¥447bn (21.4%).
- **Rejected:** Claude reads of the releases. The tables are regular, so a rule is exact and free.

## 2026-10-24 "This month" page (ROADMAP 8.5)

- **Where:** Charts > This month (`#/month`), built by `src/monthly.py`.
- **Contents:**
  - movers over 30 days;
  - new Breaking and Rising artists;
  - unsigned prospects (self-released with a Breaking or Rising tier);
  - the share of listening by label status.
- **Movers today:** 263 of the 1,000 have a month-ago value. It comes from the Wayback copies of kworb's listeners
  page, which lists only the biggest artists. From 2026-11-20 our own daily snapshots cover every artist.
- **New Breaking and Rising: held back until the Scout log is 28 days old (from 2026-11-20).** Rejected: comparing
  with 2026-10-23. Scout's method changed on 10-24 (the ranking update and release dates), so that comparison
  showed 49 "new" Rising artists caused by our changes, not the artists'.
- **Label shares:** both dates use today's label status. Comparing the statuses as logged mixed the relabelling
  (unknown fell from 26% to 14% after the label research) with real shifts in listening.

## 2026-10-24 Scout back-test (ROADMAP 8.2; owner: "Follow steps a to d ... in order")

- **What can be tested:** only listener growth (the Wayback Machine's weekly copies of kworb's listeners page since
  2023) and Wikipedia attention (24 months of page views, so testable from late 2025). Together they carry 35% of
  the score.
  - New-release pull, current share, engagement and chart reach have no archived history; they are tested from our
    daily log (data/scout_history.csv) once it is 90 days old, in January 2027.
- **Method (`src/backtest.py`):** one test date a month. On each date: hip-hop artists under 15m listeners in the
  archived page, with a copy 90 days before and 90 days after.
  - Scoring is as on the site: percentiles within the size band, weighted mean.
  - Picks are the top fifth of each band. A hit is a pick that outgrew its band's median over the next 90 days;
    chance is 50%.
  - A synthetic test checks that the method finds a signal that persists.
- **Result:** 39 dates, 2023-05 to 2026-06, 1,448 picks: **45% hit rate**.
  - With attention (9 dates since late 2025): 49%.
  - Each factor alone: growth 44%, attention 43% (fewer picks).
  - Fast 90-day listener growth tends to cool off over the next 90 days. The signals with history do not pick next
    quarter's risers; if anything, they lean the wrong way.
- **Published as is** on the Scout page ("Does it work?"), with the bias: the artists are today's registry, so acts
  that rose and fell away are missing.
- **Not changed without the owner:** the weights. The question goes to the owner in chat: lower listener growth
  from 20% (or drop it) until the full back-test in January 2027.

## 2026-10-24 UK label companies' accounts (owner: "R2: yes")

- **Companies:** the majors' UK record companies at Companies House (registry/uk_companies.csv), numbers looked up on
  the register's own search:
  - Universal Music Operations Ltd (00950138);
  - Warner Music UK Ltd (00680511);
  - Sony Music Entertainment UK Ltd (01471066);
  - BMG Rights Management (UK) Ltd (06705101).
- **Route:** Public-Registry's, using the public website, which needs no key or login. The filing history gives each
  set of full accounts. The latest 5 years per company are kept, 20 documents in all; each also carries the year
  before, so 6 years are covered.
- **Scans:** all 20 are scanned paper with no text layer, so pages cannot be selected. Each goes to Claude whole, as
  Public-Registry sends scans, with notes on UK terms: turnover, the Companies Act balance-sheet format, and no cash
  flow statement under FRS 101. The checks and correction ladder are the same as for the groups.
  - Cost: Haiku 5.5 at $0.10 per million input tokens. A 50-page scan is about 80,000 tokens, about 1 cent, so all
    20 cost about $0.20, plus any corrections.
- **Rejected: BMG's iXBRL.** BMG's UK company also files machine-readable iXBRL. A second parser (FRS 101/102
  taxonomies) for one document a year saves about a cent, so its PDF goes the same way.
- **Labels linked to a UK company:** nothing is linked by assumption; there are two sources, and only labels of the
  company's own group count.
  - The labels its accounts name (labels_named in the read). In practice the accounts mostly list subsidiary
    companies ("Laurel Records Limited"), which are separate, often dormant, so names ending in Limited/Ltd are left
    out. Warner Music UK's strategic report speaks only of "its constituent labels".
  - The group's labels whose releases carry a UK name ("Atlantic Records UK", "Parlophone UK", "Epic Records UK",
    "BMG Rights Management (UK) Ltd."). That is the group's UK arm, and each major has one UK record company.
  - Result: UMO for Def Jam Recordings, EMI, Island Records, Polydor and Virgin Music Group; Warner Music UK for
    Atlantic Records and Parlophone; Sony Music UK for Epic Records; BMG UK for BMG.
  - The label page shows the UK company's health under the group's, marked as the UK business only.
- **First reads (2026-10-24):** all 20 passed Haiku's first read, with no correction and no Opus call: about 1.4
  million input and 70,000 output tokens, about $0.18. Spot checks against the scans match: Warner Music UK FY2025
  turnover £309.3m, profit £40.9m and equity £127.0m; BMG UK 2025 net assets £483.0m (2024: £463.3m, after a £380m
  share capital), creditors due within a year £127.4m.
- **Not covered:** the US label companies (Atlantic, Interscope, Columbia and the rest) are subsidiaries that publish
  no accounts. The UK is the one large market where label companies must file theirs.

## 2026-10-24 · Design and usability in line with tventy sport
- **Owner:** "Revamp the tventy music site so its design is more in line with tventy sport ... consistency in usability when switching from sport to music on desktop and mobile."
- **Chosen,** each taken from the sport site:
  - **Header:** the wordmark with the section switcher, a search box, and the section buttons on the right.
  - **Phone header:** the search takes a full row, and the section buttons scroll in one row below it.
  - **Search:** artists by name, then labels. Arrow keys and Enter work, and "/" focuses the box. There is a second, larger search on the start page.
  - **Breadcrumbs under the header:** Home / section / page.
  - **Start page:** "Global Hip-Hop", the big search, four headline figures, then "Right now" as a framed band with a button, then the three doors, then the top list.
  - **Key-figure tiles:** outlined, no fill, the value at 22px, as sport's key figures.
  - **Phones:** the artist photo and label logo sit beside the name, the "Right now" cards are two per row, and the sub-menus scroll sideways.
  - **Footer:** links to Method, Report a correction and tventy sport.
- **Unchanged:** every page's content, figures, tables and sources.
- **Rejected:** copying the sport site's code wholesale. The two sites have different pages; only the shared shell and patterns were brought over.

## 2026-10-24 · The site becomes tventy music at tventy.se/music, public
- **Owner:** "tventy.se/sport for the basketball site and then tventy.se/music for the rap ledger ... no mention of rap ledger just that site there. The theme should be inverse with a black background and white text ... Public. Go."
- **Chosen:**
  - **Name:** the site name is tventy, with "music" in small type below it to the right. Pressing it goes to tventy.se/sport, whose header reads "sport" and links back.
  - **Rap Ledger removed** from every page: title, header and the CSV file name. The browser-storage key for watchlists keeps its old name, so saved watchlists survive.
  - **Theme:** inverse, a black background and white text, using the same tokens. The up/down colours are lightened for contrast; logos keep a white backing; the label-share shades run light to dark.
  - **Public:** the noindex tag is removed.
- **Serving:** this repository still builds and deploys the Cloudflare Pages project rap-ledger. The tventy.se router lives in the Public-Registry repository (`worker/`) and serves this project under /music. The site's relative paths work there unchanged.
- **Rejected:** moving this repository's code and data into Public-Registry. Two unrelated pipelines would be joined for no gain on the site.
- **Owner's steps:** remove the Cloudflare Access application on rap-ledger.pages.dev, since the router must reach it. DNS and the router are set up from Public-Registry.

## 2026-10-24 First report reads (owner added the API key: "R1 done ... Check company sites for PDFs if not found somewhere else")

- **Sony's site:** sony.com refuses automated requests ("Access Denied"). Its results releases are read from the
  same documents filed with the SEC as Form 6-K (HTML). Their statement tables are selected as Public-Registry does
  with HTML filings and sent as text, about 2,500 tokens each.
- **7 documents read** (UMG half-year 2025 and 2026; Bertelsmann annual 2025 and half-year 2025 and 2026; Sony year
  to March 2026 and quarter to June 2026). All passed Haiku's first read: no correction, no Opus call.
  - About 52,000 input and 25,000 output tokens in all.
  - **Checked against the documents and press:** UMG H1 2026 revenue €6,194m; Sony FY to March 2026 sales ¥12.48tn
    and operating income ¥1,447.5bn. Sony's net loss of ¥302bn is the group total, including the loss on the Sony
    Financial Group spin-off (Form 20-F).
- **One error the checks missed:** Bertelsmann's annual report was read with the right figures but a unit
  multiplier of 1 instead of millions, so its values were stored a million times too small.
  - **Fix:** a new check fails any read where total assets or revenue comes to under one million. The read was
    removed and is read again through the correction ladder.
  - The same check would have sent this read to Haiku's high-effort retry.
- **Interim periods:** half-years (UMG, Bertelsmann) are now shown with quarters on the health pages.
- **Still open:** Companies House accounts of the majors' UK label companies, for label-level health (R2, owner to
  decide).

## 2026-10-24 Label groups' financial statements and health (owner: "download and screen all their relevant quarterly and annual financial reports with all three statements ... learn from ... Hoop Ledger / Tventy ... cheap extraction of information from PDFs")

- **Lesson from the Public-Registry project:** machine-readable filings first, at no Claude cost. A PDF goes to
  Claude only where no XBRL exists, and then cheaply: page selection, a Haiku first read, checks in code, an Opus
  correction, a 10% audit sample.
  - **Measured there:** about $1.30 per 100 documents, against $8 with Opus alone. Haiku with checks made 3 wrong
    figures in about 280.
  - **Also learned there:** sending the text layer instead of the PDF saved nothing on short documents, so PDFs stay
    PDFs.
- **Free structured sources, built** (`src/collectors/financials.py`, `data/financials.csv`):
  - **SEC companyfacts API:** Warner Music Group (10-K and 10-Q, so quarters too), Reservoir Media (10-K and 10-Q),
    and Sony Group (20-F, annual, the whole group).
  - **ESEF annual reports as xBRL-JSON from filings.xbrl.org:** Universal Music Group (2021-2025) and Believe
    (2021-2024).
  - **Three statements,** 24 standard items. The concept map is taken from Public-Registry, with debt, capex,
    catalogue purchases, interest, tax and dividends added. UMG's catalogue investments and Believe's borrowings are
    tagged under the companies' own concepts.
  - **Checked against the published totals:** UMG revenue 2025 €12,507m, WMG FY2025 $6,707m, Believe 2024 €988.8m,
    Reservoir FY2026 $175.7m. 110 of 113 balance sheets balance within 1%.
- **Health ratios** (`src/health.py`): revenue growth, operating margin, free cash flow and FCF margin, FCF after
  catalogue investment, net debt, net debt / EBITDA proxy, interest cover, current ratio, equity ratio.
  - **Readings:** healthy / watch / weak, by credit-analysis rules of thumb.
  - **Current ratio bands set for music:** good 0.9+, watch 0.6+. Royalties owed to artists sit in current
    liabilities, so every group runs below 1.
  - **UMG's EBITDA proxy:** operating income plus amortisation and impairment of intangibles, the only D&A it tags.
- **PDF route aligned with Public-Registry** (owner: "make sure you are using the efficient pdf reading we
  established"):
  - **Same as there:**
    - its page finder;
    - PDF input, not text;
    - Haiku at medium effort;
    - corrections first by Haiku at high effort, then by Opus with the server-side fallback;
    - failed reads excluded and listed;
    - a fixed 2% Opus audit chosen by document ID.
  - **Interim reports:** "Consolidated Interim Statements of ..." headings and short numbers ("947") are now
    recognised.
  - **Dry run on the 5 queued reports (no Claude call):** exactly the income statement, balance sheet and cash flow
    pages of each, 15 pages sent of 435.
  - **Not taken over:** the Batches API. About 5 documents a month would save under $0.05.
- **PDF route, built and not yet run** (`src/extract/report_pdf.py`, `registry/report_pdfs.csv`): UMG's half-year
  reports, Sony's quarterly results (music segment) and Bertelsmann/BMG. It needs the `ANTHROPIC_API_KEY` secret on
  this repository and the owner's approval of the cost.
- **Not available anywhere:** EMPIRE, Concord before the merger, and other private labels publish no accounts.

## 2026-10-24 Label research (owner: "Research to find out"), finances and logos

- **25 artists researched:** the 5 the owner could not answer and the next 20 unknowns.
  - **Evidence:** release ℗ lines (Apple's iTunes lookup), press and Wikipedia; one source per artist.
  - **Applied:** 22 rows of high or medium confidence, to `registry/label_overrides.csv` with the source in the note.
  - **Not applied (low confidence):** 50 Cent and Soulja Boy (only their own label names on 2025-26 releases; the
    last documented major deals date from 2014 and 2021) and Eve (no new releases found). They stay unknown.
  - **Finding:** some Deezer label strings belong to the other artist on a collaboration. Examples: Childish
    Gambino's "ALTER Music" and Mustard's "CactusJack". The research corrected these.
- **Finances** (`registry/label_financials.csv`): 126 rows, each with period, currency, source and basis.
  - **Reported (A):** UMG FY2025, WMG FY2025, Sony's music segment FY2025, BMG 2025, Believe FY2024, Reservoir FY2026.
  - **Press-reported (B):** Concord.
  - **None found:** EMPIRE (no reputable figure). The page says so.
  - **Checked against the sources:** UMG revenue €12,507m and adjusted EBITDA €2,810m (2025 results release), and
    BMG and Concord's merger, completed on 1 September 2026 with Bertelsmann holding 67%.
- **Logos** (`registry/label_logos.csv`, `site/logos/`): 25 Wikimedia Commons files, mostly PD-textlogo.
  - **Left out:** Atlantic (a "CC0" file sourced from a fan site) and Death Row (a picture logo under a doubtful
    licence).
  - **No logo on Wikidata:** Capitol and gamma.

## 2026-10-24 Label pages, monthly run now, robust ranking (method 1.2)

- **Label pages** (owner: "an option to select on each label ... logo ... parent company ... a snapshot ... artists
  ... how they are performing, how the label is financially performing, how the parent company is financially
  performing"):
  - **Directory and pages:** a directory of every label with artists in the top 1,000 (search, filter by owner,
    sortable columns), and one page per label.
  - **Which label:** the label printed on the artist's recent releases. "X under exclusive license to Y" counts as Y.
    The display names are in `registry/label_owners.csv`.
  - **Each page shows:**
    - the roster with listeners, current listeners, Scout and newest hit;
    - the roster's yearly recording royalties (C);
    - momentum and the one to watch;
    - releases in two years;
    - the parent company and its sister labels in the top 1,000.
  - **Finances:** a label inside a major publishes no accounts of its own. The page says so and shows the roster's
    royalties as the best public measure of its size, with the parent's reported results (company filings, A)
    beside them. Private independents show press-reported figures (B) where they exist.
  - **Logos:** only free files on Wikimedia Commons (Wikidata's logo property), mostly public-domain text logos,
    credited on each page. Labels with no free logo show initials. Rejected: copying logos from label websites
    (copyright and trademark).
- **Monthly run started now** (owner) on the working branch. Its steps no longer stop the run when one fails or times
  out, the commit always runs, and a second Deezer dates pass follows MusicBrainz.
- **Current-listeners method 1.2:** artists with 50-80% of their streams dated get a provisional rank, marked * with
  the range the undated songs could move it. Ranked: 914 → 970 of 1,000. Rejected: lowering the 80% rule outright,
  which would hide how uncertain those ranks are.

## 2026-10-24 Owner's answers in chat: backfill, assumptions, Latin, catalog acts

- **A1 (yes):** the history backfill was started by Claude (Actions → backfill, on main).
- **A2 (yes):** the five Phase 7 assumptions stand:
  - black-and-white look;
  - Scout weights;
  - Apple chart presence only;
  - Feature magnet at 80%+;
  - Co-signed under 3m with a 20m+ artist.
- **P1 (a): Latin trap and reggaeton stay off the site.** The 236 artists marked Latin are kept in the registry
  (`genre = latin`) but not shown. Rejected:
  - (b) a separate Latin list;
  - (c) counting them as hip-hop.
- **P2 (yes): catalog acts.** An artist with no release in the last two years on Deezer is "Catalog", not "Not yet
  known".
  - They leave the label review list and the market-map shares (the page states how many were left out).
  - They were never in the Unsigned list.
  - The labels step now records an artist checked with nothing recent, so a catalog act is told apart from one not
    yet checked.

## 2026-10-24 Genre review settled on Claude's recommendations (owner: "go with all your recommended for the 1491 names")

Reviews now happen in chat (working agreement). The owner accepted every recommendation in the genre queue. The
recommendation rule, applied in this order:
1. The 12 artists shown in chat: as suggested there (Pharrell, Bryson Tiller, AP Dhillon and Omar Camacho other; T-Pain,
   Anderson .Paak and AUDREY NUNA hip-hop; the rest Latin).
2. The pipeline's Latin suggestions (170): Latin.
3. Any Latin evidence: Latin. That means a Spanish-speaking home country, 25%+ of Deezer releases filed as Latin, or 25%+
   of MusicBrainz votes on Latin genres.
4. Artists with MusicBrainz votes or an exact Deezer match tied to a Wikidata identity: hip-hop when the average of the
   hip-hop vote share and the Deezer rap share is 45% or more, else other.
5. Artists found on Deezer by name only: hip-hop when 50%+ of releases are rap and the Deezer audience is at least 1%
   of the Spotify listeners. Without the audience check the name could belong to a different, smaller act.
   - The other 623 stay in review: identity not confirmed. Most are producers, whose Spotify listeners come from
     credits.
6. Wikidata genres only: hip-hop when half or more are hip-hop genres.
7. No data (50): stay in review.

- **Result:** 818 decisions; 485 hip-hop, 236 Latin, 97 other. 673 stay in review. Registry: 1,630 hip-hop artists
  (was 1,145).
- **Labels:** the 5 label cases with a recommendation in chat are applied (Macklemore, B.o.B and Tory Lanez unsigned;
  Lil Peep and Coolio independent label).
- Rejected: moving all 1,491 by the pipeline's lean alone. 1,321 of them had no lean, which is why they were in review.

## 2026-10-23 Review desk, label owners from MusicBrainz, compare and watchlist

- **Review desk** (claude.ai page, its own database): the 1,491 genre and 516 label cases as cards, biggest audience
  first, one tap per decision, usable on a phone. `src/reviews.py` turns the saved answers into the two override
  files.
  - Rejected: editing the CSVs by hand. Slow on a phone, and 2,000 rows would never get done.
- **Label owners from MusicBrainz** (`src/collectors/musicbrainz_labels.py`): for a label name our table cannot
  place, the MusicBrainz label of exactly that name; then its owners and parents, up to 4 levels, and its
  distributors.
  - The first ancestor our table places decides. Example: Hall Access → Sony Music Entertainment France → Sony.
  - A name shared by two MusicBrainz labels is skipped. "Urban" is one: the German Universal label shares its name
    with others.
  - Relations MusicBrainz marks as ended (a past owner or distributor) are skipped. The first pass counted them
    and placed Heavenly Recordings under Universal through an old distribution deal.
  - A label with no placed ancestor stays unknown, because a missing parent is not proof of independence. Wikidata
    was tried first and rejected: the items exist, but most lack the parent (Urban, Vertigo Berlin).
- **Hand-added owners:** WEA Latina, WM Poland, Vertigo, Universal Records, Sony BMG, Zomba and Jive (majors);
  Loma Vista (Concord), 88rising and Reach Records (independent).
- **Compare page and watchlist:**
  - The compare page puts two artists side by side and highlights the higher figure in each row.
  - The watchlist stars artists. It is kept in the viewer's browser only, until accounts exist.

## 2026-10-23 Phase 7: Worth and Scout (owner: "insights for artists to understand their worth and labels to find new talent ... optimize the site design, usability and clarity ... find data that will bolster its appeal")

The owner was away overnight, so discovery questions were replaced by the assumptions at the end of this entry.

- **Navigation:** five sections, Charts / Scout / Worth / Labels / Method, instead of eight tabs. Sections with
  several pages show a sub-menu. The home page opens with three doors: worth for artists, rising artists for labels,
  and the market.
  - Rejected: separate sites for artists and labels. One data set, and labels and artists look at the same artists.
- **Scout score** (`src/insights.py`), 0-100, from six signals:
  - new-release pull: share of daily streams from songs out 90 days or less;
  - listener growth against 90 days ago;
  - current share;
  - Wikipedia attention: last 3 months against the 9 before;
  - streams a day per listener;
  - chart reach: Spotify weekly top 200 plus Apple Music daily top 100.
  - **Comparison:** each signal is a percentile among artists of a similar size (5 monthly-listener bands, at about
    the top 1,000's quartiles). A small act that is taking off can therefore score as high as a superstar.
  - **Missing signals:** they are left out and the weights rescaled. Listener growth is missing for everyone until 90
    days of history exist.
  - **Tiers:** Breaking 80+, Rising 65+, Watch 50+.
    - Breaking also needs a measured absolute signal: new songs pull 25%+ of the streams, or Wikipedia attention is up
      30%+. Without that rule Drake showed as "Breaking", ranked high only against the other 94 superstars.
    - Artists with 15m+ listeners get no tier: they are established, not talent to find.
  - **Rejected:**
    - one ranking across all sizes, which superstars win on every absolute signal;
    - a machine-learned model, which needs labelled history we do not have. A back-test is planned once 90 days of
      history exist.
- **Worth** (`registry/catalog_multiples.csv`): the value of an income stream = a year's income × a sale multiple
  that depends on how new the music is, judged from current share.
  - new music: 5-10× (Royalty Exchange 2025);
  - mixed: 8-13.7× (Citrin Cooperman 2025: younger masters catalogs averaged 13.7×; the low end is our
    interpolation, grade C);
  - evergreen: 10-17× (Royalty Exchange 10-15×; Citrin: older masters traded above 17×).
  - **Calculator:** for a typed-in audience, royalties come from the middle half of what artists of that size in our
    list generate per listener. For an artist in our list, their own measured lines are used.
  - Advances, recoupment and touring are not in the calculator, and the page says so.
  - Rejected: one multiple for all catalogs. Sources agree that young hip-hop catalogs trade lower.
- **Labels market map:** share of the top 1,000 by group (UMG, Sony, Warner, independent labels, self-released, not
  yet known) by artists, monthly listeners and current listeners, overall and by size band.
  - Finding: among artists whose label is known, the majors hold 82% of those with 15m+ listeners and 46% of those
    under 1.5m.
- **Levels and badges:**
  - levels: Rookie, Rising star 5m+, Headliner 15m+, Icon 40m+;
  - badges: Breaking, Unsigned and rising, Feature magnet (80%+ of daily streams as a guest), Co-signed (under 3m listeners, with a song of 50k+ daily streams together with a 20m+ artist), Global (20+ chart
    countries), Revival, Hot release.
- **New free data:**
  - **Wikipedia page views** (Wikimedia API, 24 months, the article linked on Wikidata, so no name matching). The
    API throttled 20 requests a second (HTTP 429, a 30-second wait), so it now runs at 2 workers, 0.2 seconds apart.
  - **Apple Music's daily top 100** in 25 countries (Apple's public marketing feed). It is matched by exact folded
    name; a name two artists in our list share is skipped. This is chart presence only.
  - **Wayback Machine copies of kworb's listeners page**, weekly since 2023, for real listener history.
    web.archive.org is blocked in the build container, so this runs as the one-off Actions workflow `backfill`.
- **Assumptions made without asking (owner to confirm):**
  1. The site keeps the black-and-white look; colour stays reserved for up and down.
  2. Scout signal weights as above. They are a judgement, to revisit after the first back-test.
  3. Apple's feed is used for chart presence with a link back. Its terms aim at promoting Apple Music, so the site
     never shows the feed's artwork.
  4. The Wayback backfill reads about 150 snapshots at one request every 3 seconds.

## 2026-10-23 Unsigned tab and the move to the top 1,000 (owner: "another tab of unsigned artists ... benchmark against comparable growing signed artists ... then expand to the top 1,000")

- **Who is signed, chosen: what the artist releases on now, not Wikidata's career-long label list.**
  - **Labels:** Deezer gives the label printed on each release. The artist's last 2 years, up to 6 releases, are read
    (`src/collectors/deezer_releases.py`).
  - **Owner map:** `registry/label_owners.csv` (50 patterns; "X under exclusive license to Y" goes by Y). The majors'
    labels were checked on Wikidata's parent organisations: 27 confirmed, 5 with no entry or no parent, marked as
    such.
  - **Artist status:** the status most of their recent releases share. Deezer lists a collaboration under every artist
    on it, so the latest release alone misled: Tyler, The Creator showed as Warner.
  - **Second check, recording codes (ISRCs) of the artist's own recent songs, not guest spots:**
    - No public list maps ISRC prefixes to companies, so prefixes are learned from our own data. A prefix belongs to a
      major when at least 10 lead-artist songs carry it and 90% or more come from artists whose labels are that
      major's. Learned: USUG1, USUM7, USC4R (Universal); USAT2 (Warner); USSM1, USRC1, USQX9 (Sony); and a few
      others.
    - US codes issued after 2010 start QM/QZ/QT ([Wikipedia](https://en.wikipedia.org/wiki/International_Standard_Recording_Code)):
      newer registrants, which DIY distributors and small labels use.
  - **Statuses:**
    - major;
    - major's distribution (Virgin, The Orchard, AWAL, ADA);
    - independent label (EMPIRE, gamma., BMG ...);
    - self-released, i.e. unsigned: a distributor named on the release, "Independent", or the artist's own name;
    - unknown.
  - An own-name label on recordings registered by a major counts as major. This corrected Post Malone, Gunna, NF and
    Metro Boomin.
  - **Confidence:** "confirmed" (a distributor named, or most recent songs on QM/QZ/QT codes) or "label name only".
- **Revenue:** the deal type now follows this status:
  - major → major deal;
  - major's distribution → label services, 70-85% (AWAL Core 85%, A);
  - independent → independent label;
  - self-released → DIY, 85-100% (UnitedMasters 90-100%, A).
  - Wikidata's label list is now only a fallback.
- **Benchmark (chosen):** each unsigned artist against the 5 signed artists closest in monthly listeners (0.6-1.67×,
  else 0.4-2.5×) and share of listening on recent releases.
  - "Growing" means at least 20% of listening on recent releases, until a month of listener history allows 28-day
    growth. Catalog acts, such as Wu-Tang Clan and MF DOOM, were matching before this filter.
  - **Shown:**
    - what the artist generates and keeps now (95%);
    - the peers' median;
    - the artist's streams per listener against the peers';
    - what they would keep on each deal type;
    - the growth each deal must bring to pay the same: major 4.75×, independent 1.9×, label services 1.19×.
  - Advances and label marketing money are not public and not included (stated).
- **First result:** 12 unsigned in today's 191, 5 confirmed (BigXthaPlug, Aitch, YG, Lil Mosey, Powfu).
  `review/label_review.csv` lists 62 artists to settle in `registry/label_overrides.csv`.
- **Expansion:**
  - kworb's listener pages go to 11 pages, about 25,000 artists with 500,000+ monthly listeners. Pages 2-11 have no
    peak-rank column; the parser handles both.
  - The daily snapshot reads all pages. Raw page 1 is archived daily and pages 2-11 weekly (about 1.4 MB a day
    otherwise).
  - Candidates: 1,567 Wikidata hip-hop artists are in the 25,000; Wikidata alone would give about 750 hip-hop artists.
  - Deezer is added as a third genre source (`src/collectors/deezer_genres.py`): the share of an artist's releases filed
    under Rap/Hip Hop (genre 116) or Latin (122, 197). Checks: Drake 86%, BigXthaPlug 98%, Bad Bunny 25% rap and
    67% Latin, Bruno Mars 16%.
    - It settles MusicBrainz's borderline cases and decides when votes are thin.
    - It is used only with an exact name match and 5+ releases.
    - It runs for the top 12,000 artists (one-off, 8 workers within Deezer's limit).
  - The per-artist steps (streams, dates, labels, photos, YouTube) cover the top 1,000 hip-hop artists by monthly
    listeners (`TOP_N`).
- **Site at 1,000 artists:** fields only the artist page needs moved to `site/data/a/<id>.json`; the index went from
  476 KB to 218 KB at 191 artists.
- **Top 1,000 built:**
  - **Genre rule tightened:** a Deezer-only call now needs a Wikidata identity and a rap share of 0.7 or more. Artists
    from Spanish-speaking countries go to the Latin list. Colombian reggaeton acts and name-only matches had been
    entering. Result: 1,145 hip-hop artists, with 1,491 borderline artists in `review/genre_review.csv`.
  - **Bug fixed:** the streams step had been reading both hip-hop and review artists, so review artists took places
    within the 1,000 cap. It now reads hip-hop only.
  - **Coverage:**
    - ranked: 918 of 1,000 (the other 82 have under 80% of their streams dated);
    - label status known: 562 (350 major, 80 independent, 3 major-distributed, 129 self-released); 438 still unknown;
    - unsigned tab: 128 artists, 35 of them confirmed;
    - YouTube: 225; country charts: 275.
  - **Artist files:** one file per artist would be 1,000 files, more than an artifact publish allows (255). They are now
    grouped into 26 files, `site/data/a/<n>.json`. The group is set by the second character of the Spotify ID; the
    first gives only 8 groups, because every ID starts with 0-7.
  - **Preview photos:** the private preview carries 306 photos (top 300, unsigned, top 100 by monthly listeners). Any
    other artist shows initials. The deployed site carries all 731 photos.

## 2026-10-23 Fan demographics and more YouTube (owner: "go with your defaults, next do fan demographics. Try to find YouTube data related to artists")

- **Defaults confirmed by the owner:**
  - co-headlines at 50%;
  - artist tour net 15-35%;
  - grade C tour figures as context only;
  - worldwide platform shares;
  - Billboard year-end grosses stop at 30 September.
- **What can be measured, checked one source at a time:**
  - **Countries: measured.** kworb.net's copy of Spotify's weekly top 200 in 76 countries
    (`src/collectors/kworb_countries.py`, `data/spotify_country_charts.csv`). Every artist linked on a row is
    credited, featured artists included. It runs every Friday, and the site combines the last 4 weeks.
  - **Cities: not collected.** Spotify shows each artist's top 5 cities, but its terms bar collecting them.
  - **Age and gender per artist: not public anywhere.** Only licensed providers (Soundcharts from $50 a month,
    Chartmetric) model it from Instagram/YouTube/TikTok followers. This stays at the Phase 2 licence gate; it is
    spending, so it is the owner's call.
  - **Genre level: reported.** Luminate 2025 (349.9bn US streams, about 25%, falling), Edison Q2 2025 (3h48m a
    day), YouGov 2023 (+61 under 45 / -33 over 45). No recent reliable gender or ethnicity split exists; the ones
    that circulate are about 20 years old or unsourced, so none is shown.
- **Chosen: chart presence per artist, not shares.** The first version showed shares of chart streams. That
  misled: Playboi Carti showed "0% US, Malaysia 41%", because a small country's top 200 takes far fewer streams
  than the US one, so a guest verse charting there outweighs everything else. The artist page now lists countries
  and best positions. Shares are kept only for the top 100 combined, where big markets rightly dominate.
- **Fixed:** Wikidata gave Central Cee's citizenship as "English people". Values that are not countries are now
  dropped.
- **YouTube:**
  - kworb's YouTube artist list (`archive.html`) added 1 artist; 115 of 191 now have views.
  - The other 75 are not tracked by kworb. 70 of them, and 179 of all 191, have a channel ID on Wikidata.
  - Built `src/collectors/youtube_api.py` (YouTube Data API v3, channels.list, 1 unit per 50 channels). It runs
    when the GitHub secret `YOUTUBE_API_KEY` exists, and adds subscribers and channel views for 179 artists.
  - Per the API terms, it keeps only the latest snapshot (no history without YouTube's III.L approval).
  - **Rejected:** scraping YouTube channel pages or charts.youtube.com's internal API (terms).

## 2026-10-23 Platforms, revenue streams per artist, tours (owner: "add one tab for all streaming services ... and then begin with the work regarding revenue streams for each")

- **Research** (each claim with a URL; a grade on each figure):
  - `docs/research/research_platform_shares.md`: platform shares;
  - `docs/research/research_tours.md` + `registry/tours.csv`: 116 rows, 100 artists;
  - `docs/research/research_deals.md` + `registry/deals.csv`: 68 items, 29 artists.
  - Two deal figures were spot-checked against their sources: Drake/Stake $100m a year (FT via Complex, B), and
    Cardi B/Whipshots $3.3m minimum royalty (Starco 10-K, A).
- **Platforms (chosen):**
  - Spotify streams are measured, as before.
  - YouTube views are measured from kworb.net. A page is accepted only if it links back to the same Spotify ID;
    114 of 191 artists found.
  - Deezer fans are measured.
  - The other services publish no play counts. Their royalties are estimated as Spotify royalties × a multiplier
    (`registry/platform_multipliers.csv`), from WMG's FY2025 10-K and UMG's 2025 report: Spotify 20% of revenue,
    Apple 11%, YouTube 12%.
    - Cross-check: all non-Spotify services together come to about 1.9× Spotify; ours sum to 1.3× plus measured
      YouTube.
  - YouTube views are priced at $0.60-4.80 per 1,000, mid $1.50. Official-video ads pay less than Duetti's $4.80
    blended figure.
  - **Rejected:** scaling YouTube from Spotify when its views are measured. **Rejected:** a TikTok or Meta rate per
    view: both pay blanket licences.
- **Revenue per artist (chosen):** each line has two amounts that are never mixed.
  - **Generated:** before anyone's cut.
  - **Artist's slice:** after the label's or promoter's share, before the artist's own manager and tax.
  - Each line has a grade and a basis. Publishing is shown as generated only, because writer splits need song
    credits.
  - Brand and record deals are listed as reported, never annualised or added to the total.
  - Court figures are labelled as allegations.
- **Tours (chosen):**
  - Only A/B rows count toward money. The C rows are shown as context: Drake's full-tour $320.5m traces to a Genius
    Instagram post.
  - Overlapping rows count once.
  - Co-headlines count 50% to each artist, as an assumption (C).
  - A tour spanning the 12-month window counts pro rata by days. The split stops where the gross stops: Billboard
    year-end figures cover shows to 30 September.
  - Artist net is 15-35% of gross, a rule of thumb (C). Merch is tickets × $10.24-15.16 (ATVENU), less the venue's
    0-25% and 40-60% costs.
- **Tours page:** all counted tours since 2023, with per show, per fan and the artist's slice. A "where a ticket's
  money goes" explainer is marked as rules of thumb.
- **Gaps (stated on the pages):**
  - no reported gross for Playboi Carti, GloRilla, Doechii, Gunna or most non-US artists;
  - no data for 77 artists on YouTube;
  - no deals reported for 13 artists in the top 40.


## 2026-10-23 Current listeners: dating coverage fixed (method 1.1, no change to the weights)

- **Found on the first full run:**
  - 5,652 of 5,936 songs were dated, but only 115 of 191 artists reached 80% coverage.
  - Drake (50%), Kendrick Lamar (64%) and Gunna (69%) were not ranked.
- **Cause:**
  - The 40-song cap: Drake's 90% takes 249 of his 500 songs.
  - Deezer searches return covers and "sped up" uploads first.
  - Some catalogues are missing on Deezer ("Money Trees").
- **Chosen:**
  - cap 300;
  - the artist's own releases are checked first in the Deezer results (50 instead of 15);
  - "feat." suffixes are ignored when matching titles;
  - undated songs are retried (`dates-retry`);
  - a MusicBrainz recording search for songs Deezer cannot match (`data/musicbrainz_search_dates.csv`).
- **Rejected:** lowering the 80% rule to rank the big names. It would rank artists on a minority of their listening.
- **Cost:** about 10,900 songs in all; one-off, about 1 hour on Deezer and 2-3 hours trailing on MusicBrainz.

## 2026-10-23 Built: our own top 100 by "current listeners" (owner: "go with recommended, build it")

- **Owner's choices (all as recommended):**
  - age weight 1 up to 18 months, falling to 0 at 36 months;
  - featured songs at half weight;
  - old songs that rise again stay out of the score and get a "Revival" badge.
- **Formula:**
  - Not shown on the site yet (owner: "keep that formula as something we would show in the site in a later stage").
    The method page describes the ranking in general terms.
  - The full reference is `docs/METHODOLOGY.md`, version 1.1, also as a private page:
    https://claude.ai/artifact/6jUwKAZx52ZVhgWbEt95ny. The owner asked to be able to refer to it at any time.
  - Its worked example is checked against `src/current.py`.
- **Built:**
  - `kworb.parse_songs`: every song row of the archived artist pages: Spotify track ID, lifetime and daily streams,
    and guest spots (marked *).
  - `src/collectors/release_dates.py` dates the songs behind 90% of each hip-hop artist's daily streams (at most 40).
    - Deezer search (artist + title, credits must include the artist) gives the edition date and ISRC
      (`data/track_dates.csv`).
    - MusicBrainz by ISRC gives the first release date (`data/isrc_dates.csv`).
    - The earlier of the two is used.
  - Checked on Drake's songs: MusicBrainz corrects edition dates, e.g. "God's Plan" 2018-06-29 → 2018-01-19 and
    "Hotline Bling" 2016-05-06 → 2015-07-31.
  - `src/current.py`: current share, coverage, revivals. The revival rule needs a page 28+ days older, so it starts
    working with the second monthly refresh.
  - Site: the top 100 defaults to current listeners, with a switch to monthly listeners. Artists under 80% coverage
    are listed as "not yet ranked".
- **Changed for speed:**
  - 90% of streams and at most 40 songs per artist, instead of 95% and 60;
  - Deezer requests at 0.11 s (its limit is 50 per 5 s);
  - two caches so Deezer and MusicBrainz run side by side.
  - First run: about 5,900 songs, 2 hours. Later months: only new songs.

## 2026-10-23 Proposed: our own top 100 by "current listeners" (owner asked)

- **Owner's ask:** a top 100 that is not driven by old songs that are still streamed a lot.
- **Proposed:** current listeners = monthly listeners × the current share of the artist's daily streams.
  - **Current share:** daily streams weighted by song age (from the earliest release date), divided by all daily
    streams.
    - Weight 1 up to 18 months: the industry's line between current and catalog music.
    - Weight falls straight to 0 between 18 and 36 months, so an album does not drop off a cliff the month it turns
      18 months old.
    - Songs where the artist is the featured guest count at half weight.
  - **Displayed beside it:** monthly listeners, catalog share and momentum. Momentum is kept out of the formula so the
    ranking stays easy to explain.
- **Rejected:** "implied age" = lifetime streams ÷ daily streams. It needs no dates but fails: "Not Like Us" (2024)
  comes out as 7 years old, because hits earn most of their streams early.
- **Preview** on today's top 100, top 20 songs each, Deezer album dates:
  - Drake stays #1; Don Toliver moves 14 → 2; Doechii 48 → 6; Latto 98 → 17.
  - Kanye West, Travis Scott, Lil Wayne, 50 Cent, Eminem and XXXTENTACION fall out of the top 45.
- **Not good enough yet:** dates were found for a median 70% of the artists' lead-artist daily streams; Drake only 26%.
  - Misses are features and multi-artist credits (Metro Boomin at 0% is suspect).
  - Before production: Spotify track ID → ISRC → MusicBrainz first release date (CC0), with Deezer as a fallback.
  - Publish an artist's figure only when at least 80% of their streams are dated.
- **Outcome:** chosen as recommended; see the entry above.

## 2026-10-23 Phase 0 prototype: top 100 hip-hop on Spotify (built before the owner's answers; reversible)

- **Why build before the answers:** steps 0.1-0.5 use only free sources, and nothing is public. They give the owner a
  real list and site to react to, the same way the Sweden mock did for Hoop Ledger. Everything that depends on an
  open question (genre scope, money display, licence) is kept behind a switch or a review list.
- **Universe (0.1):**
  - **Chosen:** kworb.net's daily top 2,500 by monthly listeners.
    - The raw page is archived gzipped with its SHA-256 (`raw/manifest.csv`).
    - The rows of tracked artists go to `data/spotify_listeners.csv`. The first day keeps all 2,500.
    - 133 KB a day compressed, about 50 MB a year: move raw pages out of git later, as Public-Registry plans.
  - **Rejected:** Spotify Web API. Since February 2026 new apps get no followers or popularity, and monthly
    listeners were never in it.
  - **Rejected:** scraping Spotify's own artist pages. This is banned by Spotify's User Guidelines, and the pages
    only give rounded figures (94.6M).
  - **Risk accepted for a private prototype:** kworb compiles Spotify's public counts. Its tables are not
    republished; the site shows our own selection and derived figures with credit. Ask kworb's operator before
    any public use (question 1).
- **Genre (0.2):**
  - **Chosen:** candidates are Wikidata items that have a Spotify ID and a genre under hip-hop (Q11401). Of today's
    top 2,500, 406 are candidates. Recall checked on 30 well-known rappers: all 30 are in.
  - **Chosen:** the decision comes from the share of MusicBrainz community votes on hip-hop genres:
    - 50% or more: hip-hop;
    - 30-50%: review;
    - below 30%: other.
  - **Chosen:** Wikidata is used only where there are fewer than 3 votes, and then always goes to review.
  - **Chosen:** Latin trap and reggaeton are a separate bucket (`latin`) until the owner decides.
  - **Rejected:** Wikidata alone. It tags Bruno Mars, Ed Sheeran and Miley Cyrus as hip-hop.
  - **Licence:** MusicBrainz genre tags are CC BY-NC-SA. They are used only as an internal input and never shown.
    A commercial launch needs a MetaBrainz licence (or dropping the input).
- **Identity (0.3):**
  - **Chosen:** platform IDs come only from Wikidata statements (Spotify P1902, MusicBrainz P434, YouTube P2397,
    Instagram P2003, TikTok P7085, X P2002), never guessed.
  - **Chosen:** Deezer is matched by exact name; an ambiguous match is not shown.
- **Labels:** Wikidata record labels (P264), traced to a major through parent organisation (P749) or owned by (P127).
  - QIDs looked up: UMG Q38903, WMG Q21077, Sony Music Q56760250, Q330629 and Q11315210.
  - Caveat shown on the site: P264 lists labels over the whole career, not the current deal.
- **Money v0 (0.6, provisional):** Spotify recordings only.
  - Lead-artist streams a month × $2.50 / $3.00 / $4.40 per 1,000 (Duetti 2024, grade B; high end C) gives
    royalties generated.
  - × the artist's share by deal type gives take-home:
    - major 15-30% (UK CMA, A);
    - independent 20-80% (C);
    - unknown 15-100%.
  - Shown as ranges, labelled C, with "not the artist's pay" next to the generated figure.
  - **Rejected:** a single number, and influencer rate cards for brand deals.
- **Photos (0.5):** only Wikimedia Commons files with a CC or public-domain licence, with a credit on the artist
  page; initials otherwise. **Rejected:** Spotify, Deezer and Last.fm images (terms).
- **Site:** the same plain-file setup and look as Hoop Ledger (no build step; tokens in `styles.css`, lists in
  `config.js`, pages in `app.js`). It is private (`noindex`; Cloudflare Access when deployed).
- **Working name:** "Rap Ledger", by analogy with Hoop Ledger. The owner chooses (question 4).

## 2026-10-23 Discovery and roadmap

- **Research:** three reports with a URL for each claim are in `docs/research/`:
  - data sources;
  - artist economics;
  - market, labels, product and legal.
- **Chosen:** a private prototype on free data now, with licensed data (Soundcharts trial, then a public-display
  licence) as the gate before going public or paid (ROADMAP.md, Phase 2).
- **Rejected:** building on the official Spotify API. Since the February 2026 Development Mode changes it no longer
  gives followers, popularity or monthly listeners to new apps. Extended access needs 250k+ MAU, and Developer Policy
  III.13 bans derived listener metrics.
- **Rejected:** publishing unsourced fan demographics. There is no reputable public survey of hip-hop listeners by age
  or gender newer than about 20 years. Per-artist demographics come only from licensed aggregators, labelled
  "modelled".
- **Reframed:** the brief asks to compare "labels that pay x per stream". Public data cannot measure this, so the site
  shows instead:
  - deal types;
  - known terms from court filings and published contracts;
  - the take-home range those terms imply.
- **Rejected:** net-worth figures and Celebrity Net Worth-type sources (defamation risk, no method). Earnings are
  ranges, with royalties generated kept apart from take-home.

## 2026-10-23 Working agreement

- **Chosen:** the Public-Registry `session-architect` skill, adapted:
  - the standing rules now cover platform IDs, estimates and platform terms;
  - checkpoints are in `ROADMAP.md`;
  - the board is "Music Build Board".
- **Chosen:** no CLAUDE.md, as in Public-Registry (add rules only when a failure repeats).
- **Repository:** `main` was empty and was seeded with a one-line README so pull requests have a base. Work goes to
  `claude/music-roadmap`.
