// Rap Ledger content settings. Change what the pages show here; the logic is in app.js, the look in styles.css.

// Top-100 table columns per ranking: [label, key, format]. Formats: count | delta | share | money | int.
// "current": our ranking (current listeners, recent releases weighted up); "monthly": Spotify's monthly listeners.
export const COLUMNS = {
  current: [
    ["Current listeners", "cl", "count"],
    ["From recent releases", "cur_share", "share"],
    ["Monthly listeners", "ml", "count"],
    ["By listeners", "rank", "int"],
    ["Scout score", "scout", "int"],
    ["Spotify royalties / month", "gen_mid", "money"],
  ],
  monthly: [
    ["Monthly listeners", "ml", "count"],
    ["Today", "chg", "delta"],
    ["Spotify rank", "rank_all", "int"],
    ["Peak listeners", "peak_ml", "count"],
    ["Streams / day", "daily", "count"],
    ["Spotify royalties / month", "gen_mid", "money"],
  ],
};

// How many artists outside the top 100 the Rising page lists.
export const RISING_LIMIT = 50;

// Pay gap: what an artist keeps of the recording royalties under each deal type (low, mid, high share).
// Each row has its source; grade A = primary, B = reputable secondary, C = estimate.
export const DEALS = [
  { key: "major", name: "Major label royalty deal", low: 0.15, mid: 0.20, high: 0.30, grade: "A",
    note: "UK CMA: average major-label royalty rose from 19.7% (2012) to 23.3% (2021). Before recouping the advance.",
    src: "https://gov.uk/government/news/music-streaming-report-published" },
  { key: "small", name: "Small label / production deal", low: 0.30, mid: 0.40, high: 0.50, grade: "B",
    note: "Megan Thee Stallion v. 1501 (2020 court filing): the label took 60% of recording income.",
    src: "https://complex.com/music/2020/03/megan-thee-stallion-sues-her-record-label-1501-certified-entertainment" },
  { key: "jv", name: "Joint venture / profit split", low: 0.30, mid: 0.40, high: 0.50, grade: "B",
    note: "50/50 of net profit after costs is the convention; costs come off first.",
    src: "https://www.digitalmusicnews.com/?p=156325" },
  { key: "services", name: "Label services (e.g. AWAL Core)", low: 0.70, mid: 0.80, high: 0.85, grade: "A",
    note: "AWAL Core: the artist keeps 85% on a 30-day rolling term.",
    src: "https://help.awal.com/hc/en-us/articles/40137044024595-What-are-the-terms-of-the-standard-AWAL-agreement" },
  { key: "diy", name: "DIY distributor (e.g. UnitedMasters, DistroKid)", low: 0.90, mid: 1.00, high: 1.00, grade: "A",
    note: "UnitedMasters free tier: the artist keeps 90%; SELECT ($59.99 a year): 100%.",
    src: "https://untd.io/en/artists" },
];

// Platforms page: the per-artist columns [label, key, format]; "rev:<platform>" is yearly royalties (mid estimate).
export const PLATFORM_COLUMNS = [
  ["Spotify streams / day", "daily", "count"],
  ["YouTube views / day", "yt_daily", "count"],
  ["Deezer fans", "deezer_fans", "count"],
  ["Spotify", "rev:spotify", "money"],
  ["YouTube", "rev:youtube", "money"],
  ["Apple Music", "rev:apple_music", "money"],
  ["Amazon", "rev:amazon", "money"],
  ["All streaming", "rev:streaming", "money"],
];

// Plain-language definitions shown on hover (and to screen readers) on column headings that use our own terms.
export const GLOSSARY = {
  "Current listeners": "Monthly listeners, counting the listening that comes from recent releases. Old songs still streamed a lot count for little, so this shows who is drawing an audience with new music now.",
  "From recent releases": "Share of the artist's listening that comes from songs released in the last 18–36 months.",
  "Scout score": "0–100: momentum against artists of a similar size (new songs' pull, current share, engagement, chart reach and more). Breaking 80+, Rising 65+, Watch 50+.",
  "Spotify royalties / month": "What Spotify pays the rights holders (label or distributor) for the artist's own songs, mid estimate. Not the artist's pay.",
  "New-release pull": "Share of the artist's daily streams that come from songs out 90 days or less.",
  "Current share": "Share of listening on releases of the last 18–36 months.",
  "Wikipedia, 3 mo": "English Wikipedia page views of the last 3 months against the 9 before.",
  "Streams / listener": "Spotify streams a day per monthly listener: how often listeners come back.",
  "Chart countries": "Countries where a song is in Spotify's weekly top 200 or Apple Music's daily top 100.",
  "By listeners": "Rank among hip-hop artists by Spotify monthly listeners.",
  "Shazam": "Number of Shazam charts (world, 15 countries, 31 cities; last 7 days) the artist is on: people looking their songs up, often before streams follow. Not part of the score yet.",
};
