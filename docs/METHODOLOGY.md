# Current listeners: how our top 100 is ranked

Version 1.2, 24 October 2026. Code: `src/current.py` (weights), `src/collectors/release_dates.py` (dates). A change to
any number below is a new version, logged in `DECISIONS.md`.

## The idea

Spotify's monthly listeners count everyone who played an artist in the last 28 days. For established artists, much of
that comes from songs released years ago. Our ranking counts the part of an artist's audience that comes from
**recent releases**, so it shows who is drawing listeners with new music now.

## The formula

    current listeners = monthly listeners × current share

    current share = Σ (age weight × daily streams) / Σ daily streams      (over the artist's dated songs)

    age weight    = 1                              if the song is 18 months old or less
                  = 1 − (age in months − 18) / 18  between 18 and 36 months
                  = 0                              over 36 months

    a song where the artist is the featured guest counts at half its daily streams

| Song age | 6 months | 18 months | 24 months | 27 months | 30 months | 36+ months |
| --- | --- | --- | --- | --- | --- | --- |
| Weight | 1.00 | 1.00 | 0.67 | 0.50 | 0.33 | 0.00 |

A month is 30.44 days. Age runs from the song's first release date to the day the ranking is built.

## Why these choices

- **18 months:** the music industry's standard line between current and catalog music (Luminate and its predecessors
  report "current" and "catalog" on this line).
- **A taper to 36 months, not a cliff:** with a hard cutoff, an artist would fall sharply in the month their album
  turns 18 months old, though nothing about their audience changed that month.
- **Features at half weight:** on a guest verse, part of the audience is the lead artist's.
- **Monthly listeners × share, not streams:** the result stays in people, which is easy to compare and explain.
  Streams alone favour artists whose fans replay heavily, and are easier to inflate with fake plays.
- **Assumption:** listeners split between old and new songs in the same proportion as streams.

## Worked example

An artist has 20m monthly listeners and these daily streams:

| Song | Released | Age | Weight | Daily streams | Counted | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| New single | Sep 2026 | 2 months | 1.00 | 600,000 | 600,000 | 600,000 |
| 2024 album track | Jul 2024 | 27 months | 0.50 | 300,000 | 300,000 | 150,000 |
| 2015 hit | 2015 | 11 years | 0.00 | 900,000 | 900,000 | 0 |
| Guest verse | Jan 2026 | 9 months | 1.00 | 400,000 | 200,000 | 200,000 |
| **Total** | | | | | **2,000,000** | **950,000** |

Current share = 950,000 / 2,000,000 = 47.5%. Current listeners = 20m × 47.5% = **9.5m**.

## Release dates

- Songs dated: the artist's songs by daily streams, largest first, until 90% of their (weighted) daily streams are
  covered, at most 300 songs. Large catalogues need many: Drake's 90% takes 249 of his 500 songs.
- **Deezer:** search by artist and title. The match must have the same title, ignoring brackets and "feat."
  suffixes, and must credit the artist as lead or guest. The artist's own releases are checked before covers and
  "sped up" uploads. This gives the edition's release date and the recording's ISRC code.
- **MusicBrainz:** the ISRC gives the recording's first release date. This corrects re-releases: "God's Plan" is dated
  19 Jan 2018 (single), not 29 Jun 2018 (album); "Hotline Bling" 31 Jul 2015, not 2016.
- **Songs Deezer cannot match** (some albums are missing there): MusicBrainz recording search by title and artist
  gives the earliest first release date among matching recordings. Example: Kendrick Lamar's "Money Trees" is dated
  22 Oct 2012.
- **The earlier of the two dates is used.** A year-only date counts as 1 July of that year.
- **Undated songs** are left out of the share, never counted as new or old.

## When an artist is ranked

- **Ranked:** dated songs cover at least 80% of the artist's weighted daily streams.
- **Provisional rank:** coverage is 50-80%. The dated songs' current share stands in for the whole catalogue, and the
  site marks the rank provisional and shows the range the undated songs could move it. The low end treats every
  undated song as old (weight 0); the high end treats it as new (weight 1).
- **Below 50%:** the artist is listed as "not yet ranked".

## Revival

- **Definition:** a song older than 36 months whose daily streams are up by at least 50% on a snapshot 28 or more days
  earlier, and which makes up at least 2% of the artist's daily streams.
- **Effect:** it gets a "Revival" badge and stays out of current listeners.
- **When it starts:** from the second monthly refresh, when there is an earlier snapshot to compare with.

## Sources

- Monthly listeners, daily streams and the song list: kworb.net, which compiles Spotify's public counts.
- Release dates: Deezer API and MusicBrainz (CC0).
- Shown on the site: the ranking and each artist's share "from recent releases". The method page describes the
  approach in general terms; this document is the full reference.

## Change log

- 1.2 (2026-10-24): no weights changed. Artists with 50-80% of their streams dated get a provisional rank with a
  range, instead of no rank. Owner: "make the current listener ranking robust". The monthly run also dates songs in
  a second Deezer pass after MusicBrainz.
- 1.1 (2026-10-23): no ranking weights changed. Up to 300 songs dated per artist instead of 40, because the cap
  kept large catalogues under the 80% rule (Drake 50%, Kendrick Lamar 64%). Better title matching, and a
  MusicBrainz search for songs Deezer cannot match.
- 1.0 (2026-10-23): first version. Owner's choices: taper 18 → 36 months, features at half weight, Revival badge.
