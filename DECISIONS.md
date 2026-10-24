# Decisions

What was chosen, what was considered and rejected, and why. Newest first.

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
