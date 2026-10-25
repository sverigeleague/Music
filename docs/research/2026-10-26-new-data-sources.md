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
| 1 | **ListenBrainz** | Listeners and plays per artist, last month and all time, from an open scrobble panel | Free, no key, 1 call/s | CC0, commercial use allowed | __LB_SAMPLE__ | **Built** (`listenbrainz` step). Second audience measure below the 500k floor and a monthly growth signal, internal first |
| 2 | **The MLC Public Search API** | Per song: writers, publishers, each publisher's collection share, administrators and parent publisher (who owns the song) | Free account (Data Access Hub); login as GitHub secrets | "any lawful purpose" | Not measurable without an account (HTTP 401) | **Built, skips until `MLC_USERNAME`/`MLC_PASSWORD` exist.** Fills the publishing half of "who owns it" |
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

__DETAILS__
