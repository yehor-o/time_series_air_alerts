// Time-Series Air Alert Forecast, Ukraine (demo) — static front end.
// Reads site/data/*.json (written by scripts/export_site.py) and draws everything client-side.
"use strict";

const RAMP = ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5",
  "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6", "#cde2fb"]; // sequential blue, low -> high
const COL = { red: "#d03b3b", yellow: "#f2c230", unknown: "#8394ad", nodata: "#3a3f47", permanent: "#4b2630" };
const KYIV = "Europe/Kyiv";
// language: ?lang=uk|en in the URL, else the remembered choice, else English. T(en, uk) picks the text.
const LANG = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "uk" || q === "en") { try { localStorage.setItem("lang", q); } catch (e) { /* storage blocked */ } return q; }
  try { return localStorage.getItem("lang") === "uk" ? "uk" : "en"; } catch (e) { return "en"; }
})();
const UK = LANG === "uk";
const T = (en, uk) => (UK ? uk : en);  // not L: that is Leaflet's global
const fmt = (opts) => new Intl.DateTimeFormat(UK ? "uk-UA" : "en-GB", { timeZone: KYIV, ...opts });
const fDayTime = fmt({ weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const fDay = fmt({ weekday: "short", day: "2-digit", month: "short" });
const fHour = fmt({ hour: "2-digit", minute: "2-digit" });
const fShort = fmt({ weekday: "short", day: "numeric" });
const lvlName = (l) => (l === "red" ? T("red", "червона") : l === "yellow" ? T("yellow", "жовта") : l);
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
  const names = ["meta", "now", "week", "history", "replay", "metrics", "check"];
  const [geo, ...rest] = await Promise.all([fetch("data/raions.geojson").then((r) => r.json()),
    ...names.map((n) => fetch(`data/${n}.json`).then((r) => r.json()))]);
  S.geo = geo;
  names.forEach((n, i) => (S.D[n] = rest[i]));
  S.ukName = {};  // Ukrainian district names from the map file
  geo.features.forEach((f) => { const p = f.properties; if (p.id) S.ukName[p.id] = p.id.startsWith("м. ") ? p.id.split("|")[0] : `${p.name_uk} район`; });
  applyStaticI18n();
  if (S.D.meta.sample) $("#sample-banner").hidden = false;
  $("#asof").textContent = T(`Forecast made at ${fDayTime.format(new Date(S.D.meta.forecast_time_utc))} (Kyiv time) · data up to ${fDayTime.format(new Date(S.D.meta.data_until_utc))}`,
    `Прогноз зроблено ${fDayTime.format(new Date(S.D.meta.forecast_time_utc))} (за Києвом) · дані до ${fDayTime.format(new Date(S.D.meta.data_until_utc))}`);
  if (S.D.meta.week_time_utc && S.D.meta.week_time_utc !== S.D.meta.forecast_time_utc)
    $("#asof").textContent += T(` · week view from ${fHour.format(new Date(S.D.meta.week_time_utc))}`, ` · тижневий прогноз від ${fHour.format(new Date(S.D.meta.week_time_utc))}`);
  initTabs(); initMap(); initControls(); renderLegend("#legend"); initReplay(); renderQuality(); initCheck();
}

// ---------- static texts (index.html) in Ukrainian; the About page has its own Ukrainian template ----------
const STATIC_UK = {
  "title": "Прогноз повітряних тривог, Україна (демо)",
  "#site-title": 'Прогноз повітряних тривог, Україна <span class="demo">демо</span>',
  '[data-page="map"]': "Мапа", '[data-page="replay"]': "Повтор", '[data-page="check"]': "Перевірка прогнозу",
  '[data-page="quality"]': "Наскільки добре?", '[data-page="about"]': "Про проєкт",
  "#warn": "Лише демонстрація, не офіційна система оповіщення. Завжди дійте за офіційними сигналами повітряної тривоги.",
  "#lbl-view": "Вигляд", '[data-level="raion"]': "Райони", '[data-level="oblast"]': "Області",
  "#lbl-fc": "Прогноз", '[data-h="p1"]': "Найближча 1 год", '[data-h="p3"]': "Найближчі 3 год", '[data-h="block"]': "За блоком часу",
  "#replay-title": "Повтор тестових тижнів",
  "#replay-text": "Кожна година тестового періоду: колір показує, що модель прогнозувала на наступні 3 години, використовуючи лише дані, доступні на той момент. Біла обвідка позначає райони, де тривога справді почалася протягом цих 3 годин.",
  "#rplay": "▶ Відтворити", "#rstep": "+1 год", "#panel .empty": "Натисніть на район чи область на мапі, щоб побачити прогноз.",
  '#rspeed option[value="400"]': "Повільно", '#rspeed option[value="150"]': "Звичайно", '#rspeed option[value="50"]': "Швидко",
};
function applyStaticI18n() {
  document.documentElement.lang = LANG;
  document.querySelectorAll(".langsw button").forEach((b) => {
    b.classList.toggle("on", b.dataset.lang === LANG);
    b.onclick = () => { const u = new URL(location.href); u.searchParams.set("lang", b.dataset.lang); location.href = u.toString(); };
  });
  if (!UK) return;
  for (const [sel, html] of Object.entries(STATIC_UK)) {
    if (sel === "title") { document.title = html; continue; }
    document.querySelectorAll(sel).forEach((e) => (e.innerHTML = html));
  }
  const tpl = $("#about-uk"); if (tpl) $("#page-about .docbody").innerHTML = tpl.innerHTML;
}

// ---------- helpers on data ----------
function unitKey(props) { return S.level === "raion" ? props.id : props.oblast_id; }
function unitName(id, level = S.level) {
  const u = S.D.meta.units[level][id];
  if (UK) return level === "raion" ? (id.startsWith("м. ") ? S.ukName[id] : `${S.ukName[id]}, ${u.oblast_id}`) : id;
  return level === "raion" ? `${u.name}, ${u.oblast}` : u.name;
}
function valueFor(props) {
  if (props.status !== "forecast") return null;
  const id = unitKey(props);
  if (S.h === "block") return S.D.week[S.level][id]?.[S.block];
  return S.D.now[S.level][id]?.[S.h];
}
function horizonLabel() {
  if (S.h === "p1") return T("new alert within the next hour", "нової тривоги протягом години");
  if (S.h === "p3") return T("new alert within the next 3 hours", "нової тривоги протягом 3 годин");
  const s = new Date(S.D.week.block_starts_utc[S.block]);
  return T(`new alert in ${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}`,
    `нової тривоги ${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}`);
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
  const nm = UK ? props.name_uk : props.name;
  if (props.status === "permanent") h.innerHTML = `<b>${nm}</b><br>${T("Permanent alert, no forecast", "Постійна тривога, прогнозу немає")}`;
  else if (props.status !== "forecast") h.innerHTML = `<b>${nm}</b><br>${T("No forecast", "Прогнозу немає")}`;
  else h.innerHTML = `<b>${unitName(unitKey(props))}</b><br>${T(`${pct(valueFor(props))} chance of a ${horizonLabel()}`, `Ймовірність ${horizonLabel()}: ${pct(valueFor(props))}`)}`;
  const pt = e.containerPoint;
  h.style.left = `${pt.x + 14}px`; h.style.top = `${pt.y + 10}px`; h.hidden = false;
}
function renderLegend(sel, title) {
  const steps = RAMP.map((c) => `<span style="flex:1;background:${c}"></span>`).join("");
  $(sel).innerHTML = `<div>${title || T("Chance of a new alert", "Ймовірність нової тривоги")}</div><div class="bar">${steps}</div>
    <div class="ticks"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
    <div class="keys"><span><i class="sw" style="background:${COL.permanent}"></i>${T("Permanent alert", "Постійна тривога")}</span>
    <span><i class="sw" style="background:${COL.nodata}"></i>${T("No forecast", "Прогнозу немає")}</span></div>`;
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
  if (!S.selected) { P.innerHTML = `<div class="empty">${T("Click a district or oblast on the map to see its forecast.", "Натисніть на район чи область на мапі, щоб побачити прогноз.")}</div>`; return; }
  const id = S.selected, lv = S.level, n = S.D.now[lv][id];
  const made = fDayTime.format(new Date(S.D.meta.forecast_time_utc));
  P.innerHTML = `<h2>${unitName(id)}</h2><div class="muted">${T(`${lv === "raion" ? "District" : "Oblast"} forecast, made ${made} Kyiv time`, `Прогноз для ${lv === "raion" ? "району" : "області"}, зроблено ${made} за Києвом`)}</div>
    <div class="tiles">
      <div class="tile"><div class="v">${pct(n.p1)}</div><div class="k">${T("new alert within 1 hour", "нова тривога протягом 1 години")}</div></div>
      <div class="tile"><div class="v">${pct(n.p3)}</div><div class="k">${T("new alert within 3 hours", "нова тривога протягом 3 годин")}</div></div>
      <div class="tile"><div class="v">${n.dur[0]}–${n.dur[1]} ${T("min", "хв")}</div><div class="k">${T("typical duration if one starts", "типова тривалість, якщо почнеться")}</div></div>
      <div class="tile"><div class="v">${pct(n.red)}</div><div class="k">${T(`chance it is <span class="chip red">red</span> rather than <span class="chip yellow">yellow</span>`, `ймовірність, що вона <span class="chip red">червона</span>, а не <span class="chip yellow">жовта</span>`)}</div></div>
    </div>
    <h3>${T("Next 24 hours (Kyiv time)", "Наступні 24 години (за Києвом)")}</h3><div class="cells" id="next24"></div>
    <div class="muted" style="margin-top:6px">${T(`About <b>${n.cnt[0]}–${n.cnt[1]}</b> alerts and <b>${n.hrs[0]}–${n.hrs[1]} h</b> under alert expected.`, `Очікується приблизно <b>${n.cnt[0]}–${n.cnt[1]}</b> тривог і <b>${n.hrs[0]}–${n.hrs[1]} год</b> під тривогою.`)}</div>
    <h3>${T("This week: chance of a new alert per 3-hour block", "Цей тиждень: ймовірність нової тривоги в кожному 3-годинному блоці")}</h3><div id="heat"></div>
    <h3>${T("Week-ahead strip", "Смуга на тиждень")}</h3><div id="wstrip"></div>
    <h3>${T("Last 7 days: actual alerts vs forecast", "Останні 7 днів: фактичні тривоги і прогноз")}</h3><div id="hstrip"></div>`;
  const starts = S.D.week.block_starts_utc.map((s) => new Date(s));
  const wk = S.D.week[lv][id];
  const c24 = $("#next24");
  n.next24.forEach((p, i) => c24.append(el("div", { className: "cell", title: T(`${pct(p)} chance of a new alert`, `${pct(p)} ймовірність нової тривоги`) },
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
    rect.onmousemove = (e) => showTip(e, `${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}<br><b>${pct(wk[i])}</b> ${T("chance of a new alert", "ймовірність нової тривоги")}`);
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
    r.onmousemove = (e) => showTip(e, `${fDay.format(s)} ${fHour.format(s)}<br><b>${pct(wk[i])}</b> ${T("chance of a new alert", "ймовірність нової тривоги")}`);
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
  lab(T("Actual alerts", "Фактичні тривоги"), 10); lab(T("Forecast: chance of a new alert within 3 h", "Прогноз: ймовірність нової тривоги протягом 3 год"), 46);
  u.alerts.forEach(([s, e, lvl]) => {
    const r = svgEl("rect", { x: x(s), y: 14, width: Math.max(1.5, x(e) - x(s)), height: 16, rx: 2, fill: COL[lvl] || COL.unknown });
    r.onmousemove = (ev) => showTip(ev, `${fDayTime.format(new Date(t0 + s * 6e4))} – ${fHour.format(new Date(t0 + e * 6e4))}<br>${lvl === "red" || lvl === "yellow" ? `<span class="chip ${lvl}">${lvlName(lvl)}</span>` : T("level not recorded", "рівень не зафіксовано")}`);
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
    showTip(e, `${fDayTime.format(new Date(t0 + h * 3600e3))}<br>${T(`forecast: <b>${u.pred[h]}%</b> chance of a new alert within 3 h`, `прогноз: <b>${u.pred[h]}%</b> ймовірність нової тривоги протягом 3 год`)}`);
  };
  hit.onmouseleave = () => (tip.hidden = true);
  svg.append(hit);
  host.append(svg);
  host.append(el("div", { className: "muted" }, `<span class="chip red">${lvlName("red")}</span> <span class="chip yellow">${lvlName("yellow")}</span> <i class="sw" style="background:${COL.unknown}"></i>${T("level not recorded (before 6 Sep)", "рівень не фіксувався (до 6 вересня)")}`));
}

// ---------- replay ----------
function initReplay() {
  const R = S.D.replay;
  S.rmap = L.map("rmap", { attributionControl: false, zoomSnap: 0.25, minZoom: 5, maxZoom: 9 });
  S.rlayer = L.geoJSON(S.geo, { style: () => ({ fillColor: COL.nodata, fillOpacity: 1, color: "#0e1726", weight: 0.6 }) }).addTo(S.rmap);
  S.rmap.fitBounds(S.rlayer.getBounds());
  renderLegend("#rlegend", T("Predicted chance of a new alert within 3 h", "Прогнозована ймовірність нової тривоги протягом 3 год"));
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
    $("#rtime").textContent = `${fDayTime.format(new Date(t0 + k * 3600e3))} ${T("(Kyiv time)", "(за Києвом)")}`;
    $("#rstats").innerHTML = `<div class="tile"><div class="v">${starts}</div><div class="k">${T("districts where an alert actually started in the next 3 h", "районів, де тривога справді почалася в наступні 3 год")}</div></div>
      <div class="tile"><div class="v">${starts ? Math.round((100 * hits) / starts) : 0}%</div><div class="k">${T("of those had a forecast of 50% or more", "з них мали прогноз 50% або більше")}</div></div>
      <div class="tile"><div class="v">${n ? (brier / n).toFixed(3) : "–"}</div><div class="k">${T("Brier score this hour (0 = perfect)", "Оцінка Брієра за цю годину (0 = ідеально)")}</div></div>`;
  };
  sl.oninput = () => draw(+sl.value);
  let timer = null;
  $("#rplay").onclick = () => {
    if (timer) { clearInterval(timer); timer = null; $("#rplay").textContent = T("▶ Play", "▶ Відтворити"); return; }
    $("#rplay").textContent = T("❚❚ Pause", "❚❚ Пауза");
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
  const M = S.D.metrics, F = M.full, LV = UK ? { raion: "Райони", oblast: "Області" } : { raion: "District", oblast: "Oblast" };
  const hTxt = (h) => T(`new alert within ${h} h`, `нова тривога протягом ${h} год`);
  const rows = (arr, cols) => arr.map((r) => `<tr>${cols.map(([k, f, num]) => `<td class="${num ? "num" : ""}">${f ? f(r[k]) : r[k]}</td>`).join("")}</tr>`).join("");
  const cov = M.range_coverage_validation_week;
  const lost = `<span class="lost">${T("lost", "програв")}</span>`;
  $("#quality").innerHTML = UK ? `<div class="docbody wide">
    <h2>Наскільки добре це працює?</h2>
    <p>Усе на цій сторінці виміряно на <b>тестовому періоді ${M.test_period[0]} – ${M.test_period[1]}</b>: чотирьох тижнях, яких не бачила
      жодна модель і жодне проєктне рішення. Кожну модель навчено лише на ранішніх даних, кожен прогноз використовував лише інформацію,
      доступну на свій момент, і тест запускали <b>один раз</b>. Усі рішення зафіксували до нього й нічого не змінювали після результатів,
      зокрема у двох місцях, де наша модель програла (позначено ${lost} нижче).</p>
    <p><b>AUC</b>: ймовірність, що випадкова година з новою тривогою отримала вищий прогноз, ніж випадкова година без неї (0,5 = вгадування,
      1 = ідеально). <b>Перевага (skill)</b>: наскільки менші помилки прогнозу (оцінка Брієра), ніж у простого правила «як часто тривога
      починалася в цю годину доби протягом останніх 14 днів» (0 = не краще, 0,3 = на 30% менші, нижче 0 = гірше). На графіках
      <span class="chip-b">синім</span> позначено метод, який використовує сайт, <span class="chip-g">сірим</span> — альтернативи.</p>
    <table><tr><th>Що прогнозуємо</th><th>Рівень</th><th class="num">AUC моделі</th><th class="num">AUC простого правила</th><th class="num">Перевага</th></tr>
      ${rows(M.headline.map((r) => ({ ...r, target: r.target.replace("New alert within", "Нова тривога протягом").replace("1h", "1 год").replace("3h", "3 год"),
        level: r.level === "District" ? "Район" : "Область" })), [["target"], ["level"], ["model_auc", f3, 1], ["baseline_auc", f3, 1], ["skill", f3, 1]])}</table>

    <h3>1. Наша модель проти простіших методів: чи почнеться нова тривога?</h3>
    <div class="seg" id="q-metric"><button data-m="ROC-AUC" class="on">AUC</button><button data-m="skill vs same-hour">Перевага</button></div>
    <p class="cap">LightGBM (наша модель) проти трьох простіших методів: правила за годиною доби, «інерції» (тривога ймовірна знову, якщо
      одна почалася протягом останніх годин) і логістичної регресії (проста лінійна модель). Більше — краще.</p>
    <div class="grid2" id="q-models"></div>

    <h3>2. Чи допомагає Telegram?</h3>
    <p class="cap">Та сама модель з додатковими даними з Telegram-каналів (@war_monitor: повідомлення про загрози; @kpszsu: Повітряні сили).
      Перевага; більше — краще. Telegram <b>не</b> використовується, бо програв на валідаційних тижнях до тесту. На тесті @war_monitor був трохи
      кращим на рівні областей і трохи гіршим на рівні районів; різниця менше 0,01 — у межах шуму.</p>
    <div class="grid2" id="q-tg"></div>

    <h3>3. Чи стабільна модель? По тижнях, вдень і вночі</h3>
    <p class="cap">Перевага 3-годинного прогнозу в кожному повному тестовому тижні та AUC за часом доби (за Києвом). Модель була корисною
      щотижня, вдень трохи краще.</p>
    <div class="grid2" id="q-stab"></div>

    <h3>4. Чи можна вірити відсоткам буквально? (калібрування)</h3>
    <p class="cap">Прогнози для районів на 3 години, згруповані за значенням прогнозу. Коли ми казали 40–50%, тривога починалася приблизно
      в 46% випадків. Точки на пунктирній лінії = ідеально.</p>
    <div id="calib"></div>

    <h3>5. Скільки триватиме тривога? (діапазони тривалості)</h3>
    <p class="cap">Ми показуємо діапазон «зазвичай X–Y хв» (25-й–75-й перцентиль). Добрий діапазон містить справжню тривалість приблизно
      в половині випадків (пунктирна лінія).</p>
    <div class="grid2" id="q-dur"></div>

    <h3>6. Наступні 24 години: скільки тривог і скільки годин під тривогою?</h3>
    <p class="cap">Середня похибка (менше — краще) порівняно з «як за останні 24 години» і «середнім за день за останні 7 днів».
      Години під тривогою: наша модель краща на 8%. Кількість тривог: ${lost}, середнє за 7 днів було на 4–8% кращим.
      Діапазони на мапі містили справжнє значення в ${pct(cov.raion.y_hours_24h.inside_25_75_range)} (години) і ${pct(cov.raion.y_count_24h.inside_25_75_range)} (кількість)
      випадків на останньому валідаційному тижні (ідеал — близько 50%).</p>
    <div class="grid2" id="q-24"></div>

    <h3>7. Коли саме протягом тижня? (3-годинні блоки)</h3>
    <p class="cap">AUC залежно від того, на скільки днів уперед прогноз. Сайт використовує <b>суміш</b>: нашу модель часу на найближчі
      години, яка до 3-го дня поступово переходить у «правило шаблону» (частка останніх 14 днів із тривогою в цьому блоці годин).
      Райони: суміш була найкращою в дні 1–3. Області: ${lost}, відсотки суміші на дні 1–2 були менш точними, ніж у правила шаблону
      (середня похибка ${f3(F.oblast.timing.brier_by_day["blend (chosen)"]["day 1"])} проти ${f3(F.oblast.timing.brier_by_day["pattern rule"]["day 1"])} у день 1), хоча блоки вона впорядковує так само добре.</p>
    <div class="grid2" id="q-time"></div>

    <h3>8. Червона чи жовта?</h3>
    <p class="cap">Якщо в районі починається тривога, вона червона (ракети, балістика) чи жовта (дрони)? Навчено на ${F.red.train.toLocaleString()} тривогах
      з 6 по 26 вересня, перевірено на ${F.red.test.toLocaleString()} тривогах з 27 вересня (${pct(F.red.red_share)} червоних). Найкраще працює просте правило
      «частка червоних тривог у цьому районі за останні 7 днів».</p>
    <div class="grid2" id="q-red"></div>
  </div>` : `<div class="docbody wide">
    <h2>How good is it?</h2>
    <p>Everything on this page was measured on the <b>test period ${M.test_period[0]} – ${M.test_period[1]}</b>: four weeks that no model and
      no design choice had seen. Every model was trained only on earlier data, every forecast used only information available at its
      time, and the test was run <b>once</b>. All choices were frozen before it, and nothing was changed after seeing the results, including
      the two places where our model lost (marked ${lost} below).</p>
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
      Hours under alert: our model wins by 8%. Number of alerts: ${lost}, the 7-day average was 4–8% better.
      The ranges shown on the map contained the true value ${pct(cov.raion.y_hours_24h.inside_25_75_range)} (hours) and ${pct(cov.raion.y_count_24h.inside_25_75_range)} (count) of the time
      in the last validation week (ideal about 50%).</p>
    <div class="grid2" id="q-24"></div>

    <h3>7. When in the coming week? (3-hour blocks)</h3>
    <p class="cap">AUC by how many days ahead. The site uses a <b>blend</b>: our timing model for the near term, fading into the "pattern rule"
      (share of the last 14 days with an alert in that clock block) by day 3. Districts: the blend was best on days 1–3.
      Oblasts: ${lost}, the blend's percentages for days 1–2 were less accurate than the pattern rule's
      (average error ${f3(F.oblast.timing.brier_by_day["blend (chosen)"]["day 1"])} vs ${f3(F.oblast.timing.brier_by_day["pattern rule"]["day 1"])} on day 1), although it ranks blocks equally well.</p>
    <div class="grid2" id="q-time"></div>

    <h3>8. Red or yellow?</h3>
    <p class="cap">If an alert starts in a district, is it red (missiles, ballistic) or yellow (drones)? Trained on ${F.red.train.toLocaleString()} alerts
      from 6–26 Sep, tested on ${F.red.test.toLocaleString()} alerts from 27 Sep (${pct(F.red.red_share)} red). The simple rule
      "this district's red share in the last 7 days" works best.</p>
    <div class="grid2" id="q-red"></div>
  </div>`;

  const MODELS = [["baseline: same hour, last 14 days", T("Clock-hour rule", "Правило години доби")], ["baseline: persistence", T("Persistence", "Інерція")],
    ["logistic regression", T("Logistic regression", "Логістична регресія")], ["LightGBM (chosen)", T("LightGBM (ours)", "LightGBM (наша)")]];
  const drawModels = (metric) => {
    const host = $("#q-models"); host.innerHTML = "";
    for (const lv of ["raion", "oblast"]) for (const h of [1, 3]) {
      const tb = F[lv][`start_${h}h`].table;
      hbars(host, `${LV[lv]}, ${hTxt(h)}`, MODELS.map(([k, lab]) => ({ label: lab, v: tb[k][metric], chosen: k.includes("chosen") })),
        metric === "ROC-AUC" ? { min: 0.5, max: 0.9 } : { min: -0.2, max: 0.5 });
    }
  };
  drawModels("ROC-AUC");
  document.querySelectorAll("#q-metric button").forEach((b) => (b.onclick = () => {
    document.querySelectorAll("#q-metric button").forEach((x) => x.classList.toggle("on", x === b)); drawModels(b.dataset.m);
  }));

  for (const lv of ["raion", "oblast"]) for (const h of [1, 3]) {
    const tb = F[lv][`start_${h}h`].table, k = "skill vs same-hour";
    hbars($("#q-tg"), `${LV[lv]}, ${hTxt(h)}`, [
      { label: T("No Telegram (used)", "Без Telegram (використано)"), v: tb["LightGBM (chosen)"][k], chosen: true },
      { label: "+ @war_monitor", v: tb["LightGBM + @war_monitor"][k] }, { label: "+ @kpszsu", v: tb["LightGBM + @kpszsu"][k] }],
    { min: 0, max: 0.5 });
  }
  for (const lv of ["raion", "oblast"]) {
    const wk = F[lv].start_3h.weeks;
    hbars($("#q-stab"), T(`${LV[lv]}: skill by test week (3 h)`, `${LV[lv]}: перевага по тестових тижнях (3 год)`), ["week 1", "week 2", "week 3", "week 4"].map((w) => ({ label: T(w[0].toUpperCase() + w.slice(1), `Тиждень ${w.slice(5)}`), v: wk[w]["skill vs same-hour"], chosen: true })),
      { min: 0, max: 0.6, note: T("A fifth, partial week (the last 10 hours of data) is left out.", "П'ятий неповний тиждень (останні 10 годин даних) не показано.") });
  }
  for (const lv of ["raion", "oblast"]) {
    const dn = F[lv].start_3h.day_night;
    hbars($("#q-stab"), T(`${LV[lv]}: AUC by time of day (3 h)`, `${LV[lv]}: AUC за часом доби (3 год)`), [{ label: T("Day (06–22)", "День (06–22)"), v: dn["day (06-22 Kyiv)"]["ROC-AUC"], chosen: true },
      { label: T("Night (22–06)", "Ніч (22–06)"), v: dn["night (22-06 Kyiv)"]["ROC-AUC"], chosen: true }], { min: 0.5, max: 0.9 });
  }
  drawCalibration($("#calib"), M.calibration);
  for (const lv of ["raion", "oblast"]) {
    const d = F[lv].duration, k = "true duration inside the 25-75% range", wk = "average range width (min)";
    hbars($("#q-dur"), T(`${LV[lv]}: true duration inside the range`, `${LV[lv]}: справжня тривалість у межах діапазону`), [
      { label: T("Last 10 alerts (rule)", "Останні 10 тривог (правило)"), v: d["baseline: last 10 alerts"][k], tip: T(`average range width ${Math.round(d["baseline: last 10 alerts"][wk])} min`, `середня ширина діапазону ${Math.round(d["baseline: last 10 alerts"][wk])} хв`) },
      { label: T("LightGBM (ours)", "LightGBM (наша)"), v: d["LightGBM quantiles (chosen)"][k], chosen: true, tip: T(`average range width ${Math.round(d["LightGBM quantiles (chosen)"][wk])} min`, `середня ширина діапазону ${Math.round(d["LightGBM quantiles (chosen)"][wk])} хв`) }],
    { fmt: pct, min: 0, max: 0.7, ref: { v: 0.5, label: T("ideal", "ідеал") } });
  }
  const R24 = [["baseline: same as last 24h", T("Same as last 24 h", "Як за останні 24 год")], ["baseline: daily average of last 7 days", T("7-day average", "Середнє за 7 днів")], ["LightGBM (chosen)", T("LightGBM (ours)", "LightGBM (наша)")]];
  for (const [tg, name, unit] of [["hours", T("hours under alert", "години під тривогою"), "h"], ["count", T("number of alerts", "кількість тривог"), ""]]) for (const lv of ["raion", "oblast"]) {
    const t = F[lv].next24h[tg];
    hbars($("#q-24"), `${LV[lv]}: ${name}, ${T("average miss", "середня похибка")}${unit ? T(" (h)", " (год)") : ""}`, R24.map(([k, lab]) => ({ label: lab, v: t[k].MAE, chosen: k.includes("chosen") })),
      { fmt: f2, min: 0, max: 2.5 });
  }
  const days = ["day 1", "day 2", "day 3", "day 4", "day 5", "day 6", "day 7"];
  for (const lv of ["raion", "oblast"]) {
    const a = F[lv].timing.auc_by_day;
    lchart($("#q-time"), T(`${LV[lv]}: AUC by days ahead`, `${LV[lv]}: AUC залежно від днів уперед`), days.map((d) => d.replace("day ", T("Day ", "День "))), [
      { name: T("Blend (used)", "Суміш (використано)"), short: T("Blend", "Суміш"), color: CH.chosen, vals: days.map((d) => a["blend (chosen)"][d]) },
      { name: T("Pattern rule", "Правило шаблону"), short: T("Pattern", "Шаблон"), color: CH.s2, vals: days.map((d) => a["pattern rule"][d]) },
      { name: T("Timing model alone", "Лише модель часу"), short: T("Model", "Модель"), color: CH.s3, vals: days.map((d) => a["timing model alone"][d]) }],
    { min: 0.78, max: 0.84 });
  }
  const rt = F.red.table;
  hbars($("#q-red"), T("Red vs yellow: AUC", "Червона чи жовта: AUC"), [["baseline: overall red share", T("Always the average share", "Завжди середня частка")], ["baseline: previous alert's level", T("Previous alert's level", "Рівень попередньої тривоги")],
    ["logistic, 5 level features", T("Logistic regression", "Логістична регресія")], ["raion red share last 7 days (chosen)", T("Red share, last 7 days", "Частка червоних за 7 днів")]]
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
    d.onmousemove = (e) => showTip(e, T(`forecast ${c.bin}: alerts started in <b>${pct(c.observed)}</b> of ${c.rows.toLocaleString()} cases`, `прогноз ${c.bin}: тривога почалася в <b>${pct(c.observed)}</b> з ${c.rows.toLocaleString()} випадків`));
    d.onmouseleave = () => (tip.hidden = true);
    svg.append(d);
  });
  const lx = svgEl("text", { x: sx(0.3), y: H - 4 }); lx.textContent = T("forecast probability", "прогнозована ймовірність"); svg.append(lx);
  const ly = svgEl("text", { x: sx(0.02), y: 12 }); ly.textContent = T("share of cases with a new alert (dashed = perfect)", "частка випадків з новою тривогою (пунктир = ідеально)"); svg.append(ly);
  host.append(svg);
}

// ---------- forecast check: saved forecasts vs what happened ----------
function initCheck() {
  const C = S.D.check, M = S.D.meta;
  const snapLabel = (sn) => `${fDayTime.format(new Date(sn.forecast_time_utc))} ${T("(Kyiv)", "(за Києвом)")}`;
  const opts = (lv) => Object.keys(M.units[lv]).sort((a, b) => unitName(a, lv).localeCompare(unitName(b, lv)))
    .map((id) => `<option value="${lv}|${id}">${unitName(id, lv)}</option>`).join("");
  $("#check").innerHTML = `<div class="docbody wide">
    <h2>${T("Forecast check: did the forecast come true?", "Перевірка прогнозу: чи справдився прогноз?")}</h2>
    <p>${T(`Every forecast this site publishes is saved. Once the next 24 hours have passed, it is compared here with what really
      happened: did a new alert start in each 3-hour block, how many alerts were there, and how many hours under alert.
      The saved forecast is never changed afterwards. Data for the check: up to ${fDayTime.format(new Date(C.data_until_utc))} (Kyiv).`,
      `Кожен прогноз, який публікує сайт, зберігається. Коли минають наступні 24 години, тут його порівнюють з тим, що сталося насправді:
      чи почалася нова тривога в кожному 3-годинному блоці, скільки було тривог і скільки годин під тривогою. Збережений прогноз
      потім ніколи не змінюється. Дані для перевірки: до ${fDayTime.format(new Date(C.data_until_utc))} (за Києвом).`)}</p>
    <div class="ctrl-row"><label>${T("Forecast made at", "Прогноз зроблено")} <select id="ck-snap">${C.snapshots.map((sn, i) => `<option value="${i}">${snapLabel(sn)}</option>`).join("")}</select></label>
      <label>${T("Add a place", "Додати місце")} <select id="ck-unit"><option value="">${T("choose…", "оберіть…")}</option><optgroup label="${T("Districts", "Райони")}">${opts("raion")}</optgroup><optgroup label="${T("Oblasts", "Області")}">${opts("oblast")}</optgroup></select></label></div>
    <div id="ck-summary"></div><div class="grid2" id="ck-cards"></div></div>`;
  let extra = null;
  const draw = () => {
    const sn = C.snapshots[+$("#ck-snap").value];
    const sm = sn.summary_raion, so = sn.summary_oblast;
    const known = sm.blocks_known > 0;
    $("#ck-summary").innerHTML = known ? `<div class="tiles four">
        <div class="tile"><div class="v">${pct(sm.avg_forecast_alert_blocks)} vs ${pct(sm.avg_forecast_quiet_blocks)}</div><div class="k">${T("all districts: average forecast for 3-hour blocks where an alert started vs blocks without one", "усі райони: середній прогноз для 3-годинних блоків, де тривога почалася, проти блоків без неї")}</div></div>
        <div class="tile"><div class="v">${f3(sm.auc)}</div><div class="k">${T(`AUC over ${sm.blocks_known.toLocaleString()} district blocks (oblasts: ${f3(so.auc)})`, `AUC по ${sm.blocks_known.toLocaleString()} блоках районів (області: ${f3(so.auc)})`)}</div></div>
        <div class="tile"><div class="v">${sm.count_inside_range == null ? "–" : pct(sm.count_inside_range)}</div><div class="k">${T("districts where the number of alerts fell inside the forecast range", "районів, де кількість тривог потрапила в прогнозний діапазон")}</div></div>
        <div class="tile"><div class="v">${sm.hours_inside_range == null ? "–" : pct(sm.hours_inside_range)}</div><div class="k">${T("districts where the hours under alert fell inside the forecast range", "районів, де години під тривогою потрапили в прогнозний діапазон")}</div></div></div>`
      : `<p class="cap">${T("<b>Not checkable yet:</b> the 24 hours after this forecast have not passed in the data. The page fills in as new data arrives.", "<b>Поки не можна перевірити:</b> 24 години після цього прогнозу ще не минули в даних. Сторінка заповниться, щойно надійдуть нові дані.")}</p>`;
    const host = $("#ck-cards"); host.innerHTML = "";
    const list = C.featured.map((id) => ["raion", id]);
    if (extra) list.push(extra);
    list.forEach(([lv, id]) => checkCard(host, sn, lv, id));
  };
  const first = C.snapshots.findIndex((sn) => sn.summary_raion.blocks_known > 0);  // open on the latest checkable forecast
  if (first >= 0) $("#ck-snap").value = String(first);
  $("#ck-snap").onchange = draw;
  $("#ck-unit").onchange = (e) => { extra = e.target.value ? e.target.value.split(/\|(.*)/s).slice(0, 2) : null; draw(); };
  draw();
}
function checkCard(host, sn, lv, id) {
  const u = sn[lv][id]; if (!u) return;
  const t0 = new Date(sn.forecast_time_utc).getTime();
  const box = el("div", { className: "chart" }, `<div class="ctitle">${unitName(id, lv)}</div>`);
  const cells = el("div", { className: "cells ck" });
  sn.block_starts_utc.forEach((b, i) => {
    const p = u.next24[i], y = u.actual_blocks[i];
    const mark = y == null ? `<span class="ckm unk">${T("not yet", "ще ні")}</span>` : y ? `<span class="ckm yes">${T("alert", "тривога")}</span>` : `<span class="ckm no">${T("quiet", "тихо")}</span>`;
    const c = el("div", { className: "cell" }, `${fHour.format(new Date(b))}<b>${pct(p)}</b>`);
    c.style.background = rampColor(p); c.style.color = textOn(p);
    const w = el("div", { className: "ckcol" }); w.append(c); w.append(el("div", {}, mark)); cells.append(w);
  });
  box.append(el("div", { className: "cnote" }, T("Forecast: chance of a new alert in each 3-hour block (Kyiv time). Below: what happened.", "Прогноз: ймовірність нової тривоги в кожному 3-годинному блоці (за Києвом). Нижче: що сталося.")));
  box.append(cells);
  // 24 h timeline of the actual alerts
  const W = 400, svg = svgEl("svg", { width: W, height: 34 }), x = (m) => (m / 1440) * W;
  svg.append(svgEl("rect", { x: 0, y: 6, width: W, height: 16, rx: 3, fill: "#152238", stroke: "#2b3d5c" }));
  u.alerts.forEach(([s, e, lvl]) => {
    const r = svgEl("rect", { x: x(s), y: 6, width: Math.max(1.5, x(e) - x(s)), height: 16, rx: 2, fill: COL[lvl] || COL.unknown });
    r.onmousemove = (ev) => showTip(ev, `${fDayTime.format(new Date(t0 + s * 6e4))} – ${fHour.format(new Date(t0 + e * 6e4))}${lvl === "red" || lvl === "yellow" ? `<br><span class="chip ${lvl}">${lvlName(lvl)}</span>` : ""}`);
    r.onmouseleave = () => (tip.hidden = true);
    svg.append(r);
  });
  const known = (new Date(sn.known_until_utc).getTime() - t0) / 6e4;
  if (known < 1440) svg.append(svgEl("rect", { x: x(known), y: 6, width: W - x(known), height: 16, fill: "#3a3f47", opacity: 0.85 }));  // not known yet
  const lab = svgEl("text", { x: 0, y: 33 }); lab.textContent = T("actual alerts in the 24 hours after the forecast", "фактичні тривоги за 24 години після прогнозу"); svg.append(lab);
  box.append(svg);
  const ok = (v, r) => (v == null ? `<span class="ckm unk">${T("not yet known", "ще невідомо")}</span>` : v >= r[0] && v <= r[1] ? `<span class="ckm yes2">${T("inside the range", "у діапазоні")}</span>` : `<span class="ckm out">${T("outside the range", "поза діапазоном")}</span>`);
  const hU = T("h", "год");
  box.append(el("div", { className: "tiles" }, `
    <div class="tile"><div class="v">${u.cnt[0]}–${u.cnt[1]} → ${u.actual_cnt ?? "?"}</div><div class="k">${T("alerts: forecast range → actual", "тривоги: прогнозний діапазон → факт")} · ${ok(u.actual_cnt, u.cnt)}</div></div>
    <div class="tile"><div class="v">${u.hrs[0]}–${u.hrs[1]} ${hU} → ${u.actual_hrs ?? "?"} ${hU}</div><div class="k">${T("hours under alert", "години під тривогою")} · ${ok(u.actual_hrs, u.hrs)}</div></div>`));
  host.append(box);
}

load().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<pre style="color:#f88">Failed to load data: ${e}</pre>`); console.error(e); });
