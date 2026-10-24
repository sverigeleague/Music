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
const pic = (a, big) => a.photo
  ? `<img class="pic${big ? " big" : ""}" src="${esc(a.photo.file)}" alt="" loading="lazy" decoding="async" data-initials="${esc(initials(a.name))}">`
  : `<span class="pic none${big ? " big" : ""}" aria-hidden="true">${esc(initials(a.name))}</span>`;
function count(v) {
  if (v == null) return "–";
  const a = Math.abs(v);
  return a >= 1e12 ? (v / 1e12).toFixed(2) + "tn" : a >= 1e9 ? (v / 1e9).toFixed(2) + "bn" : a >= 1e6 ? (v / 1e6).toFixed(1) + "m" : a >= 1e3 ? (v / 1e3).toFixed(0) + "k" : String(v);
}
const usd = v => v == null ? "–" : Math.abs(v) < 10 && v !== 0 ? "$" + v.toFixed(2) : "$" + count(Math.round(v));
const range = r => r ? `${usd(r.low)}–${usd(r.high)}` : "–";
const delta = v => v == null ? "–" : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${v > 0 ? "+" : ""}${count(v)}</span>`;
const pct = v => v == null ? "–" : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${v > 0 ? "+" : ""}${v.toFixed(2)}%</span>`;
const cell = (a, [, key, f]) => {
  const v = key === "gen_mid" ? a.money?.generated.mid : key === "scout" ? a.scout?.score : a[key];
  if (key === "cl" && a.cl_provisional && v != null) return `${count(v)}<span class="prov" title="Provisional: 50–80% of streams dated; could be ${count(a.cl_range[0])}–${count(a.cl_range[1])}">*</span>`;
  return f === "count" ? count(v) : f === "delta" ? delta(v) : f === "pct" ? pct(v) : f === "money" ? usd(v)
    : f === "share" ? (v == null ? "–" : Math.round(v * 100) + "%") : f === "int" ? (v ?? "–") : esc(v);
};
const chip = (t, title) => `<span class="chip" title="${esc(title || "")}">${esc(t)}</span>`;
const grade = g => `<span class="chip c" title="A primary, B reputable secondary, C our estimate">${esc(g)}</span>`;
// Five sections in the header; each page belongs to one, and sections with several pages show a sub-menu.
// Four sections in the header (owner, 2026-10-24, D1); each page belongs to one, and sections with several pages
// show a sub-menu. Method sits in the footer.
const SECTION = { top: "artists", movers: "artists", month: "artists", rising: "artists", compare: "artists", artist: "artists",
  scout: "scout", unsigned: "scout", producers: "scout",
  worth: "money", pay: "money", platforms: "money", tours: "money",
  labels: "labels", label: "labels", audience: "labels", method: "" };
const SUBNAV = {
  artists: [["top", "#/", "Top list"], ["movers", "#/movers", "Movers"], ["compare", "#/compare", "Compare"]],
  scout: [["scout", "#/scout", "Scout list"], ["unsigned", "#/unsigned", "Unsigned vs signed peers"], ["producers", "#/producers", "Producers"]],
  money: [["worth", "#/worth", "What is it worth?"], ["pay", "#/pay", "Pay gap by deal"], ["platforms", "#/platforms", "Platforms"], ["tours", "#/tours", "Tours"]],
  labels: [["labels", "#/labels", "Labels and market share"], ["audience", "#/audience", "Where it is streamed"]],
};
// Movers: today (daily change, outside the top 100) and the last 30 days, one page with a switch
const moversSwitch = on => `<div class="seg" role="group" aria-label="Period" style="margin:10px 0 4px"><a class="segbtn" href="#/movers/today"${on === "today" ? ' aria-current="page"' : ""}>Today</a><a class="segbtn" href="#/movers"${on === "month" ? ' aria-current="page"' : ""}>Last 30 days</a></div>`;
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
    .map(([, a]) => ({ href: `#/a/${a.id}`, icon: pic(a), t: a.name, sub: `#${a.rank} · ${count(a.ml)} monthly listeners${a.label_name ? " · " + a.label_name : ""}` }));
  const L = (store.data.labels || []).map(x => [score(x.name), x]).filter(x => x[0] < 9).sort((x, y) => x[0] - y[0] || y[1].ml - x[1].ml).slice(0, 4)
    .map(([, x]) => ({ href: `#/label/${x.slug}`, icon: logo(x.name), t: x.name, sub: `Label · ${x.artists.length} artists in the top 1,000` }));
  return [...A, ...L];
}
function bindSearchBox(input, box, global) {
  let hits = [], at = 0;
  const close = () => { box.hidden = true; input.setAttribute("aria-expanded", "false"); };
  const draw = () => {
    hits = searchFor(input.value); at = 0;
    if (!input.value.trim()) return close();
    box.innerHTML = hits.length ? hits.map((x, i) => `<a role="option" href="${x.href}" aria-selected="${i === at}">${x.icon}<span>${esc(x.t)}<small>${esc(x.sub)}</small></span></a>`).join("")
      : `<p class="note" style="padding:10px 12px;margin:0">No match. Try an artist or a label.</p>`;
    box.hidden = false; input.setAttribute("aria-expanded", "true");
  };
  const mark = () => box.querySelectorAll("a").forEach((a, i) => a.setAttribute("aria-selected", i === at));
  input.addEventListener("input", draw);
  input.addEventListener("focus", () => input.value && draw());
  input.addEventListener("keydown", ev => {
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") { ev.preventDefault(); at = (at + (ev.key === "ArrowDown" ? 1 : -1) + hits.length) % Math.max(1, hits.length); mark(); }
    else if (ev.key === "Enter" && hits[at]) { go(hits[at].href); input.value = ""; close(); input.blur(); }
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
const genreStore = {};
function swapWords(root) {
  if (GENRE !== "country" || !root) return;
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode())
    if (/hip[- ]hop|1,000/i.test(n.nodeValue)) n.nodeValue = n.nodeValue.replace(/hip-hop or rap/g, "country")
      .replace(/Hip-Hop|Hip-hop/g, "Country").replace(/hip-hop|hip hop/g, "country")
      .replace(/\b(top|Top|the) 1,000\b/g, `$1 ${measured()}`);  // the country list is smaller than hip-hop's
}
// the country list's size: artists with a measured audience (above Spotify's public 500k floor)
const measured = () => (store.data?.artists?.length || 1000).toLocaleString();
new MutationObserver(() => { swapWords(document.getElementById("app")); swapWords(document.getElementById("crumbs")); })
  .observe(document.getElementById("app"), { childList: true, subtree: true });
const go = hash => { location.hash = GENRE !== "hip_hop" && hash.startsWith("#/") && !hash.startsWith(PREFIX()) ? PREFIX() + hash.slice(2) : hash; };
document.addEventListener("click", e => {
  const a = e.target.closest('a[href^="#/"]');
  if (!a || GENRE === "hip_hop" || a.dataset.genre || e.defaultPrevented || e.metaKey || e.ctrlKey) return;
  const href = a.getAttribute("href");
  if (href.startsWith(PREFIX()) || href === "#/state" || href.startsWith("#/state/") || href === "#/method") return;
  e.preventDefault();
  go(href);
});

// Per-artist detail lives in 32 shard files (src/site_build.py): <data>/a/<second character's code % 32>.json.
const shards = {};
async function detailOf(id) {
  const n = id.charCodeAt(1) % 32;  // the second character: Spotify IDs all start with 0-7
  const key = GENRE + n;
  try { shards[key] = shards[key] || await (await fetch(`${DATA_DIR()}a/${n}.json`)).json(); } catch { shards[key] = {}; }
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
  const body = sorted.map(a => `<tr><td class="l">${a[rankKey]}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td>${COLS.map(c => `<td>${cell(a, c)}</td>`).join("")}
    <td class="l">${a.label_status === "major" || a.label_status === "major_distributed" ? esc(a.label_owner || "Major") : a.label_status === "independent" ? "Independent label" : a.label_status === "self_released" ? "Unsigned" : a.label_status === "catalog" ? "Catalog" : (a.major ? esc(a.major) : "–")}${a.revivals?.length ? " " + chip("Revival", a.revivals.map(r => `${r.title} (${r.year})`).join(", ")) : ""}</td></tr>`).join("");
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th>${head}<th class="l">Label group</th></tr></thead><tbody>${body}</tbody></table></div>`;
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
  return all.filter(a => a.cl_rank && a.cl_rank <= n).sort((a, b) => a.cl_rank - b.cl_rank).map(a => ({ ...a, pos: a.cl_rank }));
}
const sizeSwitch = rerender => `<div class="seg" role="group" aria-label="List size" style="margin-top:12px"><button type="button" data-size="100" aria-pressed="${ui.size === 100}">Top 100</button><button type="button" data-size="1000" aria-pressed="${ui.size === 1000}">Top 1,000</button></div>`;
const bindSize = rerender => app.querySelectorAll("[data-size]").forEach(b => b.onclick = () => { ui.size = +b.dataset.size; rerender(); });
function top() {
  nav("top");
  const d = store.data, all = d.artists, hundred = top100();
  const list = hundred.filter(a => a.name.toLowerCase().includes(ui.q));
  const N = ui.size === 1000 ? "1,000" : "100";
  const ml = hundred.reduce((s, a) => s + a.ml, 0);
  const gen = hundred.reduce((s, a) => s + (a.money?.generated.mid || 0), 0);
  const up = [...hundred].sort((a, b) => (b.chg_pct ?? -1e9) - (a.chg_pct ?? -1e9))[0];
  const majors = hundred.filter(a => a.label_status === "major" || a.label_status === "major_distributed").length;
  const unranked = all.filter(a => a.cl == null);
  const sub = ui.by === "current"
    ? `Ranked by current listeners: each artist's monthly listeners, counting the listening that comes from recent releases, so songs from years ago that are still streamed a lot do not decide the order. ${esc(d.as_of)}.`
    : `Ranked by Spotify monthly listeners, ${esc(d.as_of)}.`;
  const scoutTop = all.filter(x => x.scout?.tier === "Breaking").sort((x, y) => y.scout.score - x.scout.score).slice(0, 3);
  const labelsN = (d.labels || []).length, total = all.reduce((s, a) => s + a.ml, 0);
  app.innerHTML = `<section class="hero"><h1>Global Hip-Hop</h1>
      <p class="lede">Who is really drawing an audience in hip-hop right now, what their music earns, who owns it, and who is about to break. ${all.length.toLocaleString()} artists, updated daily, every figure sourced. <a href="#/state">This month in numbers →</a></p>
      <div class="stats"><div><b>${all.length.toLocaleString()}</b><span>hip-hop artists tracked, of Spotify's top ${d.universe.toLocaleString()}</span></div><div><b>${count(total)}</b><span>combined monthly listeners</span></div><div><b>${labelsN}</b><span>labels with artists in the top 1,000</span></div><div><b>${esc(d.as_of)}</b><span>listener data as of</span></div></div></section>
    ${pulse()}
    <section class="doors">
      <a class="door" href="#/worth"><span class="k">For artists</span><b>What is your music worth?</b><span>Royalties, what you keep under each deal, and what the catalog would sell for.</span></a>
      <a class="door" href="#/scout"><span class="k">For labels</span><b>Find who is rising</b><span>${scoutTop.length ? `Breaking now: ${scoutTop.map(x => esc(x.name)).join(", ")}.` : "Momentum scores for the top 1,000."} Filter to unsigned artists and export.</span></a>
      <a class="door" href="#/labels"><span class="k">Market</span><b>Who owns hip-hop</b><span>The majors' and independents' share of the top 1,000, by size.</span></a>
    </section>
    
    ${subnav()}<section><h1>Top ${N} hip-hop artists on Spotify</h1>
    <p class="sub">${sub} ${all.length.toLocaleString()} of Spotify's top ${d.universe.toLocaleString()} artists are hip-hop or rap.</p>
    <div class="seg" role="group" aria-label="Ranking" style="margin-top:12px"><button type="button" data-by="current" aria-pressed="${ui.by === "current"}">Our ranking: current listeners</button><button type="button" data-by="monthly" aria-pressed="${ui.by === "monthly"}">Monthly listeners</button></div> ${sizeSwitch()}</section>
    <section class="tiles">
      <div class="tile"><div class="k">Combined monthly listeners</div><div class="v">${count(ml)}</div><div class="s">these ${N}, people counted once per artist</div></div>
      <div class="tile"><div class="k">Royalties generated / month</div><div class="v">${usd(gen)}</div><div class="s">Spotify recordings, top ${N}, mid estimate ${grade("C")}</div></div>
      <div class="tile"><div class="k">Biggest riser today in this top ${N}</div><div class="v">${up ? esc(up.name) : "–"}</div><div class="s">${up ? pct(up.chg_pct) + " listeners" : ""}</div></div>
      <div class="tile"><div class="k">On a major label</div><div class="v">${majors} of ${hundred.length}</div><div class="s">from the labels on their recent releases</div></div>
    </section>
    <section><div class="toolbar"><input type="search" placeholder="Filter this list" value="${esc(ui.q)}" aria-label="Filter this list"></div>
      ${table(list, "pos")}<p class="note">${ui.by === "current" ? "* Provisional rank: 50–80% of the artist's streams are on dated songs; hover for the range. " : ""}Royalties generated are what Spotify pays the rights holders for the artist's own tracks (label or distributor), not the artist's pay. See the artist page and Pay gap.${ui.by === "current" && unranked.length ? ` Not yet ranked, because release dates are missing for too much of their listening: ${unranked.map(a => esc(a.name)).join(", ")}.` : ""}</p></section>`;
  if (d.below_floor?.length && ui.size === 1000) {
    app.insertAdjacentHTML("beforeend", belowFloor(d.below_floor, all.length));
    app.querySelector("#floorall")?.addEventListener("click", () => { ui.floorAll = true; top(); });
  }
  app.querySelectorAll("[data-by]").forEach(b => b.onclick = () => { ui.by = b.dataset.by; ui.sort = [ui.by === "current" ? "cl" : "ml", -1]; top(); });
  bindSize(top);
  const inp = app.querySelector("input");
  inp.oninput = () => { ui.q = inp.value.toLowerCase(); const p = inp.selectionStart; top(); const i = app.querySelector("input"); i.focus(); i.setSelectionRange(p, p); };
  bindSort(top);
}

// Country ranks past the measured list (owner C1): artists under kworb's 500k-listener floor, in Deezer's track
// popularity order. An order, not a size: no listener figure exists for them.
function belowFloor(rows, measured) {
  return `<section class="panel" id="below"><h2>${measured + 1}–${rows[rows.length - 1].pos}: below the 500k line ${grade("C")}</h2>
    <p class="note">Spotify's public listener counts stop at about 500,000 monthly listeners, so these artists have no measured audience here. They are listed in the order of their songs' popularity on Deezer, a rough guide only: it can misplace artists of a similar size, and newer US acts are under-represented on Deezer. Only artists with a release in the last three years.</p>
    <ol class="floorlist" start="${measured + 1}">${rows.slice(0, ui.floorAll ? rows.length : 60).map(r => `<li>${r.spotify ? `<a href="https://open.spotify.com/artist/${esc(r.spotify)}" target="_blank" rel="noopener">${esc(r.name)}</a>` : `<a href="https://www.deezer.com/artist/${esc(r.deezer)}" target="_blank" rel="noopener">${esc(r.name)}</a>`} <span class="note" title="latest release">${esc(r.year)}</span></li>`).join("")}</ol>
    ${!ui.floorAll && rows.length > 60 ? `<p class="more"><button type="button" class="btn" id="floorall">Show all ${rows.length}</button></p>` : ""}
    <p class="note">Found through Deezer's related-artists links from its country charts and Wikidata, kept when at least half of an artist's releases are filed under Country. Data: Deezer.</p></section>`;
}

function rising() {
  nav("movers");
  const inTop = new Set(top100().map(a => a.id)), rest = store.data.artists.filter(a => !inTop.has(a.id) && a.chg_pct != null);
  const list = [...rest].sort((a, b) => b.chg_pct - a.chg_pct).slice(0, RISING_LIMIT).map((a, i) => ({ ...a, rrank: i + 1 }));
  app.innerHTML = `${subnav()}<section><h1>Movers: today</h1>${moversSwitch("today")}
    <p class="sub">Biggest daily gains in monthly listeners among the ${rest.length} hip-hop artists outside the top 100. Daily moves are noisy; for momentum scored against artists of the same size, see <a href="#/scout">Scout</a>.</p></section>
    <section>${tableRising(list)}</section>`;
}
function tableRising(list) {
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th>Hip-hop rank</th><th>Monthly listeners</th><th>Today</th><th>Today %</th><th>Peak listeners</th></tr></thead><tbody>
  ${list.map(a => `<tr><td class="l">${a.rrank}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td>${a.rank}</td><td>${count(a.ml)}</td><td>${delta(a.chg)}</td><td>${pct(a.chg_pct)}</td><td>${count(a.peak_ml)}</td></tr>`).join("")}</tbody></table></div>`;
}

// ---------- unsigned
const STATUS = { major: "Major label", major_distributed: "Major's distribution", independent: "Independent label", self_released: "Unsigned (self-released)", catalog: "Catalog (no release in 2 years)", unknown: "Not yet classified" };
function unsignedPage() {
  nav("unsigned");
  const U = store.data.unsigned || [], sh = Object.fromEntries(store.data.deals.map(d => [d.deal_type, d]));
  const pct = k => Math.round(+sh[k].mid * 100) + "%";
  const be = U[0]?.break_even || {};
  app.innerHTML = `${subnav()}<section><h1>Unsigned</h1>
    <p class="sub">Hip-hop artists releasing without a label, ranked by current listeners, each set against the five growing signed artists closest to them in audience. Unsigned means the label on their recent releases is a distributor or their own name, not a record label, checked against the recording codes of their recent songs where possible.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Unsigned in the hip-hop list</div><div class="v">${U.length}</div><div class="s">${U.filter(u => u.confidence === "confirmed").length} confirmed by distributor or recording codes</div></div>
      <div class="tile"><div class="k">Keeps today, unsigned</div><div class="v">${pct("diy")}</div><div class="s">of recording royalties, after the distributor's fee</div></div>
      <div class="tile"><div class="k">Keeps on a major deal</div><div class="v">${pct("major")}</div><div class="s">so a deal must grow streams ${be.major}× to pay the same ${grade("A")}</div></div>
      <div class="tile"><div class="k">Independent label / label services</div><div class="v">${pct("independent")} / ${pct("services")}</div><div class="s">break even at ${be.independent}× / ${be.services}× the streams</div></div>
    </section>
    <section><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Release label</th><th>Monthly listeners</th><th>Current listeners</th><th>Generates / yr</th><th>Keeps now</th><th>Signed peers generate</th><th>On a major deal would keep</th><th>Scout</th></tr></thead><tbody>
      ${U.slice(0, ui.unsAll ? U.length : 50).map((u, i) => `<tr><td class="l">${i + 1}</td><td class="l"><a class="who" href="#/a/${u.id}">${pic(store.data.artists.find(a => a.id === u.id) || u)}<span>${esc(u.name)}</span></a></td>
        <td class="l wrap">${esc(u.label || "–")} ${u.confidence === "confirmed" ? chip("confirmed") : `<span class="chip warn" title="Own-name label with no other evidence: could be a small label or an imprint licensed to one">label name only</span>`}</td>
        <td>${count(u.ml)}</td><td>${count(u.cl)}</td><td>${usd(u.generated)}${u.feat > 0.9 ? ` <span class="chip warn" title="${Math.round(u.feat * 100)}% of their streams come as a featured guest on other artists' songs; the money shown counts their own songs only. Featured artists are usually paid a fee or a share agreed with the lead artist.">own songs only</span>` : ""}</td><td>${usd(u.keeps_now)}</td><td>${usd(u.peer_generated)}</td><td>${usd(u.if_signed.major)}</td><td>${(s => s ? `${s.score} ${tierChip(s.tier)}` : "–")(store.data.artists.find(a => a.id === u.id)?.scout)}</td></tr>`).join("")}
    </tbody></table></div>
    ${!ui.unsAll && U.length > 50 ? `<p class="more"><button type="button" class="btn" id="unsall">Show all ${U.length}</button></p>` : ""}
    <p class="note">Yearly at today's pace, mid estimates, streaming only (all platforms). <b>Generates</b>: royalties paid for the recordings. <b>Keeps now</b>: ${pct("diy")} of that after a distributor's fee. <b>Signed peers generate</b>: the median of the five closest growing signed artists. <b>On a major deal</b>: ${pct("major")} of today's royalties, before any advance is recouped.</p></section>
    <section><h2>Each artist against their signed peers</h2>
      ${U.slice(0, ui.unsAll ? U.length : 50).map(u => `<details class="panel"><summary><b>${esc(u.name)}</b>: ${count(u.ml)} monthly listeners, ${u.spl ? u.spl.toFixed(2) : "–"} streams a day per listener against ${u.peer_spl ? u.peer_spl.toFixed(2) : "–"} for the peers</summary>
        <div class="tablebox"><table><thead><tr><th class="l">Peer</th><th class="l">Label</th><th>Monthly listeners</th><th>Streams / day per listener</th><th>Generates / yr</th><th>Artist's slice</th></tr></thead><tbody>
        ${u.peers.map(p => `<tr><td class="l"><a href="#/a/${p.id}">${esc(p.name)}</a></td><td class="l">${esc(STATUS[p.status])}${p.owner ? " · " + esc(p.owner) : ""}</td><td>${count(p.ml)}</td><td>${p.spl ? p.spl.toFixed(2) : "–"}</td><td>${usd(p.generated)}</td><td>${usd(p.artist_slice)}</td></tr>`).join("")}
        <tr class="tot"><td class="l">${esc(u.name)} (unsigned)</td><td class="l">${esc(u.label || "")}</td><td>${count(u.ml)}</td><td>${u.spl ? u.spl.toFixed(2) : "–"}</td><td>${usd(u.generated)}</td><td>${usd(u.keeps_now)}</td></tr>
        </tbody></table></div>
        <p class="note">${u.at_peer_engagement ? `With the peers' streams per listener, ${esc(u.name)} would generate about ${usd(u.at_peer_engagement)} a year. ` : ""}Signed today, ${esc(u.name)} would keep about ${usd(u.if_signed.major)} on a major deal, ${usd(u.if_signed.independent)} with an independent label or ${usd(u.if_signed.services)} on label services, against ${usd(u.keeps_now)} now. Label money on signing (advances, marketing) is not public and not included.</p></details>`).join("")}
    </section>
    <p class="note">Peers: signed artists (major, major-distributed or independent label) with 0.6–1.67× the monthly listeners and at least 20% of their listening on recent releases, closest first. Statuses come from the labels printed on each artist's last two years of releases (Deezer) and the recording codes (ISRCs) of their recent songs; artists that cannot be placed are on the review list for the owner.</p>`;
  app.querySelector("#unsall")?.addEventListener("click", () => { ui.unsAll = true; unsignedPage(); });
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
    <section class="tablebox"><table><thead><tr><th class="l">Question</th><th class="l">What we have</th><th class="l">Status</th></tr></thead><tbody>
      <tr><td class="l"><b>Which countries</b></td><td class="l wrap">Each artist's streams in Spotify's weekly top 200 of 76 countries (kworb.net, ${weeksLabel()})</td><td class="l">${chip("measured")} for ${withGeo.length} of the top 100</td></tr>
      <tr><td class="l"><b>Which cities</b></td><td class="l wrap">Spotify shows each artist's top 5 cities on its own site, but its terms bar collecting them</td><td class="l">not collected</td></tr>
      <tr><td class="l"><b>Age and gender, per artist</b></td><td class="l wrap">Not public for any platform. Licensed providers (Soundcharts from $50 a month, Chartmetric) model it from Instagram, YouTube and TikTok followers</td><td class="l">needs a licence</td></tr>
      <tr><td class="l"><b>Hip-hop's audience as a whole</b></td><td class="l wrap">Surveys and industry reports, below</td><td class="l">${chip("reported")} genre level only</td></tr>
    </tbody></table></section>
    <section class="panel"><h2>Where the top 100's hits are streamed</h2>${markets.length ? geoBars(markets) : `<p class="note">No chart data yet.</p>`}
      <p class="note">Share of the top 100's combined streams in Spotify's weekly top 200 charts, by country (${weeksLabel()}). Big markets dominate, as they should; countries without a Spotify chart (China, most of Africa) are not covered.</p></section>
    <section class="panel"><h2>Hip-hop's audience, genre level</h2><ul>
      <li><b>The biggest genre in the US, shrinking:</b> R&amp;B/hip-hop had 349.9bn US on-demand audio streams in 2025, about 25% of the total, down 1.7 points in 2024. ${grade("B")} <a href="https://luminatedata.com/wp-content/uploads/2026/01/2025-Year-End-Music-Report-1.2026.pdf" target="_blank" rel="noopener">Luminate</a></li>
      <li><b>The most time with music:</b> people whose main genre is hip-hop/R&amp;B listen 3 hours 48 minutes a day, almost an hour more than the average American aged 13+. ${grade("B")} <a href="https://www.insideradio.com/free/edison-listeners-spending-most-daily-time-with-music-are-hip-hop-r-b-fans/article_798aa000-6358-483a-9f41-b8204aff6bcb.html" target="_blank" rel="noopener">Edison Research, Q2 2025</a></li>
      <li><b>Young:</b> net favourability of rap/hip-hop is +61 among US adults under 45 and −33 among those 45 and over, the widest age gap of any genre; 13% of under-45s call it their favourite genre. ${grade("B")} <a href="https://yougov.com/en-us/articles/45699-americans-opinions-different-music-genres-poll" target="_blank" rel="noopener">YouGov, 2023</a></li>
      <li><b>No reliable gender or ethnicity split</b> of hip-hop listeners has been published in recent years. Figures that circulate online are about 20 years old or unsourced, so they are not shown here.</li>
    </ul></section>
    <section><h2>Top ${ui.size === 1000 ? "1,000" : "100"} by country spread</h2><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Home</th><th>Countries charting</th><th>US top 200</th><th class="l">Best chart positions</th></tr></thead><tbody>
      ${hundred.map(a => `<tr><td class="l">${a.pos}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td class="l">${esc(a.country || "–")}</td><td>${a.geo ? a.geo.countries : "–"}</td><td>${a.geo && usPos(a.geo) ? "#" + usPos(a.geo) : "–"}</td><td class="l">${a.geo ? a.geo.charts.slice(0, 4).map(([cc, pos]) => `${esc(cname(cc))} #${pos}`).join(", ") : `<span class="note">not in any top 200</span>`}</td></tr>`).join("")}
    </tbody></table></div></section>`;
  bindSize(audience);
}

// ---------- tours
function tours() {
  nav("tours");
  const T = store.data.tours;
  const [sk, sd] = ui.tsort || ["gross", -1];
  const val = (t, k) => k === "net" ? t.artist_net.mid : t[k];
  const rows = [...T].sort((a, b) => ((val(a, sk) ?? -Infinity) > (val(b, sk) ?? -Infinity) ? 1 : -1) * sd);
  const best = [...T].filter(t => t.per_fan).sort((a, b) => b.per_fan - a.per_fan)[0];
  const top = T[0], sum = T.reduce((s, t) => s + t.gross, 0);
  const cols = [["Shows", "shows"], ["Tickets", "tickets"], ["Gross", "gross"], ["Per show", "per_show"], ["Per fan", "per_fan"], ["Artist's slice", "net"]];
  const steps = [["Venue, promoter and local costs", 0.35, "rent, staff, security, ticketing; the promoter keeps about 3% (Live Nation 10-K)"],
    ["Artist's production and crew", 0.30, "stage, lights, trucks, band, crew, travel: 25–45%"],
    ["Agent, manager, business manager", 0.15, "agent 10%, manager 15–20%, business manager 5% of the artist's fee"],
    ["Artist's slice", 0.20, "15–35% of gross, before tax"]];
  app.innerHTML = `${subnav()}<section><h1>Tours</h1>
    <p class="sub">Box office reported by Billboard Boxscore and Pollstar for tours since 2023 by artists in the top 100: how much a tour makes, per show and per fan, and an estimate of what reaches the artist.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Biggest tour</div><div class="v">${esc(top.artist)}</div><div class="s">${esc(top.tour)}: ${usd(top.gross)}</div></div>
      <div class="tile"><div class="k">Most money per fan</div><div class="v">${best ? usd(best.per_fan) : "–"}</div><div class="s">${best ? esc(best.artist) + ", " + esc(best.tour) : ""}</div></div>
      <div class="tile"><div class="k">Reported box office</div><div class="v">${usd(sum)}</div><div class="s">${T.length} tours, graded A or B</div></div>
    </section>
    <section class="panel"><h2>Where a ticket's money goes, roughly ${grade("C")}</h2>
      <div class="bars">${steps.map(([l, v, n]) => `<div class="barrow"><span>${esc(l)}</span><div class="track"><i style="left:0;width:${v * 100}%"></i></div><span>about ${Math.round(v * 100)}%</span></div><p class="note" style="margin:-4px 0 4px">${esc(n)}</p>`).join("")}</div>
      <p class="note">Industry rules of thumb, not reported figures: the split differs by deal (guarantee or door split) and by how big the production is. Stadium headliners keep more of the gross; a support act may keep little after costs.</p></section>
    <section><div class="tablebox"><table><thead><tr><th class="l">Artist</th><th class="l">Tour</th><th class="l">Dates</th>${cols.map(([l, k]) => `<th data-tsort="${k}"${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${l}</th>`).join("")}<th>Grade</th></tr></thead><tbody>
      ${rows.map(t => `<tr><td class="l">${t.id ? `<a href="#/a/${t.id}">${esc(t.artist)}</a>` : esc(t.artist)}</td><td class="l wrap">${esc(t.tour)}${t.co ? ` <span class="note">with ${esc(t.co)}${t.share < 1 ? ", half counted" : ""}</span>` : ""}${t.partial ? ` <span class="note" title="${esc(t.note)}">(part of the tour: Billboard's year to 30 Sep)</span>` : ""}</td><td class="l">${esc(t.start)}${t.end && t.end !== t.start ? " to " + esc(t.end) : ""}</td>
        <td>${t.shows ?? "–"}</td><td>${count(t.tickets)}</td><td>${usd(t.gross)}</td><td>${usd(t.per_show)}</td><td>${usd(t.per_fan)}</td><td>${range(t.artist_net)}</td><td>${grade(t.grade)} <a href="${esc(t.source)}" target="_blank" rel="noopener" title="${esc(t.note)}">source</a></td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Per fan = gross ÷ tickets sold. Artist's slice = 15–35% of gross (rule of thumb), half for a co-headline. Merch adds roughly $10–15 per fan in sales (ATVENU). Tours with no reported gross, such as Playboi Carti, GloRilla and Doechii, and most tours outside the US are not listed: Billboard and Pollstar publish no figure for them. Click a column to sort.</p></section>`;
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
  const val = (a, key) => key.startsWith("rev:") ? revOf(a, key.slice(4)) : a[key];
  const rows = [...hundred].sort((a, b) => ((val(a, sk) ?? -Infinity) > (val(b, sk) ?? -Infinity) ? 1 : -1) * sd);
  app.innerHTML = `${subnav()}<section><h1>Streaming platforms</h1>${sizeSwitch()}
    <p class="sub">What each service pays, what we can measure, and where the top 100's streaming money comes from. Spotify streams and YouTube views are measured. The other services publish no play counts, so their royalties are estimated from each artist's Spotify royalties, using each service's share of label streaming revenue in Warner and Universal's filings.</p></section>
    <section class="panel"><h2>Where the top ${ui.size === 1000 ? "1,000" : "100"}'s recording royalties come from, per year ${grade("C")}</h2>
      <div class="bars">${totals.map(([k, v]) => `<div class="barrow"><span>${esc(P[k]?.name || k)}${measured(k) ? " " + chip("measured") : ""}</span><div class="track"><i style="left:0;width:${v / max * 100}%"></i></div><span>${usd(v)} · ${Math.round(v / sum * 100)}%</span></div>`).join("")}</div>
      <p class="note">Mid estimates of royalties paid to the labels and distributors, before the artists' share: ${usd(sum)} a year in total.</p></section>
    <section><h2>How each service pays</h2><div class="tablebox"><table><thead><tr><th class="l">Service</th><th class="l">How it pays</th><th>Per 1,000 plays</th><th>Grade</th><th class="l">Our data</th></tr></thead><tbody>
      ${Object.values(P).map(p => `<tr><td class="l"><b>${esc(p.name)}</b></td><td class="l wrap">${esc(p.payout_model)}${M[p.platform] ? ` <span class="note">Our estimate: Spotify royalties × ${(+M[p.platform].low).toFixed(2)}–${(+M[p.platform].high).toFixed(2)}.</span>` : ""}</td><td>${rate(p)}</td><td>${grade(p.grade)}</td><td class="l wrap">${esc(p.our_data)}${p.source?.startsWith("http") ? ` <a href="${esc(p.source)}" target="_blank" rel="noopener">source</a>` : ""}</td></tr>`).join("")}
    </tbody></table></div></section>
    <section><h2>Top ${ui.size === 1000 ? "1,000" : "100"} by platform</h2><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th>${PLATFORM_COLUMNS.map(c => `<th data-psort="${c[1]}"${c[1] === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${esc(c[0])}</th>`).join("")}</tr></thead><tbody>
      ${rows.map(a => `<tr><td class="l">${a.pos}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td>${PLATFORM_COLUMNS.map(([, k, f]) => { const v = val(a, k); return `<td>${f === "money" ? usd(v) : count(v)}</td>`; }).join("")}</tr>`).join("")}
    </tbody></table></div><p class="note">Royalties per year at today's pace, mid estimate, paid to the rights holders. Click a column to sort.</p></section>`;
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
  if (!base) { app.innerHTML = `<p>Artist not found. <a href="#/">Back to the top 100</a></p>`; return; }
  if (!store.rev[id]) store.rev[id] = await detailOf(id);
  const a = { ...base, ...store.rev[id].artist, photo: base.photo && { ...base.photo, ...(store.rev[id].artist.photo || {}) } };
  crumbs([["Artists", "#/"], [a.name]]);
  setMeta(`${a.name}: listeners, earnings and label`, `${a.name}: ${count(a.ml)} monthly listeners${a.cl_rank ? `, #${a.cl_rank} by current listeners` : ""}${a.label_name ? `, ${a.label_name}` : ""}. What the music earns and who owns it, sourced.`);
  const m = a.money, yr = r => ({ low: r.low * 12, mid: r.mid * 12, high: r.high * 12 });
  const PROFILE = { spotify: "Spotify", youtube: "YouTube", instagram: "Instagram", tiktok: "TikTok", x: "X", wikidata: "Wikidata" };
  const profiles = Object.keys(PROFILE).filter(k => a.links[k]).map(k => `<a href="${esc(a.links[k])}" rel="noopener" target="_blank">${PROFILE[k]}</a>`).join(" · ");
  const links = "";
  const leadShare = a.streams ? a.lead_streams / a.streams : null;
  app.innerHTML = `<section class="head">${pic(a, true)}<div><h1>${esc(a.name)} ${star(a.id)}</h1>
      <p class="sub">${a.cl_rank ? `#${a.cl_rank} in our ranking · ` : ""}#${a.rank} in hip-hop by listeners · #${a.rank_all} on Spotify overall${a.country ? " · " + esc(a.country) : ""}${a.since ? " · active since " + esc(a.since) : ""}</p>
      ${labelOf(a) ? `<div class="parentchip">${logo(labelOf(a).name, "logo")}<span>${labelLink(a)}${labelOf(a).parent && labelOf(a).parent !== labelOf(a).name ? ` · ${esc(labelOf(a).parent)}` : ""}</span></div>` : ""}
      ${profiles ? `<p class="profiles">On ${profiles}</p>` : ""}
      <div class="links" style="margin-top:10px">${links}<a href="#/compare/${a.id}">Compare with…</a><a href="#/worth/${a.id}">Worth on other deals</a>${shareBtn(`${a.name}: ${count(a.ml)} monthly listeners${a.cl_rank ? `, #${a.cl_rank} in hip-hop by current listeners` : ""} (tventy music)`, a.slug ? `${SITE_URL}a/${a.slug}/` : "")}${a.slug ? `<a href="cards/${esc(a.slug)}.png" download="${esc(a.slug)}-tventy-music.png">Download card</a>` : ""}</div></div></section>
    <section class="tiles">
      <div class="tile"><div class="k">Monthly listeners</div><div class="v">${count(a.ml)}</div><div class="s">${delta(a.chg)} today (${pct(a.chg_pct)})</div></div>
      <div class="tile"><div class="k">Current listeners</div><div class="v">${a.cl != null ? count(a.cl) + (a.cl_provisional ? `<span class="prov">*</span>` : "") : "–"}</div><div class="s">${a.cur_share != null ? Math.round(a.cur_share * 100) + "% of listening on recent releases" : "release dates missing"}${a.cl == null && a.cur_share != null ? " · not ranked yet" : ""}${a.cl_provisional ? ` · provisional: ${count(a.cl_range[0])}–${count(a.cl_range[1])} until more songs are dated` : ""}</div></div>
      <div class="tile"><div class="k">Peak</div><div class="v">${count(a.peak_ml)}</div><div class="s">best rank #${a.peak_rank} on Spotify</div></div>
      <div class="tile"><div class="k">Streams, all time</div><div class="v">${count(a.streams)}</div><div class="s">${count(a.daily)} a day</div></div>
      <div class="tile"><div class="k">YouTube views</div><div class="v">${count(a.yt_total)}</div><div class="s">${a.yt_daily ? count(a.yt_daily) + " a day" : "no data"}${a.yt_subs ? " · " + count(a.yt_subs) + " subscribers" : ""}</div></div>
      <div class="tile"><div class="k">Deezer fans</div><div class="v">${count(a.deezer_fans)}</div><div class="s">Deezer</div></div>
    </section>
    ${summaryCard(a, store.rev[id])}
    <section class="panel" id="revenue"><h2>Revenue streams, per year at today's pace</h2><p class="note">Loading…</p></section>
    <section>
      <div class="panel"><h2>Streams</h2><dl class="kv">
        <dt>As lead artist</dt><dd>${count(a.lead_streams)}</dd>
        <dt>As featured guest</dt><dd>${count(a.feature_streams)}</dd>
        <dt>Share from features</dt><dd>${leadShare != null ? ((1 - leadShare) * 100).toFixed(0) + "%" : "–"}</dd>
        <dt>Tracks credited</dt><dd>${a.tracks ?? "–"}</dd>
        <dt>Top track</dt><dd>${esc(a.top_track || "–")}${a.top_track_streams ? " · " + count(a.top_track_streams) : ""}</dd>
        <dt>Label status</dt><dd>${esc(STATUS[a.label_status] || "–")}${labelOf(a) ? ` · ${labelLink(a)}` : ""}${a.label_owner && a.label_owner !== "the artist's own name" ? " · " + esc(a.label_owner) : ""}${a.label_basis ? `<br><span class="note">latest: ${esc(a.label_basis.label)} (${esc(a.label_basis.date)})</span>` : ""}</dd>
        <dt>Labels on record</dt><dd>${esc(a.labels.slice(0, 3).join(", ") || "–")}${a.labels.length > 3 ? ` +${a.labels.length - 3}` : ""}</dd>
      </dl><p class="note">Stream totals as of ${esc(a.streams_date || "–")} (kworb.net, from Spotify's public play counts).</p></div>
    </section>
    ${a.shazam ? `<section class="panel"><h2>Discovery</h2><p>${shazamBadge(a)}</p><p class="note">People looking the song up on Shazam: often an early sign, before streams follow. From Shazam's public charts (world, 15 countries and 31 cities, the last 7 days).</p></section>` : ""}
    ${certsPanel(a)}
    ${awardsPanel(a)}
    ${creditsPanel(a)}
    ${a.revivals?.length ? `<section class="panel"><h2>Revival</h2><p>${a.revivals.map(r => `<b>${esc(r.title)}</b> (${r.year}) is up ${Math.round(r.rise * 100)}% in daily streams on a month ago.`).join(" ")} Older songs that come back stay out of current listeners.</p></section>` : ""}
    ${collabPanel(a)}
    ${audiencePanel(a)}
    <section class="panel" id="deals" hidden></section>
    <section class="note">Genre: ${esc(a.genre_basis)}.${a.photo ? ` Photo: ${esc(a.photo.author)}, <a href="${esc(a.photo.page)}" target="_blank" rel="noopener">${esc(a.photo.license)}</a>, via Wikimedia Commons.` : ""}</section>`;
  bindStars(() => artist(id));
  revenuePanel(a);
}

// ---------- revenue streams (artist page): detail from data/a/<id>.json
async function revenuePanel(a) {
  const box = document.getElementById("revenue");
  const rev = store.rev[a.id] || (store.rev[a.id] = await detailOf(a.id));
  if (!rev.lines.length && box) { box.innerHTML = `<h2>Revenue streams</h2><p class="note">No estimate for this artist yet.</p>`; return; }
  if (!box || !document.body.contains(box)) return;
  const m = a.money, groups = ["Streaming", "Publishing", "Live"];
  const rowsFor = g => rev.lines.filter(l => l.group === g).map(l => `<tr title="${esc(l.basis)}"><td class="l">${esc(l.label)}</td><td>${range(l.generated)}</td><td>${l.artist ? range(l.artist) : "–"}</td><td>${grade(l.grade)}</td></tr>`).join("");
  const hasLive = rev.lines.some(l => l.group === "Live");
  box.innerHTML = `<h2>Revenue streams, per year at today's pace</h2>
    <div class="tablebox"><table><thead><tr><th class="l">Source</th><th>Generated</th><th>Artist's slice</th><th>Grade</th></tr></thead><tbody>
    ${groups.map(g => rev.lines.some(l => l.group === g) ? `<tr class="sec"><td class="l" colspan="4">${g}</td></tr>${rowsFor(g)}` : "").join("")}
    ${hasLive ? "" : `<tr class="sec"><td class="l" colspan="4">Live</td></tr><tr><td class="l">Touring and merch</td><td class="l note" colspan="3">No reported tour gross in the last 12 months</td></tr>`}
    <tr class="tot"><td class="l">Artist's slice, total</td><td></td><td>${range(rev.artist_total)}</td><td></td></tr></tbody></table></div>
    <p class="note"><b>Generated</b>: what the activity brings in before anyone's cut (royalties paid to the label or distributor, box office, merch sales). <b>Artist's slice</b>: before their manager, lawyer and tax. Recordings assume ${m ? `<b>${esc(m.deal_label)}</b>` : "an unknown deal"}${a.label_basis ? ` (from the label on recent releases: ${esc(a.label_basis.label)})` : a.major ? ` (${esc(a.major)}, from Wikidata's record-label list)` : ""}, before advances are recouped. Spotify and YouTube are measured; the other services are estimated from Spotify. Hover a row for its basis.</p>`;
  const tours = rev.lines.find(l => l.key === "touring")?.tours || [], other = rev.tours_context || [];
  const dbox = document.getElementById("deals");
  const tourItem = t => `<li><b>${esc(t.tour)}</b>, ${esc(t.start)}${t.end ? " to " + esc(t.end) : ""}: ${usd(t.gross)} gross${t.tickets ? `, ${count(t.tickets)} tickets (${usd(t.gross / t.tickets)} a fan)` : ""}${t.share && t.share < 1 ? `, ${Math.round(t.share * 100)}% counted in the last 12 months` : ""}${t.note ? ` (${esc(t.note)})` : ""} ${grade(t.grade || "C")} ${t.source ? `<a href="${esc(t.source)}" target="_blank" rel="noopener">source</a>` : ""}</li>`;
  if (dbox && (tours.length || other.length || rev.deals.length)) {
    dbox.hidden = false;
    dbox.innerHTML = `${tours.length ? `<h2>Tours counted (last 12 months)</h2><ul class="note">${tours.map(tourItem).join("")}</ul>` : ""}
      ${other.length ? `<h2>Earlier or uncounted tours</h2><ul class="note">${other.map(tourItem).join("")}</ul>` : ""}
      ${rev.deals.length ? `<h2>Reported deals and other income</h2><ul class="note">${rev.deals.map(d => `<li><b>${esc(({ record_deal: "Record deal", brand_deal: "Brand deal", forbes_earnings: "Forbes estimate", merch: "Merch", catalog_sale: "Catalog sale", super_bowl: "Super Bowl", business_revenue: "Business", publishing_deal: "Publishing deal", show_fee: "Show fee", feature_fee: "Feature fee" })[d.category] || d.category)}:</b> ${esc(d.item)}${d.year ? ` (${esc(d.year)})` : ""}${d.amount_usd ? `: ${usd(+d.amount_usd)}` : ""}${d.amount_note ? `, ${esc(d.amount_note)}` : ""} ${grade(d.grade || "C")} ${d.source_url ? `<a href="${esc(d.source_url)}" target="_blank" rel="noopener">source</a>` : ""}</li>`).join("")}</ul>` : ""}`;
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
    app.querySelector("#out").innerHTML = `<p>Royalties generated: <b>${usd(gross)}</b>, paid to whoever releases the music.</p><div class="bars">${DEALS.map(d => bar(d.name, { low: gross * d.low, mid: gross * d.mid, high: gross * d.high }, gross, ` ${grade(d.grade)}`)).join("")}</div>
      <ul class="note">${DEALS.map(d => `<li><b>${esc(d.name)}:</b> ${esc(d.note)} <a href="${esc(d.src)}" target="_blank" rel="noopener">source</a></li>`).join("")}</ul>`;
  };
  app.querySelectorAll("input").forEach(i => i.oninput = draw); draw();
}

function method() {
  nav("method");
  app.innerHTML = `<section class="prose"><h1>Method and sources</h1>
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
   <li><b>Royalties generated:</b> lead-artist streams × $2.50–4.40 per 1,000 (Duetti 2024 data; mid $3.00). Paid to the label or distributor. Estimate (C).</li>
   <li><b>Artist's share:</b> royalties generated × the share for the deal type (UK CMA, court filings, published distributor terms). The deal type is assumed from Wikidata's record-label list, which covers the whole career. Before recoupment. Estimate (C).</li>
   <li>Spotify's own figures for scale: it paid out more than $11bn in 2025; about 1,500 artists generated at least $1m and 80 at least $10m (recordings and publishing, before any split). <a href="https://newsroom.spotify.com/?p=39435" target="_blank" rel="noopener">Loud &amp; Clear</a> ${grade("A")}</li></ul>
  <h2>Scout score</h2><p>${cap(nSignals())} signals, each turned into a percentile among artists of a similar size (monthly listeners under 1.5m, 1.5–3m, 3–6m, 6–15m, 15m+), then averaged with these weights: ${Object.values(store.data.scout_factors).map(x => `${esc(x.label)} ${Math.round(x.weight * 100)}%`).join("; ")}. Tiers: Breaking 80+ (with a measured absolute signal), Rising 65+, Watch 50+; artists with 15m+ listeners get no tier. It is a pointer, not a prediction; the hit rate will be published once 90 days of history exist.</p>
  <h2>Worth</h2><p>Yearly royalties at today's pace (above) and what each income stream would sell for: a year's income × a multiple that depends on how new the music is. Buyers pay fewer years for new music because its streams fall faster. ${store.data.multiples.map(m => `${esc(m.vintage)} ${m.multiple_low}–${m.multiple_high}× (<a href="${esc(m.source_url)}" target="_blank" rel="noopener">source</a>)`).join("; ")}. Estimate (C), shown as a range.</p>
  <h2>Labels</h2><p>The label printed on each artist's releases of the last two years (Deezer), mapped to its owner (Universal, Sony, Warner, or independent), and checked against the registrant codes of the recordings (ISRCs). Artists that cannot be placed are listed as not yet known and go to the owner's review list.</p>
  <h2>Other sources</h2><ul>
   <li><b>Wikipedia attention:</b> monthly page views of the artist's English Wikipedia article, people only, from the Wikimedia API; the article is the one linked on the artist's Wikidata item.</li>
   <li><b>Apple Music charts:</b> the daily top 100 most-played songs in ${store.data.apple_countries} countries (Apple's public feed). Artists are matched by exact name; names shared by two artists are skipped.</li></ul>
  <h2>Not yet included</h2><p>Instagram, TikTok and X audiences and per-artist age and gender (licensed data only); listener history before 2026-10-23 (a backfill from the Internet Archive is planned).</p>
  <h2>Photos</h2><p>Wikimedia Commons, with the author and licence on each artist page. Initials where there is no free photo.</p></section>`;
}

// ---------- shared pieces for Scout, Worth, Labels and the artist summary
const STREAM_KEYS = ["spotify", "youtube", "apple_music", "amazon", "deezer", "tidal", "soundcloud", "audiomack", "tiktok", "meta", "others"];
const streamingMid = a => STREAM_KEYS.reduce((s, k) => s + (a.rev_lines?.[k] || 0), 0);
const share = v => v == null ? "–" : Math.round(v * 100) + "%";
const trend = v => v == null ? "–" : `<span class="${v >= 1.1 ? "up" : v <= 0.9 ? "down" : ""}">${v >= 1 ? "+" : ""}${Math.round((v - 1) * 100)}%</span>`;
const tierChip = t => t ? `<span class="chip tier t-${t.toLowerCase()}">${esc(t)}</span>` : "";
const statusShort = a => labelOf(a) ? `<a href="#/label/${labelOf(a).slug}">${esc(a.label_name)}</a>` : a.label_status === "major" || a.label_status === "major_distributed" ? esc(a.label_owner || "Major")
  : a.label_status === "independent" ? `Indie · ${esc(a.label_owner || "")}` : a.label_status === "self_released" ? "Unsigned" : a.label_status === "catalog" ? `<span class="note">catalog</span>` : `<span class="note">not yet known</span>`;
function sparkline(vals, w = 160, h = 36) {
  if (!vals || vals.length < 2) return "";
  const max = Math.max(...vals) || 1, step = w / (vals.length - 1);
  const pts = vals.map((v, i) => `${(i * step).toFixed(1)},${(h - 2 - (v / max) * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`;
}
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const nSignals = () => ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][Object.keys(store.data.scout_factors || {}).length] || "several";
function factorBars(sc) {
  const F = store.data.scout_factors;
  return `<div class="bars">${Object.entries(F).map(([k, f]) => { const v = sc.factors[k];
    return `<div class="barrow" title="${esc(f.label)}"><span>${esc(f.label.split(":")[0])}</span><div class="track"><i style="left:0;width:${v ?? 0}%"></i></div><span>${v == null ? "no data" : v + " / 100"}</span></div>`; }).join("")}</div>`;
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
function scoutPage() {
  nav("scout");
  const f = ui.scout = ui.scout || { status: "all", band: "all", tier: "rising", country: "all", sort: ["score", -1] };
  const all = store.data.artists.filter(a => a.scout);
  const ok = a => (f.status === "all" || (f.status === "signed" ? ["major", "major_distributed", "independent"].includes(a.label_status) : a.label_status === f.status))
    && (f.band === "all" || a.scout.band === f.band) && (f.country === "all" || a.country === f.country)
    && (f.tier !== "watch" || watch.has(a.id)) && (f.tier === "all" || f.tier === "watch" || (f.tier === "rising" ? ["Breaking", "Rising"].includes(a.scout.tier) : a.scout.tier === f.tier));
  const val = (a, k) => ({ score: a.scout.score, ml: a.ml, fresh: a.fresh_share, cur: a.cur_share, att: a.attention?.trend,
    spl: a.daily && a.ml ? a.daily / a.ml : null, geo: (a.geo?.countries || 0) + (a.apple?.countries.length || 0), shz: a.shazam?.charts ?? null, chg: a.chg_pct })[k];
  const [sk, sd] = f.sort;
  const rows = all.filter(ok).sort((a, b) => ((val(a, sk) ?? -Infinity) - (val(b, sk) ?? -Infinity)) * sd);
  const countries = [...new Set(all.map(a => a.country).filter(Boolean))].sort();
  const n = t => all.filter(a => a.scout.tier === t).length;
  const unsignedRising = all.filter(a => a.label_status === "self_released" && ["Breaking", "Rising"].includes(a.scout.tier));
  const seg = (key, opts) => `<div class="seg" role="group">${opts.map(([v, l]) => `<button type="button" data-f="${key}" data-v="${v}" aria-pressed="${f[key] === v}">${esc(l)}</button>`).join("")}</div>`;
  const cols = [["Scout score", "score"], ["Monthly listeners", "ml"], ["New-release pull", "fresh"], ["Current share", "cur"], ["Wikipedia, 3 mo", "att"], ["Streams / listener", "spl"], ["Chart countries", "geo"], ["Shazam", "shz"], ["Today", "chg"]];
  const brief = ["score", "ml", "fresh"];  // shown by default; the other signals behind "Show all signals"
  const th = ([l, k]) => `<th data-ssort="${k}"${brief.includes(k) ? "" : ` class="sig"`}${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}><span${defn(l)}>${esc(l)}</span></th>`;
  app.innerHTML = `${subnav()}<section><h1>Scout: who is rising</h1>
    <p class="sub">Every hip-hop artist in the top 1,000, scored 0–100 on ${nSignals()} signals of momentum. Each artist is compared only with artists of a similar size, so a 1m-listener act that is taking off scores as high as a superstar. The score points at who to look at; it does not predict a hit.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Breaking</div><div class="v">${n("Breaking")}</div><div class="s">score 80+</div></div>
      <div class="tile"><div class="k">Rising</div><div class="v">${n("Rising")}</div><div class="s">score 65–79</div></div>
      <div class="tile"><div class="k">Unsigned and rising</div><div class="v">${unsignedRising.length}</div><div class="s">${unsignedRising.slice(0, 3).map(a => esc(a.name)).join(", ") || "–"}</div></div>
      <div class="tile"><div class="k">Watch</div><div class="v">${n("Watch")}</div><div class="s">score 50–64</div></div>
    </section>
    <section class="filters">
      ${seg("tier", [["rising", "Breaking + Rising"], ["Breaking", "Breaking"], ["Watch", "Watch"], ["all", "All"], ["watch", `★ My watchlist (${watch.size})`]])}
      ${seg("status", [["all", "Any label"], ["self_released", "Unsigned"], ["independent", "Indie label"], ["signed", "Signed"], ["unknown", "Not yet known"]])}
      <label class="sel">Size <select data-f="band"><option value="all">all sizes</option>${BANDS.map(b => `<option${f.band === b ? " selected" : ""}>${b}</option>`).join("")}</select></label>
      <label class="sel">Country <select data-f="country"><option value="all">all countries</option>${countries.map(c => `<option${f.country === c ? " selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
      <button type="button" class="btn" id="signals" aria-pressed="${!!f.signals}">${f.signals ? "Fewer columns" : "Show all signals"}</button>
      <button type="button" class="btn" id="csv">Download CSV</button>
      <button type="button" class="btn" id="radio" title="30-second previews of each artist's newest hit, in the order shown">📻 Scout radio (${rows.filter(a => a.top_fresh?.dz).length})</button>
    </section>
    <section><div class="tablebox"><table class="${f.signals ? "" : "brief"}"><thead><tr><th class="l">#</th><th class="l">Artist</th>${cols.slice(0, 1).map(th).join("")}<th class="l">Label</th><th class="l">Newest hit</th>${cols.slice(1).map(th).join("")}</tr></thead><tbody>
      ${rows.slice(0, f.all ? rows.length : 50).map((a, i) => `<tr><td class="l">${star(a.id)} ${i + 1}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td><b>${a.scout.score}</b> ${tierChip(a.scout.tier)}</td><td class="l wrap lab">${statusShort(a)}</td>
        <td class="l wrap hit">${a.top_fresh ? `${a.scout.tier ? playBtn(a) + videoBtn(a) : ""}${esc(a.top_fresh.title)} <span class="note">${count(a.top_fresh.daily)}/day, out ${esc(a.top_fresh.released)}</span>` : `<span class="note">none in 90 days</span>`}</td>
        <td>${count(a.ml)}</td><td>${share(a.fresh_share)}</td><td class="sig">${share(a.cur_share)}</td><td class="sig">${trend(a.attention?.trend)}</td>
        <td class="sig">${val(a, "spl") ? val(a, "spl").toFixed(2) : "–"}</td><td class="sig" title="Spotify weekly top 200 + Apple Music daily top 100">${val(a, "geo") || "–"}</td><td class="sig">${shazamBadge(a, true)}</td><td class="sig">${pct(a.chg_pct)}</td></tr>`).join("") || `<tr><td class="l" colspan="12">No artist matches these filters.</td></tr>`}
    </tbody></table></div>
    ${!f.all && rows.length > 50 ? `<p class="more"><button type="button" class="btn" id="showall">Show all ${rows.length}</button></p>` : ""}
    <p class="note">${rows.length} artists. Click a column to sort. ☆ adds an artist to your watchlist (kept in this browser). Percentiles are within the artist's size band (monthly listeners ${BANDS.join(", ")}).</p></section>
    <section class="panel"><h2>How the score works</h2>
      <ul>${Object.values(store.data.scout_factors).map(x => `<li><b>${Math.round(x.weight * 100)}%</b> ${esc(x.label)}</li>`).join("")}</ul>
      <p class="note">Each signal becomes a percentile (0–100) among artists in the same size band; the score is their weighted average over the signals the artist has (at least three). Tiers: Breaking 80+ (and either new songs pulling 25%+ of streams or Wikipedia attention up 30%+), Rising 65+, Watch 50+; artists with 15m+ monthly listeners are established and get no tier. Wikipedia views count only artists with an English article. Listener growth uses the Internet Archive's weekly copies of kworb's listener page, so it exists only for artists that page lists. ${grade("C")}</p></section>
    ${backtestPanel()}`;
  app.querySelectorAll("button[data-f]").forEach(b => b.onclick = () => { f[b.dataset.f] = b.dataset.v; scoutPage(); });
  app.querySelector("#signals").onclick = () => { f.signals = !f.signals; scoutPage(); };
  bindStars(scoutPage);
  app.querySelectorAll("select[data-f]").forEach(s => s.onchange = () => { f[s.dataset.f] = s.value; scoutPage(); });
  app.querySelectorAll("th[data-ssort]").forEach(th => th.onclick = () => { f.sort = [th.dataset.ssort, sk === th.dataset.ssort ? -sd : -1]; scoutPage(); });
  app.querySelector("#showall")?.addEventListener("click", () => { f.all = true; scoutPage(); });
  app.querySelector("#radio").onclick = () => startRadio(rows.filter(a => a.top_fresh?.dz));
  app.querySelector("#csv").onclick = () => download("tventy-music-scout.csv", [["name", "spotify_url", "scout_score", "tier", "label_status", "label_group", "country", "monthly_listeners", "current_listeners", "new_release_share", "current_share", "wikipedia_trend", "streams_per_listener", "countries_charting", "newest_hit"],
    ...rows.map(a => [a.name, `https://open.spotify.com/artist/${a.id}`, a.scout.score, a.scout.tier || "", a.label_status, a.label_owner || "", a.country || "", a.ml, a.cl ?? "", a.fresh_share ?? "", a.cur_share ?? "", a.attention?.trend ?? "", val(a, "spl")?.toFixed(3) ?? "", val(a, "geo"), a.top_fresh?.title || ""])]);
}

// ---------- this month: movers, new on Scout's list, unsigned prospects, label shares (src/monthly.py)
function monthPage() {
  nav("movers");
  const M = store.data.month, byId = Object.fromEntries(store.data.artists.map(a => [a.id, a]));
  const who = id => { const a = byId[id]; return a ? `<a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a>` : ""; };
  const moverTable = (list, title) => `<div><h3>${title}</h3><div class="tablebox"><table><thead><tr><th class="l">Artist</th><th>Then</th><th>Now</th><th>Change</th></tr></thead><tbody>
    ${list.map(m => `<tr><td class="l">${who(m.id)}</td><td>${count(m.then)}</td><td>${count(m.now)}</td><td>${pct(m.pct)}</td></tr>`).join("")}</tbody></table></div></div>`;
  const ready = new Date(Date.parse(M.log_from) + M.min_log * 864e5).toISOString().slice(0, 10);
  const label = s => ({ major: "Major label", major_distributed: "Distributed by a major", independent: "Independent label", self_released: "Self-released", catalog: "Catalog (no release in 2 years)", unknown: "Not yet known" })[s] || s;
  app.innerHTML = `${subnav()}<section><h1>Movers: the last 30 days</h1>${moversSwitch("month")}
    <p class="sub">What changed in hip-hop's top 1,000 over the last 30 days: who gained and lost listeners, who joined Scout's list, the unsigned acts worth a look, and how listening splits between majors, indies and the self-released.</p></section>
    <section class="panel"><h2>Movers</h2>
      ${M.movers_n ? `<div class="grid2">${moverTable(M.up, "Biggest gains, %")}${moverTable(M.down, "Biggest falls, %")}</div>
      <p class="note">Monthly listeners on ${esc(M.today)} against the snapshot nearest 30 days earlier (from ${esc(M.movers_from)}). ${M.movers_n} of the 1,000 have one yet: our own daily snapshots began on ${esc(M.log_from)}, so for now the month-ago values come from the Internet Archive's copies of kworb's listener page, which lists the biggest artists only. From ${esc(ready)} every artist has one.</p>` : `<p class="note">No month-ago values yet.</p>`}</section>
    <section class="panel"><h2>New on Scout's list</h2>
      ${M.log_start ? `<p>Breaking now, not on ${esc(M.log_start)}: ${M.new_breaking.map(id => who(id)).join(" ") || "none"}</p><p>Rising now, not on ${esc(M.log_start)}: ${M.new_rising.map(id => who(id)).join(" ") || "none"}</p>`
        : `<p class="note">From ${esc(ready)}. Scout's daily log began on ${esc(M.log_from)}, and the score's method changed in its first days, so a shorter comparison would show our changes rather than the artists'. Today's Breaking and Rising artists are on the <a href="#/scout">Scout list</a>.</p>`}</section>
    <section class="panel"><h2>Unsigned and worth a look</h2>
      <div class="chips">${M.prospects.map(id => byId[id] ? `<span class="chipplay">${playBtn(byId[id])}${videoBtn(byId[id])}<a class="chip" href="#/a/${id}">${esc(byId[id].name)} · ${byId[id].scout?.score ?? "–"} ${byId[id].scout?.tier ? esc(byId[id].scout.tier) : ""}</a></span>` : "").join(" ")}</div>
      <p class="note">Self-released artists (their own label through a DIY distributor) with a Breaking or Rising Scout tier, best score first. <a href="#/unsigned">Unsigned against signed peers</a></p></section>
    <section class="panel"><h2>Who owns the listening</h2><div class="tablebox"><table><thead><tr><th class="l">Label status</th><th>${M.log_start ? esc(M.log_start) : "30 days ago"}</th><th>Now</th></tr></thead><tbody>
      ${M.shares.map(x => `<tr><td class="l">${esc(label(x.status))}</td><td>${x.then == null ? "–" : share(x.then)}</td><td>${share(x.now)}</td></tr>`).join("")}</tbody></table></div>
      <p class="note">Share of the top 1,000's monthly listeners (added per artist). Both columns use each artist's label status today, so a share moves only with listening, not with our relabelling. The comparison starts on ${esc(ready)}. ${grade("B")}</p></section>`;
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
  return `<section class="panel"><h2>Who makes the hits ${grade("B")}</h2><div class="tablebox"><table><thead><tr><th class="l">Song</th><th>Streams / day</th><th class="l">Produced by</th><th class="l">Written by</th></tr></thead><tbody>
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
    <p class="sub">Who is behind hip-hop's biggest songs right now: each person ranked by the daily Spotify streams of the songs they are credited on, among the three biggest songs of every artist in the top 1,000.</p></section>
    <section class="tiles"><div class="tile"><div class="k">Songs covered</div><div class="v">${C.songs || 0}</div><div class="s">3 biggest per artist</div></div>
      <div class="tile"><div class="k">Found on MusicBrainz</div><div class="v">${C.looked_up || 0}</div><div class="s">by recording code (ISRC)</div></div>
      <div class="tile"><div class="k">With a producer credit</div><div class="v">${C.with_producer || 0}</div><div class="s">credits are entered by volunteers</div></div></section>
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
  const cite = `tventy music, "State of hip-hop, ${month}", ${SITE_URL}${GENRE === "hip_hop" ? "" : GENRE + "/"}state/${st.month}/ (data as of ${st.as_of}).`;
  app.innerHTML = `<section><h1>State of hip-hop, ${esc(month)}</h1>
    <p class="sub">The month in hip-hop's top 1,000, in numbers you can quote. ${st.month === all[0]?.month ? `This month's page updates daily until the month ends; then its numbers are fixed. ` : ""}Data as of ${esc(st.as_of)}.</p>
    ${all.length > 1 ? `<div class="chips">${all.map(x => `<a class="chip" href="#/state/${x.month}"${x.month === st.month ? ' aria-current="page"' : ""}>${esc(x.month)}</a>`).join(" ")}</div>` : ""}</section>
    <section class="statgrid">${st.items.map(i => `<a class="stat" href="${esc(i.link)}"><span class="k">${esc(i.label)}</span><b>${esc(i.value)}</b><span class="note">${esc(i.detail)}</span></a>`).join("")}</section>
    <section class="panel"><h2>Quoting these numbers</h2><p>Please cite: <code>${esc(cite)}</code> <button type="button" class="linkbtn" data-share="${esc(cite)}" data-url="${esc(SITE_URL + "state/" + st.month + "/")}">Share</button></p>
    <p class="note">Every figure links to the page it comes from, with its sources and grades. Listener counts are Spotify's public numbers via kworb; money is our estimate, shown as a range on each page; labels come from the ℗ lines of recent releases. <a href="#/method">Method</a></p></section>`;
}

// ---------- Shazam (owner, 2026-10-24, K3): an internal Scout signal, shown only as a badge with a link to Shazam's chart
const shazamBadge = (a, short = false) => { const z = a.shazam; if (!z) return short ? "–" : "";
  const best = `#${z.best.rank} ${z.best.kind === "genre" ? "hip-hop" : ""} in ${z.best.place.replace(/-/g, " ")}`.replace(/\s+/g, " ");
  return `<a class="chip" href="${esc(z.url)}" target="_blank" rel="noopener" title="On ${z.charts} Shazam chart${z.charts > 1 ? "s" : ""} (7 days)${z.cities ? `, ${z.cities} cities` : ""}; best ${esc(best)}">${short ? z.charts : `Shazam: ${z.charts} chart${z.charts > 1 ? "s" : ""}, best ${esc(best)}`}</a>`; };

// ---------- certifications and chart peaks (English Wikipedia discographies, CC BY-SA)
function certsPanel(a) {
  const C = a.cert_detail, S = a.certs;
  if (!C || !S) return "";
  return `<section class="panel"><h2>Certifications ${grade("B")}</h2>
    <section class="tiles"><div class="tile"><div class="k">Certified releases</div><div class="v">${S.works}</div><div class="s">in ${S.countries} countr${S.countries === 1 ? "y" : "ies"}</div></div>
      <div class="tile"><div class="k">RIAA Platinum, all releases</div><div class="v">${S.riaa_plat}×</div><div class="s">Diamond counts as 10× (US)</div></div>
      <div class="tile"><div class="k">US No. 1s</div><div class="v">${S.no1}</div><div class="s">Billboard 200 or Hot 100, as listed</div></div></section>
    <div class="tablebox"><table><thead><tr><th class="l">Release</th><th>Year</th><th>US peak</th><th class="l">Certifications</th></tr></thead><tbody>
    ${C.top.map(w => `<tr><td class="l">${esc(w.title)} <span class="note">${esc(w.type)}</span></td><td>${esc(w.year || "–")}</td><td>${w.us_peak ? "#" + w.us_peak : "–"}</td><td class="l wrap">${w.certs.map(esc).join(", ")}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Most-certified releases first (RIAA multiples). From the artist's discography on <a href="${esc(C.url)}" target="_blank" rel="noopener">English Wikipedia</a> (CC BY-SA), which cites the certifying bodies (RIAA, BPI, ARIA, Music Canada and others). Wikipedia can lag the bodies' own databases by weeks.</p></section>`;
}

// ---------- awards and nominations (Wikidata, CC0)
function awardsPanel(a) {
  const L = a.award_list;
  if (!L || !(L.wins.length + L.nominations.length)) return "";
  const fams = {};
  for (const e of L.wins) (fams[e.family] = fams[e.family] || { w: 0, n: 0 }).w++;
  for (const e of L.nominations) (fams[e.family] = fams[e.family] || { w: 0, n: 0 }).n++;
  const line = e => `<li>${esc(e.award)}${e.work ? `, for <i>${esc(e.work)}</i>` : ""}${e.year ? ` (${esc(e.year)})` : ""}</li>`;
  return `<section class="panel"><h2>Awards ${grade("B")}</h2>
    <div class="chips">${Object.entries(fams).sort((x, y) => y[1].w - x[1].w || y[1].n - x[1].n).map(([f, v]) => `<span class="chip">${esc(f)}: ${[v.w ? `${v.w} won` : "", v.n ? `${v.n} nomination${v.n > 1 ? "s" : ""}` : ""].filter(Boolean).join(", ")}</span>`).join(" ")}</div>
    ${L.wins.length ? `<details${L.wins.length <= 6 ? " open" : ""}><summary>${L.wins.length} won</summary><ul>${L.wins.map(line).join("")}</ul></details>` : ""}
    ${L.nominations.length ? `<details><summary>${L.nominations.length} more nominations</summary><ul>${L.nominations.map(line).join("")}</ul></details>` : ""}
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
    <p>So far, the signals with an archived history do <b>not</b> pick next quarter's risers: fast listener growth tends to cool off again over the next 90 days. Only listener growth and Wikipedia attention (${Math.round(((store.data.scout_factors.growth?.weight || 0) + (store.data.scout_factors.attention?.weight || 0)) * 100)}% of the weight now; both were cut to 5% after this test) have history before our own daily log; the other signals (new-release pull, current share, engagement, chart reach) are back-tested from that log once it is 90 days old, from January 2027.</p>
    <div class="tablebox"><table><thead><tr><th class="l">Year</th><th>Test dates</th><th>Hit rate</th><th>Picks' growth, next 90 days</th><th>Everyone else's</th></tr></thead><tbody>
    ${Object.entries(years).map(([y, v]) => `<tr><td class="l">${y}</td><td>${v.n}</td><td>${Math.round(v.hr / v.n * 100)}%</td><td>${pct(avg(v.pg) * 100)}</td><td>${pct(avg(v.rg) * 100)}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Each date: hip-hop artists under 15m monthly listeners in the archived page then, 90 days before and 90 days after. Growth is the median within each group, averaged over the year's dates. The artists are today's registry, so acts that rose and fell away are missing. ${grade("B")}</p></section>`;
}

// ---------- worth: what the music earns and what it would sell for, for artists
async function worthPage() {
  nav("worth");
  const d = store.data, deals = Object.fromEntries(d.deals.map(x => [x.deal_type, x]));
  const w = ui.worth = ui.worth || { ml: 1000000, deal: "diy", vintage: "auto", pick: "" };
  const picked = w.pick && d.artists.find(a => a.id === w.pick);
  const lines = picked ? (store.rev[picked.id] = store.rev[picked.id] || await detailOf(picked.id)).lines.filter(l => l.group === "Streaming") : null;
  const sumL = k => lines.reduce((s, l) => s + l.generated[k], 0);
  const ml = picked ? picked.ml : w.ml;
  const ladder = [[1.5e6, 0], [3e6, 1], [6e6, 2], [15e6, 3], [Infinity, 4]];
  const bandIx = ml => ladder.findIndex(([m]) => ml < m);
  const peersBand = d.artists.filter(a => bandIx(a.ml) === bandIx(ml) && streamingMid(a));
  const perL = peersBand.map(a => streamingMid(a) / a.ml);  // streaming royalties a year per monthly listener
  const q = { low: quantile(perL, 0.25), mid: median(perL), high: quantile(perL, 0.75) };
  const gen = picked && lines.length ? { low: sumL("low"), mid: sumL("mid"), high: sumL("high") } : { low: ml * q.low, mid: ml * q.mid, high: ml * q.high };
  const vint = w.vintage !== "auto" ? w.vintage : picked ? (picked.cur_share == null ? "mixed" : picked.cur_share >= 0.6 ? "new" : picked.cur_share >= 0.3 ? "mixed" : "evergreen") : "mixed";
  const M = d.multiples.find(m => m.vintage === vint), mlo = +M.multiple_low, mhi = +M.multiple_high;
  const dl = deals[w.deal];
  const keep = { low: gen.low * dl.low, mid: gen.mid * dl.mid, high: gen.high * dl.high };
  const pub = { low: gen.low * 0.20, mid: gen.mid * 0.25, high: gen.high * 0.25 };
  const val = r => ({ low: r.low * mlo, mid: r.mid * (mlo + mhi) / 2, high: r.high * mhi });
  const near = [...d.artists].filter(a => streamingMid(a) && a.id !== w.pick).sort((a, b) => Math.abs(Math.log(a.ml / ml)) - Math.abs(Math.log(b.ml / ml))).slice(0, 6);
  const dealOpts = ["diy", "services", "independent", "major"].map(k => `<option value="${k}"${w.deal === k ? " selected" : ""}>${esc(deals[k].label)} (keeps ${Math.round(deals[k].low * 100)}–${Math.round(deals[k].high * 100)}%)</option>`).join("");
  const box = (k, v, s) => `<div class="tile"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
  app.innerHTML = `${subnav()}<section><h1>What is your music worth?</h1>
    <p class="sub">Enter your monthly listeners, or pick an artist, to see what the music earns in a year at today's pace, what the artist keeps under each kind of deal, and what the income would sell for as a catalog. Ranges, not quotes: grade ${grade("C")}.</p></section>
    <section class="panel"><div class="calc">
      <label>Monthly listeners on Spotify<input id="w-ml" type="number" min="1000" step="50000" value="${ml}"${picked ? " disabled" : ""}></label>
      <label>Or an artist in our list<input id="w-pick" list="w-names" placeholder="Type a name" value="${picked ? esc(picked.name) : ""}"><datalist id="w-names">${d.artists.map(a => `<option value="${esc(a.name)}">`).join("")}</datalist></label>
      <label>Deal<select id="w-deal">${dealOpts}</select></label>
      <label>How new is the music<select id="w-vint">${[["auto", "from the artist (or mixed)"], ["new", "mostly new: 60%+ of listening on recent releases"], ["mixed", "mixed"], ["evergreen", "mostly older songs"]].map(([v, l]) => `<option value="${v}"${w.vintage === v ? " selected" : ""}>${l}</option>`).join("")}</select></label>
      ${picked ? `<button type="button" class="btn" id="w-clear">Clear artist</button>` : ""}
    </div></section>
    <section class="tiles">
      ${box("Recording royalties / year", range(gen), picked ? `${esc(picked.name)}'s measured streams, all platforms` : `artists with similar listeners earn ${usd(q.low)}–${usd(q.high)} per listener`)}
      ${box("Artist keeps / year", range(keep), `${esc(dl.label)}, before manager and tax`)}
      ${box("Songwriting (publishing) / year", range(pub), "about a quarter of the recording royalties, shared by the writers")}
      ${box("Recordings would sell for", range(val(gen)), `${mlo}–${mhi}× a year's royalties (${esc(vint)} music)`)}
      ${box("Artist's royalties would sell for", range(val(keep)), "if the artist sold their share of future royalties")}
    </section>
    <section class="panel"><h2>Artists with a similar audience</h2>
      <div class="tablebox"><table><thead><tr><th class="l">Artist</th><th class="l">Label</th><th>Monthly listeners</th><th>Current share</th><th>Royalties / yr</th><th>Per listener</th><th>Recordings value, mid</th></tr></thead><tbody>
      ${near.map(a => `<tr><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td class="l">${statusShort(a)}</td><td>${count(a.ml)}</td><td>${share(a.cur_share)}</td><td>${usd(streamingMid(a))}</td><td>${usd(streamingMid(a) / a.ml)}</td><td>${usd(a.worth_mid)}</td></tr>`).join("")}
      </tbody></table></div>
      <p class="note">Royalties per listener differ with how often fans replay the music and how much of it is on YouTube: the closest peers are the best guide to your own range.</p></section>
    <section class="panel"><h2>How this is worked out</h2><ul>
      <li><b>Royalties</b>: for a typed-in audience, the middle half of what hip-hop artists of that size in our list generate per monthly listener a year (${peersBand.length} artists: ${usd(q.low)}–${usd(q.high)}, median ${usd(q.mid)}), across Spotify, YouTube and the other services. For an artist in our list, their own measured Spotify streams and YouTube views, with the other services estimated from them.</li>
      <li><b>What the artist keeps</b>: ${d.deals.filter(x => x.source).map(x => `${esc(x.label)} ${Math.round(x.low * 100)}–${Math.round(x.high * 100)}% <a href="${esc(x.source)}" target="_blank" rel="noopener">source</a>`).join("; ")}.</li>
      <li><b>Sale value</b>: buyers pay a number of years of income, fewer for new music because its streams fall faster. ${d.multiples.map(m => `${esc(m.vintage)}: ${m.multiple_low}–${m.multiple_high}× (${esc(m.source_note)}) ${grade(m.grade)} <a href="${esc(m.source_url)}" target="_blank" rel="noopener">source</a>`).join("; ")}.</li>
      <li>Not included: touring and merch (see the artist pages), brand deals, advances, and recoupment (an advance is paid back from the artist's share before any royalties reach them).</li></ul></section>
    <section><h2>Top 100 by the sale value of their recordings</h2>${worthTable()}</section>`;
  const set = (k, v) => { w[k] = v; worthPage(); };
  const mlIn = app.querySelector("#w-ml"); mlIn.onchange = () => set("ml", Math.max(1000, +mlIn.value || 0));
  app.querySelector("#w-deal").onchange = e => set("deal", e.target.value);
  app.querySelector("#w-vint").onchange = e => set("vintage", e.target.value);
  app.querySelector("#w-pick").onchange = e => { const a = d.artists.find(x => x.name.toLowerCase() === e.target.value.trim().toLowerCase()); if (a) { w.deal = a.deal_type in deals ? a.deal_type : w.deal; set("pick", a.id); } };
  const c = app.querySelector("#w-clear"); if (c) c.onclick = () => set("pick", "");
}
function worthTable() {
  const rows = [...store.data.artists].filter(a => a.worth_mid).sort((a, b) => b.worth_mid - a.worth_mid).slice(0, 100);
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Label</th><th>Royalties / yr</th><th>Artist keeps / yr</th><th>Recordings + songs, value (mid)</th><th>Current share</th></tr></thead><tbody>
    ${rows.map((a, i) => `<tr><td class="l">${i + 1}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td class="l">${statusShort(a)}</td><td>${usd(streamingMid(a))}</td><td>${range(a.rev_total)}</td><td>${usd(a.worth_mid)}</td><td>${share(a.cur_share)}</td></tr>`).join("")}
  </tbody></table></div><p class="note">Value (mid) = a year's recording and publishing royalties × the middle of the multiple range for how new the music is. Artist keeps = all income lines on the artist page, including tours where reported.</p>`;
}

// ---------- labels: who owns the hip-hop top 1,000
const GROUP_ORDER = ["Universal Music Group", "Sony Music", "Warner Music Group", "Independent labels", "Self-released", "Not yet known"];
const SHADE = ["#fff", "#d3d6db", "#a3a8b1", "#6b7079", "#3b3f46", "repeating-linear-gradient(45deg,#3b3f46 0 3px,#000 3px 6px)"];  // light to dark on the black theme
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
  const majShare = k => majors.reduce((s, g) => s + gv(g, k), 0) / tot(k);
  const known = b => G.filter(g => g !== "Not yet known").reduce((s, g) => s + m.groups[g].bands[b], 0) || 1;
  const majBand = b => majors.reduce((s, g) => s + m.groups[g].bands[b], 0) / known(b);
  // the smallest bands together (under 3m): the top 1,000 starts near 1.5m, so the lowest band alone holds few artists
  const majLow = () => majors.reduce((s, g) => s + m.groups[g].bands[0] + m.groups[g].bands[1], 0) / (known(0) + known(1));
  const indies = Object.entries(Object.assign({}, ...G.map(g => m.groups[g].labels))).sort((a, b) => b[1].ml - a[1].ml);
  const byId = Object.fromEntries(store.data.artists.map(a => [a.id, a]));
  app.innerHTML = `${subnav()}<section><h1>Labels: who owns hip-hop's top 1,000</h1>
    <p class="sub">The label behind each artist's recent releases, grouped by the company that owns it. The three majors hold most of the audience at the top; lower down, independent labels and self-released artists take a bigger share: where small labels can still sign talent.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Majors' share of listeners</div><div class="v">${share(majShare("ml"))}</div><div class="s">of the top 1,000's monthly listeners (${share(majShare("artists"))} of artists)</div></div>
      <div class="tile"><div class="k">Majors, artists 15m+</div><div class="v">${share(majBand(4))}</div><div class="s">of those whose label is known</div></div>
      <div class="tile"><div class="k">Majors, under 3m</div><div class="v">${share(majLow())}</div><div class="s">of those whose label is known</div></div>
      <div class="tile"><div class="k">Self-released</div><div class="v">${m.groups["Self-released"]?.artists || 0}</div><div class="s">artists, ${share((m.groups["Self-released"]?.ml || 0) / tot("ml"))} of listeners</div></div>
    </section>
    <section class="panel"><h2>Share of the top 1,000</h2>
      <div class="legend">${G.map((g, i) => `<span><i style="background:${SHADE[i]}"></i>${esc(g)}</span>`).join("")}</div>
      ${[["Artists", "artists"], ["Monthly listeners", "ml"], ["Current listeners", "cl"]].map(([l, k]) => `<div class="stackrow"><span>${l}</span>${stack(G.map(g => [g, gv(g, k)]))}</div>`).join("")}
      <h2 style="margin-top:12px">By size (artists, monthly listeners)</h2>
      ${m.band_labels.map((b, i) => `<div class="stackrow"><span>${esc(b)} <span class="note">${m.band_totals[i]}</span></span>${stack(G.map(g => [g, m.groups[g].bands[i]]))}</div>`).join("")}
      <div class="tablebox"><table><thead><tr><th class="l">Group</th><th>Artists</th><th>Share of artists</th><th>Monthly listeners</th><th>Share</th><th>Current listeners</th><th>Share</th></tr></thead><tbody>
        ${G.map(g => `<tr><td class="l"><b>${esc(g)}</b></td><td>${gv(g, "artists")}</td><td>${share(gv(g, "artists") / tot("artists"))}</td><td>${count(gv(g, "ml"))}</td><td>${share(gv(g, "ml") / tot("ml"))}</td><td>${count(gv(g, "cl"))}</td><td>${share(gv(g, "cl") / tot("cl"))}</td></tr>`).join("")}
      </tbody></table></div>
      <p class="note">Among artists whose label is known, the majors hold ${share(majBand(4))} of those with 15m+ monthly listeners and ${share(majLow())} of those under 3m. ${m.catalog ? `${m.catalog} catalog acts (no release in two years) are left out. ` : ""}Monthly listeners are added up per artist, so a fan of two artists counts twice. "Not yet known": no label read from recent releases yet (owner's review list). Groups follow the label printed on the last two years of releases (Deezer), checked against recording codes; distribution deals with a major count under that major.</p></section>
    <section class="panel"><h2>Independent labels and distributors in the top 1,000</h2>
      <div class="tablebox"><table><thead><tr><th class="l">Label</th><th>Artists</th><th>Monthly listeners</th></tr></thead><tbody>
      ${indies.map(([l, v]) => `<tr><td class="l">${esc(l)}</td><td>${v.artists}</td><td>${count(v.ml)}</td></tr>`).join("")}</tbody></table></div></section>
    ${groupsCompare()}${groupsCompare(true)}
    ${labelDirectory()}
    <section><h2>Rosters: the biggest artists in each group</h2>
      ${G.map(g => `<details class="panel"><summary><b>${esc(g)}</b>: ${gv(g, "artists")} artists</summary><div class="chips">${m.groups[g].top.map(id => byId[id]).filter(Boolean).map(a => `<a class="chip" href="#/a/${a.id}">${esc(a.name)} · ${count(a.ml)}</a>`).join(" ")}</div></details>`).join("")}</section>`;
  bindDirectory();
}

function collabPanel(a) {
  const C = a.collabs || [];
  if (!C.length) return "";
  const inSite = new Set(store.data.artists.map(x => x.id));
  return `<section class="panel"><h2>Collaborations</h2>
    <div class="tablebox"><table><thead><tr><th class="l">With</th><th>Songs</th><th>Their daily streams</th><th class="l">Biggest</th></tr></thead><tbody>
    ${C.map(c => `<tr><td class="l">${inSite.has(c.id) ? `<a href="#/a/${c.id}">${esc(c.name)}</a>` : esc(c.name)}</td><td>${c.songs}</td><td>${count(c.daily)}</td><td class="l wrap">${esc(c.top)}</td></tr>`).join("")}
    </tbody></table></div><p class="note">Songs where one of the two is the lead artist and the other is named in the title (feat. / with), from Spotify's play counts. Featuring a much bigger artist is an early sign labels watch.</p></section>`;
}

// Home: four highlights computed from today's data (no written commentary).
function pulse() {
  const A = store.data.artists, by = (f, xs = A) => xs.filter(x => f(x) != null).sort((a, b) => f(b) - f(a))[0];
  const song = by(a => a.top_fresh?.daily);
  const unsigned = by(a => a.scout?.score, A.filter(a => a.label_status === "self_released"));
  const riser = by(a => a.chg_pct, A.filter(a => a.ml >= 1e6));
  const reach = by(a => (a.geo?.countries || 0) + (a.apple?.countries.length || 0), A.filter(a => a.ml < 15e6));
  const item = (k, a, line) => a ? `<a class="pulse" href="#/a/${a.id}">${pic(a)}<span><span class="k">${k}</span><b>${esc(a.name)}</b><span class="note">${line}</span></span></a>` : "";
  return `<section class="band"><div class="bandhead"><h2>Right now</h2><a class="btn" href="#/scout">Open the scout list</a></div><div class="pulses">
    ${item("Hottest new song", song, song ? `${esc(song.top_fresh.title)}: ${count(song.top_fresh.daily)} streams a day` : "")}
    ${item("Top unsigned prospect", unsigned, unsigned ? `Scout ${unsigned.scout.score}, ${count(unsigned.ml)} monthly listeners` : "")}
    ${item("Biggest riser today", riser, riser ? `${pct(riser.chg_pct)} monthly listeners, now ${count(riser.ml)}` : "")}
    ${item("Widest reach under 15m", reach, reach ? `charting in ${(reach.geo?.countries || 0) + (reach.apple?.countries.length || 0)} country charts on Spotify and Apple` : "")}
  </div></section>`;
}

// ---------- compare: two artists side by side
function compare(ids) {
  nav("compare");
  const d = store.data, byId = Object.fromEntries(d.artists.map(a => [a.id, a]));
  const A = ids.map(id => byId[id]).filter(Boolean).slice(0, 2);
  const spl = a => a.daily && a.ml ? a.daily / a.ml : null;
  const charts = a => (a.geo?.countries || 0) + (a.apple?.countries.length || 0);
  const rows = [
    ["Level", a => a.level?.name, null],
    ["Monthly listeners", a => a.ml, count], ["Current listeners", a => a.cl, count],
    ["Listening on recent releases", a => a.cur_share, share], ["New-release pull (songs ≤ 90 days)", a => a.fresh_share, share],
    ["Scout score", a => a.scout?.score, v => v], ["Streams a day", a => a.daily, count], ["Streams a day per listener", a => spl(a), v => v.toFixed(2)],
    ["YouTube views a day", a => a.yt_daily, count], ["Deezer fans", a => a.deezer_fans, count], ["Chart countries (Spotify + Apple)", charts, v => v],
    ["Wikipedia, last 3 months vs 9 before", a => a.attention?.trend, trend],
    ["Label", a => a.label_status, (v, a) => statusShort(a)],
    ["Royalties generated / year", a => streamingMid(a), usd], ["Artist keeps / year (mid)", a => a.rev_total?.mid, usd],
    ["Recordings + songs, sale value (mid)", a => a.worth_mid, usd],
  ];
  const pickBox = i => `<label>Artist ${i + 1}<input data-i="${i}" list="c-names" placeholder="Type a name" value="${A[i] ? esc(A[i].name) : ""}"></label>`;
  app.innerHTML = `${subnav()}<section><h1>Compare artists</h1><p class="sub">Two artists side by side: audience, momentum, label and money. The higher number of each pair is in bold.</p></section>
    <section class="panel"><div class="calc">${pickBox(0)}${pickBox(1)}<datalist id="c-names">${d.artists.map(a => `<option value="${esc(a.name)}">`).join("")}</datalist></div></section>
    ${A.length === 2 ? `<section><div class="tablebox"><table class="cmp"><thead><tr><th class="l"></th>${A.map(a => `<th class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></th>`).join("")}</tr></thead><tbody>
      ${rows.map(([l, f, fmt]) => { const v = A.map(f), num = v.every(x => typeof x === "number"), hi = num && v[0] !== v[1] ? (v[0] > v[1] ? 0 : 1) : -1;
        return `<tr><td class="l">${esc(l)}</td>${A.map((a, i) => `<td class="l">${v[i] == null ? "–" : `<span${i === hi ? ' class="hi"' : ""}>${fmt ? fmt(v[i], a) : esc(v[i])}</span>`}</td>`).join("")}</tr>`; }).join("")}
    </tbody></table></div><p class="note">Money lines are estimates (grade C); see each artist's page for the ranges and sources.</p></section>` : `<p class="note">Pick two artists, or start from one of these: ${(() => { const b = store.data.artists.filter(x => x.scout?.tier === "Breaking").sort((x, y) => y.scout.score - x.scout.score); const t = [...store.data.artists].sort((x, y) => y.ml - x.ml); const pairs = [[t[0], t[1]], b.length > 1 ? [b[0], b[1]] : null, t[2] && b[0] ? [t[2], b[0]] : null].filter(Boolean); return pairs.map(([x, y]) => `<a href="#/compare/${x.id}/${y.id}">${esc(x.name)} vs ${esc(y.name)}</a>`).join(" · "); })()}.</p>`}`;
  app.querySelectorAll("input[data-i]").forEach(inp => inp.onchange = () => {
    const a = d.artists.find(x => x.name.toLowerCase() === inp.value.trim().toLowerCase());
    if (!a) return;
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
  const money = (v, r) => { const n = +v; if (isNaN(n)) return esc(v); if (r.unit === "percent") return n.toFixed(1) + "%";
    const sym = ({ EUR: "€", USD: "$", JPY: "¥" })[r.currency] || ""; return `${sym}${n.toLocaleString("en", { maximumFractionDigits: 1 })}${r.unit === "millions" ? "m" : r.unit === "billions" ? "bn" : ""}`; };
  const facts = rows.filter(r => r.unit === "text");
  const by = {};
  for (const r of rows.filter(r => r.unit !== "text" && !isNaN(+r.value))) (by[r.metric] = by[r.metric] || []).push(r);
  const lines = Object.entries(by).map(([m, rs]) => { rs.sort((x, y) => y.period.localeCompare(x.period)); const [cur, prev] = rs;
    const chg = prev && cur.unit !== "percent" && +prev.value ? (+cur.value / +prev.value - 1) * 100 : null;
    return `<tr><td class="l">${esc(nice(m))}</td><td>${money(cur.value, cur)}</td><td>${prev ? money(prev.value, prev) : "–"}</td><td>${chg == null ? "–" : pct(chg)}</td><td class="l">${cur.basis === "reported" ? grade("A") : grade("B")} <a href="${esc(cur.source_url)}" target="_blank" rel="noopener" title="${esc(cur.period)}${cur.note ? ": " + esc(cur.note) : ""}">source</a></td></tr>`; });
  const periods = Object.values(by).map(rs => rs[0].period);
  const latest = periods.sort().reverse()[0] || "";
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
    <div class="tablebox"><table><thead><tr><th class="l">Label</th><th class="l">Owner</th>${cols.map(([l, k]) => `<th data-lsort="${k}"${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${l}</th>`).join("")}</tr></thead><tbody>
    ${L.map(x => `<tr><td class="l"><a class="who" href="#/label/${x.slug}">${logo(x.name)}<span>${esc(x.name)}</span></a></td><td class="l">${esc(x.parent || "–")}</td><td>${x.n}</td><td>${count(x.ml)}</td><td>${count(x.cl)}</td><td>${usd(x.royalties)}</td><td>${x.rb || "–"}</td><td>${x.scout_avg ?? "–"}</td><td>${x.releases_2y || "–"}</td></tr>`).join("") || `<tr><td class="l" colspan="9">No label matches.</td></tr>`}
    </tbody></table></div><p class="note">Labels as printed on the artists' releases of the last two years. Royalties: what the roster's recordings generate a year across streaming services (mid estimate ${grade("C")}), paid to the label before the artists' share.</p></section>`;
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
  const total = store.data.artists.reduce((x, a) => x + a.ml, 0);
  const sister = (store.data.labels || []).filter(x => x.parent === L.parent && x.slug !== L.slug).slice(0, 8);
  const top = [...roster].sort((a, b) => (b.scout?.score ?? -1) - (a.scout?.score ?? -1))[0];
  const own = L.parent && L.parent !== L.name;
  app.innerHTML = `<section class="head labelhead">${logo(L.name, "logo big")}<div><h1>${esc(L.name)}</h1>
      <p class="sub">${L.status === "independent" ? "Independent label" : L.status === "major_distributed" ? "Distributed by a major" : "Major-label imprint"}${own ? ` · owned by <b>${esc(L.parent)}</b>` : ""} · ${roster.length} of hip-hop's top 1,000</p>
      ${own ? `<div class="parentchip">${logo(L.parent, "logo")}<span>Parent company: ${esc(L.parent)}</span></div>` : ""}</div></section>
    <section class="tiles">
      <div class="tile"><div class="k">Monthly listeners</div><div class="v">${count(L.ml)}</div><div class="s">${share(L.ml / total)} of the top 1,000, added per artist</div></div>
      <div class="tile"><div class="k">Current listeners</div><div class="v">${count(L.cl)}</div><div class="s">on recent releases</div></div>
      <div class="tile"><div class="k">Roster royalties / year</div><div class="v">${usd(L.royalties)}</div><div class="s">recordings, all streaming, mid ${grade("C")}</div></div>
      <div class="tile"><div class="k">Momentum</div><div class="v">${L.breaking + L.rising}</div><div class="s">${L.breaking} Breaking, ${L.rising} Rising · avg Scout ${L.scout_avg ?? "–"}</div></div>
      <div class="tile"><div class="k">Releases, last 2 years</div><div class="v">${L.releases_2y || "–"}</div><div class="s">across artists we track (Deezer)</div></div>
    </section>
    ${top?.scout ? `<section class="panel"><h2>The one to watch</h2><p><a href="#/a/${top.id}"><b>${esc(top.name)}</b></a>: Scout ${top.scout.score} ${tierChip(top.scout.tier)}, ${count(top.ml)} monthly listeners${top.top_fresh ? `, newest hit "${esc(top.top_fresh.title)}" at ${count(top.top_fresh.daily)} streams a day` : ""}.</p></section>` : ""}
    <section><h2>Roster</h2><div class="tablebox"><table><thead><tr><th class="l">Artist</th><th>Monthly listeners</th><th>Current listeners</th><th>Scout</th><th>New-release pull</th><th>Today</th><th>Royalties / yr</th><th class="l">Newest hit</th></tr></thead><tbody>
      ${roster.map(a => `<tr><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td>${count(a.ml)}</td><td>${count(a.cl)}</td><td>${a.scout ? `${a.scout.score} ${tierChip(a.scout.tier)}` : "–"}</td><td>${share(a.fresh_share)}</td><td>${pct(a.chg_pct)}</td><td>${usd(a.streaming_mid)}</td><td class="l wrap">${a.top_fresh ? esc(a.top_fresh.title) : `<span class="note">none in 90 days</span>`}</td></tr>`).join("")}
    </tbody></table></div><p class="note">Hip-hop artists in the top 1,000 whose recent releases carry this label. Royalties are paid to the label before the artist's share (see each artist's page).</p></section>
    <section class="panel"><h2>${esc(L.name)}: finances</h2>${own ? `<p class="note">${esc(L.name)} is part of ${esc(L.parent)} and publishes no accounts of its own. The best public measure of its size is the roster's royalties above.</p>` : finTable(L.name)}</section>
    ${(own ? L.parent : L.name) === "Sony Music" ? sonyMusicPanel() : ""}
    ${healthPanel((store.data.company_of || {})[own ? L.parent : L.name])}
    ${Object.entries(store.data.group_finances || {}).filter(([, F]) => F.uk?.labels.includes(L.name)).map(([c]) => healthPanel(c)).join("")}
    ${own ? `<section class="panel"><h2>${esc(L.parent)}: key reported figures</h2>${finTable(L.parent)}</section>` : ""}
    ${sister.length ? `<section class="panel"><h2>Other ${esc(L.parent)} labels in the top 1,000</h2><div class="chips">${sister.map(x => `<a class="chip" href="#/label/${x.slug}">${esc(x.name)} · ${x.artists.length}</a>`).join(" ")}</div></section>` : ""}
    ${(store.data.label_logos || {})[L.name] ? `<p class="note">Logo: <a href="${esc(store.data.label_logos[L.name].page)}" target="_blank" rel="noopener">Wikimedia Commons</a> (${esc(store.data.label_logos[L.name].licence)}). Trademarks belong to their owners.</p>` : ""}`;
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
const money2 = (v, cur) => v == null ? "–" : `${v < 0 ? "−" : ""}${({ EUR: "€", USD: "$", JPY: "¥", GBP: "£" })[cur] || ""}${count(Math.abs(v))}`;
const fmtRatio = (v, kind, cur) => v == null ? "–" : kind === "pct" ? (v * 100).toFixed(1) + "%" : kind === "x" ? v.toFixed(1) + "×" : money2(v, cur);
const readingChip = r => r ? `<span class="chip read-${r}">${({ good: "healthy", watch: "watch", weak: "weak" })[r]}</span>` : "";
function healthPanel(company) {
  const F = (store.data.group_finances || {})[company];
  if (!F) return "";
  const cur = F.currency, cols = [...F.years.map(y => ({ ...y, label: "FY " + y.period.slice(0, 7) })), ...F.quarters.map(q => ({ ...q, label: (q.type === "H" ? "H1 to " : "Q to ") + q.period.slice(0, 7) }))];
  const table = (st, title) => { const items = STMT[st].filter(i => cols.some(c => c.values[i] != null)); if (!items.length) return "";
    return `<h3>${title}</h3><div class="tablebox"><table><thead><tr><th class="l"></th>${cols.map(c => `<th${c.type !== "FY" ? ' class="q"' : ""}><a href="${esc(c.source)}" target="_blank" rel="noopener">${esc(c.label)}</a></th>`).join("")}</tr></thead><tbody>
      ${items.map(i => `<tr><td class="l">${esc(ITEM_LABEL[i])}</td>${cols.map(c => `<td${c.type !== "FY" ? ' class="q"' : ""}>${money2(c.values[i], cur)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`; };
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
    <div class="tablebox"><table><thead><tr><th class="l"></th>${cols.map(c => `<th${c.period_type !== "FY" ? ' class="q"' : ""}><a href="${esc(c.source)}" target="_blank" rel="noopener">${esc(c.label)}</a></th>`).join("")}</tr></thead><tbody>
    ${rows.map(([k, l]) => `<tr><td class="l">${k === "sales" || k === "operating_income" ? `<b>${l}</b>` : l}</td>${cols.map(c => `<td${c.period_type !== "FY" ? ' class="q"' : ""}>${yen(c.values[k])}</td>`).join("")}</tr>`).join("")}
    <tr><td class="l">Operating margin</td>${cols.map(c => `<td${c.period_type !== "FY" ? ' class="q"' : ""}>${c.values.sales && c.values.operating_income != null ? (c.values.operating_income / c.values.sales * 100).toFixed(1) + "%" : "–"}</td>`).join("")}</tr>
    <tr><td class="l">Sales growth, year on year</td>${cols.map(c => `<td${c.period_type !== "FY" ? ' class="q"' : ""}>${growth(c)}</td>`).join("")}</tr>
    </tbody></table></div>
    <p class="note">Sony's fiscal year ends on 31 March. Sales are to external customers by product category, as filed with the SEC (Form 6-K); shaded columns are quarters. Column headings link to the releases.</p></section>`;
}
function groupsCompare(uk = false) {
  const G = store.data.group_finances || {};
  const names = Object.keys(G).filter(n => !!G[n].uk === uk);
  if (!names.length) return "";
  return `<section class="panel"><h2>${uk ? "The majors' UK record companies" : "Label groups'"} financial health, side by side ${grade("A")}</h2><div class="tablebox"><table><thead><tr><th class="l">Measure</th>${names.map(n => `<th>${esc(n)}</th>`).join("")}</tr></thead><tbody>
    <tr><td class="l">Latest fiscal year</td>${names.map(n => `<td>${esc(G[n].years.at(-1)?.period || "–")}</td>`).join("")}</tr>
    <tr><td class="l">Revenue</td>${names.map(n => `<td>${money2(G[n].years.at(-1)?.values.revenue, G[n].currency)}</td>`).join("")}</tr>
    ${Object.entries(RATIO).map(([k, [l, kind]]) => `<tr><td class="l">${esc(l)}</td>${names.map(n => { const h = G[n].health[k]; return `<td>${h ? fmtRatio(h.value, kind, G[n].currency) + " " + readingChip(h.reading) : "–"}</td>`; }).join("")}</tr>`).join("")}
  </tbody></table></div><p class="note">${uk ? "Each company's statutory accounts at Companies House: the UK business only, where the groups' UK labels sign and market artists. A label page shows its UK company when the accounts name the label or its releases carry a UK name (\"Atlantic Records UK\")." : `Sony Group is the whole group (games, pictures, music, electronics). Bertelsmann (BMG's owner) files no machine-readable accounts, and private labels (EMPIRE, Concord before the BMG merger) publish none.`}</p></section>`;
}

// ---------- artist summary card: level, scout score, worth, attention
const midRange = r => `about ${usd(r.mid)}<br><span class="note">${range(r)}</span>`;
function summaryCard(a, rev) {
  const sc = a.scout, wo = rev.artist?.worth || a.worth, att = a.attention_series;
  return `<section class="card">
    <div class="cardcol"><h2>Level</h2><div class="big">${esc(a.level?.name || "–")}</div>
      <div class="chips">${(a.level?.badges || []).map(b => `<span class="chip badge">${esc(b)}</span>`).join(" ") || `<span class="note">no badges yet</span>`}</div>
      <p class="note"><span class="def" title="Rookie under 5m monthly listeners, Rising star 5m+, Headliner 15m+, Icon 40m+">How levels work</span></p></div>
    <div class="cardcol"><h2>Scout score</h2>${sc ? `<div class="big">${sc.score} ${tierChip(sc.tier)}</div><p class="note">against artists of ${esc(sc.band)} monthly listeners</p>${sc.tier && a.top_fresh?.id ? `<p class="hear">${playBtn(a)}<span>Newest hit: <b>${esc(a.top_fresh.title)}</b></span></p>` : ""}${sc.tier && a.video ? `<p class="hear">${videoBtn(a)}<span>Video (${esc(a.video.why)}): <b>${esc(a.video.title)}</b></span></p>` : ""}${factorBars(sc)}` : `<p class="note">Not enough signals yet.</p>`}</div>
    <div class="cardcol"><h2>Worth ${grade("C")}</h2>
      <dl class="kv"><dt>Artist keeps / year</dt><dd>${range(rev.artist_total || a.rev_total)}</dd>
      ${wo ? `<dt>Recordings would sell for</dt><dd>${midRange(wo.recordings)}</dd><dt>Artist's royalties</dt><dd>${midRange(wo.artist_royalties)}</dd><dt>Songwriting</dt><dd>${midRange(wo.publishing)}</dd>` : ""}</dl>
      ${wo ? `<p class="note">${esc(wo.vintage)} music: ${wo.multiple[0]}–${wo.multiple[1]}× a year's royalties. <a href="#/worth">How</a></p>` : ""}
      <h2 style="margin-top:10px">Wikipedia attention</h2>
      ${att ? `<div class="sparkrow">${sparkline(att.views)}<span>${trend(a.attention?.trend)} <span class="note">last 3 months against the 9 before</span></span></div><p class="note">Monthly English Wikipedia page views since ${esc(att.start)}.</p>` : `<p class="note">No English Wikipedia article linked.</p>`}
    </div></section>`;
}

// ---------- router
async function route() {
  // a static page (site/a/<slug>/, site/label/<slug>/) opens its artist or label until the visitor navigates
  let h = (location.hash || window.BOOT || "").replace(/^#\/?/, "").replace(/\?.*$/, "").split("/");
  GENRE = h[0] === "country" ? "country" : "hip_hop";
  if (GENRE !== "hip_hop") h = h.slice(1).length ? h.slice(1) : [""];
  document.documentElement.dataset.genre = GENRE;
  document.querySelectorAll("[data-genre]").forEach(a => a.dataset.genre === GENRE ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
  document.querySelectorAll(".mainnav a").forEach(a => { const base = a.dataset.href || a.getAttribute("href"); a.dataset.href = base; a.setAttribute("href", GENRE === "hip_hop" ? base : PREFIX() + base.slice(2)); });
  if (!genreStore[GENRE]) {
    const g = genreStore[GENRE] = { data: await (await fetch(`${DATA_DIR()}index.json`)).json() };
    // page-specific data loads in the background (D6); pages other than the start page and artist pages wait for it
    g.extra = fetch(`${DATA_DIR()}extra.json`).then(r => r.json()).then(x => Object.assign(g.data, x));
  }
  store.data = genreStore[GENRE].data;
  store.extra = genreStore[GENRE].extra;
  const NAMES = { movers: ["Artists", "Movers"], month: ["Artists", "Movers"], rising: ["Artists", "Movers"], compare: ["Artists", "Compare"],
    scout: ["Scout"], unsigned: ["Scout", "Unsigned vs signed peers"], producers: ["Scout", "Producers"],
    worth: ["Money"], pay: ["Money", "Pay gap by deal"], platforms: ["Money", "Platforms"], tours: ["Money", "Tours"],
    labels: ["Labels"], audience: ["Labels", "Where it is streamed"], method: ["Method"], state: ["State of hip-hop"] };
  const SEC = { Artists: "#/", Scout: "#/scout", Money: "#/worth", Labels: "#/labels", Method: "#/method" };
  crumbs((NAMES[h[0]] || []).map((t, i, xs) => [t, i < xs.length - 1 ? SEC[t] : ""]));
  const TITLES = { rising: "Rising hip-hop artists today", month: "Hip-hop movers: the last 30 days", movers: h[1] === "today" ? "Hip-hop movers today" : "Hip-hop movers: the last 30 days", pay: "Pay gap by record deal",
    platforms: "Hip-hop royalties by streaming platform", tours: "Hip-hop tours: gross and revenue per fan", audience: "Where hip-hop is streamed",
    unsigned: "Unsigned hip-hop artists against signed peers", method: "Method and sources", scout: "Scout: rising hip-hop artists for A&R",
    worth: "What is your music worth?", state: "State of hip-hop: the month in numbers", producers: "The producers and songwriters behind hip-hop's biggest songs", labels: "Who owns hip-hop: labels and market share", compare: "Compare hip-hop artists" };
  if (h[0] !== "" && h[0] !== "a") await store.extra;
  setMeta(TITLES[h[0]] || "Global hip-hop: listeners, earnings and labels of the top 1,000 artists");
  if (h[0] === "a") artist(decodeURIComponent(h[1]));
  else if (h[0] === "rising") rising();
  else if (h[0] === "movers") (h[1] === "today" ? rising() : monthPage());
  else if (h[0] === "month") monthPage();
  else if (h[0] === "producers") producersPage();
  else if (h[0] === "state") statePage(h[1]);
  else if (h[0] === "pay") pay();
  else if (h[0] === "platforms") platforms();
  else if (h[0] === "tours") tours();
  else if (h[0] === "audience") audience();
  else if (h[0] === "unsigned") unsignedPage();
  else if (h[0] === "method") method();
  else if (h[0] === "scout") scoutPage();
  else if (h[0] === "worth") { if (h[1]) { const a = store.data.artists.find(x => x.id === h[1]); ui.worth = { ...(ui.worth || { ml: 1000000, vintage: "auto" }), pick: h[1], deal: a && ["diy", "services", "independent", "major"].includes(a.deal_type) ? a.deal_type : "diy" }; } worthPage(); }
  else if (h[0] === "labels") labelsPage();
  else if (h[0] === "label") labelPage(decodeURIComponent(h[1] || ""));
  else if (h[0] === "compare") compare(h.slice(1).map(decodeURIComponent));
  else top();
  document.getElementById("foot").innerHTML = `Data as of ${esc(store.data.as_of)}; built ${esc(store.data.built)}. Sources: kworb.net (Spotify public counts), Wikidata, MusicBrainz, Deezer, Wikimedia Commons. Estimates are ranges, not reported figures. <a href="#/state">State of hip-hop</a> · <a href="#/method">Method</a> · <a href="mailto:swedenrocked@gmail.com?subject=Correction">Report a correction</a> · <a href="https://tventy.se/sport/">tventy sport</a>`;
  window.scrollTo(0, 0);
}
function setMeta(title, desc) {
  if (GENRE === "country") { title = title.replace(/Hip-hop|Hip-Hop/g, "Country").replace(/hip-hop/g, "country"); desc = desc && desc.replace(/hip-hop/g, "country"); }
  document.title = `${title} · tventy music`;
  const m = document.querySelector('meta[name="description"]');
  if (m) m.content = desc || "Who is drawing an audience in hip-hop, what the music earns, who owns it and who is about to break: the top 1,000 artists, updated daily, every figure sourced.";
}
addEventListener("hashchange", route);
bindSearchBox(document.getElementById("q"), document.getElementById("q-results"), true);
route().catch(e => { app.innerHTML = `<p class="note">Could not load the data: ${esc(e.message)}</p>`; });
