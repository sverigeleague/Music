# Smaller acts below kworb's floor: Deezer fans and the other free size signals, country by country

2026-10-26. Owner: "yes, look into deezer fans for smaller countries", then "triangulate with other sources to make the
ranking as robust as possible". Code: `src/collectors/small_acts.py` (who and what is read), `src/small_acts.py` (the
calibration, the hold-out check and the score), `site_build.add_smaller` (the page data).

## The question

Scout's country view ranks each country's artists by the Scout score, which needs Spotify monthly listeners. The only
free source of those is kworb.net, which lists Spotify artists down to about 500,000 monthly listeners. So Sweden has
15 scored hip-hop artists, Canada 24, Denmark 12, Finland 7 and Norway 5. Can free sources rank the acts below that
floor, and how far can such a ranking be trusted?

## 1. Deezer fans alone

Deezer fans (`nb_fan`) were set against Spotify monthly listeners for every artist that has both (kworb's latest
listener pages; Deezer IDs from the registry and `data/deezer_genres.csv`): 21,737 artists of all genres.

- Across all genres the rank correlation (Spearman) is **0.37**; hip-hop **0.50** (2,499 artists), country 0.59.
- The listeners-per-fan ratio swings by country, as expected from Deezer's market (median Spotify listeners per Deezer
  fan, hip-hop): France 3, Belgium 5, South Africa 6, Brazil 20, Germany 33, United Kingdom 46, Netherlands 50, United
  States 70, Italy 81, Canada 144, Poland 170, Sweden 278, Norway 507, India 1,667. One fan stands for 100 times more
  listeners in Norway than in France.
- Within a country, fans order hip-hop artists only moderately: United States 0.70, Canada 0.68, Brazil 0.54,
  France 0.52, Netherlands 0.51, Germany 0.49, United Kingdom 0.42, Sweden 0.34, Belgium 0.32, Poland 0.30,
  Denmark 0.29, Turkey 0.17, Russia 0.02 (Norway and Finland: too few artists to say).

Deezer fans are a cumulative "favourite" count: they never fall, so older acts keep fans long after listening moves
on. On their own they are too weak in the Nordics, Poland, Turkey and Russia to rank anyone.

## 2. The other free signals, and how each agrees with Spotify listeners

The same comparison for every candidate signal, on the registry's artists with kworb counts (hip-hop 2,211, country
384; `data/small_acts_calibration.csv`). Spearman of each signal with monthly listeners within the country; the last
column is the combined estimate (section 3) on artists held out of the fit.

Hip-hop:

| Country | artists | listeners per Deezer fan (median) | Deezer fans | Deezer track rank | Wikipedia | ListenBrainz | combined (hold-out) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **All** | 2211 | 48 | 0.50 | 0.53 | 0.50 | 0.31 | **0.69** |
| United States | 858 | 70 | 0.70 | 0.79 | 0.60 | 0.43 | 0.77 |
| France | 207 | 3 | 0.52 | 0.74 | 0.44 | 0.28 | 0.69 |
| Germany | 172 | 33 | 0.49 | 0.64 | 0.36 | 0.27 | 0.64 |
| Brazil | 138 | 20 | 0.54 | 0.74 | 0.54 | 0.34 | 0.70 |
| United Kingdom | 120 | 46 | 0.42 | 0.73 | 0.47 | 0.39 | 0.70 |
| Italy | 97 | 81 | 0.53 | 0.70 | 0.59 | 0.38 | 0.69 |
| Poland | 77 | 170 | 0.30 | 0.69 | 0.43 | 0.32 | 0.53 |
| Turkey | 56 | 39 | 0.17 | 0.77 | 0.69 | -0.01 | 0.71 |
| Netherlands | 53 | 50 | 0.51 | 0.60 | 0.40 | 0.01 | 0.62 |
| Russia | 43 | 114 | 0.02 | 0.45 | 0.51 | 0.22 | 0.51 |
| Spain | 25 | 94 | 0.40 | 0.67 | 0.56 | 0.38 | 0.60 |
| Canada | 24 | 144 | 0.68 | 0.71 | 0.60 | 0.68 | 0.74 |
| Sweden | 15 | 278 | 0.34 | 0.53 | 0.47 | 0.50 | 0.70 |
| Denmark | 12 | 135 | 0.29 | 0.28 | – | -0.14 | 0.44 |
| Australia | 11 | 76 | 0.69 | 0.94 | – | 0.33 | 0.80 |
| Belgium | 11 | 5 | 0.32 | 0.10 | 0.71 | 0.41 | 0.33 |
| Finland | 7 | 129 | – | – | – | – | 0.64 |
| Norway | 5 | 507 | – | – | – | – | 0.10 |

Country music: all 384 artists 0.59 (fans), 0.78 (track rank), 0.59 (Wikipedia), 0.31 (ListenBrainz), **0.76
combined**; United States (368) 0.76, Canada (13) 0.91. "–": under 8 artists with that signal.

What each signal is:

- **Deezer track rank:** the sum of Deezer's `rank` over the artist's top 10 tracks (`artist/{id}/top`). The best
  single signal almost everywhere: it follows current listening, where fans accumulate.
- **Deezer fans:** see section 1.
- **Wikipedia:** monthly views of the English and the home-language article (sv, no, da, fi, nl, fr, de... from the
  Wikidata sitelinks), last three full months. Only artists with an article (about two in three).
- **ListenBrainz:** all-time listeners in its open panel (by the MusicBrainz ID on Wikidata). Weak, as the earlier
  test found; it adds little but costs one request per 500 artists.
- **YouTube subscribers:** not measurable here (the key exists only as a GitHub secret). The official channel IDs are
  added (Wikidata P2397: 186 smaller hip-hop acts, 2 country), the daily `ytapi` step reads them from its next run,
  and the estimate takes them in once the data lands. The page says when it is not in yet.
- **Local charts** (Spotify weekly top 200 per country from the archived kworb pages, by Spotify ID; Apple Music daily
  top 100 and Shazam country and city charts, by exact name): presence says something real, but few smaller acts
  chart (25 of 331 hip-hop acts), so it is a score signal, not a size signal.
- **Official national charts** (Sverigetopplistan, VG-lista, Hitlisten, the Finnish list): not used. Their terms were
  not read in this pass, and Spotify's weekly top 200 per country (already held) is deeper than their top 40-60, which
  are mostly streaming-based anyway. Left as a follow-up.

## 3. The method

1. **Put every source on one scale.** For each source, on the calibration artists, fit
   log10(source) = c[country] + d · log10(listeners). The source is regressed on listeners, not the reverse: the
   calibration set is cut at kworb's floor, a cut on listeners, which leaves this slope unbiased (the reverse fit would
   be flattened by the cut). The country term carries the "Deezer is big in France" effect; it is shrunk toward the
   genre's pooled term by n / (n + 10), so a country with few calibration artists leans on the pool. Each reading
   then gives an estimate (x − c[country]) / d.
2. **Weigh by how well each source orders artists** within countries (its pooled within-country Spearman r: weight
   r² / (1 − r²); no source above half the total weight). Weighing by the sources' rank agreement beat weighing by
   their residual variance on the hold-out (hip-hop 0.69 against 0.65): Deezer's track rank is monotonic with
   listeners but not linear in log terms.
3. **Combine robustly:** the weighted median of the sources' estimates, then the weighted mean of the estimates
   clipped to within a factor of about 3 of that median. No single source decides.
4. **Agreement as confidence:** a source within a factor of about 3 of the combined estimate "agrees". The page shows
   "3 of 4". When fewer than half agree, the artist is flagged ("sources disagree") and ranked after the others. On the
   hold-out set this flag marks 6% of artists; their median miss is 2.9 times against 1.7 for the rest, and their rank
   correlation 0.42 against 0.71. Among the smaller acts themselves the flag is far more common (86 of 331 hip-hop
   acts, 26%): the sources disagree more below the floor, one more reason the list is provisional.
5. **Hold-out check:** ten folds, each artist estimated from a fit made without it; Spearman of the estimate with true
   listeners per country (table above), median miss 1.7 times (hip-hop) and 1.6 times (country).

**The limit.** Every tested artist sits above the floor. Within a narrow band the method is much weaker: for
hip-hop artists with 500k to 1.5m listeners the hold-out rank correlation is 0.31 (United States 0.27, France 0.27,
Germany 0.35, Netherlands 0.46, Sweden 0.54 on 13). Smaller acts span a wider range (from a few thousand listeners to
500k), which is closer to the full-range 0.69, but below the floor the calibration is an extrapolation. So the page
shows size as a third of the set (larger, mid, smaller), never as a listener figure.

## 4. Who: finding the smaller acts

Spotify IDs only from a source that links them; Deezer alone gives none.

1. **Wikidata:** items with a hip-hop genre (P136 under Q11401) or the occupation rapper (P106), or a country genre
   (Q83440), with a Spotify ID (P1902) or a Deezer ID (P2722). Country: P27/P495 by QID (src/origin.py's rule).
   7,777 hip-hop and 1,399 country items.
2. **Deezer's related artists** of those and of the registry's artists from the same countries: 11,823 read for
   hip-hop. Kept only when a Wikidata item carries that Deezer ID (933); the other 6,043 have no country source and are
   not listed anywhere (counted only).
3. **MusicBrainz url relations** for Wikidata items with no Deezer ID but a MusicBrainz ID (870 looked up at 1 a
   second): the one Deezer page the MusicBrainz artist links, when it links no other Spotify page.
4. Left out: anyone on kworb's listener pages or already in the registry; countries whose view already has 100 scored
   (hip-hop: United States, France, Germany, Brazil, United Kingdom; country: United States).
5. **Genre** through the registry's rule (`genre.decide`, then `decide_country`), with Wikidata linking the Deezer
   page (match "links") and no MusicBrainz votes (not read, to spare MusicBrainz). Spanish-speaking countries go to
   review, as the owner's rule says. Two Spotify IDs on one item: review.
6. **Active:** no release in three years: a past act, not listed (as the country site's below-floor list).

Hip-hop result: 2,784 candidates; 389 accepted, 1,638 to review, 757 other genres. Country: 404 candidates; 8
accepted, 181 to review, 215 other. Review file: `review/small_acts_review.csv` (1,819 rows).

| Hip-hop | candidates | accepted | to review | other genre | with Spotify ID |
|---|---:|---:|---:|---:|---:|
| Sweden | 121 | 12 | 54 | 55 | 12 |
| Norway | 79 | 4 | 59 | 16 | 4 |
| Denmark | 95 | 16 | 55 | 24 | 16 |
| Finland | 136 | 19 | 64 | 53 | 19 |
| Canada | 125 | 30 | 65 | 30 | 29 |
| Australia | 36 | 5 | 22 | 9 | 5 |
| Netherlands | 61 | 24 | 28 | 9 | 20 |
| Belgium | 92 | 21 | 26 | 45 | 20 |
| Spain | 109 | 0 | 108 | 1 | 0 |
| Switzerland | 51 | 19 | 22 | 10 | 9 |

Why so many go to review: 506 have Wikidata hip-hop genres but no MusicBrainz votes (the registry rule asks for
votes before taking Wikidata's genres alone), 438 have only the occupation "rapper" and no genre, 251 have Deezer
filing 20-70% of releases as Rap/Hip Hop, 94 are Spanish-language (owner rule). Most of the first two have no Deezer
page linked anywhere, so even accepted they would have little to measure them by.

## 5. Results on the site (scored → scored + smaller acts listed)

Hip-hop: Sweden 15 → 25, Canada 24 → 49, Denmark 12 → 26, Finland 7 → 23, Norway 5 → 7, Netherlands 53 → 78, Russia
43 → 74, Poland 77 → 89, Italy 97 → 100, Switzerland 3 → 14, Australia 11 → 13, Belgium 11 (not listed: check too
weak), Spain 26 (all candidates in review). Countries with only smaller acts (Ghana, Bulgaria, Lithuania...) now appear
in the picker. 299 smaller hip-hop acts listed in all. Country music: Canada 45 → 48, Norway 0 → 1; Sweden,
Australia and the Netherlands none.

No country reaches 100 from this alone: the free sources that link a Spotify or Deezer page to a country (Wikidata,
MusicBrainz) hold only the better-documented smaller acts.

## 6. Per-country reliability (status on the page)

- **Shown, checked in the country** (own hold-out Spearman 0.4+ on 8+ artists): hip-hop Sweden 0.70, Canada 0.75,
  Netherlands 0.62, Denmark 0.44 (marginal), Poland 0.53, Russia 0.51, Turkey 0.71, Italy 0.69, Australia 0.80,
  Japan 0.83; country music Canada 0.91.
- **Shown on the overall figure** (fewer than 8 artists with listener counts to test there, said on the page):
  Finland, Norway, Switzerland, Austria, Israel, Iran and the other small markets.
- **Not shown** (tested and below 0.4): Belgium 0.33. Deezer is so large there (5 Spotify listeners per fan) and its
  track ranks so flat (0.10) that the sources do not order Belgian rappers.

## 7. What a Deezer-based ranking can and cannot claim

Can: that an act is larger or smaller than other smaller acts of the same country and genre, roughly (within a
factor of about 2 on average, much worse for a few, who are flagged); that its new songs are a large part of its top
tracks; that it charts at home.

Cannot: a listener count, a comparison with the Scout score or the top-100 list above it, an order among acts of
similar size (the 500k-1.5m test: 0.31), or completeness: acts with no Wikidata entry, or an entry without a Deezer
link, are missing, and Deezer-only finds have no country source at all.

## 8. Score of the smaller acts (grade C, provisional)

A percentile over all smaller acts of the genre: size estimate 40%, share of the Deezer top 10 released in the last
90 days 25%, home-country charts 15%, Wikipedia trend (last 3 months against the 3 before, 30+ views) 10%, Deezer fan
growth 10% (weekly snapshots in `data/deezer_fans_history.csv`, from the daily workflow on Mondays; growth needs two a
week or more apart). Needs the size estimate and one more signal.

## Data

`data/small_acts.csv` (2,784 + 404 rows, 820 KB), `data/small_acts_calibration.csv` (2,595 rows, 291 KB),
`data/musicbrainz_deezer_links.json` (870 MBIDs, 108 KB), `data/deezer_fans_history.csv` (first snapshot 2026-10-26, 397 acts, 10 KB; then weekly).
Site: `scout_countries.json` hip-hop 566 → 639 KB raw (119 → 140 KB gzip), country 88 → 91 KB; `scout.json` +2 KB.
Loaded only with the country view, as before.

## Terms

Deezer API (no key; used under the site's non-commercial status, credited, as elsewhere on the site), Wikidata (CC0),
Wikimedia pageviews API (free; it throttles: answers 429 with Retry-After 7 s, so views are read one at a time),
MusicBrainz (1 request a second, url relations CC0), ListenBrainz (CC0), kworb.net, Apple Music RSS, Shazam (badge
only, as decided K3).

## Update 2026-10-27 (owner's answers)

- Genre: for these candidates a Wikidata hip-hop genre or the occupation rapper is enough without MusicBrainz votes
  (`genre.decide_small`), with Latin, beatmaker, Deezer-contradiction and Spanish-language checks; country music
  likewise on a Wikidata country genre.
- Every country's list is shown with its confidence (a weak check is said plainly); past acts, single-source and
  unsized acts are listed and marked.
- Discovery widened to the Deezer related artists with no Wikidata item, Deezer's chart and editor playlists, the
  official national charts (`2026-10-27-national-charts.md`) and our Spotify, Apple Music and Shazam charts, the
  country always from Wikidata or MusicBrainz (url relations). Hip-hop candidates 2,784 → 5,023, listed smaller acts
  299 → 1,602; countries at 100: 6 → 10. Details and per-country counts: DECISIONS.md, 2026-10-27.
