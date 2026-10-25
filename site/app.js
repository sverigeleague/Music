// tventy music front end: reads site/data/index.json (built by src/site_build.py), no server.
// Pages: top 100, rising, artist, pay gap, method. What they show is set in config.js; the look in styles.css.
import { COLUMNS, RISING_LIMIT, DEALS, PLATFORM_COLUMNS, GLOSSARY } from "./config.js";
// a column heading with its plain-language definition on hover (config.js GLOSSARY)
const defn = label => GLOSSARY[label] ? ` title="${esc(GLOSSARY[label])}" class="def"` : "";

const app = document.getElementById("app");
const store = { data: null, rev: {} };
const ui = { sort: ["cl", -1], q: "", by: "current", size: 100 };

// ---------- helpers
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const initials = n => String(n || "").split(/[\s\-–]+/).filter(w => /^[\p{L}\d]/u.test(w)).slice(0, 2).map(w => w[0]).join("").toUpperCase();
// where the artist is from, as small flags after the name (up to two); the country name on hover and for screen readers
const flag = a => a?.cc?.length ? `<span class="flags" role="img" aria-label="${esc(a.country || "")}" title="${esc(a.country || "")}">${a.cc.slice(0, 2).map(c => `<img src="flags/${c}.svg" alt="" width="16" height="12" loading="lazy">`).join("")}</span>` : "";
const pic = (a, big) => a.photo
  ? `<img class="pic${big ? " big" : ""}" src="${esc(a.photo.file)}" alt="" width="${big ? 120 : 32}" height="${big ? 120 : 32}" ${big ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async" data-initials="${esc(initials(a.name))}">`
  : `<span class="pic none${big ? " big" : ""}" aria-hidden="true">${esc(initials(a.name))}</span>`;
function count(v) {
  if (v == null) return "–";
  const a = Math.abs(v);
  return a >= 1e12 ? (v / 1e12).toFixed(2) + "tn" : a >= 1e9 ? (v / 1e9).toFixed(2) + "bn" : a >= 1e6 ? (v / 1e6).toFixed(1) + "m" : a >= 1e3 ? (v / 1e3).toFixed(0) + "k" : String(v);
}
const usd = v => v == null || v === 0 ? "–"  // no estimate shows as a dash, never "$0"
  : (v < 0 ? "−$" : "$") + (Math.abs(v) < 10 ? Math.abs(v).toFixed(2) : count(Math.round(Math.abs(v))));
// countries with a song on Spotify's weekly top 200 or Apple Music's daily top 100, each counted once
// reach: the count in the index, until geo and apple arrive with extra.json
const chartCountries = a => !a.geo && !a.apple && a.reach != null ? a.reach : new Set([...(a.geo?.charts || []).map(c => c[0]), ...(a.apple?.countries || [])]).size;
const range = r => !r ? "–" : usd(r.low) === usd(r.high) ? usd(r.low) : `${usd(r.low)}–${usd(r.high)}`;  // one value when the ends meet
const delta = v => v == null ? "–" : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${v > 0 ? "+" : v < 0 ? "−" : ""}${count(Math.abs(v))}</span>`;
// one decimal; two below 1% (a daily move of +0.04%); a true minus sign, as the money figures
const pct = v => v == null ? "–" : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(Math.abs(v) < 1 ? 2 : 1)}%</span>`;
const cell = (a, [, key, f]) => {
  const v = key === "gen_mid" ? a.money?.generated.mid : key === "scout" ? a.scout?.score : a[key];
  if (key === "cl" && a.cl_provisional && v != null) return `${count(v)}<span class="prov" title="Provisional: 50–80% of streams dated; could be ${count(a.cl_range[0])}–${count(a.cl_range[1])}">*</span>`;
  if ((key === "ml" || key === "cl") && a.floor) return "under 500k";  // below kworb's listener floor (country)
  if (key === "cl" && v === 0) return `<span class="note" title="Almost none of the listening is on recent releases (the last 18–36 months): a catalog act">catalog only</span>`;
  if (key === "gen_mid" && v != null && a.feat > 0.9)  // nearly all streams as a featured guest: own songs earn little
    return `${v < 1000 ? "&lt;$1k" : usd(v)} <span class="chip" title="${Math.round(a.feat * 100)}% of this artist's streams come as a featured guest; the money counts their own songs only">own songs only</span>`;
  if (f === "money" && v != null && v > 0 && v < 1000) return "&lt;$1k";
  return f === "count" ? count(v) : f === "delta" ? delta(v) : f === "pct" ? pct(v) : f === "money" ? usd(v)
    : f === "share" ? (v == null ? "–" : Math.round(v * 100) + "%") : f === "int" ? (v ?? "–") : esc(v);
};
// below kworb's 500k-listener floor (country) there is no listener figure: those artists rank by daily streams
const mlx = a => a.floor ? "under 500k" : count(a.ml);
const chip = (t, title) => `<span class="chip" title="${esc(title || "")}">${esc(t)}</span>`;
const grade = g => `<span class="chip c" title="A primary, B reputable secondary, C our estimate">${esc(g)}</span>`;
// Four sections in the header (owner, 2026-10-24, D1); each page belongs to one, and sections with several pages
// show a sub-menu. Method sits in the footer.
const SECTION = { top: "artists", movers: "artists", month: "artists", rising: "artists", compare: "artists", artist: "artists",
  scout: "scout", unsigned: "scout", producers: "scout",
  worth: "money", pay: "money", platforms: "money", tours: "money",
  labels: "labels", label: "labels", audience: "labels",
  method: "about", changelog: "about", quality: "about", glossary: "about", press: "about" };  // the footer's pages
const SUBNAV = {
  artists: [["top", "#/", "Top list"], ["movers", "#/movers", "Movers"], ["compare", "#/compare", "Compare"]],
  scout: [["scout", "#/scout", "Scout list"], ["unsigned", "#/unsigned", "Unsigned vs signed peers"], ["producers", "#/producers", "Producers"]],
  money: [["worth", "#/worth", "What is it worth?"], ["pay", "#/pay", "Pay gap by deal"], ["platforms", "#/platforms", "Platforms"], ["tours", "#/tours", "Tours"]],
  labels: [["labels", "#/labels", "Labels and market share"], ["audience", "#/audience", "Where it is streamed"]],
  about: [["method", "#/method", "Method"], ["changelog", "#/changelog", "Method changelog"], ["quality", "#/quality", "Data quality"], ["glossary", "#/glossary", "Glossary"], ["press", "#/press", "Press"]],
};
// Movers: today (daily change, outside the top 100) and the last 30 days, one page with a switch
const moversSwitch = on => `<div class="seg" role="group" aria-label="Period" style="margin:10px 0 4px"><a class="segbtn" href="#/movers/today"${on === "today" ? ' aria-current="page"' : ""}>Today</a><a class="segbtn" href="#/movers"${on === "month" ? ' aria-current="page"' : ""}>Past month</a></div>`;
let pageId = "top";
const nav = id => (pageId = id, document.querySelectorAll("[id^=nav-]").forEach(a => a.id === "nav-" + SECTION[id] ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
const subnav = (id = pageId) => { const sub = SUBNAV[SECTION[id]]; return sub ? `<nav class="subnav" aria-label="Pages">${sub.map(([k, h, l]) => `<a href="${h}"${k === id ? ' aria-current="page"' : ""}>${esc(l)}</a>`).join("")}</nav>` : ""; };

// Breadcrumbs under the header, as on tventy sport: Home / section / page; empty on the start page.
const crumbs = parts => { document.getElementById("crumbs").innerHTML = parts.length ? [["Home", "#/"], ...parts].map(([t, h]) => h ? `<a href="${h}">${esc(t)}</a>` : `<span>${esc(t)}</span>`).join(" &nbsp;/&nbsp; ") : ""; };

// Search, in the header and on the start page: artists by name, then labels; arrows and Enter work, "/" focuses it.
const fold = s => String(s || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
function searchFor(q) {
  const t = fold(q).trim();
  if (!t || !store.data) return [];
  const score = n => { const f = fold(n); return f === t ? 0 : f.startsWith(t) ? 1 : f.includes(" " + t) ? 2 : f.includes(t) ? 3 : 9; };
  const A = store.data.artists.map(a => [score(a.name), a]).filter(x => x[0] < 9).sort((x, y) => x[0] - y[0] || y[1].ml - x[1].ml).slice(0, 8)
    .map(([, a]) => ({ href: `#/a/${a.id}`, icon: pic(a), t: a.name, flag: flag(a), sub: `#${a.rank} by ${a.floor ? "streams" : "monthly listeners"} · ${mlx(a)} monthly listeners${a.label_name ? " · " + a.label_name : ""}` }));
  // the other genre's artists and labels too (its list loads on the first search), marked and linking to its own pages
  const og = GENRE === "hip_hop" ? "country" : "hip_hop", od = otherGenre(og), ogP = og === "hip_hop" ? "#/" : "#/" + og + "/", ogW = og === "hip_hop" ? "Hip-hop" : "Country";
  const labs = [...(store.data.labels || []).map(x => ({ x })), ...(od?.labels || []).filter(x => !(store.data.labels || []).some(y => y.name === x.name)).map(x => ({ x, other: true }))];
  // owners ("universal" finds Universal Music Group): the Labels directory filtered to that owner's labels
  const owners = [...new Set((store.data.labels || []).map(x => x.parent).filter(Boolean))].map(p => [score(p), p]).filter(x => x[0] < 9).sort((x, y) => x[0] - y[0]).slice(0, 2)
    .map(([, p]) => { const n = (store.data.labels || []).filter(x => x.parent === p); return { href: `#/labels/owner/${encodeURIComponent(p)}`, icon: logo(p), t: p, sub: `Label owner · ${n.length} label${n.length === 1 ? "" : "s"}, ${new Set(n.flatMap(x => x.artists)).size} artists in our list` }; });
  const L = labs.map(o => [score(o.x.name), o]).filter(x => x[0] < 9).sort((x, y) => x[0] - y[0] || !!x[1].other - !!y[1].other || y[1].x.ml - x[1].x.ml).slice(0, 4)
    .map(([, { x, other }]) => ({ href: `${other ? ogP : "#/"}label/${x.slug}`, genre: other ? og : undefined, icon: logo(x.name), t: x.name, sub: `${other ? ogW + " · " : ""}Label · ${x.artists.length} artist${x.artists.length === 1 ? "" : "s"} in our list` }));
  const O = od ? od.artists.map(a => [score(a.name), a]).filter(x => x[0] < 2).sort((x, y) => x[0] - y[0] || y[1].ml - x[1].ml).slice(0, 3)
    .map(([, a]) => ({ href: `${og === "hip_hop" ? "#/" : "#/" + og + "/"}a/${a.id}`, genre: og, icon: pic(a), t: a.name, flag: flag(a),
      sub: `${og === "hip_hop" ? "Hip-hop" : "Country"} · #${a.rank} by ${a.floor ? "streams" : "monthly listeners"} · ${mlx(a)} monthly listeners` })) : [];
  return [...A, ...O, ...owners, ...L];
}
function loadGenre(g) {
  if (genreStore[g]) return Promise.resolve(genreStore[g].data);
  return fetch(g === "hip_hop" ? "data/index.json" : `data/${g}/index.json`).then(r => r.ok ? r.json() : null)
    .then(d => { if (d && !genreStore[g]) genreStore[g] = { data: d }; return genreStore[g]?.data || null; }).catch(() => null);
}
let otherLoading = false;
function otherGenre(g) {
  if (genreStore[g]) return genreStore[g].data;
  if (!otherLoading) {
    otherLoading = true;
    fetch(g === "hip_hop" ? "data/index.json" : `data/${g}/index.json`).then(r => r.ok ? r.json() : null)
      .then(d => { if (d) genreStore[g] = { data: d }; document.querySelectorAll("input[type=search]").forEach(i => i === document.activeElement && i.dispatchEvent(new Event("input")));
        if (d && pageId === "labels" && !app.contains(document.activeElement)) labelsPage(); })  // its tile compares with the other genre: drawn the same on a slow connection
      .catch(() => {}).finally(() => { otherLoading = false; });
  }
  return null;
}
function bindSearchBox(input, box, global) {
  let hits = [], at = 0;
  input.setAttribute("role", "combobox"); input.setAttribute("aria-autocomplete", "list");  // aria-expanded is valid on a combobox, not a search box
  const close = () => { box.hidden = true; input.setAttribute("aria-expanded", "false"); };
  const draw = () => {
    hits = searchFor(input.value); at = 0;
    if (!input.value.trim()) return close();
    box.innerHTML = hits.length ? hits.map((x, i) => `<a role="option" href="${x.href}"${x.genre ? ` data-genre-link="${x.genre}"` : ""} aria-selected="${i === at}">${x.icon}<span>${esc(x.t)}${x.flag || ""}<small>${esc(x.sub)}</small></span></a>`).join("")
      : `<p class="note" style="padding:10px 12px;margin:0">No match. Try an artist or a label.</p>`;
    box.hidden = false; input.setAttribute("aria-expanded", "true");
  };
  const mark = () => box.querySelectorAll("a").forEach((a, i) => a.setAttribute("aria-selected", i === at));
  input.addEventListener("input", draw);
  input.addEventListener("focus", () => input.value && draw());
  input.addEventListener("keydown", ev => {
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") { ev.preventDefault(); at = (at + (ev.key === "ArrowDown" ? 1 : -1) + hits.length) % Math.max(1, hits.length); mark(); }
    else if (ev.key === "Enter" && hits[at]) { hits[at].genre ? (location.hash = hits[at].href) : go(hits[at].href); input.value = ""; close(); input.blur(); }
    else if (ev.key === "Escape") { close(); input.blur(); }
  });
  box.addEventListener("click", ev => { if (ev.target.closest("a")) { input.value = ""; close(); } });
  if (!global) return;
  document.addEventListener("click", ev => { if (!ev.target.closest(".search")) { close(); app.querySelectorAll(".results").forEach(b => (b.hidden = true)); } });
  document.addEventListener("keydown", ev => { if (ev.key === "/" && !/input|select|textarea/i.test(document.activeElement.tagName)) { ev.preventDefault(); input.focus(); } });
}

// ---------- genres (owner, 2026-10-24, C3): hip-hop at #/..., country at #/country/..., each with its own data
// (data/ and data/country/). Page copy is written for hip-hop; on country pages the word is swapped in the rendered
// text, and links inside the pages stay on the country side.
let GENRE = "hip_hop";
const DATA_DIR = () => GENRE === "hip_hop" ? "data/" : `data/${GENRE}/`;
const PREFIX = () => GENRE === "hip_hop" ? "#/" : `#/${GENRE}/`;
const GDIR = () => GENRE === "hip_hop" ? "" : `${GENRE}/`;  // the genre's folder of static pages and share cards
const genreStore = {};
function swapWords(root) {
  if (GENRE !== "country" || !root) return;
  // quoted text (the Wikipedia descriptions, CC BY-SA) is never rewritten: "country, Americana, and hip-hop" stays
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT,
    { acceptNode: n => n.parentElement?.closest(".about, [data-noswap]") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  for (let n = w.nextNode(); n; n = w.nextNode())
    if (/hip[- ]hop|1,000/i.test(n.nodeValue)) n.nodeValue = n.nodeValue.replace(/hip-hop (or|and) rap/g, "country")
      .replace(/Hip-Hop|Hip-hop/g, "Country").replace(/hip-hop|hip hop/g, "country")
      .replace(/\b(top|Top|the) 1,000\b/g, `$1 ${measured()}`);  // the country list is smaller than hip-hop's
}
// "How this ranking works" (owner, 2026-10-25): each ranked page lists the metrics it uses, what each measures and its
// weight, under the page's introduction; Method keeps the full detail. Rows: [metric, what it measures, weight].
const FLOOR_ROW = () => GENRE === "country" ? [["Below 500k monthly listeners", "Spotify publishes no listener count there: those artists follow, ranked by streams a day (kworb), then in Deezer's order (grade C)", "order only"]] : [];
const HOW = {
  top: () => ui.by === "monthly"
    ? [["Monthly listeners", "people who played the artist on Spotify in the last 28 days (Spotify's public count, via kworb.net, daily)", "100%"], ...FLOOR_ROW()]
    : [["Current listeners", "monthly listeners × current share: the audience for what the artist is putting out now", "100%"],
       ["Monthly listeners", "people who played the artist on Spotify in the last 28 days (Spotify's public count, via kworb.net)", "input"],
       ["Current share", "the share of the artist's streams that come from recent releases; older songs fade out of it as they age, featured songs count half", "input"], ...FLOOR_ROW()],
  movers: () => location.hash.includes("today") || location.hash.includes("rising")
    ? [["Change in monthly listeners today", "the day's gain in Spotify monthly listeners, in percent, among artists outside the top 100", "100%"]]
    : [["Change in monthly listeners, about a month", "monthly listeners now against the snapshot nearest 30 days earlier (the Days column gives each artist's window), in percent", "100%"]],
  scout: () => [...Object.entries(store.data.scout_factors || {}).map(([k, x]) => [x.label.split(":")[0], SCOUT_INFO[k] || x.label, `${Math.round(x.weight * 100)}%`]),
    ["How they combine", "each signal becomes a percentile among artists of similar size; missing signals are left out and the other weights scaled up to 100%", ""],
    ["Tiers", TIER_RULE(), ""]],
  unsigned: () => [["Current listeners", "monthly listeners × the share of streams on recent releases (as the top list)", "ranks the list"],
    ["Monthly listeners", "Spotify's public count, where current listeners are equal", "breaks ties"],
    ["Peers", "the 5 active signed artists (at least 20% of listening on recent releases) closest in size (0.6–1.67× the monthly listeners, else 0.4–2.5×) and in share on recent releases", "the comparison"]],
  producers: () => [["Streams a day on credited songs", "daily Spotify streams of each artist's 3 biggest songs, credited to every producer or writer MusicBrainz lists on them", "100%"]],
  labels: () => [["Monthly listeners", "the sum over the label's artists in the list (recent releases decide an artist's label)", "100%"]],
  tours: () => [["Reported gross", "box office reported to Billboard Boxscore or Pollstar (grade A or B)", "100%"]],
};
// one tier sentence for the How box, the Scout panel and Method (src/insights.py TIERS, BREAKING_FRESH/ATTENTION)
const TIER_RULE = () => "Breaking: score 80+ and either new songs pulling 25%+ of daily streams or Wikipedia attention up 30%+; Rising: 65+ (including 80+ without that test); Watch: 50–64; artists with 15m+ monthly listeners are established and get no tier; a score resting on under 60% of the factor weight is provisional and gets no tier. A signal measured as absent (no chart entry, no song out in 90 days, not on US radio) scores 0";
const SCOUT_INFO = {
  velocity: "share of the artist's daily streams from songs out 90 days or less",
  growth: "monthly listeners now against 90 days ago (where history exists)",
  current: "share of listening on recent releases",
  attention: "English Wikipedia page views, the last 3 months against the 9 before",
  engagement: "streams a day per monthly listener: how hard the audience listens",
  breadth: "countries where a song is in Spotify's weekly top 200 or Apple Music's daily top 100",
  momentum: "today's change in monthly listeners",
  radio: "US AM/FM airplay audience of the artist's songs this week",
};
function addHow() {
  const app = document.getElementById("app"), rows = HOW[pageId] && HOW[pageId]();
  if (!rows || !rows.length || app.querySelector(".how") || /\/label\//.test(location.hash)) return;  // not on one label's page
  const sec = [...app.querySelectorAll("section")].find(x => x.querySelector(":scope > h1") && !x.classList.contains("hero"));
  if (!sec) return;
  const at = [...sec.querySelectorAll(":scope > p.sub")].pop() || sec.querySelector(":scope > h1");
  // open on wide screens; on phones it starts closed so the tiles and the table come first
  const wide = matchMedia("(min-width: 721px)").matches, role = rows.some(r => /%$/.test(r[2])) ? "Weight" : "Role";
  at.insertAdjacentHTML("afterend", `<details class="how"${wide ? " open" : ""}><summary>How this ranking works</summary><table class="stack"><thead><tr><th class="l">Metric</th><th class="l">What it measures</th><th>${role}</th></tr></thead><tbody>${rows.map(([m, d, w]) => `<tr><td class="l"><b>${esc(m)}</b></td><td class="l wrap">${esc(d)}</td><td>${esc(w)}</td></tr>`).join("")}</tbody></table><p class="note">Full detail and sources: <a href="${PREFIX()}method">Method</a> · every term defined: <a href="${PREFIX()}glossary">Glossary</a>.</p></details>`);
}

// the country list's size: artists with full data (above Spotify's public 500k floor, and below it those identified
// and ranked by streams or Deezer's order); the names-only places after them are not counted
const measured = () => (store.data?.artists?.length || 1000).toLocaleString();
// country pages: write the genre prefix into every in-site link, so a link opened in a new tab, copied or followed by
// a search engine leads to the country page too (the click handler below only covers plain clicks)
function prefixLinks(root) {
  if (GENRE === "hip_hop" || !root) return;
  root.querySelectorAll('a[href^="#/"]').forEach(a => {
    const h = a.getAttribute("href");
    if (!h.startsWith(PREFIX()) && !a.dataset.genre && !a.dataset.genreLink) a.setAttribute("href", PREFIX() + h.slice(2));
  });
}
new MutationObserver(() => { addHow(); prefixLinks(document.getElementById("app")); prefixLinks(document.getElementById("crumbs")); swapWords(document.getElementById("app")); swapWords(document.getElementById("crumbs")); stackify(document.getElementById("app")); keyboardTables(document.getElementById("app")); })
  .observe(document.getElementById("app"), { childList: true, subtree: true });
const go = hash => { location.hash = GENRE !== "hip_hop" && hash.startsWith("#/") && !hash.startsWith(PREFIX()) ? PREFIX() + hash.slice(2) : hash; };
document.addEventListener("click", e => {
  const a = e.target.closest('a[href^="#/"]');
  if (!a || GENRE === "hip_hop" || a.dataset.genre || a.dataset.genreLink || e.defaultPrevented || e.metaKey || e.ctrlKey) return;
  const href = a.getAttribute("href");
  if (href.startsWith(PREFIX())) return;
  e.preventDefault();
  go(href);
});

// ---------- loading and errors (2026-10-25): a failed or broken data file shows a message and a retry, never a
// blank or stale page; an unknown address says so instead of showing the start page
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
function loadFailed(e) {
  console.error(e);
  nav("error"); crumbs([]);
  app.innerHTML = `<section class="panel" role="alert"><h1>The data did not load</h1><p>${navigator.onLine === false ? "You appear to be offline." : "The connection failed or timed out."} Check your connection and try again.</p><p><button type="button" class="btn" id="retry">Try again</button></p><p class="note">Detail: ${esc(e?.message || e)}</p></section>`;
  app.querySelector("#retry").onclick = () => { app.innerHTML = `<p class="note">Loading…</p>`; route().catch(loadFailed); };
}
function notFound() {
  nav("notfound"); crumbs([["Page not found"]]); setMeta("Page not found");
  app.innerHTML = `<section class="panel"><h1>Page not found</h1><p>There is no page at this address. It may have moved, or the link may be mistyped.</p><p><a href="#/">Go to the top list</a> · <a href="#/scout">Scout</a> · <a href="#/labels">Labels</a></p></section>`;
}
// Skip link (index.html, static pages): moves focus to the page content without changing the hash route
document.addEventListener("click", e => { if (e.target.closest?.("a.skip")) { e.preventDefault(); app.focus(); } });
// Sortable column headings: reachable by Tab and sorted by Enter or Space, with focus kept on the same heading
document.addEventListener("keydown", e => {
  const th = e.target.closest?.("th[tabindex]");
  if (!th || (e.key !== "Enter" && e.key !== " ")) return;
  e.preventDefault();
  const attr = [...th.attributes].find(x => /^data-\w*s(c|or)/.test(x.name));
  th.click();
  const again = attr && app.querySelector(`th[${attr.name}="${CSS.escape(attr.value)}"]`);
  if (again) { again.tabIndex = 0; again.focus(); }
});
function keyboardTables(root) {
  root.querySelectorAll("thead th").forEach(th => { if (th.onclick && !th.hasAttribute("tabindex")) th.tabIndex = 0; });
  // wide tables scroll sideways inside their box: keyboard users can focus the box to scroll it
  const used = new Set([...root.querySelectorAll(".tablebox[aria-label]")].map(b => b.getAttribute("aria-label")));
  root.querySelectorAll(".tablebox:not([tabindex])").forEach(b => { if (b.scrollWidth > b.clientWidth + 1) {
    const name = (b.previousElementSibling?.matches("h2, h3") ? b.previousElementSibling : b.closest("section, .panel")?.querySelector("h1, h2"))?.textContent?.trim().slice(0, 80) || "Table";
    let label = name; for (let i = 2; used.has(label); i++) label = `${name} (table ${i})`;  // each region needs its own name
    used.add(label); b.tabIndex = 0; b.setAttribute("role", "region"); b.setAttribute("aria-label", label); } });
}

// Per-artist detail lives in 32 shard files (src/site_build.py): <data>/a/<second character's code % 32>.json.
const shards = {};
async function detailOf(id) {
  const n = id.charCodeAt(1) % 32;  // the second character: Spotify IDs all start with 0-7
  const key = GENRE + n;
  // a failed shard is not kept and is thrown, so the page shows the load error and its retry (not an artist with no money)
  shards[key] = shards[key] || await getJSON(`${DATA_DIR()}a/${n}.json`);
  return shards[key][id] || { lines: [], deals: [], artist: {}, artist_total: null };
}

// A photo that fails to load (a copy of the site without every photo) falls back to the artist's initials.
document.addEventListener("error", e => {
  const img = e.target;
  if (img.tagName !== "IMG" || !img.classList.contains("pic")) return;
  const span = document.createElement("span");
  span.className = img.className + " none";
  span.setAttribute("aria-hidden", "true");
  span.textContent = img.dataset.initials || "";
  img.replaceWith(span);
}, true);

// ---------- pages
function table(rows, rankKey = "rank") {
  const COLS = COLUMNS[ui.by];
  const [k, dir] = ui.sort;
  const val = a => k === "gen_mid" ? a.money?.generated.mid : k === "scout" ? a.scout?.score : a[k];
  const sorted = [...rows].sort((a, b) => ((val(a) ?? -Infinity) > (val(b) ?? -Infinity) ? 1 : -1) * dir);
  const head = COLS.map(c => `<th data-sort="${c[1]}"${c[1] === k ? ` aria-sort="${dir < 0 ? "descending" : "ascending"}"` : ""}><span${defn(c[0])}>${esc(c[0])}</span></th>`).join("");
  // a 1,000-row table takes 1–2 s to lay out on a mid-range phone: the first 200 rows, the rest on request
  const cut = !ui.allRows && sorted.length > 250, more = cut ? `<p class="more"><button type="button" class="btn" data-allrows>Show all ${sorted.length.toLocaleString()} rows</button></p>` : "";
  const body = (cut ? sorted.slice(0, 200) : sorted).map(a => `<tr><td class="l">${a[rankKey]}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a>${a.feat >= 0.9 ? `<div class="note guest" title="${Math.round(a.feat * 100)}% of this artist's Spotify streams today come as a featured guest on other artists' songs; the ranking counts them as for any artist">mostly as a featured guest</div>` : ""}</td>${COLS.map(c => `<td>${cell(a, c)}</td>`).join("")}
    <td class="l">${a.label_status === "major" || a.label_status === "major_distributed" ? esc(a.label_owner || "Major") : a.label_status === "independent" ? "Independent label" : a.label_status === "self_released" ? statusWordHtml(a) : a.label_status === "catalog" ? `<span title="No release in the last two years">Catalog</span>` : (a.major ? esc(a.major) : `<span class="note">not yet classified</span>`)}${a.revivals?.length ? " " + chip("Revival", a.revivals.map(r => `${r.title} (${r.year})`).join(", ")) : ""}</td></tr>`).join("");
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th>${head}<th class="l">Label group</th></tr></thead><tbody>${body}</tbody></table></div>${more}`;
}
function bindSort(rerender) {
  app.querySelectorAll("th[data-sort]").forEach(th => th.onclick = () => {
    ui.sort = [th.dataset.sort, ui.sort[0] === th.dataset.sort ? -ui.sort[1] : -1]; rerender();
  });
}

// The list in view: the top 100 or top 1,000 (ui.size), by our ranking or by monthly listeners (ui.by).
function top100() {
  const all = store.data.artists, n = ui.size;
  if (ui.by === "monthly") return all.slice(0, n).map(a => ({ ...a, pos: a.rank }));
  const ranked = all.filter(a => a.cl_rank && a.cl_rank <= n).sort((a, b) => a.cl_rank - b.cl_rank).map(a => ({ ...a, pos: a.cl_rank }));
  // below the 500k floor (country) there is no listener figure to rank by: those artists follow at their list place
  // numbered on from the last ranked place, so artists not yet ranked (no release dates) leave no gap
  const last = ranked.length ? ranked[ranked.length - 1].pos : 0;
  const floor = all.filter(a => a.floor && a.rank <= n).sort((a, b) => a.rank - b.rank).map((a, i) => ({ ...a, pos: last + i + 1 }));
  return ranked.concat(floor);
}
const sizeSwitch = rerender => `<div class="seg" role="group" aria-label="List size" style="margin-top:12px"><button type="button" data-size="100" aria-pressed="${ui.size === 100}">Top 100</button><button type="button" data-size="1000" aria-pressed="${ui.size === 1000}">Top 1,000</button></div>`;
const bindSize = rerender => app.querySelectorAll("[data-size]").forEach(b => b.onclick = () => { ui.size = +b.dataset.size; rerender(); });
function top() {
  nav("top");
  const d = store.data, all = d.artists, hundred = top100();
  const list = hundred.filter(a => a.name.toLowerCase().includes(ui.q));
  const N = ui.size === 1000 ? "1,000" : "100";
  const ml = hundred.reduce((s, a) => s + (a.second_of ? 0 : a.ml || 0), 0), measuredN = hundred.filter(a => a.ml != null).length;
  const gen = hundred.reduce((s, a) => s + (a.money?.generated.mid || 0), 0);
  const up = [...hundred].sort((a, b) => (b.chg_pct ?? -1e9) - (a.chg_pct ?? -1e9))[0];
  const majors = hundred.filter(a => a.label_status === "major" || a.label_status === "major_distributed").length;
  const nFloor = all.filter(a => a.floor).length;
  const unranked = all.filter(a => a.cl == null && !a.floor);  // missing release dates; below the floor is another case
  const sub = ui.by === "current"
    ? `Ranked by current listeners: each artist's monthly listeners, counting the listening that comes from recent releases, so songs from years ago that are still streamed a lot do not decide the order. ${esc(d.as_of)}.`
    : `Ranked by Spotify monthly listeners, ${esc(d.as_of)}.`;
  const scoutTop = all.filter(x => x.scout?.tier === "Breaking").sort((x, y) => y.scout.score - x.scout.score).slice(0, 3);
  const labelsN = (d.labels || []).length, total = all.reduce((s, a) => s + (a.second_of ? 0 : a.ml || 0), 0);  // second Spotify profiles left out
  app.innerHTML = `<section class="hero"><h1>Global Hip-Hop</h1>
      <p class="lede">Who is really drawing an audience in hip-hop right now, what their music earns, who owns it, and who is about to break. ${all.length.toLocaleString()} artists, updated daily, every figure sourced. <a href="#/state">This month in numbers →</a></p>
      <div class="stats"><div><b>${all.length.toLocaleString()}</b><span>hip-hop artists tracked${nFloor ? `: ${(all.length - nFloor).toLocaleString()} of Spotify's top ${d.universe.toLocaleString()}, ${nFloor.toLocaleString()} below its 500k floor` : `, of Spotify's top ${d.universe.toLocaleString()}`}</span></div><div><b>${count(total)}</b><span>monthly listeners, summed across artists (a fan of two artists counts twice; second Spotify profiles of the same artist left out)</span></div><div><b>${labelsN}</b><span>labels with artists in the top 1,000</span></div><div><b>${esc(d.as_of)}</b><span>listener data as of</span></div></div></section>
    ${pulse()}
    <section class="doors">
      <a class="door" href="#/worth"><span class="k">For artists</span><b>What is your music worth?</b><span>Royalties, what you keep under each deal, and what the catalog would sell for.</span></a>
      <a class="door" href="#/scout"><span class="k">For labels</span><b>Find who is rising</b><span>${scoutTop.length ? `Breaking now: ${scoutTop.map(x => esc(x.name)).join(", ")}.` : "Momentum scores for the top 1,000."} Filter to unsigned artists and export.</span></a>
      <a class="door" href="#/labels"><span class="k">Market</span><b>Who owns hip-hop</b><span>The majors' and independents' share of the top 1,000, by size.</span></a>
    </section>
    
    ${subnav()}<section><h1>Top ${N} hip-hop artists on Spotify</h1>
    <p class="sub">${sub} ${hundred.length < +N.replace(",", "") ? `${hundred.length.toLocaleString()} artists are ranked in this view; the others lack release dates (listed under the table). ` : ""}We track the ${(all.length - nFloor).toLocaleString()} biggest hip-hop and rap artists among Spotify's top ${d.universe.toLocaleString()} by monthly listeners${nFloor ? `; ${nFloor.toLocaleString()} more below its 500k-listener floor follow` : ""}.</p>
    <div class="seg" role="group" aria-label="Ranking" style="margin-top:12px"><button type="button" data-by="current" aria-pressed="${ui.by === "current"}">Our ranking: current listeners</button><button type="button" data-by="monthly" aria-pressed="${ui.by === "monthly"}">Monthly listeners</button></div> ${sizeSwitch()}</section>
    <section class="tiles">
      <div class="tile"><div class="k">Monthly listeners, summed</div><div class="v">${count(ml)}</div><div class="s">across the ${measuredN === hundred.length ? hundred.length.toLocaleString() : measuredN.toLocaleString() + " with a measured count"} in this list; a fan of two artists counts twice</div></div>
      <div class="tile"><div class="k">Spotify royalties / month</div><div class="v">${usd(gen)}</div><div class="s">Spotify recordings, top ${N}, mid estimate ${grade("C")}</div></div>
      <div class="tile"><div class="k">Biggest riser today in this top ${N}</div><div class="v">${up ? esc(up.name) : "–"}</div><div class="s">${up ? pct(up.chg_pct) + " listeners" : ""}</div></div>
      <div class="tile"><div class="k">On a major label</div><div class="v">${majors.toLocaleString()} of ${hundred.length.toLocaleString()}</div><div class="s">from the labels on their recent releases</div></div>
    </section>
    <section><div class="toolbar"><input type="search" placeholder="Filter this list" value="${esc(ui.q)}" aria-label="Filter this list"></div>
      ${table(list, "pos")}<p class="note">${ui.by === "current" ? "* Provisional rank: 50–80% of the artist's streams are on dated songs; hover for the range. " : ""}Spotify royalties are what Spotify alone pays the rights holders each month for the artist's own tracks (label or distributor), not the artist's pay. See the artist page and Pay gap.${ui.by === "current" && unranked.length ? ` Not yet ranked, because release dates are missing for too much of their listening: ${unranked.map(a => esc(a.name)).join(", ")}.` : ""}</p></section>`;
  if (d.below_floor?.length && ui.size === 1000) {
    app.insertAdjacentHTML("beforeend", belowFloor(d.below_floor, ui.by === "current" && hundred.length ? hundred[hundred.length - 1].pos : all.length));  // numbered on from the table's last place
    app.querySelector("#floorall")?.addEventListener("click", () => { ui.floorAll = true; top(); });
  }
  app.querySelectorAll("[data-by]").forEach(b => b.onclick = () => { ui.by = b.dataset.by; ui.sort = [ui.by === "current" ? "cl" : "ml", -1]; top(); });
  bindSize(top);
  const inp = app.querySelector("input");
  inp.oninput = () => { ui.q = inp.value.toLowerCase(); const p = inp.selectionStart; top(); const i = app.querySelector("input"); i.focus(); i.setSelectionRange(p, p); };
  bindSort(top);
  app.querySelector("[data-allrows]")?.addEventListener("click", () => { ui.allRows = true; const y = scrollY; top(); scrollTo(0, y); });
}

// Country ranks past the measured list (owner C1): artists under kworb's 500k-listener floor, in Deezer's track
// popularity order. An order, not a size: no listener figure exists for them.
function belowFloor(rows, measured) {
  return `<section class="panel" id="below"><h2 data-noswap>Places ${(measured + 1).toLocaleString()}–${(measured + rows.length).toLocaleString()}:further artists below the 500k line, in Deezer's order ${grade("C")}</h2>
    <p class="note">Spotify's public listener counts stop at about 500,000 monthly listeners, so these artists have no measured audience here. They are listed in the order of their songs' popularity on Deezer, a rough guide only: it can misplace artists of a similar size, and newer US acts are under-represented on Deezer. Only artists with a release in the last three years.</p>
    <ol class="floorlist" start="${measured + 1}">${rows.slice(0, ui.floorAll ? rows.length : 60).map(r => `<li>${r.spotify ? `<a href="https://open.spotify.com/artist/${esc(r.spotify)}" target="_blank" rel="noopener">${esc(r.name)}</a>` : `<a href="https://www.deezer.com/artist/${esc(r.deezer)}" target="_blank" rel="noopener">${esc(r.name)}</a>`} <span class="note" title="latest release">${esc(r.year)}</span></li>`).join("")}</ol>
    ${!ui.floorAll && rows.length > 60 ? `<p class="more"><button type="button" class="btn" id="floorall">Show all ${rows.length}</button></p>` : ""}
    <p class="note">Found through Deezer's related-artists links from its country charts and Wikidata, kept when at least half of an artist's releases are filed under Country. Data: Deezer.</p></section>`;
}

function rising() {
  nav("movers");
  const inTop = new Set(store.data.artists.slice(0, 100).map(a => a.id)), rest = store.data.artists.filter(a => !inTop.has(a.id) && a.chg_pct != null);  // fixed: the top 100 by monthly listeners, whatever the list view
  const list = [...rest].sort((a, b) => b.chg_pct - a.chg_pct).slice(0, RISING_LIMIT).map((a, i) => ({ ...a, rrank: i + 1 }));
  app.innerHTML = `${subnav()}<section><h1>Movers: today</h1>${moversSwitch("today")}
    <p class="sub">Biggest daily gains in monthly listeners among the ${rest.length} hip-hop artists outside the top 100 by monthly listeners (those with a measured count yesterday and today). Daily moves are noisy; for momentum scored against artists of the same size, see <a href="#/scout">Scout</a>.</p></section>
    <section>${tableRising(list)}</section>`;
}
function tableRising(list) {
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th>Hip-hop rank</th><th>Monthly listeners</th><th>Today</th><th>Today %</th><th>Peak listeners</th></tr></thead><tbody>
  ${list.map(a => `<tr><td class="l">${a.rrank}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td>${a.rank}</td><td>${mlx(a)}</td><td>${delta(a.chg)}</td><td>${pct(a.chg_pct)}</td><td>${count(a.peak_ml)}</td></tr>`).join("")}</tbody></table></div>`;
}

// ---------- unsigned
const LICENSED = /under (exclusive )?licen[cs]e to|\blabel deal\b/i;  // "X under exclusive license to UnitedMasters LLC"
// owner, 2026-10-25: a licence to a distribution service leaves the masters with the artist, so it stays self-released
// without a warning; a licence to a record label is already classed by that label (labels.classify_label)
const ESTABLISHED_YEARS = 8;  // as src/labels.py
// an unsigned prospect (src/labels.py independent_kind): self-released, no label deal on record, under ESTABLISHED_YEARS
// of releases and 10m listeners, with current listeners and a song of their own in the last 2 years; not a second profile
const isProspect = a => a?.label_status === "self_released" && a.indie_kind === "prospect" && !a.second_of;
// a prospect we name as a pick (start page, Scout, This month): not mostly a featured guest (as insights.is_pick)
const isPick = a => isProspect(a) && !(a.feat >= 0.9);
const SERVICES = /licen[cs]e to (unitedmasters|stem|distrokid|tunecore|cd baby|amuse|too lost)\b/i;
const STATUS = { major: "Major label", major_distributed: "Major's distribution", independent: "Independent label", self_released: "Self-released", catalog: "Catalog (no release in 2 years)", unknown: "Not yet classified" };
// one wording for a status wherever it shows (list, artist page, Compare, CSV): the self-released split in three
const statusWord = a => a?.label_status !== "self_released" ? STATUS[a?.label_status] || "Not yet classified"
  : a.indie_kind === "established" ? "Independent (established)" : a.indie_kind === "inactive" ? (a.cl === 0 ? "Self-released, catalog only" : "Self-released, no recent release") : "Unsigned prospect";
const statusWordHtml = a => a?.label_status === "self_released" && a.indie_basis?.length ? `<span title="${esc(a.indie_basis.join("; "))}">${esc(statusWord(a))}</span>` : esc(statusWord(a));
// current listeners: "catalog only" instead of a bare 0
const clx = a => a.floor ? "under 500k" : a.cl === 0 ? `<span class="note" title="Almost none of the listening is on recent releases (the last 18–36 months)">catalog only</span>` : count(a.cl);
function unsignedPage() {
  nav("unsigned");
  const ALL = store.data.unsigned || [], sh = Object.fromEntries(store.data.deals.map(d => [d.deal_type, d]));
  // owner, 2026-10-25: only artists with no label deal on record and a short career count as unsigned prospects;
  // established acts releasing on their own (Jeezy, Lil Pump) are listed apart, below
  // and only those with a current audience and a song of their own in the last 2 years (Knust, Makaveli: listed apart)
  const U = ALL.filter(u => u.indie_kind === "prospect"), E = ALL.filter(u => u.indie_kind === "established"), X = ALL.filter(u => u.indie_kind === "inactive");
  const pct = k => Math.round(+sh[k].mid * 100) + "%";
  const be = U[0]?.break_even || {};
  app.innerHTML = `${subnav()}<section><h1>Unsigned</h1>
    <p class="sub">Up-and-coming hip-hop artists releasing without a label and with no label deal on record, ranked by current listeners, each set against the five active signed artists (at least 20% of their listening on recent releases) closest to them in audience. Unsigned means the label on their recent releases is a distributor or their own name, not a record label, checked against the recording codes of their recent songs where possible. A prospect also has listeners on recent releases and a song of their own released in the last two years. Established artists who release on their own after a label deal, after ${ESTABLISHED_YEARS}+ years of releases or with 10m+ monthly listeners, and self-released artists with no current audience or no recent song, are listed apart at the end.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Unsigned prospects</div><div class="v">${U.length}</div><div class="s">no label deal on record, under ${ESTABLISHED_YEARS} years of releases and 10m listeners, a recent song of their own; ${E.length} established independents${X.length ? ` and ${X.length} with no current audience or recent song` : ""} listed apart${(n => n > ALL.length ? `; ${n - ALL.length} more self-released have no stream figure or no signed artist close in size` : "")(store.data.artists.filter(a => a.label_status === "self_released").length)}</div></div>
      <div class="tile"><div class="k">Keeps today, unsigned</div><div class="v">${pct("diy")}</div><div class="s">of recording royalties, after the distributor's fee</div></div>
      <div class="tile"><div class="k">Keeps on a major deal</div><div class="v">${pct("major")}</div><div class="s">so a deal must grow streams ${be.major}× to pay the same ${grade("A")}</div></div>
      <div class="tile"><div class="k">Independent label / label services</div><div class="v">${pct("independent")} / ${pct("services")}</div><div class="s">break even at ${be.independent}× / ${be.services}× the streams</div></div>
    </section>
    <div class="links" style="margin:8px 0"><button type="button" class="btn" id="uns-csv">Download prospects CSV (${U.length})</button><span class="note">official public profiles (Spotify, YouTube, Instagram, Wikidata) only; no personal contact data</span></div>
    <section><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Release label</th><th>Monthly listeners</th><th>Current listeners</th><th>Generates / yr</th><th>Keeps now</th><th>Signed peers generate</th><th>On a major deal would keep</th><th>Scout</th></tr></thead><tbody>
      ${U.slice(0, ui.unsAll ? U.length : 50).map((u, i) => `<tr${u.feat > 0.9 ? ' class="dim"' : ""}><td class="l">${i + 1}</td><td class="l"><a class="who" href="#/a/${u.id}">${pic(store.data.artists.find(a => a.id === u.id) || u)}<span>${esc(u.name)}</span>${flag(store.data.artists.find(a => a.id === u.id) || u)}</a></td>
        <td class="l wrap">${lname(u.label || "–")} ${LICENSED.test(u.label || "") && !SERVICES.test(u.label || "") ? `<span class="chip warn" title="The release line says the recordings are licensed to another company: this may be a licence or label-services deal rather than unsigned, so Keeps now may be too high">licensed out</span>` : u.confidence === "confirmed" ? chip("confirmed") : `<span class="chip warn" title="Own-name label with no other evidence: could be a small label or an imprint licensed to one">label name only</span>`}</td>
        <td>${mlx(u)}</td><td>${clx(u)}</td><td>${usd(u.generated)}${u.feat > 0.9 ? ` <span class="chip warn" title="${Math.round(u.feat * 100)}% of their streams come as a featured guest on other artists' songs; the money shown counts their own songs only. Featured artists are usually paid a fee or a share agreed with the lead artist.">own songs only</span>` : ""}</td><td>${usd(u.keeps_now)}</td>${u.feat > 0.9 ? `<td colspan="2"><span class="note" title="Nearly all of this artist's streams come as a featured guest, so their own songs are not comparable with signed lead artists">not compared</span></td>` : `<td>${usd(u.peer_generated)}</td><td>${usd(u.if_signed.major)}</td>`}<td>${(s => s ? `${s.score} ${tierChip(s.tier)}` : "–")(store.data.artists.find(a => a.id === u.id)?.scout)}</td></tr>`).join("")}
    </tbody></table></div>
    ${!ui.unsAll && U.length > 50 ? `<p class="more"><button type="button" class="btn" id="unsall">Show all ${U.length}</button></p>` : ""}
    <p class="note">Yearly at today's pace, mid estimates, streaming only (all platforms). <b>Generates</b>: royalties paid for the recordings. <b>Keeps now</b>: ${pct("diy")} of that after a distributor's fee. <b>Signed peers generate</b>: the median of the five closest active signed artists. Artists whose streams come almost all as a featured guest are greyed and not compared. <b>On a major deal</b>: ${pct("major")} of today's royalties, before any advance is recouped.</p></section>
    <section><h2>Each artist against their signed peers</h2>
      ${U.slice(0, ui.unsAll ? U.length : 50).map(u => `<details class="panel"><summary><b>${esc(u.name)}</b>${flag(store.data.artists.find(a => a.id === u.id) || u)}: ${mlx(u)} monthly listeners, ${u.spl ? u.spl.toFixed(2) : "–"} streams a day per listener against ${u.peer_spl ? u.peer_spl.toFixed(2) : "–"} for the peers</summary>
        <div class="tablebox"><table><thead><tr><th class="l">Peer</th><th class="l">Label</th><th>Monthly listeners</th><th>Streams / day per listener</th><th>Generates / yr</th><th>Artist's slice</th></tr></thead><tbody>
        ${u.peers.map(p => `<tr><td class="l"><a href="#/a/${p.id}">${esc(p.name)}</a>${flag(store.data.artists.find(a => a.id === p.id))}</td><td class="l">${esc(STATUS[p.status])}${p.owner ? " · " + esc(p.owner) : ""}</td><td>${mlx(p)}</td><td>${p.spl ? p.spl.toFixed(2) : "–"}</td><td>${usd(p.generated)}</td><td>${usd(p.artist_slice)}</td></tr>`).join("")}
        <tr class="tot"><td class="l">${esc(u.name)} (unsigned)</td><td class="l">${lname(u.label || "")}</td><td>${mlx(u)}</td><td>${u.spl ? u.spl.toFixed(2) : "–"}</td><td>${usd(u.generated)}</td><td>${usd(u.keeps_now)}</td></tr>
        </tbody></table></div>
        <p class="note">${u.at_peer_engagement ? `With the peers' streams per listener, ${esc(u.name)} would generate about ${usd(u.at_peer_engagement)} a year. ` : ""}Signed today, ${esc(u.name)} would keep about ${usd(u.if_signed.major)} on a major deal, ${usd(u.if_signed.independent)} with an independent label or ${usd(u.if_signed.services)} on label services, against ${usd(u.keeps_now)} now. Label money on signing (advances, marketing) is not public and not included.</p></details>`).join("")}
    </section>
    ${X.length ? `<details class="panel"><summary><b>No current audience or no recent song (${X.length})</b>: self-released, but not counted as unsigned prospects</summary>
      <div class="tablebox"><table><thead><tr><th class="l">Artist</th><th class="l">Release label</th><th>Monthly listeners</th><th>Current listeners</th><th class="l">Why not a prospect</th></tr></thead><tbody>
      ${X.map(u => `<tr><td class="l"><a class="who" href="#/a/${u.id}">${pic(store.data.artists.find(a => a.id === u.id) || u)}<span>${esc(u.name)}</span>${flag(store.data.artists.find(a => a.id === u.id) || u)}</a></td><td class="l wrap">${lname(u.label || "–")}</td><td>${mlx(u)}</td><td>${u.cl == null ? "–" : clx(u)}</td><td class="l wrap">${esc((u.indie_basis || []).join("; "))}</td></tr>`).join("")}
      </tbody></table></div></details>` : ""}
    ${E.length ? `<details class="panel"><summary><b>Established independents (${E.length})</b>: self-released now, but with a label deal on record, ${ESTABLISHED_YEARS}+ years of releases or 10m+ monthly listeners, so not counted as unsigned prospects</summary>
      <div class="tablebox"><table><thead><tr><th class="l">Artist</th><th class="l">Release label</th><th>Monthly listeners</th><th class="l">Why established</th></tr></thead><tbody>
      ${E.map(u => `<tr><td class="l"><a class="who" href="#/a/${u.id}">${pic(store.data.artists.find(a => a.id === u.id) || u)}<span>${esc(u.name)}</span>${flag(store.data.artists.find(a => a.id === u.id) || u)}</a></td><td class="l wrap">${lname(u.label || "–")}</td><td>${mlx(u)}</td><td class="l wrap">${esc((u.indie_basis || []).join("; "))}</td></tr>`).join("")}
      </tbody></table></div></details>` : ""}
    <p class="note">Peers: signed artists (major, major-distributed or independent label) with 0.6–1.67× the monthly listeners (0.4–2.5× when fewer than three qualify) and at least 20% of their listening on recent releases, closest first. Statuses come from the labels printed on each artist's last two years of releases (Deezer) and the recording codes (ISRCs) of their recent songs; artists that cannot be placed are checked by our editors.</p>`;
  app.querySelector("#unsall")?.addEventListener("click", () => { ui.unsAll = true; unsignedPage(); });
  app.querySelector("#uns-csv").onclick = () => unsignedCsv(U);
  syncScreen("unsigned");
}

// ---------- audience
const cname = cc => store.data.countries[cc] || cc.toUpperCase();
const weeksLabel = () => { const w = store.data.chart_weeks || {}; return w.latest ? (w.weeks > 1 ? `${w.weeks} weeks to ${w.latest}` : `week ending ${w.latest}`) : "no chart data yet"; };
const usPos = g => { const u = g.charts.find(([cc]) => cc === "us"); return u ? u[1] : null; };
function audiencePanel(a) {
  const g = a.geo;
  return `<section class="panel"><h2>Where the hits are played</h2>
    ${g ? `<p>${esc(a.name)} has a song in Spotify's weekly top 200 in <b>${g.countries} of 76 countries</b> (${weeksLabel()}). Best positions:</p>
      <div class="chips">${g.charts.slice(0, 16).map(([cc, pos]) => `<span class="chip">${esc(cname(cc))} #${pos}</span>`).join(" ")}${g.charts.length > 16 ? ` <span class="note">+${g.charts.length - 16} more</span>` : ""}</div>
      <p class="note">A chart position, not a share of fans: a small country's top 200 takes far fewer streams than the US one, so one guest verse can chart abroad while the artist's main audience sits just below the US cut-off.</p>`
        : `<p class="note">No song in any country's Spotify top 200 (${weeksLabel()}), so there is no measured country spread.${a.country ? ` Home country: ${esc(a.country)}.` : ""}</p>`}
    ${a.apple ? `<p><b>Apple Music:</b> in the daily top 100 in ${a.apple.countries.length} of ${store.data.apple_countries} countries (${esc(store.data.apple_day)}), best #${a.apple.best_pos}: ${a.apple.countries.map(cc => esc(cname(cc))).join(", ")}. Songs: ${a.apple.songs.map(esc).join(", ")}.</p>` : store.data.apple_day ? `<p class="note">Not in Apple Music's daily top 100 in any of the ${store.data.apple_countries} countries we read (${esc(store.data.apple_day)}).</p>` : ""}
    <p class="note">The age and gender of ${esc(a.name)}'s fans are not public; see Audience.</p></section>`;
}
function audience() {
  nav("audience");
  const hundred = top100(), d = store.data;
  const sum = {};
  for (const a of hundred) if (a.geo) for (const [cc, , st] of a.geo.charts) sum[cc] = (sum[cc] || 0) + st;
  const tot = Object.values(sum).reduce((x, y) => x + y, 0) || 1;
  const markets = Object.entries(sum).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([cc, v]) => [cc, v / tot]);
  const geoBars = (top) => `<div class="bars">${top.map(([cc, sh]) => `<div class="barrow"><span>${esc(cname(cc))}</span><div class="track"><i style="left:0;width:${sh * 100}%"></i></div><span>${Math.round(sh * 100)}%</span></div>`).join("")}</div>`;
  const withGeo = hundred.filter(a => a.geo);
  app.innerHTML = `${subnav()}<section><h1>Where hip-hop is streamed</h1>${sizeSwitch()}
    <p class="sub">Who listens, and where. Some of it can be measured from public data; some of it cannot, and this page says which.</p></section>
    <section class="tablebox"><table class="stack"><thead><tr><th class="l">Question</th><th class="l">What we have</th><th class="l">Status</th></tr></thead><tbody>
      <tr><td class="l"><b>Which countries</b></td><td class="l wrap">Each artist's streams in Spotify's weekly top 200 of 76 countries (kworb.net, ${weeksLabel()})</td><td class="l">${chip("measured")} for ${withGeo.length} of the top 100</td></tr>
      <tr><td class="l"><b>Which cities</b></td><td class="l wrap">Spotify shows each artist's top 5 cities on its own site, but its terms bar collecting them</td><td class="l">not collected</td></tr>
      <tr><td class="l"><b>Age and gender, per artist</b></td><td class="l wrap">Not public for any platform. Licensed providers (Soundcharts from $50 a month, Chartmetric) model it from Instagram, YouTube and TikTok followers</td><td class="l">needs a licence</td></tr>
      <tr><td class="l"><b>Hip-hop's audience as a whole</b></td><td class="l wrap">${GENRE === "country" ? "Genre-level surveys of country listeners are not collected yet" : "Surveys and industry reports, below"}</td><td class="l">${GENRE === "country" ? "not collected" : `${chip("reported")} genre level only`}</td></tr>
    </tbody></table></section>
    <section class="panel"><h2>Where the top 100's hits are streamed</h2>${markets.length ? geoBars(markets) : `<p class="note">No chart data yet.</p>`}
      <p class="note">Share of the top 100's combined streams in Spotify's weekly top 200 charts, by country (${weeksLabel()}). Big markets dominate, as they should; countries without a Spotify chart (China, most of Africa) are not covered.</p></section>
    ${GENRE === "country" ? "" : `<section class="panel" data-noswap><h2>Hip-hop's audience, genre level</h2><ul>
      <li><b>The biggest genre in the US, shrinking:</b> R&amp;B/hip-hop had 349.9bn US on-demand audio streams in 2025, about 25% of the total; in 2024 its share had fallen 1.7 percentage points, to 25.3%. ${grade("B")} <a href="https://luminatedata.com/wp-content/uploads/2026/01/2025-Year-End-Music-Report-1.2026.pdf" target="_blank" rel="noopener">Luminate 2025</a>, <a href="https://luminatedata.com/blog/how-rb-hip-hop-streaming-share-could-get-its-groove-back" target="_blank" rel="noopener">Luminate on 2024</a></li>
      <li><b>The most time with music:</b> people whose main genre is hip-hop/R&amp;B listen 3 hours 48 minutes a day, almost an hour more than the average American aged 13+. ${grade("B")} <a href="https://www.insideradio.com/free/edison-listeners-spending-most-daily-time-with-music-are-hip-hop-r-b-fans/article_798aa000-6358-483a-9f41-b8204aff6bcb.html" target="_blank" rel="noopener">Edison Research, Q2 2025</a></li>
      <li><b>Young:</b> net favourability of rap/hip-hop is +61 among US adults under 45 and −33 among those 45 and over, the widest age gap of any genre; 13% of under-45s call it their favourite genre. ${grade("B")} <a href="https://yougov.com/en-us/articles/45699-americans-opinions-different-music-genres-poll" target="_blank" rel="noopener">YouGov, 2023</a></li>
      <li><b>No reliable gender or ethnicity split</b> of hip-hop listeners has been published in recent years. Figures that circulate online are about 20 years old or unsourced, so they are not shown here.</li>
    </ul></section>`}
    <section><h2>Top ${ui.size === 1000 ? "1,000" : "100"} by country spread</h2><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Home</th><th>Countries charting</th><th>US top 200</th><th class="l">Best chart positions</th></tr></thead><tbody>
      ${hundred.map(a => `<tr><td class="l">${a.pos}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td class="l">${esc(a.country || "–")}</td><td>${a.geo ? a.geo.countries : "–"}</td><td>${a.geo && usPos(a.geo) ? "#" + usPos(a.geo) : "–"}</td><td class="l">${a.geo ? a.geo.charts.slice(0, 4).map(([cc, pos]) => `${esc(cname(cc))} #${pos}`).join(", ") : `<span class="note">not in any top 200</span>`}</td></tr>`).join("")}
    </tbody></table></div></section>`;
  bindSize(audience);
}

// ---------- tours
// tour dates in one format: "Apr–Dec 2025", "Oct 2024–Sep 2025", "2023"; a year-only end the same as the start's year: "from Aug 2025"
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const ym = s => { const m = String(s || "").match(/^(\d{4})(?:-(\d{2}))?/); return !m ? esc(s || "") : m[2] ? `${MON[+m[2] - 1]} ${m[1]}` : m[1]; };
function tourDates(s, e) {
  const a = ym(s), b = ym(e), ys = String(s || "").slice(0, 4), ye = String(e || "").slice(0, 4);
  if (!e || a === b) return a;
  if (/^\d{4}$/.test(String(e))) return ye === ys ? (/^\d{4}$/.test(String(s)) ? a : `from ${a}`) : `${a}–${b}`;
  return ys === ye && a.includes(" ") ? `${a.split(" ")[0]}–${b}` : `${a}–${b}`;
}
// a tour whose end is known only as a year, with a gross that stops at a Billboard cut-off: the months the gross covers
// ("Aug–Sep 2025", not "from Aug 2025"), so every row reads month to month
const tourSpan = t => tourDates(t.start, /^\d{4}$/.test(String(t.end || "")) && t.gross_through ? t.gross_through : t.end);
function tours() {
  nav("tours");
  const T = store.data.tours;
  const [sk, sd] = ui.tsort || ["gross", -1];
  const val = (t, k) => k === "net" ? t.artist_net.mid : t[k];
  const rows = [...T].sort((a, b) => ((val(a, sk) ?? -Infinity) > (val(b, sk) ?? -Infinity) ? 1 : -1) * sd);
  const best = [...T].filter(t => t.per_fan).sort((a, b) => b.per_fan - a.per_fan)[0];
  const top = T[0], sum = T.reduce((s, t) => s + t.gross, 0);
  const cols = [["Shows", "shows"], ["Tickets", "tickets"], ["Gross", "gross"], ["Per show", "per_show"], ["Per fan", "per_fan"], ["Artist's slice", "net"]];
  // one definition of the artist's slice across the site: before agent, manager and tax (as the artist pages)
  const steps = [["Venue, promoter and local costs", 0.35, "rent, staff, security, ticketing; the promoter keeps about 3% (Live Nation 10-K)"],
    ["Artist's production and crew", 0.30, "stage, lights, trucks, band, crew, travel: 25–45%"],
    ["Left for the artist", 0.35, "before agent, manager and tax: the most a typical tour leaves. Out of it the agent takes about 10%, the manager 15–20% and the business manager 5%, about a third in all. We count the artist's slice as 15–35% of gross: bigger productions and support slots leave less"]];
  app.innerHTML = `${subnav()}<section><h1>Tours</h1>
    <p class="sub">Box office reported by Billboard Boxscore and Pollstar for tours since 2023 by artists on our list: how much a tour makes, per show and per fan, and an estimate of what reaches the artist.</p></section>
    <section class="tiles">
      ${top ? `<div class="tile"><div class="k">Biggest tour</div><div class="v">${esc(top.artist)}</div><div class="s">${esc(top.tour)}${top.co && top.share < 1 ? ` with ${esc(top.co)} (co-headline)` : ""}: ${usd(top.gross)}</div></div>` : ""}
      <div class="tile"><div class="k">Most money per fan</div><div class="v">${best ? usd(best.per_fan) : "–"}</div><div class="s">${best ? esc(best.artist) + ", " + esc(best.tour) : ""}</div></div>
      <div class="tile"><div class="k">Reported box office</div><div class="v">${usd(sum)}</div><div class="s">${T.length} tours, graded A or B</div></div>
    </section>
    <section class="panel"><h2>Where a ticket's money goes, roughly ${grade("C")}</h2>
      <div class="bars">${steps.map(([l, v, n]) => `<div class="barrow"><span>${esc(l)}</span><div class="track"><i style="left:0;width:${v * 100}%"></i></div><span>about ${Math.round(v * 100)}%</span></div><p class="note" style="margin:-4px 0 4px">${esc(n)}</p>`).join("")}</div>
      <p class="note">Industry rules of thumb, not reported figures: the split differs by deal (guarantee or door split) and by how big the production is. Stadium headliners keep more of the gross; a support act may keep little after costs.</p></section>
    ${toursByBand(T)}
    <section><div class="tablebox"><table class="stack"><thead><tr><th class="l">Artist</th><th class="l">Tour</th><th class="l">Dates</th>${cols.map(([l, k]) => `<th data-tsort="${k}"${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${l}</th>`).join("")}<th>Grade</th></tr></thead><tbody>
      ${rows.map(t => `<tr><td class="l">${t.id ? `<a href="#/a/${t.id}">${esc(t.artist)}</a>` : esc(t.artist)}</td><td class="l wrap">${esc(t.tour)}${t.co ? ` <span class="note">with ${esc(t.co)}${t.share < 1 ? ", half counted" : ""}</span>` : ""}${t.partial ? ` <span class="note" title="${esc(t.note)}">(part of the tour: ${t.gross_through ? `gross for shows to ${ym(t.gross_through)}` : "the gross covers one Billboard reporting window"})</span>` : ""}</td><td class="l">${tourSpan(t)}</td>
        <td>${t.shows ?? "–"}</td><td>${count(t.tickets)}</td><td>${usd(t.gross)}</td><td>${usd(t.per_show)}</td><td>${usd(t.per_fan)}</td><td>${range(t.artist_net)}</td><td>${grade(t.grade)} <a href="${esc(t.source)}" target="_blank" rel="noopener" title="${esc(t.note)}">source</a></td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Per fan = gross ÷ tickets sold. Artist's slice = 15–35% of gross (rule of thumb), before agent, manager and tax, half for a co-headline. Merch adds roughly $10–15 per fan in sales (ATVENU). Tours with no reported gross, such as Playboi Carti, GloRilla and Doechii, and most tours outside the US are not listed: Billboard and Pollstar publish no figure for them. Click a column to sort.</p></section>`;
  app.querySelectorAll("th[data-tsort]").forEach(th => th.onclick = () => { ui.tsort = [th.dataset.tsort, sk === th.dataset.tsort ? -sd : -1]; tours(); });
}

// ---------- platforms
const STREAMING = ["spotify", "youtube", "apple_music", "amazon", "pandora", "deezer", "tidal", "soundcloud", "audiomack", "tiktok", "meta", "others"];
const revOf = (a, key) => key === "streaming" ? STREAMING.reduce((s, k) => s + (a.rev_lines?.[k] || 0), 0) : a.rev_lines?.[key];
function platforms() {
  nav("platforms");
  const d = store.data, P = d.platforms, M = Object.fromEntries(d.multipliers.map(m => [m.platform, m]));
  const hundred = top100();
  const totals = STREAMING.map(k => [k, hundred.reduce((s, a) => s + (a.rev_lines?.[k] || 0), 0)]).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const max = totals[0]?.[1] || 1, sum = totals.reduce((s, [, v]) => s + v, 0);
  const rate = p => p.per_1000_mid ? `$${(+p.per_1000_low).toFixed(2)}–${(+p.per_1000_high).toFixed(2)}` : "not per play";
  const measured = k => ["spotify", "youtube"].includes(k);
  const [sk, sd] = ui.psort || ["rev:streaming", -1];
  const val = (a, key) => key.startsWith("rev:") ? revOf(a, key.slice(4)) : key === "lead_daily" ? (a.daily != null && a.feat != null ? Math.round(a.daily * (1 - a.feat)) : null) : a[key];
  const rows = [...hundred].sort((a, b) => ((val(a, sk) ?? -Infinity) > (val(b, sk) ?? -Infinity) ? 1 : -1) * sd);
  app.innerHTML = `${subnav()}<section><h1>Streaming platforms</h1>${sizeSwitch()}
    <p class="sub">What each service pays, what we can measure, and where the top 100's streaming money comes from. Spotify streams and YouTube views are measured. The other services publish no play counts, so their royalties are estimated from each artist's Spotify royalties, using each service's share of label streaming revenue in Warner and Universal's filings.</p></section>
    <section class="panel"><h2>Where the top ${ui.size === 1000 ? "1,000" : "100"}'s recording royalties come from, per year ${grade("C")}</h2>
      <div class="bars">${totals.map(([k, v]) => `<div class="barrow"><span>${esc(P[k]?.name || k)}${measured(k) ? " " + chip("measured") : ""}</span><div class="track"><i style="left:0;width:${v / max * 100}%"></i></div><span>${usd(v)} · ${Math.round(v / sum * 100)}%</span></div>`).join("")}</div>
      <p class="note">Mid estimates of royalties paid to the labels and distributors, before the artists' share: ${usd(sum)} a year in total. ${(() => { const by = {}; totals.filter(([k]) => M[k]).forEach(t => (by[M[t[0]].mid] = by[M[t[0]].mid] || []).push(t));  // services estimated with the same ratio show the same total
        return Object.values(by).filter(g => g.length > 1).map(g => `${g.map(([k]) => esc(P[k]?.name || k)).join(" and ")} show the same total because ${g.length > 2 ? "all" : "both"} are estimated at the same ratio to Spotify (${(+M[g[0][0]].mid).toFixed(2)}×, mid), not measured.`).join(" "); })()} YouTube is likely understated: only views on the channels kworb tracks are counted, so fan uploads paid through Content ID and much of YouTube Music listening are not in it.</p></section>
    <section><h2>How each service pays</h2><div class="tablebox" data-noswap><table><thead><tr><th class="l">Service</th><th class="l">How it pays</th><th>Per 1,000 plays</th><th>Grade</th><th class="l">Our data</th></tr></thead><tbody>
      ${Object.values(P).map(p => `<tr><td class="l"><b>${esc(GENRE === "country" && p.platform === "others" ? p.name.replace("Pandora, ", "") : p.name)}</b></td><td class="l wrap">${esc(p.payout_model)}${M[p.platform] ? ` <span class="note">Our estimate: Spotify royalties × ${(+M[p.platform].low).toFixed(2)}–${(+M[p.platform].high).toFixed(2)}.</span>` : ""}</td><td>${rate(p)}</td><td>${grade(p.grade)}</td><td class="l wrap">${esc(p.our_data)}${p.source?.startsWith("http") ? ` <a href="${esc(p.source)}" target="_blank" rel="noopener">source</a>` : ""}</td></tr>`).join("")}
    </tbody></table></div></section>
    <section><h2>Top ${ui.size === 1000 ? "1,000" : "100"} by platform</h2><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th>${PLATFORM_COLUMNS.map(c => `<th data-psort="${c[1]}"${c[1] === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${esc(c[0])}</th>`).join("")}</tr></thead><tbody>
      ${rows.map(a => `<tr><td class="l">${a.pos}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td>${PLATFORM_COLUMNS.map(([, k, f]) => { const v = val(a, k); return `<td>${f === "money" ? usd(v) : count(v)}</td>`; }).join("")}</tr>`).join("")}
    </tbody></table></div><p class="note">Royalties per year at today's pace, mid estimate, paid to the rights holders. Spotify streams a day are those of the songs where the artist is the lead artist, the streams the royalties are paid on; streams as a featured guest are left out here (the artist page shows both). Click a column to sort.</p></section>`;
  app.querySelectorAll("th[data-psort]").forEach(th => th.onclick = () => { ui.psort = [th.dataset.psort, sk === th.dataset.psort ? -sd : -1]; platforms(); });
  bindSize(platforms);
}

function bar(label, r, max, extra = "") {
  const w = v => Math.max(0, Math.min(100, v / max * 100));
  return `<div class="barrow"><span>${esc(label)}</span><div class="track"><i class="range" style="left:${w(r.low)}%;width:${w(r.high) - w(r.low)}%"></i><i style="left:${w(r.mid)}%;width:2px"></i></div><span>${range(r)}${extra}</span></div>`;
}

async function artist(id) {
  nav("artist");
  const base = store.data.artists.find(x => x.id === id);
  if (!base) {  // an artist of the other genre's list (an old or hand-edited link) opens there; otherwise say so
    const og = GENRE === "hip_hop" ? "country" : "hip_hop", od = await loadGenre(og);
    if (od?.artists.some(x => x.id === id)) { location.replace(`${og === "hip_hop" ? "#/" : "#/" + og + "/"}a/${id}`); return; }
    crumbs([["Artists", "#/"], ["Not found"]]); setMeta("Artist not found");
    app.innerHTML = `<section class="panel"><h1>Artist not found</h1><p>This artist is not in the current list: the list is rebuilt daily from the top ${measured()} and artists who fall out of it leave the site.</p><p><a href="#/">Back to the top list</a></p></section>`; return; }
  if (!store.rev[id]) store.rev[id] = await detailOf(id);
  const a = { ...base, ...store.rev[id].artist, photo: base.photo && { ...base.photo, ...(store.rev[id].artist.photo || {}) } };
  crumbs([["Artists", "#/"], [a.name]]);
  setMeta(`${a.name}: listeners, earnings and label`, `${a.name}: ${mlx(a)} monthly listeners${a.cl_rank ? `, #${a.cl_rank} by current listeners` : ""}${a.label_name ? `, ${a.label_name}` : ""}. What the music earns and who owns it, sourced.`);
  const m = a.money, yr = r => ({ low: r.low * 12, mid: r.mid * 12, high: r.high * 12 });
  const PROFILE = { spotify: "Spotify", youtube: "YouTube", instagram: "Instagram", tiktok: "TikTok", x: "X", wikidata: "Wikidata" };
  const profiles = Object.keys(PROFILE).filter(k => a.links[k]).map(k => `<a href="${esc(a.links[k])}" rel="noopener" target="_blank">${PROFILE[k]}</a>`).join(" · ");
  const links = "";
  const leadShare = a.streams ? a.lead_streams / a.streams : null;
  app.innerHTML = `<section class="head">${pic(a, true)}<div><h1>${esc(a.name)} ${star(a.id)}</h1>
      <p class="sub">${a.cl_rank ? `<span class="def" title="Rank by current listeners: monthly listeners counting only listening to recent releases">#${a.cl_rank.toLocaleString()} by current listeners</span> · ` : ""}#${a.rank.toLocaleString()} in hip-hop by ${a.floor === "streams" ? "streams a day" : a.floor ? "Deezer's order" : "listeners"}${a.rank_all ? ` · #${a.rank_all.toLocaleString()} on Spotify overall` : ""}${a.country ? " · " + flag(a) + esc(a.country) : ""}${a.since ? " · active since " + esc(a.since) : ""}</p>
      ${a.about ? `<p class="about">${esc(a.about.text)}${a.about.source === "wikipedia" ? ` <span class="note"><a href="${esc(a.about.url)}" target="_blank" rel="noopener">Wikipedia</a>, CC BY-SA</span>` : ""}</p>` : ""}
      ${labelOf(a) ? `<div class="parentchip">${logo(labelOf(a).name, "logo")}<span>${labelLink(a)}${(() => { const L = labelOf(a), g = L.group && L.group !== L.name ? L.group : null;  // same company name as the label-status line (BMG, owned by Bertelsmann)
        return g ? ` · ${esc(g)}${L.parent && L.parent !== g ? ` (owned by ${esc(L.parent)})` : ""}` : L.parent && L.parent !== L.name ? ` · ${esc(L.parent)}` : ""; })()}</span></div>` : ""}
      ${profiles ? `<p class="profiles">On ${profiles}</p>` : ""}
      ${a.second_of ? `<p class="note">A second Spotify profile of <a href="#/a/${a.second_of}">${esc(a.second_of_name || "another artist")}</a> (the same Wikidata item, Deezer page or name). Label status and level are the main profile's; these listeners are left out of the summed totals and market shares.</p>` : ""}
      <div class="links" style="margin-top:10px">${links}<a href="#/compare/${a.id}">Compare with…</a>${a.ml || a.daily ? `<a href="#/worth/${a.id}">Worth on other deals</a>` : ""}<a href="#/sheet/${a.id}">One-pager (print / PDF)</a>${corrLink(a.name, artistUrl(a))}${shareBtn(`${a.name}: ${mlx(a)} monthly listeners${a.cl_rank ? `, #${a.cl_rank} in ${GENRE === "country" ? "country" : "hip-hop"} by current listeners` : ""} (tventy music)`, a.slug ? `${SITE_URL}${GDIR()}a/${a.slug}/` : "")}${a.slug ? `<a href="${GDIR()}cards/${esc(a.slug)}.png" download="${esc(a.slug)}-tventy-music.png">Download card</a>` : ""}</div></div></section>
    <section class="tiles">
      <div class="tile"><div class="k">Monthly listeners</div><div class="v">${mlx(a)}</div><div class="s">${a.floor === "streams" ? "below the public list; ranked by streams a day" : a.floor ? "below the public list; placed in Deezer's order (grade C)" : `${delta(a.chg)} today (${pct(a.chg_pct)})`}</div></div>
      <div class="tile"><div class="k">Current listeners</div><div class="v">${a.cl != null ? count(a.cl) + (a.cl_provisional ? `<span class="prov">*</span>` : "") : "–"}</div><div class="s">${a.floor ? "no listener count below 500k on Spotify" + (a.cur_share != null ? `; ${a.cur_share > 0 && a.cur_share < 0.01 ? "<1" : Math.round(a.cur_share * 100)}% of streams on recent releases` : "") : a.cl === 0 ? "catalog act: almost no listening on recent releases (the last 18–36 months)" : a.cur_share != null ? (a.cur_share > 0 && a.cur_share < 0.01 ? "<1" : Math.round(a.cur_share * 100)) + "% of listening on recent releases" : "release dates missing"}${a.cl == null && a.cur_share != null && !a.floor ? " · not ranked yet" : ""}${a.cl_provisional ? ` · provisional: ${count(a.cl_range[0])}–${count(a.cl_range[1])} until more songs are dated` : ""}</div></div>
      <div class="tile"><div class="k">Peak</div><div class="v">${count(a.peak_ml)}</div><div class="s">${a.peak_rank ? `best rank #${a.peak_rank} on Spotify` : "most monthly listeners kworb has seen"}</div></div>
      <div class="tile"><div class="k">Streams, all time</div><div class="v">${count(a.streams)}</div><div class="s">${a.daily != null ? count(a.daily) + " a day" : "not measured: no Spotify play counts on kworb yet"}</div></div>
      <div class="tile"><div class="k">YouTube views</div><div class="v">${count(a.yt_total || a.yt_channel_views)}</div><div class="s">${a.yt_daily ? count(a.yt_daily) + " a day" : a.yt_api_daily ? `${count(a.yt_api_daily)} a day on the artist's own channel` : a.yt_total ? "views a day not measured yet" : a.yt_channel_views ? "own channel, all time; views a day after a week of readings" : "not measured: no YouTube channel matched yet"}${a.yt_subs ? " · " + count(a.yt_subs) + " subscribers" : ""}${a.yt_basis ? `<br><span class="note" title="Matched ${esc(a.yt_basis.match.startsWith("channel") ? "through a video on the artist's own YouTube channel" : a.yt_basis.match === "kworb_spotify_link" ? "through kworb's link from the artist's Spotify page" : "through the page's link back to the artist's Spotify profile")}">kworb.net, measured, ${esc(a.yt_basis.date || "")}</span>` : a.yt_channel_views ? `<br><span class="note" title="The artist's own channel (ID from Wikidata or MusicBrainz); fan uploads and other channels are not counted. YouTube's terms allow keeping these figures 30 days, so no history is kept.">YouTube Data API, measured${a.yt_api_window ? `, ${esc(a.yt_api_window[0])} to ${esc(a.yt_api_window[1])}` : ""}</span>` : ""}</div></div>
      <div class="tile"><div class="k">Deezer fans</div><div class="v">${count(a.deezer_fans)}</div><div class="s">Deezer</div></div>
    </section>
    ${summaryCard(a, store.rev[id])}
    <section class="panel" id="revenue"><h2>Revenue streams, per year at today's pace</h2><p class="note">Loading…</p></section>
    ${agePanel(a)}
    ${peerCard(a)}
    <section>
      <div class="panel"><h2>Streams</h2><dl class="kv">
        <dt>As lead artist</dt><dd>${count(a.lead_streams)}</dd>
        <dt>As featured guest</dt><dd>${count(a.feature_streams)}</dd>
        <dt>Share from features</dt><dd>${leadShare != null ? ((1 - leadShare) * 100).toFixed(0) + "%" : "–"}</dd>
        <dt>Tracks credited</dt><dd>${a.tracks ?? "–"}</dd>
        <dt>Top track</dt><dd>${esc(a.top_track || "–")}${a.top_track_streams ? " · " + count(a.top_track_streams) : ""}${(/[([](?:feat|ft)\.?\s([^)\]]*)/i.exec(a.top_track || "") || [])[1] && fold(/[([](?:feat|ft)\.?\s([^)\]]*)/i.exec(a.top_track)[1]).includes(fold(a.name)) ? ` <span class="note">(as featured guest)</span>` : ""}</dd>
        <dt>Label status</dt><dd>${statusWordHtml(a)}${a.label_status === "self_released" && a.indie_basis?.length ? `<br><span class="note">${esc(a.indie_basis.join("; "))}</span>` : ""}${labelOf(a) ? ` · ${labelLink(a)}` : ""}${a.label_owner && a.label_owner !== "the artist's own name" && a.label_owner !== (labelOf(a)?.name || a.label_name) ? " · " + esc(a.label_owner) : ""}${a.label_basis ? `<br><span class="note">${a.label_override || ["unknown", "catalog"].includes(a.label_status) ? "latest" : "based on"}: ${lname(a.label_basis.label)} (${esc(a.label_basis.date)})${a.label_newest ? `; newest release: ${lname(a.label_newest.label)} (${esc(a.label_newest.date)})` : ""}</span>` : ""}</dd>
        <dt>Labels on record</dt><dd>${a.labels?.length ? esc(a.labels.slice(0, 3).join(", ")) + (a.labels.length > 3 ? ` +${a.labels.length - 3}` : "") + `<br><span class="note">Wikidata's record-label list (all years)</span>` : a.label_basis ? `${lname(a.label_basis.label)}<br><span class="note">from recent releases; none listed on Wikidata</span>` : `<span class="note">none listed on Wikidata</span>`}</dd>
      </dl><p class="note">${(() => { const sd = a.streams_date, old = sd && store.data.as_of && (Date.parse(store.data.as_of) - Date.parse(sd)) / 864e5 > 14;  // kworb page not refreshed in two weeks
        return sd ? `Stream totals as of ${esc(sd)} (kworb.net, from Spotify's public play counts).${old ? ` <b>Stale:</b> more than two weeks older than the rest of the data (${esc(store.data.as_of)}).` : ""}` : "No stream totals yet: kworb.net has no page of Spotify's public play counts for this artist."; })()}</p></div>
    </section>
    ${a.radio_rank ? `<section class="panel"><h2>On US radio</h2><p><b>#${a.radio_rank.rank}</b> of the ${a.radio_rank.of} hip-hop artists on the US airplay chart this week, by the audience their songs reached on AM/FM radio.</p><p class="note">Our ranking from the week's airplay audience estimates (all formats). Radio pays the songs' writers and publishers, not the recordings${GENRE === "country" ? "; see the radio line in the money table" : ""}.</p></section>` : ""}
    ${a.shazam ? `<section class="panel"><h2>Discovery</h2><p>${shazamBadge(a)}</p><p class="note">People looking the song up on Shazam: often an early sign, before streams follow. On ${a.shazam.charts} of Shazam's public charts that we read${a.shazam.cities ? a.shazam.cities === 1 ? ", one of them a city chart" : `, ${a.shazam.cities} of them city charts` : ""} (performance over the last 7 days).</p></section>` : ""}
    ${certsPanel(a)}
    ${awardsPanel(a)}
    ${creditsPanel(a)}
    ${a.revivals?.length ? `<section class="panel"><h2>Revival</h2><p>${a.revivals.map(r => `<b>${esc(r.title)}</b> (${r.year}) is up ${Math.round(r.rise * 100)}% in daily streams on a month ago.`).join(" ")} Older songs that come back stay out of current listeners.</p></section>` : ""}
    ${collabPanel(a)}
    ${audiencePanel(a)}
    <section class="panel" id="deals" hidden></section>
    <section class="note">Genre: ${esc(a.genre_basis)}.${a.photo ? ` Photo: ${esc(a.photo.author)}, <a href="${esc(a.photo.page)}" target="_blank" rel="noopener">${esc(a.photo.license)}</a>, via Wikimedia Commons.` : ""}</section>`;
  bindStars(() => artist(id));
  stackify(app);
  revenuePanel(a);
}

// Phones: tables marked "stack" show each row as a block, every value under its column's name (from the header)
function stackify(root) {
  root.querySelectorAll("table.stack").forEach(t => {
    const heads = [...t.querySelectorAll("thead th")].map(th => th.innerText.trim());
    t.querySelectorAll("tbody tr").forEach(tr => [...tr.children].forEach((td, i) => { if (i && heads[i] && td.dataset.k !== heads[i]) td.dataset.k = heads[i]; }));
  });
}

// ---------- revenue streams (artist page): detail from data/a/<id>.json
async function revenuePanel(a) {
  const box = document.getElementById("revenue");
  const rev = store.rev[a.id] || (store.rev[a.id] = await detailOf(a.id));
  if (!rev.lines.length && box) { box.innerHTML = `<h2>Revenue streams</h2><p class="note">No estimate for this artist yet.</p>`; return; }
  if (!box || !document.body.contains(box)) return;
  const m = a.money, groups = ["Streaming", "Publishing", "Live"];
  const rowsFor = g => rev.lines.filter(l => l.group === g).map(l => `<tr title="${esc(l.basis)}"><td class="l">${esc(l.label)}</td><td data-k="Generated">${range(l.generated)}</td><td data-k="Artist's slice">${l.artist ? range(l.artist) : "–"}</td><td data-k="Grade">${grade(l.grade)}</td></tr>`).join("");
  const hasLive = rev.lines.some(l => l.group === "Live");
  box.innerHTML = `<h2>Revenue streams, per year at today's pace</h2>
    <div class="tablebox"><table class="rev"><thead><tr><th class="l">Source</th><th>Generated</th><th>Artist's slice</th><th>Grade</th></tr></thead><tbody>
    ${groups.map(g => rev.lines.some(l => l.group === g) ? `<tr class="sec"><td class="l" colspan="4">${g}</td></tr>${rowsFor(g)}` : "").join("")}
    ${hasLive ? "" : `<tr class="sec"><td class="l" colspan="4">Live</td></tr><tr><td class="l">Touring and merch</td><td class="l note" colspan="3">No reported tour gross in the last 12 months</td></tr>`}
    <tr class="tot"><td class="l">Artist's slice, total</td><td></td><td data-k="Total">${range(rev.artist_total)}</td><td></td></tr></tbody></table></div>
    <p class="note"><b>Generated</b>: what the activity brings in before anyone's cut (royalties paid to the label or distributor, box office, merch sales). <b>Artist's slice</b>: before their manager, lawyer and tax. Recordings assume ${m ? `<b>${esc(m.deal_label)}</b>` : "an unknown deal"}${a.label_basis ? ` (from the label on recent releases: ${lname(a.label_basis.label)})` : a.major ? ` (${esc(a.major)}, from Wikidata's record-label list)` : ""}, before advances are recouped. Spotify ${rev.lines.some(l => l.key === "youtube") ? "and YouTube are measured; YouTube counts only views on the channels kworb tracks, so fan uploads and some YouTube Music listening are not in it" : "is measured; YouTube is not measured for this artist (kworb tracks the bigger channels only), so it is left out of the total"}. The other services are estimated from Spotify. Hover a row for its basis.</p>`;
  const tours = rev.lines.find(l => l.key === "touring")?.tours || [], other = rev.tours_context || [];
  const dbox = document.getElementById("deals");
  const tourItem = t => `<li><b>${esc(t.tour)}</b>, ${tourSpan(t)}: ${usd(t.gross)} gross${t.tickets ? `, ${count(t.tickets)} tickets (${usd(t.gross / t.tickets)} a fan)` : ""}${t.share && t.share < 1 ? `, ${Math.round(t.share * 100)}% counted in the last 12 months` : ""}${t.note ? ` (${esc(t.note)})` : ""} ${grade(t.grade || "C")} ${t.source ? `<a href="${esc(t.source)}" target="_blank" rel="noopener">source</a>` : ""}</li>`;
  if (dbox && (tours.length || other.length || rev.deals.length)) {
    dbox.hidden = false;
    dbox.innerHTML = `${tours.length ? `<h2>Tours counted (last 12 months)</h2><ul class="note">${tours.map(tourItem).join("")}</ul><p class="note"><b>May be partial:</b> only the ${tours.length === 1 ? "report" : `${tours.length} reports`} above ${tours.length === 1 ? "is" : "are"} counted. Dates with no published box office are left out, so the touring line can understate live income.</p>` : ""}
      ${other.length ? `<h2>Earlier or uncounted tours</h2><ul class="note">${other.map(tourItem).join("")}</ul>` : ""}
      ${(() => { const dealItem = d => `<li><b>${esc(({ record_deal: "Record deal", legal: "Legal filing", brand_deal: "Brand deal", forbes_earnings: "Forbes estimate", merch: "Merch", catalog_sale: "Catalog sale", super_bowl: "Super Bowl", business_revenue: "Business", publishing_deal: "Publishing deal", show_fee: "Show fee", feature_fee: "Feature fee" })[d.category] || d.category)}:</b> ${esc(d.item)}${d.year ? ` (${esc(d.year)})` : ""}${d.amount_usd ? `: <b>${usd(+d.amount_usd)}</b>` : ""}.${d.amount_note ? ` ${esc(d.amount_note.replace(/^(\W*)(\w)/, (m, q, c) => q + c.toUpperCase())).replace(/\.?$/, ".")}` : ""} ${grade(d.grade || "C")} ${d.source_url ? `<a href="${esc(d.source_url)}" target="_blank" rel="noopener">source</a>` : ""}</li>`;
        const own = rev.deals.filter(d => d.relation !== "context"), ctx = rev.deals.filter(d => d.relation === "context");
        return (own.length ? `<h2>Reported deals and other income</h2><ul class="note">${own.map(dealItem).join("")}</ul>` : "")
          + (ctx.length ? `<h2>Context: deals around the artist (not their income)</h2><ul class="note">${ctx.map(dealItem).join("")}</ul>` : ""); })()}`;
  }
}

function pay() {
  nav("pay");
  const sp = store.data.rates.find(r => r.item === "master_per_1000");
  app.innerHTML = `${subnav()}<section><h1>Pay gap: same streams, different deals</h1>
    <p class="sub">What an artist keeps from Spotify recording royalties under each kind of deal. Change the streams to match your own.</p></section>
    <section class="panel"><div class="calc">
      <label>Spotify streams<input id="streams" type="number" min="0" step="100000" value="100000000"></label>
      <label>Rate per 1,000 streams (USD)<input id="rate" type="number" min="0" step="0.1" value="${esc(sp.mid)}"></label>
    </div><div id="out"></div>
    <p class="note">Rate: ${esc(sp.note)} ${grade(sp.grade)} <a href="${esc(sp.source)}" target="_blank" rel="noopener">source</a>. Before advances are recouped, before manager (15–20%) and lawyer fees, and before tax. Publishing (songwriting) money is separate: about a quarter of the recording amount again, split among the writers.</p></section>`;
  const draw = () => {
    const s = +app.querySelector("#streams").value || 0, r = +app.querySelector("#rate").value || 0, gross = s * r / 1000;
    // the same deal table as the worth calculator and the artist pages (registry/deal_shares.csv), best paid last
    const D = ["major", "independent", "services", "diy"].map(k => store.data.deals.find(x => x.deal_type === k)).filter(Boolean);
    app.querySelector("#out").innerHTML = `<p>Royalties generated: <b>${usd(gross)}</b>, paid to whoever releases the music.</p><div class="bars">${D.map(d => bar(d.label, { low: gross * d.low, mid: gross * d.mid, high: gross * d.high }, gross, ` ${grade(d.grade)}`)).join("")}</div>
      <ul class="note">${D.map(d => `<li><b>${esc(d.label)}:</b> keeps ${Math.round(d.low * 100)}–${Math.round(d.high * 100)}%. ${esc(d.note)}.${d.source ? ` <a href="${esc(d.source)}" target="_blank" rel="noopener">source</a>` : ""}</li>`).join("")}
      <li><b>Joint venture / profit split:</b> not drawn. It splits net profit after costs (50/50 is the convention), so it is not a share of the royalties: what the artist keeps depends on the costs. <a href="https://www.digitalmusicnews.com/?p=156325" target="_blank" rel="noopener">source</a></li></ul>`;
  };
  app.querySelectorAll("input").forEach(i => i.oninput = draw); draw();
}

// one definition everywhere (Method, Quality, Labels, State: src/state.py): a release in the last two years whose label
// is placed with its owner, or self-released; catalog acts (no recent release) and those not yet classified are not
const labelKnown = a => ["major", "major_distributed", "independent", "self_released"].includes(a.label_status);
// How complete each source is for this list: the gaps, said plainly
function coverageTable() {
  const A = store.data.artists, n = A.length, pctOf = f => Math.round(100 * A.filter(f).length / n) + "%";
  const rows = [
    ["Label owner known", labelKnown, `the label on the last two years' releases, placed with its owner (as on Labels and State; the ${pctOf(a => a.label_status === "catalog")} catalog acts, with no release in two years, are not counted)`],
    ["Ranked by current listeners", a => a.cl != null, "enough of the listening is on songs with a known release date"],
    ["Listener growth (90 days)", a => a.growth90 != null, "a snapshot about 90 days ago (our daily log, or the Internet Archive)"],
    ["Certifications", a => a.certs, "an English Wikipedia discography that lists RIAA, BPI and other awards"],
    ["Awards", a => a.awards, "wins or nominations listed on Wikidata"],
    ["Shazam charts", a => a.shazam, "a song on a Shazam chart in the last 7 days"],
    ["YouTube views a day measured", a => a.yt_daily || a.yt_api_daily, "a kworb.net YouTube page (the bigger artists), else the artist's own channel through the YouTube Data API (a channel ID on Wikidata or MusicBrainz, a week of readings)"],
    ["Photo", a => a.photo, "a free-licence photo on Wikimedia Commons"]];
  return `<h2>Data coverage</h2><div class="tablebox"><table><thead><tr><th class="l">What</th><th>Share of the ${n.toLocaleString()} artists</th><th class="l">Needs</th></tr></thead><tbody>
    ${rows.map(([l, f, d]) => `<tr><td class="l">${esc(l)}</td><td>${pctOf(f)}</td><td class="l wrap note">${esc(d)}</td></tr>`).join("")}</tbody></table></div>
    <p class="note">A missing figure is left out, never filled in with a guess.</p>`;
}

function method() {
  nav("method");
  app.innerHTML = `${subnav()}<section class="prose"><h1>Method and sources</h1>
  <p>Every number has a source and a grade: <b>A</b> primary (company filings, regulators, court records, the platform's own disclosure), <b>B</b> reputable secondary, <b>C</b> our estimate, always shown as a range.</p>
  <h2>Who is in the list</h2><ul>
   <li>Spotify's top ${store.data.universe.toLocaleString()} artists by monthly listeners (kworb.net, which compiles Spotify's public pages; updated daily).</li>
   ${GENRE === "country" ? `<li>Country when at least 60% of the artist's genre votes are country (MusicBrainz community votes), or at least 60% of their releases are filed under Country on Deezer (with the artist confirmed on Wikidata), or two-thirds of their Wikidata genres are country. Borderline cases (30–60%) are decided by hand.</li>
   <li>Below about 500,000 monthly listeners Spotify's public counts stop. Those places are filled from Deezer's related-artists links, ordered by the popularity of each artist's songs on Deezer: an order, not a size (grade C).</li>
   <li>Money: country's listening leans more to Amazon Music and Pandora than rap's, so those services weigh more; US radio adds a songwriters' line (radio pays the songs' writers and publishers, not the recordings).</li></ul>`
   : `<li>Hip-hop or rap if most of the artist's genre votes are hip-hop (MusicBrainz community votes), with Wikidata genres where votes are thin. Borderline cases are decided by hand. Latin trap and reggaeton are a separate list for now.</li></ul>`}
  <h2>Our ranking</h2><p>The top 100 is ranked by <b>current listeners</b>: each artist's monthly listeners, counting the listening that comes from recent releases. Songs that came out years ago but are still streamed a lot add little, so the ranking shows who is drawing an audience with new music now. Release dates come from Deezer and MusicBrainz; an artist is ranked only when the dates cover most of their listening. Older songs that suddenly rise again are marked "Revival" and stay out of the ranking. Method version 1.2, 24 October 2026; changes are listed in the decision log.</p>
  <h2>Numbers</h2><ul>
   <li><b>Monthly listeners:</b> unique listeners over the last 28 days, as Spotify shows them. Measured.</li>
   <li><b>Streams:</b> Spotify's public play counts summed over every track the artist is credited on (kworb.net); lead and featured credits apart. Measured.</li>
   ${(r => `<li><b>Royalties generated:</b> lead-artist streams × $${r.low}–${r.high} per 1,000. The middle, $${r.mid}, is Duetti's 2024 figure for independent masters (<a href="${esc(r.source)}" target="_blank" rel="noopener">source</a>) ${grade("B")}; Spotify disputes per-stream figures. The range around it is our estimate ${grade("C")}: lower for listening heavy in ad-supported plans, higher for US-heavy listening. Paid to the label or distributor.</li>`)(store.data.rates.find(x => x.platform === "spotify" && x.item === "master_per_1000"))}
   <li><b>Artist's share:</b> royalties generated × the share for the deal type (UK CMA, court filings, published distributor terms). The deal type follows the label on the artist's releases of the last two years (see Labels); only where that is unknown is it inferred from Wikidata's record-label list, which covers the whole career. Before recoupment. Estimate (C).</li>
   <li>Spotify's own figures for scale: it paid out more than $11bn in 2025; about 1,500 artists generated at least $1m and 80 at least $10m (recordings and publishing, before any split). <a href="https://newsroom.spotify.com/?p=39435" target="_blank" rel="noopener">Loud &amp; Clear</a> ${grade("A")}</li></ul>
  <h2>Scout score</h2><p>${cap(nSignals())} signals, each turned into a percentile among artists of a similar size (monthly listeners ${bands().map(bandName).join(", ")}), then averaged with these weights: ${Object.values(store.data.scout_factors).map(x => `${esc(x.label)} ${Math.round(x.weight * 100)}%`).join("; ")}. Tiers: ${TIER_RULE()}. It is a pointer, not a prediction: the back-test on archived listener pages (<a href="#/scout">Scout</a>) found the signals with a long history do not yet pick next quarter's risers; the hit rate on our own daily log will be published once 90 days of it exist.</p>
  <h2>Worth</h2><p>Yearly royalties at today's pace (above) and what each income stream would sell for: a year's income × a multiple that depends on how old the songs earning it are. Buyers pay fewer years for new music because its streams fall faster. Each of the artist's songs as lead artist is placed by its release date in an age band: new (under 3 years), mixed (3–10 years) or evergreen (10+ years). The artist's multiple is the bands' multiples weighted by the streams a day on songs of each age. Where under half of those streams are on dated songs, the band follows the share of listening on recent releases instead. The bands are our split; the multiples per band are sourced: ${store.data.multiples.map(m => `${esc(m.vintage)} ${m.multiple_low}–${m.multiple_high}× (<a href="${esc(m.source_url)}" target="_blank" rel="noopener">source</a>)`).join("; ")}. Estimate (C), shown as a range.</p>
  <h2>Labels</h2><p>The label printed on each artist's releases of the last two years (Deezer), mapped to its owner (Universal, Sony, Warner, or independent), and checked against the registrant codes of the recordings (ISRCs). Artists that cannot be placed are listed as not yet known until an editor checks them.</p>
  <ul>
   <li><b>Licensed out ("under exclusive license to X"):</b> the company the recordings are licensed to decides the status, not the artist's own imprint named first. Licensed to a record label (for example Atlantic or Ministry of Sound), the artist counts as signed to that label. Licensed to a distribution service that leaves the masters with the artist (UnitedMasters, Stem, DistroKid, TuneCore, CD Baby, Amuse, Too Lost), the artist stays self-released. ONErpm offers both plain distribution and label-services deals with advances, so a licence to it is flagged "licensed out" rather than decided.</li>
   <li><b>"Label Deal" in a label name</b> (for example "D-Block Europe Label Deal" on Deezer): not a company. We found no published definition of the phrase. Our reading: it names the artist's own imprint as set up in a distributor's or partner's system, which signals a deal behind the release without saying with whom. We treat it as not unsigned and check the recording codes: D-Block Europe's 2026 recordings carry a registrant code (US-A2P) that also appears on other companies' releases (Rostrum Records, BIGHIT MUSIC), so a third party registered them. Their earlier recordings were registered by Universal, and their 2023 single "Prada" was licensed to Ministry of Sound. So they are an established independent with a partner deal, not an unsigned prospect.</li>
   <li><b>Unsigned prospects and established independents:</b> self-released artists are split. An established independent has a record label on Wikidata's career-long list, or own recordings registered by a major (ISRC), or ${ESTABLISHED_YEARS}+ years of releases (Wikidata's "active since" or the earliest dated song as lead), or 10m+ monthly listeners. Jeezy, Lil Pump and KYLE are examples. Of the rest, an unsigned prospect also needs current listeners above zero and a song of their own released in the last two years; those without are shown as "catalog only" or "no recent release". Only prospects count on the Unsigned page, in Scout's "Unsigned" filter and in the prospect picks; the picks (start page, State, Scout's "Unsigned and rising", This month) also leave out artists with 90%+ of their streams as a featured guest. Market shares still count every self-released artist, because they measure who owns the listening.</li>
   <li><b>Second Spotify profiles:</b> two profiles in the list that share a Wikidata item, a confirmed Deezer page or a name (2Pac and Makaveli, Ye and Kanye West, Miyagi & Andy Panda and MiyaGi & Endspiel) are one artist. The smaller is marked "(second Spotify profile)", takes the main profile's label status and level, and is left out of summed listeners, market shares and label totals (a listener of both mostly counts once already). Each pair is checked by our editors.</li></ul>
  <h2>Other sources</h2><ul>
   <li><b>Wikipedia attention:</b> monthly page views of the artist's English Wikipedia article, people only, from the Wikimedia API; the article is the one linked on the artist's Wikidata item.</li>
   <li><b>Apple Music charts:</b> the daily top 100 most-played songs in ${store.data.apple_countries} countries (Apple's public feed). Artists are matched by exact name; names shared by two artists are skipped.</li></ul>
  <h2>Not yet included</h2><p>Instagram, TikTok and X audiences and per-artist age and gender (licensed data only); daily listener history before 2026-10-23 (weekly archived pages from the Internet Archive are used for the Scout back-test and listener growth only).</p>
  ${coverageTable()}
  <h2>Photos</h2><p>Wikimedia Commons, with the author and licence on each artist page. Initials where there is no free photo.</p></section>`;
}

// ---------- shared pieces for Scout, Worth, Labels and the artist summary
const STREAM_KEYS = ["spotify", "youtube", "apple_music", "amazon", "pandora", "deezer", "tidal", "soundcloud", "audiomack", "tiktok", "meta", "others"];
// a sale multiple blended by release age: two decimals on every page; a band's sourced multiple stays as quoted (8–13.7×)
const xm = (v, blended = true) => blended ? (+v).toFixed(2) : String(+v);
// the build's unrounded total where it has one (extra.json), so every page shows the screener's figure; else the lines
const streamingMid = a => a.streaming_mid ?? STREAM_KEYS.reduce((s, k) => s + (a.rev_lines?.[k] || 0), 0);
const share = v => v == null ? "–" : v > 0 && v < 0.005 ? "<1%" : Math.round(v * 100) + "%";
const trend = v => v == null ? "–" : `<span class="${v >= 1.1 ? "up" : v <= 0.9 ? "down" : ""}">${v >= 1 ? "+" : ""}${Math.round((v - 1) * 100)}%</span>`;
const TIER_TIP = { Breaking: "Score 80+, and new songs pull 25%+ of streams or Wikipedia attention is up 30%+", Rising: "Score 65+ (80+ without new songs or attention clearly up)", Watch: "Score 50–64" };
const tierChip = t => t ? `<span class="chip tier t-${t.toLowerCase()}" title="${TIER_TIP[t] || ""}">${esc(t)}</span>` : "";
// under 60% of the factor weight measured (src/insights.py TIER_MIN_WEIGHT): the score stands, with no tier
const provChip = sc => `<span class="chip" title="Only ${Math.round((sc.weight || 0) * 100)}% of the factor weight is measured for this artist, so the score is provisional and gets no tier">provisional</span>`;
const statusShort = a => labelOf(a) ? `<a href="#/label/${labelOf(a).slug}">${esc(a.label_name)}</a>` : a.label_status === "major" || a.label_status === "major_distributed" ? esc(a.label_owner || "Major")
  : a.label_status === "independent" ? `Indie · ${esc(a.label_owner || "")}` : a.label_status === "self_released" ? statusWordHtml(a) : a.label_status === "catalog" ? `<span class="note" title="No release in the last two years">catalog</span>` : `<span class="note">not yet classified</span>`;
function sparkline(vals, w = 160, h = 36) {
  if (!vals || vals.length < 2) return "";
  const max = Math.max(...vals) || 1, step = w / (vals.length - 1);
  const pts = vals.map((v, i) => `${(i * step).toFixed(1)},${(h - 2 - (v / max) * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`;
}
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const nSignals = () => ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][Object.keys(store.data.scout_factors || {}).length] || "several";
// a signal measured as absent scores 0 (src/insights.py ZERO_IS_ABSENT): the bar says what is missing
const ZERO_NONE = { velocity: "0: no new song", breadth: "0: not charting", radio: "0: not on radio" };
function factorBars(sc) {
  const F = store.data.scout_factors;
  return `<div class="bars">${Object.entries(F).map(([k, f]) => { const v = sc.factors[k];
    return `<div class="barrow" title="${esc(f.label)}"><span>${esc(f.label.split(":")[0])}</span><div class="track"><i style="left:0;width:${v ?? 0}%"></i></div><span>${v == null ? "no data" : v === 0 && ZERO_NONE[k] ? ZERO_NONE[k] : v + " / 100"}</span></div>`; }).join("")}</div>`;
}
const median = xs => { const s = xs.filter(x => x != null && isFinite(x)).sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : null; };
const quantile = (xs, q) => { const s = xs.filter(x => x != null && isFinite(x)).sort((a, b) => a - b); return s.length ? s[Math.min(s.length - 1, Math.floor(q * s.length))] : null; };
function download(name, rows) {
  const csv = rows.map(r => r.map(v => /[",\n]/.test(String(v ?? "")) ? `"${String(v).replace(/"/g, '""')}"` : (v ?? "")).join(",")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

// Watchlist: artists a scout follows, kept in this browser only.
const WATCH_KEY = "rapledger.watch";
const watch = new Set((() => { try { return JSON.parse(localStorage.getItem(WATCH_KEY) || "[]"); } catch { return []; } })());
const saveWatch = () => { try { localStorage.setItem(WATCH_KEY, JSON.stringify([...watch])); } catch { /* storage blocked: kept for this visit */ } };
const star = id => `<button type="button" class="star" data-watch="${id}" aria-pressed="${watch.has(id)}" title="${watch.has(id) ? "On your watchlist" : "Add to your watchlist"}">${watch.has(id) ? "★" : "☆"}</button>`;
const bindStars = rerender => app.querySelectorAll("[data-watch]").forEach(b => b.onclick = e => { e.preventDefault(); const id = b.dataset.watch; watch.has(id) ? watch.delete(id) : watch.add(id); saveWatch(); rerender(); });

// ---------- scout: who is rising, for labels
const BANDS = ["under 1.5m", "1.5-3m", "3-6m", "6-15m", "15m+"];
// country: artists below the 500k floor form their own band, sized by streams a day (src/insights.py FLOOR_LABEL)
const bands = () => GENRE === "country" && store.data.artists.some(a => a.floor) ? ["under 500k (by streams)", ...BANDS] : BANDS;
// the artist's countries for the Scout filter: "Jamaica / United States" counts under both; a few Wikidata names in plain form
// DistroKid names an artist's releases "<number> Records DK" when no label is given: show what it is, not the number
const lname = s => esc(String(s ?? "").replace(/^\d{4,} Records DK$/, "DistroKid (numbered label)"));
const PLACE = { "Kingdom of the Netherlands": "Netherlands", "Karachi": "Pakistan", "East Germany": "Germany" };  // filter only: the artist page keeps Wikidata's name  // "Cina" is dropped in the build (an Indonesian subdistrict, not China)
const placesOf = a => (a.country || "").split(" / ").map(c => PLACE[c.trim()] || c.trim()).filter(Boolean);
// the band as shown: where the under-500k band exists, "under 1.5m" holds only 500k–1.5m
const bandName = b => b === "under 1.5m" && bands().length > BANDS.length ? "500k–1.5m" : b.replace(/(\d)-(\d)/, "$1–$2");
function scoutPage() {
  nav("scout");
  const f = ui.scout = ui.scout || { status: "all", band: "all", tier: "rising", country: "all", sort: ["score", -1] };
  const all = store.data.artists.filter(a => a.scout);
  const ok = a => (f.status === "all" || (f.status === "signed" ? ["major", "major_distributed", "independent"].includes(a.label_status) : f.status === "prospect" ? isProspect(a) : a.label_status === f.status))
    && (f.band === "all" || a.scout.band === f.band) && (f.country === "all" || placesOf(a).includes(f.country))
    && (f.tier !== "watch" || watch.has(a.id)) && (f.tier === "all" || f.tier === "watch" || (f.tier === "rising" ? ["Breaking", "Rising"].includes(a.scout.tier) : a.scout.tier === f.tier));
  const val = (a, k) => ({ score: a.scout.score, ml: a.ml, fresh: a.fresh_share, cur: a.cur_share, att: a.attention?.trend,
    spl: a.daily && a.ml ? a.daily / a.ml : null, geo: chartCountries(a), shz: a.shazam?.charts ?? null, chg: a.chg_pct })[k];
  const [sk, sd] = f.sort;
  // blanks (no figure) always last, whichever way the column is sorted
  const rows = all.filter(ok).sort((a, b) => { const x = val(a, sk), y = val(b, sk); return x == null ? (y == null ? 0 : 1) : y == null ? -1 : (x - y) * sd; });
  const countries = [...new Set(all.flatMap(placesOf))].sort();
  const n = t => all.filter(a => a.scout.tier === t).length;
  const unsignedRising = all.filter(a => isPick(a) && ["Breaking", "Rising"].includes(a.scout.tier)).sort((a, b) => b.scout.score - a.scout.score);
  const seg = (key, opts) => `<div class="seg" role="group">${opts.map(([v, l]) => `<button type="button" data-f="${key}" data-v="${v}" aria-pressed="${f[key] === v}">${esc(l)}</button>`).join("")}</div>`;
  const cols = [["Scout score", "score"], ["Monthly listeners", "ml"], ["New-release pull", "fresh"], ["Current share", "cur"], ["Wikipedia, 3 mo", "att"], ["Streams / listener", "spl"], ["Chart countries", "geo"], ["Shazam", "shz"], ["Today", "chg"]];
  const brief = ["score", "ml", "fresh"];  // shown by default; the other signals behind "Show all signals"
  const th = ([l, k]) => `<th data-ssort="${k}"${brief.includes(k) ? "" : ` class="sig"`}${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}><span${defn(l)}>${esc(l)}</span></th>`;
  app.innerHTML = `${subnav()}<section><h1>Scout: who is rising</h1>
    <p class="sub">${all.length === store.data.artists.length ? "Every hip-hop artist in the top 1,000" : `${all.length.toLocaleString()} of the hip-hop artists in the top 1,000 (those with enough signals to score)`}, scored 0–100 on ${nSignals()} signals of momentum. Each artist is compared only with artists of a similar size, so a 1m-listener act that is taking off scores as high as a superstar. The score points at who to look at; it does not predict a hit.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Breaking</div><div class="v">${n("Breaking")}</div><div class="s">score 80+ with new songs or Wikipedia attention clearly up</div></div>
      <div class="tile"><div class="k">Rising</div><div class="v">${n("Rising")}</div><div class="s">score 65+ (80+ without the Breaking test)</div></div>
      <div class="tile"><div class="k">Unsigned and rising</div><div class="v">${unsignedRising.length}</div><div class="s">${unsignedRising.length ? "best scores: " + unsignedRising.slice(0, 3).map(a => `${esc(a.name)} (${a.scout.score})`).join(", ") : "–"}</div></div>
      <div class="tile"><div class="k">Watch</div><div class="v">${n("Watch")}</div><div class="s">score 50–64</div></div>
    </section>
    <section class="filters">
      ${seg("tier", [["rising", "Breaking + Rising"], ["Breaking", "Breaking"], ["Watch", "Watch"], ["all", "All"], ["watch", `★ My watchlist (${watch.size})`]])}
      ${seg("status", [["all", "Any label"], ["prospect", "Unsigned prospect"], ["self_released", "Any self-released"], ["independent", "Indie label"], ["signed", "Any label deal"], ["unknown", "Not yet known"]])}
      <label class="sel">Size <select data-f="band"><option value="all">all sizes</option>${bands().map(b => `<option value="${esc(b)}"${f.band === b ? " selected" : ""}>${esc(bandName(b))}</option>`).join("")}</select></label>
      <label class="sel">Country <select data-f="country"><option value="all">all countries</option>${countries.map(c => `<option${f.country === c ? " selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
      <button type="button" class="btn" id="signals" aria-pressed="${!!f.signals}">${f.signals ? "Fewer columns" : "Show all signals"}</button>
      <button type="button" class="btn" id="csv">Download CSV</button>${linkBtn()}
      <button type="button" class="btn" id="radio" title="30-second previews of each artist's newest hit, in the order shown">📻 Scout radio (${rows.filter(a => a.top_fresh?.dz).length})</button>
    </section>
    <section><div class="tablebox"><table class="${f.signals ? "" : "brief"}"><thead><tr><th class="l">#</th><th class="l">Artist</th>${cols.slice(0, 1).map(th).join("")}<th class="l">Label</th><th class="l">Newest hit</th>${cols.slice(1).map(th).join("")}</tr></thead><tbody>
      ${rows.slice(0, f.all ? rows.length : 50).map((a, i) => `<tr><td class="l">${star(a.id)} ${i + 1}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td><b>${a.scout.score}</b> ${a.scout.provisional ? provChip(a.scout) : tierChip(a.scout.tier)}</td><td class="l wrap lab">${statusShort(a)}</td>
        <td class="l wrap hit">${a.top_fresh ? `${a.scout.tier ? playBtn(a) + videoBtn(a) : ""}${esc(a.top_fresh.title)} <span class="note">${count(a.top_fresh.daily)}/day, out ${esc(a.top_fresh.released)}</span>` : `<span class="note">none in 90 days</span>`}</td>
        <td>${mlx(a)}</td><td>${share(a.fresh_share)}</td><td class="sig">${share(a.cur_share)}</td><td class="sig">${trend(a.attention?.trend)}</td>
        <td class="sig">${val(a, "spl") ? val(a, "spl").toFixed(2) : "–"}</td><td class="sig" title="Spotify weekly top 200 + Apple Music daily top 100">${val(a, "geo") || "–"}</td><td class="sig">${shazamBadge(a, true)}</td><td class="sig">${pct(a.chg_pct)}</td></tr>`).join("") || `<tr><td class="l" colspan="12">${f.band === "15m+" && !["all", "watch"].includes(f.tier) ? "Artists with 15m+ monthly listeners are established and get no tier: choose All to see them." : "No artist matches these filters."}</td></tr>`}
    </tbody></table></div>
    ${!f.all && rows.length > 50 ? `<p class="more"><button type="button" class="btn" id="showall">Show all ${rows.length}</button></p>` : ""}
    <p class="note">${rows.length} artists. Click a column to sort. ☆ adds an artist to your watchlist (kept in this browser). Percentiles are within the artist's size band (monthly listeners ${bands().map(bandName).join(", ")}).</p></section>
    <section class="panel"><h2>How the score works</h2>
      <ul>${Object.values(store.data.scout_factors).map(x => `<li><b>${Math.round(x.weight * 100)}%</b> ${esc(x.label)}</li>`).join("")}</ul>
      <p class="note">Each signal becomes a percentile (0–100) among artists in the same size band; the score is their weighted average over the signals the artist has (at least three). Tiers: ${TIER_RULE()}. Wikipedia views count only artists with an English article. Listener growth uses the Internet Archive's weekly copies of kworb's listener page, so it exists only for artists that page lists. ${grade("C")}</p></section>
    ${backtestPanel()}`;
  app.querySelectorAll("button[data-f]").forEach(b => b.onclick = () => { f[b.dataset.f] = b.dataset.v; scoutPage(); });
  app.querySelector("#signals").onclick = () => { f.signals = !f.signals; scoutPage(); };
  bindStars(scoutPage);
  app.querySelectorAll("select[data-f]").forEach(s => s.onchange = () => { f[s.dataset.f] = s.value; scoutPage(); });
  app.querySelectorAll("th[data-ssort]").forEach(th => th.onclick = () => { f.sort = [th.dataset.ssort, sk === th.dataset.ssort ? -sd : -1]; scoutPage(); });
  app.querySelector("#showall")?.addEventListener("click", () => { f.all = true; scoutPage(); });
  app.querySelector("#radio").onclick = () => startRadio(rows.filter(a => a.top_fresh?.dz));
  app.querySelector("#csv").onclick = () => download("tventy-music-scout.csv", [["name", "spotify_url", "scout_score", "tier", "label_status", "label", "label_group", "country", "monthly_listeners", "current_listeners", "new_release_share", "current_share", "wikipedia_trend", "streams_per_listener", "countries_charting", "newest_hit"],
    ...rows.map(a => [a.name, `https://open.spotify.com/artist/${a.id}`, a.scout.score, a.scout.tier || (a.scout.provisional ? "provisional" : ""), statusWord(a), a.label_name || "", a.label_owner || "", a.country || "", a.floor ? "under 500k" : a.ml, a.cl ?? "", a.fresh_share ?? "", a.cur_share ?? "", a.attention?.trend ?? "", val(a, "spl")?.toFixed(3) ?? "", val(a, "geo"), a.top_fresh?.title || ""])]);
  syncScreen("scout");
}

// ---------- this month: movers, new on Scout's list, unsigned prospects, label shares (src/monthly.py)
function monthPage() {
  nav("movers");
  const M = store.data.month, byId = Object.fromEntries(store.data.artists.map(a => [a.id, a]));
  const who = id => { const a = byId[id]; return a ? `<a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a>` : ""; };
  const days = d => Math.round((Date.parse(M.today) - Date.parse(d)) / 864e5);  // each row's own window: archived copies differ by artist
  const moverTable = (list, title) => `<div><h3>${title}</h3><div class="tablebox"><table><thead><tr><th class="l">Artist</th><th>Then</th><th>Now</th><th>Change</th><th>Days</th></tr></thead><tbody>
    ${list.map(m => `<tr><td class="l">${who(m.id)}</td><td>${count(m.then)}</td><td>${count(m.now)}</td><td>${pct(m.pct)}</td><td title="from ${esc(m.from || M.movers_from)}">${days(m.from || M.movers_from)}</td></tr>`).join("")}</tbody></table></div></div>`;
  const thenKnown = M.shares.some(x => x.then != null);
  const ready = new Date(Date.parse(M.log_from) + M.min_log * 864e5).toISOString().slice(0, 10);
  const label = s => ({ major: "Major label", major_distributed: "Distributed by a major", independent: "Independent label", self_released: "Self-released", catalog: "Catalog (no release in 2 years)", unknown: "Not yet known" })[s] || s;
  app.innerHTML = `${subnav()}<section><h1>Movers: the past month</h1>${moversSwitch("month")}
    <p class="sub">What changed in hip-hop's top 1,000 over about a month (${days(M.movers_from)} days at most: since ${esc(M.movers_from)}, depending on the artist's archived snapshot): who gained and lost listeners, who joined Scout's list, the unsigned acts worth a look, and how listening splits between majors, indies and the self-released.</p></section>
    <section class="panel"><h2>Movers</h2>
      ${M.movers_n ? `<p class="sub">Among the ${M.movers_n.toLocaleString()} artists with a month-ago figure, not all ${measured()} yet.</p><div class="grid2">${moverTable(M.up, "Biggest gains, %")}${moverTable(M.down, "Biggest falls, %")}</div>
      <p class="note">Monthly listeners on ${esc(M.today)} against the snapshot nearest 30 days earlier (the Days column gives each artist's window; the earliest is ${esc(M.movers_from)}). ${M.movers_n.toLocaleString()} of the 1,000 have one yet: our own daily snapshots began on ${esc(M.log_from)}, so for now the month-ago values come from the Internet Archive's copies of kworb's listener page, which lists the biggest artists only. From ${esc(ready)} every artist has one.</p>` : `<p class="note">No month-ago values yet.</p>`}</section>
    <section class="panel"><h2>New on Scout's list</h2>
      ${M.log_start ? `<p>Breaking now, not on ${esc(M.log_start)}: ${M.new_breaking.map(id => who(id)).join(" ") || "none"}</p><p>Rising now, not on ${esc(M.log_start)}: ${M.new_rising.map(id => who(id)).join(" ") || "none"}</p>`
        : `<p class="note">From ${esc(ready)}. Scout's daily log began on ${esc(M.log_from)}, and the score's method changed in its first days, so a shorter comparison would show our changes rather than the artists'. Today's Breaking and Rising artists are on the <a href="#/scout">Scout list</a>.</p>`}</section>
    <section class="panel"><h2>Unsigned and worth a look</h2>
      <div class="chips">${M.prospects.map(id => byId[id] ? `<span class="chipplay">${playBtn(byId[id])}${videoBtn(byId[id])}<a class="chip" href="#/a/${id}">${esc(byId[id].name)} · ${byId[id].scout?.score ?? "–"} ${byId[id].scout?.tier ? esc(byId[id].scout.tier) : ""}</a></span>` : "").join(" ")}</div>
      <p class="note">Unsigned prospects (self-released, no label deal on record, under ${ESTABLISHED_YEARS} years of releases) with a Breaking or Rising Scout tier, best score first${(n => n > M.prospects.length ? ` (the top ${M.prospects.length} of ${n})` : "")(store.data.artists.filter(a => isPick(a) && ["Breaking", "Rising"].includes(a.scout?.tier)).length)}; artists whose streams come 90%+ as a featured guest are left out. <a href="#/unsigned">Unsigned against signed peers</a></p></section>
    <section class="panel"><h2>Who owns the listening</h2><div class="tablebox"><table><thead><tr><th class="l">Label status</th>${thenKnown ? `<th>${M.log_start ? esc(M.log_start) : "A month ago"}</th>` : ""}<th>Now</th></tr></thead><tbody>
      ${(() => { const out = ["catalog", "unknown"], kn = k => 1 - M.shares.filter(x => out.includes(x.status)).reduce((s, x) => s + (x[k] || 0), 0) || 1;  // as on Labels: among artists whose label is known
        return M.shares.filter(x => !out.includes(x.status)).map(x => `<tr><td class="l">${esc(label(x.status))}</td>${thenKnown ? `<td>${x.then == null ? "–" : share(x.then / kn("then"))}</td>` : ""}<td>${share(x.now / kn("now"))}</td></tr>`).join(""); })()}</tbody></table></div>
      <p class="note">Share of the monthly listeners (added per artist) of the top 1,000's artists whose label is known, as on the <a href="#/labels">Labels</a> page: catalog acts (no release in two years) and artists not yet classified are left out. Rounded, so the rows may not add to 100%. Both columns use each artist's label status today, so a share moves only with listening, not with our relabelling. The comparison starts on ${esc(ready)}. ${grade("B")}</p></section>`;
}

// ---------- docked player for Scout's risers (owner, 2026-10-24): Spotify's own embed for songs and YouTube's
// privacy-enhanced player (youtube-nocookie.com) for videos, loaded on the first press of ▶ or 🎬, so no third-party
// code or cookies load before a listener asks for them. Spotify plays full songs for listeners signed in, 30-second
// previews for everyone else. Where Spotify's control script cannot load, a plain embed is used.
let spotifyCtl = null, spotifyApi = null;
// share: the device's share sheet where there is one, else the link is copied
const SITE_URL = "https://tventy.se/music/";
const shareBtn = (text, url = "") => `<button type="button" class="linkbtn" data-share="${esc(text)}" data-url="${esc(url)}">Share</button>`;
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-share]");
  if (!b) return;
  const url = b.dataset.url || location.href, text = b.dataset.share;
  try { if (navigator.share) { await navigator.share({ title: document.title, text, url }); return; } } catch { return; }
  try { await navigator.clipboard.writeText(`${text} ${url}`); b.textContent = "Link copied"; } catch { b.textContent = "Copy the address bar"; }
  setTimeout(() => (b.textContent = "Share"), 2500);
});
const playBtn = a => a?.top_fresh?.id ? `<button type="button" class="play" data-track="${esc(a.top_fresh.id)}" data-label="${esc(a.name + " · " + a.top_fresh.title)}" aria-label="Play ${esc(a.top_fresh.title)} by ${esc(a.name)}" title="Play on Spotify">▶</button>` : "";
const videoBtn = a => a?.video?.id ? `<button type="button" class="play vid" data-video="${esc(a.video.id)}" data-label="${esc(a.name + " · " + a.video.title)}" aria-label="Watch ${esc(a.video.title)}" title="Watch on YouTube (${esc(a.video.why)})">🎬</button>` : "";
const loadSpotify = () => spotifyApi = spotifyApi || new Promise(res => {
  window.onSpotifyIframeApiReady = api => res(api);
  const s = Object.assign(document.createElement("script"), { src: "https://open.spotify.com/embed/iframe-api/v1", async: true, onerror: () => res(null) });
  document.body.appendChild(s);
  setTimeout(() => res(null), 6000);
});
function dock(label, mode) {
  let d = document.getElementById("dock");
  if (!d) {
    d = Object.assign(document.createElement("aside"), { id: "dock", className: "dock" });
    d.setAttribute("aria-label", "Player");
    d.innerHTML = `<div class="wrap dockbar"><span class="docklabel"></span><a class="note" href="#/scout">Scout list</a><button type="button" class="dockclose" aria-label="Close the player">×</button></div><div class="wrap dockbody"></div>`;
    document.body.appendChild(d);
    document.body.classList.add("has-dock");
    d.querySelector(".dockclose").onclick = () => { spotifyCtl?.destroy?.(); spotifyCtl = null; radio.audio?.pause(); radio.queue = []; d.remove(); document.body.classList.remove("has-dock"); };
  }
  d.querySelector(".docklabel").textContent = label;
  d.dataset.mode = mode;
  return d.querySelector(".dockbody");
}
function fresh(body) { spotifyCtl?.destroy?.(); spotifyCtl = null; radio.audio?.pause(); body.innerHTML = `<div id="dockframe"></div>`; return body.firstChild; }
async function play(id, label) {
  const body = dock(label, "audio"), uri = "spotify:track:" + id;
  if (spotifyCtl) { spotifyCtl.loadUri(uri); spotifyCtl.play(); return; }
  const el = fresh(body), api = await loadSpotify();
  if (!el.isConnected) return;
  if (!api) { el.innerHTML = `<iframe title="Spotify player" src="https://open.spotify.com/embed/track/${encodeURIComponent(id)}" width="100%" height="80" frameborder="0" allow="autoplay; clipboard-write; encrypted-media"></iframe>`; return; }
  api.createController(el, { uri, width: "100%", height: 80 }, c => { spotifyCtl = c; c.addListener("ready", () => c.play()); });
}
function playVideo(id, label) {
  const el = fresh(dock(label, "video"));
  el.innerHTML = `<iframe title="YouTube video" src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>`;
}
document.addEventListener("click", e => {
  const b = e.target.closest("button.play");
  if (!b) return;
  e.preventDefault();
  b.dataset.video ? playVideo(b.dataset.video, b.dataset.label) : play(b.dataset.track, b.dataset.label);
});

// ---------- Scout radio (owner, 2026-10-24): 30-second Deezer previews of the risers' newest hits, one after another,
// in the order of the Scout list as filtered. Deezer's preview links expire within the hour, so each one is fetched
// when it is about to play, through Deezer's API in its documented JSONP form (the API sends no CORS headers); nothing
// is fetched before the radio is started. Previews by Deezer, credited with a link to each track.
const radio = { queue: [], i: 0, audio: null };
const jsonp = url => new Promise((res, rej) => {
  const cb = "dzcb" + Math.random().toString(36).slice(2), s = document.createElement("script");
  const done = () => { delete window[cb]; s.remove(); };
  window[cb] = d => { done(); res(d); };
  s.onerror = () => { done(); rej(new Error("Deezer did not answer")); };
  s.src = `${url}${url.includes("?") ? "&" : "?"}output=jsonp&callback=${cb}`;
  document.body.appendChild(s);
  setTimeout(() => { if (window[cb]) { done(); rej(new Error("Deezer timed out")); } }, 8000);
});
function startRadio(list) {
  if (!list.length) return;
  radio.queue = list; radio.i = 0;
  radioPlay();
}
async function radioPlay() {
  const a = radio.queue[radio.i];
  if (!a) return;
  const body = fresh(dock(`📻 ${a.name} · ${a.top_fresh.title}`, "radio"));
  body.innerHTML = `<div class="radio">
      <button type="button" data-r="prev" aria-label="Previous">⏮</button><button type="button" data-r="toggle" aria-label="Pause">⏸</button><button type="button" data-r="next" aria-label="Next">⏭</button>
      <span class="note">${radio.i + 1} / ${radio.queue.length}</span>
      <a href="#/a/${a.id}">${esc(a.name)}</a> ${a.scout ? `${a.scout.score} ${tierChip(a.scout.tier)}` : ""}
      <button type="button" data-r="star" aria-pressed="${watch.has(a.id)}">${watch.has(a.id) ? "★ On watchlist" : "☆ Watchlist"}</button>
      <a class="note" href="https://www.deezer.com/track/${encodeURIComponent(a.top_fresh.dz)}" target="_blank" rel="noopener">Preview: Deezer</a>
      <span class="note" data-r="msg"></span></div>`;
  radio.audio?.pause();
  radio.audio = new Audio();
  radio.audio.onended = () => radioStep(1);
  body.onclick = e => {
    const b = e.target.closest("[data-r]");
    if (!b) return;
    const r = b.dataset.r;
    if (r === "prev") radioStep(-1);
    else if (r === "next") radioStep(1);
    else if (r === "toggle") { radio.audio.paused ? radio.audio.play() : radio.audio.pause(); b.textContent = radio.audio.paused ? "▶" : "⏸"; }
    else if (r === "star") { watch.has(a.id) ? watch.delete(a.id) : watch.add(a.id); saveWatch(); b.textContent = watch.has(a.id) ? "★ On watchlist" : "☆ Watchlist"; b.setAttribute("aria-pressed", watch.has(a.id)); }
  };
  try {
    const t = await jsonp(`https://api.deezer.com/track/${encodeURIComponent(a.top_fresh.dz)}`);
    if (radio.queue[radio.i] !== a) return;  // skipped while loading
    if (!t?.preview) throw new Error("no preview");
    radio.audio.src = t.preview;
    await radio.audio.play();
  } catch (err) {
    const m = body.querySelector('[data-r="msg"]');
    if (m) m.textContent = "No preview for this song; next in 2 seconds";
    setTimeout(() => radio.queue[radio.i] === a && radioStep(1), 2000);
  }
}
function radioStep(d) {
  radio.i = Math.max(0, Math.min(radio.queue.length - 1, radio.i + d));
  radioPlay();
}

// ---------- producer and songwriter credits (MusicBrainz, CC0)
const mbRec = id => `https://musicbrainz.org/recording/${encodeURIComponent(id)}`;
function creditsPanel(a) {
  const C = a.song_credits;
  if (!C?.length) return "";
  return `<section class="panel"><h2>Who makes the hits ${grade("B")}</h2><div class="tablebox"><table class="stack"><thead><tr><th class="l">Song</th><th>Streams / day</th><th class="l">Produced by</th><th class="l">Written by</th></tr></thead><tbody>
    ${C.map(c => `<tr><td class="l"><a href="${mbRec(c.recording)}" target="_blank" rel="noopener">${esc(c.title)}</a></td><td>${count(c.daily)}</td><td class="l wrap">${c.producers.map(n => `<a href="#/producers?q=${encodeURIComponent(n)}">${esc(n)}</a>`).join(", ") || "–"}</td><td class="l wrap">${c.writers.map(esc).join(", ") || "–"}</td></tr>`).join("")}
  </tbody></table></div><p class="note">The artist's biggest songs as lead artist, with the credits entered on MusicBrainz (open data). Credits are partial: a blank means none entered yet.</p></section>`;
}
function producersPage() {
  nav("producers");
  const C = store.data.credits || { producers: [], writers: [] }, q = (location.hash.split("?q=")[1] || "");
  const want = decodeURIComponent(q).toLowerCase();
  const tbl = (list, who) => `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">${who}</th><th>Streams / day on credited songs</th><th>Artists</th><th class="l">Biggest songs</th></tr></thead><tbody>
    ${list.map((p, i) => `<tr${want && p.name.toLowerCase() === want ? ' class="hl"' : ""}><td class="l">${i + 1}</td><td class="l"><a href="https://musicbrainz.org/artist/${esc(p.mbid)}" target="_blank" rel="noopener">${esc(p.name)}</a></td><td>${count(p.daily)}</td><td>${p.artists}</td>
      <td class="l wrap">${p.songs.map(s => `${esc(s.title)} <span class="note">(<a href="#/a/${s.artist_id}">${esc(s.artist)}</a>)</span>`).join(", ")}</td></tr>`).join("")}</tbody></table></div>`;
  app.innerHTML = `${subnav()}<section><h1>Producers and songwriters</h1>
    <p class="sub">Who is credited on the songs the top 1,000's hip-hop artists are streamed most for today: each person ranked by the daily Spotify streams of the songs they are credited on, among each artist's three most-streamed songs as lead artist (old hits included, as long as they are still played).${C.songs ? ` Only ${(C.with_producer || 0).toLocaleString()} of the ${C.songs.toLocaleString()} songs (${share((C.with_producer || 0) / C.songs)}) have a producer credit so far.` : ""}</p></section>
    <section class="tiles"><div class="tile"><div class="k">Songs covered</div><div class="v">${(C.songs || 0).toLocaleString()}</div><div class="s">3 most-streamed per artist</div></div>
      <div class="tile"><div class="k">Found on MusicBrainz</div><div class="v">${(C.looked_up || 0).toLocaleString()}</div><div class="s">by recording code (ISRC)</div></div>
      <div class="tile"><div class="k">With a producer credit</div><div class="v">${(C.with_producer || 0).toLocaleString()}</div><div class="s">credits are entered by volunteers</div></div></section>
    <section><h2>Producers</h2>${tbl(C.producers, "Producer")}</section>
    <section><h2>Songwriters</h2>${tbl(C.writers, "Songwriter")}
    <p class="note">Credits from <a href="https://musicbrainz.org" target="_blank" rel="noopener">MusicBrainz</a> (open data, CC0). They are partial, so the ranking favours people whose credits are entered: read it as "credited on", not as a complete count. ${grade("B")}</p></section>`;
  if (want) app.querySelector("tr.hl")?.scrollIntoView({ block: "center" });
}

// ---------- State of hip-hop (owner, 2026-10-24, D5): the month's quotable numbers, one permanent page per month
function statePage(ym) {
  nav("state");
  const all = store.data.state || [], st = all.find(x => x.month === ym) || all[0];
  if (!st) { app.innerHTML = `<p class="note">No month stored yet.</p>`; return; }
  const month = new Date(st.month + "-01T00:00:00Z").toLocaleDateString("en", { month: "long", year: "numeric", timeZone: "UTC" });
  const cite = `tventy music, "State of ${GENRE === "country" ? "country" : "hip-hop"}, ${month}", ${SITE_URL}${GDIR()}state/${st.month}/ (data as of ${st.as_of}).`;
  app.innerHTML = `<section><h1>State of hip-hop, ${esc(month)}</h1>
    <p class="sub">The month in hip-hop's top 1,000, in numbers you can quote. ${st.month === all[0]?.month ? `This month's page updates daily until the month ends; then its numbers are fixed. ` : ""}Data as of ${esc(st.as_of)}.</p>
    ${all.length > 1 ? `<div class="chips">${all.map(x => `<a class="chip" href="#/state/${x.month}"${x.month === st.month ? ' aria-current="page"' : ""}>${esc(x.month)}</a>`).join(" ")}</div>` : ""}</section>
    <section class="statgrid">${st.items.map(i => `<a class="stat" href="${esc(i.link)}"><span class="k">${esc(i.label)}</span><b>${esc(i.value)}</b><span class="note">${esc(i.detail)}</span></a>`).join("")}</section>
    <section class="panel"><h2>Quoting these numbers</h2><p>Please cite: <code>${esc(cite)}</code> <button type="button" class="linkbtn" data-share="${esc(cite)}" data-url="${esc(SITE_URL + (GENRE === "hip_hop" ? "" : GENRE + "/") + "state/" + st.month + "/")}">Share</button></p>
    <p class="note">Every figure links to the page it comes from, with its sources and grades. Listener counts are Spotify's public numbers via kworb; money is our estimate, shown as a range on each page; labels come from the ℗ lines of recent releases. <a href="#/method">Method</a></p></section>`;
}

// ---------- Shazam (owner, 2026-10-24, K3): an internal Scout signal, shown only as a badge with a link to Shazam's chart
const shazamBadge = (a, short = false) => { const z = a.shazam; if (!z) return short ? "–" : "";
  // "united-states/st.-louis" -> "St. Louis, United States"; "world" -> "worldwide"
  const place = z.best.place === "world" ? "worldwide" : "in " + z.best.place.split("/").reverse().map(p => p.replace(/-/g, " ").replace(/(^|\s)(\p{Ll})/gu, (m, s, c) => s + c.toUpperCase())).join(", ");
  const best = `#${z.best.rank} ${z.best.kind === "hiphop" ? "hip-hop" : z.best.kind === "country" ? "country" : ""} ${place}`.replace(/\s+/g, " ");
  return `<a class="chip" href="${esc(z.url)}" target="_blank" rel="noopener" title="On ${z.charts} Shazam chart${z.charts > 1 ? "s" : ""} (7 days)${z.cities ? `, ${z.cities} cities` : ""}; best ${esc(best)}">${short ? z.charts : `Shazam: ${z.charts} chart${z.charts > 1 ? "s" : ""}, best ${esc(best)}`}</a>`; };

// ---------- certifications and chart peaks (English Wikipedia discographies, CC BY-SA)
function certsPanel(a) {
  const C = a.cert_detail, S = a.certs;
  if (!C || !S) return "";
  const peaks = C.top.some(w => w.us_peak);
  return `<section class="panel"><h2>Certifications ${grade("B")}</h2>
    <section class="tiles"><div class="tile"><div class="k">Certified releases</div><div class="v">${S.works}</div><div class="s">in ${S.countries} countr${S.countries === 1 ? "y" : "ies"}</div></div>
      ${S.riaa_plat ? `<div class="tile"><div class="k">RIAA Platinum, all releases</div><div class="v">${S.riaa_plat}×</div><div class="s">Diamond counts as 10× (US); guest features included</div></div>`
        : S.main ? `<div class="tile"><div class="k">${esc(S.main.body)}</div><div class="v">${S.main.n}</div><div class="s">certifications, the most of any body</div></div>` : ""}
      ${S.no1 || S.no1_feat ? `<div class="tile"><div class="k">US No. 1s as lead artist</div><div class="v">${S.no1 || "–"}</div><div class="s">Billboard 200 or Hot 100, as listed${S.no1_feat ? `; plus ${S.no1_feat} as a featured guest` : ""}</div></div>` : ""}</section>
    <div class="tablebox"><table class="stack"><thead><tr><th class="l">Release</th><th>Year</th>${peaks ? "<th>US peak</th>" : ""}<th class="l">Certifications</th></tr></thead><tbody>
    ${C.top.map(w => `<tr><td class="l">${esc(w.title)} <span class="note">${esc(w.featured ? `${w.type}, as featured guest` : w.type)}</span></td><td>${esc(w.year || "–")}</td>${peaks ? `<td>${w.us_peak ? "#" + w.us_peak : "–"}</td>` : ""}<td class="l wrap">${w.certs.map(esc).join(", ")}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Most-certified releases first (RIAA multiples, then Diamond over Platinum over Gold for any body). From the artist's discography on <a href="${esc(C.url)}" target="_blank" rel="noopener">${{ fr: "French", de: "German" }[C.lang] || "English"} Wikipedia</a> (CC BY-SA), which cites the certifying bodies (RIAA, BPI, ARIA, Music Canada and others). Wikipedia can lag the bodies' own databases by weeks.</p></section>`;
}

// ---------- awards and nominations (Wikidata, CC0)
function awardsPanel(a) {
  const L = a.award_list;
  if (!L || !(L.wins.length + L.nominations.length)) return "";
  const fams = {};
  for (const e of L.wins) (fams[e.family] = fams[e.family] || { w: 0, n: 0 }).w++;
  for (const e of L.nominations) (fams[e.family] = fams[e.family] || { w: 0, n: 0 }).n++;
  // Wikidata lists wins far more often than nominations: a nomination count below the wins would read as a fact, so hide it
  if (L.nominations.length < L.wins.length) for (const f in fams) fams[f].n = 0;
  const line = e => `<li>${esc(e.award)}${e.work ? `, for <i>${esc(e.work)}</i>` : ""}${e.year ? ` (${esc(e.year)})` : ""}</li>`;
  return `<section class="panel"><h2>Awards ${grade("B")}</h2>
    <div class="chips">${Object.entries(fams).filter(([, v]) => v.w || v.n).sort((x, y) => y[1].w - x[1].w || y[1].n - x[1].n).map(([f, v]) => `<span class="chip">${esc(f)}: ${[v.w ? `at least ${v.w} won` : "", v.n ? `${v.n} nomination${v.n > 1 ? "s" : ""}` : ""].filter(Boolean).join(", ")}</span>`).join(" ")}</div>
    ${L.wins.length ? `<details${L.wins.length <= 6 ? " open" : ""}><summary>At least ${L.wins.length} win${L.wins.length === 1 ? "" : "s"} (Wikidata, incomplete)</summary><ul>${L.wins.map(line).join("")}</ul></details>` : ""}
    ${L.nominations.length ? `<details><summary>${L.nominations.length < L.wins.length ? "Nominations listed (fewer than the wins: Wikidata is incomplete)" : `${L.nominations.length}${L.wins.length ? " more" : ""} nomination${L.nominations.length === 1 ? "" : "s"} listed`}</summary><ul>${L.nominations.map(line).join("")}</ul></details>` : ""}
    <p class="note">As listed on <a href="https://www.wikidata.org/wiki/${esc(L.qid)}" target="_blank" rel="noopener">Wikidata</a> (open data, edited by volunteers). It is not complete: many wins and most nominations are not entered yet, so treat these as a floor, not a total.</p></section>`;
}

function backtestPanel() {
  const B = store.data.backtest;
  if (!B || !B.picks) return "";
  const years = {};
  for (const t of B.tests) { const y = (years[t.date.slice(0, 4)] = years[t.date.slice(0, 4)] || { n: 0, hr: 0, pg: [], rg: [] }); y.n++; y.hr += t.hit_rate; y.pg.push(t.pick_growth); y.rg.push(t.rest_growth); }
  const avg = xs => xs.reduce((a, b) => a + b, 0) / xs.length;
  return `<section class="panel"><h2>Does it work? The back-test</h2>
    <p>Of the artists that would have been Scout's picks (the top fifth of their size band) on ${B.tests.length} dates from ${esc(B.from)} to ${esc(B.to)}, <b>${Math.round(B.hit_rate * 100)}%</b> outgrew the typical artist of their size over the next 90 days (${B.hits} of ${B.picks} picks). Chance is 50%. With Wikipedia attention added (dates since late 2025): <b>${B.hit_rate_with_attention == null ? "–" : Math.round(B.hit_rate_with_attention * 100) + "%"}</b>.</p>
    <p>So far, the signals with an archived history do <b>not</b> pick next quarter's risers: fast listener growth tends to cool off again over the next 90 days. Only listener growth and Wikipedia attention (${Math.round(((store.data.scout_factors.growth?.weight || 0) + (store.data.scout_factors.attention?.weight || 0)) * 100)}% of the weight now; both were cut to 5% after ${GENRE === "hip_hop" ? "this test" : "the <span data-noswap>hip-hop</span> back-test, which found the same"}) have history before our own daily log; the other signals (new-release pull, current share, engagement, chart reach) are back-tested from that log once it is 90 days old, from January 2027.</p>
    <div class="tablebox"><table><thead><tr><th class="l">Year</th><th>Test dates</th><th>Hit rate</th><th>Picks' growth, next 90 days</th><th>Everyone else's</th></tr></thead><tbody>
    ${Object.entries(years).map(([y, v]) => `<tr><td class="l">${y}</td><td>${v.n}</td><td>${Math.round(v.hr / v.n * 100)}%</td><td>${pct(avg(v.pg) * 100)}</td><td>${pct(avg(v.rg) * 100)}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Each date: hip-hop artists under 15m monthly listeners in the archived page then, 90 days before and 90 days after. Growth is the median within each group, averaged over the year's dates. The artists are today's registry, so acts that rose and fell away are missing. ${grade("B")}</p></section>`;
}

// ---------- worth: what the music earns and what it would sell for, for artists
async function worthPage() {
  nav("worth");
  const d = store.data, deals = Object.fromEntries(d.deals.map(x => [x.deal_type, x]));
  const K4 = ["diy", "services", "independent", "major"];  // deal not on record: the range spans all four deal types
  deals.unknown = deals.unknown || { label: "Deal unknown", low: Math.min(...K4.map(k => deals[k].low)), mid: median(K4.map(k => deals[k].mid)), high: Math.max(...K4.map(k => deals[k].high)) };
  const w = ui.worth = ui.worth || { ml: 1000000, deal: "diy", vintage: "auto", pick: "" };
  const picked = w.pick && d.artists.find(a => a.id === w.pick && (a.ml || a.daily));  // no stream figure: nothing to value
  const allL = picked ? (store.rev[picked.id] = store.rev[picked.id] || await detailOf(picked.id).catch(loadFailed))?.lines : null;
  if (picked && !allL) return;  // the artist's file did not load: the error and its retry are shown
  const lines = allL && allL.filter(l => l.group === "Streaming"), pubL = allL && allL.filter(l => l.group === "Publishing");
  const sumL = (k, ls = lines) => ls.reduce((s, l) => s + l.generated[k], 0);
  // below the 500k floor: no listener figure; similar artists are found by daily streams / 0.10 (as the site build's
  // internal size measure), and the box shows "under 500k", never the estimate
  const ml = picked ? (picked.ml ?? (picked.daily ? picked.daily / 0.10 : null)) : w.ml;
  const ladder = [[1.5e6, 0], [3e6, 1], [6e6, 2], [15e6, 3], [Infinity, 4]];
  const bandIx = ml => ladder.findIndex(([m]) => ml < m);
  const peersBand = d.artists.filter(a => a.ml && bandIx(a.ml) === bandIx(ml) && streamingMid(a));
  const perL = peersBand.map(a => streamingMid(a) / a.ml);  // streaming royalties a year per monthly listener
  const q = { low: quantile(perL, 0.25), mid: median(perL), high: quantile(perL, 0.75) };
  const gen = picked && lines.length ? { low: sumL("low"), mid: sumL("mid"), high: sumL("high") } : { low: ml * q.low, mid: ml * q.mid, high: ml * q.high };
  // "auto" with an artist: the build's multiple, blended by the release age of the artist's streams (or by current
  // share when too few songs are dated); otherwise the chosen band's sourced multiple
  const wm = w.vintage === "auto" && picked?.wmult;
  const vint = w.vintage !== "auto" ? w.vintage : wm ? wm[2] : picked ? (picked.cur_share == null ? "mixed" : picked.cur_share >= 0.6 ? "new" : picked.cur_share >= 0.3 ? "mixed" : "evergreen") : "mixed";
  const M = d.multiples.find(m => m.vintage === vint), mlo = wm ? wm[0] : +M.multiple_low, mhi = wm ? wm[1] : +M.multiple_high;
  const ageMix = wm && wm[4] ? Object.entries(wm[4]).filter(([, v]) => v > 0).map(([k, v]) => `${Math.round(v * 100)}% ${k}`).join(", ") : "";
  const dl = deals[w.deal];
  const keep = { low: gen.low * dl.low, mid: gen.mid * dl.mid, high: gen.high * dl.high };
  // an artist in the list: their own publishing lines (radio too, for country), as the Top 100's value; else a quarter
  const pub = picked && pubL.length ? { low: sumL("low", pubL), mid: sumL("mid", pubL), high: sumL("high", pubL) } : { low: gen.low * 0.20, mid: gen.mid * 0.25, high: gen.high * 0.25 };
  const val = r => ({ low: r.low * mlo, mid: r.mid * (mlo + mhi) / 2, high: r.high * mhi });
  const both = { low: val(gen).low + val(pub).low, mid: val(gen).mid + val(pub).mid, high: val(gen).high + val(pub).high };
  const mid = r => !r.high ? "–" : usd(r.low) === usd(r.high) ? usd(r.mid) : `about ${usd(r.mid)}`;  // headline: the mid; the range sits below
  const near = [...d.artists].filter(a => a.ml && streamingMid(a) && a.id !== w.pick).sort((a, b) => Math.abs(Math.log(a.ml / ml)) - Math.abs(Math.log(b.ml / ml))).slice(0, 6);
  const dealOpts = [...K4, "unknown"].map(k => `<option value="${k}"${w.deal === k ? " selected" : ""}>${esc(deals[k].label)} (keeps ${Math.round(deals[k].low * 100)}–${Math.round(deals[k].high * 100)}%)</option>`).join("");
  const box = (k, v, s) => `<div class="tile"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
  app.innerHTML = `${subnav()}<section><h1>What is your music worth?</h1>
    <p class="sub">Enter your monthly listeners, or pick an artist, to see what the music earns in a year at today's pace, what the artist keeps under each kind of deal, and what the income would sell for as a catalog. Ranges, not quotes: grade ${grade("C")}.</p></section>
    <section class="panel"><div class="calc">
      <label>Monthly listeners on Spotify<input id="w-ml" type="number" min="1000" step="50000" value="${picked && picked.floor ? "" : ml}"${picked && picked.floor ? ' placeholder="under 500k"' : ""}${picked ? " disabled" : ""}></label>
      <label>Or an artist in our list<input id="w-pick" list="w-names" placeholder="Type a name" value="${picked ? esc(picked.name) : ""}"><datalist id="w-names">${d.artists.filter(a => a.ml || a.daily).map(a => `<option value="${esc(a.name)}">`).join("")}</datalist></label>
      <label>Deal<select id="w-deal">${dealOpts}</select></label>
      <label>How new is the music<select id="w-vint">${[["auto", "from the age of the artist's songs (or mixed)"], ["new", "mostly new: songs under 3 years old"], ["mixed", "mixed: songs 3–10 years old"], ["evergreen", "evergreen: songs 10+ years old"]].map(([v, l]) => `<option value="${v}"${w.vintage === v ? " selected" : ""}>${l}</option>`).join("")}</select></label>
      ${picked ? `<button type="button" class="btn" id="w-clear">Clear artist</button>` : ""}
    </div></section>
    <section class="tiles">
      ${box("Recording royalties / year", mid(gen), `range ${range(gen)} a year · ${picked ? `${esc(picked.name)}'s measured streams, all platforms` : `artists with similar listeners earn ${usd(q.low)}–${usd(q.high)} per listener a year`}`)}
      ${box("Artist keeps from recordings / year", mid(keep), `range ${range(keep)} a year · ${w.deal === "unknown" ? "deal not on record: the range spans all four deal types" : esc(dl.label)}; streaming only, before manager and tax`)}
      ${box("Songwriting (publishing) / year", mid(pub), `range ${range(pub)} a year · ${picked && pubL.length > 1 ? "streaming publishing plus radio airplay" : "about a quarter of the recording royalties"}, shared by the writers`)}
      ${box("Recordings would sell for", mid(val(gen)), `range ${range(val(gen))} · ${xm(mlo, !!wm && wm[3] !== "current share")}–${xm(mhi, !!wm && wm[3] !== "current share")}× a year's recording royalties (${ageMix ? `streams by song age: ${esc(ageMix)}` : `${esc(vint)} music`})`)}
      ${box("Songs would sell for", mid(val(pub)), `range ${range(val(pub))} · the same multiple on a year's publishing`)}
      ${box("Recordings + songs would sell for", mid(both), `range ${range(both)} · the two above added: the value in the tables below`)}
      ${box("Artist's royalties would sell for", mid(val(keep)), `range ${range(val(keep))} · if the artist sold their share of future recording royalties`)}
    </section>
    ${dealPanel(gen, picked, w)}
    <section class="panel"><h2>Artists with a similar audience</h2>
      <div class="tablebox"><table><thead><tr><th class="l">Artist</th><th class="l">Label</th><th>Monthly listeners</th><th>Current share</th><th>Streaming royalties / yr</th><th>Per listener</th><th>Recordings + songs, value (mid)</th></tr></thead><tbody>
      ${near.map(a => `<tr><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td class="l">${statusShort(a)}</td><td>${mlx(a)}</td><td>${share(a.cur_share)}</td><td>${usd(streamingMid(a))}</td><td>${usd(streamingMid(a) / a.ml)}</td><td>${usd(a.worth_mid)}</td></tr>`).join("")}
      </tbody></table></div>
      <p class="note">Royalties per listener differ with how often fans replay the music and how much of it is on YouTube: the closest peers are the best guide to your own range.</p></section>
    <section class="panel"><h2>How this is worked out</h2><ul>
      <li><b>Royalties</b>: for a typed-in audience, the middle half of what hip-hop artists of that size in our list generate per monthly listener a year (${peersBand.length} artists: ${usd(q.low)}–${usd(q.high)}, median ${usd(q.mid)}), across Spotify, YouTube and the other services. For an artist in our list, their own measured Spotify streams and YouTube views, with the other services estimated from them.</li>
      <li><b>What the artist keeps</b>: ${d.deals.filter(x => x.source).map(x => `${esc(x.label)} ${Math.round(x.low * 100)}–${Math.round(x.high * 100)}% <a href="${esc(x.source)}" target="_blank" rel="noopener">source</a>`).join("; ")}.</li>
      <li><b>Sale value</b>: buyers pay a number of years of income, fewer for new music because its streams fall faster. ${d.multiples.map(m => `${esc(m.vintage)}: ${m.multiple_low}–${m.multiple_high}× (${esc(m.source_note)}) ${grade(m.grade)} <a href="${esc(m.source_url)}" target="_blank" rel="noopener">source</a>`).join("; ")}. The multiples are quoted on a catalog's net income; we apply them to the royalties paid to the rights holders, before the artist's and writers' share and any costs, so treat the values as indicative.</li>
      <li><b>Mid and range</b>: the headline figure is the mid royalties × the middle multiple. The range multiplies the low ends together (low royalties, lowest multiple, smallest deal share) and the high ends together, so it is wide: the mid is the better single guide.</li>
      <li>Not included: touring and merch (see the artist pages), brand deals, advances, and recoupment (an advance is paid back from the artist's share before any royalties reach them).</li></ul></section>
    <section><h2>Top 100 by the sale value of their recordings and songs</h2>${worthTable()}</section>`;
  const set = (k, v) => { w[k] = v; worthPage(); };
  const mlIn = app.querySelector("#w-ml"); mlIn.onchange = () => set("ml", Math.max(1000, +mlIn.value || 0));
  app.querySelector("#w-deal").onchange = e => set("deal", e.target.value);
  app.querySelector("#w-vint").onchange = e => set("vintage", e.target.value);
  app.querySelector("#w-pick").onchange = e => { const a = d.artists.find(x => x.name.toLowerCase() === e.target.value.trim().toLowerCase()); if (a) { w.deal = K4.includes(a.deal_type) ? a.deal_type : "unknown"; set("pick", a.id); } };
  const c = app.querySelector("#w-clear"); if (c) c.onclick = () => set("pick", "");
  bindDeal(w, worthPage);
}
function worthTable() {
  const rows = [...store.data.artists].filter(a => a.worth_mid).sort((a, b) => b.worth_mid - a.worth_mid).slice(0, 100);
  return `<div class="tablebox"><table class="stack"><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Label</th><th>Streaming royalties / yr</th><th>Artist keeps / yr (incl. tours)</th><th>Recordings + songs, value (mid)</th><th>Current share</th></tr></thead><tbody>
    ${rows.map((a, i) => `<tr><td class="l rk">${i + 1}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td class="l">${statusShort(a)}</td><td>${usd(streamingMid(a))}</td><td>${range(a.rev_total)}</td><td>${usd(a.worth_mid)}</td><td>${share(a.cur_share)}</td></tr>`).join("")}
  </tbody></table></div><p class="note">Value (mid) = a year's recording and publishing royalties × the middle of the multiple range for how new the music is. Artist keeps = all income lines on the artist page, including tours where reported.</p>`;
}

// ---------- labels: who owns the hip-hop top 1,000
const GROUP_ORDER = ["Universal Music Group", "Sony Music", "Warner Music Group", "Independent labels", "Self-released", "Not yet known"];
// dark to light on the white page; groups outside the order above (HYBE America in country) get the striped shades
const SHADE = ["#000", "#3b3f46", "#6b7079", "#a3a8b1", "#d3d6db", "repeating-linear-gradient(45deg,#d3d6db 0 3px,#fff 3px 6px)",
  "repeating-linear-gradient(-45deg,#000 0 2px,#fff 2px 5px)", "radial-gradient(#000 1px,#fff 1.5px) 0 0/5px 5px"];
function stack(parts) {
  const tot = parts.reduce((s, [, v]) => s + v, 0) || 1;
  return `<div class="stack">${parts.map(([g, v], i) => `<i style="width:${v / tot * 100}%;background:${SHADE[i]}" title="${esc(g)}: ${Math.round(v / tot * 100)}%"></i>`).join("")}</div>`;
}
function labelsPage() {
  nav("labels");
  const m = store.data.market, G = GROUP_ORDER.filter(g => m.groups[g]).concat(Object.keys(m.groups).filter(g => !GROUP_ORDER.includes(g)));
  const gv = (g, k) => m.groups[g][k];
  const tot = k => G.reduce((s, g) => s + gv(g, k), 0) || 1;
  const majors = G.slice(0, 3).filter(g => m.groups[g]);
  const majShare = k => majors.reduce((s, g) => s + gv(g, k), 0) / (G.filter(g => g !== "Not yet known").reduce((s, g) => s + gv(g, k), 0) || 1);  // of artists whose label is known
  const known = b => G.filter(g => g !== "Not yet known").reduce((s, g) => s + m.groups[g].bands[b], 0) || 1;
  const majBand = b => majors.reduce((s, g) => s + m.groups[g].bands[b], 0) / known(b);
  // the smallest bands together (under 3m): the top 1,000 starts near 1.5m, so the lowest band alone holds few artists
  const majLow = () => majors.reduce((s, g) => s + m.groups[g].bands[0] + m.groups[g].bands[1], 0) / (known(0) + known(1));
  const indies = Object.entries(Object.assign({}, ...G.map(g => m.groups[g].labels))).sort((a, b) => b[1].ml - a[1].ml);
  const byId = Object.fromEntries(store.data.artists.map(a => [a.id, a]));
  app.innerHTML = `${subnav()}<section><h1>Labels: who owns hip-hop's top 1,000</h1>
    <p class="sub">The label behind each artist's recent releases, grouped by the company that owns it. The three majors hold most of the audience at the top; lower down, independent labels and self-released artists take a bigger share: where small labels can still sign talent.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Majors' share of listeners</div><div class="v">${share(majShare("ml"))}</div><div class="s">of the listeners of artists in the list whose label is known (${share(majShare("artists"))} of those artists)${(() => { const og = GENRE === "hip_hop" ? "country" : "hip_hop", od = otherGenre(og); if (!od && !labelsPage.waiting) { labelsPage.waiting = true; loadGenre(og).then(() => { if (/labels$/.test(location.hash)) labelsPage(); }); }
          return od?.majors_share != null ? `; ${share(od.majors_share)} in ${og === "hip_hop" ? "<span data-noswap>hip-hop</span>" : "country"}` : ""; })()}</div></div>
      <div class="tile"><div class="k">Majors, artists 15m+</div><div class="v">${share(majBand(4))}</div><div class="s">of those whose label is known</div></div>
      <div class="tile"><div class="k">Majors, under 3m</div><div class="v">${share(majLow())}</div><div class="s">of those whose label is known</div></div>
      <div class="tile"><div class="k">Self-released</div><div class="v">${m.groups["Self-released"]?.artists || 0}</div><div class="s">artists, ${share((m.groups["Self-released"]?.ml || 0) / (tot("ml") - (m.groups["Not yet known"]?.ml || 0) || 1))} of the listeners of those whose label is known</div></div>
    </section>
    <section class="panel"><h2>Share of the top 1,000</h2>
      <div class="legend">${G.map((g, i) => `<span><i style="background:${SHADE[i]}"></i>${esc(g)}</span>`).join("")}</div>
      ${[["Artists", "artists"], ["Monthly listeners", "ml"], ["Current listeners", "cl"]].map(([l, k]) => `<div class="stackrow"><span>${l}</span>${stack(G.map(g => [g, gv(g, k)]))}</div>`).join("")}
      <h2 style="margin-top:12px">By size (artists, monthly listeners)</h2>
      ${m.band_labels.map((b, i) => `<div class="stackrow"><span>${esc(i === 0 && store.data.artists.some(a => a.floor) ? b + " (including under 500k)" : b.replace(/(\d)-(\d)/, "$1–$2"))} <span class="note">${m.band_totals[i]}</span></span>${stack(G.map(g => [g, m.groups[g].bands[i]]))}</div>`).join("")}
      <div class="tablebox"><table><thead><tr><th class="l">Group</th><th>Artists</th><th>Share of artists</th><th>Monthly listeners</th><th>Share</th><th>Current listeners</th><th>Share</th></tr></thead><tbody>
        ${G.map(g => `<tr><td class="l"><b>${esc(g)}</b></td><td>${gv(g, "artists")}</td><td>${share(gv(g, "artists") / tot("artists"))}</td><td>${count(gv(g, "ml"))}</td><td>${share(gv(g, "ml") / tot("ml"))}</td><td>${count(gv(g, "cl"))}</td><td>${share(gv(g, "cl") / tot("cl"))}</td></tr>`).join("")}
      </tbody></table></div>
      <p class="note">Among artists whose label is known, the majors hold ${share(majBand(4))} of those with 15m+ monthly listeners and ${share(majLow())} of those under 3m. ${m.catalog ? `${m.catalog} catalog acts (no release in two years) are left out. ` : ""}The shares in this table are of all the other artists, those not yet known included, so they run lower than the tiles above; they are rounded and may not add to 100%. Monthly listeners are added up per artist, so a fan of two artists counts twice. "Not yet known": no label read from recent releases yet (waiting for an editor's check). Groups follow the label printed on the last two years of releases (Deezer), checked against recording codes; distribution deals with a major count under that major.</p></section>
    <section class="panel"><h2>Independent labels and distributors in the top 1,000</h2>
      <div class="tablebox"><table><thead><tr><th class="l">Label</th><th>Artists</th><th>Monthly listeners</th></tr></thead><tbody>
      ${indies.map(([l, v]) => `<tr><td class="l">${esc(l)}</td><td>${v.artists}</td><td>${count(v.ml)}</td></tr>`).join("")}</tbody></table></div>
      <p class="note">By the company behind the label: an imprint counts under its owner here, so these rows can be larger than the same name's row in the label list below.</p></section>
    ${alignedFinancials()}${groupsCompare()}${groupsCompare(true)}
    ${labelDirectory()}
    <section><h2>Rosters: the biggest artists in each group</h2>
      ${G.map(g => `<details class="panel"><summary><b>${esc(g)}</b>: ${gv(g, "artists")} artist${gv(g, "artists") === 1 ? "" : "s"}</summary><div class="chips">${m.groups[g].top.map(id => byId[id]).filter(Boolean).map(a => `<a class="chip" href="#/a/${a.id}">${esc(a.name)}${flag(a)} · ${mlx(a)}</a>`).join(" ")}</div></details>`).join("")}</section>`;
  bindDirectory();
}

function collabPanel(a) {
  const C = a.collabs || [];
  if (!C.length) return "";
  const inSite = new Set(store.data.artists.map(x => x.id));
  return `<section class="panel"><h2>Collaborations</h2>
    <div class="tablebox"><table class="stack"><thead><tr><th class="l">With</th><th>Songs</th><th>Their daily streams</th><th class="l">Biggest</th></tr></thead><tbody>
    ${C.map(c => `<tr><td class="l">${inSite.has(c.id) ? `<a href="#/a/${c.id}">${esc(c.name)}</a>` : esc(c.name)}</td><td>${c.songs}</td><td>${count(c.daily)}</td><td class="l wrap">${esc(c.top)}</td></tr>`).join("")}
    </tbody></table></div><p class="note">Songs where one of the two is the lead artist and the other is named in the title (feat. / with), from Spotify's play counts. Featuring a much bigger artist is an early sign labels watch.</p></section>`;
}

// Home: four highlights computed from today's data (no written commentary).
function pulse() {
  const A = store.data.artists, by = (f, xs = A) => xs.filter(x => f(x) != null).sort((a, b) => f(b) - f(a))[0];
  const song = by(a => a.top_fresh?.daily);
  const unsigned = by(a => a.scout?.score, A.filter(isPick));  // not mostly a featured guest (SRNO)
  const riser = by(a => a.chg_pct, A.filter(a => a.ml >= 1e6));
  const reach = by(chartCountries, A.filter(a => a.ml < 15e6));
  const item = (k, a, line) => a ? `<a class="pulse" href="#/a/${a.id}">${pic(a)}<span><span class="k">${k}</span><b>${esc(a.name)}${flag(a)}</b><span class="note">${line}</span></span></a>` : "";
  return `<section class="band"><div class="bandhead"><h2>Right now</h2><a class="btn" href="#/scout">Open the scout list</a></div><div class="pulses">
    ${item("Hottest new song", song, song ? `${esc(song.top_fresh.title)}: ${count(song.top_fresh.daily)} streams a day` : "")}
    ${item("Top unsigned prospect", unsigned, unsigned ? `Scout ${unsigned.scout.score}, ${mlx(unsigned)} monthly listeners` : "")}
    ${item("Biggest riser today, 1m+ listeners", riser, riser ? `${pct(riser.chg_pct)} monthly listeners, now ${count(riser.ml)}` : "")}
    ${item("Widest reach under 15m", reach, reach ? `on the charts in ${chartCountries(reach)} countr${chartCountries(reach) === 1 ? "y" : "ies"} (Spotify or Apple)` : "")}
  </div></section>`;
}

// ---------- compare: two artists side by side
function compare(ids) {
  nav("compare");
  // either genre's artists can be compared ("Morgan Wallen vs Drake"); the other genre's list loads on demand
  const og = GENRE === "hip_hop" ? "country" : "hip_hop", od = otherGenre(og);
  if (!od && !compare.waiting) { compare.waiting = true; loadGenre(og).then(() => { compare.waiting = false; if (location.hash.includes("compare")) compare(ids); }); }
  const d = { ...store.data, artists: [...store.data.artists, ...(od ? od.artists.map(a => ({ ...a, other: og })) : [])] };
  const byId = Object.fromEntries(d.artists.map(a => [a.id, a]));
  const A = [...new Set(ids)].map(id => byId[id]).filter(Boolean).slice(0, 2);  // the same artist twice compares nothing
  const spl = a => a.daily && a.ml ? a.daily / a.ml : null;
  const charts = chartCountries;
  const rows = [
    ["Level", a => a.level?.name, null],
    ["Monthly listeners", a => a.floor ? "under 500k" : a.ml, v => typeof v === "string" ? v : count(v)], ["Current listeners", a => a.cl, count],
    ["Listening on recent releases", a => a.cur_share, share], ["New-release pull (songs ≤ 90 days)", a => a.fresh_share, share],
    ["Scout score", a => a.scout?.score, v => v], ["Streams a day", a => a.daily, count], ["Streams a day per listener", a => spl(a), v => v.toFixed(2)],
    ["YouTube views a day", a => a.yt_daily || a.yt_api_daily, count], ["Deezer fans", a => a.deezer_fans, count], ["Chart countries (Spotify or Apple)", charts, v => v],
    ["Wikipedia, last 3 months vs 9 before", a => a.attention?.trend, trend],
    ["Label", a => a.label_status, (v, a) => statusShort(a)],
    ["Streaming royalties / yr, all services", a => streamingMid(a), usd], ["Artist keeps / year (mid): streaming, plus touring where reported", a => a.rev_total?.mid, (v, a) => `${usd(v)} <span class="note">${a.rev_lines?.touring ? "incl. touring" : "streaming only"}</span>`],
    ["Recordings + songs, sale value (mid)", a => a.worth_mid, usd],
  ];
  const pickBox = i => `<label>Artist ${i + 1}<input data-i="${i}" list="c-names" placeholder="Type a name" value="${A[i] ? esc(A[i].name) : ""}"></label>`;
  app.innerHTML = `${subnav()}<section><h1>Compare artists</h1><p class="sub">Two artists side by side: audience, momentum, label and money. The higher number of each pair is in bold.</p></section>
    <section class="panel"><div class="calc">${pickBox(0)}${pickBox(1)}<datalist id="c-names">${d.artists.map(a => `<option value="${esc(a.name)}">`).join("")}</datalist></div></section>
    ${A.length === 2 ? `<section><div class="tablebox"><table class="cmp"><thead><tr><th class="l"><span class="vh">Measure</span></th>${A.map(a => `<th class="l"><a class="who" href="${a.other ? (a.other === "hip_hop" ? "#/" : "#/" + a.other + "/") : PREFIX()}a/${a.id}"${a.other ? ` data-genre-link="${a.other}"` : ""}>${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></th>`).join("")}</tr></thead><tbody>
      ${rows.map(([l, f, fmt]) => { const v = A.map(f), num = v.every(x => typeof x === "number"), hi = num && v[0] !== v[1] ? (v[0] > v[1] ? 0 : 1) : -1;
        return `<tr><td class="l">${esc(l)}</td>${A.map((a, i) => `<td class="l">${v[i] == null ? "–" : `<span${i === hi ? ' class="hi"' : ""}>${fmt ? fmt(v[i], a) : esc(v[i])}</span>`}</td>`).join("")}</tr>`; }).join("")}
    </tbody></table></div><p class="note">Money lines are estimates (grade C); see each artist's page for the ranges and sources.${A.some(a => a.other) && !A.every(a => a.other) ? " The two are in different genres: the Scout score and level compare each artist with their own genre's list." : ""}</p></section>` : `<p class="note">Pick two artists, or start from one of these: ${(() => { const b = store.data.artists.filter(x => x.scout?.tier === "Breaking").sort((x, y) => y.scout.score - x.scout.score); const t = [...store.data.artists].sort((x, y) => y.ml - x.ml); const top2 = od ? [...od.artists].sort((x, y) => y.ml - x.ml)[0] : null; const pairs = [[t[0], t[1]], b.length > 1 ? [b[0], b[1]] : null, t[2] && b[0] ? [t[2], b[0]] : null, top2 ? [t[0], top2] : null].filter(Boolean); return pairs.map(([x, y]) => `<a href="#/compare/${x.id}/${y.id}">${esc(x.name)} vs ${esc(y.name)}</a>`).join(" · "); })()}.</p>`}`;
  app.querySelectorAll("input[data-i]").forEach(inp => inp.oninput = () => inp.setCustomValidity(""));
  app.querySelectorAll("input[data-i]").forEach(inp => inp.onchange = () => {
    const a = d.artists.find(x => x.name.toLowerCase() === inp.value.trim().toLowerCase());
    if (!a) return;
    if (A.some((x, i) => x.id === a.id && i !== +inp.dataset.i)) { inp.setCustomValidity("Already picked: choose another artist"); inp.reportValidity(); return; }
    const next = A.map(x => x.id); next[+inp.dataset.i] = a.id;
    go("#/compare/" + next.filter(Boolean).join("/"));
  });
}

// ---------- label directory and label snapshot pages
const labelBySlug = s => (store.data.labels || []).find(L => L.slug === s);
const labelOf = a => a.label_name ? (store.data.labels || []).find(L => L.name === a.label_name) : null;
const logo = (name, cls = "logo") => { const l = (store.data.label_logos || {})[name];
  return l ? `<img class="${cls}" src="${esc(l.file)}" alt="${esc(name)} logo" loading="lazy">` : `<span class="${cls} none" aria-hidden="true">${esc(initials(name))}</span>`; };
const labelLink = a => { const L = labelOf(a); return L ? `<a href="#/label/${L.slug}">${esc(L.name)}</a>` : ""; };
function finTable(company) {
  const lc = (company || "").toLowerCase();
  const rows = (store.data.label_financials || []).filter(r => r.company && lc && (r.company.toLowerCase().includes(lc) || lc.includes(r.company.toLowerCase())));
  if (!rows.length) return `<p class="note">No published accounts for ${esc(company)}: a private company or a division that does not report on its own.</p>`;
  const nice = m => m.replace(/_/g, " ").replace(/\bebitda\b/i, "EBITDA").replace(/\boibda\b/i, "OIBDA").replace(/^./, c => c.toUpperCase());
  const money = (v, r) => { const n = +v; if (isNaN(n)) return esc(v); const neg = n < 0 ? "−" : ""; if (r.unit === "percent") return neg + Math.abs(n).toFixed(1) + "%";
    if (r.unit === "millions" || r.unit === "billions") return money2(n * (r.unit === "millions" ? 1e6 : 1e9), r.currency);  // one money format with the statements below
    const sym = ({ EUR: "€", USD: "$", JPY: "¥" })[r.currency] || ""; return `${neg}${sym}${Math.abs(n).toLocaleString("en", { maximumFractionDigits: 1 })}${r.unit === "millions" ? "m" : r.unit === "billions" ? "bn" : ""}`; };
  const facts = rows.filter(r => r.unit === "text");
  const by = {};
  // an empty value is no figure ("" would read as 0: EMPIRE showed "Revenue 0")
  for (const r of rows.filter(r => r.unit !== "text" && r.value !== "" && r.value != null && r.period && !isNaN(+r.value))) (by[r.metric] = by[r.metric] || []).push(r);
  if (!Object.keys(by).length && !facts.length) return `<p class="note">No published accounts for ${esc(company)}: a private company or a division that does not report on its own.</p>`;
  const lines = Object.entries(by).map(([m, rs]) => { rs.sort((x, y) => y.period.localeCompare(x.period)); const [cur, prev] = rs;
    const chg = prev && cur.unit !== "percent" && +prev.value ? (+cur.value / +prev.value - 1) * 100 : null;
    const pp = prev && cur.unit === "percent" ? +cur.value - +prev.value : null;  // a margin moves in percentage points
    const yr = Math.max(...(cur.period.match(/20\d\d/g) || [0]).map(Number)), old = yr && +String(store.data.as_of).slice(0, 4) - yr >= 2;  // flag a figure two or more years old
    return `<tr><td class="l">${esc(nice(m))}</td><td>${money(cur.value, cur)}${old ? `<br><span class="note">${esc(cur.period)}: an older figure</span>` : ""}</td><td>${prev ? money(prev.value, prev) : "–"}</td><td>${chg != null ? pct(chg) : pp != null ? `${pp >= 0 ? "+" : "−"}${Math.abs(pp).toFixed(1)}pp` : "–"}</td><td class="l">${cur.basis === "reported" ? grade("A") : grade("B")} <a href="${esc(cur.source_url)}" target="_blank" rel="noopener" title="${esc(cur.period)}${cur.note ? ": " + esc(cur.note) : ""}">source</a></td></tr>`; });
  const periods = Object.values(by).map(rs => rs[0].period);
  const pyr = p => Math.max(0, ...(p.match(/20\d\d(-\d\d)?/g) || []).map(s => +s.replace("-", ".")));  // "FY2025 (year ended 2025-09-30)" → 2025.09
  const latest = periods.filter(p => !/forecast|pro forma/i.test(p)).sort((a, b) => pyr(b) - pyr(a))[0] || periods[0] || "";
  return `${facts.length ? `<dl class="kv">${facts.map(f => `<dt>${esc(nice(f.metric))}</dt><dd>${esc(f.value)}</dd>`).join("")}</dl>` : ""}
    ${lines.length ? `<div class="tablebox"><table><thead><tr><th class="l">Measure</th><th>Latest</th><th>Year before</th><th>Change</th><th class="l">Basis</th></tr></thead><tbody>${lines.join("")}</tbody></table></div>
    <p class="note">Latest period: ${esc(latest)}. A = the company's own report, B = press-reported. Hover "source" for the exact period and notes.</p>` : ""}`;
}
function labelDirectory() {
  const f = ui.labf = ui.labf || { q: "", group: "all", sort: ["ml", -1] };
  const L = (store.data.labels || []).filter(x => (f.group === "all" || x.parent === f.group) && x.name.toLowerCase().includes(f.q));
  const [sk, sd] = f.sort;
  L.sort((a, b) => ((a[sk] ?? -1) > (b[sk] ?? -1) ? 1 : -1) * sd);
  const parents = [...new Set((store.data.labels || []).map(x => x.parent).filter(Boolean))].sort();
  const cols = [["Artists", "n"], ["Monthly listeners", "ml"], ["Current listeners", "cl"], ["Royalties / yr", "royalties"], ["Rising + Breaking", "rb"], ["Avg scout", "scout_avg"], ["Releases, 2 yrs", "releases_2y"]];
  L.forEach(x => { x.n = x.artists.length; x.rb = x.rising + x.breaking; });
  return `<section class="panel" id="labeldir"><h2>Every label in the top 1,000</h2>
    <div class="filters"><input type="search" id="lab-q" placeholder="Find a label" value="${esc(f.q)}" aria-label="Find a label">
      <label class="sel">Owner <select id="lab-g"><option value="all">all owners</option>${parents.map(p => `<option${f.group === p ? " selected" : ""}>${esc(p)}</option>`).join("")}</select></label></div>
    <div class="tablebox"><table class="stack"><thead><tr><th class="l">Label</th><th class="l">Owner</th>${cols.map(([l, k]) => `<th data-lsort="${k}"${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${l}</th>`).join("")}</tr></thead><tbody>
    ${L.map(x => `<tr><td class="l"><a class="who" href="#/label/${x.slug}">${logo(x.name)}<span>${esc(x.name)}</span></a></td><td class="l">${esc(x.parent || "–")}</td><td>${x.n}</td><td>${count(x.ml)}</td><td>${count(x.cl)}</td><td>${usd(x.royalties)}</td><td>${x.rb}</td><td>${x.scout_avg ?? "–"}</td><td>${x.releases_2y ?? "–"}</td></tr>`).join("") || `<tr><td class="l" colspan="9">No label matches.</td></tr>`}
    </tbody></table></div><p class="note">Labels as printed on the artists' releases of the last two years; an imprint has its own row here, so its owner's row can count fewer artists than the owner's total above. "–" means no figure. Royalties: what the roster's recordings generate a year across streaming services (mid estimate ${grade("C")}), paid to the label before the artists' share.</p></section>`;
}
function bindDirectory() {
  const f = ui.labf, q = app.querySelector("#lab-q");
  if (!q) return;
  q.oninput = () => { f.q = q.value.toLowerCase(); const p = q.selectionStart; labelsPage(); const i = app.querySelector("#lab-q"); i.focus(); i.setSelectionRange(p, p); document.getElementById("labeldir").scrollIntoView(); };
  app.querySelector("#lab-g").onchange = e => { f.group = e.target.value; labelsPage(); document.getElementById("labeldir").scrollIntoView(); };
  app.querySelectorAll("th[data-lsort]").forEach(th => th.onclick = () => { f.sort = [th.dataset.lsort, f.sort[0] === th.dataset.lsort ? -f.sort[1] : -1]; labelsPage(); document.getElementById("labeldir").scrollIntoView(); });
}
function labelPage(s) {
  nav("labels");
  const L = labelBySlug(s);
  if (!L) { app.innerHTML = `<p>Label not found. <a href="#/labels">All labels</a></p>`; return; }
  crumbs([["Labels", "#/labels"], [L.name]]);
  setMeta(`${L.name}: roster, momentum and finances`, `${L.name}${L.parent && L.parent !== L.name ? ", owned by " + L.parent : ""}: artists in hip-hop's top 1,000, how they are performing, and the finances behind them.`);
  const byId = Object.fromEntries(store.data.artists.map(a => [a.id, a]));
  const roster = L.artists.map(id => byId[id]).filter(Boolean);
  const total = store.data.artists.reduce((x, a) => x + (a.second_of ? 0 : a.ml || 0), 0);
  const sister = (store.data.labels || []).filter(x => x.parent === L.parent && x.slug !== L.slug).slice(0, 8);
  const top = [...roster].sort((a, b) => (b.scout?.score ?? -1) - (a.scout?.score ?? -1))[0];
  const own = L.parent && L.parent !== L.name;
  app.innerHTML = `<section class="head labelhead">${logo(L.name, "logo big")}<div><h1>${esc(L.name)}</h1>
      <p class="sub">${L.status === "independent" ? "Independent label" : L.status === "major_distributed" ? "Distributed by a major" : "Major-label imprint"}${own ? ` · owned by <b>${esc(L.parent)}</b>` : ""} · ${roster.length} of hip-hop's top 1,000</p>
      ${own ? `<div class="parentchip">${logo(L.parent, "logo")}<span>Parent company: ${esc(L.parent)}</span></div>` : ""}
      <div class="links" style="margin-top:10px"><a href="#/label/${L.slug}/sheet">One-pager (print / PDF)</a><button type="button" class="linkbtn" id="lab-csv">Roster CSV (${roster.length})</button>${corrLink(L.name, `${SITE_URL}${GDIR()}label/${L.slug}/`)}</div></div></section>
    <section class="tiles">
      <div class="tile"><div class="k">Monthly listeners</div><div class="v">${count(L.ml)}</div><div class="s">${share(L.ml / total)} of the top 1,000, added per artist</div></div>
      <div class="tile"><div class="k">Current listeners</div><div class="v">${count(L.cl)}</div><div class="s">on recent releases</div></div>
      <div class="tile"><div class="k">Roster royalties / year</div><div class="v">${usd(L.royalties)}</div><div class="s">recordings, all streaming, mid ${grade("C")}</div></div>
      <div class="tile"><div class="k">Momentum</div><div class="v">${L.breaking + L.rising}</div><div class="s">${L.breaking} Breaking, ${L.rising} Rising · avg Scout ${L.scout_avg ?? "–"}</div></div>
      <div class="tile"><div class="k">Releases, last 2 years</div><div class="v">${L.releases_2y ?? "–"}</div><div class="s">across artists we track (Deezer)</div></div>
    </section>
    ${top?.scout ? `<section class="panel"><h2>The one to watch</h2><p><a href="#/a/${top.id}"><b>${esc(top.name)}</b></a>${flag(top)}: Scout ${top.scout.score} ${tierChip(top.scout.tier)}, ${mlx(top)} monthly listeners${top.top_fresh ? `, newest hit "${esc(top.top_fresh.title)}" at ${count(top.top_fresh.daily)} streams a day` : ""}.</p></section>` : ""}
    <section><h2>Roster</h2><div class="tablebox"><table><thead><tr><th class="l">Artist</th><th>Monthly listeners</th><th>Current listeners</th><th>Scout</th><th>New-release pull</th><th>Today</th><th>Streaming royalties / yr</th><th class="l">Newest hit</th></tr></thead><tbody>
      ${roster.map(a => `<tr><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td>${mlx(a)}</td><td>${clx(a)}</td><td>${a.scout ? `${a.scout.score} ${a.scout.provisional ? provChip(a.scout) : tierChip(a.scout.tier)}` : "–"}</td><td>${share(a.fresh_share)}</td><td>${pct(a.chg_pct)}</td><td>${usd(a.streaming_mid)}</td><td class="l wrap">${a.top_fresh ? esc(a.top_fresh.title) : `<span class="note">none in 90 days</span>`}</td></tr>`).join("")}
    </tbody></table></div><p class="note">Hip-hop artists in the top 1,000 whose recent releases carry this label. Royalties are paid to the label before the artist's share (see each artist's page); "–" means no measured streams, so that artist adds nothing to the roster total.</p></section>
    <section class="panel"><h2>${esc(L.name)}: finances</h2>${own ? `<p class="note">${esc(L.name)} is part of ${esc(L.parent)} and publishes no accounts of its own. The best public measure of its size is the roster's royalties above.</p>` : finTable(L.name)}</section>
    ${(own ? L.parent : L.name) === "Sony Music" ? sonyMusicPanel() : ""}
    ${healthPanel((store.data.company_of || {})[own ? L.parent : L.name])}
    ${Object.entries(store.data.group_finances || {}).filter(([, F]) => F.uk?.labels.includes(L.name)).map(([c]) => healthPanel(c)).join("")}
    ${own ? `<section class="panel"><h2>${esc(L.parent)}: key reported figures</h2>${finTable(L.parent)}</section>` : ""}
    ${sister.length ? `<section class="panel"><h2>Other ${esc(L.parent)} labels in the top 1,000</h2><div class="chips">${sister.map(x => `<a class="chip" href="#/label/${x.slug}">${esc(x.name)} · ${x.artists.length}</a>`).join(" ")}</div></section>` : ""}
    ${(store.data.label_logos || {})[L.name] ? `<p class="note">Logo: <a href="${esc(store.data.label_logos[L.name].page)}" target="_blank" rel="noopener">Wikimedia Commons</a> (${esc(store.data.label_logos[L.name].licence)}). Trademarks belong to their owners.</p>` : ""}`;
  app.querySelector("#lab-csv").onclick = () => labelCsv(L);
}

// ---------- label groups' financial health (filed statements: SEC XBRL and ESEF annual reports)
const ITEM_LABEL = { revenue: "Revenue", direct_costs: "Cost of revenue", sga: "Selling, general and admin.", da: "Depreciation and amortisation",
  operating_income: "Operating income", interest_expense: "Interest expense", pretax_income: "Profit before tax", income_tax: "Income tax",
  net_income: "Net income", cash: "Cash", current_assets: "Current assets", total_assets: "Total assets", current_liabilities: "Current liabilities",
  total_liabilities: "Total liabilities", long_term_debt: "Long-term debt", short_term_debt: "Short-term debt", total_liabilities_and_equity: "Liabilities and equity",
  equity: "Equity", cfo: "Cash from operations", capex: "Capital expenditure", catalog_purchases: "Catalogue and business purchases",
  cfi: "Cash from investing", dividends_paid: "Dividends paid", cff: "Cash from financing" };
const STMT = { IS: ["revenue", "direct_costs", "sga", "da", "operating_income", "interest_expense", "pretax_income", "income_tax", "net_income"],
  BS: ["cash", "current_assets", "total_assets", "current_liabilities", "long_term_debt", "short_term_debt", "total_liabilities", "equity"],
  CF: ["cfo", "capex", "catalog_purchases", "cfi", "dividends_paid", "cff"] };
const RATIO = { revenue_growth: ["Revenue growth", "pct"], operating_margin: ["Operating margin", "pct"], fcf_margin: ["Free cash flow margin", "pct"],
  leverage: ["Net debt / EBITDA (proxy)", "x"], interest_cover: ["Interest cover", "x"], current_ratio: ["Current ratio", "x"], equity_ratio: ["Equity ratio", "pct"],
  net_debt: ["Net debt", "money"], fcf: ["Free cash flow", "money"] };
const money2 = (v, cur) => v == null ? "–" : `${v < 0 ? "−" : ""}${({ EUR: "€", USD: "$", JPY: "¥", GBP: "£" })[cur] || ""}${count(Math.abs(v)).replace(/\.0(?=[a-z]+$)/, "")}`;  // "€298m", not "€298.0m"
// cash flow: money going out in brackets, as in the filings (payments are tagged as positive amounts)
const OUTFLOW = new Set(["capex", "catalog_purchases", "dividends_paid"]);
const cashCell = (i, v, cur) => v == null ? "–" : OUTFLOW.has(i) || v < 0 ? `(${money2(Math.abs(v), cur)})` : money2(v, cur);
const fmtRatio = (v, kind, cur) => v == null ? "–" : kind === "pct" ? (v < 0 ? "−" : "") + Math.abs(v * 100).toFixed(1) + "%" : kind === "x" ? (v < 0 ? "−" : "") + Math.abs(v).toFixed(1) + "×" : money2(v, cur);  // a true minus sign, as money2
const readingChip = r => r ? `<span class="chip read-${r}">${({ good: "healthy", watch: "watch", weak: "weak" })[r]}</span>` : "";
function healthPanel(company) {
  const F = (store.data.group_finances || {})[company];
  if (!F) return "";
  const cur = F.currency, cols = [...F.years.map(y => ({ ...y, label: "FY " + y.period.slice(0, 7) })), ...F.quarters.map(q => ({ ...q, label: (q.type === "H" ? "H1 to " : "Q to ") + q.period.slice(0, 7) }))];
  const table = (st, title) => { const items = STMT[st].filter(i => cols.some(c => c.values[i] != null)); if (!items.length) return "";
    return `<h3>${title}</h3><div class="tablebox"><table><thead><tr><th class="l"><span class="vh">Line item</span></th>${cols.map(c => `<th${c.type !== "FY" ? ' class="q"' : ""}><a href="${esc(c.source)}" target="_blank" rel="noopener">${esc(c.label)}</a></th>`).join("")}</tr></thead><tbody>
      ${items.map(i => `<tr><td class="l">${esc(ITEM_LABEL[i])}</td>${cols.map(c => `<td${c.type !== "FY" ? ' class="q"' : ""}>${st === "CF" ? cashCell(i, c.values[i], cur) : money2(c.values[i], cur)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>${st === "CF" ? `<p class="note">Brackets: money going out.</p>` : ""}`; };
  const uk = F.uk ? `<p class="note">The UK company, not ${esc(F.uk.group)} worldwide: it runs ${F.uk.labels.length ? esc(F.uk.labels.join(", ")) : "the group's labels"} in the UK (labels named in its accounts, or whose releases carry a UK name). <a href="https://find-and-update.company-information.service.gov.uk/company/${esc(F.uk.number)}" target="_blank" rel="noopener">Companies House ${esc(F.uk.number)}</a>. UK accounts are annual; a blank line is one the accounts do not print (UK subsidiaries often file no cash flow statement).</p>` : "";
  return `<section class="panel"><h2>${esc(company)}: financial health ${grade("A")}</h2>
    ${F.note ? `<p class="note">${esc(F.note)}.</p>` : ""}${uk}
    <div class="healthgrid">${Object.entries(RATIO).filter(([k]) => F.health[k]).map(([k, [l, kind]]) => `<div class="hcell"><span class="k">${esc(l)}</span><b>${fmtRatio(F.health[k].value, kind, cur)}</b>${readingChip(F.health[k].reading)}</div>`).join("")}</div>
    <p class="note">Latest fiscal year (${esc(F.years.at(-1)?.period || "–")}), from the company's filed statements (${esc(F.source_kind)}). Readings are credit-analysis rules of thumb, not ratings; the current-ratio bands are set lower for music groups, whose royalties owed to artists and songwriters sit in current liabilities. Compare the groups with each other rather than with other industries.</p>
    ${table("IS", "Income statement")}${table("BS", "Balance sheet")}${table("CF", "Cash flow")}
    <p class="note">Figures as filed, in ${esc(cur)}. Column headings link to the filings. Shaded columns are interim periods: a quarter (three months) or a half-year (six months) to that date, with the balance sheet at that date. A blank means the company does not tag that line in its XBRL; the full statements are in the filing.</p></section>`;
}
function sonyMusicPanel() {
  const S = store.data.sony_music;
  if (!S?.periods?.length) return "";
  const fy = S.periods.filter(p => p.period_type === "FY" && p.values.sales).slice(-3), q = S.periods.filter(p => p.period_type === "Q" && p.values.sales).slice(-4);
  const cols = [...fy.map(p => ({ ...p, label: "FY to " + p.period_end.slice(0, 7) })), ...q.map(p => ({ ...p, label: "Q to " + p.period_end.slice(0, 7) }))];
  const prev = p => S.periods.find(x => x.period_type === p.period_type && x.period_end === `${+p.period_end.slice(0, 4) - 1}${p.period_end.slice(4)}`);
  const rows = [["recorded_streaming", "Recorded music: streaming"], ["recorded_other", "Recorded music: other"], ["publishing", "Music publishing"], ["visual_media", "Visual media and platform"], ["sales", "Music sales"], ["operating_income", "Operating income"]];
  const yen = v => v == null ? "–" : "¥" + Math.round(v / 1e9).toLocaleString("en") + "bn";
  const growth = p => { const b = prev(p); return b?.values.sales ? pct((p.values.sales / b.values.sales - 1) * 100) : "–"; };
  return `<section class="panel"><h2>Sony Music: the music business on its own ${grade("A")}</h2>
    <p class="note">Sony Group reports Music as one segment. Its results releases split music sales by type; operating income is the segment's.</p>
    <div class="tablebox"><table><thead><tr><th class="l"><span class="vh">Line item</span></th>${cols.map(c => `<th${c.period_type !== "FY" ? ' class="q"' : ""}><a href="${esc(c.source)}" target="_blank" rel="noopener">${esc(c.label)}</a></th>`).join("")}</tr></thead><tbody>
    ${rows.map(([k, l]) => `<tr><td class="l">${k === "sales" || k === "operating_income" ? `<b>${l}</b>` : l}</td>${cols.map(c => `<td${c.period_type !== "FY" ? ' class="q"' : ""}>${yen(c.values[k])}</td>`).join("")}</tr>`).join("")}
    <tr><td class="l">Operating margin</td>${cols.map(c => `<td${c.period_type !== "FY" ? ' class="q"' : ""}>${c.values.sales && c.values.operating_income != null ? (c.values.operating_income / c.values.sales * 100).toFixed(1) + "%" : "–"}</td>`).join("")}</tr>
    <tr><td class="l">Sales growth, year on year</td>${cols.map(c => `<td${c.period_type !== "FY" ? ' class="q"' : ""}>${growth(c)}</td>`).join("")}</tr>
    </tbody></table></div>
    <p class="note">Sony's fiscal year ends on 31 March. Sales are to external customers by product category, as filed with the SEC (Form 6-K); shaded columns are quarters. Column headings link to the releases.</p></section>`;
}
function groupsCompare(uk = false) {
  const G = store.data.group_finances || {};
  // the majors first, then the others (revenues are in different currencies, so no ranking by size)
  const ORDER = [/universal/i, /sony/i, /warner/i, /bertelsmann|bmg/i, /believe/i, /reservoir/i], oi = n => (i => i < 0 ? 99 : i)(ORDER.findIndex(re => re.test(n)));
  const names = Object.keys(G).filter(n => !!G[n].uk === uk).sort((a, b) => oi(a) - oi(b));
  if (!names.length) return "";
  const newest = names.map(n => G[n].years.at(-1)?.period || "").sort().at(-1);
  const stale = p => p && newest && (new Date(newest) - new Date(p)) / 864e5 > 270;  // a fiscal year or more behind the newest column
  return `<section class="panel"><h2>${uk ? "UK record companies'" : "Label groups'"} financial health, side by side ${grade("A")}</h2><div class="tablebox"><table><thead><tr><th class="l">Measure</th>${names.map(n => `<th>${esc(n)}</th>`).join("")}</tr></thead><tbody>
    <tr><td class="l">Latest fiscal year</td>${names.map(n => { const p = G[n].years.at(-1)?.period; return `<td>${esc(p || "–")}${stale(p) ? `<br><span class="note">an older year than the others</span>` : ""}</td>`; }).join("")}</tr>
    <tr><td class="l">Revenue</td>${names.map(n => `<td>${money2(G[n].years.at(-1)?.values.revenue, G[n].currency)}</td>`).join("")}</tr>
    ${Object.entries(RATIO).map(([k, [l, kind]]) => `<tr><td class="l">${esc(l)}</td>${names.map(n => { const h = G[n].health[k]; return `<td>${h ? fmtRatio(h.value, kind, G[n].currency) + " " + readingChip(h.reading) : "–"}</td>`; }).join("")}</tr>`).join("")}
  </tbody></table></div><p class="note">${uk ? "Each company's statutory accounts at Companies House: the UK business only, where the groups' UK labels sign and market artists. A label page shows its UK company when the accounts name the label or its releases carry a UK name (\"Atlantic Records UK\")." : `Sony Group is the whole group (games, pictures, music, electronics). Bertelsmann (BMG's owner) files no machine-readable accounts, so its figures are read from its annual report PDFs; private labels (EMPIRE, Concord before the BMG merger) publish none.`}</p></section>`;
}

// ---------- artist summary card: level, scout score, worth, attention
const midRange = r => !r || !r.high ? `<span class="note">not estimated (no measured streams)</span>`  // no zeros shown as a value
  : usd(r.low) === usd(r.high) ? usd(r.mid) : `about ${usd(r.mid)}<br><span class="note">${range(r)}</span>`;
function summaryCard(a, rev) {
  const sc = a.scout, wo = rev.artist?.worth || a.worth, att = a.attention_series;
  return `<section class="card">
    <div class="cardcol"><h2>Level</h2><div class="big">${esc(a.level?.name || "–")}</div>
      <div class="chips">${(a.level?.badges || []).map(b => `<span class="chip badge">${esc(b)}</span>`).join(" ") || `<span class="note">no badges yet</span>`}</div>
      <p class="note"><span class="def" title="Rookie under 5m monthly listeners (Established if active 15+ years), Rising star 5m+, Headliner 15m+, Icon 40m+">How levels work</span></p></div>
    <div class="cardcol"><h2>Scout score</h2>${sc ? `<div class="big">${sc.score} ${sc.provisional ? provChip(sc) : tierChip(sc.tier)}</div><p class="note">${sc.band.startsWith("under 500k") ? "against artists below 500k monthly listeners (sized by streams a day)" : `against artists with ${esc(sc.band.replace("-", "–"))} monthly listeners`}${a.label_status === "catalog" ? ". Catalog act: the score tracks momentum on new music, so read it lightly here" : ""}</p>${sc.tier && a.top_fresh?.id ? `<p class="hear">${playBtn(a)}<span>Newest hit: <b>${esc(a.top_fresh.title)}</b></span></p>` : ""}${sc.tier && a.video ? `<p class="hear">${videoBtn(a)}<span>Video (${esc(a.video.why)}): <b>${esc(a.video.title)}</b></span></p>` : ""}${factorBars(sc)}` : `<p class="note">Not enough signals yet.</p>`}</div>
    <div class="cardcol"><h2>Worth ${grade("C")}</h2>
      <dl class="kv"><dt>Artist keeps / year<br><span class="note">${(rev.lines || []).some(l => l.group === "Live") ? "streaming and touring" : "streaming; no tour in 12 months"}</span></dt><dd>${(rev.artist_total || a.rev_total)?.high ? midRange(rev.artist_total || a.rev_total) : `<span class="note">not estimated</span>`}${rev.lines?.length && !rev.lines.some(l => l.key === "youtube") ? `<br><span class="note">excludes YouTube (not measured)</span>` : ""}</dd>
      ${wo ? `<dt>Recordings would sell for</dt><dd>${midRange(wo.recordings)}</dd><dt>Artist's streaming royalties, valued</dt><dd>${midRange(wo.artist_royalties)}</dd><dt>Songwriting would sell for</dt><dd>${midRange(wo.publishing)}</dd>` : ""}</dl>
      ${wo?.recordings?.high ? `<p class="note">Values cover streaming and songwriting royalties only, not touring or merch: ${wo.age_mix ? `weighting each age band's multiple by the streams on songs of that age (${Object.entries(wo.age_mix).filter(([, v]) => v > 0).map(([k, v]) => `${Math.round(v * 100)}% ${k}`).join(", ")})` : `${esc(wo.vintage)} music`}, it sells for ${xm(wo.multiple[0], !!wo.age_mix)}–${xm(wo.multiple[1], !!wo.age_mix)}× a year's royalties. The low end is the low royalty estimate × ${wo.multiple[0]}, the high end the high estimate × ${wo.multiple[1]}, so the range is wide; "about" is the mid. <a href="#/worth">How</a></p>` : ""}
      <h2 style="margin-top:10px">Wikipedia attention</h2>
      ${att ? `<div class="sparkrow">${sparkline(att.views)}<span>${trend(a.attention?.trend)} <span class="note">last 3 months against the 9 before</span></span></div><p class="note">Monthly English Wikipedia page views since ${esc(att.start)}.</p>` : `<p class="note">No English Wikipedia article linked.</p>`}
    </div></section>`;
}

// ---------- catalog screener (investors, 2026-10-26): filter catalogs by sale value, age of the music, royalties and
// owner; CSV with the ranges, multiples and grade. Everything comes from index.json (worth_range from src/site_build.py).
SECTION.screener = "money"; SECTION.sheet = "artists"; SECTION.quality = "about";
SUBNAV.money.splice(1, 0, ["screener", "#/screener", "Catalog screener"]);
const VALUE_BANDS = [["any", "any value", 0, Infinity], ["u10", "under $10m", 0, 1e7], ["10-50", "$10m–50m", 1e7, 5e7], ["50-250", "$50m–250m", 5e7, 2.5e8], ["250+", "$250m and more", 2.5e8, Infinity]];
const AGE_MIX = { any: ["any age mix", () => true], evergreen: ["mostly evergreen (50%+ of streams on songs 10+ years old)", a => (a.age_profile?.evergreen ?? 0) >= 0.5],
  mixed: ["mostly 3–10 years old (50%+)", a => (a.age_profile?.mixed ?? 0) >= 0.5], new: ["mostly new (50%+ on songs under 3 years old)", a => (a.age_profile?.new ?? 0) >= 0.5] };
const OWNERS = { any: ["any owner", () => true], notmajor: ["not with a major (indie label or self-released)", a => ["independent", "self_released"].includes(a.label_status)],
  major: ["major label or major's distribution", a => ["major", "major_distributed"].includes(a.label_status)], independent: ["independent label", a => a.label_status === "independent"],
  self_released: ["self-released", a => a.label_status === "self_released"], catalog: ["catalog (no release in 2 years)", a => a.label_status === "catalog"], unknown: ["not yet classified", a => !a.label_status || a.label_status === "unknown"] };
const ROYALTY_MIN = [["0", "any royalties"], ["1e6", "$1m+ a year"], ["5e6", "$5m+ a year"], ["2e7", "$20m+ a year"]];
// share of streams by the age of the songs, as a small bar (new / mixed / evergreen); title gives the percentages
// a band with no streams is left out of age_profile: read it as 0
const ageOf = a => a.age_profile ? { new: a.age_profile.new || 0, mixed: a.age_profile.mixed || 0, evergreen: a.age_profile.evergreen || 0, coverage: a.age_profile.coverage } : null;
const ageBar = a => { const p = ageOf(a); if (!p || !(p.new + p.mixed + p.evergreen)) return `<span class="note">not dated</span>`;
  const t = `${Math.round(p.new * 100)}% new, ${Math.round(p.mixed * 100)}% 3–10 years, ${Math.round(p.evergreen * 100)}% 10+ years`;
  return `<span class="agebar" role="img" aria-label="${t}" title="${t}"><i style="width:${p.new * 100}%"></i><i style="width:${p.mixed * 100}%"></i><i style="width:${p.evergreen * 100}%"></i></span><span class="note"> ${Math.round(p.evergreen * 100)}% 10+ yrs</span>`; };
const valRange = a => a.worth_range ? `<b>about ${usd(a.worth_mid)}</b><br><span class="note">${range({ low: a.worth_range[0], high: a.worth_range[1] })}</span>` : usd(a.worth_mid);
HOW.screener = () => [["Recordings + songs, value", "a year's streaming and songwriting royalties at today's pace × a sale multiple; the mid is the headline, the range below it", "filters and sorts"],
  ["Sale multiple", "years of royalties a buyer pays: each age band's sourced multiple, weighted by the streams on songs of that age", "input"],
  ["Age mix", "share of the artist's daily streams on songs under 3, 3–10 and 10+ years old (release dates from Deezer and MusicBrainz)", "filter"],
  ["Streaming royalties / year", "royalties generated on all services before anyone's cut (Spotify and YouTube measured, the rest estimated from them)", "filter"]];
function screenerPage() {
  nav("screener");
  crumbs([["Money", "#/worth"], ["Catalog screener"]]);
  setMeta("Hip-hop catalog screener: sale values by age, royalties and owner", "Screen the hip-hop top 1,000 as catalogs: estimated sale value ranges, the age of the music, royalties a year and who owns the recordings. Export to CSV.");
  const f = ui.screen = ui.screen || { value: "any", age: "any", owner: "any", roy: "0", country: "all", sort: ["value", -1] };
  const all = store.data.artists.filter(a => a.worth_mid);
  const vb = VALUE_BANDS.find(b => b[0] === f.value) || VALUE_BANDS[0];
  const rows0 = all.filter(a => a.worth_mid >= vb[2] && a.worth_mid < vb[3] && AGE_MIX[f.age][1](a) && OWNERS[f.owner][1](a)
    && (a.streaming_mid || 0) >= +f.roy && (f.country === "all" || placesOf(a).includes(f.country)));
  const val = (a, k) => ({ value: a.worth_mid, roy: a.streaming_mid, keep: a.rev_total?.mid, mult: a.wmult ? (a.wmult[0] + a.wmult[1]) / 2 : null,
    ever: a.age_profile?.evergreen, nw: a.age_profile?.new, ml: a.ml ?? (a.daily ? a.daily / 10 : null), rel: a.latest_release ? Date.parse(a.latest_release) : null })[k];
  const [sk, sd] = f.sort;
  const rows = rows0.sort((a, b) => { const x = val(a, sk), y = val(b, sk); return x == null ? (y == null ? 0 : 1) : y == null ? -1 : (x - y) * sd; });  // blanks last
  const countries = [...new Set(all.flatMap(placesOf))].sort();
  const sum = k => rows.reduce((s, a) => s + (k === "mid" ? a.worth_mid : a.worth_range ? a.worth_range[k === "low" ? 0 : 1] : 0), 0);
  const medMult = median(rows.filter(a => a.wmult).map(a => (a.wmult[0] + a.wmult[1]) / 2));
  const ever = rows.filter(a => (a.age_profile?.evergreen ?? 0) >= 0.5).length, notMajor = rows.filter(OWNERS.notmajor[1]).length;
  const sel = (key, opts) => `<label class="sel">${opts.label}<select data-sf="${key}">${opts.list.map(([v, l]) => `<option value="${esc(v)}"${f[key] === v ? " selected" : ""}>${esc(l)}</option>`).join("")}</select></label>`;
  const th = (l, k, cls = "") => `<th data-scr="${k}"${cls ? ` class="${cls}"` : ""}${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}><span${defn(l)}>${esc(l)}</span></th>`;
  const box = (k, v, s) => `<div class="tile"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
  app.innerHTML = `${subnav()}<section><h1>Catalog screener</h1>
    <p class="sub">The hip-hop top 1,000 seen as catalogs: what each artist's recordings and songs would sell for, how old the music earning it is, the royalties a year and who owns the recordings. Filter, sort and export a shortlist. Values are our estimates ${grade("C")}: a first screen before a data room, not a valuation.</p></section>
    <section class="tiles">
      ${box("Catalogs matching", rows.length.toLocaleString(), `of ${all.length.toLocaleString()} with a value estimate`)}
      ${box("Combined value (mid)", rows.length ? usd(sum("mid")) : "–", rows.length ? `range ${range({ low: sum("low"), high: sum("high") })}; summed estimates` : "no catalog matches")}
      ${box("Median multiple", medMult ? xm(medMult) + "×" : "–", "years of royalties a buyer pays, mid of each artist's range")}
      ${box("Mostly evergreen", ever.toLocaleString(), "50%+ of streams on songs 10+ years old: the slowest decay")}
      ${box("Not with a major", notMajor.toLocaleString(), "independent label or self-released, on the last two years' releases")}
    </section>
    <section class="filters">
      ${sel("value", { label: "Value", list: VALUE_BANDS.map(b => [b[0], b[1]]) })}
      ${sel("age", { label: "Age of the music", list: Object.entries(AGE_MIX).map(([k, v]) => [k, v[0]]) })}
      ${sel("owner", { label: "Owner", list: Object.entries(OWNERS).map(([k, v]) => [k, v[0]]) })}
      ${sel("roy", { label: "Royalties", list: ROYALTY_MIN })}
      ${sel("country", { label: "Country", list: [["all", "all countries"], ...countries.map(c => [c, c])] })}
      <button type="button" class="btn" id="scr-csv">Download CSV (${rows.length})</button>
      <button type="button" class="btn" id="scr-reset">Reset</button>${linkBtn()}
    </section>
    <section><div class="tablebox"><table class="stack screener"><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Owner</th>${th("Recordings + songs, value", "value")}${th("Multiple", "mult")}<th class="l">Age mix</th>${th("Streaming royalties / yr", "roy")}${th("Monthly listeners", "ml")}</tr></thead><tbody>
      ${rows.slice(0, f.all ? rows.length : 100).map((a, i) => `<tr><td class="l rk">${i + 1}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td class="l wrap">${statusShort(a)}</td>
        <td>${valRange(a)}</td><td title="${a.wmult?.[3] === "current share" ? "Too few songs dated: the multiple follows the share of listening on recent releases" : "Weighted by the release age of the streams"}">${a.wmult ? `${xm(a.wmult[0], a.wmult[3] !== "current share")}–${xm(a.wmult[1], a.wmult[3] !== "current share")}×${a.wmult[3] === "current share" ? "*" : ""}` : "–"}</td><td class="l">${ageBar(a)}</td>
        <td>${usd(a.streaming_mid)}${a.rev_total?.high ? `<br><span class="note" title="All income lines on the artist page under the deal assumed, including reported tours">artist keeps <span style="white-space:nowrap">${range(a.rev_total)}</span></span>` : ""}</td><td>${mlx(a)}${a.latest_release ? `<br><span class="note">latest release <span style="white-space:nowrap">${esc(a.latest_release)}</span></span>` : ""}</td></tr>`).join("") || `<tr><td class="l" colspan="8">No catalog matches these filters.</td></tr>`}
    </tbody></table></div>
    ${!f.all && rows.length > 100 ? `<p class="more"><button type="button" class="btn" id="scr-all">Show all ${rows.length}</button></p>` : ""}
    <p class="note">Click a column to sort; blanks sort last. * multiple set by the share of listening on recent releases, because under half of the streams are on dated songs. Monthly listeners below the 500k public floor (country) sort by streams a day.</p></section>
    <section class="panel"><h2>How this works</h2><ul>
      <li><b>Value</b> ${grade("C")}: a year's streaming and songwriting royalties at today's pace × a sale multiple. The low end multiplies the low royalty estimate by the lowest multiple, the high end the high estimate by the highest, so ranges are wide; "about" is the mid. Touring, merch, brand deals and costs are not in it, and the multiples are quoted on a catalog's net income while we apply them to royalties before the artist's and writers' share: treat values as indicative.</li>
      <li><b>Multiples</b>: ${store.data.multiples.map(m => `${esc(m.vintage)} ${m.multiple_low}–${m.multiple_high}× ${grade(m.grade)} <a href="${esc(m.source_url)}" target="_blank" rel="noopener">source</a>`).join("; ")}. Each artist's multiple weights these by the streams on songs of each age (under 3, 3–10, 10+ years); the band edges are our split.</li>
      <li><b>Royalties</b> ${grade("C")}: Spotify streams (kworb.net, from Spotify's public play counts) and YouTube views where measured, with the other services estimated from Spotify; rates from <code>registry/rates.csv</code> (Spotify's middle figure ${grade("B")}).</li>
      <li><b>Owner</b>: the label on the artist's releases of the last two years (Deezer), placed with its owner and checked against the recordings' registrant codes. It says who releases the music now, not who owns older masters: a catalog can sit with an earlier label. ${store.data.quality ? `${(store.data.quality.queues.find(q => q.file.includes("label")) || {}).open ?? 0} label cases are in the review queue (<a href="#/quality">Data quality</a>).` : ""}</li>
      <li>Data as of ${esc(store.data.as_of)}. Method in full: <a href="#/method">Method</a>; one artist's figures: <a href="#/worth">What is it worth?</a></li></ul></section>`;
  app.querySelectorAll("select[data-sf]").forEach(s => s.onchange = () => { f[s.dataset.sf] = s.value; f.all = false; screenerPage(); });
  app.querySelectorAll("th[data-scr]").forEach(t => t.onclick = () => { f.sort = [t.dataset.scr, sk === t.dataset.scr ? -sd : -1]; screenerPage(); });
  app.querySelector("#scr-all")?.addEventListener("click", () => { f.all = true; screenerPage(); });
  app.querySelector("#scr-reset").onclick = () => { ui.screen = null; screenerPage(); };
  app.querySelector("#scr-csv").onclick = () => download(`tventy-music-${GENRE === "country" ? "country" : "hip-hop"}-catalog-screener.csv`, [["name", "spotify_url", "owner_status", "label", "label_group", "country", "value_low_usd", "value_mid_usd", "value_high_usd", "multiple_low", "multiple_high", "multiple_basis", "share_streams_new", "share_streams_3_10y", "share_streams_10y_plus", "share_streams_dated", "streaming_royalties_mid_usd_year", "artist_keeps_low_usd_year", "artist_keeps_high_usd_year", "monthly_listeners", "latest_release", "grade", "data_as_of", "note"],
    ...rows.map(a => [a.name, `https://open.spotify.com/artist/${a.id}`, statusWord(a), a.label_name || "", a.label_owner || "", a.country || "", a.worth_range?.[0] ?? "", a.worth_mid, a.worth_range?.[1] ?? "", a.wmult?.[0] ?? "", a.wmult?.[1] ?? "", a.wmult?.[3] ?? "", ageOf(a)?.new ?? "", ageOf(a)?.mixed ?? "", ageOf(a)?.evergreen ?? "", ageOf(a)?.coverage ?? "", a.streaming_mid ?? "", a.rev_total?.low ?? "", a.rev_total?.high ?? "", a.floor ? "under 500k" : a.ml ?? "", a.latest_release || "", "C (estimate)", store.data.as_of, "indicative estimate, not a valuation; tventy music"])]);
  syncScreen("screener");
}

// ---------- artist one-pager (A&R and investors, 2026-10-26): the key facts on one printable page, every figure with
// its source, method and grade; the browser's print dialog saves it as a PDF
async function sheetPage(id) {
  nav("sheet");
  const base = store.data.artists.find(x => x.id === id);
  if (!base) { app.innerHTML = `<p>Artist not found. <a href="#/">Back to the top list</a></p>`; return; }
  const rev = store.rev[id] = store.rev[id] || await detailOf(id);
  const a = { ...base, ...rev.artist }, wo = rev.artist?.worth;
  crumbs([["Artists", "#/"], [a.name, `#/a/${a.id}`], ["One-pager"]]);
  setMeta(`${a.name}: one-pager`, `${a.name} on one page: audience, label, earnings and catalog value ranges, Scout score, with sources and grades.`);
  const L = labelOf(a), sum = (ls, k, f = "generated") => ls.reduce((s, l) => s + (l[f]?.[k] || 0), 0);
  const st = rev.lines.filter(l => l.group === "Streaming"), other = rev.lines.filter(l => l.group !== "Streaming");
  const stR = f => ({ low: sum(st, "low", f), mid: sum(st, "mid", f), high: sum(st, "high", f) });
  const row = (k, v, src) => `<tr><td class="l">${k}</td><td>${v}</td><td class="l note">${src}</td></tr>`;
  const kworb = `kworb.net, measured${a.streams_date ? `, ${esc(a.streams_date)}` : ""}`;
  const pageUrl = a.slug ? `${SITE_URL}${GENRE === "country" ? "country/" : ""}a/${a.slug}/` : `${SITE_URL}${PREFIX()}a/${a.id}`;
  app.innerHTML = `<section class="sheet">
    <div class="sheethead">${pic(a, true)}<div><h1>${esc(a.name)} ${flag(a)}</h1>
      <p class="sub">${a.cl_rank ? `#${a.cl_rank.toLocaleString()} by current listeners · ` : ""}#${a.rank.toLocaleString()} in hip-hop by ${a.floor === "streams" ? "streams a day" : a.floor ? "Deezer's order" : "monthly listeners"}${a.country ? ` · ${esc(a.country)}` : ""}${a.since ? ` · active since ${esc(a.since)}` : ""}${a.level?.name ? ` · level: ${esc(a.level.name)}` : ""}</p>
      ${a.about ? `<p class="about">${esc(a.about.text)}${a.about.source === "wikipedia" ? ` <span class="note">(Wikipedia, CC BY-SA)</span>` : ""}</p>` : ""}
      <p class="note">tventy music one-pager · data as of ${esc(store.data.as_of)} · ${esc(pageUrl)}</p></div></div>
    <div class="noprint links"><button type="button" class="btn" id="sheet-print">Print or save as PDF</button><a href="#/a/${a.id}">Full artist page</a><a href="#/compare/${a.id}">Compare with…</a></div>
    <div class="sheetgrid">
      <div class="panel"><h2>Audience</h2><table class="sheettab"><tbody>
        ${row("Monthly listeners", mlx(a), a.floor ? "below Spotify's public 500k floor" : `Spotify's public count via kworb.net, measured, ${esc(store.data.as_of)}`)}
        ${row("Current listeners", a.cl != null ? clx(a) : "–", a.floor ? "no listener count below 500k on Spotify" : a.cur_share != null ? `${share(a.cur_share)} of listening on recent releases; our measure` : "release dates missing")}
        ${row("Spotify streams, all time", count(a.streams), a.daily != null ? `${count(a.daily)} a day; ${kworb}` : "not measured")}
        ${row("YouTube views", count(a.yt_total), a.yt_daily ? `${count(a.yt_daily)} a day; kworb.net, measured` : "not measured")}
        ${row("Deezer fans", count(a.deezer_fans), "Deezer, measured")}
        ${row("Chart countries", chartCountries(a) || "–", "Spotify weekly top 200 or Apple Music daily top 100")}
      </tbody></table></div>
      <div class="panel"><h2>Label and deal</h2><table class="sheettab"><tbody>
        ${row("Status", esc(statusWord(a)), a.label_override ? "checked by our editors" : "from the label on the last two years' releases (Deezer)")}
        ${row("Label", L ? esc(L.name) : esc(a.label_name || "–"), a.label_basis ? `latest: ${lname(a.label_basis.label)} (${esc(a.label_basis.date)})` : "")}
        ${row("Owner", esc(a.label_owner && a.label_owner !== "the artist's own name" ? a.label_owner : a.label_status === "self_released" ? "the artist" : (L?.parent || "–")), "label → owner, sourced in the label registry")}
        ${row("Deal assumed for money", a.money ? esc(a.money.deal_label) : `<span class="note">none: no money estimate</span>`, "by label status; real terms are rarely public")}
      </tbody></table></div>
      <div class="panel"><h2>Earnings per year ${grade("C")}</h2><table class="sheettab"><tbody>
        ${st.length ? row("Streaming royalties, all services", range(stR("generated")), "generated, before anyone's cut; Spotify (and YouTube where measured) measured, others estimated") : ""}
        ${st.length ? row("Artist's slice of streaming", range(stR("artist")), "under the deal assumed, before manager and tax") : ""}
        ${other.map(l => row(esc(l.label), `${range(l.generated)}${l.artist ? `<br><span class="note">artist: ${range(l.artist)}</span>` : ""}`, `${grade(l.grade)} ${esc((l.basis || "").slice(0, 110))}${(l.basis || "").length > 110 ? "…" : ""}`)).join("")}
        ${row("<b>Artist keeps, total</b>", `<b>${range(rev.artist_total || a.rev_total)}</b>`, (rev.lines || []).some(l => l.group === "Live") ? "streaming, songwriting and reported touring" : "no tour reported in 12 months")}
      </tbody></table></div>
      <div class="panel"><h2>Catalog value ${grade("C")}</h2>${wo?.recordings?.high ? `<table class="sheettab"><tbody>
        ${row("Recordings", range(wo.recordings), `about ${usd(wo.recordings.mid)}`)}
        ${row("Songs (publishing)", range(wo.publishing), `about ${usd(wo.publishing.mid)}`)}
        ${row("Recordings + songs", range({ low: wo.recordings.low + wo.publishing.low, high: wo.recordings.high + wo.publishing.high }), `about ${usd(a.worth_mid)}`)}
        ${row("Multiple", `${xm(wo.multiple[0], !!wo.age_mix)}–${xm(wo.multiple[1], !!wo.age_mix)}×`, wo.age_mix ? `streams by song age: ${Object.entries(wo.age_mix).filter(([, v]) => v > 0).map(([k, v]) => `${Math.round(v * 100)}% ${k}`).join(", ")}` : `${esc(wo.vintage)} music, by current share`)}
      </tbody></table><p class="note">A year's streaming and songwriting royalties × sourced sale multiples by age of the music; indicative, not a valuation. Touring and merch not included.</p>` : `<p class="note">Not estimated: no measured streams.</p>`}</div>
      <div class="panel"><h2>Scout ${a.scout ? `${a.scout.score} / 100 ${a.scout.provisional ? provChip(a.scout) : tierChip(a.scout.tier)}` : ""}</h2>${a.scout ? `<p class="note">${a.scout.provisional ? `Provisional: on ${Math.round((a.scout.weight || 0) * 100)}% of the signals by weight, so no tier. ` : ""}${a.scout.band.startsWith("under 500k") ? "Against artists below 500k monthly listeners" : `Against artists with ${esc(a.scout.band.replace("-", "–"))} monthly listeners`}; each signal a percentile, 0–100. A pointer, not a prediction.</p>
        <table class="sheettab"><tbody>${Object.entries(store.data.scout_factors).map(([k, x]) => row(esc(x.label.split(":")[0]), a.scout.factors[k] ?? "–", `weight ${Math.round(x.weight * 100)}%`)).join("")}</tbody></table>
        ${a.top_fresh ? `<p class="note">Newest hit: ${esc(a.top_fresh.title)}, ${count(a.top_fresh.daily)} streams a day, out ${esc(a.top_fresh.released)}.</p>` : ""}` : `<p class="note">Not enough signals to score.</p>`}</div>
      <div class="panel"><h2>Recognition</h2><table class="sheettab"><tbody>
        ${row("Certifications", a.certs ? `${a.certs.works.toLocaleString()} works` : "–", a.certs ? `${a.certs.riaa_plat ? `${a.certs.riaa_plat.toLocaleString()}× RIAA platinum; ` : ""}${a.certs.no1 ? `${a.certs.no1} US No. 1s as lead` : ""}; Wikipedia discographies` : "none listed")}
        ${row("Awards", a.awards?.wins ? `at least ${a.awards.wins} win${a.awards.wins === 1 ? "" : "s"}${a.awards.grammys ? `<br><span class="note">incl. ${a.awards.grammys} Grammy${a.awards.grammys === 1 ? "" : "s"}</span>` : ""}` : a.awards?.noms ? `at least ${a.awards.noms} nomination${a.awards.noms === 1 ? "" : "s"}` : "–", "as listed on Wikidata, incomplete: a floor, not a total")}
        ${row("Wikipedia attention", trend(a.attention?.trend), "page views, last 3 months against the 9 before")}
      </tbody></table></div>
    </div>
    <div class="panel sheetfoot"><h2>Sources and grades</h2><p class="note">Grades: <b>A</b> primary (filings, the platform's own disclosure), <b>B</b> reputable secondary, <b>C</b> our estimate, always a range. Measured: Spotify's public counts via kworb.net, Deezer, kworb's YouTube pages. Estimated: every money figure, from measured streams × platform rates (registry/rates.csv) × deal shares (registry/deal_shares.csv) and sale multiples (registry/catalog_multiples.csv). Labels: Deezer release labels, Wikidata, MusicBrainz and the recordings' registrant codes. Corrections: hello@tventy.se. Method: ${esc(SITE_URL + PREFIX())}method · data quality: ${esc(SITE_URL + PREFIX())}quality.</p></div>
  </section>`;
  app.querySelector("#sheet-print").onclick = () => window.print();
}

// ---------- data quality and corrections (trust, 2026-10-26): coverage per field, open review queues, the latest date
// of each source, the corrections log and the method's versions (src/quality.py, from files in the repository)
function qualityPage() {
  nav("quality");
  crumbs([["Data quality"]]);
  setMeta("Data quality and corrections", "How complete the hip-hop data is, what is waiting for review, how fresh each source is, and every correction we have made.");
  const Q = store.data.quality || { queues: [], sources: [], corrections: [], method: [] }, A = store.data.artists, n = A.length;
  const pctOf = f => { const k = A.filter(f).length; return `${k < n ? Math.min(99, Math.round(100 * k / n)) : 100}%<br><span class="note">${k.toLocaleString()}</span>`; };
  const fields = [
    ["Monthly listeners", a => a.ml != null, "Spotify's public count (kworb.net); none below the 500k floor", "measured"],
    ["Spotify streams a day", a => a.daily != null, "kworb.net artist pages (Spotify play counts)", "measured"],
    ["Release-age mix of streams", a => (a.age_profile?.coverage ?? 0) >= 0.5, "half or more of the lead streams on songs with a release date", "measured"],
    ["Royalty estimate", a => a.streaming_mid, "measured streams × rates × deal shares", "estimated (C)"],
    ["Catalog value estimate", a => a.worth_mid, "royalties × sourced sale multiples", "estimated (C)"],
    ["Country of origin", a => a.cc?.length, "Wikidata citizenship (matching the birthplace when several)", "reported"],
    ["Scout score", a => a.scout, "at least three of the signals", "our measure"],
    ["Deezer fans", a => a.deezer_fans != null, "Deezer artist matched by ISRC or song titles", "measured"]];
  const open = Q.queues.reduce((s, q) => s + q.open, 0);
  const old = s => (Date.parse(store.data.as_of) - Date.parse(s.latest.length === 7 ? s.latest + "-01" : s.latest)) / 864e5;
  const stale = s => s.cadence.startsWith("daily") ? old(s) > 3 : s.cadence === "weekly" ? old(s) > 14 : s.cadence === "monthly" ? old(s) > 45 : old(s) > 200;
  app.innerHTML = `${subnav()}<section><h1>Data quality and corrections</h1>
    <p class="sub">How complete the data is, what is waiting for a decision, how fresh each source is, and every correction made so far. A missing figure is left out, never filled in with a guess; an uncertain match goes to a review queue, not into the data.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Artists tracked</div><div class="v">${n.toLocaleString()}</div><div class="s">data as of ${esc(store.data.as_of)}; built ${esc(store.data.built)}</div></div>
      <div class="tile"><div class="k">Label owner known</div><div class="v">${Math.round(100 * A.filter(labelKnown).length / n)}%</div><div class="s">${A.filter(labelKnown).length.toLocaleString()} of ${n.toLocaleString()}, from the last two years' releases; catalog acts not counted</div></div>
      <div class="tile"><div class="k">Open review items</div><div class="v">${open.toLocaleString()}</div><div class="s">across ${Q.queues.filter(q => q.open).length} queues, for our editors</div></div>
      <div class="tile"><div class="k">Corrections logged</div><div class="v">${Q.corrections.length}</div><div class="s">${Q.corrections.length ? `latest ${esc(Q.corrections[0].date)}` : "none yet"}</div></div>
      <div class="tile"><div class="k">Ranking method</div><div class="v">${Q.method[0] ? "v" + esc(Q.method[0].version) : "–"}</div><div class="s">${Q.method[0] ? esc(Q.method[0].date) : ""}</div></div>
    </section>
    <section class="panel"><h2>Coverage of the main fields</h2><div class="tablebox"><table class="stack"><thead><tr><th class="l">Field</th><th>Artists with it</th><th class="l">Needs</th><th class="l">Method</th></tr></thead><tbody>
      ${fields.map(([l, f, d, m]) => `<tr><td class="l"><b>${esc(l)}</b></td><td>${pctOf(f)}</td><td class="l wrap note">${esc(d)}</td><td class="l">${esc(m)}</td></tr>`).join("")}</tbody></table></div>
      ${coverageTable().replace("<h2>Data coverage</h2>", "<h3>Further fields</h3>")}</section>
    <section class="panel"><h2>Review queues</h2><p class="note">Cases our rules could not settle. Each waits for an editor's decision; until then the artist keeps the safe default (left out of the list, or "not yet classified").</p>
      <div class="tablebox"><table class="stack"><thead><tr><th class="l">Queue</th><th>Open</th><th>Rows</th></tr></thead><tbody>
      ${Q.queues.map(q => `<tr><td class="l wrap">${esc(q.what)}</td><td><b>${q.open.toLocaleString()}</b></td><td>${q.rows.toLocaleString()}</td></tr>`).join("") || `<tr><td class="l" colspan="3">No review queue for this genre.</td></tr>`}</tbody></table></div></section>
    <section class="panel"><h2>Freshness of each source</h2><div class="tablebox"><table class="stack"><thead><tr><th class="l">Data</th><th class="l">Source</th><th class="l">Read</th><th>Since</th><th>Latest</th></tr></thead><tbody>
      ${Q.sources.map(s => `<tr><td class="l"><b>${esc(s.what)}</b></td><td class="l wrap">${esc(s.source)}</td><td class="l">${esc(s.cadence)}</td><td>${esc(s.first)}</td><td>${esc(s.latest)}${stale(s) ? ` <span class="chip" title="Older than its usual cadence against the data date">late</span>` : ""}</td></tr>`).join("")}</tbody></table></div>
      <p class="note">Dates are the first and latest found in each data file. "Late" means older than the source's usual cadence, measured against the data date (${esc(store.data.as_of)}). Small artists' stream pages on kworb.net refresh irregularly; an artist page flags stream totals more than two weeks old.</p></section>
    <section class="panel"><h2>Corrections log</h2><p class="note">Every correction to a published figure or classification, and every change to how a number is worked out, newest first. Each links to our public <a href="https://github.com/sverigeleague/Music/blob/main/DECISIONS.md" target="_blank" rel="noopener">decision log</a>, where the full reasoning is filed by date. Spotted an error? <a href="mailto:hello@tventy.se?subject=Correction">hello@tventy.se</a>.</p>
      <div class="tablebox"><table class="stack"><thead><tr><th class="l">Date</th><th class="l">What</th><th class="l">Field</th><th class="l">Was</th><th class="l">Now</th><th class="l">Why</th></tr></thead><tbody>
      ${Q.corrections.map(c => `<tr><td class="l">${esc(c.date)}</td><td class="l wrap"><b>${esc(c.subject)}</b>${c.kind === "method" ? ` ${chip("method", "A change to how a number is worked out; it moves every artist's figure")}` : ""}</td><td class="l wrap">${esc(c.field)}</td><td class="l wrap">${esc(c.was)}</td><td class="l wrap">${esc(c.now)}</td><td class="l wrap note">${esc(c.basis)}. <a href="https://github.com/sverigeleague/Music/blob/main/DECISIONS.md" target="_blank" rel="noopener" title="${esc(c.source)}">Decision log</a></td></tr>`).join("") || `<tr><td class="l" colspan="6">No corrections yet.</td></tr>`}</tbody></table></div></section>
    <section class="panel"><h2>Ranking method versions</h2><ul>${Q.method.map(m => `<li><b>${esc(m.version)}</b> (${esc(m.date)}): ${esc(m.change)}</li>`).join("")}</ul>
      <p class="note">A change to any number in the current-listeners ranking is a new version. Money and Scout method changes are in the corrections log above (marked "method") and, version by version, in the <a href="#/changelog">method changelog</a>. Full detail: <a href="#/method">Method</a>.</p></section>`;
}

// ---------- press, method changelog, glossary, correction requests (ROADMAP 11.6, 11.7, 11.13, 11.17; 2026-10-26).
// Press (#/press): only figures other pages already show, each dated with its method and a citation line; an estimate
// always as a range with its grade. Changelog (#/changelog): registry/method_changes.csv, read by src/quality.py
// (store.data.quality.changes, joined to corrections.csv). Glossary (#/glossary): config.js GLOSSARY + the How rows.
const hashUrl = p => `${SITE_URL}${PREFIX()}${p}`;
const artistUrl = a => a.slug ? `${SITE_URL}${GDIR()}a/${a.slug}/` : hashUrl(`a/${a.id}`);
// a prefilled email; nothing is sent or stored by the site
const corrLink = (name, url) => `<a href="mailto:hello@tventy.se?subject=${encodeURIComponent(`Correction: ${name} (${url})`)}&body=${encodeURIComponent(`Page: ${url}\r\n\r\nWhat is wrong (the figure, label or fact as shown on the page):\r\n\r\n\r\nWhat it should be:\r\n\r\n\r\nSource we can check (a link, a release, a filing):\r\n\r\n\r\nYour role, if you wish (artist, manager, label, other):\r\n`)}" title="Opens an email to hello@tventy.se with the page filled in; nothing is stored on this site">Report a correction</a>`;
const copyBtns = root => root.querySelectorAll("[data-copy]").forEach(b => b.onclick = async () => {
  try { await navigator.clipboard.writeText(b.dataset.copy); b.textContent = "Copied"; } catch { b.textContent = "Select the text to copy"; }
  setTimeout(() => (b.textContent = "Copy"), 2500); });
function pressPage() {
  nav("press");
  crumbs([["Press"]]);
  const d = store.data, A = d.artists, w = GENRE === "country" ? "country" : "hip-hop", W = w[0].toUpperCase() + w.slice(1), on = d.as_of, n = A.length.toLocaleString();
  setMeta(`${W} in numbers: figures for the press`, `Quotable, dated figures on ${w}'s top artists, labels and money on Spotify, each with its method and a citation line.`);
  const m = d.market || { groups: {} }, g = k => m.groups[k] || { artists: 0, ml: 0 }, keys = Object.keys(m.groups).filter(k => k !== "Not yet known");
  const sum = (ks, f) => ks.reduce((s, k) => s + g(k)[f], 0), knownMl = sum(keys, "ml"), knownN = sum(keys, "artists"), MAJ = GROUP_ORDER.slice(0, 3);
  const st = Object.fromEntries(((d.state || [])[0]?.items || []).map(i => [i.key, i]));
  const ranked = A.filter(a => a.cl_rank).sort((a, b) => a.cl_rank - b.cl_rank), first = ranked[0], byMl = A.find(a => a.rank === 1 && a.ml);
  const M = { measured: ["measured", "Spotify's public counts via kworb.net, read daily"], classed: ["measured + classified", "measured listeners; each artist's label from the ℗ lines of their recent releases (Deezer), checked against recording codes"],
    ours: ["our measure", "tventy's Scout score: momentum against artists of a similar size, from public signals"], est: ["estimate", "our estimate from measured streams × published per-stream rates; always a range"] };
  const F = [];  // [section, label, value html, quote, method key, page path, extra note]
  const add = (...x) => F.push(x);
  if (knownMl) {
    const mj = sum(MAJ, "ml") / knownMl, sr = g("Self-released").ml / knownMl, il = g("Independent labels").ml / knownMl;
    add("Labels and market share", "Majors' share of listeners", share(mj), `Universal, Sony and Warner hold ${share(mj)} of the Spotify monthly listeners of ${w}'s top ${n} artists whose label is known (${knownN.toLocaleString()} artists).`, "classed", "labels", `${share(sum(MAJ, "artists") / (knownN || 1))} of those artists`);
    add("Labels and market share", "Independent labels' share", share(il), `Independent labels hold ${share(il)} of the Spotify monthly listeners of ${w}'s top ${n} artists whose label is known.`, "classed", "labels", `${g("Independent labels").artists.toLocaleString()} artists`);
    add("Labels and market share", "Self-released artists' share", share(sr), `Self-released artists hold ${share(sr)} of the Spotify monthly listeners of ${w}'s top ${n} artists whose label is known.`, "classed", "labels", `${g("Self-released").artists.toLocaleString()} artists`);
  }
  if (first) add("Top artists", "No. 1 by current listeners", esc(first.name), `${first.name} is No. 1 in ${w} by current listeners on Spotify: ${count(first.cl)} (monthly listeners counting only the listening to recent releases; ${count(first.ml)} monthly listeners in all).`, "measured", `a/${first.id}`, `${count(first.cl)} current, ${count(first.ml)} monthly`, first);
  if (byMl) add("Top artists", "Most monthly listeners", esc(byMl.name), `${byMl.name} has the most Spotify monthly listeners in ${w}: ${count(byMl.ml)}.`, "measured", `a/${byMl.id}`, `${count(byMl.ml)} monthly listeners`, byMl);
  if (st.mover) add("Top artists", "Biggest riser, about a month", esc(st.mover.value), `${st.mover.value} is ${w}'s biggest riser over about a month on Spotify: ${st.mover.detail}.`, "measured", st.mover.link.slice(2), esc(st.mover.detail));
  const brk = A.filter(a => a.scout?.tier === "Breaking"), best = [...brk].sort((a, b) => b.scout.score - a.scout.score)[0];
  if (brk.length) add("Rising and unsigned", "Rated Breaking", brk.length.toLocaleString(), `${brk.length} ${w} artists rate Breaking on tventy's Scout score, which measures momentum against artists of a similar size (top: ${best.name}, ${best.scout.score} out of 100).`, "ours", "scout", `top: ${esc(best.name)} (${best.scout.score})`);
  const U = (d.unsigned || []).filter(u => u.indie_kind === "prospect");
  if (d.unsigned) add("Rising and unsigned", "Unsigned prospects", U.length.toLocaleString(), `tventy counts ${U.length} unsigned prospects among ${w}'s top ${n} artists on Spotify: no label deal on record, under ${ESTABLISHED_YEARS} years of releases and 10m monthly listeners, and a recent song of their own.`, "classed", "unsigned", "labels from recent releases; established independents counted apart");
  if (st.unsigned) add("Rising and unsigned", "Top unsigned prospect", esc(st.unsigned.value), `${st.unsigned.value} is the top unsigned prospect in ${w} on tventy's Scout score: ${st.unsigned.detail}.`, "ours", st.unsigned.link.slice(2), esc(st.unsigned.detail));
  // as the State page adds it up: the top 100 by current listeners, an artist with no measured streams adding nothing
  const t100 = ranked.slice(0, 100), yr = k => t100.reduce((s, a) => s + (k === "mid" && a.rev_lines?.spotify || (a.money?.generated?.[k] || 0) * 12), 0);
  if (t100.some(a => a.money?.generated)) { const r = { low: yr("low"), mid: yr("mid"), high: yr("high") };
    add("Money (estimates)", `Spotify royalties, top ${t100.length} a year`, `${range(r)} ${grade("C")}`, `${w[0].toUpperCase() + w.slice(1)}'s top ${t100.length} artists by current listeners generate an estimated ${range(r)} a year in Spotify recording royalties (mid ${usd(r.mid)}), paid to the rights holders before the artist's share; a tventy estimate, grade C.`, "est", "worth", `mid ${usd(r.mid)}; paid to labels or distributors, not the artists' pay`); }
  const cat = A.filter(a => a.worth_mid && a.worth_range).sort((a, b) => b.worth_mid - a.worth_mid)[0];
  if (cat) add("Money (estimates)", "Highest catalog value", `${esc(cat.name)}<br><span class="note">${range({ low: cat.worth_range[0], high: cat.worth_range[1] })}</span> ${grade("C")}`, `${cat.name}'s recordings and songs would sell for an estimated ${range({ low: cat.worth_range[0], high: cat.worth_range[1] })} (mid ${usd(cat.worth_mid)}) at published catalog-sale multiples: a tventy estimate, grade C, indicative and not a valuation.`, "est", `a/${cat.id}`, `mid ${usd(cat.worth_mid)}; a year's royalties × sourced sale multiples by song age`, cat);
  const tot = A.reduce((s, a) => s + (a.second_of ? 0 : a.ml || 0), 0);
  add("The list", `${W} artists tracked`, n, `tventy tracks ${n} ${w} artists from Spotify's top ${d.universe.toLocaleString()} by monthly listeners, with ${count(tot)} monthly listeners combined (a fan of two artists counts twice).`, "measured", "", `${count(tot)} monthly listeners combined; of Spotify's top ${d.universe.toLocaleString()}`);
  const card = ([, k, v, q, how, path, note]) => { const a = path.startsWith("a/") && A.find(x => x.id === path.slice(2)), url = a ? artistUrl(a) : hashUrl(path), src = `Source: tventy music, ${on}, ${url}`;
    return `<div class="pressfig"><div class="k">${esc(k)}</div><div class="v">${v}</div><p>${esc(q)}</p>
      <p class="note">${chip(M[how][0], M[how][1])} ${note} · <a href="#/${path}">on the site</a></p>
      <p class="cite"><code>${esc(src)}</code> <button type="button" class="linkbtn" data-copy="${esc(q + " " + src)}">Copy</button></p></div>`; };
  const secs = [...new Set(F.map(f => f[0]))];
  app.innerHTML = `${subnav()}<section><h1>${esc(W)} in numbers: for the press</h1>
    <p class="sub">Figures you can quote, each from a page of this site, with the date of the data, how it is worked out and a citation line. Listener counts are measured; money figures are our estimates and are always given as a range with grade C, never as reported earnings. Data as of ${esc(on)}; the page updates daily.</p></section>
    <section class="panel" id="cite"><h2>How to cite</h2><ul>
      <li>Quote the sentence with the line under it: <code>Source: tventy music, &lt;date of the data&gt;, &lt;page address&gt;</code>. The date matters: listener counts change daily.</li>
      <li>Call an estimate an estimate and give the range. Royalties and catalog values are worked out from measured streams and published rates (grade C); labels' and artists' actual earnings are not public.</li>
      <li>Grades: <b>A</b> primary (filings, the platform's own disclosure), <b>B</b> reputable secondary, <b>C</b> our estimate. Terms are defined in the <a href="#/glossary">Glossary</a>; methods and their changes in <a href="#/method">Method</a> and the <a href="#/changelog">method changelog</a>.</li>
      <li>For figures fixed at a month's end, cite <a href="#/state">State of ${esc(w)}</a> for that month. Questions or a correction: <a href="mailto:hello@tventy.se?subject=${encodeURIComponent("Press: tventy music")}">hello@tventy.se</a>.</li></ul></section>
    ${secs.map(s => `<section class="panel"><h2>${esc(s)}</h2><div class="pressgrid">${F.filter(f => f[0] === s).map(card).join("")}</div></section>`).join("")}`;
  copyBtns(app);
}
const AREA = { money: ["Money estimates", "Royalties, the artist's share by deal and catalog sale values"], scout: ["Scout score", "How momentum is scored and when a tier is given"],
  unsigned: ["Unsigned prospects", "Who counts as an unsigned prospect"], other: ["Other figures", "Changes to how a summary figure is counted"] };
function changelogPage() {
  nav("changelog");
  crumbs([["Method changelog"]]);
  setMeta("Method changelog: money and Scout", "Every change to how the money estimates, the Scout score and the Unsigned list are worked out: the date, what changed and its effect.");
  const Q = store.data.quality || {}, C = Q.changes || [], R = Q.method || [], cur = k => C.find(c => c.area === k && c.version);
  const DL = "https://github.com/sverigeleague/Music/blob/main/DECISIONS.md";
  const only = r => r.genre === "all" ? "" : ` <span data-noswap>${chip(r.genre === "country" ? "country list only" : "hip-hop list only", "This change applies to one genre's list")}</span>`;
  app.innerHTML = `${subnav()}<section><h1>Method changelog</h1>
    <p class="sub">Every change to how our money estimates, the Scout score and the Unsigned list are worked out, newest first: the date, what changed and what it did to the figures. A change that moved published figures is also in the <a href="#/quality">corrections log</a>; the full reasoning is in our public <a href="${DL}" target="_blank" rel="noopener">decision log</a>, filed by date.</p></section>
    <section class="tiles">${["money", "scout", "unsigned"].map(k => cur(k) ? `<div class="tile"><div class="k">${esc(AREA[k][0])}</div><div class="v">v${esc(cur(k).version)}</div><div class="s">since ${esc(cur(k).date)}</div></div>` : "").join("")}
      ${R[0] ? `<div class="tile"><div class="k">Top-list ranking</div><div class="v">v${esc(R[0].version)}</div><div class="s">since ${esc(R[0].date)}</div></div>` : ""}</section>
    ${Object.keys(AREA).filter(k => C.some(c => c.area === k)).map(k => `<section class="panel" id="ch-${k}"><h2>${esc(AREA[k][0])}</h2><p class="note">${esc(AREA[k][1])}.</p>
      <div class="tablebox"><table class="stack"><thead><tr><th class="l">Version</th><th class="l">Date</th><th class="l">What changed</th><th class="l">Effect</th></tr></thead><tbody>
      ${C.filter(c => c.area === k).map(c => `<tr><td class="l"><b>${c.version ? "v" + esc(c.version) : "–"}</b></td><td class="l">${esc(c.date)}</td><td class="l wrap">${esc(c.change)}${only(c)}</td>
        <td class="l wrap">${esc(c.effect)}${c.now ? `<br><span class="note">${esc(c.field)}: was ${esc(c.was)}; now ${esc(c.now)}</span>` : ""} <span class="note"><a href="${DL}" target="_blank" rel="noopener" title="${esc(c.source)}">Decision log</a></span></td></tr>`).join("")}</tbody></table></div></section>`).join("")
      || `<section class="panel"><p class="note">No method changes logged yet.</p></section>`}
    ${R.length ? `<section class="panel" id="ch-ranking"><h2>Top-list ranking (current listeners)</h2><ul>${R.map(m => `<li><b>v${esc(m.version)}</b> (${esc(m.date)}): ${esc(m.change)}</li>`).join("")}</ul></section>` : ""}
    <p class="note">A new version is any change that can move a published figure; a wording or layout change is not one. Spotted an error? Write to <a href="mailto:hello@tventy.se?subject=Correction">hello@tventy.se</a>.</p>`;
}
function glossaryPage() {
  nav("glossary");
  crumbs([["Glossary"]]);
  setMeta("Glossary", "What each figure on tventy music means: listeners, current share, Scout signals, royalty and catalog estimates, grades.");
  const T = new Map(), add = (t, def, at) => { if (!T.has(t)) T.set(t, { def, at: new Map() }); if (at) T.get(t).at.set(at[0], at[1]); };
  Object.entries(GLOSSARY).forEach(([t, def]) => add(t, def));
  const PAGES = [["top", "Top list", "#/"], ["movers", "Movers", "#/movers"], ["scout", "Scout", "#/scout"], ["unsigned", "Unsigned", "#/unsigned"], ["producers", "Producers", "#/producers"], ["labels", "Labels", "#/labels"], ["tours", "Tours", "#/tours"]];
  const by = ui.by;
  for (const [k, l, h] of PAGES) for (const v of k === "top" ? ["monthly", "current"] : [by]) {
    ui.by = v;
    try { (HOW[k]?.() || []).forEach(([t, def]) => add(t, def[0].toUpperCase() + def.slice(1) + (/\.$/.test(def) ? "" : "."), [l, h])); } catch { /* a page's data not loaded yet */ }
  }
  ui.by = by;
  const rows = [...T].sort((a, b) => a[0].localeCompare(b[0], "en", { sensitivity: "base" }));
  const slug = t => "g-" + fold(t).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  app.innerHTML = `${subnav()}<section><h1>Glossary</h1>
    <p class="sub">What each figure on the site means, in plain words. The same definitions appear when you hold the pointer over a column heading, and in each page's "How this ranking works" box. Sources and grades for every figure: <a href="#/method">Method</a>.</p></section>
    <section class="panel"><dl class="gloss">${rows.map(([t, x]) => `<dt id="${slug(t)}">${esc(t)}</dt><dd>${esc(x.def)}${x.at.size ? ` <span class="note">Used on: ${[...x.at].map(([l, h]) => `<a href="${h}">${esc(l)}</a>`).join(", ")}</span>` : ""}</dd>`).join("")}</dl></section>`;
}

// ---------- deal comparison and advance recoupment (artists and managers, 2026-10-26): on #/worth/<id> (or a typed
// audience), what the artist keeps under each deal type over 1–5 years, with an advance paid back from the artist's
// share first. Deal shares: store.data.deals (registry/deal_shares.csv). Illustrative, before costs; never a contract.
const DEAL_ROWS = ["diy", "services", "independent", "major"];  // "unknown" is not a deal one can choose
const CHG_OPTS = [[-0.3, "fall 30% a year"], [-0.15, "fall 15% a year"], [0, "stay at today's pace"], [0.15, "grow 15% a year"], [0.3, "grow 30% a year"]];
const sig2 = v => { if (!(v > 0)) return 0; const p = 10 ** (Math.floor(Math.log10(v)) - 1); return Math.round(v / p) * p; };
// the artist's share paid month by month, royalties changing by g a year (compounded monthly)
const paidBy = (perYear, g, months) => { let s = 0; for (let m = 0; m < months; m++) s += perYear / 12 * (1 + g) ** (m / 12); return s; };
// months until the artist's share has paid back the advance (0: no advance; null: not within 10 years)
const recoupMonths = (adv, perYear, g) => { if (!(adv > 0)) return 0; if (!(perYear > 0)) return null; let s = 0;
  for (let m = 0; m < 120; m++) { s += perYear / 12 * (1 + g) ** (m / 12); if (s >= adv) return m + 1; } return null; };
const monthsWord = m => m == null ? "not within 10 years" : m === 0 ? "nothing to recoup" : m < 12 ? `${m} month${m > 1 ? "s" : ""}` : `${(m / 12).toFixed(1)} years`;
function dealPanel(gen, picked, w) {
  const deals = Object.fromEntries(store.data.deals.map(x => [x.deal_type, x]));
  const majorMid = +deals.major.mid;
  const key = picked ? picked.id : `ml${w.ml}`;  // a typed advance holds for this artist or audience only
  const adv = w.adv != null && w.advFor === key ? w.adv : sig2(gen.mid * majorMid * 1.5), g = w.chg ?? 0;
  w.advFor = key; w.adv = adv;  // default: about 18 months of the artist's share on a major deal
  const who = picked ? esc(picked.name) : "an artist with this audience";
  const rows = DEAL_ROWS.filter(k => deals[k]).map(k => {
    const D = deals[k], a = k === "diy" ? 0 : adv;  // distributors rarely pay an advance: DIY is shown without one
    const per = { low: gen.low * +D.low, mid: gen.mid * +D.mid, high: gen.high * +D.high };
    const cash = (r, y) => Math.max(a, paidBy(r, g, 12 * y));  // the advance is the artist's to keep; royalties start once it is paid back
    const left = Math.max(0, a - paidBy(per.mid, g, 60));
    return `<tr${w.deal === k ? ' class="tot"' : ""}><td class="l"><b>${esc(D.label)}</b>${w.deal === k && picked ? ` ${chip("assumed today", "The deal type assumed from the artist's label status; the real terms are not public")}` : ""}<br><span class="note">keeps ${Math.round(D.low * 100)}–${Math.round(D.high * 100)}% ${grade(D.grade)}${D.source ? ` <a href="${esc(D.source)}" target="_blank" rel="noopener">source</a>` : ""}</span></td>
      <td>${a ? usd(a) : `<span class="note">none</span>`}</td><td>${usd(per.mid)}<br><span class="note">${range(per)}</span></td>
      <td>${monthsWord(recoupMonths(a, per.mid, g))}${a ? `<br><span class="note">${monthsWord(recoupMonths(a, per.high, g))} to ${monthsWord(recoupMonths(a, per.low, g))}</span>` : ""}</td>
      ${[1, 2, 3, 4, 5].map(y => `<td>${usd(cash(per.mid, y))}${y === 5 ? `<br><span class="note">${range({ low: cash(per.low, 5), high: cash(per.high, 5) })}</span>` : ""}</td>`).join("")}
      <td>${left ? usd(left) : "–"}</td></tr>`; }).join("");
  return `<section class="panel" id="deal-compare"><h2>Deal comparison: what ${who} would keep over five years</h2>
    <p class="sub">The same recording royalties (about ${usd(gen.mid)} a year, range ${range(gen)}) run through each kind of deal, with an advance the artist pays back from their own share before any royalties reach them. Illustrative, before costs, manager and tax ${grade("C")}: not a statement about any artist's actual contract.</p>
    <div class="calc"><label>Advance on a label deal (US$)<input id="d-adv" type="number" min="0" step="10000" value="${Math.round(adv)}"></label>
      <label>Streams over the five years<select id="d-chg">${CHG_OPTS.map(([v, l]) => `<option value="${v}"${v === g ? " selected" : ""}>${l}</option>`).join("")}</select></label></div>
    <div class="tablebox"><table class="stack"><thead><tr><th class="l">Deal</th><th>Advance</th><th>Artist's share / yr</th><th>Advance paid back in</th><th>Cash to artist, year 1</th><th>By year 2</th><th>By year 3</th><th>By year 4</th><th>By year 5</th><th>Still owed after 5 years</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="note">Cash figures are cumulative and use the mid estimates; the range under them (and under year 5) multiplies the low ends together and the high ends together. "Paid back in" uses the mid; the line under it runs from the high case (fastest) to the low case (slowest).</p>
    <details class="how"><summary>How this works</summary><ul>
      <li><b>Royalties</b>: ${picked ? `${esc(picked.name)}'s measured Spotify streams (and YouTube views where measured) with the other services estimated from them` : "what artists of this size in our list generate per monthly listener"}: the recording royalties paid to the label or distributor ${grade("C")}. Songwriting income is left out: under most record deals it is not used to pay back the advance.</li>
      <li><b>Artist's share</b>: ${DEAL_ROWS.filter(k => deals[k]).map(k => `${esc(deals[k].label)} ${Math.round(deals[k].low * 100)}–${Math.round(deals[k].high * 100)}% (${esc(deals[k].note)}) ${grade(deals[k].grade)}`).join("; ")}.</li>
      <li><b>Advance and recoupment</b>: the label pays the advance up front and keeps the artist's share of royalties until the advance is paid back; the artist does not repay an advance that never recoups. Cash to the artist by a year is therefore the larger of the advance and the share earned so far. Self-released artists are shown with no advance, as distributors rarely pay one. The default advance is about 18 months of the artist's share on a major deal at the mid estimate; type any amount.</li>
      <li><b>Not modelled</b>: recording, video and marketing costs that many deals also recoup, cross-collateralisation across albums, a label's own spend and reach (which can grow the streams), term and ownership of the masters. These move real offers more than the share does.</li>
      <li>Streams: your assumption, compounded month by month. Data as of ${esc(store.data.as_of)}.</li></ul></details></section>`;
}
function bindDeal(w, rerender) {
  const adv = app.querySelector("#d-adv"), chg = app.querySelector("#d-chg");
  if (adv) adv.onchange = () => { w.adv = Math.max(0, +adv.value || 0); rerender().then(() => document.getElementById("deal-compare")?.scrollIntoView()); };
  if (chg) chg.onchange = () => { w.chg = +chg.value; rerender().then(() => document.getElementById("deal-compare")?.scrollIntoView()); };
}

// ---------- catalog age (investors, 2026-10-26): on the artist page, the share of the artist's streams by the age of
// the songs (age_profile, in the artist's shard) and the sale multiple it implies (worth, src/insights.py blended)
const AGE_BAND = { new: "Under 3 years old", mixed: "3–10 years old", evergreen: "10+ years old" };
function agePanel(a) {
  const p = ageOf(a), wo = a.worth, M = store.data.multiples || [];
  if (!wo?.multiple || !M.length) return "";
  const byAge = wo.method === "release age" && wo.age_mix;
  const mix = byAge ? wo.age_mix : null, x = v => `${+v}×`, xb = v => `${xm(v, !!mix)}×`;  // sourced bands as quoted; a blend to 2 decimals
  const bars = p ? M.map(m => { const v = p[m.vintage] || 0;
    return `<div class="barrow"><span>${AGE_BAND[m.vintage] || esc(m.vintage)}</span><div class="track"><i style="left:0;width:${v * 100}%"></i></div><span>${share(v)} · ${x(m.multiple_low)}–${x(m.multiple_high)}</span></div>`; }).join("") : "";
  const sum = mix ? M.map(m => `${share(mix[m.vintage] || 0)} × ${x(m.multiple_low)}–${x(m.multiple_high)}`).join(" + ") : "";
  return `<section class="panel" id="catalog-age"><h2>Catalog age: how fast the income may fade</h2>
    ${p ? `<p class="note">Share of ${esc(a.name)}'s daily streams on their own songs (not features), by the age of the song; next to each band, the sale multiple buyers pay for music of that age.</p><div class="bars">${bars}</div>
      <p class="note">${share(p.coverage)} of the lead streams are on songs with a release date${p.coverage < 0.5 ? ": too few to value the catalog by song age" : "; the shares above are of those"}.</p>` : `<p class="note">No release dates for ${esc(a.name)}'s songs yet, so the streams cannot be split by song age.</p>`}
    <p><b>Multiple used: ${xb(wo.multiple[0])}–${xb(wo.multiple[1])}</b> a year's royalties. ${mix ? `Each band's multiple weighted by its share of the streams: ${sum} = ${xb(wo.multiple[0])}–${xb(wo.multiple[1])}.` : `Too few streams are dated, so the multiple follows the share of listening on recent releases: ${esc(wo.vintage)} music.`}${wo.recordings?.high ? ` On a year's recording royalties that gives ${range(wo.recordings)} for the recordings (about ${usd(wo.recordings.mid)}) ${grade("C")}.` : ""}</p>
    <details class="how"><summary>How this works</summary><ul>
      <li><b>Why age matters</b>: a new song's streams usually fall fastest in its first years; songs that are still played 10 years on have settled. So buyers pay fewer years of income for new music and more for evergreen music.</li>
      <li><b>Multiples</b>: ${M.map(m => `${esc(AGE_BAND[m.vintage] || m.vintage)} ${m.multiple_low}–${m.multiple_high}× (${esc(m.source_note)}) ${grade(m.grade)} <a href="${esc(m.source_url)}" target="_blank" rel="noopener">source</a>`).join("; ")}. The band edges (3 and 10 years) are our split. The multiples are quoted on a catalog's net income; we apply them to royalties before the artist's and writers' share and any costs, so the value is indicative, not a valuation.</li>
      <li><b>Song age</b>: from each song's first release date (Deezer and MusicBrainz), weighted by its daily Spotify streams (kworb.net, measured). A reissue or compilation can carry a later date than the original, which makes a catalog look newer than it is. When under half of the lead streams are dated, the multiple follows the share of listening on recent releases instead.</li>
      <li>Data as of ${esc(store.data.as_of)}. All artists by catalog value and age: <a href="#/screener">Catalog screener</a>.</li></ul></details></section>`;
}

// ---------- label one-pager and roster export (investors and analysts, 2026-10-26): #/label/<slug>/sheet prints the
// roster's size, audience, royalty and value ranges, Scout tiers and published accounts; the roster also downloads as
// CSV with readable fields, sources and the data date (src/insights.py labels_index: roy_low/high, value_low/mid/high)
const labelRoster = L => { const byId = Object.fromEntries(store.data.artists.map(a => [a.id, a])); return L.artists.map(id => byId[id]).filter(Boolean); };
const labelRange = (L, lo, hi, mid) => L[hi] ? `${range({ low: L[lo], high: L[hi] })}${L[mid] ? `<br><span class="note">about ${usd(L[mid])}</span>` : ""}` : usd(L[mid]);
function labelCsv(L) {
  const g = GENRE === "country" ? "country" : "hip-hop", page = a => a.slug ? `${SITE_URL}${GDIR()}a/${a.slug}/` : `${SITE_URL}${PREFIX()}a/${a.id}`;
  download(`tventy-music-${g}-${L.slug}-roster.csv`, [["name", "spotify_url", "tventy_page", "label", "label_status", "label_owner", "country", "monthly_listeners", "current_listeners", "share_on_recent_releases", "scout_score", "scout_tier", "streaming_royalties_mid_usd_year", "catalog_value_low_usd", "catalog_value_mid_usd", "catalog_value_high_usd", "multiple_low", "multiple_high", "share_streams_new", "share_streams_3_10y", "share_streams_10y_plus", "latest_release", "newest_hit", "second_profile_of", "listeners_source", "money_grade", "data_as_of", "note"],
    ...labelRoster(L).map(a => [a.name, `https://open.spotify.com/artist/${a.id}`, page(a), a.label_name || "", statusWord(a), a.label_owner || "", a.country || "", a.floor ? "under 500k" : a.ml ?? "", a.floor ? "" : a.cl ?? "", a.cur_share ?? "",
      a.scout?.score ?? "", a.scout?.tier || (a.scout?.provisional ? "provisional" : ""), a.streaming_mid || "", a.worth_range?.[0] ?? "", a.worth_mid || "", a.worth_range?.[1] ?? "", a.wmult?.[0] ?? "", a.wmult?.[1] ?? "",
      ageOf(a)?.new ?? "", ageOf(a)?.mixed ?? "", ageOf(a)?.evergreen ?? "", a.latest_release || "", a.top_fresh?.title || "", a.second_of || "",
      "Spotify public counts via kworb.net (measured)", "C (estimate, royalties and value)", store.data.as_of, "label from the artist's releases of the last two years (Deezer); values indicative, not a valuation; tventy music"])]);
}
function labelSheet(s) {
  nav("label");
  const L = labelBySlug(s);
  if (!L) { app.innerHTML = `<p>Label not found. <a href="#/labels">All labels</a></p>`; return; }
  crumbs([["Labels", "#/labels"], [L.name, `#/label/${L.slug}`], ["One-pager"]]);
  setMeta(`${L.name}: label one-pager`, `${L.name} on one page: roster size, audience, royalty and catalog value ranges, Scout tiers and published accounts, with sources and grades.`);
  const roster = labelRoster(L), counted = roster.filter(a => !a.second_of), own = L.parent && L.parent !== L.name;
  const total = store.data.artists.reduce((x, a) => x + (a.second_of ? 0 : a.ml || 0), 0);
  const tier = t => counted.filter(a => a.scout?.tier === t).length;
  const aged = counted.filter(a => ageOf(a) && a.streaming_mid), wt = aged.reduce((x, a) => x + a.streaming_mid, 0);
  const mix = wt ? Object.fromEntries(["new", "mixed", "evergreen"].map(k => [k, aged.reduce((x, a) => x + ageOf(a)[k] * a.streaming_mid, 0) / wt])) : null;
  const size = a => a.ml ?? (a.daily ? a.daily / 10 : 0);  // below the 500k floor: streams a day, as the screener
  const top = [...counted].sort((a, b) => size(b) - size(a)).slice(0, 10);
  const row = (k, v, src) => `<tr><td class="l">${k}</td><td>${v}</td><td class="l note">${src}</td></tr>`;
  const status = L.status === "independent" ? "Independent label" : L.status === "major_distributed" ? "Distributed by a major" : "Major-label imprint";
  app.innerHTML = `<section class="sheet">
    <div class="sheethead">${logo(L.name, "logo big")}<div><h1>${esc(L.name)}</h1>
      <p class="sub">${status}${own ? ` · owned by ${esc(L.parent)}` : ""} · ${roster.length} artist${roster.length === 1 ? "" : "s"} in hip-hop's top 1,000</p>
      <p class="note">tventy music label one-pager · data as of ${esc(store.data.as_of)} · ${esc(`${SITE_URL}${GDIR()}label/${L.slug}/`)}</p></div></div>
    <div class="noprint links"><button type="button" class="btn" id="lsheet-print">Print or save as PDF</button><button type="button" class="btn" id="lsheet-csv">Roster CSV (${roster.length})</button><a href="#/label/${L.slug}">Full label page</a></div>
    <div class="sheetgrid">
      <div class="panel"><h2>Roster and audience</h2><table class="sheettab"><tbody>
        ${row("Artists in the list", roster.length, roster.length > counted.length ? `${roster.length - counted.length} second profile${roster.length - counted.length > 1 ? "s" : ""} listed, not added to the sums` : "the label on each artist's releases of the last two years (Deezer)")}
        ${row("Monthly listeners, added", count(L.ml), `${share(L.ml / total)} of the list's listeners; Spotify via kworb.net, measured`)}
        ${row("Current listeners, added", count(L.cl), "listening on recent releases; our measure")}
        ${row("Releases, last 2 years", L.releases_2y ?? "–", "across the artists we track (Deezer)")}
      </tbody></table></div>
      <div class="panel"><h2>Money per year ${grade("C")}</h2><table class="sheettab"><tbody>
        ${row("Roster streaming royalties", labelRange(L, "roy_low", "roy_high", "royalties"), "generated, paid to the label before the artists' share; all services")}
        ${row("Roster recordings + songs value", labelRange(L, "value_low", "value_high", "value_mid"), "a year's streaming and songwriting royalties × sale multiples by song age")}
        ${row("Roster streams by song age", mix ? `${share(mix.new)} / ${share(mix.mixed)} / ${share(mix.evergreen)}` : "–", mix ? "under 3 / 3–10 / 10+ years, weighted by each artist's royalties" : "no dated streams")}
      </tbody></table><p class="note">Sums of per-artist estimates: the low ends added together and the high ends together. Indicative, not a valuation; who owns older masters is not tracked.</p></div>
      <div class="panel"><h2>Scout</h2><table class="sheettab"><tbody>
        ${row("Breaking", tier("Breaking"), "score 80+ with new songs or attention clearly up")}
        ${row("Rising", tier("Rising"), "score 65+")}
        ${row("Watch", tier("Watch"), "score 50–64")}
        ${row("Average score", L.scout_avg ?? "–", "0–100 against artists of similar size; a pointer, not a prediction")}
      </tbody></table></div>
    </div>
    <div class="panel"><h2>Biggest artists</h2><div class="tablebox"><table class="sheettab stack"><thead><tr><th class="l">Artist</th><th>Monthly listeners</th><th>Scout</th><th>Streaming royalties / yr</th><th>Recordings + songs value</th></tr></thead><tbody>
      ${top.map(a => `<tr><td class="l">${esc(a.name)} ${flag(a)}</td><td>${mlx(a)}</td><td>${a.scout ? `${a.scout.score} ${tierChip(a.scout.tier)}` : "–"}</td><td>${usd(a.streaming_mid)}</td><td>${a.worth_range ? range({ low: a.worth_range[0], high: a.worth_range[1] }) : "–"}</td></tr>`).join("")}
    </tbody></table></div>${counted.length > 10 ? `<p class="note">${counted.length - 10} more in the roster CSV.</p>` : ""}</div>
    <div class="panel"><h2>Accounts</h2>${own ? `<p class="note">${esc(L.name)} is part of ${esc(L.parent)} and publishes no accounts of its own; the owner's reported figures:</p>${finTable(L.parent)}` : finTable(L.name)}</div>
    <div class="panel sheetfoot"><h2>Sources and grades</h2><p class="note">Grades: <b>A</b> primary (filings), <b>B</b> reputable secondary, <b>C</b> our estimate, always a range. Measured: Spotify's public counts via kworb.net, Deezer releases. Estimated: royalties from measured streams × platform rates (registry/rates.csv); values × sale multiples (registry/catalog_multiples.csv). Label: as printed on the artists' releases of the last two years, placed with its owner (label registry, MusicBrainz, recording registrant codes). Accounts: the companies' own reports (A) or the press (B). Corrections: hello@tventy.se. Method: ${esc(SITE_URL + PREFIX())}method.</p></div>
  </section>`;
  app.querySelector("#lsheet-print").onclick = () => window.print();
  app.querySelector("#lsheet-csv").onclick = () => labelCsv(L);
}

// ---------- saved screens (A&R and investors, 2026-10-26): Scout, screener and Unsigned filters in the page address
// (#/scout?tier=all&band=1.5-3m), so a copied link opens the same view. Only values that differ from the page's
// defaults are written; an unknown value in a hand-edited link falls back to the default.
const SCREENS = { scout: ["scout", { status: "all", band: "all", tier: "rising", country: "all", sort: ["score", -1] }, ["signals", "all"]],
  screener: ["screen", { value: "any", age: "any", owner: "any", roy: "0", country: "all", sort: ["value", -1] }, ["all"]],
  unsigned: ["uns", {}, ["all"]] };
const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const SCREEN_OK = { age: v => has(AGE_MIX, v), owner: v => has(OWNERS, v), value: v => VALUE_BANDS.some(b => b[0] === v), roy: v => ROYALTY_MIN.some(r => r[0] === v),
  tier: v => ["rising", "Breaking", "Watch", "all", "watch"].includes(v), status: v => ["all", "prospect", "self_released", "independent", "signed", "unknown"].includes(v) };
const screenNow = p => p === "unsigned" ? { all: !!ui.unsAll } : ui[SCREENS[p][0]] || {};
function readScreen(p) {
  const qs = location.hash.split("?")[1];
  if (!qs) return;
  const q = new URLSearchParams(qs), [key, def, flags] = SCREENS[p];
  if (p === "unsigned") { ui.unsAll = q.get("all") === "1"; return; }
  const f = { ...def };
  for (const k of Object.keys(def)) { const v = q.get(k); if (v == null) continue;
    if (Array.isArray(def[k])) { const [c, d] = v.split(","); if (c) f[k] = [c, d === "1" ? 1 : -1]; }
    else if (!SCREEN_OK[k] || SCREEN_OK[k](v)) f[k] = v; }
  for (const k of flags) f[k] = q.get(k) === "1";
  ui[key] = f;
}
function syncScreen(p) {
  const [, def, flags] = SCREENS[p], f = screenNow(p), q = new URLSearchParams();
  for (const k of Object.keys(def)) { const v = Array.isArray(f[k]) ? f[k].join(",") : f[k], d = Array.isArray(def[k]) ? def[k].join(",") : def[k]; if (v != null && String(v) !== String(d)) q.set(k, v); }
  for (const k of flags) if (f[k]) q.set(k, "1");
  const base = (location.hash || PREFIX() + p).replace(/\?.*$/, ""), want = q.toString() ? `${base}?${q}` : base;
  if (location.hash !== want) history.replaceState(history.state, "", want);  // no hashchange: the page is not redrawn
}
const linkBtn = () => `<button type="button" class="btn" data-copylink title="Copy a link to this exact view: the filters and sort are in the address">Copy link to this view</button>`;
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-copylink]");
  if (!b) return;
  try { await navigator.clipboard.writeText(location.href); b.textContent = "Link copied"; } catch { b.textContent = "Copy the address bar"; }
  setTimeout(() => (b.textContent = "Copy link to this view"), 2500);
});

// ---------- hip-hop and country side by side (analysts and press, 2026-10-26, ROADMAP 11.11): #/genres (and
// #/country/genres) loads both genres' index and extra.json and works out each figure as that genre's own page does
// (Labels tiles, catalog screener, label one-pager, Platforms, Scout). The two lists are different universes: said on the page.
SECTION.genres = "artists"; SUBNAV.artists.push(["genres", "#/genres", "Genres compared"]);
// another genre's page files, merged as route's loadPart merges the genre in view (artist_more in index order)
function loadGenreParts(g, ps) {
  return loadGenre(g).then(d => { if (!d) throw new Error(`the ${g === "hip_hop" ? "hip-hop" : g} data did not load`);
    const s = genreStore[g], parts = s.parts = s.parts || {}, have = s.have = s.have || {}, dir = g === "hip_hop" ? "data/" : `data/${g}/`;
    return Promise.all(ps.map(p => parts[p] || (parts[p] = getJSON(`${dir}${p}.json`).then(x => { const more = x.artist_more || {}; delete x.artist_more;
      for (const k in more) if (more[k].length === s.data.artists.length) s.data.artists.forEach((a, i) => { a[k] = more[k][i]; });
      have[p] = true; return Object.assign(s.data, x); }).catch(e => { delete parts[p]; throw e; })))).then(() => s.data); });
}
function genreFigures(d) {
  const A = d.artists, counted = A.filter(a => !a.second_of), m = d.market;
  // Labels page tiles: majors = the first three groups, shares of the listeners of artists whose label is known
  const G = GROUP_ORDER.filter(g => m.groups[g]).concat(Object.keys(m.groups).filter(g => !GROUP_ORDER.includes(g))), gv = (g, k) => m.groups[g][k];
  const known = k => G.filter(g => g !== "Not yet known").reduce((s, g) => s + gv(g, k), 0) || 1, tot = k => G.reduce((s, g) => s + gv(g, k), 0) || 1;
  const maj = k => G.slice(0, 3).reduce((s, g) => s + gv(g, k), 0) / known(k);
  const valued = A.filter(a => a.worth_mid), add = f => valued.reduce((s, a) => s + (f(a) || 0), 0);  // catalog screener, no filter
  const aged = counted.filter(a => ageOf(a) && a.streaming_mid), wt = aged.reduce((x, a) => x + a.streaming_mid, 0);  // label one-pager
  const plat = Object.fromEntries(STREAMING.map(k => [k, A.reduce((s, a) => s + (a.rev_lines?.[k] || 0), 0)]));  // Platforms, whole list
  const listed = counted.filter(a => a.ml && !a.floor), ml = listed.reduce((s, a) => s + a.ml, 0);
  return { n: A.length, floor: A.filter(a => a.floor).length, ml, majMl: maj("ml"), majN: maj("artists"),
    self: (m.groups["Self-released"]?.ml || 0) / (tot("ml") - (m.groups["Not yet known"]?.ml || 0) || 1), selfN: m.groups["Self-released"]?.artists || 0,
    roy: A.reduce((s, a) => s + (streamingMid(a) || 0), 0), perL: ml ? listed.reduce((s, a) => s + (streamingMid(a) || 0), 0) / ml : null,
    value: { low: add(a => a.worth_range?.[0]), mid: add(a => a.worth_mid), high: add(a => a.worth_range?.[1]) }, valued: valued.length,
    mult: median(valued.filter(a => a.wmult).map(a => (a.wmult[0] + a.wmult[1]) / 2)),
    mix: wt ? Object.fromEntries(["new", "mixed", "evergreen"].map(k => [k, aged.reduce((x, a) => x + ageOf(a)[k] * a.streaming_mid, 0) / wt])) : null,
    plat, platSum: Object.values(plat).reduce((s, v) => s + v, 0), radio: A.reduce((s, a) => s + (a.rev_lines?.radio || 0), 0),
    tiers: Object.fromEntries(["Breaking", "Rising", "Watch"].map(t => [t, A.filter(a => a.scout?.tier === t).length])),
    top: [...listed].sort((x, y) => y.ml - x.ml).slice(0, 10), as_of: d.as_of };
}
async function genresPage() {
  nav("genres");
  crumbs([["Artists", "#/"], ["Genres compared"]]);
  const title = "Hip-hop and country compared: ownership, pay and catalog value";
  app.innerHTML = `${subnav()}<p class="note">Loading both genres…</p>`;
  const [H, C] = await Promise.all([loadGenreParts("hip_hop", ["extra"]), loadGenreParts("country", ["extra"])]);
  if (pageId !== "genres") return;  // the visitor moved on
  document.title = `${title} · tventy music`;  // set here: setMeta would turn "hip-hop" into "country" on the country side
  const dm = document.querySelector('meta[name="description"]'); if (dm) dm.content = "Hip-hop's top 1,000 and country's list side by side: majors' share, self-released share, royalties, catalog values, the age of the music, platforms and Scout tiers, every figure sourced.";
  const h = genreFigures(H), c = genreFigures(C);
  const row = (k, note, f) => `<tr><td class="l">${k}${note ? `<br><span class="note">${note}</span>` : ""}</td><td>${f(h)}</td><td>${f(c)}</td></tr>`;
  const head = l => `<thead><tr><th class="l">${l}</th><th>Hip-hop</th><th>Country</th></tr></thead>`;
  const mixOf = x => x.mix ? `${share(x.mix.new)} / ${share(x.mix.mixed)} / ${share(x.mix.evergreen)}` : "–";
  const P = C.platforms, keys = STREAMING.filter(k => h.plat[k] / (h.platSum || 1) >= 0.005 || c.plat[k] / (c.platSum || 1) >= 0.005)
    .sort((x, y) => (c.plat[y] / (c.platSum || 1) + h.plat[y] / (h.platSum || 1)) - (c.plat[x] / (c.platSum || 1) + h.plat[x] / (h.platSum || 1)));
  const pname = k => k === "others" ? "Other services (Tencent, NetEase, regional)" : P[k]?.name || k;
  const topList = (x, g) => `<div><h3>${g === "hip_hop" ? "Hip-hop" : "Country"}</h3><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th>Monthly listeners</th></tr></thead><tbody>
    ${x.top.map((a, i) => `<tr><td class="l">${i + 1}</td><td class="l"><a class="who" href="${g === "hip_hop" ? "#/" : "#/country/"}a/${a.id}" data-genre-link="${g}">${pic(a)}<span>${esc(a.name)}</span>${flag(a)}</a></td><td>${count(a.ml)}</td></tr>`).join("")}</tbody></table></div></div>`;
  app.innerHTML = `${subnav()}<div data-noswap><section><h1>Hip-hop and country, side by side</h1>
    <p class="sub">Who owns each genre's biggest artists, what the music earns, what the catalogs would sell for and how old the music earning it is. Each figure is worked out as on that genre's own pages, from the same data.</p>
    <p class="note"><b>Two different lists.</b> Hip-hop: the ${h.n.toLocaleString()} hip-hop artists with the most Spotify monthly listeners. Country: ${c.n.toLocaleString()} country artists, ${(c.n - c.floor).toLocaleString()} above Spotify's public 500k-listener floor and ${c.floor.toLocaleString()} below it, ranked by streams a day or Deezer's order (no listener count). The hip-hop list stops at about 1.5m listeners, so it holds fewer small artists: shares and sums compare the lists as published, not the two genres as a whole. Data as of ${esc(h.as_of)} (hip-hop) and ${esc(c.as_of)} (country).</p></section>
    <section class="panel"><h2>Size and ownership</h2><div class="tablebox"><table class="cmp">${head("Measure")}<tbody>
      ${row("Artists in the list", "", x => x.n.toLocaleString() + (x.floor ? `<br><span class="note">${x.floor} below 500k</span>` : ""))}
      ${row(`Monthly listeners, added ${chip("measured")}`, "a sum over the artists with a listener count: a fan of two artists counts twice; second Spotify profiles left out", x => count(x.ml))}
      ${row(`Majors' share of listeners ${grade("B")}`, "Universal, Sony and Warner, of the listeners of artists whose label is known (as on Labels)", x => `${share(x.majMl)}<br><span class="note">${share(x.majN)} of those artists</span>`)}
      ${row(`Self-released share of listeners ${grade("B")}`, "of the listeners of artists whose label is known", x => `${share(x.self)}<br><span class="note">${x.selfN} artists</span>`)}
    </tbody></table></div><p class="note">Labels: the label printed on each artist's releases of the last two years (Deezer), placed with its owner and checked against the recordings' registrant codes; catalog acts (no release in two years) are left out of the shares. Listeners: Spotify's public counts via kworb.net.</p></section>
    <section class="panel"><h2>Money ${grade("C")}</h2><div class="tablebox"><table class="cmp">${head("Measure")}<tbody>
      ${row("Streaming royalties a year, added", "generated on all services before anyone's cut, mid estimates at today's pace", x => usd(x.roy))}
      ${row("Per monthly listener a year", "the royalties of artists with a listener count ÷ their listeners", x => x.perL ? "$" + x.perL.toFixed(2) : "–")}
      ${row("Recordings + songs value, added", "a year's streaming and songwriting royalties × sale multiples by song age (as the catalog screener)", x => `about ${usd(x.value.mid)}<br><span class="note">${range(x.value)}; ${x.valued.toLocaleString()} catalogs</span>`)}
      ${row("Median sale multiple", "years of royalties a buyer pays, mid of each artist's range", x => x.mult ? xm(x.mult) + "×" : "–")}
      ${row("Streams by song age", "under 3 / 3–10 / 10+ years, weighted by each artist's royalties", mixOf)}
    </tbody></table></div><p class="note">Sums of per-artist estimates: the low ends added together and the high ends together, so the ranges are wide. Indicative, not valuations. Method: royalties from measured Spotify streams and YouTube views, other services estimated from them with each genre's own platform ratios (registry/platform_multipliers.csv and platform_multipliers_country.csv); values with the sale multiples in registry/catalog_multiples.csv.</p></section>
    <section class="panel"><h2>Where the recording royalties come from ${grade("C")}</h2><div class="tablebox"><table class="cmp">${head("Service, share of streaming royalties")}<tbody>
      ${keys.map(k => row(esc(pname(k)) + (["spotify", "youtube"].includes(k) ? " " + chip("measured") : ""), "", x => share(x.plat[k] / (x.platSum || 1)))).join("")}
      ${row("US radio airplay, a year", "paid to the songs' writers and publishers, not the recordings; not in the shares above", x => usd(x.radio))}
    </tbody></table></div><p class="note">Mid estimates over each whole list. Only Spotify and YouTube are measured; the other services are estimated from each artist's Spotify royalties with ratios from label filings and genre research: country over-indexes on Amazon Music (about 1.5–2.2× its all-genre share) and Pandora, so those ratios are set higher for country. In hip-hop's estimates Pandora sits inside "Other services". Radio is estimated from the US airplay audience where an artist is on the airplay chart; a dash means no radio line in that list's estimates.</p></section>
    <section class="panel"><h2>Scout tiers</h2><div class="tablebox"><table class="cmp">${head("Tier")}<tbody>
      ${row(tierChip("Breaking"), "score 80+ with new songs or attention clearly up", x => x.tiers.Breaking)}
      ${row(tierChip("Rising"), "score 65+", x => x.tiers.Rising)}
      ${row(tierChip("Watch"), "score 50–64", x => x.tiers.Watch)}
    </tbody></table></div><p class="note">Scout scores each artist against artists of similar size in their own genre's list, with each genre's own signals (country adds US radio), so a tier count compares how much momentum each list holds, not one scale. A pointer, not a prediction. <a href="#/scout">Scout</a></p></section>
    <section class="panel"><h2>The ten biggest by monthly listeners ${chip("measured")}</h2><div class="grid2">${topList(h, "hip_hop")}${topList(c, "country")}</div></section>
    <section class="panel"><h2>Sources and grades</h2><p class="note"><b>Measured</b>: Spotify's public monthly listeners and play counts (kworb.net), YouTube views, Deezer releases. <b>B</b>: label ownership, from release labels and registrant codes. <b>C</b>: our estimates, always shown as a range on each artist's page. Each genre's own pages hold the detail: <a href="#/labels" data-genre-link="hip_hop">hip-hop labels</a>, <a href="#/country/labels" data-genre-link="country">country labels</a>, <a href="#/screener" data-genre-link="hip_hop">hip-hop catalogs</a>, <a href="#/country/screener" data-genre-link="country">country catalogs</a>, <a href="#/method">Method</a>.</p></section></div>`;
}

// ---------- label groups' results with periods aligned (investors, 2026-10-26, ROADMAP 11.14): on Labels, each
// company's latest fiscal year in its own column, labelled with the months it covers and its currency, on one
// calendar strip; a year well behind the newest is marked. From label_financials (registry/label_financials.csv).
const FIN_COS = [["Universal Music Group", "Universal Music Group"], ["Sony Music (Sony Group Music segment)", "Sony Music (music segment)"], ["Warner Music Group", "Warner Music Group"], ["BMG", "BMG"], ["Believe", "Believe"], ["Reservoir Media", "Reservoir Media"]];
// each line: the first metric (or set of metrics, added) the company reports; profit carries its own name
const FIN_LINES = [["Revenue", ["total_revenue", "revenue", "music_segment_sales"]], ["Recorded music", ["recorded_music_revenue", ["recorded_music_streaming_sales", "recorded_music_other_sales"]]],
  ["Recorded music streaming", ["recorded_music_streaming_revenue", "recorded_music_streaming_sales", ["subscription_streaming_revenue", "ad_supported_streaming_revenue"]]],
  ["Music publishing", ["music_publishing_revenue", "music_publishing_sales"]], ["Profit", ["adjusted_ebitda", "adjusted_oibda", "operating_ebitda_adjusted", "music_segment_operating_income"]]];
const PROFIT_NAME = { adjusted_ebitda: "adjusted EBITDA", adjusted_oibda: "adjusted OIBDA", operating_ebitda_adjusted: "operating EBITDA, adjusted", music_segment_operating_income: "segment operating income" };
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function alignedFinancials() {
  const R = (store.data.label_financials || []).filter(r => r.unit === "millions" && r.value !== "" && !isNaN(+r.value));
  const endOf = r => (/year ended (\d{4}-\d{2}-\d{2})/.exec(r.period || "") || [])[1];
  const cols = FIN_COS.map(([co, name]) => {
    const rs = R.filter(r => r.company === co && endOf(r)), ends = [...new Set(rs.map(endOf))].sort();
    if (!ends.length) return null;
    const end = ends.at(-1), prevEnd = `${+end.slice(0, 4) - 1}${end.slice(4)}`;
    const get = (e, ms) => { for (const m of ms) { const ks = Array.isArray(m) ? m : [m], xs = ks.map(k => rs.find(r => endOf(r) === e && r.metric === k));
      if (xs.every(Boolean)) return { v: xs.reduce((s, r) => s + +r.value, 0), r: xs[0], k: ks[0], sum: ks.length > 1 }; } return null; };
    const v = Object.fromEntries(FIN_LINES.map(([l, ms]) => [l, get(end, ms)])), rev0 = get(prevEnd, FIN_LINES[0][1]);
    const y = +end.slice(0, 4), mo = +end.slice(5, 7), sy = mo === 12 ? y : y - 1, sm = mo % 12;  // the 12 months to the period end
    return { co, name, end, cur: v.Revenue?.r.currency || rs[0].currency, v, rev0, fy: (/^(Sony )?FY\d{4}/.exec(v.Revenue?.r.period || "") || [""])[0],
      span: `${MON[sm]} ${sy} – ${MON[mo - 1]} ${y}`, t0: sy + sm / 12, t1: y + mo / 12 };
  }).filter(Boolean);
  if (!cols.length) return "";
  const newest = cols.map(c => c.end).sort().at(-1), lo = Math.min(...cols.map(c => c.t0)), hi = Math.max(...cols.map(c => c.t1));
  const behind = c => Math.round((Date.parse(newest) - Date.parse(c.end)) / (864e5 * 30.44)), stale = c => behind(c) >= 9;  // as groupsCompare: 270 days
  const money = (x, c) => x ? `${money2(x.v * 1e6, c.cur)}${x.sum ? `<span class="note">*</span>` : ""}` : "–";
  const td = (c, s) => `<td${stale(c) ? ' class="q"' : ""}>${s}</td>`;
  return `<section class="panel" id="fin-aligned"><h2>Label groups' music results, periods aligned ${grade("A")}</h2>
    <p class="note">Each company's latest reported fiscal year, in its own currency. The years end in different months, so the columns cover different twelve months: the strip shows which.</p>
    <div class="bars">${cols.map(c => `<div class="barrow"><span>${esc(c.name)}</span><div class="track"><i style="left:${(c.t0 - lo) / (hi - lo) * 100}%;width:${(c.t1 - c.t0) / (hi - lo) * 100}%"></i></div><span>${esc(c.span)}${stale(c) ? " · older" : ""}</span></div>`).join("")}</div>
    <div class="tablebox"><table><thead><tr><th class="l">Measure</th>${cols.map(c => `<th${stale(c) ? ' class="q"' : ""}>${esc(c.name)}</th>`).join("")}</tr></thead><tbody>
      <tr><td class="l">Fiscal year</td>${cols.map(c => td(c, `${esc(c.fy || "FY")}<br><span class="note">${esc(c.span)}</span>${stale(c) ? `<br><span class="note"><b>${behind(c)} months older</b> than the newest column</span>` : ""}`)).join("")}</tr>
      <tr><td class="l">Currency</td>${cols.map(c => td(c, `<b>${esc(c.cur)}</b>`)).join("")}</tr>
      ${FIN_LINES.map(([l]) => `<tr><td class="l">${l === "Profit" ? "Profit measure" : esc(l)}</td>${cols.map(c => td(c, `${money(c.v[l], c)}${l === "Profit" && c.v[l] ? `<br><span class="note">${esc(PROFIT_NAME[c.v[l].k] || c.v[l].k)}</span>` : ""}`)).join("")}</tr>`).join("")}
      <tr><td class="l">Profit margin</td>${cols.map(c => td(c, c.v.Profit && c.v.Revenue ? (c.v.Profit.v / c.v.Revenue.v * 100).toFixed(1) + "%" : "–")).join("")}</tr>
      <tr><td class="l">Revenue growth, own currency</td>${cols.map(c => td(c, c.rev0 && c.v.Revenue ? pct((c.v.Revenue.v / c.rev0.v - 1) * 100) : "–")).join("")}</tr>
      <tr><td class="l">Basis</td>${cols.map(c => td(c, c.v.Revenue ? `${c.v.Revenue.r.basis === "reported" ? grade("A") : grade("B")} <a href="${esc(c.v.Revenue.r.source_url)}" target="_blank" rel="noopener" title="${esc(c.v.Revenue.r.period)}${c.v.Revenue.r.note ? ": " + esc(c.v.Revenue.r.note) : ""}">source</a>` : "–")).join("")}</tr>
    </tbody></table></div>
    <p class="note"><b>Why there is no total:</b> the columns are in euros, yen and dollars and cover different twelve-month periods. Adding them needs an exchange rate for each company's own year (an average rate for revenue, not today's), and even then the sum would mix, for example, Warner's year to September with Sony's year to March. Compare growth rates and margins, which need no conversion. Shaded columns are a fiscal year nine months or more older than the newest. * the sum of two reported lines (Sony: streaming and other recorded music sales; Universal: subscription and ad-supported streaming). Sony Music is Sony Group's music segment, not the whole group; BMG is Bertelsmann's music business. The profit measures are each company's own and are not defined the same way: compare them with care. Margin and growth are our arithmetic on the reported figures.</p></section>`;
}

// ---------- peer benchmark (artists, 2026-10-26, ROADMAP 11.15): on the artist page, the artist's percentile among the
// 10 artists of the same genre's list nearest in monthly listeners, on five measures from the index (no extra download)
const ord = n => n + (n % 100 >= 11 && n % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th");
function peerCard(a) {
  if (!a.ml || a.floor || a.second_of) return "";
  const near = store.data.artists.filter(p => p.id !== a.id && p.ml && !p.floor && !p.second_of)
    .sort((x, y) => Math.abs(Math.log(x.ml / a.ml)) - Math.abs(Math.log(y.ml / a.ml))).slice(0, 10);
  if (near.length < 5) return "";
  const M = [["Current share", "share of listening on recent releases", x => x.cur_share, v => share(v), "measured"],
    ["Streams a day per listener", "Spotify streams a day ÷ monthly listeners", x => x.daily && x.ml ? x.daily / x.ml : null, v => v.toFixed(2), "measured"],
    ["Scout score", "0–100, against artists of similar size", x => x.scout?.score, v => String(v), ""],
    ["Spotify royalties per listener / yr", "own songs' Spotify recording royalties (mid estimate) ÷ monthly listeners", x => x.money?.generated?.mid && x.ml ? x.money.generated.mid * 12 / x.ml : null, v => "$" + v.toFixed(2), "C"],
    ["Chart countries", "Spotify weekly top 200 or Apple Music daily top 100", x => x.reach, v => String(v), "measured"]];
  const rows = M.map(([l, d, f, fmt, g]) => { const me = f(a), vs = near.map(f).filter(v => v != null && isFinite(v)).sort((x, y) => x - y);
    if (me == null || !isFinite(me) || vs.length < 5) return `<tr><td class="l">${esc(l)}</td><td>–</td><td>–</td><td>–</td><td>–</td></tr>`;
    const below = vs.filter(v => v < me).length, same = vs.filter(v => v === me).length, p = Math.round((below + same / 2) / vs.length * 100);
    return `<tr><td class="l">${esc(l)} ${g === "measured" ? chip("measured") : g ? grade(g) : ""}<br><span class="note">${esc(d)}</span></td><td><b>${fmt(me)}</b></td><td>${fmt(median(vs))}</td><td>${fmt(vs[0])}–${fmt(vs.at(-1))}</td><td><b>${ord(p)}</b><br><span class="note">above ${below} of ${vs.length}${same ? `, level with ${same}` : ""}</span></td></tr>`; });
  const lo = Math.min(...near.map(p => p.ml)), hi = Math.max(...near.map(p => p.ml));
  return `<section class="panel" id="peers"><h2>Against the 10 nearest artists</h2>
    <div class="tablebox"><table class="stack"><thead><tr><th class="l">Measure</th><th>${esc(a.name)}</th><th>Peers' median</th><th>Peers' range</th><th>Percentile</th></tr></thead><tbody>${rows.join("")}</tbody></table></div>
    <p class="note"><b>Nearest</b>: the 10 artists in this hip-hop list closest to ${esc(a.name)} in Spotify monthly listeners, measured as a ratio (2m and 8m are equally far from 4m): ${count(lo)} to ${count(hi)}. Second Spotify profiles and artists below 500k (no listener count) are left out. Percentile: the share of those peers below ${esc(a.name)}, ties counted half. Royalties are our estimate (grade C) of Spotify only, the one service measured for every artist; the Scout score is ours. Peers: ${near.map(p => `<a href="#/a/${p.id}">${esc(p.name)}</a>`).join(", ")}.</p></section>`;
}

// ---------- unsigned prospects export (A&R, 2026-10-26, ROADMAP 11.12): the Unsigned page's prospects as CSV, with
// the official public profiles we hold (src/site_build.py public_links) and never personal contact data
function unsignedCsv(U) {
  const byId = Object.fromEntries(store.data.artists.map(a => [a.id, a])), g = GENRE === "country" ? "country" : "hip-hop";
  const page = a => a?.slug ? `${SITE_URL}${GDIR()}a/${a.slug}/` : `${SITE_URL}${PREFIX()}a/${a?.id || ""}`;
  const ev = u => LICENSED.test(u.label || "") && !SERVICES.test(u.label || "") ? "licensed out (may be a licence or services deal)" : u.confidence === "confirmed" ? "confirmed (release label and recording codes)" : "label name only";
  download(`tventy-music-${g}-unsigned-prospects.csv`, [["name", "spotify_url", "youtube_channel_url", "instagram_url", "wikidata_url", "tventy_page", "country", "release_label", "unsigned_evidence", "why_a_prospect",
    "monthly_listeners", "current_listeners", "share_on_recent_releases", "streams_a_day_per_listener", "share_of_streams_as_featured_guest", "royalties_generated_mid_usd_year", "artist_keeps_now_mid_usd_year", "signed_peers_generate_median_usd_year",
    "scout_score", "scout_tier", "links_source", "listeners_source", "money_grade", "data_as_of", "note"],
    ...U.map(u => { const a = byId[u.id], L = u.links || {};
      return [u.name, L.spotify || `https://open.spotify.com/artist/${u.id}`, L.youtube || "", L.instagram || "", L.wikidata || "", page(a || u), a?.country || "", u.label || "", ev(u), (u.indie_basis || []).join("; "),
        u.floor ? "under 500k" : u.ml ?? "", u.floor ? "" : u.cl ?? "", u.cur_share ?? "", u.spl != null ? +u.spl.toFixed(3) : "", u.feat ?? "", u.generated ?? "", u.keeps_now ?? "", u.feat > 0.9 ? "" : u.peer_generated ?? "",
        a?.scout?.score ?? "", a?.scout?.tier || "", "Spotify: kworb.net; YouTube channel: Wikidata P2397, else MusicBrainz; Instagram: Wikidata P2003", "Spotify public counts via kworb.net (measured)",
        "C (estimate)", store.data.as_of, "official public profiles only, no personal contact data; unsigned = no label deal on record, from release labels and recording codes; tventy music"]; })]);
}

// ---------- tours by size band (investors and managers, 2026-10-26, ROADMAP 11.18): on Tours, the counted tours
// grouped by the artist's monthly listeners today, with median gross per show and per ticket in each band
function toursByBand(T) {
  const byId = Object.fromEntries(store.data.artists.map(a => [a.id, a]));
  const bandOf = a => !a ? null : a.floor || !a.ml ? "under 500k (by streams)" : BANDS[[1.5e6, 3e6, 6e6, 15e6].filter(x => a.ml >= x).length];
  const order = ["15m+", "6-15m", "3-6m", "1.5-3m", "under 1.5m", "under 500k (by streams)"];
  const by = {}; T.forEach(t => { const b = bandOf(byId[t.id]); if (b) (by[b] = by[b] || []).push(t); });
  const bs = order.filter(b => by[b]);
  if (!bs.length) return "";
  const nm = b => b === "under 1.5m" && GENRE === "country" ? "500k–1.5m" : b.replace(/(\d)-(\d)/, "$1–$2");
  return `<section class="panel"><h2>By the artist's size</h2><div class="tablebox"><table class="stack"><thead><tr><th class="l">Monthly listeners today</th><th>Tours</th><th>Artists</th><th>Median gross per show</th><th>Median gross per ticket</th><th>Median tickets per show</th></tr></thead><tbody>
    ${bs.map(b => { const ts = by[b], few = ts.length < 3;
      return `<tr><td class="l"><b>${esc(nm(b))}</b>${few ? `<br><span class="note">few tours: read with care</span>` : ""}</td><td>${ts.length}</td><td>${new Set(ts.map(t => t.id)).size}</td><td>${usd(median(ts.map(t => t.per_show)))}</td><td>${usd(median(ts.map(t => t.per_fan)))}</td><td>${count(median(ts.filter(t => t.tickets && t.shows).map(t => Math.round(t.tickets / t.shows))))}</td></tr>`; }).join("")}
  </tbody></table></div>
  <p class="note">Bands by each artist's Spotify monthly listeners today, not at the time of the tour. Medians over the tours with that figure; a co-headlined tour counts whole here. Coverage: only tours whose box office was reported to Billboard Boxscore or Pollstar (grades A and B) are counted. Reporting is voluntary and comes from promoters and venues, so the biggest arena and stadium tours are well covered and smaller club and theatre tours, festival fees and most dates outside North America and Europe are not: the smaller bands rest on few tours and lean towards the artists who report. Where a gross covers only part of a tour, its shows and tickets are those of the same window.</p></section>`;
}

// ---------- router
// extra.json split by page (src/site_build.py PARTS, 2026-10-26): scout.json holds all Scout reads beyond the index,
// unsigned.json only the Unsigned page's. NEEDS: the files a page reads; a page not listed loads them all. Before
// listing a page, grep its store.data.* and artist-field uses against PARTS.
const PARTS = ["extra", "scout", "unsigned"];
const NEEDS = { scout: ["scout"], ...Object.fromEntries("movers month rising compare producers state pay platforms tours audience method worth labels label screener sheet quality genres".split(" ").map(p => [p, ["extra", "scout"]])),
  press: ["extra", "unsigned"], changelog: ["extra"], glossary: [] };  // glossary: the index's scout_factors only
let routeSeq = 0;
async function route() {
  const seq = ++routeSeq;
  // a static page (site/a/<slug>/, site/label/<slug>/) opens its artist or label until the visitor navigates
  let h = (location.hash || window.BOOT || "").replace(/^#\/?/, "").replace(/\?.*$/, "").split("/");
  GENRE = h[0] === "country" ? "country" : "hip_hop";
  if (GENRE !== "hip_hop") h = h.slice(1).length ? h.slice(1) : [""];
  document.documentElement.dataset.genre = GENRE;
  document.querySelectorAll("[data-genre]").forEach(a => a.dataset.genre === GENRE ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
  document.querySelectorAll(".mainnav a").forEach(a => { const base = a.dataset.href || a.getAttribute("href"); a.dataset.href = base; a.setAttribute("href", GENRE === "hip_hop" ? base : PREFIX() + base.slice(2)); });
  // a page that needs extra.json starts it alongside the index rather than after it
  const want = h[0] === "" || h[0] === "a" ? [] : NEEDS[h[0]] || PARTS;
  const early = Object.fromEntries(want.filter(p => !genreStore[GENRE]?.parts?.[p]).map(p => [p, getJSON(`${DATA_DIR()}${p}.json`)]));
  Object.values(early).forEach(p => p.catch(() => {}));  // a failure is reported where it is awaited
  if (!genreStore[GENRE]) { const k = GENRE, d = await getJSON(`${DATA_DIR()}index.json`).catch(e => { if (seq === routeSeq) throw e; }); if (d && !genreStore[k]) genreStore[k] = { data: d }; }
  if (seq !== routeSeq) return;
  const g = genreStore[GENRE];
  // page-specific data loads in the background (D6); pages other than the start page and artist pages wait for it.
  // (A genre first loaded by a cross-genre search has its index but not this yet.)
  // artist_more: per-artist fields only those pages read (src/site_build.py LATER), one array per field in the
  // index's artist order, merged back into the artist rows. A failed load is forgotten, so the next page tries again.
  // The start page and artist pages start it only once drawn, so it does not slow their own downloads.
  // extra.json is split by page (PARTS); each file is merged once and, if it fails, tried again on the next page
  const parts = g.parts = g.parts || {}, have = g.have = g.have || {}, dir = DATA_DIR();  // this genre's, even if a later route switches
  const loadPart = p => parts[p] || (parts[p] = (early[p] || getJSON(`${dir}${p}.json`)).then(x => { const more = x.artist_more || {}; delete x.artist_more;
    for (const k in more) if (more[k].length === g.data.artists.length) g.data.artists.forEach((a, i) => { a[k] = more[k][i]; });
    have[p] = true; return Object.assign(g.data, x); }).catch(e => { delete parts[p]; throw e; }));
  const loadExtra = (ps = PARTS) => Promise.all(ps.map(loadPart));
  store.data = genreStore[GENRE].data;
  const NAMES = { movers: ["Artists", "Movers"], month: ["Artists", "Movers"], rising: ["Artists", "Movers"], compare: ["Artists", "Compare"],
    scout: ["Scout"], unsigned: ["Scout", "Unsigned vs signed peers"], producers: ["Scout", "Producers"],
    worth: ["Money"], pay: ["Money", "Pay gap by deal"], platforms: ["Money", "Platforms"], tours: ["Money", "Tours"],
    labels: ["Labels"], audience: ["Labels", "Where it is streamed"], method: ["Method"], state: ["State of hip-hop"] };
  const SEC = { Artists: "#/", Scout: "#/scout", Money: "#/worth", Labels: "#/labels", Method: "#/method" };
  crumbs((NAMES[h[0]] || []).map((t, i, xs) => [t, i < xs.length - 1 ? SEC[t] : ""]));
  const TITLES = { rising: "Rising hip-hop artists today", month: "Hip-hop movers: the past month", movers: h[1] === "today" ? "Hip-hop movers today" : "Hip-hop movers: the past month", pay: "Pay gap by record deal",
    platforms: "Hip-hop royalties by streaming platform", tours: "Hip-hop tours: gross and revenue per fan", audience: "Where hip-hop is streamed",
    unsigned: "Unsigned hip-hop artists against signed peers", method: "Method and sources", scout: "Scout: rising hip-hop artists for A&R",
    worth: "What is your music worth?", state: "State of hip-hop: the month in numbers", producers: "The producers and songwriters behind hip-hop's biggest songs", labels: "Who owns hip-hop: labels and market share", compare: "Compare hip-hop artists" };
  if (want.length) { if (!want.every(p => have[p])) app.innerHTML = `<p class="note">Loading…</p>`; await loadExtra(want).catch(e => { if (seq === routeSeq) throw e; }); }
  if (seq !== routeSeq) return;  // the visitor moved on while this page's files loaded: the newer route draws (or reports) its page
  setMeta(TITLES[h[0]] || "Global hip-hop: listeners, earnings and labels of the top 1,000 artists");
  if (h[0] === "a") await artist(decodeURIComponent(h[1]));  // awaited: the footer below must not show (and then jump) before the page
  else if (h[0] === "rising") rising();
  else if (h[0] === "movers") (h[1] === "today" ? rising() : monthPage());
  else if (h[0] === "month") monthPage();
  else if (h[0] === "producers") producersPage();
  else if (h[0] === "state") statePage(h[1]);
  else if (h[0] === "pay") pay();
  else if (h[0] === "platforms") platforms();
  else if (h[0] === "tours") tours();
  else if (h[0] === "audience") audience();
  else if (h[0] === "unsigned") { readScreen("unsigned"); unsignedPage(); }
  else if (h[0] === "method") method();
  else if (h[0] === "scout") { readScreen("scout"); scoutPage(); }
  else if (h[0] === "worth") { if (h[1]) { const a = store.data.artists.find(x => x.id === h[1]); ui.worth = { ...(ui.worth || { ml: 1000000, vintage: "auto" }), pick: h[1], deal: a && ["diy", "services", "independent", "major"].includes(a.deal_type) ? a.deal_type : "unknown" }; } worthPage(); }
  else if (h[0] === "labels") { if (h[1] === "owner" && h[2]) ui.labf = { q: "", sort: ["ml", -1], ...(ui.labf || {}), group: decodeURIComponent(h[2]) }; labelsPage(); if (h[1] === "owner") setTimeout(() => document.getElementById("labeldir")?.scrollIntoView()); }
  else if (h[0] === "label") (h[2] === "sheet" ? labelSheet : labelPage)(decodeURIComponent(h[1] || ""));
  else if (h[0] === "compare") compare(h.slice(1).map(decodeURIComponent));
  else if (h[0] === "screener") { readScreen("screener"); screenerPage(); }
  else if (h[0] === "sheet") await sheetPage(decodeURIComponent(h[1] || ""));
  else if (h[0] === "quality") qualityPage();
  else if (h[0] === "genres") await genresPage();
  else if (h[0] === "press") pressPage();
  else if (h[0] === "changelog") changelogPage();
  else if (h[0] === "glossary") glossaryPage();
  else if (h[0] === "") top();
  else notFound();
  document.getElementById("foot").innerHTML = `Data as of ${esc(store.data.as_of)}; built ${esc(store.data.built)}. Sources: kworb.net (Spotify public counts), Wikidata, MusicBrainz, Deezer, Wikimedia Commons. Estimates are ranges, not reported figures. <a href="#/state">State of ${GENRE === "country" ? "country" : "hip-hop"}</a> · <a href="#/press">Press</a> · <a href="#/method">Method</a> · <a href="#/changelog">Method changelog</a> · <a href="#/quality">Data quality and corrections</a> · <a href="#/glossary">Glossary</a> · <a href="mailto:hello@tventy.se?subject=Correction">Report a correction</a> · <a href="https://tventy.se/sport/">tventy sport</a>`;
  prefixLinks(document.getElementById("foot"));  // country: footer links keep the genre (new tab, copied link)
  window.scrollTo(0, 0);
  if (!PARTS.every(p => parts[p])) setTimeout(() => loadExtra().catch(() => {}), 0);  // in the background, for the next page
}
function setMeta(title, desc) {
  desc = desc || "Who is drawing an audience in hip-hop, what the music earns, who owns it and who is about to break: the top 1,000 artists, updated daily, every figure sourced.";
  if (GENRE === "country") { title = title.replace(/Hip-hop|Hip-Hop/g, "Country").replace(/hip-hop/g, "country"); desc = desc && desc.replace(/hip-hop/g, "country"); }
  if (store.data?.artists) { const n = s => s && s.replace(/\b(top|Top|the) 1,000\b/g, `$1 ${measured()}`); title = n(title); desc = n(desc); }  // the list's own size (country 754)
  document.title = `${title} · tventy music`;
  const m = document.querySelector('meta[name="description"]');
  if (m) m.content = desc || "Who is drawing an audience in hip-hop, what the music earns, who owns it and who is about to break: the top 1,000 artists, updated daily, every figure sourced.";
}
addEventListener("hashchange", () => route().catch(loadFailed));
bindSearchBox(document.getElementById("q"), document.getElementById("q-results"), true);
route().catch(loadFailed);
