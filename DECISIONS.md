# Decisions

What was chosen, what was considered and rejected, and why. Newest first.

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
