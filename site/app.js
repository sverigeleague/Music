// tventy music front end: reads site/data/index.json (built by src/site_build.py), no server.
// Pages: top 100, rising, artist, pay gap, method. What they show is set in config.js; the look in styles.css.
import { COLUMNS, RISING_LIMIT, DEALS, PLATFORM_COLUMNS } from "./config.js";

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
const SECTION = { top: "charts", rising: "charts", platforms: "charts", tours: "charts", audience: "charts",
  scout: "scout", unsigned: "scout", compare: "scout", worth: "worth", pay: "worth", labels: "labels", label: "labels", method: "method" };
const SUBNAV = {
  charts: [["top", "#/", "Top list"], ["rising", "#/rising", "Rising"], ["platforms", "#/platforms", "Platforms"], ["tours", "#/tours", "Tours"], ["audience", "#/audience", "Audience"]],
  scout: [["scout", "#/scout", "Scout list"], ["unsigned", "#/unsigned", "Unsigned vs signed peers"], ["compare", "#/compare", "Compare artists"]],
  worth: [["worth", "#/worth", "What is it worth?"], ["pay", "#/pay", "Pay gap by deal"]],
};
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
    else if (ev.key === "Enter" && hits[at]) { location.hash = hits[at].href; input.value = ""; close(); input.blur(); }
    else if (ev.key === "Escape") { close(); input.blur(); }
  });
  box.addEventListener("click", ev => { if (ev.target.closest("a")) { input.value = ""; close(); } });
  if (!global) return;
  document.addEventListener("click", ev => { if (!ev.target.closest(".search")) { close(); app.querySelectorAll(".results").forEach(b => (b.hidden = true)); } });
  document.addEventListener("keydown", ev => { if (ev.key === "/" && !/input|select|textarea/i.test(document.activeElement.tagName)) { ev.preventDefault(); input.focus(); } });
}

// Per-artist detail lives in 32 shard files (src/site_build.py): data/a/<second character's code % 32>.json.
const shards = {};
async function detailOf(id) {
  const n = id.charCodeAt(1) % 32;  // the second character: Spotify IDs all start with 0-7
  try { shards[n] = shards[n] || await (await fetch(`data/a/${n}.json`)).json(); } catch { shards[n] = {}; }
  return shards[n][id] || { lines: [], deals: [], artist: {}, artist_total: null };
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
  const head = COLS.map(c => `<th data-sort="${c[1]}"${c[1] === k ? ` aria-sort="${dir < 0 ? "descending" : "ascending"}"` : ""}>${esc(c[0])}</th>`).join("");
  const body = sorted.map(a => `<tr><td class="l">${a[rankKey]}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td>
    <td class="l">${a.label_status === "major" || a.label_status === "major_distributed" ? esc(a.label_owner || "Major") : a.label_status === "independent" ? "Independent label" : a.label_status === "self_released" ? "Unsigned" : a.label_status === "catalog" ? "Catalog" : (a.major ? esc(a.major) : "–")}${a.revivals?.length ? " " + chip("Revival", a.revivals.map(r => `${r.title} (${r.year})`).join(", ")) : ""}</td>${COLS.map(c => `<td>${cell(a, c)}</td>`).join("")}</tr>`).join("");
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Label group</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
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
      <div class="search big"><input id="q2" type="search" placeholder="Find an artist or a label, e.g. Drake, Interscope" autocomplete="off" aria-label="Search"><div class="results" id="q2-results" hidden></div></div>
      <div class="stats"><div><b>${all.length.toLocaleString()}</b><span>hip-hop artists tracked, of Spotify's top ${d.universe.toLocaleString()}</span></div><div><b>${count(total)}</b><span>combined monthly listeners</span></div><div><b>${labelsN}</b><span>labels with artists in the top 1,000</span></div><div><b>${esc(d.as_of)}</b><span>listener data as of</span></div></div></section>
    ${pulse()}
    <section class="doors">
      <a class="door" href="#/worth"><span class="k">For artists</span><b>What is your music worth?</b><span>Royalties, what you keep under each deal, and what the catalog would sell for.</span></a>
      <a class="door" href="#/scout"><span class="k">For labels</span><b>Find who is rising</b><span>${scoutTop.length ? `Breaking now: ${scoutTop.map(x => esc(x.name)).join(", ")}.` : "Momentum scores for the top 1,000."} Filter to unsigned artists and export.</span></a>
      <a class="door" href="#/labels"><span class="k">Market</span><b>Who owns hip-hop</b><span>The majors' and independents' share of the top 1,000, by size.</span></a>
    </section>
    
    ${subnav()}<section><h1>Top ${N} hip-hop artists on Spotify</h1>
    <p class="sub">${sub} ${all.length} of Spotify's top ${d.universe.toLocaleString()} artists are hip-hop or rap.</p>
    <div class="seg" role="group" aria-label="Ranking" style="margin-top:12px"><button type="button" data-by="current" aria-pressed="${ui.by === "current"}">Our ranking: current listeners</button><button type="button" data-by="monthly" aria-pressed="${ui.by === "monthly"}">Monthly listeners</button></div> ${sizeSwitch()}</section>
    <section class="tiles">
      <div class="tile"><div class="k">Combined monthly listeners</div><div class="v">${count(ml)}</div><div class="s">these ${N}, people counted once per artist</div></div>
      <div class="tile"><div class="k">Royalties generated / month</div><div class="v">${usd(gen)}</div><div class="s">Spotify recordings, top ${N}, mid estimate ${grade("C")}</div></div>
      <div class="tile"><div class="k">Biggest riser today</div><div class="v">${up ? esc(up.name) : "–"}</div><div class="s">${up ? pct(up.chg_pct) + " listeners" : ""}</div></div>
      <div class="tile"><div class="k">On a major label</div><div class="v">${majors} of ${hundred.length}</div><div class="s">from the labels on their recent releases</div></div>
    </section>
    <section><div class="toolbar"><input type="search" placeholder="Find an artist" value="${esc(ui.q)}" aria-label="Find an artist"></div>
      ${table(list, "pos")}<p class="note">${ui.by === "current" ? "* Provisional rank: 50–80% of the artist's streams are on dated songs; hover for the range. " : ""}Royalties generated are what Spotify pays the rights holders for the artist's own tracks (label or distributor), not the artist's pay. See the artist page and Pay gap.${ui.by === "current" && unranked.length ? ` Not yet ranked, because release dates are missing for too much of their listening: ${unranked.map(a => esc(a.name)).join(", ")}.` : ""}</p></section>`;
  app.querySelectorAll("[data-by]").forEach(b => b.onclick = () => { ui.by = b.dataset.by; ui.sort = [ui.by === "current" ? "cl" : "ml", -1]; top(); });
  bindSize(top);
  const inp = app.querySelector("input");
  inp.oninput = () => { ui.q = inp.value.toLowerCase(); const p = inp.selectionStart; top(); const i = app.querySelector("input"); i.focus(); i.setSelectionRange(p, p); };
  bindSort(top);
  bindSearchBox(document.getElementById("q2"), document.getElementById("q2-results"));
}

function rising() {
  nav("rising");
  const inTop = new Set(top100().map(a => a.id)), rest = store.data.artists.filter(a => !inTop.has(a.id) && a.chg_pct != null);
  const list = [...rest].sort((a, b) => b.chg_pct - a.chg_pct).slice(0, RISING_LIMIT).map((a, i) => ({ ...a, rrank: i + 1 }));
  app.innerHTML = `${subnav()}<section><h1>Rising: hip-hop outside the top 100</h1>
    <p class="sub">Biggest daily gains in monthly listeners among the ${rest.length} hip-hop artists outside the top 100. From the first full month, this page ranks month-on-month growth confirmed on a second platform (Breakout Watch, roadmap step 1.3).</p></section>
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
      ${U.map((u, i) => `<tr><td class="l">${i + 1}</td><td class="l"><a class="who" href="#/a/${u.id}">${pic(store.data.artists.find(a => a.id === u.id) || u)}<span>${esc(u.name)}</span></a></td>
        <td class="l wrap">${esc(u.label || "–")} ${u.confidence === "confirmed" ? chip("confirmed") : `<span class="chip warn" title="Own-name label with no other evidence: could be a small label or an imprint licensed to one">label name only</span>`}</td>
        <td>${count(u.ml)}</td><td>${count(u.cl)}</td><td>${usd(u.generated)}</td><td>${usd(u.keeps_now)}</td><td>${usd(u.peer_generated)}</td><td>${usd(u.if_signed.major)}</td><td>${(s => s ? `${s.score} ${tierChip(s.tier)}` : "–")(store.data.artists.find(a => a.id === u.id)?.scout)}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Yearly at today's pace, mid estimates, streaming only (all platforms). <b>Generates</b>: royalties paid for the recordings. <b>Keeps now</b>: ${pct("diy")} of that after a distributor's fee. <b>Signed peers generate</b>: the median of the five closest growing signed artists. <b>On a major deal</b>: ${pct("major")} of today's royalties, before any advance is recouped.</p></section>
    <section><h2>Each artist against their signed peers</h2>
      ${U.map(u => `<details class="panel"><summary><b>${esc(u.name)}</b>: ${count(u.ml)} monthly listeners, ${u.spl ? u.spl.toFixed(2) : "–"} streams a day per listener against ${u.peer_spl ? u.peer_spl.toFixed(2) : "–"} for the peers</summary>
        <div class="tablebox"><table><thead><tr><th class="l">Peer</th><th class="l">Label</th><th>Monthly listeners</th><th>Streams / day per listener</th><th>Generates / yr</th><th>Artist's slice</th></tr></thead><tbody>
        ${u.peers.map(p => `<tr><td class="l"><a href="#/a/${p.id}">${esc(p.name)}</a></td><td class="l">${esc(STATUS[p.status])}${p.owner ? " · " + esc(p.owner) : ""}</td><td>${count(p.ml)}</td><td>${p.spl ? p.spl.toFixed(2) : "–"}</td><td>${usd(p.generated)}</td><td>${usd(p.artist_slice)}</td></tr>`).join("")}
        <tr class="tot"><td class="l">${esc(u.name)} (unsigned)</td><td class="l">${esc(u.label || "")}</td><td>${count(u.ml)}</td><td>${u.spl ? u.spl.toFixed(2) : "–"}</td><td>${usd(u.generated)}</td><td>${usd(u.keeps_now)}</td></tr>
        </tbody></table></div>
        <p class="note">${u.at_peer_engagement ? `With the peers' streams per listener, ${esc(u.name)} would generate about ${usd(u.at_peer_engagement)} a year. ` : ""}Signed today, ${esc(u.name)} would keep about ${usd(u.if_signed.major)} on a major deal, ${usd(u.if_signed.independent)} with an independent label or ${usd(u.if_signed.services)} on label services, against ${usd(u.keeps_now)} now. Label money on signing (advances, marketing) is not public and not included.</p></details>`).join("")}
    </section>
    <p class="note">Peers: signed artists (major, major-distributed or independent label) with 0.6–1.67× the monthly listeners and at least 20% of their listening on recent releases, closest first. Statuses come from the labels printed on each artist's last two years of releases (Deezer) and the recording codes (ISRCs) of their recent songs; artists that cannot be placed are on the review list for the owner.</p>`;
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
  app.innerHTML = `${subnav()}<section><h1>Audience</h1>${sizeSwitch()}
    <p class="sub">Who listens, and where. Some of it can be measured from public data; some of it cannot, and this page says which.</p></section>
    <section class="tablebox"><table><thead><tr><th class="l">Question</th><th class="l">What we have</th><th class="l">Status</th></tr></thead><tbody>
      <tr><td class="l"><b>Which countries</b></td><td class="l wrap">Each artist's streams in Spotify's weekly top 200 of 76 countries (kworb.net, ${weeksLabel()})</td><td class="l">${chip("measured")} for ${withGeo.length} of the top 100</td></tr>
      <tr><td class="l"><b>Which cities</b></td><td class="l wrap">Spotify shows each artist's top 5 cities on its own site, but its terms bar collecting them</td><td class="l">not collected</td></tr>
      <tr><td class="l"><b>Age and gender, per artist</b></td><td class="l wrap">Not public for any platform. Licensed providers (Soundcharts from $50 a month, Chartmetric) model it from Instagram, YouTube and TikTok followers</td><td class="l">needs a licence (roadmap 2.3)</td></tr>
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
const STREAMING = ["spotify", "youtube", "apple_music", "amazon", "deezer", "tidal", "soundcloud", "audiomack", "tiktok", "meta", "others"];
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
  crumbs([["Charts", "#/"], [a.name]]);
  const m = a.money, yr = r => ({ low: r.low * 12, mid: r.mid * 12, high: r.high * 12 });
  const links = Object.entries(a.links).filter(([, u]) => u).map(([k, u]) => `<a href="${esc(u)}" rel="noopener" target="_blank">${esc(k[0].toUpperCase() + k.slice(1))}</a>`).join("");
  const leadShare = a.streams ? a.lead_streams / a.streams : null;
  app.innerHTML = `<section class="head">${pic(a, true)}<div><h1>${esc(a.name)} ${star(a.id)}</h1>
      <p class="sub">${a.cl_rank ? `#${a.cl_rank} in our ranking · ` : ""}#${a.rank} in hip-hop by listeners · #${a.rank_all} on Spotify overall${a.country ? " · " + esc(a.country) : ""}${a.since ? " · active since " + esc(a.since) : ""}</p>
      <div class="links" style="margin-top:10px">${links}<a href="#/compare/${a.id}">Compare with…</a><a href="#/worth/${a.id}">Worth on other deals</a></div></div></section>
    ${summaryCard(a, store.rev[id])}
    <section class="tiles">
      <div class="tile"><div class="k">Monthly listeners</div><div class="v">${count(a.ml)}</div><div class="s">${delta(a.chg)} today (${pct(a.chg_pct)})</div></div>
      <div class="tile"><div class="k">Current listeners</div><div class="v">${a.cl != null ? count(a.cl) + (a.cl_provisional ? `<span class="prov">*</span>` : "") : "–"}</div><div class="s">${a.cur_share != null ? Math.round(a.cur_share * 100) + "% of listening on recent releases" : "release dates missing"}${a.cl == null && a.cur_share != null ? " · not ranked yet" : ""}${a.cl_provisional ? ` · provisional: ${count(a.cl_range[0])}–${count(a.cl_range[1])} until more songs are dated` : ""}</div></div>
      <div class="tile"><div class="k">Peak</div><div class="v">${count(a.peak_ml)}</div><div class="s">best rank #${a.peak_rank} on Spotify</div></div>
      <div class="tile"><div class="k">Streams, all time</div><div class="v">${count(a.streams)}</div><div class="s">${count(a.daily)} a day</div></div>
      <div class="tile"><div class="k">YouTube views</div><div class="v">${count(a.yt_total)}</div><div class="s">${a.yt_daily ? count(a.yt_daily) + " a day" : "no data"}${a.yt_subs ? " · " + count(a.yt_subs) + " subscribers" : ""}</div></div>
      <div class="tile"><div class="k">Deezer fans</div><div class="v">${count(a.deezer_fans)}</div><div class="s">Deezer</div></div>
    </section>
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
  <p>Prototype, private. Every number has a source and a grade: <b>A</b> primary (company filings, regulators, court records, the platform's own disclosure), <b>B</b> reputable secondary, <b>C</b> our estimate, always shown as a range.</p>
  <h2>Who is in the list</h2><ul>
   <li>Spotify's top ${store.data.universe.toLocaleString()} artists by monthly listeners (kworb.net, which compiles Spotify's public pages; updated daily).</li>
   <li>Hip-hop or rap if most of the artist's genre votes are hip-hop (MusicBrainz community votes), with Wikidata genres where votes are thin. Borderline cases are decided by hand. Latin trap and reggaeton are a separate list for now.</li></ul>
  <h2>Our ranking</h2><p>The top 100 is ranked by <b>current listeners</b>: each artist's monthly listeners, counting the listening that comes from recent releases. Songs that came out years ago but are still streamed a lot add little, so the ranking shows who is drawing an audience with new music now. Release dates come from Deezer and MusicBrainz; an artist is ranked only when the dates cover most of their listening. Older songs that suddenly rise again are marked "Revival" and stay out of the ranking. The full method will be published here.</p>
  <h2>Numbers</h2><ul>
   <li><b>Monthly listeners:</b> unique listeners over the last 28 days, as Spotify shows them. Measured.</li>
   <li><b>Streams:</b> Spotify's public play counts summed over every track the artist is credited on (kworb.net); lead and featured credits apart. Measured.</li>
   <li><b>Royalties generated:</b> lead-artist streams × $2.50–4.40 per 1,000 (Duetti 2024 data; mid $3.00). Paid to the label or distributor. Estimate (C).</li>
   <li><b>Artist's share:</b> royalties generated × the share for the deal type (UK CMA, court filings, published distributor terms). The deal type is assumed from Wikidata's record-label list, which covers the whole career. Before recoupment. Estimate (C).</li>
   <li>Spotify's own figures for scale: it paid out more than $11bn in 2025; about 1,500 artists generated at least $1m and 80 at least $10m (recordings and publishing, before any split). <a href="https://newsroom.spotify.com/?p=39435" target="_blank" rel="noopener">Loud &amp; Clear</a> ${grade("A")}</li></ul>
  <h2>Scout score</h2><p>Six signals, each turned into a percentile among artists of a similar size (monthly listeners under 1.5m, 1.5–3m, 3–6m, 6–15m, 15m+), then averaged with these weights: ${Object.values(store.data.scout_factors).map(x => `${esc(x.label)} ${Math.round(x.weight * 100)}%`).join("; ")}. Tiers: Breaking 80+ (with a measured absolute signal), Rising 65+, Watch 50+; artists with 15m+ listeners get no tier. It is a pointer, not a prediction; the hit rate will be published once 90 days of history exist.</p>
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
    spl: a.daily && a.ml ? a.daily / a.ml : null, geo: (a.geo?.countries || 0) + (a.apple?.countries.length || 0), chg: a.chg_pct })[k];
  const [sk, sd] = f.sort;
  const rows = all.filter(ok).sort((a, b) => ((val(a, sk) ?? -Infinity) - (val(b, sk) ?? -Infinity)) * sd);
  const countries = [...new Set(all.map(a => a.country).filter(Boolean))].sort();
  const n = t => all.filter(a => a.scout.tier === t).length;
  const unsignedRising = all.filter(a => a.label_status === "self_released" && ["Breaking", "Rising"].includes(a.scout.tier));
  const seg = (key, opts) => `<div class="seg" role="group">${opts.map(([v, l]) => `<button type="button" data-f="${key}" data-v="${v}" aria-pressed="${f[key] === v}">${esc(l)}</button>`).join("")}</div>`;
  const cols = [["Scout score", "score"], ["Monthly listeners", "ml"], ["New-release pull", "fresh"], ["Current share", "cur"], ["Wikipedia, 3 mo", "att"], ["Streams / listener", "spl"], ["Chart countries", "geo"], ["Today", "chg"]];
  app.innerHTML = `${subnav()}<section><h1>Scout: who is rising</h1>
    <p class="sub">Every hip-hop artist in the top 1,000, scored 0–100 on six signals of momentum. Each artist is compared only with artists of a similar size, so a 1m-listener act that is taking off scores as high as a superstar. The score points at who to look at; it does not predict a hit.</p></section>
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
      <button type="button" class="btn" id="csv">Download CSV</button>
    </section>
    <section><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th>${cols.slice(0, 1).map(([l, k]) => `<th data-ssort="${k}"${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${esc(l)}</th>`).join("")}<th class="l">Label</th>${cols.slice(1).map(([l, k]) => `<th data-ssort="${k}"${k === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${esc(l)}</th>`).join("")}<th class="l">Newest hit</th></tr></thead><tbody>
      ${rows.map((a, i) => `<tr><td class="l">${star(a.id)} ${i + 1}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td><b>${a.scout.score}</b> ${tierChip(a.scout.tier)}</td><td class="l">${statusShort(a)}</td><td>${count(a.ml)}</td><td>${share(a.fresh_share)}</td><td>${share(a.cur_share)}</td><td>${trend(a.attention?.trend)}</td>
        <td>${val(a, "spl") ? val(a, "spl").toFixed(2) : "–"}</td><td title="Spotify weekly top 200 + Apple Music daily top 100">${val(a, "geo") || "–"}</td><td>${pct(a.chg_pct)}</td>
        <td class="l wrap">${a.top_fresh ? `${esc(a.top_fresh.title)} <span class="note">${count(a.top_fresh.daily)}/day, out ${esc(a.top_fresh.released)}</span>` : `<span class="note">none in 90 days</span>`}</td></tr>`).join("") || `<tr><td class="l" colspan="12">No artist matches these filters.</td></tr>`}
    </tbody></table></div>
    <p class="note">${rows.length} artists. Click a column to sort. ☆ adds an artist to your watchlist (kept in this browser). Percentiles are within the artist's size band (monthly listeners ${BANDS.join(", ")}).</p></section>
    <section class="panel"><h2>How the score works</h2>
      <ul>${Object.values(store.data.scout_factors).map(x => `<li><b>${Math.round(x.weight * 100)}%</b> ${esc(x.label)}</li>`).join("")}</ul>
      <p class="note">Each signal becomes a percentile (0–100) among artists in the same size band; the score is their weighted average over the signals the artist has (at least three). Tiers: Breaking 80+ (and either new songs pulling 25%+ of streams or Wikipedia attention up 30%+), Rising 65+, Watch 50+; artists with 15m+ monthly listeners are established and get no tier. Wikipedia views count only artists with an English article. Our own listener history started on 2026-10-23: once 90 days exist, listener growth joins the score and every month's picks are checked against what happened next, and that hit rate is published. ${grade("C")}</p></section>`;
  app.querySelectorAll("button[data-f]").forEach(b => b.onclick = () => { f[b.dataset.f] = b.dataset.v; scoutPage(); });
  bindStars(scoutPage);
  app.querySelectorAll("select[data-f]").forEach(s => s.onchange = () => { f[s.dataset.f] = s.value; scoutPage(); });
  app.querySelectorAll("th[data-ssort]").forEach(th => th.onclick = () => { f.sort = [th.dataset.ssort, sk === th.dataset.ssort ? -sd : -1]; scoutPage(); });
  app.querySelector("#csv").onclick = () => download("tventy-music-scout.csv", [["name", "spotify_url", "scout_score", "tier", "label_status", "label_group", "country", "monthly_listeners", "current_listeners", "new_release_share", "current_share", "wikipedia_trend", "streams_per_listener", "countries_charting", "newest_hit"],
    ...rows.map(a => [a.name, `https://open.spotify.com/artist/${a.id}`, a.scout.score, a.scout.tier || "", a.label_status, a.label_owner || "", a.country || "", a.ml, a.cl ?? "", a.fresh_share ?? "", a.cur_share ?? "", a.attention?.trend ?? "", val(a, "spl")?.toFixed(3) ?? "", val(a, "geo"), a.top_fresh?.title || ""])]);
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
  const indies = Object.entries(Object.assign({}, ...G.map(g => m.groups[g].labels))).sort((a, b) => b[1].ml - a[1].ml);
  const byId = Object.fromEntries(store.data.artists.map(a => [a.id, a]));
  app.innerHTML = `<section><h1>Labels: who owns hip-hop's top 1,000</h1>
    <p class="sub">The label behind each artist's recent releases, grouped by the company that owns it. The three majors hold most of the audience at the top; lower down, independent labels and self-released artists take a bigger share: where small labels can still sign talent.</p></section>
    <section class="tiles">
      <div class="tile"><div class="k">Majors' share of listeners</div><div class="v">${share(majShare("ml"))}</div><div class="s">of the top 1,000's monthly listeners (${share(majShare("artists"))} of artists)</div></div>
      <div class="tile"><div class="k">Majors, artists 15m+</div><div class="v">${share(majBand(4))}</div><div class="s">of those whose label is known</div></div>
      <div class="tile"><div class="k">Majors, under 1.5m</div><div class="v">${share(majBand(0))}</div><div class="s">of those whose label is known</div></div>
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
      <p class="note">Among artists whose label is known, the majors hold ${share(majBand(4))} of those with 15m+ monthly listeners and ${share(majBand(0))} of those under 1.5m. ${m.catalog ? `${m.catalog} catalog acts (no release in two years) are left out. ` : ""}Monthly listeners are added up per artist, so a fan of two artists counts twice. "Not yet known": no label read from recent releases yet (owner's review list). Groups follow the label printed on the last two years of releases (Deezer), checked against recording codes; distribution deals with a major count under that major.</p></section>
    <section class="panel"><h2>Independent labels and distributors in the top 1,000</h2>
      <div class="tablebox"><table><thead><tr><th class="l">Label</th><th>Artists</th><th>Monthly listeners</th></tr></thead><tbody>
      ${indies.map(([l, v]) => `<tr><td class="l">${esc(l)}</td><td>${v.artists}</td><td>${count(v.ml)}</td></tr>`).join("")}</tbody></table></div></section>
    ${groupsCompare()}
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
    </tbody></table></div><p class="note">Money lines are estimates (grade C); see each artist's page for the ranges and sources.</p></section>` : `<p class="note">Pick two artists.</p>`}`;
  app.querySelectorAll("input[data-i]").forEach(inp => inp.onchange = () => {
    const a = d.artists.find(x => x.name.toLowerCase() === inp.value.trim().toLowerCase());
    if (!a) return;
    const next = A.map(x => x.id); next[+inp.dataset.i] = a.id;
    location.hash = "#/compare/" + next.filter(Boolean).join("/");
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
    ${healthPanel((store.data.company_of || {})[own ? L.parent : L.name])}
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
const money2 = (v, cur) => v == null ? "–" : `${v < 0 ? "−" : ""}${({ EUR: "€", USD: "$", JPY: "¥" })[cur] || ""}${count(Math.abs(v))}`;
const fmtRatio = (v, kind, cur) => v == null ? "–" : kind === "pct" ? (v * 100).toFixed(1) + "%" : kind === "x" ? v.toFixed(1) + "×" : money2(v, cur);
const readingChip = r => r ? `<span class="chip read-${r}">${({ good: "healthy", watch: "watch", weak: "weak" })[r]}</span>` : "";
function healthPanel(company) {
  const F = (store.data.group_finances || {})[company];
  if (!F) return "";
  const cur = F.currency, cols = [...F.years.map(y => ({ ...y, label: "FY " + y.period.slice(0, 7) })), ...F.quarters.map(q => ({ ...q, label: "Q to " + q.period.slice(0, 7) }))];
  const table = (st, title) => { const items = STMT[st].filter(i => cols.some(c => c.values[i] != null)); if (!items.length) return "";
    return `<h3>${title}</h3><div class="tablebox"><table><thead><tr><th class="l"></th>${cols.map(c => `<th${c.type === "Q" ? ' class="q"' : ""}><a href="${esc(c.source)}" target="_blank" rel="noopener">${esc(c.label)}</a></th>`).join("")}</tr></thead><tbody>
      ${items.map(i => `<tr><td class="l">${esc(ITEM_LABEL[i])}</td>${cols.map(c => `<td${c.type === "Q" ? ' class="q"' : ""}>${money2(c.values[i], cur)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`; };
  return `<section class="panel"><h2>${esc(company)}: financial health ${grade("A")}</h2>
    ${F.note ? `<p class="note">${esc(F.note)}.</p>` : ""}
    <div class="healthgrid">${Object.entries(RATIO).filter(([k]) => F.health[k]).map(([k, [l, kind]]) => `<div class="hcell"><span class="k">${esc(l)}</span><b>${fmtRatio(F.health[k].value, kind, cur)}</b>${readingChip(F.health[k].reading)}</div>`).join("")}</div>
    <p class="note">Latest fiscal year (${esc(F.years.at(-1)?.period || "–")}), from the company's filed statements (${esc(F.source_kind)}). Readings are credit-analysis rules of thumb, not ratings; the current-ratio bands are set lower for music groups, whose royalties owed to artists and songwriters sit in current liabilities. Compare the groups with each other rather than with other industries.</p>
    ${table("IS", "Income statement")}${table("BS", "Balance sheet")}${table("CF", "Cash flow")}
    <p class="note">Figures as filed, in ${esc(cur)}. Column headings link to the filings. Quarter columns are the three months to that date. A blank means the company does not tag that line in its XBRL; the full statements are in the filing.</p></section>`;
}
function groupsCompare() {
  const G = store.data.group_finances || {};
  const names = Object.keys(G);
  if (!names.length) return "";
  return `<section class="panel"><h2>Label groups' financial health, side by side ${grade("A")}</h2><div class="tablebox"><table><thead><tr><th class="l">Measure</th>${names.map(n => `<th>${esc(n)}</th>`).join("")}</tr></thead><tbody>
    <tr><td class="l">Latest fiscal year</td>${names.map(n => `<td>${esc(G[n].years.at(-1)?.period || "–")}</td>`).join("")}</tr>
    <tr><td class="l">Revenue</td>${names.map(n => `<td>${money2(G[n].years.at(-1)?.values.revenue, G[n].currency)}</td>`).join("")}</tr>
    ${Object.entries(RATIO).map(([k, [l, kind]]) => `<tr><td class="l">${esc(l)}</td>${names.map(n => { const h = G[n].health[k]; return `<td>${h ? fmtRatio(h.value, kind, G[n].currency) + " " + readingChip(h.reading) : "–"}</td>`; }).join("")}</tr>`).join("")}
  </tbody></table></div><p class="note">Sony Group is the whole group (games, pictures, music, electronics). Bertelsmann (BMG's owner) files no machine-readable accounts, and private labels (EMPIRE, Concord before the BMG merger) publish none.</p></section>`;
}

// ---------- artist summary card: level, scout score, worth, attention
const midRange = r => `about ${usd(r.mid)}<br><span class="note">${range(r)}</span>`;
function summaryCard(a, rev) {
  const sc = a.scout, wo = rev.artist?.worth || a.worth, att = a.attention_series;
  return `<section class="card">
    <div class="cardcol"><h2>Level</h2><div class="big">${esc(a.level?.name || "–")}</div>
      <div class="chips">${(a.level?.badges || []).map(b => `<span class="chip badge">${esc(b)}</span>`).join(" ") || `<span class="note">no badges yet</span>`}</div>
      <p class="note">Rookie under 5m monthly listeners, Rising star 5m+, Headliner 15m+, Icon 40m+.</p></div>
    <div class="cardcol"><h2>Scout score</h2>${sc ? `<div class="big">${sc.score} ${tierChip(sc.tier)}</div><p class="note">against artists of ${esc(sc.band)} monthly listeners</p>${factorBars(sc)}` : `<p class="note">Not enough signals yet.</p>`}</div>
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
  if (!store.data) store.data = await (await fetch("data/index.json")).json();
  const h = location.hash.replace(/^#\/?/, "").split("/");
  const NAMES = { rising: ["Charts", "Rising"], platforms: ["Charts", "Platforms"], tours: ["Charts", "Tours"], audience: ["Charts", "Audience"],
    scout: ["Scout"], unsigned: ["Scout", "Unsigned vs signed peers"], compare: ["Scout", "Compare artists"], worth: ["Worth"], pay: ["Worth", "Pay gap by deal"],
    labels: ["Labels"], method: ["Method"] };
  const SEC = { Charts: "#/", Scout: "#/scout", Worth: "#/worth", Labels: "#/labels", Method: "#/method" };
  crumbs((NAMES[h[0]] || []).map((t, i, xs) => [t, i < xs.length - 1 ? SEC[t] : ""]));
  if (h[0] === "a") artist(decodeURIComponent(h[1]));
  else if (h[0] === "rising") rising();
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
  document.getElementById("foot").innerHTML = `Data as of ${esc(store.data.as_of)}; built ${esc(store.data.built)}. Sources: kworb.net (Spotify public counts), Wikidata, MusicBrainz, Deezer, Wikimedia Commons. Estimates are ranges, not reported figures. <a href="#/method">Method</a> · <a href="mailto:swedenrocked@gmail.com?subject=Correction">Report a correction</a> · <a href="https://tventy.se/sport/">tventy sport</a>`;
  window.scrollTo(0, 0);
}
addEventListener("hashchange", route);
bindSearchBox(document.getElementById("q"), document.getElementById("q-results"), true);
route().catch(e => { app.innerHTML = `<p class="note">Could not load the data: ${esc(e.message)}</p>`; });
