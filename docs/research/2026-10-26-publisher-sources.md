# Who publishes a song, and who wrote it: free sources without The MLC (checked 2026-10-26)

**Question.** The owner will not open an MLC account, so `src/collectors/mlc.py` will not run. What free sources,
used within their terms, can say (a) who publishes each hit song, ideally with shares, and (b) who wrote it?

**This builds on** `docs/research/2026-10-26-new-data-sources.md`. That file already covers The MLC (row 1), the Discogs
releases dump (row 5), Genius (row 9: "not now") and ASCAP/BMI Songview (refused). The rows below are only repeated
where we measured something new.

**Short answer.**

- **Songwriters:** MusicBrainz, which we already use, names the writers of 34 of our 40 biggest hip-hop songs. Lower
  down the list it covers far fewer songs (about 1 in 6). Genius would roughly double coverage lower down, but only
  if the owner creates a free API token and confirms Genius's terms.
- **Publisher names:** MusicBrainz names publishers on 16 of the 40 biggest songs and about 1 in 20 songs overall. We
  already call it and the data is free to use (CC0), so this is the cheapest step. Genius names a "Publisher" on
  about 3 in 4 songs in the public examples, under the same condition as above.
- **Publisher shares (who owns what %):** no free source that allows automated use gives them. The MLC was the only
  one. ASCAP, BMI and Songview show shares, but BMI's terms ban automated lookups and ASCAP's could not be read.
  Without The MLC, the site can say **which publishers** are on a song, **not how much** each owns.

## Ranked table

Sample: the 40 biggest hip-hop songs in our data (lead artist, by all-time Spotify streams from kworb, at most 2 per
artist; ISRC from `data/track_dates.csv`), measured 2026-10-26. "Lower down" means 20 songs: the top song of 20
randomly chosen artists ranked 400–1,000. "All songs" means a random 80 of the 3,047 hip-hop songs in
`data/credits.csv` (each artist's 3 biggest songs).

| # | Source | What it gives | Writers: top 40 / lower 20 | Publisher: top 40 / lower 20 | Cost | Key | Terms verdict | Effort |
|---|---|---|---|---|---|---|---|---|
| 1 | **MusicBrainz works** (already used) | Writers, composers, lyricists; publishers (names, "sub-publisher" flag); ISWC (the song's ID code) | **34/40 (85%)** / 6/20 (30%); all songs: 13/80 (16%) | **16/40 (40%)** / 1/20 (5%); all songs: 4/80 (5%) | Free | No | **OK.** Core data CC0 (https://musicbrainz.org/doc/About/Data_License); 1 call/s (https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting) | **Small.** Add `label-rels` to the call `credits.py` already makes, and save publishers and ISWC |
| 2 | **Genius API** | `writer_artists`, `producer_artists`, and "custom performances" with labels such as "Publisher", "Copyright ©", "Phonographic Copyright ℗", "Label", "Performance Rights" | Estimated **27/27 (100%)** | Estimated **20/27 (74%)** | Free | **Yes:** free API client token (owner's Genius account) | **Unclear.** genius.com, docs.genius.com and the terms page all answered HTTP 403 to us, so we could not read them. A quoted copy says the service is "for personal use" and not for "direct commercial endeavors without the express written consent of Genius" (via https://developer.apple.com/forums/thread/132280). Lyrics are licensed and off limits (https://lyricsgenius.readthedocs.io/en/stable/how_it_works.html) | **Medium.** No ISRC lookup: search by title and artist, then confirm the match with the `apple_music_id` or Spotify link in the reply |
| 3 | **Discogs API** (unauthenticated) | Per release: "Published By" companies, "Written-By" credits | 11/40 (28%) / 2/20 | **3/40 tied to the song** (singles). On 6 more, an album-wide list of up to 50 publishers not tied to tracks / 2/20 album-wide | Free | No (search needs a free token; we reached releases through MusicBrainz's Discogs links) | **Probably OK.** Data is CC0 except images and user data (API Terms of Use, https://support.discogs.com/hc/en-us/articles/360009334593; page refused our fetch, read via search excerpts). 25 calls/min unauthenticated (measured header `x-discogs-ratelimit: 25`) | Medium. Adds little over MusicBrainz: only 1 extra song with a song-level publisher (Can't Hold Us) |
| 4 | **Wikidata** (already used) | Composer, lyricist, author (P86, P676, P50); publisher (P123) | 14/40 (35%) / 0/20 | **0/40** / 0/20 | Free | No | OK (CC0) | Small, but adds nothing MusicBrainz lacks |
| 5 | Deezer API (already used) | Only main and featured performers (`contributors`), plus the album label | 0 (no writers field) | 0 (no copyright line in the album reply) | Free | No | OK | n/a |
| 6 | iTunes Search API (free, no key) | Album "copyright" text | 0 | 0. It is the ℗ (recording) line, e.g. "℗ 2016 Young Money Entertainment/Cash Money Records" for *Views*: the record label, not the publisher | Free | No | n/a | n/a |
| — | ASCAP ACE, BMI Repertoire, Songview | Writers, publishers, **shares**, ISWC | — | — | Free to search by hand | No API | **No.** BMI bans "data-mining, scraping or crawling" and any "robot, spider, script or other automated query" (https://www.bmi.com/legal/terms-and-conditions-of-use, read via a search excerpt; the page answers 403). ASCAP's terms could not be read; ACE has no API | — |
| — | CISAC ISWC Net | ISWC, title, writers | — | — | Free download | Click-through licence | **Not for this.** The open-data licence only covers identifying a song's ISWC; "no additional rights" are granted (https://iswc.org/open-data) | — |
| — | SoundExchange / IFPI ISRC search | Recording facts (artist, label, year), not songs | — | — | Free | — | Web search only; terms not found. Not a publisher source | — |
| — | Spotify credits | Writers, producers (label-supplied) | — | — | — | Login | **No.** The Web API has no credits endpoint (developer forum, https://community.spotify.com/t5/Spotify-for-Developers/Request-Spotify-API-Credits-Endpoint/td-p/7503978); the app's credits panel needs a login, and scraping is banned (User Guidelines) | — |
| — | Apple Music API credits | Composers | — | — | $99/yr | Developer programme | **Stop: costs money** | — |
| — | TIDAL API | Credits (composer, publisher in the old v1) | — | — | Free | OAuth client | Credits in the public v2 API appear marked "INTERNAL" (copy of the spec at https://apis.io/apis/tidal/tidal-credits-api/); not confirmed on TIDAL's own site. Worth asking TIDAL, not building | — |
| — | The MLC | Writers, publishers, **shares**, parent company | — | — | Free | Account | "Any lawful purpose": the only source with shares. Ruled out by the owner | Built |

## What we measured

**MusicBrainz** (2026-10-26, our User-Agent, 1.1 s between calls; each ISRC → its recordings → their works with
writers and publishers → the work itself for its ISWC):

- **Top 40:** 39 found, 36 linked to a song (work), 34 with writers, 23 with an ISWC, 16 with publishers.
- **Lower 20:** 13 found, 6 linked to a song, 6 with writers, 1 with publishers (Project Pat, "Life We Live").
- **All songs:** 37 of 80 found, 12 with writers, 4 with publishers. This fits `data/credits.csv` as a whole: 535 of
  3,047 hip-hop songs (18%) have writers.
- **What the publisher lists look like:** they are long, typically 8 to 20 names per song (One Dance has 21). They
  mix original publishers, administrators and foreign sub-publishers. Only 10 of 182 links carry the "sub-publisher"
  flag, and a few Japanese sub-publishers appear under Japanese names.
  - On 14 of the 16 songs, the names can be grouped to Sony Music Publishing, Universal Music Publishing, Warner
    Chappell, Kobalt or BMG by simple name rules (EMI April, Sony/ATV → Sony; Songs of Universal → UMPG;
    Warner-Tamerlane, WC Music → Warner Chappell).
  - **Errors seen:** on One Dance and God's Plan, the record companies "Sony Music Entertainment" and "Universal Music
    Group" are entered as publishers.
  - There are **no shares**.
- **Biggest songs with no publisher in MusicBrainz include:** STAY, rockstar, goosebumps, Lucid Dreams, HUMBLE.,
  SICKO MODE, The Box, INDUSTRY BABY, In Da Club, Mask Off and Hey Ya!.

**Discogs** (2026-10-26, no token, through the Discogs "master" links on MusicBrainz release groups → main release;
2.5 s between calls):

- **Top 40:** 30 had a Discogs release, 11 had song-level "Written-By" credits.
- **"Published By":** 3 songs were singles, where the list is the song's own: Can't Hold Us, Without Me, Lose
  Yourself. On 6 albums the list covers the whole album (43 to 50 names) and cannot be tied to a song.
- **Lower 20:** 7 had a release, 2 had writers.

**Wikidata** (SPARQL, by ISRC and by MusicBrainz recording and work IDs):

- **Top 40:** 27 songs have an item. 14 have writers. **None has a publisher (P123).**
- **Lower 20:** 2 items, neither with writers.

**Genius** (estimated; we did not sign up):

- **Where the data came from:** we read Genius API replies saved in a public course project on GitHub
  (`radziko/dtu-02467-computational-social-science`, `project/data/lyrics/*.json`, collected 2023). It holds 27
  songs, the top songs of 9 hip-hop artists: YG, T.I., Quavo, NAV, JID, Swae Lee, EST Gee, BRS Kash and Southside.
- **Coverage:** all 27 had writers. 20 had a "Publisher" entry (e.g. Quavo "HUNCHO DREAMS" → Reservoir Media), 14
  had "Copyright ©" and 13 had "Performance Rights" (ASCAP/BMI).
- **Matching:** 27 of 27 carry an `apple_music_id` and 11 carry a Spotify link, which helps confirm a match.
- **Caveats:** this is a small, older sample of mid-to-big artists. The credits are entered by Genius users and
  labels, and there are no shares.

**Copyright lines:**

- `data/release_labels.csv` holds only Deezer's `label` field. Deezer's album reply has no ℗ or © line (checked on
  *Views*).
- The free iTunes lookup gives the ℗ line, which names the record label.
- So the copyright lines we can read do not name publishers. The © line on Genius sometimes does, because Genius
  copies it from the label's metadata.

Cached replies (scratch, not in the repo): `/tmp/claude-0/-home-user/ab6197c0-4f65-5d60-87c9-8d5130aa11e9/scratchpad/pub/`
(`cache/`, `result_sample.json`, `result_sample_mid.json`, `wikidata_*.json`, `genius_examples/`).

## Recommendation

1. **Do now (no owner action): extend the MusicBrainz credits step.**
   - **The change:** add `label-rels` to the `inc` of the recording call `credits.py` already makes. Save the work's
     publishers (name, MusicBrainz label ID, sub-publisher flag) and the ISWC in two new columns, then re-check
     `data/credits.csv` once.
   - **Cost:** no new calls per song beyond the one re-check pass.
   - **Show it as** "Publishers on record (MusicBrainz, volunteer-entered; no shares)". Grade C.
   - **Group names** to the five publishing groups with a small name table (publisher rows in
     `registry/label_owners.csv`, as planned for The MLC). Drop names that are record companies.
   - **Gives:** publishers for about 40% of the very biggest songs and about 5% overall. That is enough for a
     "Published by" line on top artists' pages. It is not enough for a publishing market share.
2. **Then, if the owner agrees (owner action needed): Genius as the main source.**
   - **What the owner does:** creates a free API client at https://genius.com/api-clients with his own Genius
     account and stores the "client access token" as `GENIUS_TOKEN`. This is a key, not logged-in scraping: the API
     is the documented route.
   - **What the owner also does:** opens https://genius.com/static/terms (and any API terms linked from the
     api-clients page) in a browser, because our fetches were refused. He confirms that showing writer and publisher
     names on a non-commercial public site is allowed. If the terms say "personal use only" for the API too, he
     writes to Genius first. Never touch lyrics.
   - **How it works:** per song, `/search?q=<title> <artist>`, then `/songs/<id>`. Accept a match only when the
     artist matches and the `apple_music_id` or Spotify link agrees. Cache each reply with its date. Keep to a polite
     1 call/s (no limit is published).
   - **Gives (estimated):** writers on nearly all hits and publisher names on about 3 in 4. That fills most of what
     MusicBrainz misses. Still no shares.
3. **Skip** Discogs for publishers: it adds 1 song in 40 over MusicBrainz, and album-wide lists cannot be tied to
   songs. The CC0 dump (earlier file, row 5) stays the better Discogs route for label evidence. Also skip Wikidata
   (no publishers), Deezer, iTunes, Spotify, Apple, ASCAP/BMI/Songview and ISWC Net.
4. **Say plainly on the site that shares are unknown.**
   - Any "publishing market share" would have to count songs per publisher group, not money. It must be labelled as
     such.
   - The MLC remains the only free source with shares under clear terms ("any lawful purpose"). If the owner ever
     changes his mind, `mlc.py` is ready.

## What the owner would need to do

- **For step 1:** nothing.
- **For step 2:** create a Genius account and API client (free), add the `GENIUS_TOKEN` secret, read Genius's terms
  in a browser and say yes or no, or email Genius if the terms are unclear about public display.
- **Nothing else** here costs money or needs a login to scrape.
