# Country: platform weights and the radio songwriting line (owner C5, 2026-10-24)

Research of 2026-10-24. Grades: A primary filing, B reputable secondary, C our estimate.

## kworb's radio audience is a 7-day figure

kworb.net/radio's `aud` for the #1 song on 2026-10-24 is 68.9m. Billboard's Radio Songs #1 in August 2026 had 67.7m
impressions for the week (Luminate): https://www.rttnews.com/story.aspx?Id=3680780 (B). So a year of airplay is
`aud x 1e6 x 52` impressions, not `x 365`. The top 100 in data/radio.csv add up to about 1.8bn impressions a week.

## 1. Country platform weights (Spotify recordings = 1; all C)

Evidence (platform-by-genre data are thin and 2017-2022):
- Pandora vs Spotify: country is 8% of Pandora streams vs 4.5% on Spotify (about 1.8x).
  https://hmc.chartmetric.com/crs-country-music-stats (B, 2022)
- Listeners' top-100 songs: country 39% for Pandora fans, 9% for Spotify fans, 29% for daily radio listeners
  (hip-hop/R&B: 17%, 26%, 19%).
  https://colemaninsights.com/coleman-insights-blog/how-platform-choice-impacts-contemporary-music-tastes (B, 2020)
- Amazon: about 2x the industry's share of country streams.
  https://hitsdailydouble.com/news&id=308026&title+AMAZON-ECHOES-IN-MUSIC-CITY (B, 2017; seen in search only) and
  "country bags a bigger share of listening on Amazon than anywhere else":
  https://www.musicweek.com/digital/read/amazon-music-director-ryan-redington-on-country-s-streaming-revolution/079179 (B, 2020)
- AM/FM is country listeners' most over-indexed music activity (+12%, Luminate):
  https://www.insideradio.com/free/luminates-year-end-report-includes-key-takeaways-for-radio/article_849eeee4-9250-11ed-a145-4bf1790bc31b.html (B)
- No Luminate, Edison or CMA table splits country by service.

Pandora's base: $1,270m royalties in 2024 (SiriusXM 10-K,
https://www.sec.gov/Archives/edgar/data/908937/000090893725000005/siri-20241231.htm, A) against Spotify's US revenue
of EUR 6,136m (20-F, https://www.sec.gov/Archives/edgar/data/1639920/000163992025000003/ck0001639920-20241231.htm, A);
assuming about 75% of Pandora's royalties go to recordings and Spotify pays about 50% of revenue to recordings (C),
Pandora pays about 0.29 of Spotify across all genres.

Proposed country multipliers (low / mid / high; hip-hop mid in brackets):

| platform | low | mid | high | basis |
|---|---|---|---|---|
| apple_music | 0.35 | 0.45 | 0.60 | (0.55) no sign country over-indexes on Apple |
| amazon | 0.40 | 0.55 | 0.85 | (0.30) the average x 1.5-2.2 |
| pandora (new) | 0.30 | 0.50 | 0.80 | 0.29 x 1.8 |
| others (without Pandora) | 0.05 | 0.10 | 0.20 | (0.30) Tencent/NetEase hardly matter for US country |
| deezer | 0.01 | 0.02 | 0.03 | |
| tidal | unchanged | | | |
| soundcloud | 0.005 | 0.01 | 0.02 | |
| audiomack | 0.001 | 0.002 | 0.005 | |
| tiktok | 0.02 | 0.04 | 0.08 | |
| meta | unchanged | | | |

YouTube uses measured views: no change. SiriusXM satellite stays in "others" (its royalty costs mix automaker and
talk costs). Not modelled: Pandora's non-interactive tier pays through SoundExchange, 45% straight to the artist.

## 2. Radio songwriting line: $0.15 / $0.25 / $0.40 per 1,000 audience impressions (C)

US AM/FM pays recordings nothing; it pays songwriters and publishers through ASCAP, BMI, SESAC and GMR.

Inputs:
- US radio over-the-air revenue 2024: $10.7bn (BIA),
  https://www.nysbroadcasters.org/post/bia-advisory-services-mid-year-report-positive-signs-for-radio (B)
- BMI 2.16% (2024), 2.20% for 2026-29 (RMLC settlement): https://radioink.com/?p=94187 (B)
- ASCAP about 1.73-1.75% before 2022, raised since on confidential terms; assumed 1.9-2.1%:
  https://www.musicbusinessworldwide.com/ascap-secures-higher-rates-in-settlement-with-us-radio-broadcasters (B/C)
- SESAC 0.2824% (B); GMR confidential, assumed 0.3-0.6% (C). Combined 4.6-5.2%.
- Music about 75-80% of radio listening (News/Talk 10.7%, Sports 4.4%, Nielsen Q3 2024):
  https://develop.nielsen.com/wp-content/uploads/sites/2/2024/10/The_Record_Data_Tables_Q3.pdf (B)
- About 3h51 of audio a day, 33% AM/FM (Edison): https://radioink.com/?p=103108 and
  https://www.westwoodone.com/wp-content/uploads/2026/03/Share-of-Ear_WWO.pdf (B); about 286m Americans 13+ (Census).

Arithmetic (low / mid / high):
- Pool = $10.7bn x 0.88 x music share (0.70/0.75/0.80) x PRO rate (4.6/4.9/5.2%) = $303m / $346m / $392m.
- After PRO overhead and non-feature uses (85/88/90%): $258m / $305m / $353m to writers and publishers.
- Impressions = 286m x AM/FM hours a day (1.35/1.27/1.20) x 365 x music share (0.80/0.77/0.75) x songs an hour
  (12/11/10) = 1.35tn / 1.12tn / 0.94tn a year.
- Pool / impressions = $0.19 / $0.27 / $0.38 per 1,000; rounded and widened to $0.15 / $0.25 / $0.40.
- Cross-check: the 2014 Touve/Rockonomic figure is about $0.19 per 1,000 net to writers and publishers:
  https://www.hypebot.com/in-2014-the-value-of-a-spin-per-listener-to-songwriters-on-us-radio-was-00000955/ (B)

Formula: `radio_songwriting = aud x 1e6 x 52 x rate / 1000`. Example: "Been By Now" (aud 48.65) is about 2.53bn
impressions a year: $380k / $632k / $1.01m for all of the song's writers and publishers.

## 3. Whose money

PRO money splits about 50/50 between writers and publishers. Country hits usually have 3-4 writers, often Nashville
staff writers, so the artist may get none of it. Shown as generated only (no artist slice), labelled "Radio airplay
(songwriters)", separate from the streaming Publishing line (they do not overlap). data/credits.csv's writers could
later give the artist's share.

Biggest uncertainties: ASCAP and GMR rates (about +/-15% on the pool); how many stations Luminate monitors and its
audience base; the platform tilts rest on 2017-2022 data.
