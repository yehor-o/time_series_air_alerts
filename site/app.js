// Time-Series Air Alert Forecast, Ukraine (demo) — static front end.
// Reads site/data/*.json (written by scripts/export_site.py) and draws everything client-side.
"use strict";

const RAMP = ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5",
  "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6", "#cde2fb"]; // sequential blue, low -> high
const COL = { red: "#d03b3b", yellow: "#f2c230", unknown: "#8394ad", nodata: "#3a3f47", permanent: "#4b2630" };
const KYIV = "Europe/Kyiv";
const fmt = (opts) => new Intl.DateTimeFormat("en-GB", { timeZone: KYIV, ...opts });
const fDayTime = fmt({ weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const fDay = fmt({ weekday: "short", day: "2-digit", month: "short" });
const fHour = fmt({ hour: "2-digit", minute: "2-digit" });
const fShort = fmt({ weekday: "short", day: "numeric" });
const pct = (p) => (p == null ? "–" : `${Math.round(p * 100)}%`);

function rampColor(p) {
  if (p == null || isNaN(p)) return COL.nodata;
  const x = Math.max(0, Math.min(1, p)) * (RAMP.length - 1);
  const i = Math.floor(x), f = x - i;
  if (i >= RAMP.length - 1) return RAMP[RAMP.length - 1];
  const a = hex(RAMP[i]), b = hex(RAMP[i + 1]);
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(",")})`;
}
function hex(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); }
function textOn(p) { return p > 0.55 ? "#0b1424" : "#eef2f8"; }
const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, html = "") => { const e = document.createElement(tag); Object.assign(e, attrs); e.innerHTML = html; return e; };
const svgEl = (tag, attrs) => { const e = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };

const S = { level: "raion", h: "p1", block: 0, selected: null, D: {} };

async function load() {
  const names = ["meta", "now", "week", "history", "replay", "metrics"];
  const [geo, ...rest] = await Promise.all([fetch("data/raions.geojson").then((r) => r.json()),
    ...names.map((n) => fetch(`data/${n}.json`).then((r) => r.json()))]);
  S.geo = geo;
  names.forEach((n, i) => (S.D[n] = rest[i]));
  if (S.D.meta.sample) $("#sample-banner").hidden = false;
  $("#asof").textContent = `Forecast made at ${fDayTime.format(new Date(S.D.meta.forecast_time_utc))} (Kyiv time) · data up to ${fDayTime.format(new Date(S.D.meta.data_until_utc))}`;
  initTabs(); initMap(); initControls(); renderLegend("#legend"); initReplay(); renderQuality();
}

// ---------- helpers on data ----------
function unitKey(props) { return S.level === "raion" ? props.id : props.oblast_id; }
function unitName(id, level = S.level) {
  const u = S.D.meta.units[level][id];
  return level === "raion" ? `${u.name}, ${u.oblast}` : u.name;
}
function valueFor(props) {
  if (props.status !== "forecast") return null;
  const id = unitKey(props);
  if (S.h === "block") return S.D.week[S.level][id]?.[S.block];
  return S.D.now[S.level][id]?.[S.h];
}
function horizonLabel() {
  if (S.h === "p1") return "new alert within the next hour";
  if (S.h === "p3") return "new alert within the next 3 hours";
  const s = new Date(S.D.week.block_starts_utc[S.block]);
  return `new alert in ${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}`;
}

// ---------- tabs ----------
function initTabs() {
  document.querySelectorAll("#tabs button").forEach((b) => b.onclick = () => {
    document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("on", x === b));
    document.querySelectorAll(".page").forEach((p) => p.classList.toggle("on", p.id === `page-${b.dataset.page}`));
    if (b.dataset.page === "map") S.map.invalidateSize();
    if (b.dataset.page === "replay") { S.rmap.invalidateSize(); S.rmap.fitBounds(S.rlayer.getBounds()); }
  });
}

// ---------- main map ----------
function styleFor(props, value, selected) {
  if (props.status === "permanent") return { fillColor: COL.permanent, fillOpacity: 1, color: "#6b3a45", weight: 0.6 };
  if (props.status !== "forecast") return { fillColor: COL.nodata, fillOpacity: 1, color: "#555b66", weight: 0.6 };
  const fill = rampColor(value);
  const oblastView = S.level === "oblast";
  return { fillColor: fill, fillOpacity: 1, color: selected ? "#ffffff" : (oblastView ? fill : "#0e1726"),
    weight: selected ? 2.2 : (oblastView ? 0.8 : 0.6) };
}
function initMap() {
  S.map = L.map("map", { zoomControl: false, attributionControl: false, zoomSnap: 0.25, minZoom: 5, maxZoom: 9 });
  L.control.zoom({ position: "topright" }).addTo(S.map);
  S.layer = L.geoJSON(S.geo, {
    style: (f) => styleFor(f.properties, valueFor(f.properties), false),
    onEachFeature: (f, lyr) => {
      lyr.on("mousemove", (e) => showHover(e, f.properties));
      lyr.on("mouseout", () => ($("#hover").hidden = true));
      lyr.on("click", () => { if (f.properties.status === "forecast") select(unitKey(f.properties)); });
    },
  }).addTo(S.map);
  S.map.fitBounds(S.layer.getBounds(), { paddingTopLeft: [0, 60] });
}
function restyle() {
  S.layer.eachLayer((l) => {
    const p = l.feature.properties;
    const sel = p.status === "forecast" && S.selected && unitKey(p) === S.selected;
    l.setStyle(styleFor(p, valueFor(p), sel));
    if (sel) l.bringToFront();
  });
}
function showHover(e, props) {
  const h = $("#hover");
  if (props.status === "permanent") h.innerHTML = `<b>${props.name}</b><br>Permanent alert, no forecast`;
  else if (props.status !== "forecast") h.innerHTML = `<b>${props.name}</b><br>No forecast`;
  else h.innerHTML = `<b>${unitName(unitKey(props))}</b><br>${pct(valueFor(props))} chance of a ${horizonLabel()}`;
  const pt = e.containerPoint;
  h.style.left = `${pt.x + 14}px`; h.style.top = `${pt.y + 10}px`; h.hidden = false;
}
function renderLegend(sel, title) {
  const steps = RAMP.map((c) => `<span style="flex:1;background:${c}"></span>`).join("");
  $(sel).innerHTML = `<div>${title || "Chance of a new alert"}</div><div class="bar">${steps}</div>
    <div class="ticks"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
    <div class="keys"><span><i class="sw" style="background:${COL.permanent}"></i>Permanent alert</span>
    <span><i class="sw" style="background:${COL.nodata}"></i>No forecast</span></div>`;
}

// ---------- controls ----------
function initControls() {
  document.querySelectorAll("[data-level]").forEach((b) => b.onclick = () => {
    document.querySelectorAll("[data-level]").forEach((x) => x.classList.toggle("on", x === b));
    S.level = b.dataset.level; S.selected = null; restyle(); renderPanel();
  });
  document.querySelectorAll("[data-h]").forEach((b) => b.onclick = () => {
    document.querySelectorAll("[data-h]").forEach((x) => x.classList.toggle("on", x === b));
    S.h = b.dataset.h; $("#blockpicker").hidden = S.h !== "block"; restyle();
  });
  const starts = S.D.week.block_starts_utc.map((s) => new Date(s));
  const days = [...new Set(starts.map((d) => fDay.format(d)))];
  const dp = $("#daypick"), bp = $("#blockpick");
  const drawBlocks = (day) => {
    bp.innerHTML = "";
    starts.forEach((d, i) => {
      if (fDay.format(d) !== day) return;
      const b = el("button", { className: i === S.block ? "on" : "" }, `${fHour.format(d)}`);
      b.onclick = () => { S.block = i; drawBlocks(day); restyle(); };
      bp.append(b);
    });
  };
  days.forEach((day, k) => {
    const b = el("button", { className: k === 0 ? "on" : "" }, day);
    b.onclick = () => {
      dp.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
      S.block = starts.findIndex((d) => fDay.format(d) === day); drawBlocks(day); restyle();
    };
    dp.append(b);
  });
  drawBlocks(days[0]);
}

// ---------- side panel ----------
function select(id) { S.selected = id; restyle(); renderPanel(); }
function renderPanel() {
  const P = $("#panel");
  if (!S.selected) { P.innerHTML = `<div class="empty">Click a district or oblast on the map to see its forecast.</div>`; return; }
  const id = S.selected, lv = S.level, n = S.D.now[lv][id];
  P.innerHTML = `<h2>${unitName(id)}</h2><div class="muted">${lv === "raion" ? "District" : "Oblast"} forecast, made ${fDayTime.format(new Date(S.D.meta.forecast_time_utc))} Kyiv time</div>
    <div class="tiles">
      <div class="tile"><div class="v">${pct(n.p1)}</div><div class="k">new alert within 1 hour</div></div>
      <div class="tile"><div class="v">${pct(n.p3)}</div><div class="k">new alert within 3 hours</div></div>
      <div class="tile"><div class="v">${n.dur[0]}–${n.dur[1]} min</div><div class="k">typical duration if one starts</div></div>
      <div class="tile"><div class="v">${pct(n.red)}</div><div class="k">chance it is <span class="chip red">red</span> rather than <span class="chip yellow">yellow</span></div></div>
    </div>
    <h3>Next 24 hours (Kyiv time)</h3><div class="cells" id="next24"></div>
    <div class="muted" style="margin-top:6px">About <b>${n.cnt[0]}–${n.cnt[1]}</b> alerts and <b>${n.hrs[0]}–${n.hrs[1]} h</b> under alert expected.</div>
    <h3>This week: chance of a new alert per 3-hour block</h3><div id="heat"></div>
    <h3>Week-ahead strip</h3><div id="wstrip"></div>
    <h3>Last 7 days: actual alerts vs forecast</h3><div id="hstrip"></div>`;
  const starts = S.D.week.block_starts_utc.map((s) => new Date(s));
  const wk = S.D.week[lv][id];
  const c24 = $("#next24");
  n.next24.forEach((p, i) => c24.append(el("div", { className: "cell", title: `${pct(p)} chance of a new alert` },
    `<span class="t">${fHour.format(starts[i])}</span>${pct(p)}`)));
  c24.querySelectorAll(".cell").forEach((c, i) => { c.style.background = rampColor(n.next24[i]); c.style.color = textOn(n.next24[i]); });
  drawHeat($("#heat"), starts, wk);
  drawWeekStrip($("#wstrip"), starts, wk);
  drawHistory($("#hstrip"), S.D.history, S.D.history[lv][id]);
}

const tip = el("div", { className: "strip-tip" }); tip.hidden = true; document.body.append(tip);
function showTip(e, html) { tip.innerHTML = html; tip.style.left = `${e.clientX + 12}px`; tip.style.top = `${e.clientY + 10}px`; tip.hidden = false; }

function drawHeat(host, starts, wk) {
  const days = [...new Set(starts.map((d) => fDay.format(d)))];
  const W = 400, cw = 38, ch = 20, left = 80, top = 16;
  const svg = svgEl("svg", { width: W, height: top + days.length * (ch + 2) + 4 });
  const blocks = ["00", "03", "06", "09", "12", "15", "18", "21"];
  blocks.forEach((b, j) => { const t = svgEl("text", { x: left + j * (cw + 2) + cw / 2, y: 11, "text-anchor": "middle" }); t.textContent = `${b}:00`; svg.append(t); });
  days.forEach((d, r) => { const t = svgEl("text", { x: 0, y: top + r * (ch + 2) + 14 }); t.textContent = d; svg.append(t); });
  starts.forEach((s, i) => {
    const r = days.indexOf(fDay.format(s));
    const j = Math.floor(Number(fmt({ hour: "2-digit", hourCycle: "h23" }).format(s)) / 3);
    const rect = svgEl("rect", { x: left + j * (cw + 2), y: top + r * (ch + 2), width: cw, height: ch, rx: 3, fill: rampColor(wk[i]) });
    rect.onmousemove = (e) => showTip(e, `${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}<br><b>${pct(wk[i])}</b> chance of a new alert`);
    rect.onmouseleave = () => (tip.hidden = true);
    svg.append(rect);
  });
  host.append(svg);
}

function drawWeekStrip(host, starts, wk) {
  const W = 400, H = 70, base = 52, n = starts.length, bw = W / n;
  const svg = svgEl("svg", { width: W, height: H });
  svg.append(svgEl("line", { x1: 0, x2: W, y1: base, y2: base, stroke: "#2b3d5c" }));
  starts.forEach((s, i) => {
    const h = Math.max(1, wk[i] * 44);
    const r = svgEl("rect", { x: i * bw + 0.5, y: base - h, width: bw - 1, height: h, rx: 1.5, fill: rampColor(Math.max(wk[i], 0.35)) });
    r.onmousemove = (e) => showTip(e, `${fDay.format(s)} ${fHour.format(s)}<br><b>${pct(wk[i])}</b> chance of a new alert`);
    r.onmouseleave = () => (tip.hidden = true);
    svg.append(r);
    if (fHour.format(s) === "00:00") { const t = svgEl("text", { x: i * bw, y: H - 4 }); t.textContent = fShort.format(s); svg.append(t); }
  });
  host.append(svg);
}

function drawHistory(host, H, u) {
  const W = 400, hours = H.hours, t0 = new Date(H.start_utc).getTime(), x = (m) => (m / (hours * 60)) * W;
  const svg = svgEl("svg", { width: W, height: 110 });
  const lab = (txt, y) => { const t = svgEl("text", { x: 0, y }); t.textContent = txt; svg.append(t); };
  lab("Actual alerts", 10); lab("Forecast: chance of a new alert within 3 h", 46);
  u.alerts.forEach(([s, e, lvl]) => {
    const r = svgEl("rect", { x: x(s), y: 14, width: Math.max(1.5, x(e) - x(s)), height: 16, rx: 2, fill: COL[lvl] || COL.unknown });
    r.onmousemove = (ev) => showTip(ev, `${fDayTime.format(new Date(t0 + s * 6e4))} – ${fHour.format(new Date(t0 + e * 6e4))}<br>${lvl === "red" || lvl === "yellow" ? `<span class="chip ${lvl}">${lvl}</span>` : "level not recorded"}`);
    r.onmouseleave = () => (tip.hidden = true);
    svg.append(r);
  });
  const base = 92, top = 52;
  const pts = u.pred.map((p, h) => `${(h + 0.5) / hours * W},${base - (p / 100) * (base - top)}`).join(" ");
  svg.append(svgEl("polygon", { points: `0,${base} ${pts} ${W},${base}`, fill: "#3987e5", "fill-opacity": 0.25 }));
  svg.append(svgEl("polyline", { points: pts, fill: "none", stroke: "#5598e7", "stroke-width": 2 }));
  svg.append(svgEl("line", { x1: 0, x2: W, y1: base, y2: base, stroke: "#2b3d5c" }));
  for (let d = 0; d <= hours; d += 24) {
    svg.append(svgEl("line", { x1: x(d * 60), x2: x(d * 60), y1: 12, y2: base, stroke: "#2b3d5c", "stroke-dasharray": "2,3" }));
    if (d < hours) { const t = svgEl("text", { x: x(d * 60) + 2, y: 106 }); t.textContent = fShort.format(new Date(t0 + d * 3600e3)); svg.append(t); }
  }
  const hit = svgEl("rect", { x: 0, y: 50, width: W, height: 44, fill: "transparent" });
  hit.onmousemove = (e) => {
    const h = Math.min(hours - 1, Math.floor(((e.offsetX) / W) * hours));
    showTip(e, `${fDayTime.format(new Date(t0 + h * 3600e3))}<br>forecast: <b>${u.pred[h]}%</b> chance of a new alert within 3 h`);
  };
  hit.onmouseleave = () => (tip.hidden = true);
  svg.append(hit);
  host.append(svg);
  host.append(el("div", { className: "muted" }, `<span class="chip red">red</span> <span class="chip yellow">yellow</span> <i class="sw" style="background:${COL.unknown}"></i>level not recorded (before 6 Sep)`));
}

// ---------- replay ----------
function initReplay() {
  const R = S.D.replay;
  S.rmap = L.map("rmap", { attributionControl: false, zoomSnap: 0.25, minZoom: 5, maxZoom: 9 });
  S.rlayer = L.geoJSON(S.geo, { style: () => ({ fillColor: COL.nodata, fillOpacity: 1, color: "#0e1726", weight: 0.6 }) }).addTo(S.rmap);
  S.rmap.fitBounds(S.rlayer.getBounds());
  renderLegend("#rlegend", "Predicted chance of a new alert within 3 h");
  const sl = $("#rslider"); sl.max = R.hours - 1;
  const t0 = new Date(R.start_utc).getTime();
  const draw = (k) => {
    let hits = 0, starts = 0, brier = 0, n = 0;
    S.rlayer.eachLayer((l) => {
      const p = l.feature.properties;
      if (p.status !== "forecast") { l.setStyle({ fillColor: p.status === "permanent" ? COL.permanent : COL.nodata }); return; }
      const u = R.raion[p.id], pr = u.p[k] / 100, y = u.y[k];
      l.setStyle({ fillColor: rampColor(pr), color: y ? "#ffffff" : "#0e1726", weight: y ? 1.6 : 0.5 });
      if (y) { l.bringToFront(); starts++; if (pr >= 0.5) hits++; }
      if (y != null) { brier += (pr - y) ** 2; n++; }  // null = outcome unknown (data hole / end of data)
    });
    $("#rtime").textContent = `${fDayTime.format(new Date(t0 + k * 3600e3))} (Kyiv time)`;
    $("#rstats").innerHTML = `<div class="tile"><div class="v">${starts}</div><div class="k">districts where an alert actually started in the next 3 h</div></div>
      <div class="tile"><div class="v">${starts ? Math.round((100 * hits) / starts) : 0}%</div><div class="k">of those had a forecast of 50% or more</div></div>
      <div class="tile"><div class="v">${n ? (brier / n).toFixed(3) : "–"}</div><div class="k">Brier score this hour (0 = perfect)</div></div>`;
  };
  sl.oninput = () => draw(+sl.value);
  let timer = null;
  $("#rplay").onclick = () => {
    if (timer) { clearInterval(timer); timer = null; $("#rplay").textContent = "▶ Play"; return; }
    $("#rplay").textContent = "❚❚ Pause";
    timer = setInterval(() => { sl.value = (+sl.value + 1) % R.hours; draw(+sl.value); }, +$("#rspeed").value);
  };
  $("#rstep").onclick = () => { sl.value = Math.min(R.hours - 1, +sl.value + 1); draw(+sl.value); };
  draw(0);
}

// ---------- quality: how good is it? (test results + model comparison) ----------
const CH = { chosen: "#3987e5", other: "#6b7a93", s2: "#d95926", s3: "#199e70", grid: "#2b3d5c", ink: "#b6c2d6", muted: "#8394ad" };
const f3 = (v) => (v == null ? "–" : (+v).toFixed(3));
const f2 = (v) => (v == null ? "–" : (+v).toFixed(2));

// Horizontal bars, one per method; the chosen method in blue, alternatives grey; value labels at the bar end.
function hbars(host, title, items, { fmt = f3, min = 0, max = 1, ref = null, note = "" } = {}) {
  const W = 400, lw = 150, rowH = 26, top = ref ? 18 : 6, H = top + items.length * rowH + 22;
  const sx = (v) => lw + ((v - min) / (max - min)) * (W - lw - 54);
  const box = el("div", { className: "chart" }, `<div class="ctitle">${title}</div>`);
  const svg = svgEl("svg", { width: W, height: H });
  const x0 = sx(Math.max(min, 0));
  [min, (min + max) / 2, max].forEach((v) => {
    svg.append(svgEl("line", { x1: sx(v), x2: sx(v), y1: top, y2: H - 18, stroke: CH.grid, "stroke-dasharray": "2,3" }));
    const t = svgEl("text", { x: sx(v) - 8, y: H - 4 }); t.textContent = fmt(v); svg.append(t);
  });
  items.forEach((it, k) => {
    const y = top + k * rowH, a = Math.min(x0, sx(it.v)), w = Math.max(2, Math.abs(sx(it.v) - x0));
    const lab = svgEl("text", { x: 0, y: y + 15, class: it.chosen ? "strong" : "" }); lab.textContent = it.label; svg.append(lab);
    const r = svgEl("rect", { x: a, y: y + 4, width: w, height: 16, rx: 4, fill: it.chosen ? CH.chosen : CH.other });
    r.onmousemove = (e) => showTip(e, `${it.label}: <b>${fmt(it.v)}</b>${it.tip ? "<br>" + it.tip : ""}`);
    r.onmouseleave = () => (tip.hidden = true);
    svg.append(r);
    // with a reference line the value sits inside the bar end, so it never collides with the line
    const v = ref ? svgEl("text", { x: sx(it.v) - 6, y: y + 16, "text-anchor": "end", class: "inbar" })
      : svgEl("text", { x: Math.max(sx(it.v), x0) + 5, y: y + 16, class: it.chosen ? "strong" : "" });
    v.textContent = fmt(it.v); svg.append(v);
  });
  svg.append(svgEl("line", { x1: x0, x2: x0, y1: top, y2: H - 18, stroke: CH.muted }));
  if (ref) {
    svg.append(svgEl("line", { x1: sx(ref.v), x2: sx(ref.v), y1: top, y2: H - 18, stroke: "#eef2f8", "stroke-width": 1.5, "stroke-dasharray": "5,3" }));
    const t = svgEl("text", { x: sx(ref.v), y: top - 6, "text-anchor": "middle" }); t.textContent = ref.label; svg.append(t);
  }
  box.append(svg);
  if (note) box.append(el("div", { className: "cnote" }, note));
  host.append(box);
}

// Lines over x categories (e.g. lead day), legend + end labels, hover shows all series at that x.
function lchart(host, title, xs, series, { fmt = f3, min, max, note = "" } = {}) {
  const W = 400, H = 210, l = 40, r = 70, t = 10, b = 26;
  const sx = (i) => l + (i / (xs.length - 1)) * (W - l - r), sy = (v) => t + (1 - (v - min) / (max - min)) * (H - t - b);
  const box = el("div", { className: "chart" }, `<div class="ctitle">${title}</div>`);
  const svg = svgEl("svg", { width: W, height: H });
  for (let k = 0; k <= 4; k++) {
    const v = min + (k / 4) * (max - min);
    svg.append(svgEl("line", { x1: l, x2: W - r, y1: sy(v), y2: sy(v), stroke: CH.grid }));
    const tx = svgEl("text", { x: 0, y: sy(v) + 4 }); tx.textContent = fmt(v); svg.append(tx);
  }
  xs.forEach((x, i) => { const tx = svgEl("text", { x: sx(i) - 14, y: H - 6 }); tx.textContent = x; svg.append(tx); });
  series.forEach((s) => {
    svg.append(svgEl("polyline", { points: s.vals.map((v, i) => `${sx(i)},${sy(v)}`).join(" "), fill: "none", stroke: s.color, "stroke-width": 2 }));
    s.vals.forEach((v, i) => svg.append(svgEl("circle", { cx: sx(i), cy: sy(v), r: 4, fill: s.color, stroke: "#0e1726", "stroke-width": 2 })));
  });
  // end labels, nudged apart so they never overlap
  const ends = series.map((s) => ({ s, y: sy(s.vals[s.vals.length - 1]) })).sort((a, b2) => a.y - b2.y);
  ends.forEach((e, k) => { if (k && e.y - ends[k - 1].y < 13) e.y = ends[k - 1].y + 13; });
  ends.forEach((e) => { const tx = svgEl("text", { x: W - r + 6, y: e.y + 4 }); tx.textContent = e.s.short; tx.setAttribute("fill", CH.ink); svg.append(tx); });
  xs.forEach((x, i) => {
    const hit = svgEl("rect", { x: sx(i) - (W - l - r) / (2 * (xs.length - 1)), y: t, width: (W - l - r) / (xs.length - 1), height: H - t - b, fill: "transparent" });
    hit.onmousemove = (e) => showTip(e, `<b>${x}</b><br>` + series.map((s) => `<i class="sw" style="background:${s.color}"></i>${s.name}: <b>${fmt(s.vals[i])}</b>`).join("<br>"));
    hit.onmouseleave = () => (tip.hidden = true);
    svg.append(hit);
  });
  box.append(svg);
  box.append(el("div", { className: "legend-row" }, series.map((s) => `<span><i class="sw" style="background:${s.color}"></i>${s.name}</span>`).join("")));
  if (note) box.append(el("div", { className: "cnote" }, note));
  host.append(box);
}

function renderQuality() {
  const M = S.D.metrics, F = M.full, LV = { raion: "District", oblast: "Oblast" };
  const rows = (arr, cols) => arr.map((r) => `<tr>${cols.map(([k, f, num]) => `<td class="${num ? "num" : ""}">${f ? f(r[k]) : r[k]}</td>`).join("")}</tr>`).join("");
  const cov = M.range_coverage_validation_week;
  $("#quality").innerHTML = `<div class="docbody wide">
    <h2>How good is it?</h2>
    <p>Everything on this page was measured on the <b>test period ${M.test_period[0]} – ${M.test_period[1]}</b>: four weeks that no model and
      no design choice had seen. Every model was trained only on earlier data, every forecast used only information available at its
      time, and the test was run <b>once</b>. All choices were frozen before it, and nothing was changed after seeing the results, including
      the two places where our model lost (marked <span class="lost">lost</span> below).</p>
    <p><b>AUC</b>: the chance that a random hour with a new alert got a higher forecast than a random hour without one (0.5 = guessing, 1 = perfect).
      <b>Skill</b>: how much smaller the forecast errors (Brier score) are than the simple rule "how often did an alert start at this clock hour on
      each of the last 14 days" (0 = no better, 0.3 = 30% smaller, below 0 = worse). In the charts, <span class="chip-b">blue</span> is the method
      the site uses and <span class="chip-g">grey</span> are the alternatives.</p>
    <table><tr><th>What we predict</th><th>Level</th><th class="num">Model AUC</th><th class="num">Simple rule AUC</th><th class="num">Skill</th></tr>
      ${rows(M.headline, [["target"], ["level"], ["model_auc", f3, 1], ["baseline_auc", f3, 1], ["skill", f3, 1]])}</table>

    <h3>1. Our model vs simpler methods: will a new alert start?</h3>
    <div class="seg" id="q-metric"><button data-m="ROC-AUC" class="on">AUC</button><button data-m="skill vs same-hour">Skill</button></div>
    <p class="cap">LightGBM (our model) against three simpler methods: the clock-hour rule, "persistence" (an alert is likely again if one started in the
      last hours) and logistic regression (a simple straight-line model). Higher is better.</p>
    <div class="grid2" id="q-models"></div>

    <h3>2. Does Telegram help?</h3>
    <p class="cap">The same model with extra inputs from Telegram channels (@war_monitor: threat reports; @kpszsu: the Air Force). Skill; higher is better.
      Telegram was <b>not</b> used, because it lost on the validation weeks before the test. On the test, @war_monitor was slightly better at oblast level and
      slightly worse at district level; differences below 0.01 are within noise.</p>
    <div class="grid2" id="q-tg"></div>

    <h3>3. Is it stable? Week by week, day vs night</h3>
    <p class="cap">Skill of the 3-hour forecast in each full test week, and AUC by time of day (Kyiv). The model was useful in every week, a bit better by day.</p>
    <div class="grid2" id="q-stab"></div>

    <h3>4. Can the percentages be taken literally? (calibration)</h3>
    <p class="cap">District forecasts for 3 hours, grouped by the forecast. When we said 40–50%, an alert started in about 46% of cases. Points on the dashed line = perfect.</p>
    <div id="calib"></div>

    <h3>5. How long will an alert last? (duration ranges)</h3>
    <p class="cap">We show a range "usually X–Y min" (our 25th–75th percentile). A good range contains the true duration about half the time (dashed line).</p>
    <div class="grid2" id="q-dur"></div>

    <h3>6. Next 24 hours: how many alerts, how many hours under alert?</h3>
    <p class="cap">Average miss (lower is better), against "same as the last 24 hours" and "daily average of the last 7 days".
      Hours under alert: our model wins by 8%. Number of alerts: <span class="lost">lost</span>, the 7-day average was 4–8% better.
      The ranges shown on the map contained the true value ${pct(cov.raion.y_hours_24h.inside_25_75_range)} (hours) and ${pct(cov.raion.y_count_24h.inside_25_75_range)} (count) of the time
      in the last validation week (ideal about 50%).</p>
    <div class="grid2" id="q-24"></div>

    <h3>7. When in the coming week? (3-hour blocks)</h3>
    <p class="cap">AUC by how many days ahead. The site uses a <b>blend</b>: our timing model for the near term, fading into the "pattern rule"
      (share of the last 14 days with an alert in that clock block) by day 3. Districts: the blend was best on days 1–3.
      Oblasts: <span class="lost">lost</span>, the blend's percentages for days 1–2 were less accurate than the pattern rule's
      (average error ${f3(F.oblast.timing.brier_by_day["blend (chosen)"]["day 1"])} vs ${f3(F.oblast.timing.brier_by_day["pattern rule"]["day 1"])} on day 1), although it ranks blocks equally well.</p>
    <div class="grid2" id="q-time"></div>

    <h3>8. Red or yellow?</h3>
    <p class="cap">If an alert starts in a district, is it red (missiles, ballistic) or yellow (drones)? Trained on ${F.red.train.toLocaleString()} alerts
      from 6–26 Sep, tested on ${F.red.test.toLocaleString()} alerts from 27 Sep (${pct(F.red.red_share)} red). The simple rule
      "this district's red share in the last 7 days" works best.</p>
    <div class="grid2" id="q-red"></div>
  </div>`;

  const MODELS = [["baseline: same hour, last 14 days", "Clock-hour rule"], ["baseline: persistence", "Persistence"],
    ["logistic regression", "Logistic regression"], ["LightGBM (chosen)", "LightGBM (ours)"]];
  const drawModels = (metric) => {
    const host = $("#q-models"); host.innerHTML = "";
    for (const lv of ["raion", "oblast"]) for (const h of [1, 3]) {
      const tb = F[lv][`start_${h}h`].table;
      hbars(host, `${LV[lv]}, new alert within ${h} h`, MODELS.map(([k, lab]) => ({ label: lab, v: tb[k][metric], chosen: k.includes("chosen") })),
        metric === "ROC-AUC" ? { min: 0.5, max: 0.9 } : { min: -0.2, max: 0.5 });
    }
  };
  drawModels("ROC-AUC");
  document.querySelectorAll("#q-metric button").forEach((b) => (b.onclick = () => {
    document.querySelectorAll("#q-metric button").forEach((x) => x.classList.toggle("on", x === b)); drawModels(b.dataset.m);
  }));

  for (const lv of ["raion", "oblast"]) for (const h of [1, 3]) {
    const tb = F[lv][`start_${h}h`].table, k = "skill vs same-hour";
    hbars($("#q-tg"), `${LV[lv]}, new alert within ${h} h`, [
      { label: "No Telegram (used)", v: tb["LightGBM (chosen)"][k], chosen: true },
      { label: "+ @war_monitor", v: tb["LightGBM + @war_monitor"][k] }, { label: "+ @kpszsu", v: tb["LightGBM + @kpszsu"][k] }],
    { min: 0, max: 0.5 });
  }
  for (const lv of ["raion", "oblast"]) {
    const wk = F[lv].start_3h.weeks;
    hbars($("#q-stab"), `${LV[lv]}: skill by test week (3 h)`, ["week 1", "week 2", "week 3", "week 4"].map((w) => ({ label: w[0].toUpperCase() + w.slice(1), v: wk[w]["skill vs same-hour"], chosen: true })),
      { min: 0, max: 0.6, note: "A fifth, partial week (the last 10 hours of data) is left out." });
  }
  for (const lv of ["raion", "oblast"]) {
    const dn = F[lv].start_3h.day_night;
    hbars($("#q-stab"), `${LV[lv]}: AUC by time of day (3 h)`, [{ label: "Day (06–22)", v: dn["day (06-22 Kyiv)"]["ROC-AUC"], chosen: true },
      { label: "Night (22–06)", v: dn["night (22-06 Kyiv)"]["ROC-AUC"], chosen: true }], { min: 0.5, max: 0.9 });
  }
  drawCalibration($("#calib"), M.calibration);
  for (const lv of ["raion", "oblast"]) {
    const d = F[lv].duration, k = "true duration inside the 25-75% range", wk = "average range width (min)";
    hbars($("#q-dur"), `${LV[lv]}: true duration inside the range`, [
      { label: "Last 10 alerts (rule)", v: d["baseline: last 10 alerts"][k], tip: `average range width ${Math.round(d["baseline: last 10 alerts"][wk])} min` },
      { label: "LightGBM (ours)", v: d["LightGBM quantiles (chosen)"][k], chosen: true, tip: `average range width ${Math.round(d["LightGBM quantiles (chosen)"][wk])} min` }],
    { fmt: pct, min: 0, max: 0.7, ref: { v: 0.5, label: "ideal" } });
  }
  const R24 = [["baseline: same as last 24h", "Same as last 24 h"], ["baseline: daily average of last 7 days", "7-day average"], ["LightGBM (chosen)", "LightGBM (ours)"]];
  for (const [tg, name, unit] of [["hours", "hours under alert", "h"], ["count", "number of alerts", ""]]) for (const lv of ["raion", "oblast"]) {
    const t = F[lv].next24h[tg];
    hbars($("#q-24"), `${LV[lv]}: ${name}, average miss${unit ? " (h)" : ""}`, R24.map(([k, lab]) => ({ label: lab, v: t[k].MAE, chosen: k.includes("chosen") })),
      { fmt: f2, min: 0, max: 2.5 });
  }
  const days = ["day 1", "day 2", "day 3", "day 4", "day 5", "day 6", "day 7"];
  for (const lv of ["raion", "oblast"]) {
    const a = F[lv].timing.auc_by_day;
    lchart($("#q-time"), `${LV[lv]}: AUC by days ahead`, days.map((d) => d.replace("day ", "Day ")), [
      { name: "Blend (used)", short: "Blend", color: CH.chosen, vals: days.map((d) => a["blend (chosen)"][d]) },
      { name: "Pattern rule", short: "Pattern", color: CH.s2, vals: days.map((d) => a["pattern rule"][d]) },
      { name: "Timing model alone", short: "Model", color: CH.s3, vals: days.map((d) => a["timing model alone"][d]) }],
    { min: 0.78, max: 0.84 });
  }
  const rt = F.red.table;
  hbars($("#q-red"), "Red vs yellow: AUC", [["baseline: overall red share", "Always the average share"], ["baseline: previous alert's level", "Previous alert's level"],
    ["logistic, 5 level features", "Logistic regression"], ["raion red share last 7 days (chosen)", "Red share, last 7 days"]]
    .map(([k, lab]) => ({ label: lab, v: rt[k]["ROC-AUC"], chosen: k.includes("chosen") })), { min: 0.5, max: 0.9 });
}
function drawCalibration(host, cal) {
  const W = 360, H = 300, m = 34, sx = (v) => m + v * (W - m - 8), sy = (v) => H - m - v * (H - m - 8);
  const svg = svgEl("svg", { width: W, height: H });
  for (let v = 0; v <= 1.001; v += 0.25) {
    svg.append(svgEl("line", { x1: sx(0), x2: sx(1), y1: sy(v), y2: sy(v), stroke: "#2b3d5c" }));
    const t = svgEl("text", { x: 2, y: sy(v) + 3 }); t.textContent = `${v * 100}%`; svg.append(t);
    const t2 = svgEl("text", { x: sx(v) - 8, y: H - m + 14 }); t2.textContent = `${v * 100}%`; svg.append(t2);
  }
  svg.append(svgEl("line", { x1: sx(0), y1: sy(0), x2: sx(1), y2: sy(1), stroke: "#8394ad", "stroke-dasharray": "4,4" }));
  const pts = cal.map((c) => `${sx(c.predicted)},${sy(c.observed)}`).join(" ");
  svg.append(svgEl("polyline", { points: pts, fill: "none", stroke: "#3987e5", "stroke-width": 2 }));
  cal.forEach((c) => {
    const d = svgEl("circle", { cx: sx(c.predicted), cy: sy(c.observed), r: 4.5, fill: "#3987e5", stroke: "#152238", "stroke-width": 2 });
    d.onmousemove = (e) => showTip(e, `forecast ${c.bin}: alerts started in <b>${pct(c.observed)}</b> of ${c.rows.toLocaleString()} cases`);
    d.onmouseleave = () => (tip.hidden = true);
    svg.append(d);
  });
  const lx = svgEl("text", { x: sx(0.3), y: H - 4 }); lx.textContent = "forecast probability"; svg.append(lx);
  const ly = svgEl("text", { x: sx(0.02), y: 12 }); ly.textContent = "share of cases with a new alert (dashed = perfect)"; svg.append(ly);
  host.append(svg);
}

load().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<pre style="color:#f88">Failed to load data: ${e}</pre>`); console.error(e); });
