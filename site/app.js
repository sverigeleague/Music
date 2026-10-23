// Rap Ledger front end: reads site/data/index.json (built by src/site_build.py), no server.
// Pages: top 100, rising, artist, pay gap, method. What they show is set in config.js; the look in styles.css.
import { COLUMNS, RISING_LIMIT, DEALS, PLATFORM_COLUMNS } from "./config.js";

const app = document.getElementById("app");
const store = { data: null, rev: {} };
const ui = { sort: ["cl", -1], q: "", by: "current" };

// ---------- helpers
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const initials = n => String(n || "").split(/[\s\-–]+/).filter(w => /^[\p{L}\d]/u.test(w)).slice(0, 2).map(w => w[0]).join("").toUpperCase();
const pic = (a, big) => a.photo
  ? `<img class="pic${big ? " big" : ""}" src="${esc(a.photo.file)}" alt="" loading="lazy" decoding="async">`
  : `<span class="pic none${big ? " big" : ""}" aria-hidden="true">${esc(initials(a.name))}</span>`;
function count(v) {
  if (v == null) return "–";
  const a = Math.abs(v);
  return a >= 1e9 ? (v / 1e9).toFixed(2) + "bn" : a >= 1e6 ? (v / 1e6).toFixed(1) + "m" : a >= 1e3 ? (v / 1e3).toFixed(0) + "k" : String(v);
}
const usd = v => v == null ? "–" : "$" + count(Math.round(v));
const range = r => r ? `${usd(r.low)}–${usd(r.high)}` : "–";
const delta = v => v == null ? "–" : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${v > 0 ? "+" : ""}${count(v)}</span>`;
const pct = v => v == null ? "–" : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${v > 0 ? "+" : ""}${v.toFixed(2)}%</span>`;
const cell = (a, [, key, f]) => {
  const v = key === "gen_mid" ? a.money?.generated.mid : a[key];
  return f === "count" ? count(v) : f === "delta" ? delta(v) : f === "pct" ? pct(v) : f === "money" ? usd(v)
    : f === "share" ? (v == null ? "–" : Math.round(v * 100) + "%") : f === "int" ? (v ?? "–") : esc(v);
};
const chip = (t, title) => `<span class="chip" title="${esc(title || "")}">${esc(t)}</span>`;
const grade = g => `<span class="chip c" title="A primary, B reputable secondary, C our estimate">${esc(g)}</span>`;
const nav = id => document.querySelectorAll("[id^=nav-]").forEach(a => a.id === "nav-" + id ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));

// ---------- pages
function table(rows, rankKey = "rank") {
  const COLS = COLUMNS[ui.by];
  const [k, dir] = ui.sort;
  const val = a => k === "gen_mid" ? a.money?.generated.mid : a[k];
  const sorted = [...rows].sort((a, b) => ((val(a) ?? -Infinity) > (val(b) ?? -Infinity) ? 1 : -1) * dir);
  const head = COLS.map(c => `<th data-sort="${c[1]}"${c[1] === k ? ` aria-sort="${dir < 0 ? "descending" : "ascending"}"` : ""}>${esc(c[0])}</th>`).join("");
  const body = sorted.map(a => `<tr><td class="l">${a[rankKey]}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td>
    <td class="l">${a.major ? esc(a.major) : a.labels.length ? "Independent" : "–"}${a.revivals?.length ? " " + chip("Revival", a.revivals.map(r => `${r.title} (${r.year})`).join(", ")) : ""}</td>${COLS.map(c => `<td>${cell(a, c)}</td>`).join("")}</tr>`).join("");
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th class="l">Label group</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
function bindSort(rerender) {
  app.querySelectorAll("th[data-sort]").forEach(th => th.onclick = () => {
    ui.sort = [th.dataset.sort, ui.sort[0] === th.dataset.sort ? -ui.sort[1] : -1]; rerender();
  });
}

function top100() {
  const all = store.data.artists;
  if (ui.by === "monthly") return all.slice(0, 100).map(a => ({ ...a, pos: a.rank }));
  return all.filter(a => a.cl_rank && a.cl_rank <= 100).sort((a, b) => a.cl_rank - b.cl_rank).map(a => ({ ...a, pos: a.cl_rank }));
}
function top() {
  nav("top");
  const d = store.data, all = d.artists, hundred = top100();
  const list = hundred.filter(a => a.name.toLowerCase().includes(ui.q));
  const ml = hundred.reduce((s, a) => s + a.ml, 0);
  const gen = hundred.reduce((s, a) => s + (a.money?.generated.mid || 0), 0);
  const up = [...hundred].sort((a, b) => (b.chg_pct ?? -1e9) - (a.chg_pct ?? -1e9))[0];
  const majors = hundred.filter(a => a.major).length;
  const unranked = all.filter(a => a.cl == null);
  const sub = ui.by === "current"
    ? `Ranked by current listeners: each artist's monthly listeners, counting the listening that comes from recent releases, so songs from years ago that are still streamed a lot do not decide the order. ${esc(d.as_of)}.`
    : `Ranked by Spotify monthly listeners, ${esc(d.as_of)}.`;
  app.innerHTML = `<section><h1>Top 100 hip-hop artists on Spotify</h1>
    <p class="sub">${sub} ${all.length} of Spotify's top ${d.universe.toLocaleString()} artists are hip-hop or rap.</p>
    <div class="seg" role="group" aria-label="Ranking" style="margin-top:12px"><button type="button" data-by="current" aria-pressed="${ui.by === "current"}">Our ranking: current listeners</button><button type="button" data-by="monthly" aria-pressed="${ui.by === "monthly"}">Monthly listeners</button></div></section>
    <section class="tiles">
      <div class="tile"><div class="k">Combined monthly listeners</div><div class="v">${count(ml)}</div><div class="s">these 100, people counted once per artist</div></div>
      <div class="tile"><div class="k">Royalties generated / month</div><div class="v">${usd(gen)}</div><div class="s">Spotify recordings, top 100, mid estimate ${grade("C")}</div></div>
      <div class="tile"><div class="k">Biggest riser today</div><div class="v">${up ? esc(up.name) : "–"}</div><div class="s">${up ? pct(up.chg_pct) + " listeners" : ""}</div></div>
      <div class="tile"><div class="k">On a major label</div><div class="v">${majors} of 100</div><div class="s">as listed on Wikidata ${grade("B")}</div></div>
    </section>
    <section><div class="toolbar"><input type="search" placeholder="Find an artist" value="${esc(ui.q)}" aria-label="Find an artist"></div>
      ${table(list, "pos")}<p class="note">Royalties generated are what Spotify pays the rights holders for the artist's own tracks (label or distributor), not the artist's pay. See the artist page and Pay gap.${ui.by === "current" && unranked.length ? ` Not yet ranked, because release dates are missing for too much of their listening: ${unranked.map(a => esc(a.name)).join(", ")}.` : ""}</p></section>`;
  app.querySelectorAll("[data-by]").forEach(b => b.onclick = () => { ui.by = b.dataset.by; ui.sort = [ui.by === "current" ? "cl" : "ml", -1]; top(); });
  const inp = app.querySelector("input");
  inp.oninput = () => { ui.q = inp.value.toLowerCase(); const p = inp.selectionStart; top(); const i = app.querySelector("input"); i.focus(); i.setSelectionRange(p, p); };
  bindSort(top);
}

function rising() {
  nav("rising");
  const inTop = new Set(top100().map(a => a.id)), rest = store.data.artists.filter(a => !inTop.has(a.id) && a.chg_pct != null);
  const list = [...rest].sort((a, b) => b.chg_pct - a.chg_pct).slice(0, RISING_LIMIT).map((a, i) => ({ ...a, rrank: i + 1 }));
  app.innerHTML = `<section><h1>Rising: hip-hop outside the top 100</h1>
    <p class="sub">Biggest daily gains in monthly listeners among the ${rest.length} hip-hop artists outside the top 100. From the first full month, this page ranks month-on-month growth confirmed on a second platform (Breakout Watch, roadmap step 1.3).</p></section>
    <section>${tableRising(list)}</section>`;
}
function tableRising(list) {
  return `<div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th><th>Hip-hop rank</th><th>Monthly listeners</th><th>Today</th><th>Today %</th><th>Peak listeners</th></tr></thead><tbody>
  ${list.map(a => `<tr><td class="l">${a.rrank}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td><td>${a.rank}</td><td>${count(a.ml)}</td><td>${delta(a.chg)}</td><td>${pct(a.chg_pct)}</td><td>${count(a.peak_ml)}</td></tr>`).join("")}</tbody></table></div>`;
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
  app.innerHTML = `<section><h1>Streaming platforms</h1>
    <p class="sub">What each service pays, what we can measure, and where the top 100's streaming money comes from. Spotify streams and YouTube views are measured. The other services publish no play counts, so their royalties are estimated from each artist's Spotify royalties, using each service's share of label streaming revenue in Warner and Universal's filings.</p></section>
    <section class="panel"><h2>Where the top 100's recording royalties come from, per year ${grade("C")}</h2>
      <div class="bars">${totals.map(([k, v]) => `<div class="barrow"><span>${esc(P[k]?.name || k)}${measured(k) ? " " + chip("measured") : ""}</span><div class="track"><i style="left:0;width:${v / max * 100}%"></i></div><span>${usd(v)} · ${Math.round(v / sum * 100)}%</span></div>`).join("")}</div>
      <p class="note">Mid estimates of royalties paid to the labels and distributors, before the artists' share: ${usd(sum)} a year in total.</p></section>
    <section><h2>How each service pays</h2><div class="tablebox"><table><thead><tr><th class="l">Service</th><th class="l">How it pays</th><th>Per 1,000 plays</th><th>Grade</th><th class="l">Our data</th></tr></thead><tbody>
      ${Object.values(P).map(p => `<tr><td class="l"><b>${esc(p.name)}</b></td><td class="l wrap">${esc(p.payout_model)}${M[p.platform] ? ` <span class="note">Our estimate: Spotify royalties × ${(+M[p.platform].low).toFixed(2)}–${(+M[p.platform].high).toFixed(2)}.</span>` : ""}</td><td>${rate(p)}</td><td>${grade(p.grade)}</td><td class="l wrap">${esc(p.our_data)}${p.source?.startsWith("http") ? ` <a href="${esc(p.source)}" target="_blank" rel="noopener">source</a>` : ""}</td></tr>`).join("")}
    </tbody></table></div></section>
    <section><h2>Top 100 by platform</h2><div class="tablebox"><table><thead><tr><th class="l">#</th><th class="l">Artist</th>${PLATFORM_COLUMNS.map(c => `<th data-psort="${c[1]}"${c[1] === sk ? ` aria-sort="${sd < 0 ? "descending" : "ascending"}"` : ""}>${esc(c[0])}</th>`).join("")}</tr></thead><tbody>
      ${rows.map(a => `<tr><td class="l">${a.pos}</td><td class="l"><a class="who" href="#/a/${a.id}">${pic(a)}<span>${esc(a.name)}</span></a></td>${PLATFORM_COLUMNS.map(([, k, f]) => { const v = val(a, k); return `<td>${f === "money" ? usd(v) : count(v)}</td>`; }).join("")}</tr>`).join("")}
    </tbody></table></div><p class="note">Royalties per year at today's pace, mid estimate, paid to the rights holders. Click a column to sort.</p></section>`;
  app.querySelectorAll("th[data-psort]").forEach(th => th.onclick = () => { ui.psort = [th.dataset.psort, sk === th.dataset.psort ? -sd : -1]; platforms(); });
}

function bar(label, r, max, extra = "") {
  const w = v => Math.max(0, Math.min(100, v / max * 100));
  return `<div class="barrow"><span>${esc(label)}</span><div class="track"><i class="range" style="left:${w(r.low)}%;width:${w(r.high) - w(r.low)}%"></i><i style="left:${w(r.mid)}%;width:2px"></i></div><span>${range(r)}${extra}</span></div>`;
}

function artist(id) {
  nav("");
  const a = store.data.artists.find(x => x.id === id);
  if (!a) { app.innerHTML = `<p>Artist not found. <a href="#/">Back to the top 100</a></p>`; return; }
  document.getElementById("crumbs").innerHTML = `<a href="#/">Top 100</a> / ${esc(a.name)}`;
  const m = a.money, yr = r => ({ low: r.low * 12, mid: r.mid * 12, high: r.high * 12 });
  const links = Object.entries(a.links).filter(([, u]) => u).map(([k, u]) => `<a href="${esc(u)}" rel="noopener" target="_blank">${esc(k[0].toUpperCase() + k.slice(1))}</a>`).join("");
  const leadShare = a.streams ? a.lead_streams / a.streams : null;
  app.innerHTML = `<section class="head">${pic(a, true)}<div><h1>${esc(a.name)}</h1>
      <p class="sub">${a.cl_rank ? `#${a.cl_rank} in our ranking · ` : ""}#${a.rank} in hip-hop by listeners · #${a.rank_all} on Spotify overall${a.country ? " · " + esc(a.country) : ""}${a.since ? " · active since " + esc(a.since) : ""}</p>
      <div class="links" style="margin-top:10px">${links}</div></div></section>
    <section class="tiles">
      <div class="tile"><div class="k">Monthly listeners</div><div class="v">${count(a.ml)}</div><div class="s">${delta(a.chg)} today (${pct(a.chg_pct)})</div></div>
      <div class="tile"><div class="k">Current listeners</div><div class="v">${a.cl != null ? count(a.cl) : "–"}</div><div class="s">${a.cur_share != null ? Math.round(a.cur_share * 100) + "% of listening on recent releases" : "release dates missing"}${a.cl == null && a.cur_share != null ? " · not ranked yet" : ""}</div></div>
      <div class="tile"><div class="k">Peak</div><div class="v">${count(a.peak_ml)}</div><div class="s">best rank #${a.peak_rank} on Spotify</div></div>
      <div class="tile"><div class="k">Streams, all time</div><div class="v">${count(a.streams)}</div><div class="s">${count(a.daily)} a day</div></div>
      <div class="tile"><div class="k">YouTube views</div><div class="v">${count(a.yt_total)}</div><div class="s">${a.yt_daily ? count(a.yt_daily) + " a day" : "no data"}</div></div>
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
        <dt>Labels on record</dt><dd>${esc(a.labels.slice(0, 3).join(", ") || "–")}${a.labels.length > 3 ? ` +${a.labels.length - 3}` : ""}</dd>
      </dl><p class="note">Stream totals as of ${esc(a.streams_date || "–")} (kworb.net, from Spotify's public play counts).</p></div>
    </section>
    ${a.revivals?.length ? `<section class="panel"><h2>Revival</h2><p>${a.revivals.map(r => `<b>${esc(r.title)}</b> (${r.year}) is up ${Math.round(r.rise * 100)}% in daily streams on a month ago.`).join(" ")} Older songs that come back stay out of current listeners.</p></section>` : ""}
    <section class="panel" id="deals" hidden></section>
    <section class="note">Genre: ${esc(a.genre_basis)}.${a.photo ? ` Photo: ${esc(a.photo.author)}, <a href="${esc(a.photo.page)}" target="_blank" rel="noopener">${esc(a.photo.license)}</a>, via Wikimedia Commons.` : ""}</section>`;
  revenuePanel(a);
}

// ---------- revenue streams (artist page): detail from data/a/<id>.json
async function revenuePanel(a) {
  const box = document.getElementById("revenue");
  let rev = store.rev[a.id];
  if (!rev) {
    try { rev = store.rev[a.id] = await (await fetch(`data/a/${a.id}.json`)).json(); }
    catch { if (box) box.innerHTML = `<h2>Revenue streams</h2><p class="note">Could not load the estimate.</p>`; return; }
  }
  if (!box || !document.body.contains(box)) return;
  const m = a.money, groups = ["Streaming", "Publishing", "Live"];
  const rowsFor = g => rev.lines.filter(l => l.group === g).map(l => `<tr title="${esc(l.basis)}"><td class="l">${esc(l.label)}</td><td>${range(l.generated)}</td><td>${l.artist ? range(l.artist) : "–"}</td><td>${grade(l.grade)}</td></tr>`).join("");
  const hasLive = rev.lines.some(l => l.group === "Live");
  box.innerHTML = `<h2>Revenue streams, per year at today's pace</h2>
    <div class="tablebox"><table><thead><tr><th class="l">Source</th><th>Generated</th><th>Artist's slice</th><th>Grade</th></tr></thead><tbody>
    ${groups.map(g => rev.lines.some(l => l.group === g) ? `<tr class="sec"><td class="l" colspan="4">${g}</td></tr>${rowsFor(g)}` : "").join("")}
    ${hasLive ? "" : `<tr class="sec"><td class="l" colspan="4">Live</td></tr><tr><td class="l">Touring and merch</td><td class="l note" colspan="3">No reported tour gross in the last 12 months</td></tr>`}
    <tr class="tot"><td class="l">Artist's slice, total</td><td></td><td>${range(rev.artist_total)}</td><td></td></tr></tbody></table></div>
    <p class="note"><b>Generated</b>: what the activity brings in before anyone's cut (royalties paid to the label or distributor, box office, merch sales). <b>Artist's slice</b>: before their manager, lawyer and tax. Recordings assume ${m ? `<b>${esc(m.deal_label)}</b>` : "an unknown deal"}${a.major ? ` (${esc(a.major)}, from Wikidata's record-label list)` : ""}, before advances are recouped. Spotify and YouTube are measured; the other services are estimated from Spotify. Hover a row for its basis.</p>`;
  const tours = rev.lines.find(l => l.key === "touring")?.tours || [];
  const dbox = document.getElementById("deals");
  if (dbox && (tours.length || rev.deals.length)) {
    dbox.hidden = false;
    dbox.innerHTML = `${tours.length ? `<h2>Tours counted</h2><ul class="note">${tours.map(t => `<li><b>${esc(t.tour)}</b>, ${esc(t.start)}${t.end ? " to " + esc(t.end) : ""}: ${usd(t.gross)} gross${t.tickets ? `, ${count(t.tickets)} tickets (${usd(t.gross / t.tickets)} a fan)` : ""}${t.share < 1 ? `, ${Math.round(t.share * 100)}% of it in the last 12 months` : ""} ${grade(t.grade || "C")} ${t.source ? `<a href="${esc(t.source)}" target="_blank" rel="noopener">source</a>` : ""}</li>`).join("")}</ul>` : ""}
      ${rev.deals.length ? `<h2>Reported deals and other income</h2><ul class="note">${rev.deals.map(d => `<li><b>${esc(d.category)}:</b> ${esc(d.item)}${d.year ? ` (${esc(d.year)})` : ""}${d.amount_usd ? `: ${usd(+d.amount_usd)}` : ""}${d.amount_note ? `, ${esc(d.amount_note)}` : ""} ${grade(d.grade || "C")} ${d.source_url ? `<a href="${esc(d.source_url)}" target="_blank" rel="noopener">source</a>` : ""}</li>`).join("")}</ul>` : ""}`;
  }
}

function pay() {
  nav("pay");
  const sp = store.data.rates.find(r => r.item === "master_per_1000");
  app.innerHTML = `<section><h1>Pay gap: same streams, different deals</h1>
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
  <h2>Not yet included</h2><p>Apple Music, YouTube, Amazon, TikTok and Instagram audiences; touring (Pollstar and Billboard Boxscore grosses), merch, brand deals; fan demographics; label ownership map. See the roadmap.</p>
  <h2>Photos</h2><p>Wikimedia Commons, with the author and licence on each artist page. Initials where there is no free photo.</p></section>`;
}

// ---------- router
async function route() {
  if (!store.data) store.data = await (await fetch("data/index.json")).json();
  document.getElementById("crumbs").innerHTML = "";
  const h = location.hash.replace(/^#\/?/, "").split("/");
  if (h[0] === "a") artist(decodeURIComponent(h[1]));
  else if (h[0] === "rising") rising();
  else if (h[0] === "pay") pay();
  else if (h[0] === "platforms") platforms();
  else if (h[0] === "method") method();
  else top();
  document.getElementById("foot").textContent = `Data as of ${store.data.as_of}; built ${store.data.built}. Sources: kworb.net (Spotify public counts), Wikidata, MusicBrainz, Deezer, Wikimedia Commons. Estimates are ranges, not reported figures.`;
  window.scrollTo(0, 0);
}
addEventListener("hashchange", route);
route().catch(e => { app.innerHTML = `<p class="note">Could not load the data: ${esc(e.message)}</p>`; });
