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
python -m src.site_build && python -m http.server -d site 8000   # then open http://localhost:8000
```

## Files

- `raw/`: original pages, gzipped, never changed; `raw/manifest.csv` holds their SHA-256 hashes.
- `data/spotify_listeners.csv`: daily monthly listeners, rank, daily change and peak for tracked artists.
- `data/spotify_streams.csv`: stream totals and daily streams per artist (total, as lead, solo, as feature).
- `data/musicbrainz.csv`, `data/wikidata.json`: cached lookups (MusicBrainz genre votes are internal only, CC BY-NC-SA).
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
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Keep it private with Cloudflare Access (Zero Trust → Access →
Applications → self-hosted, domain `rap-ledger.pages.dev`, allow the owner's email, one-time PIN), as for Hoop Ledger.
