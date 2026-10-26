# Morning brief, 26 October 2026: the night's work on the music site

You asked for 12 hours of unattended work: optimise the site, research data sources, review it through an investment
banker's eyes, and build products. The sport site's repository is not connected to this session, so all of the work
was on the music site. Everything is on the branch `claude/music-roadmap`, in pull request #14, for you to merge. Each
change has an entry in DECISIONS.md.

**Interruption:** the session hit its usage limit at about 23:40 UTC. Work stopped until about 06:30 UTC, so roughly
5 of the 12 hours ran.

## What changed

- **Two fresh reviews through an investment banker's eyes**, 25 and 15 findings. Nearly all are fixed:
  - **Figures:**
    - one Spotify rate everywhere ($2.50–3.60 per 1,000; middle $3.00, Duetti 2024);
    - the same figure on every page (top-100 royalties, "label known", list sizes);
    - awards shown as a floor, not a total.
  - **Unsigned prospects:**
    - A prospect needs a current audience, a release in the last two years, under 10m listeners, and to be mostly a
      lead artist, not a guest.
    - 22 hip-hop prospects remain. Jeezy, BigXthaPlug, Meek Mill and the like are "established independents", with
      the evidence shown.
  - **Duplicates:** second Spotify profiles (Ye/Kanye, Makaveli/2Pac, Miyagi) are labelled and left out of totals.
    Bob/B.o.B was checked and is not a pair.
  - **Scout:**
    - A missing signal scores 0, not a middling value.
    - A tier needs 60% of the signals; below that the score is shown as provisional.
  - **Country pages:** share and card links fixed; the ranking has no gaps.
  - **Wording:** client wording throughout, with internal jargon and file paths removed.
- **New pages:**
  - catalog screener (Money);
  - artist one-pager to print or save as PDF;
  - label one-pager and roster CSV;
  - data quality and corrections log;
  - deal comparison with advance recoupment (worth page);
  - catalog age panel on artist pages;
  - filter views kept in the page address (send a colleague the exact view).
- **Speed and quality:**
  - The country start page is ready in 1.9 s, down from 3.6 s; Scout in 2.4 s, down from 3.5 s.
  - Photos are 40% smaller.
  - The accessibility scan is clean.
  - Search engines get better page data and a real 404 page.
  - A failed data load shows a retry message instead of a broken page.
  - Data checks now run in CI and before every deploy.
- **Data:**
  - Catalog value by the age of the songs.
  - YouTube matched through the artist's own channel. YouTube Data API wired in, waiting for its key.
  - ListenBrainz collected (a weak signal, kept internal).
  - The MLC (who publishes each song) built, waiting for an account.
  - 16 merged MusicBrainz IDs updated.
  - 18 label owners researched.
- **Research and ideas:**
  - `docs/research/2026-10-26-new-data-sources.md`: about 25 sources, ranked.
  - `docs/product/2026-10-26-ideas.md`: 24 ideas, ranked, also in ROADMAP Phase 11.

## What needs you (in order of value)

1. **Merge PR #14** once you have looked at the preview.
2. **YouTube Data API key**, as the GitHub secret `YOUTUBE_API_KEY` (steps in DECISIONS.md, "YouTube Data API set
   up"). It adds own-channel figures for about 680 hip-hop artists, against 255 from kworb today.
3. **The MLC account**, free per its terms: confirm there is no fee at sign-up. Add `MLC_USERNAME` and `MLC_PASSWORD`
   as GitHub secrets. It shows who publishes each hit song.
4. **Genre queue policy:** 306 artists waiting in genre review now have their identity confirmed and would qualify as
   hip-hop. Accepting them adds about a fifth of new names to the top 1,000. Evidence:
   `review/genre_identity_confirmed.csv`.
5. **Second profiles:** check `review/second_profiles.csv` (4 confirmed pairs).
6. **Public or not:**
   - the data-quality page shows the review backlog (736 genre, about 333 label);
   - the corrections rule (every correction logged in `registry/corrections.csv`).
7. **Licence first (ROADMAP 2.1)** for an embeddable widget or a public data API.
8. **Free keys you could request:**
   - setlist.fm (non-commercial use only);
   - Ticketmaster Discovery;
   - Last.fm, which needs written approval for public pages.

## Known limits

- The label research added 18 owners, not the 50–100 aimed for. Most release copyright lines name only the label or
  the artist, not a distributor.
- Values, royalties and deal outcomes remain estimates (grade C, shown as ranges).
- The deployed site updates only after the merge, through the site workflow.
