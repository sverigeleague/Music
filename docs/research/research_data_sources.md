# Audience-metric data sources for a music analytics site (checked 2026-10-23)

## TL;DR
1. **The official Spotify Web API no longer works as a metrics source for a new project.** Since 11 Feb 2026, new Development Mode apps get no artist `followers`, no `popularity`, no batch `GET /artists`, no top-tracks, and search is capped at 10 results. Dev Mode also needs the owner to have Premium and allows only 5 users. Extended Quota (which keeps the old fields) has been open only to registered organisations with at least 250k MAU since 15 May 2025. **Monthly listeners has never been in the official API.** Separately, Spotify's Developer Policy bans "creating new or derived listenership metrics", and its User Guidelines ban scraping.
2. **The practical Spotify feed is kworb.net (unofficial) or a licensed aggregator.** kworb publishes daily monthly-listener rankings (top 2,500) and per-artist stream totals. Licensed options are Soundcharts (API from $50/mo) or Chartmetric (API from $350/mo). Neither aggregator's standard terms allow you to republish its data on a public site. You need a written display or redistribution licence.
3. **YouTube Data API is free (10k units/day), but its rules work against trend history.** You may not store non-authorised statistics for more than 30 days, and you may not compute derived metrics. The exception is an audited "analytics use case" approval (Policy III.L, applications open since 1 Jun 2026).
4. **For a free MVP, the cleanest data is Deezer, MusicBrainz/Wikidata and Wikimedia Commons.** Deezer `nb_fan` needs no authentication. MusicBrainz and Wikidata give CC0 IDs and genres. Wikimedia Commons gives freely licensed photos. **Last.fm data is non-commercial only.**

---

## 1. Spotify

| Item | Current status | Source |
|---|---|---|
| Nov 2024 restrictions | Apps created on or after 27 Nov 2024 lost related artists, recommendations, audio features/analysis, featured and category playlists, preview URLs in multi-get, and algorithmic/editorial playlists. Older extended-mode apps were not affected. | https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api |
| Extended quota (15 May 2025) | Organisations only, no individuals. Requires a legally registered business, a launched service, **≥250k MAU**, presence in key markets and commercial viability. Review can take up to 6 weeks. | https://developer.spotify.com/blog/2025-04-15-updating-the-criteria-for-web-api-extended-access ; https://developer.spotify.com/documentation/web-api/concepts/quota-modes |
| Feb 2026 Dev Mode changes | New apps from 11 Feb 2026; existing Dev Mode apps from 9 Mar 2026. Owner must have Premium. 5 users per app. Removed: batch GETs, `/artists/{id}/top-tracks`, new releases, browse categories. Search limit cut to 10. **Artist `followers` and `popularity` removed.** Track and album `popularity` removed. Extended Quota apps are explicitly unaffected. | https://developer.spotify.com/documentation/web-api/references/changes/february-2026 ; https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide |
| Artist object | `followers`, `genres` and `popularity` are all marked **Deprecated**. `images` is not deprecated. Developers report that Dev Mode responses omit genres entirely; I could not confirm this in the official changelog. Even before this, about 25–30% of artists, mostly independents, had empty genre arrays (anecdotal). | https://developer.spotify.com/documentation/web-api/reference/get-an-artist ; https://github.com/marcelmarais/spotify-mcp-server/issues/73 ; https://community.spotify.com/t5/Spotify-for-Developers/Get-Artist-API-is-not-returning-any-or-all-Genres/td-p/6880841 |
| Monthly listeners | Not in any official API. It is visible only on artist pages in the Spotify clients, which scrapers read through internal web-player endpoints. | https://community.spotify.com/t5/Spotify-for-Developers/Monthly-listeners-API-endpoint/m-p/5526336/highlight/true ; https://apify.com/scrapesage/spotify-scraper |
| ToS | Developer Policy III.13: "Do not analyze the Spotify Content or the Spotify Service for any purpose", including "creating new or derived listenership metrics" and benchmarking. III.14 bans ML training. II.4 requires Spotify attribution and a link back. II.5: cover art may be used only in connection with the content. User Guidelines §5 ban "crawling" or "scraping … by automated means". | https://developer.spotify.com/policy ; https://www.spotify.com/us/legal/user-guidelines/ |
| Image display | Do not crop, distort or overlay artwork. Show the Spotify logo and link back ("OPEN SPOTIFY" and similar). | https://developer.spotify.com/documentation/design |
| charts.spotify.com | Daily and weekly top songs and albums for global, about 75 countries and cities. Daily charts publish before 22:00 UTC; the weekly window is Fri–Thu. The FAQ gives no reuse licence; the footer only links to the general spotify.com legal terms. CSV download needs login (from my background knowledge, **not verified**). I did not verify whether an official "top artists" chart exists. | https://support.spotify.com/us/artists/article/charts/ ; https://charts.spotify.com/charts/overview/global |
| Wrapped / Loud & Clear | Annual only. Wrapped 2025 global top 10 included Drake (#4) and Kendrick Lamar (#6). Loud & Clear 2026 (2025 data): $11B paid out, ~1,500 artists earned >$1M. Useful for editorial context, not for monthly metrics. | https://www.digitalmusicnews.com/2025/12/03/spotify-wrapped-2025-highlights/ ; https://www.hypebot.com/spotify-loud-clear-report-2026-11b-paid-as-global-musical-middle-class-expands |

## 2. Third-party aggregators

| Source | What you get | Access / cost | Republish? | Source |
|---|---|---|---|---|
| **kworb.net** | `/spotify/listeners.html`: daily top 2,500 artists by monthly listeners, with daily change, peak, and data since 1 Mar 2023. `/spotify/artists.html`: total, daily, lead, solo and feature streams per artist. `/spotify/artist/{spotifyId}_songs.html`: per-track total and daily streams (verified, updated 2026-10-22). Also YouTube, iTunes, radio and chart aggregates. | Free static HTML. robots.txt is `Allow: /`. No API. | No published terms. The underlying data comes from Spotify, so Spotify's ToS risk applies. It is a one-person site, so it is a single point of failure. Ask the operator for permission. | https://kworb.net/spotify/ ; https://kworb.net/spotify/listeners.html ; https://kworb.net/robots.txt |
| **Soundcharts API** | Spotify monthly listeners (latest and by month, plus the top 50 "where people listen" cities weekly), followers and popularity, socials, streams, playlists, charts, airplay. Audience reports cover Instagram, YouTube and TikTok demographics for accounts with ≥1k followers. | From **$50/mo for 10k queries**; volume tiers up to 100M+. 1,000 free test calls. Data shares from $2,000/mo. A Google snippet showed an older "$250/500k" price, so confirm. | ToS §5.3: "public exploitation of the Service and data" needs authorisation. Credit "Source: www.soundcharts.com". YouTube-derived data is bound by YouTube's terms. **Needs a written licence.** | https://soundcharts.com/en/pricing/developers ; https://www.soundcharts.com/en/terms ; https://doc.api.soundcharts.com/api/v2/doc/reference/path/artist/get-spotify-monthly-listeners-latest ; https://developers.soundcharts.com/api/reference/artist/get-audience-report-latest |
| **Chartmetric API** | Cross-platform artist, track, playlist, chart and social data, including Spotify listeners, TikTok, YouTube and Instagram. Audience demographics include age bands 13–17 through 65+, gender, city, language and ethnicity. | API **$350/mo (1 req/s)**, $600 (2/s), $1,200 (5/s), $2,000 (10/s). Data feed from about $1,000. Web plans $40–150/mo. | API terms were not publicly retrievable (404). **Not verified.** Assume a public-display licence is needed. | https://chartmetric.com/plans/api ; https://chartmetric.com/pricing ; https://help.chartmetric.com/en/articles/9221882-i-m-a-developer-which-chartmetric-plan-is-right-for-me ; https://chartmetric.com/use-cases/audience-insights |
| **Songstats Enterprise API** | Spotify, Apple, Amazon, Deezer, TikTok, YouTube, Instagram and more. | Pricing by email (api@songstats.com). A RapidAPI listing says each resource can be requested 100 times per 30 days by default (unverified). | Developer terms: developers.stats.company/terms (not read). | https://lab.songstats.com/the-songstats-api-enterprise-access-to-music-data-across-all-dsps-ee26e2a3b3b2 ; https://data.songstats.com/llms.txt |
| **Viberate** | Covers about 4M artists, refreshed daily. | Custom API quote. Web plans start around $19.90/mo. | Unknown. Ask. | https://www.viberate.com/pricing/ |
| **Luminate (Billboard data)** | US and Canada sales, streaming and airplay. More than 200 charts, including Billboard's. | Enterprise through an account rep. One A2IM promo was $495/mo with a one-year commitment (third-party report). | Enterprise licence. | https://luminatedata.com/faq ; https://yespress.io/luminate |
| **Musicstax** | Could not verify methodology or terms. Skip it. | | | |
| **Every Noise at Once** | Frozen since Dec 2023, when Glenn McDonald was laid off from Spotify. No successor found. | | | https://techcrunch.com/2024/02/12/every-noise-shut-down-spotify-layoffs |

Note: since 16 Jan 2026, YouTube data no longer counts toward Billboard US charts.
(https://www.hollywoodreporter.com/music/music-industry-news/youtube-stop-supplying-data-billboard-charts-1236453508/)

## 3. YouTube

- **Data API v3** gives `subscriberCount` (rounded down to 3 significant figures, and can be hidden via `hiddenSubscriberCount`), channel `viewCount`, and per-video view, like and comment counts. Starting 24 Aug 2026, `viewCount` counts a view the moment playback starts. https://developers.google.com/youtube/v3/docs/channels
- **Quota:** 10,000 units/day by default. `channels.list` costs 1 unit and `search.list` costs 100. You can't buy more quota; you raise it through a compliance audit. https://developers.google.com/youtube/v3/determine_quota_cost
- **Policy blockers:**
  - III.E.4: refresh or delete stored data within 30 days, and "must not store statistics retrieved as Non-Authorized Data for more than 30 days".
  - III.E.4.h: no "new or derived data or metrics".
  - III.E.2.a: aggregation is allowed only for channel data.
  - III.E.4.f: historical data may be shown "accurately in context of time".
  - III.L: audited analytics developers can apply for derived metrics and longer storage (applications open from 1 Jun 2026).
  - https://developers.google.com/youtube/terms/developer-policies
- **YouTube Charts** (charts.youtube.com) publishes weekly global and country Top Songs, Top Artists, Videos and Shorts. There is no official API, so you would have to scrape it. https://ppc.land/youtube-pulls-the-plug-on-billboard-charts-after-streaming-weight-dispute/

## 4. Other DSPs

- **Apple Music API:** catalog metadata plus a `charts` endpoint (most-played songs, albums and playlists by storefront and genre). It returns ranked lists, **not play counts**. Needs a developer token (Apple Developer Program, $99/yr). https://developer.apple.com/documentation/applemusicapi/charts.md
- **Deezer API:** `GET https://api.deezer.com/artist/{id}` returns `nb_fan` (Eminem: 19,152,526 on test) and images, with no auth. `/chart/{genre}/artists` exists, and Rap/Hip-Hop is genre 116 (from memory, not tested). I could not confirm the rate limit (commonly cited as 50 requests per 5 s) or the commercial-use terms. https://api.deezer.com/artist/13 ; https://developers.deezer.com/guidelines
- **SoundCloud API:** play-stream limit is 15k per 24 h. App registration has been intermittently closed; one 2026 vendor claims it now requires Artist Pro (unverified). Fields like `followers_count` and `playback_count` were not verified. https://developers.soundcloud.com/docs/api/rate-limits ; https://scrapecreators.com/blog/soundcloud-scrapers
- **Audiomack:** third-party catalogs describe a v1 API with OAuth 1.0a. I could not verify current key issuance. https://providers.apievangelist.com/providers/audiomack/
- **TIDAL:** the openapi.tidal.com v2 catalog API has no popularity or play metrics. https://providers.apievangelist.com/providers/tidal/
- **Amazon Music Web API:** still "closed Beta". https://developer.amazon.com/docs/music/API_web_overview.html

## 5. Social

- **TikTok:**
  - The Research API is for not-for-profit researchers only, in specific regions, and **commercial use is prohibited**. https://developers.tiktok.com/docs/en/research-api-faq ; https://developers.tiktok.com/docs/en/research-api-codebook
  - The Display/Login Kit `/v2/user/info/` endpoint returns follower and likes counts only for the user who authorised your app, so it is useless for other artists. https://developers.tiktok.com/docs/en/tiktok-api-v2-get-user-info
  - For other accounts' public follower counts and sound-usage counts, the options are scraping (against TikTok's ToS) or Chartmetric/Soundcharts.
- **Instagram:** Graph API **Business Discovery** returns `followers_count` and `media_count` (plus per-media like, comment and view counts) for *other* public Business or Creator accounts. You need your own Professional account, a Facebook-Login app and app review. Age-gated accounts are excluded. Rate limit is about 200 calls per user-hour (third-party figure). https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-facebook-login/business-discovery.md ; https://www.getphyllo.com/post/instagram-api-rate-limits-explained-and-how-to-scale-beyond-them-2026
- **X/Twitter:** pay-per-use is the default since Feb 2026, at about $0.01 per user lookup. Legacy Basic was $200/mo and Pro $5,000/mo. Figures are from secondary sources. https://www.postproxy.dev/blog/x-api-pricing-2026/ ; https://gigazine.net/gsc_news/en/20260209-x-api-pay-per-use
- **Facebook Pages:** follower counts of other Pages need the Page Public Content Access feature and app review. Not verified in this pass; low priority.

## 6. Genre classification ("hip-hop/rap")

Spotify's genres field is deprecated, absent in Dev Mode, and empty for many independent artists. Recommended approach:

- **Wikidata** P136 (genre), with values hip-hop music Q11401, rap/trap and subgenres. Wikidata also holds P1902 (Spotify artist ID) for joining datasets. It is CC0. https://www.wikidata.org/wiki/Property:P136 ; https://www.wikidata.org/wiki/Property:P1902
- **MusicBrainz** genre entities are CC0, but genre *tags* on artists are supplementary data under **CC BY-NC-SA 3.0**, so commercial use needs a MetaBrainz licence. Rate limit is 1 request/s per IP, with a descriptive User-Agent required. https://musicbrainz.org/doc/MusicBrainz_Database ; https://musicbrainz.org/doc/About/Data_License ; https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- **Last.fm** top tags are useful as a signal but the data is non-commercial only (see section 8).
- **Rule:** classify an artist as hip-hop if at least two of these agree: Wikidata P136, MusicBrainz tag, Last.fm tag, or Spotify genre (where available). Keep a manual override table for the top 100. Seed the candidate list from Deezer chart genre 116 and kworb or Spotify chart artists.

## 7. Artist images

| Source | Public-site legality | Source |
|---|---|---|
| Spotify API images | Allowed only alongside Spotify attribution and a link back, with no crop or overlay. The images are tied to API use, which is itself restricted for analytics. | https://developer.spotify.com/policy ; https://developer.spotify.com/documentation/design |
| Deezer `picture_*` | No explicit licence found. **Risky.** | https://developers.deezer.com/guidelines |
| Last.fm | Images are expressly excluded from the licence (ToS 5.1.8). | https://www.last.fm/api/tos |
| **Wikimedia Commons** (via Wikidata P18) | **Best option.** Each file carries a CC-BY/CC-BY-SA/PD licence; show author, licence and link. Personality-rights caveat: don't imply endorsement. | https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia |
| fanart.tv | Fan-uploaded; its ToS page blocked fetching (403). Copyright stays with labels and photographers. **Treat it as not licensed for commercial use.** | (not verified) |
| Discogs | Images are "Restricted Data". | https://support.discogs.com/hc/en-us/articles/360009334593 |

Fallback when no free photo exists: a generated monogram or initials avatar.

## 8. Free and open data

- **MusicBrainz:** IDs, relationships and URL links to Spotify, Deezer, YouTube and Instagram. Core data is CC0; tags and ratings are NC (see above).
- **Wikidata:** CC0. Provides IDs, genre, P18 image, birth date, country and origin city. Use SPARQL or dumps; the API rate-limited my test immediately, so cache aggressively. https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits
- **Last.fm API:** `artist.getInfo` gives `listeners` and `playcount` (scrobbles). The ToS restricts it to "solely for non-commercial purposes"; commercial use needs a separate agreement. You must credit Last.fm, and there is a 100 MB cache cap. Last.fm users skew toward rock/indie, so it under-represents hip-hop. https://www.last.fm/api/tos
- **Discogs:** monthly CC0 dumps of release, artist and label data. API limit is 60 requests/min authenticated. No audience metrics. https://support.discogs.com/hc/en-us/articles/360009334593

## 9. Fan demographics for *other* artists

- **Spotify:** no public API for demographics. Spotify for Artists covers only your own roster. The public artist page shows the top 5 "where people listen" cities (seen in the client; not checked against an official document this pass). Soundcharts exposes the top 50 cities weekly.
- **Chartmetric / Soundcharts:** age, gender and country/city audience data from Instagram, TikTok and YouTube (inferred via third-party audience panels). Paid, and needs a display licence.
- **Public surveys (genre-level only):**
  - Edison Research Share of Ear Q2 2025: hip-hop/R&B-primary listeners spend the most daily time with music, 3h48m. https://news.radio-online.com/articles/n47712/Hip-Hop-R&B-Fans-Lead-in-Daily-Music-Listening
  - Luminate 2025 Year-End: R&B/hip-hop is still the #1 US genre with 349.9B on-demand audio streams. https://luminatedata.com/wp-content/uploads/2026/01/2025-Year-End-Music-Report-1.2026.pdf ; https://www.ajournalofmusicalthings.com/luminates-year-end-report-of-music-in-2025-is-here/
  - I found no reliable 2025 age, gender or ethnicity survey of hip-hop listeners. Pew was not found. Statista-sourced aggregator figures are undated, so **don't publish them as fact**.

---

## Source summary

| Source | Key metrics | Access | Cost | ToS/republish risk | Reliability (1-5) |
|---|---|---|---|---|---|
| Spotify Web API (Dev Mode) | IDs, names, images (no followers or popularity) | OAuth, 5 users, Premium | Free | High (III.13 analytics ban) | 2 |
| Spotify Web API (Extended) | + followers, popularity, genres (deprecated) | ≥250k MAU, organisation | Free | High | 4 (if you can get it) |
| Spotify monthly listeners (scrape) | Monthly listeners, top cities, track play counts | Internal endpoints | Free / Apify | **Very high** (scraping ban) | 3 |
| charts.spotify.com | Top songs/albums daily and weekly, with streams | Web, CSV after login | Free | Medium–high | 5 |
| kworb.net | Monthly listeners (top 2,500), total and track streams, YouTube views | Scrape static HTML | Free | Medium–high (derived from Spotify, no licence) | 4 |
| Soundcharts API | Everything incl. monthly listeners, cities, demographics | API key | From $50/mo | Needs written public licence | 4 |
| Chartmetric API | Everything incl. demographics | API key | $350–2,000/mo | Needs written licence (terms unverified) | 4 |
| Songstats / Viberate / Luminate | Cross-DSP; Luminate US consumption | Sales | Quote; Luminate ~$495+/mo | Licence | 3–5 |
| YouTube Data API | Subscribers (3 significant figures), views | API key | Free, 10k units/day | 30-day storage, no derived metrics (unless III.L approved) | 5 |
| YouTube Charts | Weekly top artists and songs | Scrape | Free | Medium | 5 |
| Apple Music API | Chart ranks (no counts) | Dev token | $99/yr | Low–medium | 4 |
| Deezer API | `nb_fan`, charts, images | No auth | Free | Unclear | 4 |
| SoundCloud / Audiomack | Followers, plays | Gated / unclear | Free | Unclear | 2 |
| TikTok Research API | Followers, likes, views | Academic only | Free | **Commercial use banned** | n/a |
| Instagram Business Discovery | `followers_count`, media stats | Graph API + app review | Free | Low–medium (Meta Platform Terms) | 4 |
| X API | Followers | Pay-per-use | ~$0.01 per lookup | Low | 4 |
| Last.fm API | Listeners, scrobbles, tags | API key | Free | **Non-commercial only** | 3 (skews away from hip-hop) |
| MusicBrainz | IDs, links, tags | API/dumps, 1 req/s | Free | Core CC0; tags NC | 4 |
| Wikidata / Commons | Genre, IDs, images | SPARQL/dumps | Free | CC0 / per-file CC | 4 |
| Discogs | Discography metadata | API/dumps | Free | CC0 dumps; images restricted | 4 |

## Recommended stack

### (a) Free MVP: top 100 hip-hop on Spotify, monthly
1. **Universe:** scrape kworb `listeners.html` once a month. Snapshot daily if you can, because the page only shows the current day. Filter to hip-hop using Wikidata P136 plus MusicBrainz and Last.fm tags plus a manual review of the top 100. Join IDs through Wikidata P1902 and MusicBrainz URL relations.
2. **Metrics:**
   - kworb: monthly listeners, total streams, top-track streams.
   - Deezer `nb_fan`.
   - YouTube `subscriberCount` and `viewCount`. Store only the latest value, refresh within 30 days, and show history only "in context of time". Or apply for III.L before keeping a series.
   - Optionally Last.fm listeners, only while the site is non-commercial.
3. **Breakout signal:** month-on-month % change in monthly listeners and daily stream velocity from kworb, together with the Deezer fan delta. Restrict it to artists below the top 100 (kworb lists 2,500).
4. **Images:** Wikimedia Commons with credits; monogram fallback.
5. **Do:** credit every source, link to the Spotify profile, ask kworb's operator for permission, keep the site non-commercial (no ads) until a licence is in place.

### (b) Scaled paid version: top 1,000 per genre, all platforms
- **Primary licensed feed:** Soundcharts or Chartmetric, under a **negotiated redistribution/public-display licence** (expect enterprise pricing well above list). This covers monthly listeners, cities, TikTok, Instagram and YouTube, plus demographics.
- **Supplements:** official APIs where the terms allow (YouTube with III.L approval, Instagram Business Discovery, Deezer, Apple charts, X pay-per-use), Luminate for US consumption, and Wikidata/MusicBrainz (with a MetaBrainz commercial licence if you use tags).
- Your own entity resolution and genre taxonomy, stored in your own database.

## Explicit risks
1. **Spotify legal and policy risk:** monthly listeners only exist through scraping. Analytics on Spotify data is barred by Developer Policy III.13, and scraping by User Guidelines §5. A cease-and-desist or IP block is plausible. kworb could disappear or block you.
2. **Policy drift:** Spotify has tightened access in Nov 2024, May 2025 and Feb 2026. Expect more.
3. **YouTube** month-on-month history is non-compliant without III.L approval.
4. **Aggregator licences:** the Soundcharts ToS explicitly forbids public exploitation without authorisation; I could not read Chartmetric's terms.
5. **Data quality:** subscriber rounding; YouTube's view-count definition change on 24 Aug 2026; Spotify's 28-day rolling listener window; missing days in feeds; streaming fraud inflating breakout signals. Require multi-platform confirmation before flagging a breakout.
6. **Images and likeness rights:** never hotlink DSP images without the matching terms.
7. **Demographics** for other artists are modelled estimates from paid vendors. Label them as estimates.

## Not verified
- Chartmetric API terms.
- Songstats terms and pricing.
- Deezer commercial terms and rate limit.
- fanart.tv terms.
- SoundCloud registration status.
- Whether charts.spotify.com has an official top-artists chart, and whether CSV export needs login.
- Musicstax methodology.
- Facebook PPCA details.
- Spotify's official status for `genres` in Dev Mode.
- A current demographic survey of hip-hop listeners.
- Some X and TikTok figures come from secondary blogs.
