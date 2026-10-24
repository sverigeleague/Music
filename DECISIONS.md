# Decisions

What was chosen, what was considered and rejected, and why. Newest first.

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
