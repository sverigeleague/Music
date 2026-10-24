# Rap Ledger (working name)

Monthly tracker of hip-hop artists' audiences and the economics behind them: who is listened to, who is rising, and
what that is worth to the artist under each kind of deal. Plan and phases: [ROADMAP.md](ROADMAP.md). Why each choice
was made: [DECISIONS.md](DECISIONS.md). Research with sources: `docs/research/`.

Status: **Phase 0 prototype, private.** Spotify top 100 hip-hop from free sources; money figures are estimates.

## Setup

```
pip install -r requirements.txt
python -m pytest -q
python -m src.run snapshot      # today's top 2,500 by monthly listeners (kworb.net)
python -m src.run registry      # hip-hop decision per artist -> registry/artists.csv, review/genre_review.csv
python -m src.run streams       # total and daily streams, lead vs feature (kworb.net artist pages)
python -m src.run deezer        # Deezer fans
python -m src.run photos        # Wikimedia Commons photos with credits
python -m src.run ytapi         # YouTube channel subscribers and views (needs the secret YOUTUBE_API_KEY)
python -m src.run countries     # weekly Spotify top 200 in 76 countries: where each artist's songs chart
python -m src.run dates         # first release dates of the songs behind each artist's streams (Deezer)
python -m src.run mbdates       # MusicBrainz first release dates for those songs (can run alongside)
python -m src.site_build && python -m http.server -d site 8000   # then open http://localhost:8000
```

## Files

- `raw/`: original pages, gzipped, never changed; `raw/manifest.csv` holds their SHA-256 hashes.
- `data/spotify_listeners.csv`: daily monthly listeners, rank, daily change and peak for tracked artists.
- `data/spotify_streams.csv`: stream totals and daily streams per artist (total, as lead, solo, as feature).
- `data/musicbrainz.csv`, `data/wikidata.json`: cached lookups (MusicBrainz genre votes are internal only, CC BY-NC-SA).
- `data/track_dates.csv`, `data/isrc_dates.csv`: song release dates (Deezer edition date and ISRC; MusicBrainz first
  release date by ISRC). They feed our ranking, current listeners (`src/current.py`).
- `registry/artists.csv`: one row per candidate artist: genre decision and its basis, platform IDs, labels, major.
- `registry/genre_overrides.csv`: the owner's genre decisions; they win over the rule.
- `registry/rates.csv`, `registry/deal_shares.csv`: payout rates and artist shares, each with grade and source.
- `review/genre_review.csv`: borderline and Latin artists waiting for the owner's decision.

## Genre review

Open `review/genre_review.csv`. For each artist you decide, add a row to `registry/genre_overrides.csv`:
`spotify_id,name,decision,note,decided_by,date` where decision is `hip_hop`, `latin` or `other`. The next registry
run applies it.

## Schedule (`.github/workflows/`, run from `main`)

- `daily` (09:17 UTC): the listeners snapshot, about 1 minute.
- `monthly` (2nd of the month): registry, streams, Deezer, photos, about 15 minutes.
- `site`: builds and deploys the site after each run when the Cloudflare secrets are set.
- `tests`: on pull requests and code changes to main.

## Website (`site/`)

Plain files, no build step, the same setup as Hoop Ledger: colours and spacing in `site/styles.css`, what the pages
show in `site/config.js`, the pages in `site/app.js`. Deploys to Cloudflare Pages project `rap-ledger` with the secrets
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Public at https://tventy.se/music (owner, 2026-10-24), served by the tventy.se router in the Public-Registry
repository (`worker/`); no Cloudflare Access application on rap-ledger.pages.dev, or the router cannot reach it.

## Secrets (GitHub → Settings → Secrets and variables → Actions)

- `YOUTUBE_API_KEY`: YouTube Data API v3 key. Google Cloud console → new project → APIs & Services → enable
  "YouTube Data API v3" → Credentials → Create credentials → API key; restrict it to that API. Free quota
  (10,000 units a day) is far more than the monthly run needs (about 4 units).
- `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`: website deploy (see Website).

## Review desk

Reviews are answered in chat: Claude posts numbered batches and applies the replies. The page below is optional.

Borderline genres and unplaced labels are settled on the claude.ai page "Rap Ledger Review Desk"
(https://claude.ai/artifact/EA2MZxZE9DuhYBCRYAskAF): tap an answer per artist. Claude exports the answers
(collections `genre` and `label`) to `review/decisions.json` and runs `python -m src.reviews` to write
`registry/genre_overrides.csv` and `registry/label_overrides.csv`. `python -m src.reviews queue <file>` rebuilds the
page's queue file from the two review lists.
