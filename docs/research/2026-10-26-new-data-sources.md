# New data sources: what is left to add (checked 2026-10-25/26)

Scope: sources the site does **not** use yet, for hip-hop and country rankings, money estimates, label and song
ownership, and scouting. Already in use (not re-proposed): kworb (Spotify listeners, streams, country charts, YouTube,
US radio), Deezer, Apple Music country charts (RSS), Shazam charts (incl. cities), Wikidata, Wikipedia (page views,
descriptions, discographies), MusicBrainz (genres, credits, labels, dates), Discogs labels dump, YouTube Data API and
feeds, SEC/ESEF filings, Companies House, Sony 6-K, Wayback. Earlier rejections are kept (DECISIONS.md 2026-10-24
"New sources, step 1"): RIAA site, Billboard, Official Charts, Bandsintown, Songkick, Tunefind, Instagram/TikTok
follower counts. The owner's K2 (DECISIONS.md 2026-10-24) keeps non-commercial-licensed sources open while the site is
non-commercial.

"Measured" below means a call was made from this project on 2026-10-25 with the contact User-Agent; artists are
Drake, Kendrick Lamar, Sexyy Red, SRNO, BigXthaPlug (hip-hop), Morgan Wallen, Zach Bryan, Luke Combs, Shaboozey,
Treaty Oak Revival (country).

## Ranked table

| # | Source | Gives | Access | Terms for our use | Measured coverage | Recommendation |
|---|---|---|---|---|---|---|
| 1 | **The MLC Public Search API** | Per song: writers, publishers, each publisher's collection share, administrators and parent publisher (who owns the song) | Free account (Data Access Hub); login as GitHub secrets | "any lawful purpose" | Not measurable without an account (HTTP 401) | **Built, skips until `MLC_USERNAME`/`MLC_PASSWORD` exist.** Fills the publishing half of "who owns it" |
| 2 | **ListenBrainz** | Listeners and plays per artist, last month and all time, from an open scrobble panel | Free, no key, 1 call/s | CC0, commercial use allowed | All 10 sample artists. Full run: 970 of 1,000 hip-hop and 740 of 757 country known; 944 and 704 with last-month listeners | **Built and run** (`listenbrainz` step). Tracks size broadly but is weak among artists of similar size, so it stays internal: a candidate Scout growth signal once the back-test has 3 months |
| 3 | setlist.fm API | Past concerts per artist (date, venue, city, tour name), by MusicBrainz ID | Free key | Non-commercial only; short caching only; attribution | Not measured (key) | Owner gets a key; then a show-count signal (live activity, tours page), counts only |
| 4 | Ticketmaster Discovery API | Upcoming events, venues, on-sale dates, sometimes price ranges | Free key, 5,000 calls/day, 5/s | No revenue from the API; cache "reasonable periods" | Not measured (key) | Owner gets a key; then upcoming tour dates for the tours money line (forward-looking) |
| 5 | Discogs releases dump | Per release: "Phonographic Copyright", "Published By", "Licensed To" companies | Free CC0 monthly dump (large) | CC0 (images restricted) | Not measured | Next offline step for ownership evidence where labels are unknown |
| 6 | Last.fm API | Listeners and scrobbles per artist, tags | Free key | Non-commercial; **public pages need Last.fm's written approval** | Not measured (key) | Owner writes to Last.fm for approval; only then build |
| 7 | GDELT DOC API | News article counts per artist per day | Free, no key, 1 call / 5 s | Open | Throttled from our shared address (HTTP 429); names under ~5 letters refused ("SRNO") | Run in Actions later as a Scout "press attention" signal; names need quoting rules |
| 8 | DART (Korea) for HYBE; Companies House API | HYBE (Big Machine, QC Media) accounts; UK independents and publishers (Kobalt, Beggars) | Free keys | Public filings | Not measured | Extends label economics; medium effort |
| 9 | Genius API | Song credits, page views ("stats") | Token | Terms page refuses automated fetch (403); lyrics licensed | API 401 without token | Not now; credits are already covered by MusicBrainz |
| 10 | Audiomack API | Rap charts and trending (strong for new hip-hop) | Consumer key, issuance unclear | Site bars spiders | API 401 ("Invalid consumer key") | Ask Audiomack for a key; Scout value is high for hip-hop |
| 11 | Google Trends API | Search interest by region | Alpha, by application | n/a | n/a | Apply for the alpha; not buildable now |
| 12 | IFPI, RIAA, Luminate year-end | Market totals | Free reports | Quote with source | Already in docs/research | Already used; refresh yearly by hand |
| — | Apple Music API city charts | City top 25s | $99/yr developer programme | — | — | Hard stop (costs money) |
| — | Spotify city and viral charts | City and viral charts | Login required | User Guidelines ban scraping | API 401 | No |
| — | YouTube Charts | Weekly artist and song charts | No API | robots.txt disallows `/api/`; ToS bars automated access | — | No |
| — | TikTok Creative Center | Trending sounds | No public API | TikTok ToS 3.4 bars automated extraction | — | No |
| — | Billboard | Charts | Pay-per-crawl (TollBit) | Answered HTTP 402 to our fetch | — | No (rejected 2026-10-24) |
| — | Bandsintown, Songkick | Tour dates | App ID / paid licence | Artist-only use / paid only | — | No |
| — | ASCAP / BMI Songview | Writers, publishers, shares | Web search only | Terms pages refuse automated fetch (403) | — | No; the MLC API gives the same kind of data under clear terms |
| — | US Copyright Office CPRS | Registrations and claimants | Web search only | No API found | — | No |
| — | Mediabase, Chartmetric, Soundcharts, Luminate data | Radio spins, cross-platform metrics | Paid | Paid licence | — | Note only (Phase 2 licence gate) |
| — | SoundCloud, Boomplay, Anghami, JioSaavn | Plays, regional charts | OAuth or no API | Boomplay's robots.txt disallows `/json/` and ClaudeBot | SoundCloud API 401 | Low relevance to US hip-hop and country; no |

## 1. The MLC Public Search API (built; needs a login)

- **What it gives:** search by ISRC → the MLC song code → the work, with:
  - the ISWC;
  - writers, with IPI numbers;
  - publishers, with `collectionShare`, role code, administrators and `parentPublishers` (the chain up to the
    owning group).
  - OpenAPI 1.2.0: https://public-api.themlc.com/api/doc (endpoints `/oauth/token`, `/search/recordings`,
    `/works`, `/work/id/{id}`).
- **Terms:**
  - "You may use the data in the Database for any lawful purpose" (https://themlc.com/musical-works-database-terms-use,
    s.1).
  - The database is reached through "a bulk download and/or public API that any member of the public can obtain or
    use" (s.2).
  - The MLC website itself bars "any robot, spider, scraper, or other automated means" without written permission
    (https://www.themlc.com/terms-use, s.3), so only the API is used, never the portal.
  - The MLC "makes no warranties … with respect to the accuracy or completeness" (s.7).
- **Access:**
  - Enrolment in the Data Access Hub (https://www.themlc.com/dqi; https://blog.themlc.com/resources/dataprograms says
    "Music publishers and administrators, DSPs, CMOs, music technology companies, and others can use the first
    version of The MLC's Public Search API in BETA").
  - No price is published. Confirm it is free at sign-up; any fee is a hard stop.
  - Without a token, `/search/recordings` answered HTTP 401 (measured), so coverage could not be measured.
  - Bulk data (DDEX BWARM) is a separate subscription. Its price is not published.
- **Rate limit:** none published. We use 1 a second.
- **Value:** the site's Labels section covers who owns the masters. It knows nothing about who owns the songs.
  - The MLC names the publishers and their US mechanical collection shares. It follows them up to the parent
    (Sony Music Publishing, UMPG, Warner Chappell, Kobalt, Concord …).
  - That allows a "publishing" ownership line per artist and a publishers' market share in Labels.
  - It also checks the songwriting money line (country's radio songwriting line, C5).
- **Effort:** collector, step, workflow and test done. Check the parser at the first live run: it was written from
  the schema.

## 2. ListenBrainz (built and run)

- **What it gives:**
  - `POST /1/popularity/artist`: all-time listens and distinct users per artist, up to at least 500 MBIDs a call
    (tested with 100, 200 and 500).
  - `GET /1/stats/artist/<mbid>/listeners?range=month`: listeners and listens in the last full calendar month. Other
    ranges: week, quarter, year, all_time, this_month.
  - Docs: https://listenbrainz.readthedocs.io/en/latest/users/api/popularity.html ,
    https://listenbrainz.readthedocs.io/en/latest/users/api/statistics.html
  - Artist stats update daily: https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html
- **Terms:**
  - "User listen data and text is made public under the Creative Commons Zero (CC0) license." This is the
    ListenBrainz page footer (`frontend/js/src/components/Footer.tsx` in https://github.com/metabrainz/listenbrainz-server).
  - "All of our data is available for commercial use." From the README:
    https://github.com/metabrainz/listenbrainz-server/blob/master/README.md
  - MetaBrainz asks companies "with a current revenue stream or an expected revenue stream" to take a support tier.
    Non-commercial and small non-profit tiers are $0: https://metabrainz.org/supporters/account-type
  - The site is non-commercial (K2), so nothing is due now. Revisit when the site earns money.
- **Rate limit:**
  - "All users of the API must ensure that each of their client applications never make more than ONE call per
    second" (https://listenbrainz.readthedocs.io/en/latest/users/api/index.html).
  - Response headers showed `X-RateLimit-Limit: 30` per 10 s.
  - We pace at 1 a second (`src/http.py`).
- **Measured (2026-10-25):** 

| Artist | ListenBrainz users, all time | ListenBrainz listeners, Sept 2026 | Spotify monthly listeners (kworb) |
|---|---|---|---|
| Drake | 154,532 (after the merged-ID redirect) | 3,497 | 94.7m |
| Kendrick Lamar | 117,917 | 5,482 | 69.9m |
| Sexyy Red | 7,274 | 438 | 17.4m |
| SRNO | 717 | 18 | 4.3m |
| BigXthaPlug | 4,750 | 504 | 19.7m |
| Morgan Wallen | 8,046 | 738 | 32.7m |
| Zach Bryan | 6,907 | 637 | 27.1m |
| Luke Combs | 6,273 | 577 | 24.3m |
| Shaboozey | 8,505 | 755 | 18.2m |
| Treaty Oak Revival | 726 | 93 | 9.4m |

  **Full run (2026-10-25, both top 1,000s, data/listenbrainz.csv):**

  - Hip-hop: 986 of 1,000 have a MusicBrainz ID. 970 are known to ListenBrainz and 944 have last-month listener
    stats. The median is 89 listeners; 348 have under 50.
  - Country: 748 of 757 have an ID, 740 are known and 704 have stats. The median is 26; 460 have under 50. Of the
    359 below the 500k floor, 316 have stats.
  - 17 artists were found only through a merged-ID redirect. 62 returned HTTP 204 (stats not computed).

  **Fit with Spotify monthly listeners (our calculation, log scale):**

  - Across all artists: hip-hop r = 0.58 (Spearman 0.53, n = 944); country r = 0.76 (Spearman 0.75, n = 388).
  - Among artists of similar size, the fit is weak:
    - country 500k–1.5m: Spearman 0.23 (n = 159);
    - hip-hop 0.5–3m: 0.15 (n = 421);
    - on the 119 country artists where both exist, Deezer's rank sum scores 0.30 and ListenBrainz 0.14.
  - Below the floor, against kworb daily streams: Spearman 0.31 (n = 62).
  - **Reading:** ListenBrainz separates big from small, but it does not order artists of similar size better than
    Deezer. It should not reorder the country floor list. Its possible use is change over time (a riser in an
    independent panel), which needs 2–3 stored months and the back-test.
- **Catches:**
  - The registry's Drake MBID (`9a1e8681…`) is a merged ID. ListenBrainz returned null for it; MusicBrainz redirects
    it to `9fff2f8a…`, which has 154,532 users. The collector follows such redirects (`data/musicbrainz_redirects.json`).
  - HTTP 204 for an artist the popularity table knows means "no listener stats computed". will.i.am gets 204 for
    every range. It is stored blank, never as zero.
  - The listeners response names the top users. Those names are removed before archiving.
- **Panel bias:** ListenBrainz users skew to rock and indie and to Europe. Drake has 3,497 listeners there in
  September 2026, against about 60m Spotify monthly listeners. Only ranks and month-on-month change are usable,
  never the counts as an audience size.
- **Effort:** done. About 1,700 calls, about 30 minutes, monthly.

## 3. setlist.fm

- **What it gives:** past setlists per artist (date, venue, city, country, tour), looked up by MusicBrainz ID
  (`GET /1.0/artist/{mbid}/setlists`): https://api.setlist.fm/docs/1.0/index.html
- **Terms:**
  - "You are permitted to use the API solely for non-commercial purposes" and "you must display attribution on your
    website or client application wherever Setlist.fm data is used" (https://www.setlist.fm/help/terms, s.4).
  - You may not "retain any copies of the Setlist.fm data, except for the purposes of retaining cached information
    for short periods" (s.3). So keep counts only, not raw setlists.
- **Rate limit:** not published. Community reports put it at 2/s and 1,440/day
  (https://apis.io/plans/setlistfm/setlistfm-plans-pricing/). At 1,440 a day, both top 1,000s take 2 days.
- **Value:** shows in the last 12 months per artist, a measured live-activity signal.
  - It helps the tours money line, where most artists have no reported gross. A show count times a capacity band
    would still be an estimate (grade C).
  - It also helps the "Established/Rookie" levels.
- **Recommendation:** owner registers (free) and adds `SETLISTFM_API_KEY`. Same pattern as the MLC collector.

## 4. Ticketmaster Discovery API

- **What it gives:** upcoming events by attraction (artist), with venue, date, on-sale date, and sometimes price
  ranges.
- **Quota:** "All API keys are issued with a default quota of 5000 API calls per day" and 5 requests a second
  (https://developer.ticketmaster.com/products-and-docs/apis/getting-started/).
- **Terms (https://developer.ticketmaster.com/support/terms-of-use/), you shall not:**
  - "Cache or store any Event Content other than for reasonable periods in order to provide the service you are
    providing";
  - "derive revenues from the use or provision of the Ticketmaster API".
  - So it is fine for a non-commercial site; revisit before ads or subscriptions.
- **Value:** the forward-looking half of tours: announced arena and stadium runs, before Billboard reports grosses.
  It would show on the artist page as "Upcoming shows (Ticketmaster)" with a link out.
- **Recommendation:** owner key `TICKETMASTER_API_KEY`. Match artists by Ticketmaster's own MusicBrainz or
  Spotify link where present, never by name alone.

## 5. Discogs releases dump (credits and companies)

- **What it gives:** the monthly CC0 releases dump (https://data.discogs.com/) lists, per release, companies with
  roles: "Phonographic Copyright (p)", "Copyright (c)", "Published By", "Licensed To", "Distributed By". That is
  evidence of who owns the masters and the publishing, and it covers releases our label table cannot place.
- **Terms:** the dumps are CC0. Images are "Restricted Data" (https://support.discogs.com/hc/en-us/articles/360009334593).
- **Effort:** medium-high. The releases dump is very large, so it has to be streamed and filtered by our artists'
  Discogs IDs (Wikidata P1953). Run it in Actions.
- **Value:** labels coverage (ROADMAP 8.1). It complements the MLC on publishing.

## 6. Last.fm

- **What it gives:** listeners and scrobbles per artist, and tags (`artist.getInfo`).
- **Terms (https://www.last.fm/api/tos):**
  - 3.1: "You are permitted to use the Last.fm Data solely for non-commercial purposes".
  - 2.7: "You agree to only give public access to pages using Last.fm's web services … that have been previously
    approved by Last.fm in writing".
  - 4.3.4: a 100 MB "Reasonable Usage Cap".
- **Value:** the biggest open listener panel. The roadmap names it as the second measure below the floor.
  ListenBrainz now covers that role in part, under clearer terms.
- **Recommendation:** owner writes to Last.fm for approval. Build only after a yes.

## 7. GDELT DOC API (news attention)

- **What it gives:** daily counts of news articles matching a phrase, worldwide
  (https://api.gdeltproject.org/api/v2/doc/doc, `mode=timelinevolraw`).
- **Measured:**
  - From this container's shared address, the first two calls returned HTTP 429 with "Please limit requests to one
    every 5 seconds".
  - A short name was refused: "The specified phrase is too short" (SRNO).
- **Value:** a Scout signal (press attention rising). Ambiguous names (Future, Drake, Shaboozey is fine) need
  quoting with "rapper" or "singer".
- **Recommendation:** later, in Actions (its own address), at 1 call per 5 s. It is free and open.

## 8. Company filings beyond the current set

- **HYBE:** owns Big Machine (country) and QC Media (hip-hop). It files in Korea on DART, which has a free key:
  https://opendart.fss.or.kr/
- **Companies House REST API:** a free key, for UK independents and publishers (Kobalt Music Group, Beggars Group,
  Domino). Today the collector reads the public website.
- **Value:** label economics on the Money and Labels pages. Medium effort, owner key.

## 9. Not recommended now, with the reason

- **Genius:** the API needs a token (HTTP 401). genius.com refused our fetch of its terms (HTTP 403), so the terms
  were not read. Its lyrics are licensed from publishers (https://lyricsgenius.readthedocs.io/en/latest/how_it_works.html).
  Credits are already covered by MusicBrainz.
- **Audiomack:**
  - `api.audiomack.com/v1/chart/...` answered "Invalid consumer key" (HTTP 401).
  - The docs (https://www.audiomack.com/data-api/docs) list rap charts and trending, but not how to get a key.
  - The site's terms bar using "any spider, readers, site search application, or other device to retrieve or index
    any portion" (https://audiomack.com/about/terms-of-service).
  - High value for new hip-hop: ask Audiomack.
- **Google Trends API:** alpha, by application only (https://ppc.land/google-opens-alpha-testing-for-new-trends-api-targeting-developers-and-journalists/).
- **Spotify charts (city, viral):** the chart service answered HTTP 401 without a login. Scraping is banned by the
  User Guidelines (https://www.spotify.com/us/legal/user-guidelines/). Country-level weekly charts already come
  through kworb.
- **Apple Music API city charts:** needs the Apple Developer Program at $99 a year
  (https://developer.apple.com/documentation/applemusicapi/charts.md). That is a hard stop. Country charts already
  come from the free RSS feed.
- **YouTube Charts:** no API. https://charts.youtube.com/robots.txt has `Disallow: /api/`. YouTube's terms bar
  automated access except by public search engines under robots.txt or with written permission
  (https://www.youtube.com/static?template=terms).
- **TikTok Creative Center:** TikTok's terms s.3.4 bar anyone to "scrape, crawl, export or otherwise extract any
  data or content in any form, for any purpose … using any automated system or software … except as approved in
  writing" (https://www.tiktok.com/legal/page/us/terms-of-service/en).
- **Billboard:** our fetch of billboard.com's terms was redirected to tollbit.billboard.com and answered HTTP 402
  Payment Required (pay-per-crawl). It was already rejected on terms on 2026-10-24.
- **Bandsintown:** the data terms are "meant to be used solely by artists, or people working in connection with or
  on behalf of artists" and bar aggregating its content "with third party content (without distinction)"
  (https://corp.bandsintown.com/data-applications-terms).
- **Songkick:** "not approving API requests for student projects, educational purposes or hobbyist purposes";
  licence fee only (https://www.songkick.com/developer).
- **ASCAP/BMI Songview:**
  - Writers, publishers and shares, free to search on each society's site (https://www.bmi.com/press/entry/585005).
  - There is no API, and both terms pages refused automated fetch (HTTP 403), so they could not be read.
  - The MLC API gives the same kind of data under "any lawful purpose".
- **US Copyright Office public records (CPRS):** a web search system since June 2025
  (https://copyright.gov/newsnet/2025/1071.html). No official API was found.
- **Paid (note only, Phase 2 licence gate):**
  - Mediabase (radio spins);
  - Luminate data feeds (https://luminatedata.com/faq);
  - Chartmetric (API from $350/month, https://chartmetric.com/plans/api);
  - Soundcharts (from $50/month, https://soundcharts.com/en/pricing/developers).
- **SoundCloud, Boomplay, Anghami, JioSaavn:**
  - SoundCloud's charts API answered HTTP 401 (OAuth app needed).
  - Boomplay's robots.txt disallows `/json/` and ClaudeBot (https://www.boomplay.com/robots.txt).
  - All are low relevance to US hip-hop and country.
- **IFPI, RIAA, Luminate year-end reports:** already cited in `docs/research/research_market.md`. Refresh them by
  hand each spring:
  - IFPI GMR 2026: $31.7bn, +6.4%:
    https://www.ifpi.org/global-music-report-2026-global-recorded-music-revenues-grow-6-4-as-record-companies-drive-innovation/
  - RIAA 2025: $11.5bn, a record: https://www.riaa.com/wp-content/uploads/2026/03/RIAA-Year-End-Revenue-2025.pdf

## 10. Integration proposal (for whoever edits `src/site_build.py` and `site/app.js`)

Nothing here is wired yet. Others are editing those two files, so this section is the specification.

**ListenBrainz (data present from today; internal until the back-test says otherwise)**

The measured fit (section 2) is weak among artists of similar size. So nothing is shown on the pages yet, and the
country floor order stays Deezer's.

1. **`src/site_build.py`:**
   - Next to `views, history = wikipedia.load(), wayback.load()` (line ~138), add `lbz = listenbrainz.load()`.
   - In the per-artist record (next to `"attention": ...`, line ~242), add
     `"lbz": {"users": r["users_month"], "month": r["month"], "history": r["history"][-12:]}`, only when
     `users_month` is set.
   - Put `"lbz"` in `DETAIL_ONLY`.
   - This carries the data for the back-test only.
2. **Scout, after 3 stored months (January 2027 at the earliest):**
   - Back-test a factor `"open_panel"` in `insights.raw_factors`: the change in ListenBrainz listeners over 2 months.
   - Only for artists with 50+ listeners in both months. Smaller counts are noise.
   - If it adds hit rate in `src/backtest.py`, give it a low weight in `FACTORS` (like `radio`), and add one Method
     line: "ListenBrainz (MetaBrainz Foundation), CC0: an open panel of listeners, used for change only".
3. **If it is ever shown** (owner's call):
   - one line on the artist page, "ListenBrainz listeners, <month>: N";
   - grade C;
   - a link to `https://listenbrainz.org/artist/<mbid>/`;
   - the note "a small open panel; useful for change, not audience size";
   - hidden when blank.

**The MLC (once the secrets exist and a first run has been checked)**

1. **`src/site_build.py`:**
   - Next to `song_credits` (line ~156), add `song_publishers(sid)`: for each of `hits[sid]`,
     `mlc.load().get(isrc)` → `[{publisher, share, top_parent, administrator}]`.
   - Group the `top_parent` (else the publisher) to a publishing group with the same owner table logic as labels.
     `registry/label_owners.csv` would gain publisher rows (Sony Music Publishing, UMPG, Warner Chappell, Kobalt,
     BMG, Concord, Reservoir, Downtown/Songtrust …).
   - Add `"song_publishers"` to `DETAIL_ONLY`.
   - A build-wide `"publishing"` block in `EXTRA_KEYS`: the share of the top songs' daily streams by publishing
     group, weighted by MLC share. Count only songs whose shares sum to 90–110%; report the others as "shares
     incomplete".
2. **Artist page:** extend "Who makes the hits" with a "Published by" column (publisher, share %, group).
   - The note: "Publishers and their US mechanical shares as registered with The MLC (the US mechanical licensing
     collective); shares are self-reported by publishers and may not add to 100%."
   - Link each song to `https://portal.themlc.com/search` (no deep links are known yet; check at the first run).
   - Grade B.
3. **Labels section:** a "Publishing" tab beside the masters market map: the publishing groups' shares of the top
   songs, with the same basis line as the masters shares ("among songs with complete MLC shares").
4. **Money:** the songwriting line (country C5 and the publishing share in `revenue.py`) can state "publisher on
   record: X (MLC)" rather than an assumed split. The figure stays an estimate with a range.


