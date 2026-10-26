/* Ads P&L weekly review - static dashboard.
 * Reads ONLY data/*.json exported from the dbt marts (dashboard/export.py).
 * Unfiltered numbers come straight from kpi_weekly. Filtered slices use the additive components in
 * kpi_cube and the SAME formulas as dbt/macros/metric_catalogue.sql (sum the parts, then divide).
 */
"use strict";

// ------------------------------------------------------------------ formulas (mirror metric_catalogue)
const FORMULA = {
  ad_revenue:           { num: "gross_revenue" },
  net_ad_revenue:       { num: "net_revenue" },
  ecpm:                 { num: "gross_revenue", den: "impressions", scale: 1000 },
  ctr:                  { num: "clicks", den: "impressions" },
  fill_rate:            { num: "filled_requests", den: "ad_requests", inventory: true },
  active_advertisers:   { num: "active_advertisers" },
  roas:                 { num: "attributed_gmv", den: "gross_revenue" },
  ad_requests:          { num: "ad_requests", inventory: true },
  impressions:          { num: "impressions" },
  clicks:               { num: "clicks" },
  cpc:                  { num: "cpc_revenue", den: "cpc_clicks" },
  cvr:                  { num: "attributed_orders", den: "clicks" },
  bid_density:          { num: "bidders_sum", den: "ad_requests", inventory: true },
  reserve_binding_rate: { num: "reserve_binding_count", den: "filled_requests", inventory: true },
  top10_concentration:  { num: "top10_revenue", den: "gross_revenue" },
  arpa:                 { num: "gross_revenue", den: "active_advertisers" },
  ad_take_rate:         { num: "gross_revenue", den: "gov", inventory: true },
};
const JD = ["ad_revenue", "ecpm", "ctr", "fill_rate", "active_advertisers", "roas"];
const PRODUCTS = { all: "All products", food_listing: "Food listings", instamart_search: "Instamart products", home_banner: "Home banners" };
const PRODUCT_ORDER = ["food_listing", "instamart_search", "home_banner"];
const SEGMENTS = { all: "All advertisers", chain: "Restaurant chains", independent: "Independent restaurants", brand: "Brands" };

// ------------------------------------------------------------------ data loading
const D = {};
const loading = {};
function need(names) {
  return Promise.all(names.map((n) => {
    if (!loading[n]) {
      loading[n] = fetch(`data/${n}.json`).then((r) => {
        if (!r.ok) throw new Error(`data/${n}.json: ${r.status}`);
        return r.json();
      }).then((j) => {
        if (n === "meta") { D.meta = j; return; }
        D[n] = j.rows.map((row) => Object.fromEntries(j.columns.map((c, i) => [c, row[i]])));
      });
    }
    return loading[n];
  }));
}
const CORE = ["meta", "weeks", "metrics", "kpi_weekly", "kpi_cube", "zones_dim"];

let CUBE = new Map(), KPI = new Map(), MET = {}, WEEKS = [], ZNAME = {};
function indexCore() {
  CUBE = new Map(D.kpi_cube.map((r) => [`${r.week_number}|${r.surface}|${r.zone_id}|${r.advertiser_segment}`, r]));
  KPI = new Map(D.kpi_weekly.map((r) => [`${r.week_number}|${r.product}|${r.metric}`, r]));
  D.metrics.forEach((m) => (MET[m.metric] = m));
  WEEKS = D.weeks.map((w) => w.week_number);
  D.zones_dim.forEach((z) => (ZNAME[z.zone_id] = z.zone_name));
}

// ------------------------------------------------------------------ state (in the hash)
const S = { page: "summary", w: null, p: "all", z: "all", s: "all" };
function readHash() {
  const [path, q] = location.hash.replace(/^#\/?/, "").split("?");
  S.page = ["summary", "drivers", "inventory", "advertisers", "zones"].includes(path) ? path : "summary";
  const p = new URLSearchParams(q || "");
  const last = WEEKS[WEEKS.length - 1];
  const w = parseInt(p.get("w"), 10);
  S.w = WEEKS.includes(w) ? w : last;
  S.p = PRODUCTS[p.get("p")] ? p.get("p") : "all";
  S.z = p.get("z") && (p.get("z") === "all" || ZNAME[p.get("z")]) ? p.get("z") : "all";
  S.s = SEGMENTS[p.get("s")] ? p.get("s") : "all";
}
function writeHash(page = S.page) {
  const p = new URLSearchParams();
  if (S.w !== WEEKS[WEEKS.length - 1]) p.set("w", S.w);
  if (S.p !== "all") p.set("p", S.p);
  if (S.z !== "all") p.set("z", S.z);
  if (S.s !== "all") p.set("s", S.s);
  const qs = p.toString();
  const h = `#/${page}${qs ? "?" + qs : ""}`;
  if (location.hash !== h) location.hash = h; else render();
}
const filtered = () => S.z !== "all" || S.s !== "all";

// ------------------------------------------------------------------ metric access
function cubeRow(w, p = S.p, z = S.z, s = S.s) { return CUBE.get(`${w}|${p}|${z}|${s}`); }
function ratio(f, rows) {
  let n = 0, d = 0, have = false;
  for (const r of rows) {
    if (!r || r[f.num] == null || (f.den && r[f.den] == null)) continue;
    have = true; n += r[f.num]; if (f.den) d += r[f.den];
  }
  if (!have) return null;
  if (f.den) return d ? (n / d) * (f.scale || 1) : null;
  return n * (f.scale || 1);
}
/** value for one week; uses kpi_weekly when unfiltered, cube components otherwise */
function metricAt(metric, w, opt = {}) {
  const p = opt.p ?? S.p, z = opt.z ?? S.z, s = opt.s ?? S.s;
  if (z === "all" && s === "all" && KPI.has(`${w}|${p}|${metric}`)) return KPI.get(`${w}|${p}|${metric}`).value;
  const f = FORMULA[metric]; if (!f) return null;
  if (f.inventory && s !== "all") return null;
  return ratio(f, [cubeRow(w, p, z, s)]);
}
function metricCompare(metric, w) {
  if (!filtered() && KPI.has(`${w}|${S.p}|${metric}`)) {
    const k = KPI.get(`${w}|${S.p}|${metric}`);
    return { value: k.value, prior: k.prior_week_value, wow: k.wow_pct, avg4: k.four_week_avg, vs4: k.vs_4wk_pct };
  }
  const f = FORMULA[metric];
  if (!f || (f.inventory && S.s !== "all")) return { value: null };
  const value = metricAt(metric, w), prior = metricAt(metric, w - 1);
  const prev = [1, 2, 3, 4].map((i) => cubeRow(w - i)).filter(Boolean);
  let avg4 = null;
  if (prev.length) avg4 = f.den ? ratio(f, prev) : ratio(f, prev) / prev.length;
  const rel = (a, b) => (a == null || b == null || b === 0 ? null : (a - b) / Math.abs(b));
  return { value, prior, wow: rel(value, prior), avg4, vs4: rel(value, avg4) };
}
const series = (metric, opt) => WEEKS.map((w) => metricAt(metric, w, opt));

// ------------------------------------------------------------------ formatting
const nf = (d) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });
function inr(v, compact = true) {
  if (v == null || isNaN(v)) return "–";
  const a = Math.abs(v), sgn = v < 0 ? "−" : "";
  if (!compact) return sgn + "₹" + nf(a < 100 ? 2 : 0).format(a);
  if (a >= 1e7) return `${sgn}₹${nf(2).format(a / 1e7)}Cr`;
  if (a >= 1e5) return `${sgn}₹${nf(a >= 1e6 ? 1 : 2).format(a / 1e5)}L`;
  if (a >= 1e3) return `${sgn}₹${nf(1).format(a / 1e3)}K`;
  return `${sgn}₹${nf(a < 100 ? 2 : 0).format(a)}`;
}
function count(v) {
  if (v == null || isNaN(v)) return "–";
  const a = Math.abs(v);
  if (a >= 1e6) return nf(2).format(v / 1e6) + "M";
  if (a >= 1e5) return nf(0).format(v / 1e3) + "K";
  if (a >= 1e4) return nf(1).format(v / 1e3) + "K";
  return nf(0).format(v);
}
const pct = (v, d) => (v == null || isNaN(v) ? "–" : nf(d ?? (Math.abs(v) < 0.1 ? 2 : 1)).format(v * 100) + "%");
// Change label for a metric: rates (unit 'pct') move in percentage points, everything else in relative %.
const delta = (m, cur, base, rel) => {
  if (MET[m]?.unit === "pct" && cur != null && base != null) {
    const pp = (cur - base) * 100;
    return (pp > 0 ? "+" : pp < 0 ? "−" : "±") + nf(Math.abs(pp) < 1 ? 2 : 1).format(Math.abs(pp)) + "\u00a0pp";
  }
  return signedPct(rel);
};
const signedPct = (v) => (v == null || isNaN(v) ? "–" : (v > 0 ? "+" : v < 0 ? "−" : "±") + nf(Math.abs(v) < 0.1 ? 1 : 0).format(Math.abs(v) * 100) + "%");
function fmt(unit, v) {
  if (unit === "inr") return inr(v);
  if (unit === "pct") return pct(v);
  if (unit === "x") return v == null ? "–" : nf(2).format(v) + "×";
  if (unit === "ratio") return v == null ? "–" : nf(1).format(v);
  return count(v);
}
const fmtM = (metric, v) => fmt(MET[metric]?.unit || "count", v);
function tone(metric, delta) {
  if (delta == null || Math.abs(delta) < 0.005) return "neu";
  const g = MET[metric]?.good_direction || "neutral";
  if (g === "neutral") return "neu";
  return (delta > 0) === (g === "up") ? "good" : "bad";
}
const weekLabel = (w) => {
  const r = D.weeks.find((x) => x.week_number === w);
  if (!r) return `Week ${w}`;
  const f = (s) => new Date(s + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  return `Week ${w} (${f(r.week_start)}–${f(r.week_end)})`;
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const prettyCat = (c) => String(c || "").replace(/_/g, " ").replace(/^\w/, (m) => m.toUpperCase());

// ------------------------------------------------------------------ charts (ECharts, themed from CSS vars)
let charts = [];
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function theme() {
  return { ink: css("--ink"), ink2: css("--ink-2"), muted: css("--muted"), hair: css("--hair"), axis: css("--axis"),
    surface: css("--surface"), accent: css("--accent"), s1: css("--s1"), s2: css("--s2"), s3: css("--s3"),
    good: css("--good-mark"), bad: css("--bad-mark"), neutral: css("--neutral"),
    seq: [0, 1, 2, 3, 4, 5, 6].map((i) => css(`--seq-${i}`)) };
}
function base(T) {
  return {
    animation: false,
    textStyle: { fontFamily: css("--font") || "system-ui", color: T.ink2 },
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", backgroundColor: T.surface, borderColor: T.hair, borderWidth: 1, textStyle: { color: T.ink, fontSize: 12.5 },
      axisPointer: { type: "line", lineStyle: { color: T.axis, width: 1 } }, extraCssText: "box-shadow:0 6px 20px rgba(15,25,35,.12);border-radius:8px;" },
  };
}
const legendTop = () => (window.innerWidth < 600 ? 52 : 34);
const xWeeks = (T, extra = {}) => ({ type: "category", data: WEEKS.map((w) => `W${w}`), boundaryGap: false,
  axisLine: { lineStyle: { color: T.axis } }, axisTick: { show: false }, axisLabel: { color: T.muted, fontSize: 11 }, ...extra });
const yVal = (T, fmtFn, extra = {}) => ({ type: "value", scale: true, splitNumber: 4, axisLabel: { color: T.muted, fontSize: 11, formatter: fmtFn },
  splitLine: { lineStyle: { color: T.hair, width: 1 } }, axisLine: { show: false }, ...extra });
function mount(id, option) {
  const el = document.getElementById(id);
  if (!el || !window.echarts) return null;
  const c = echarts.init(el, null, { renderer: "svg" });
  c.setOption(option);
  charts.push(c);
  return c;
}
const selMark = (T) => ({ symbol: "none", silent: true, label: { show: false },
  lineStyle: { color: T.accent, width: 1, type: "solid" }, data: [{ xAxis: `W${S.w}` }] });
/** single-series weekly line, selected week marked */
function weeklyLine(id, data, fmtFn, color, opt = {}) {
  const T = theme();
  return mount(id, { ...base(T),
    xAxis: xWeeks(T), yAxis: yVal(T, fmtFn, opt.y || {}),
    tooltip: { ...base(T).tooltip, valueFormatter: fmtFn },
    series: [{ type: "line", name: opt.name || "", data, showSymbol: false, symbolSize: 8, lineStyle: { width: 2, color: color || T.s1 },
      itemStyle: { color: color || T.s1 }, areaStyle: opt.area === false ? undefined : { color: color || T.s1, opacity: 0.08 },
      markLine: selMark(T), connectNulls: false }],
  });
}

// ------------------------------------------------------------------ html helpers
function panel(id, cls, title, sub, body, opts = {}) {
  return `<section class="panel ${cls}" id="p-${id}">
    <div class="panel-head"><div><h2>${title}</h2>${sub ? `<p class="sub">${sub}</p>` : ""}</div>
    ${opts.table ? `<button class="tv" type="button" aria-pressed="false" data-tv="${id}">Table</button>` : ""}</div>
    <div class="pbody" data-body="${id}">${body}</div>
    ${opts.note ? `<p class="note warn">${opts.note}</p>` : ""}</section>`;
}
const TABLES = {};
function htmlTable(cols, rows, cls = "") {
  return `<div class="tbl-wrap"><table class="${cls}"><thead><tr>${cols.map((c) => `<th class="${c.l ? "l" : ""}">${esc(c.h)}</th>`).join("")}</tr></thead>
  <tbody>${rows.map((r) => `<tr>${r.map((v, i) => `<td class="${cols[i].l ? "l" : ""}${cols[i].cls ? " " + cols[i].cls : ""}">${v}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function wireTableToggles() {
  document.querySelectorAll(".tv").forEach((b) => b.addEventListener("click", () => {
    const id = b.dataset.tv, on = b.getAttribute("aria-pressed") !== "true";
    b.setAttribute("aria-pressed", on);
    const body = document.querySelector(`[data-body="${id}"]`);
    const chartEl = body.querySelector(".chart, .charts");
    let tbl = body.querySelector(".tv-table");
    if (on) {
      if (!tbl && TABLES[id]) { tbl = document.createElement("div"); tbl.className = "tv-table"; tbl.innerHTML = TABLES[id](); body.appendChild(tbl); }
      if (chartEl) chartEl.style.display = "none"; if (tbl) tbl.style.display = "";
    } else {
      if (chartEl) chartEl.style.display = ""; if (tbl) tbl.style.display = "none";
      charts.forEach((c) => c.resize());
    }
  }));
}
function filterNote(unsupported) {
  const active = [];
  if (unsupported.includes("p") && S.p !== "all") active.push("product");
  if (unsupported.includes("z") && S.z !== "all") active.push("zone");
  if (unsupported.includes("s") && S.s !== "all") active.push("advertiser type");
  return active.length ? `Not filterable by ${active.join(" or ")}; showing all.` : "";
}
function scopeLine() {
  const parts = [weekLabel(S.w), PRODUCTS[S.p], S.z === "all" ? "All zones" : ZNAME[S.z], SEGMENTS[S.s]];
  return `<p class="scope">${parts.map(esc).join(" · ")}</p>`;
}
function header(q, answer) {
  return `<header class="ph"><h1>${q}</h1><p class="answer">${answer}</p>${scopeLine()}</header>`;
}

// ------------------------------------------------------------------ page: summary
function pageSummary() {
  const w = S.w;
  const rev = metricCompare("ad_revenue", w);
  const movers = (D.movers || []).filter((m) => m.week_number === w);
  const top = movers[0];
  const ans = rev.value == null ? "No revenue in this slice for the selected week." :
    `${weekLabel(w)}: ad revenue was <b>${inr(rev.value)}</b>, <b class="${tone("ad_revenue", rev.wow)}">${signedPct(rev.wow)}</b> vs last week and ` +
    `<b class="${tone("ad_revenue", rev.vs4)}">${signedPct(rev.vs4)}</b> vs the 4-week average.` +
    (top && !filtered() && S.p === "all" ? ` Biggest mover: <b>${esc(top.metric_label)}</b> at ${fmt(top.unit, top.value)} (${signedPct(top.vs_4wk_pct)} vs 4-wk avg).` : "");

  const cards = JD.map((m) => {
    const c = metricCompare(m, w), lab = MET[m]?.metric_label || m;
    const na = c.value == null;
    return `<article class="card${na ? " na" : ""}">
      <div class="lbl"><span>${esc(lab)}</span><abbr title="${esc(MET[m]?.definition || "")}">ⓘ</abbr></div>
      <div class="val">${na ? "Not available for this filter" : fmtM(m, c.value)}</div>
      ${na ? "" : `<div class="deltas">
        <span class="d"><span class="n ${tone(m, c.wow)}">${delta(m, c.value, c.prior, c.wow)}</span><span class="b">vs last week (${fmtM(m, c.prior)})</span></span>
        <span class="d"><span class="n ${tone(m, c.vs4)}">${delta(m, c.value, c.avg4, c.vs4)}</span><span class="b">vs 4-wk avg (${fmtM(m, c.avg4)})</span></span></div>
        <div class="spark" id="sp-${m}"></div>`}
    </article>`;
  }).join("");

  const moverHtml = movers.length ? `<div class="movers">${movers.map((m) => `
    <div class="mover"><span class="rk">${m.mover_rank}</span>
      <div><div class="mn">${esc(m.metric_label)}</div><div class="mv">${fmt(m.unit, m.value)} vs ${fmt(m.unit, m.four_week_avg)} 4-wk avg</div></div>
      <div class="pct ${tone(m.metric, m.vs_4wk_pct)}">${m.metric === "click_log_gap" ? pct(m.value) : signedPct(m.vs_4wk_pct)}</div></div>`).join("")}</div>`
    : `<p class="note">No movers for the first weeks (needs a 4-week baseline).</p>`;

  const html = header("How did ads do last week?", ans) + `<div class="cards">${cards}</div>
  <div class="grid">
    ${panel("trend", "c8", "Ad revenue, 26 weeks", "Gross billed revenue per week; the vertical line marks the selected week", `<div class="chart" id="ch-trend"></div>`, { table: true })}
    ${panel("movers", "c4", "Biggest movers", "Metrics furthest from their 4-week average this week", moverHtml, { note: filterNote(["p", "z", "s"]) })}
    ${panel("mix", "c12", "Revenue by product", "Weekly gross revenue split by ad product", `<div class="chart" id="ch-mix"></div>`, { table: true })}
  </div>`;
  return { html, after: () => {
    const T = theme();
    JD.forEach((m) => {
      const data = series(m);
      if (!document.getElementById(`sp-${m}`)) return;
      mount(`sp-${m}`, { animation: false, grid: { left: 0, right: 0, top: 4, bottom: 2 }, xAxis: { type: "category", show: false, data: WEEKS },
        yAxis: { type: "value", show: false, scale: true }, tooltip: { show: false },
        series: [{ type: "line", data, showSymbol: false, lineStyle: { width: 1.5, color: T.muted },
          markPoint: { symbol: "circle", symbolSize: 7, itemStyle: { color: T.accent, borderColor: T.surface, borderWidth: 2 }, label: { show: false },
            data: [{ coord: [WEEKS.indexOf(w), data[WEEKS.indexOf(w)]] }] } }] });
    });
    const rv = series("ad_revenue");
    weeklyLine("ch-trend", rv, (v) => inr(v), T.s1, { name: "Ad revenue" });
    TABLES.trend = () => htmlTable([{ h: "Week", l: true }, { h: "Ad revenue" }, { h: "WoW" }],
      WEEKS.map((x, i) => [weekLabel(x), inr(rv[i]), signedPct(i && rv[i - 1] ? rv[i] / rv[i - 1] - 1 : null)]));
    const cols = [T.s1, T.s2, T.s3];
    const mix = PRODUCT_ORDER.map((p) => WEEKS.map((x) => metricAt("ad_revenue", x, { p })));
    mount("ch-mix", { ...base(T), legend: { top: 0, left: 0, icon: "rect", itemWidth: 12, itemHeight: 8, textStyle: { color: T.ink2 } },
      grid: { ...base(T).grid, top: legendTop() }, tooltip: { ...base(T).tooltip, trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => inr(v) },
      xAxis: { ...xWeeks(T), boundaryGap: true }, yAxis: yVal(T, (v) => inr(v), { scale: false }),
      series: PRODUCT_ORDER.map((p, i) => ({ name: PRODUCTS[p], type: "bar", stack: "r", data: mix[i], barMaxWidth: 22,
        itemStyle: { color: cols[i], borderColor: T.surface, borderWidth: 1, opacity: S.p === "all" || S.p === p ? 1 : 0.3 } })) });
    TABLES.mix = () => htmlTable([{ h: "Week", l: true }, ...PRODUCT_ORDER.map((p) => ({ h: PRODUCTS[p] }))],
      WEEKS.map((x, i) => [weekLabel(x), ...mix.map((s) => inr(s[i]))]));
  } };
}

// ------------------------------------------------------------------ page: drivers
function pageDrivers() {
  const w = S.w;
  const br = D.revenue_bridge.find((r) => r.week_number === w && r.surface === S.p);
  const banner = S.p === "home_banner";
  const priceName = banner ? "eCPM" : S.p === "all" ? "Price" : "CPC";
  const eff = br ? [["Ad requests", br.requests_effect], ["Fill rate", br.fill_effect], ["CTR", br.ctr_effect], [priceName, br.price_effect]] : [];
  const big = eff.slice().sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0];
  const ans = !br ? "Week 1 has no prior week to bridge from. Pick a later week." :
    `Revenue moved <b class="${br.revenue_change >= 0 ? "good" : "bad"}">${br.revenue_change >= 0 ? "+" : "−"}${inr(Math.abs(br.revenue_change))}</b> ` +
    `(${signedPct(br.revenue_prior ? br.revenue_change / br.revenue_prior : null)}) from week ${w - 1} to week ${w}. ` +
    `The largest driver was <b>${big[0]}</b>, worth <b class="${big[1] >= 0 ? "good" : "bad"}">${big[1] >= 0 ? "+" : "−"}${inr(Math.abs(big[1]))}</b>.`;
  const k = (m, x) => KPI.get(`${x}|all|${m}`)?.value;   // blended values for the all-products row come from kpi_weekly
  const drvRows = br ? [
    ["Ad requests", count(br.requests_prior), count(br.requests_current), br.requests_effect],
    ["Fill rate", pct(br.fill_prior ?? k("fill_rate", w - 1)), pct(br.fill_current ?? k("fill_rate", w)), br.fill_effect],
    ...(S.p === "all" ? [["CTR (blended)", pct(k("ctr", w - 1)), pct(k("ctr", w)), br.ctr_effect], ["Price (blended CPC)", inr(k("cpc", w - 1), false), inr(k("cpc", w), false), br.price_effect]] :
      banner ? [["CTR", "not billed", "not billed", br.ctr_effect], ["eCPM", inr(br.price_prior), inr(br.price_current), br.price_effect]] :
      [["CTR", pct(br.ctr_prior), pct(br.ctr_current), br.ctr_effect], ["CPC", inr(br.price_prior, false), inr(br.price_current, false), br.price_effect]]),
  ] : [];
  const drvTable = br ? htmlTable([{ h: "Driver", l: true }, { h: `Wk ${w - 1}` }, { h: `Wk ${w}` }, { h: "Effect" }],
    [...drvRows.map((r) => [r[0], r[1], r[2], `<span class="${r[3] >= 0 ? "good" : "bad"}">${r[3] >= 0 ? "+" : "−"}${inr(Math.abs(r[3]))}</span>`]),
     ["<b>Total change</b>", inr(br.revenue_prior), inr(br.revenue_current), `<b>${br.revenue_change >= 0 ? "+" : "−"}${inr(Math.abs(br.revenue_change))}</b>`]]) : "";
  const posProduct = S.p === "all" ? "food_listing" : S.p;

  const html = header("Why did revenue change?", ans) + `<div class="grid">
    ${panel("bridge", "c7", "Revenue bridge", `Week ${w - 1} → week ${w}: revenue = requests × fill rate × CTR × ${banner ? "revenue per impression" : "CPC"}`, `<div class="chart tall" id="ch-bridge"></div>`, { table: true, note: filterNote(["z", "s"]) })}
    ${panel("drivers", "c5", "Driver values", "Each effect holds the drivers to its left at this week's level, so the effects add up exactly", drvTable || `<p class="note">No prior week.</p>`, { note: filterNote(["z", "s"]) })}
    ${panel("dtrend", "c12", "Driver trends", "The four terms of the revenue identity for the filtered slice", `<div class="charts grid">
      <div class="c6"><div class="sub">Ad requests</div><div class="chart short" id="ch-d1"></div></div>
      <div class="c6"><div class="sub">Fill rate</div><div class="chart short" id="ch-d2"></div></div>
      <div class="c6"><div class="sub">CTR</div><div class="chart short" id="ch-d3"></div></div>
      <div class="c6"><div class="sub">${banner ? "eCPM" : "CPC"}</div><div class="chart short" id="ch-d4"></div></div></div>`,
      { note: S.s !== "all" ? "Ad requests and fill rate are inventory metrics and are not split by advertiser type." : "" })}
    ${panel("pos", "c6", "CTR by position and platform", `${PRODUCTS[posProduct]}, week ${w}`, `<div class="chart" id="ch-pos"></div>`, { table: true, note: [S.p === "all" ? "Showing food listings (pick a product to change)." : "", filterNote(["z", "s"])].filter(Boolean).join(" ") })}
    ${panel("p1", "c6", "Position 1 CTR by platform, 26 weeks", PRODUCTS[posProduct], `<div class="chart" id="ch-p1"></div>`, { table: true, note: filterNote(["z", "s"]) })}
  </div>`;
  return { html, after: () => {
    const T = theme();
    if (br) {
      const labels = [`Week ${w - 1}`, ...eff.map((e) => e[0]), `Week ${w}`];
      // floating bars: an invisible base + a visible delta, stacked on absolute values
      let run = br.revenue_prior;
      const ghost = [0], vis = [{ value: br.revenue_prior, itemStyle: { color: T.s1 } }];
      eff.forEach(([, v]) => { ghost.push(v >= 0 ? run : run + v); vis.push({ value: Math.abs(v), raw: v, itemStyle: { color: v >= 0 ? T.good : T.bad } }); run += v; });
      ghost.push(0); vis.push({ value: br.revenue_current, itemStyle: { color: T.s1 } });
      const lows = [br.revenue_prior, br.revenue_current, ...ghost.slice(1, -1)];
      const highs = [br.revenue_prior, br.revenue_current, ...ghost.slice(1, -1).map((g, i) => g + vis[i + 1].value)];
      const span = Math.max(...highs) - Math.min(...lows);
      const rawLo = Math.max(0, Math.min(...lows) - span * 0.6);
      const mag = Math.pow(10, Math.floor(Math.log10(Math.max(span, 1))));
      const lo = Math.floor(rawLo / mag) * mag;
      mount("ch-bridge", { ...base(T), grid: { ...base(T).grid, bottom: 22 }, tooltip: { ...base(T).tooltip, trigger: "item",
          formatter: (p) => p.seriesIndex === 1 ? `${esc(p.name)}<br><b>${p.data.raw != null ? (p.data.raw >= 0 ? "+" : "−") + inr(Math.abs(p.data.raw)) : inr(p.value)}</b>` : "" },
        xAxis: { type: "category", data: labels, axisLine: { lineStyle: { color: T.axis } }, axisTick: { show: false }, axisLabel: { color: T.ink2, fontSize: 11.5, interval: 0, width: 62, overflow: "break", lineHeight: 14 } },
        yAxis: yVal(T, (v) => inr(v), { min: lo, scale: false, splitNumber: 3, axisLabel: { color: T.muted, fontSize: 11, formatter: (v) => inr(v), showMinLabel: false } }),
        series: [{ type: "bar", stack: "w", data: ghost.map((g, i) => (i === 0 || i === ghost.length - 1 ? 0 : g)), itemStyle: { color: "transparent" }, silent: true, barMaxWidth: 28 },
          { type: "bar", stack: "w", data: vis, barMaxWidth: 28, itemStyle: { borderRadius: 4 },
            labelLayout: { hideOverlap: true },
            label: { show: true, position: "top", color: T.ink2, fontSize: window.innerWidth < 600 ? 10 : 11, formatter: (p) => p.data.raw != null ? (p.data.raw >= 0 ? "+" : "−") + inr(Math.abs(p.data.raw)) : inr(p.value) } }] });
      TABLES.bridge = () => drvTable;
    }
    const banner_ = S.p === "home_banner";
    weeklyLine("ch-d1", series("ad_requests"), count, T.s1);
    weeklyLine("ch-d2", series("fill_rate"), (v) => pct(v), T.s1);
    weeklyLine("ch-d3", banner_ ? WEEKS.map(() => null) : series("ctr"), (v) => pct(v), T.s1);
    weeklyLine("ch-d4", series(banner_ ? "ecpm" : "cpc"), (v) => inr(v, false), T.s1);
    // position x platform
    const pw = D.platform_weekly.filter((r) => r.surface === posProduct);
    const positions = [...new Set(pw.map((r) => r.slot_position))].sort((a, b) => a - b);
    const ctrOf = (rows) => { const i = rows.reduce((a, r) => a + r.impressions, 0); return i ? rows.reduce((a, r) => a + r.clicks, 0) / i : null; };
    const plat = ["android", "ios"], pc = [T.s1, T.s2];
    const cur = plat.map((pl) => positions.map((pos) => ctrOf(pw.filter((r) => r.week_number === w && r.platform === pl && r.slot_position === pos))));
    mount("ch-pos", { ...base(T), legend: { top: 0, left: 0, icon: "rect", itemWidth: 12, itemHeight: 8, textStyle: { color: T.ink2 } }, grid: { ...base(T).grid, top: legendTop() },
      tooltip: { ...base(T).tooltip, axisPointer: { type: "shadow" }, valueFormatter: (v) => pct(v) },
      xAxis: { type: "category", data: positions.map((p) => `Position ${p}`), axisLine: { lineStyle: { color: T.axis } }, axisTick: { show: false }, axisLabel: { color: T.muted } },
      yAxis: yVal(T, (v) => pct(v), { scale: false }),
      series: plat.map((pl, i) => ({ name: pl === "ios" ? "iOS" : "Android", type: "bar", data: cur[i], barMaxWidth: 22, barGap: "15%", itemStyle: { color: pc[i], borderRadius: [4, 4, 0, 0] } })) });
    TABLES.pos = () => htmlTable([{ h: "Position", l: true }, { h: "Android CTR" }, { h: "iOS CTR" }], positions.map((p, i) => [`Position ${p}`, pct(cur[0][i]), pct(cur[1][i])]));
    const p1 = plat.map((pl) => WEEKS.map((x) => ctrOf(pw.filter((r) => r.week_number === x && r.platform === pl && r.slot_position === 1))));
    mount("ch-p1", { ...base(T), legend: { top: 0, left: 0, icon: "roundRect", itemWidth: 14, itemHeight: 3, textStyle: { color: T.ink2 } }, grid: { ...base(T).grid, top: legendTop() },
      tooltip: { ...base(T).tooltip, valueFormatter: (v) => pct(v) }, xAxis: xWeeks(T), yAxis: yVal(T, (v) => pct(v)),
      series: plat.map((pl, i) => ({ name: pl === "ios" ? "iOS" : "Android", type: "line", data: p1[i], showSymbol: false, lineStyle: { width: 2, color: pc[i] }, itemStyle: { color: pc[i] },
        markLine: i === 0 ? selMark(T) : undefined })) });
    TABLES.p1 = () => htmlTable([{ h: "Week", l: true }, { h: "Android" }, { h: "iOS" }], WEEKS.map((x, i) => [weekLabel(x), pct(p1[0][i]), pct(p1[1][i])]));
  } };
}

// ------------------------------------------------------------------ page: inventory
function pageInventory() {
  const w = S.w;
  const fr = metricCompare("fill_rate", w), bd = metricCompare("bid_density", w), rb = metricCompare("reserve_binding_rate", w);
  const ans = fr.value == null ? "Inventory metrics are not split by advertiser type: clear that filter to see fill and auction health." :
    `Fill rate was <b>${pct(fr.value)}</b> (<span class="${tone("fill_rate", fr.wow)}">${signedPct(fr.wow)}</span> WoW) with <b>${fmtM("bid_density", bd.value)}</b> eligible bidders per auction. ` +
    `The reserve price set the price in <b>${pct(rb.value)}</b> of filled auctions (<span class="${tone("reserve_binding_rate", rb.vs4)}">${signedPct(rb.vs4)}</span> vs 4-wk avg).`;
  const up = D.unfilled_premium.filter((r) => r.week_number === w && (S.z === "all" || r.zone_id === S.z) && (S.p === "all" || r.surface === S.p)).slice(0, 12);
  const upTable = up.length ? htmlTable([{ h: "Zone", l: true }, { h: "Slot", l: true }, { h: "Hour", l: true }, { h: "Unfilled" }, { h: "Fill rate" }],
    up.map((r) => [esc(ZNAME[r.zone_id]), r.surface === "home_banner" ? "Home banner" : "Food listing", `${String(r.event_hour).padStart(2, "0")}:00`, count(r.unfilled_requests), pct(r.fill_rate)]))
    : `<p class="note">No unfilled premium (lunch/dinner) food or banner slots for this filter.</p>`;
  const inv = D.inventory_surface.filter((r) => r.week_number === w && (S.p === "all" || r.surface === S.p));
  const invTable = htmlTable([{ h: "Slot / category", l: true }, { h: "Requests" }, { h: "Fill rate" }, { h: "Bid density" }, { h: "Reserve-binding" }, { h: "Avg price" }],
    inv.map((r) => [r.surface === "instamart_search" ? `Instamart · ${prettyCat(r.request_category)}` : PRODUCTS[r.surface], count(r.ad_requests), pct(r.fill_rate),
      nf(1).format(r.bid_density), pct(r.reserve_binding_rate), r.surface === "home_banner" ? inr(r.avg_clearing_price) + " CPM" : inr(r.avg_clearing_price, false)]));
  const distProduct = S.p === "all" ? "food_listing" : S.p;
  const html = header("Are we selling our slots well?", ans) + `<div class="grid">
    ${panel("heat", "c12", "Fill rate by zone and hour", `Week ${w}, all slots. Colour follows the scale below: stronger blue = more of the inventory sold`, `<div class="chart tall" id="ch-heat"></div>`, { table: true, note: filterNote(["p", "s"]) })}
    ${panel("bid", "c6", "Bid density", "Average eligible bidders per auction", `<div class="chart short" id="ch-bid"></div>`)}
    ${panel("res", "c6", "Reserve-binding rate", "Share of filled auctions priced by the reserve", `<div class="chart short" id="ch-res"></div>`)}
    ${panel("dist", "c6", "Clearing price distribution", `${PRODUCTS[distProduct]}, week ${w}: filled auctions by clearing price`, `<div class="chart" id="ch-dist"></div>`, { table: true, note: [S.p === "all" ? "Showing food listings (pick a product to change)." : "", filterNote(["z", "s"])].filter(Boolean).join(" ") })}
    ${panel("unf", "c6", "Unfilled premium slots", "Lunch and dinner hours (12–2 pm, 7–10 pm) with the most unsold food or banner requests", upTable, { note: filterNote(["s"]) })}
    ${panel("inv", "c12", "Inventory by slot and Instamart category", `Week ${w}`, invTable, { note: filterNote(["z", "s"]) })}
  </div>`;
  return { html, after: () => {
    const T = theme();
    const hm = D.fill_heatmap.filter((r) => r.week_number === w);
    const zones = D.zones_dim.map((z) => z.zone_id);
    const data = hm.map((r) => [r.event_hour, zones.indexOf(r.zone_id), r.fill_rate]);
    mount("ch-heat", { ...base(T), grid: { left: 8, right: 12, top: 8, bottom: 46, containLabel: true },
      tooltip: { ...base(T).tooltip, trigger: "item", formatter: (p) => `${esc(ZNAME[zones[p.value[1]]])}, ${String(p.value[0]).padStart(2, "0")}:00<br><b>${pct(p.value[2])}</b> filled` },
      xAxis: { type: "category", data: [...Array(24).keys()].map((h) => String(h).padStart(2, "0")), splitArea: { show: false }, axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: T.muted, fontSize: 10.5 } },
      yAxis: { type: "category", inverse: true, data: zones.map((z) => ZNAME[z]), axisTick: { show: false }, axisLine: { show: false },
        axisLabel: { fontSize: 11, color: (v) => (S.z !== "all" && v === ZNAME[S.z] ? T.accent : T.ink2), fontWeight: (v) => (S.z !== "all" && v === ZNAME[S.z] ? 700 : 400) } },
      visualMap: { min: 0, max: 1, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemWidth: 10, itemHeight: 160, text: ["100%", "0%"], textStyle: { color: T.muted, fontSize: 11 },
        inRange: { color: T.seq.slice(0, 7) } },
      series: [{ type: "heatmap", data, itemStyle: { borderColor: T.surface, borderWidth: 2, borderRadius: 3 }, emphasis: { itemStyle: { borderColor: T.accent, borderWidth: 2 } } }] });
    TABLES.heat = () => htmlTable([{ h: "Zone", l: true }, ...[...Array(24).keys()].map((h) => ({ h: String(h).padStart(2, "0") }))],
      zones.map((z) => [esc(ZNAME[z]), ...[...Array(24).keys()].map((h) => { const r = hm.find((x) => x.zone_id === z && x.event_hour === h); return r ? nf(0).format(r.fill_rate * 100) : "–"; })]));
    weeklyLine("ch-bid", series("bid_density"), (v) => nf(1).format(v), T.s1);
    weeklyLine("ch-res", series("reserve_binding_rate"), (v) => pct(v), T.s1);
    const ds = D.clearing_price_dist.filter((r) => r.week_number === w && r.surface === distProduct);
    const step = distProduct === "home_banner" ? 10 : 1;
    const bins = new Map();
    ds.forEach((r) => { const b = Math.floor(r.price_bucket / step) * step; bins.set(b, (bins.get(b) || 0) + r.filled_requests); });
    const keys = [...bins.keys()].sort((a, b) => a - b);
    mount("ch-dist", { ...base(T), tooltip: { ...base(T).tooltip, axisPointer: { type: "shadow" }, valueFormatter: count },
      xAxis: { type: "category", data: keys.map((k) => `₹${k}`), axisLine: { lineStyle: { color: T.axis } }, axisTick: { show: false }, axisLabel: { color: T.muted, fontSize: 11 } },
      yAxis: yVal(T, count, { scale: false }), series: [{ type: "bar", data: keys.map((k) => bins.get(k)), barMaxWidth: 22, barCategoryGap: "12%", itemStyle: { color: T.s1, borderRadius: [4, 4, 0, 0] } }] });
    TABLES.dist = () => htmlTable([{ h: distProduct === "home_banner" ? "CPM bucket" : "CPC bucket", l: true }, { h: "Filled auctions" }], keys.map((k) => [`₹${k}–${k + step}`, count(bins.get(k))]));
  } };
}

// ------------------------------------------------------------------ page: advertisers
function pageAdvertisers() {
  const w = S.w;
  const act = metricCompare("active_advertisers", w), conc = metricCompare("top10_concentration", w);
  const sm = D.advertiser_weekly_summary.find((r) => r.week_number === w) || {};
  const ans = `<b>${count(act.value)}</b> advertisers spent in week ${w} (<span class="${tone("active_advertisers", act.wow)}">${signedPct(act.wow)}</span> WoW). ` +
    `${count(sm.new)} were new and ${sm.churn_provisional ? "churn for this week is still provisional" : `${count(sm.churned)} churned`}. ` +
    `The top 10 accounts took <b>${pct(conc.value)}</b> of revenue.`;
  const segOk = (seg) => S.s === "all" || seg === S.s;
  const top = D.top_advertisers.filter((r) => r.week_number === w && segOk(r.advertiser_segment)).slice(0, 15);
  const topTable = htmlTable([{ h: "#", l: true }, { h: "Advertiser", l: true, cls: "name" }, { h: "Type", l: true }, { h: "Spend" }, { h: "WoW" }, { h: "Budget used", l: true }, { h: "ROAS" }],
    top.map((r) => [r.spend_rank, esc(r.advertiser_name), `<span class="tag">${{ chain: "Chain", independent: "Independent", brand: "Brand" }[r.advertiser_segment] || ""}</span>`,
      r.is_active ? inr(r.gross_spend) : `<span class="bad">No spend</span>`,
      `<span class="${r.spend_wow_pct == null ? "neu" : r.spend_wow_pct >= 0 ? "good" : "bad"}">${signedPct(r.spend_wow_pct)}</span>`,
      r.budget_utilisation == null ? "–" : `<span class="meter"><i style="width:${Math.min(100, r.budget_utilisation * 100).toFixed(0)}%"></i></span>${pct(r.budget_utilisation, 0)}`,
      r.roas == null ? "–" : nf(2).format(r.roas) + "×"]));
  // cohort triangle
  const co = D.cohorts;
  const maxK = Math.max(...co.map((r) => r.weeks_since_first));
  const cohorts = [...new Set(co.map((r) => r.cohort_week))].sort((a, b) => a - b);
  const T0 = theme();
  const shade = (v) => { if (v == null) return ""; const i = Math.min(6, Math.floor(v * 7)); return `background:${T0.seq[i]};color:${i >= 4 ? "#fff" : "inherit"}`; };
  const coHtml = `<div class="tbl-wrap"><table class="cohort"><thead><tr><th class="l">First week</th><th>Size</th>${[...Array(Math.min(maxK, 12) + 1).keys()].map((k) => `<th>+${k}</th>`).join("")}</tr></thead><tbody>
    ${cohorts.map((c) => { const size = co.find((r) => r.cohort_week === c)?.cohort_size;
      return `<tr><td class="c0">${c === 1 ? "W1 (existing base)" : "W" + c}</td><td>${count(size)}</td>${[...Array(Math.min(maxK, 12) + 1).keys()].map((k) => {
        const r = co.find((x) => x.cohort_week === c && x.weeks_since_first === k); return `<td style="${shade(r?.retention)}">${r ? nf(0).format(r.retention * 100) : ""}</td>`; }).join("")}</tr>`; }).join("")}
    </tbody></table></div>`;
  const catType = S.s === "brand" || S.p === "instamart_search" || S.p === "home_banner" ? "brand" : S.s === "all" && S.p === "all" ? null : "restaurant";
  const html = header("Who is growing, who is leaving?", ans) + `<div class="grid">
    ${panel("act", "c6", "Active advertisers", "Distinct advertisers with spend in the week", `<div class="chart short" id="ch-act"></div>`, { table: true })}
    ${panel("newch", "c6", "New and churned advertisers", "Churn = active last week, then inactive 4 straight weeks; the last 3 weeks are provisional. Week 1 is the existing base, so it has no new count", `<div class="chart short" id="ch-newch"></div>`, { table: true, note: filterNote(["p", "z", "s"]) })}
    ${panel("conc", "c6", "Top-10 concentration", "Share of revenue from the 10 largest advertisers", `<div class="chart short" id="ch-conc"></div>`)}
    ${panel("roascat", "c6", "ROAS by category", `Week ${w}${catType ? ", " + (catType === "brand" ? "brands" : "restaurants") : ""}`, `<div class="chart" id="ch-roascat"></div>`, { table: true,
      note: [S.s === "chain" || S.s === "independent" ? "Category view splits restaurants vs brands, not chains vs independents." : "", filterNote(["z"])].filter(Boolean).join(" ") })}
    ${panel("top", "c12", "Top accounts this week", "Largest spenders, plus last week's top accounts that stopped spending", topTable, { note: filterNote(["p", "z"]) })}
    ${panel("cohort", "c12", "Weekly cohort retention", "Share of each first-spend cohort still spending N weeks later (%)", coHtml, { note: filterNote(["p", "z", "s"]) })}
  </div>`;
  return { html, after: () => {
    const T = theme();
    const av = series("active_advertisers");
    weeklyLine("ch-act", av, count, T.s1);
    TABLES.act = () => htmlTable([{ h: "Week", l: true }, { h: "Active" }], WEEKS.map((x, i) => [weekLabel(x), count(av[i])]));
    const sm2 = D.advertiser_weekly_summary;
    mount("ch-newch", { ...base(T), legend: { top: 0, left: 0, icon: "rect", itemWidth: 12, itemHeight: 8, textStyle: { color: T.ink2 } }, grid: { ...base(T).grid, top: legendTop() },
      tooltip: { ...base(T).tooltip, axisPointer: { type: "shadow" }, formatter: (ps) => `${ps[0].axisValue}<br>` + ps.map((p) => `${p.marker}${esc(p.seriesName)}: <b>${p.value == null ? "provisional" : count(p.value)}</b>`).join("<br>") },
      xAxis: { ...xWeeks(T), boundaryGap: true }, yAxis: yVal(T, count, { scale: false }),
      series: [{ name: "New", type: "bar", data: sm2.map((r) => (r.week_number === 1 ? null : r.new)), barMaxWidth: 14, itemStyle: { color: T.s1, borderRadius: [4, 4, 0, 0] }, markLine: selMark(T) },
        { name: "Churned", type: "bar", data: sm2.map((r) => (r.churn_provisional ? null : r.churned)), barMaxWidth: 14, itemStyle: { color: T.s2, borderRadius: [4, 4, 0, 0] } }] });
    TABLES.newch = () => htmlTable([{ h: "Week", l: true }, { h: "Active" }, { h: "New" }, { h: "Churned" }],
      sm2.map((r) => [weekLabel(r.week_number), count(r.active), r.week_number === 1 ? "existing base" : count(r.new), r.churn_provisional ? "provisional" : count(r.churned)]));
    weeklyLine("ch-conc", series("top10_concentration"), (v) => pct(v), T.s1);
    const cats = D.categories.filter((r) => r.week_number === w && (!catType || r.advertiser_type === catType) && r.gross_revenue > 0).sort((a, b) => a.roas - b.roas);
    mount("ch-roascat", { ...base(T), grid: { left: 8, right: 40, top: 6, bottom: 6, containLabel: true },
      tooltip: { ...base(T).tooltip, trigger: "item", formatter: (p) => `${esc(p.name)}<br><b>${nf(2).format(p.value)}×</b> ROAS · ${inr(cats[p.dataIndex].gross_revenue)} spend` },
      xAxis: { type: "value", splitLine: { lineStyle: { color: T.hair } }, axisLabel: { color: T.muted, formatter: (v) => v + "×" } },
      yAxis: { type: "category", data: cats.map((c) => (catType ? "" : c.advertiser_type === "brand" ? "Brand · " : "Food · ") + prettyCat(c.category)), axisTick: { show: false }, axisLine: { lineStyle: { color: T.axis } }, axisLabel: { color: T.ink2, fontSize: 11 } },
      series: [{ type: "bar", data: cats.map((c) => c.roas), barMaxWidth: 12, itemStyle: { color: T.s1, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: "right", color: T.ink2, fontSize: 10.5, formatter: (p) => nf(1).format(p.value) + "×" } }] });
    document.getElementById("ch-roascat").style.height = Math.max(260, cats.length * 20 + 30) + "px"; charts[charts.length - 1].resize();
    TABLES.roascat = () => htmlTable([{ h: "Category", l: true }, { h: "Type", l: true }, { h: "Spend" }, { h: "CTR" }, { h: "ROAS" }],
      cats.slice().reverse().map((c) => [prettyCat(c.category), c.advertiser_type, inr(c.gross_revenue), pct(c.ctr), nf(2).format(c.roas) + "×"]));
  } };
}

// ------------------------------------------------------------------ page: zones & categories
function pageZones() {
  const w = S.w;
  const rows = D.zones_dim.map((z) => {
    const c = cubeRow(w, S.p, z.zone_id, S.s);
    const prev = [1, 2, 3, 4].map((i) => cubeRow(w - i, S.p, z.zone_id, S.s)).filter(Boolean);
    const avg = prev.length ? prev.reduce((a, r) => a + (r.gross_revenue || 0), 0) / prev.length : null;
    return { ...z, rev: c?.gross_revenue ?? 0, ctr: c ? ratio(FORMULA.ctr, [c]) : null, roas: c ? ratio(FORMULA.roas, [c]) : null,
      fill: c && S.s === "all" ? ratio(FORMULA.fill_rate, [c]) : null, vs4: avg ? ((c?.gross_revenue ?? 0) - avg) / avg : null };
  });
  const byRev = rows.slice().sort((a, b) => b.rev - a.rev);
  const withRoas = rows.filter((r) => r.roas != null && r.rev > 0).sort((a, b) => a.roas - b.roas);
  const ans = `<b>${esc(byRev[0].zone_name)}</b> brought in the most ad revenue (${inr(byRev[0].rev)}). ` +
    (withRoas.length ? `ROAS is weakest in <b>${esc(withRoas[0].zone_name)}</b> (${nf(2).format(withRoas[0].roas)}×) and strongest in <b>${esc(withRoas[withRoas.length - 1].zone_name)}</b> (${nf(2).format(withRoas[withRoas.length - 1].roas)}×).` : "");
  const zt = htmlTable([{ h: "Zone", l: true }, { h: "Revenue" }, { h: "vs 4-wk" }, { h: "CTR" }, { h: "ROAS" }, { h: "Fill" }],
    byRev.map((r) => [`${S.z === r.zone_id ? "<b>" : ""}${esc(r.zone_name)}${S.z === r.zone_id ? "</b>" : ""}`, inr(r.rev),
      `<span class="${r.vs4 == null ? "neu" : r.vs4 >= 0 ? "good" : "bad"}">${signedPct(r.vs4)}</span>`, pct(r.ctr), r.roas == null ? "–" : nf(2).format(r.roas) + "×", pct(r.fill)]));
  const catType = S.s === "brand" || S.p === "instamart_search" || S.p === "home_banner" ? "brand" : S.s === "all" && S.p === "all" ? null : "restaurant";
  const cats = D.categories.filter((r) => r.week_number === w && (!catType || r.advertiser_type === catType) && r.gross_revenue > 0);
  const ct = htmlTable([{ h: "Category", l: true }, { h: "Spend" }, { h: "vs 4-wk" }, { h: "CTR" }, { h: "ROAS" }],
    cats.slice().sort((a, b) => b.gross_revenue - a.gross_revenue).map((c) => [`${prettyCat(c.category)} <span class="tag">${c.advertiser_type === "brand" ? "Brand" : "Food"}</span>`, inr(c.gross_revenue),
      `<span class="${c.spend_vs_4wk_pct == null ? "neu" : c.spend_vs_4wk_pct >= 0 ? "good" : "bad"}">${signedPct(c.spend_vs_4wk_pct)}</span>`, pct(c.ctr), nf(2).format(c.roas) + "×"]));
  const html = header("Where should sales focus?", ans) + `<div class="grid">
    ${panel("map", "c6", "Revenue and ROAS by zone", "Bubble size = ad revenue; colour = ROAS on the scale below. Positions are zone centroids in Bengaluru", `<div class="chart tall" id="ch-map"></div>`)}
    ${panel("zt", "c6", "Zones", `Week ${w}`, zt)}
    ${panel("quad", "c6", "Grow or fix", "Each dot is a category. Top left: strong ROAS but spend falling, so sales should grow it. Bottom right: spend rising on weak ROAS, so fix targeting or bids. Dot size = spend", `<div class="chart tall" id="ch-quad"></div>`, { table: true, note: [S.s === "chain" || S.s === "independent" ? "Categories split restaurants vs brands, not chains vs independents." : "", filterNote(["z"])].filter(Boolean).join(" ") })}
    ${panel("ct", "c6", "Categories", `Week ${w}`, ct, { note: filterNote(["z"]) })}
  </div>`;
  return { html, after: () => {
    const T = theme();
    const maxRev = Math.max(...rows.map((r) => r.rev), 1);
    const rv = rows.filter((r) => r.roas != null).map((r) => r.roas);
    const lons = rows.map((r) => r.lon), lats = rows.map((r) => r.lat);
    const padX = (Math.max(...lons) - Math.min(...lons)) * 0.12, padY = (Math.max(...lats) - Math.min(...lats)) * 0.08;
    mount("ch-map", { ...base(T), grid: { left: 10, right: 60, top: 10, bottom: 44, containLabel: false },
      tooltip: { ...base(T).tooltip, trigger: "item", formatter: (p) => `${esc(p.data.name)}<br><b>${inr(p.data.rev)}</b> revenue<br>ROAS ${p.data.roas == null ? "–" : nf(2).format(p.data.roas) + "×"} · CTR ${pct(p.data.ctr)}` },
      xAxis: { type: "value", min: Math.min(...lons) - padX, max: Math.max(...lons) + padX, show: false },
      yAxis: { type: "value", min: Math.min(...lats) - padY, max: Math.max(...lats) + padY, show: false },
      visualMap: { dimension: 2, min: Math.min(...rv), max: Math.max(...rv), orient: "horizontal", left: "center", bottom: 0, itemWidth: 10, itemHeight: 140, calculable: false,
        text: ["High ROAS", "Low"], textStyle: { color: T.muted, fontSize: 11 }, inRange: { color: T.seq.slice(2, 7) } },
      series: [{ type: "scatter", data: rows.map((r) => ({ name: r.zone_name, value: [r.lon, r.lat, r.roas ?? 0], rev: r.rev, roas: r.roas, ctr: r.ctr,
          symbolSize: 8 + 26 * Math.sqrt(r.rev / maxRev),
          itemStyle: { borderColor: S.z === r.zone_id ? T.accent : T.surface, borderWidth: S.z === r.zone_id ? 3 : 2 } })),
        labelLayout: { hideOverlap: true }, emphasis: { label: { show: true, fontWeight: 600 } },
        label: { show: true, position: "right", distance: 4, color: T.ink2, fontSize: 10.5, formatter: (p) => p.data.name } }] });
    const med = cats.map((c) => c.roas).sort((a, b) => a - b)[Math.floor(cats.length / 2)] || 0;
    const maxS = Math.max(...cats.map((c) => c.gross_revenue), 1);
    const grp = [["restaurant", "Restaurants", T.s1], ["brand", "Brands", T.s2]].filter(([k]) => !catType || k === catType);
    mount("ch-quad", { ...base(T), legend: grp.length > 1 ? { top: 0, left: 0, textStyle: { color: T.ink2 } } : undefined, grid: { ...base(T).grid, top: grp.length > 1 ? 34 : 16, right: 64 },
      tooltip: { ...base(T).tooltip, trigger: "item", formatter: (p) => `${esc(prettyCat(p.data.cat))}<br>ROAS <b>${nf(2).format(p.value[1])}×</b><br>Spend ${inr(p.data.spend)} (${signedPct(p.value[0])} vs 4-wk)` },
      xAxis: { type: "value", name: "Spend vs 4-wk avg", nameLocation: "middle", nameGap: 28, nameTextStyle: { color: T.muted }, axisLabel: { color: T.muted, formatter: (v) => signedPct(v) }, splitLine: { lineStyle: { color: T.hair } } },
      yAxis: { type: "value", scale: true, axisLabel: { color: T.muted, formatter: (v) => v + "×" }, splitLine: { lineStyle: { color: T.hair } } },
      series: grp.map(([k, name, col], i) => ({ name, type: "scatter",
        data: cats.filter((c) => c.advertiser_type === k && c.spend_vs_4wk_pct != null).map((c) => ({ value: [c.spend_vs_4wk_pct, c.roas], cat: c.category, spend: c.gross_revenue,
          symbolSize: 8 + 26 * Math.sqrt(c.gross_revenue / maxS) })),
        itemStyle: { color: col, opacity: 0.85, borderColor: T.surface, borderWidth: 2 },
        labelLayout: { hideOverlap: true },
        label: { show: true, position: "right", distance: 3, color: T.ink2, fontSize: 10.5,
          formatter: (p) => ((p.value[0] < 0 && p.value[1] >= med) || (p.value[0] > 0 && p.value[1] < med) || p.data.spend > maxS * 0.45 ? prettyCat(p.data.cat) : "") },
        markLine: i === 0 ? { silent: true, symbol: "none", lineStyle: { color: T.axis, width: 1, type: "solid" }, label: { show: false },
          data: [{ xAxis: 0 }, { yAxis: med }] } : undefined })) });
    TABLES.quad = () => ct;
  } };
}

// ------------------------------------------------------------------ router / render
const PAGES = { summary: [pageSummary, ["movers"]], drivers: [pageDrivers, ["revenue_bridge", "platform_weekly"]],
  inventory: [pageInventory, ["fill_heatmap", "inventory_surface", "unfilled_premium", "clearing_price_dist"]],
  advertisers: [pageAdvertisers, ["advertiser_weekly_summary", "cohorts", "top_advertisers", "categories"]],
  zones: [pageZones, ["categories"]] };

let renderSeq = 0;
async function render() {
  readHash();
  const seq = ++renderSeq;
  const pageEl = document.getElementById("page");
  pageEl.classList.add("busy");
  document.querySelectorAll("#nav a").forEach((a) => a.setAttribute("aria-current", a.dataset.page === S.page ? "page" : "false"));
  document.querySelectorAll("#nav a").forEach((a) => (a.href = location.hash.replace(/^#\/\w+/, `#/${a.dataset.page}`) || `#/${a.dataset.page}`));
  syncFilters();
  const [fn, files] = PAGES[S.page];
  try { await need(files); } catch (e) { pageEl.innerHTML = `<p class="note">Could not load data: ${esc(e.message)}. Reload the page to try again.</p>`; return; }
  if (seq !== renderSeq) return;
  charts.forEach((c) => c.dispose()); charts = [];
  Object.keys(TABLES).forEach((k) => delete TABLES[k]);
  const { html, after } = fn();
  pageEl.innerHTML = html;
  pageEl.classList.remove("busy");
  after && after();
  wireTableToggles();
  document.title = `${document.querySelector(".ph h1")?.textContent || "Ads P&L"} · Ads P&L Weekly Review`;
}
function syncFilters() {
  const set = (id, v) => { const el = document.getElementById(id); el.value = String(v); el.classList.toggle("active", String(v) !== "all" && !(id === "f-week" && v === WEEKS[WEEKS.length - 1])); };
  set("f-week", S.w); set("f-product", S.p); set("f-zone", S.z); set("f-segment", S.s);
}
function initFilters() {
  const wk = document.getElementById("f-week");
  wk.innerHTML = D.weeks.slice().reverse().map((w) => `<option value="${w.week_number}">${esc(weekLabel(w.week_number))}</option>`).join("");
  const z = document.getElementById("f-zone");
  D.zones_dim.slice().sort((a, b) => a.zone_name.localeCompare(b.zone_name)).forEach((r) => { const o = document.createElement("option"); o.value = r.zone_id; o.textContent = r.zone_name; z.appendChild(o); });
  const on = (id, k, parse = (v) => v) => document.getElementById(id).addEventListener("change", (e) => { S[k] = parse(e.target.value); writeHash(); });
  on("f-week", "w", (v) => parseInt(v, 10)); on("f-product", "p"); on("f-zone", "z"); on("f-segment", "s");
  document.getElementById("f-reset").addEventListener("click", () => { S.w = WEEKS[WEEKS.length - 1]; S.p = S.z = S.s = "all"; writeHash(); });
}
function initFooter() {
  const m = D.meta || {};
  document.getElementById("foot-refresh").textContent = m.refreshed_at || "–";
  document.getElementById("foot-note").textContent = "Restaurant and brand names are from public Kaggle datasets; every ad metric is invented.";
  if (m.metric_dictionary_url) document.getElementById("foot-dict").href = m.metric_dictionary_url;
  if (m.repo_url) document.getElementById("foot-repo").href = m.repo_url;
}

let resizeT;
window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => charts.forEach((c) => c.resize()), 120); });
window.addEventListener("hashchange", render);
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", render);

(async function boot() {
  try {
    await need(CORE);
  } catch (e) {
    document.getElementById("page").innerHTML = `<p class="note">Could not load the dashboard data (${esc(e.message)}). If you are running locally, generate it with <code>make dashboard</code>.</p>`;
    return;
  }
  indexCore(); initFilters(); initFooter();
  need(["movers", "revenue_bridge", "platform_weekly", "fill_heatmap", "inventory_surface", "unfilled_premium", "clearing_price_dist",
    "advertiser_weekly_summary", "cohorts", "top_advertisers", "categories"]).catch(() => {});   // warm the cache in the background
  render();
})();
