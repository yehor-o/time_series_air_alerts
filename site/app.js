// Time-Series Air Alert Forecast, Ukraine (demo) — static front end.
// Reads site/data/*.json (written by scripts/export_site.py) and draws everything client-side.
"use strict";

const RAMP = ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5",
  "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6", "#cde2fb"]; // sequential blue, low -> high
// design theme: ?theme=<name> (remembered), else the default; colours below follow the CSS variables of the theme
(() => {
  const q = new URLSearchParams(location.search).get("theme");
  let th = q;
  try { if (q) localStorage.setItem("theme", q); else th = localStorage.getItem("theme"); } catch (e) { /* storage blocked */ }
  th = th || "noir";  // default design: Editorial Dark
  if (th !== "classic") document.documentElement.dataset.theme = th;
})();
const cv = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const V = { bg: cv("--bg"), surface: cv("--surface"), line: cv("--line"), text: cv("--text-primary"), ink: cv("--text-secondary"), muted: cv("--text-muted") };
const COL = { red: "#d03b3b", yellow: "#f2c230", unknown: V.muted, nodata: cv("--nodata"), permanent: cv("--permanent"), on: "#ff4b45" };
const CONT_H = 24;  // an alert running at least this long is shown as "continuous": a new-alert forecast means nothing there
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
  S.tF = new Date(S.D.meta.forecast_time_utc);                        // the hourly forecast (1 h, 3 h, duration, 24 h, red)
  S.tW = new Date(S.D.meta.week_time_utc || S.D.meta.forecast_time_utc);  // the 3-hour blocks (made at 00:00 / 12:00 Kyiv)
  buildInfo();
  applyStaticI18n();
  if (S.D.meta.sample) $("#sample-banner").hidden = false;
  $("#asof").textContent = T(`Forecast made at ${fDayTime.format(S.tF)} (Kyiv time) · data up to ${fDayTime.format(new Date(S.D.meta.data_until_utc))}`,
    `Прогноз зроблено ${fDayTime.format(S.tF)} (за Києвом) · дані до ${fDayTime.format(new Date(S.D.meta.data_until_utc))}`);
  if (+S.tW !== +S.tF) $("#asof").textContent += T(` · 3-hour blocks from ${fHour.format(S.tW)}`, ` · 3-годинні блоки від ${fHour.format(S.tW)}`);
  const trained = S.D.meta.models_trained_utc ? fDayTime.format(new Date(S.D.meta.models_trained_utc)) : "–";
  document.querySelectorAll(".about-trained").forEach((e) => (e.textContent = trained));
  initTabs(); initMap(); initControls(); renderLegend("#legend", null, true); renderTopRisk(); initReplay(); renderQuality(); initCheck();
  // the rolling log of the site's own hourly forecasts: tells which hours of the history strip have no saved forecast.
  // Loaded after the page is drawn (it grows to a few hundred kB); an open panel redraws its history strip when it arrives.
  fetch("data/p3_log.json").then((r) => r.json()).then((j) => { S.D.p3log = j; if (S.selected && $("#hstrip")) drawPanelHistory(); }).catch(() => {});
}

// ---------- per unit: the alert running at the forecast moment, and the evidence behind the red share ----------
// Both come from history.json (the 7 days before the forecast moment t, same t as now.json). An alert still running at t
// is drawn up to t, so "end == t" means "still active"; its real end is not known and not used.
function buildInfo() {
  const H = S.D.history, end = H.hours * 60, h0 = new Date(H.start_utc).getTime();
  S.info = {}; S.nat = {};
  for (const lv of ["raion", "oblast"]) {
    S.info[lv] = {};
    let red = 0, all = 0;
    for (const [id, n] of Object.entries(S.D.now[lv])) {
      const al = H[lv]?.[id]?.alerts || [];
      const run = al.find(([, e]) => e >= end);
      const active = n.active != null ? n.active > 0 : !!run;
      // alerts that started inside the 7 days (s > 0; s = 0 means it started earlier) with a known level: the red-share rule's input
      const lv7 = al.filter(([s, , l]) => s > 0 && (l === "red" || l === "yellow"));
      const nRed = lv7.filter(([, , l]) => l === "red").length;
      red += nRed; all += lv7.length;
      S.info[lv][id] = {
        active,
        since: active && run && run[0] > 0 ? new Date(h0 + run[0] * 6e4) : null,
        week: !!(active && run && run[0] === 0),  // started before the 7-day window: running for 7+ days
        continuous: !!(active && run && end - run[0] >= CONT_H * 60),
        nRed, nLvl: lv7.length,
      };
    }
    S.nat[lv] = all ? red / all : null;  // national share over the same 7 days (the rule's fallback)
  }
}
const info = (id, lv = S.level) => S.info?.[lv]?.[id] || {};
const sameDay = (d) => fDay.format(d) === fDay.format(S.tF);
function onTxt(i) {  // "Under alert since 21:14"
  if (!i.since) return T("Under alert now", "Зараз триває тривога");
  const at = sameDay(i.since) ? fHour.format(i.since) : fDayTime.format(i.since);
  return T(`Under alert since ${at}`, `Тривога триває з ${at}`);
}
function contTxt(i) {  // "Continuous alert for 7+ days"
  if (i.week) return T("Continuous alert for 7+ days", "Безперервна тривога понад 7 днів");
  return T(`Continuous alert since ${fDayTime.format(i.since)}`, `Безперервна тривога з ${fDayTime.format(i.since)}`);
}
function onShort(i) {  // short forms for the Major-cities card
  if (i.continuous) return i.week ? T("alert for 7+ days", "тривога понад 7 днів") : T(`alert since ${fDay.format(i.since)}`, `тривога з ${fDay.format(i.since)}`);
  return i.since ? T(`alert since ${fHour.format(i.since)}`, `тривога з ${fHour.format(i.since)}`) : T("under alert now", "зараз тривога");
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
  const late = s < S.tF ? T(" (block already started)", " (блок уже почався)") : "";
  return T(`new alert in ${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}${late}`,
    `нової тривоги ${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}${late}`);
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
  const fill = info(unitKey(props)).continuous ? COL.permanent : rampColor(value);  // continuous alert: no forecast colour
  const oblastView = S.level === "oblast";
  return { fillColor: fill, fillOpacity: 1, color: selected ? V.text : (oblastView ? fill : V.bg),
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
  // "under alert now": red stripes drawn over the forecast colour by a second, non-clickable copy of the shapes
  S.over = new Map();
  S.olayer = L.geoJSON(S.geo, { interactive: false, style: () => ({ stroke: false, fillColor: "url(#on-hatch)", fillOpacity: 0 }) }).addTo(S.map);
  S.olayer.eachLayer((l) => S.over.set(l.feature, l));
  restyle();
  S.map.fitBounds(S.layer.getBounds(), { paddingTopLeft: [0, 60] });
  const svg = S.map.getPanes().overlayPane.querySelector("svg");  // exists only once the map has a view
  if (svg) {
    const defs = svgEl("defs", {}), pat = svgEl("pattern", { id: "on-hatch", patternUnits: "userSpaceOnUse", width: 7, height: 7, patternTransform: "rotate(45)" });
    pat.append(svgEl("rect", { x: 0, y: 0, width: 2.4, height: 7, fill: COL.on }));
    defs.append(pat); svg.prepend(defs);
  }
}
// Major cities: the district (or oblast) that contains each city; forecasts are per district.
const CITIES = [
  { en: "Kyiv", uk: "Київ", raion: "м. Київ|м. Київ", oblast: "м. Київ" },
  { en: "Lviv", uk: "Львів", raion: "Львівська область|Львівський район", oblast: "Львівська область" },
  { en: "Kharkiv", uk: "Харків", raion: "Харківська область|Харківський район", oblast: "Харківська область" },
  { en: "Odesa", uk: "Одеса", raion: "Одеська область|Одеський район", oblast: "Одеська область" },
];
function renderTopRisk() {
  let box = $("#toprisk");
  if (!box) { box = el("div", { id: "toprisk", className: "toprisk" }); $("#page-map .mapwrap").append(box); }
  const lv = S.level, n = S.D.now[lv];
  box.innerHTML = `<div class="tt"><span>${T("Major cities: chance of a new alert", "Великі міста: ймовірність нової тривоги")}</span><span class="cols"><i>1 ${T("h", "год")}</i><i>3 ${T("h", "год")}</i></span></div>` +
    CITIES.filter((c) => n[c[lv]]).map((c) => {
      const id = c[lv], sub = id.startsWith("м. ") ? "" : `<small>${unitName(id, lv).split(", ")[0]}</small>`;
      const vals = info(id, lv).active ? `<span class="now-on">${onShort(info(id, lv))}</span>` : `<b>${pct(n[id].p1)}</b><b>${pct(n[id].p3)}</b>`;
      return `<button data-id="${id}"><span>${T(c.en, c.uk)}${sub}</span><span class="cols">${vals}</span></button>`;
    }).join("");
  box.querySelectorAll("button").forEach((b) => (b.onclick = () => select(b.dataset.id)));
}
function restyle() {
  const sel = [];
  S.layer.eachLayer((l) => {
    const p = l.feature.properties;
    const s = p.status === "forecast" && S.selected && unitKey(p) === S.selected;
    l.setStyle(styleFor(p, valueFor(p), s));
    // stripes: always for a continuous alert (no forecast there); for a short one only in the 1 h / 3 h views ("now")
    const i = p.status === "forecast" ? info(unitKey(p)) : {};
    S.over?.get(l.feature)?.setStyle({ fillOpacity: i.continuous ? 0.9 : i.active && S.h !== "block" ? 0.75 : 0 });
    if (s) { l.bringToFront(); sel.push(l); }
  });
  sel.forEach((l) => S.over?.get(l.feature)?.bringToFront());  // keep the stripes above the selected outline's fill
}
const hatch = (base) => `background:repeating-linear-gradient(135deg,${COL.on} 0 2px,transparent 2px 5px),${base}`;
function showHover(e, props) {
  const h = $("#hover");
  const nm = UK ? props.name_uk : props.name;
  if (props.status === "permanent") h.innerHTML = `<b>${nm}</b><br>${T("Permanent alert, no forecast", "Постійна тривога, прогнозу немає")}`;
  else if (props.status !== "forecast") h.innerHTML = `<b>${nm}</b><br>${T("No forecast", "Прогнозу немає")}`;
  else {
    const i = info(unitKey(props)), name = `<b>${unitName(unitKey(props))}</b>`;
    if (i.continuous) h.innerHTML = `${name}<br><span class="now-on">${contTxt(i)}</span><br>${T("No forecast: a new alert cannot start while this one runs.", "Прогнозу немає: нова тривога не може початися, поки триває ця.")}`;
    else h.innerHTML = `${name}${i.active ? `<br><span class="now-on">${onTxt(i)}</span>` : ""}<br>${T(`${pct(valueFor(props))} chance of a ${horizonLabel()}`, `Ймовірність ${horizonLabel()}: ${pct(valueFor(props))}`)}${i.active ? T(", after the current alert ends", ", після завершення поточної") : ""}`;
  }
  const pt = e.containerPoint;
  h.style.left = `${pt.x + 14}px`; h.style.top = `${pt.y + 10}px`; h.hidden = false;
}
function renderLegend(sel, title, live = false) {
  const steps = RAMP.map((c) => `<span style="flex:1;background:${c}"></span>`).join("");
  // live: the main map's keys; "block" = the time-block view, where short alerts are not striped
  const on = live ? `${live !== "block" ? `<span><i class="sw" style="${hatch(RAMP[6])}"></i>${T("Under alert now", "Зараз тривога")}</span>` : ""}
    <span><i class="sw" style="${hatch(COL.permanent)}"></i>${T(`Continuous alert (${CONT_H} h+)`, `Безперервна тривога (${CONT_H}+ год)`)}</span>` : "";
  $(sel).innerHTML = `<div>${title || T("Chance of a new alert", "Ймовірність нової тривоги")}</div><div class="bar">${steps}</div>
    <div class="ticks"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
    <div class="keys">${on}<span><i class="sw" style="background:${COL.permanent}"></i>${T("Permanent alert", "Постійна тривога")}</span>
    <span><i class="sw" style="background:${COL.nodata}"></i>${T("No forecast", "Прогнозу немає")}</span></div>`;
}

// ---------- controls ----------
function initControls() {
  document.querySelectorAll("[data-level]").forEach((b) => b.onclick = () => {
    document.querySelectorAll("[data-level]").forEach((x) => x.classList.toggle("on", x === b));
    S.level = b.dataset.level; S.selected = null; restyle(); renderPanel(); renderTopRisk();
  });
  document.querySelectorAll("[data-h]").forEach((b) => b.onclick = () => {
    document.querySelectorAll("[data-h]").forEach((x) => x.classList.toggle("on", x === b));
    S.h = b.dataset.h; $("#blockpicker").hidden = S.h !== "block"; restyle(); renderLegend("#legend", null, S.h === "block" ? "block" : true);
  });
  const starts = S.D.week.block_starts_utc.map((s) => new Date(s));
  const days = [...new Set(starts.map((d) => fDay.format(d)))];
  const dp = $("#daypick"), bp = $("#blockpick");
  const late = T("Started before this forecast: for the next hours, the 1 h / 3 h forecast is newer",
    "Почався до цього прогнозу: на найближчі години новіший прогноз на 1 / 3 год");
  const drawBlocks = (day) => {
    bp.innerHTML = "";
    starts.forEach((d, i) => {
      if (fDay.format(d) !== day) return;
      const b = el("button", { className: (i === S.block ? "on" : "") + (d < S.tF ? " past" : "") }, `${fHour.format(d)}`);
      if (d < S.tF) b.title = late;
      b.onclick = () => { S.block = i; drawBlocks(day); restyle(); };
      bp.append(b);
    });
  };
  S.block = Math.max(0, starts.findIndex((d) => d >= S.tF));  // open on the first block that has not started yet
  const day0 = fDay.format(starts[S.block]);
  days.forEach((day) => {
    const b = el("button", { className: day === day0 ? "on" : "" }, day);
    b.onclick = () => {
      dp.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
      const k = starts.findIndex((d) => fDay.format(d) === day && d >= S.tF);
      S.block = k >= 0 ? k : starts.findIndex((d) => fDay.format(d) === day); drawBlocks(day); restyle();
    };
    dp.append(b);
  });
  drawBlocks(day0);
}

// ---------- side panel ----------
function select(id) { S.selected = id; restyle(); renderPanel(); }
// red tile: the rule is "share of red among this unit's alerts in the last 7 days" (D35); show the evidence it rests on,
// and never a bare 0% / 100% from a handful of alerts
function redTile(n, i, lv) {
  const chip = T(`<span class="chip red">red</span>`, `<span class="chip red">червона</span>`);
  if (i.nLvl == null) return [pct(n.red), T(`chance it is ${chip}`, `шанс, що ${chip}`)];
  if (!i.nLvl) return [pct(n.red), T(`chance it is ${chip} · no alerts here in 7 days, so the national share`, `шанс, що ${chip} · тут не було тривог за 7 днів, тож частка по країні`)];
  if (i.nRed === 0 || i.nRed === i.nLvl) return [`${i.nRed} ${T("of", "з")} ${i.nLvl}`,
    T(`alerts here in 7 days were <span class="chip red">red</span>; nationally ${pct(S.nat[lv])}`, `тривог тут за 7 днів були <span class="chip red">червоними</span>; по країні ${pct(S.nat[lv])}`)];
  return [pct(n.red), T(`chance it is ${chip} · ${i.nRed} of ${i.nLvl} alerts here in 7 days`, `шанс, що ${chip} · ${i.nRed} з ${i.nLvl} тривог тут за 7 днів`)];
}
function renderPanel() {
  const P = $("#panel");
  if (!S.selected) { P.innerHTML = `<div class="empty">${T("Click a district or oblast on the map to see its forecast.", "Натисніть на район чи область на мапі, щоб побачити прогноз.")}</div>`; return; }
  const id = S.selected, lv = S.level, n = S.D.now[lv][id], i = info(id, lv);
  const made = fDayTime.format(S.tF), unitW = lv === "raion" ? T("district", "районі") : T("oblast", "області");
  const head = `<h2>${unitName(id)}</h2><div class="muted">${T(`${lv === "raion" ? "District" : "Oblast"} forecast, made ${made} Kyiv time`, `Прогноз для ${lv === "raion" ? "району" : "області"}, зроблено ${made} за Києвом`)}</div>`;
  const hist = `<h3>${T("Last 7 days: actual alerts vs forecast", "Останні 7 днів: фактичні тривоги і прогноз")}</h3><div id="hstrip"></div>`;
  if (i.continuous) {  // a new-alert forecast means nothing while one alert runs for days: show none
    P.innerHTML = `${head}<div class="now-on big">${contTxt(i)}</div>
      <p class="note">${T(`One alert has been running here for ${CONT_H} hours or more. This can happen when a front-line or border community inside the ${unitW} keeps the alert on. A new alert cannot start while it runs, so no forecast is shown.`,
        `Одна тривога триває тут ${CONT_H} годин або довше. Так буває, коли прифронтова чи прикордонна громада в ${unitW} тримає тривогу. Поки вона триває, нова тривога не може початися, тому прогноз не показано.`)}</p>${hist}`;
    drawPanelHistory();
    return;
  }
  const [rv, rk] = redTile(n, i, lv);
  const older = +S.tW !== +S.tF, wMade = fHour.format(S.tW);
  P.innerHTML = `${head}
    ${i.active ? `<div class="now-on big">${onTxt(i)} ${T("(Kyiv time). The chances below are for a new alert after this one ends.", "(за Києвом). Ймовірності нижче стосуються нової тривоги після завершення цієї.")}</div>` : ""}
    <h3>${T("Right now · updated every hour", "Зараз · оновлюється щогодини")}</h3>
    <div class="hero"><div class="hero-v">${pct(n.p3)}</div>
      <div class="hero-k">${T("chance of a new alert in the next 3 hours", "ймовірність нової тривоги протягом наступних 3 годин")}</div>
      <div class="hero-bar"><span style="width:${Math.round(n.p3 * 100)}%"></span></div></div>
    <div class="tiles three">
      <div class="tile"><div class="v">${pct(n.p1)}</div><div class="k">${T("within 1 hour", "протягом 1 години")}</div></div>
      <div class="tile"><div class="v">${n.dur[0]}–${n.dur[1]} ${T("min", "хв")}</div><div class="k">${T("typical duration", "типова тривалість")}</div></div>
      <div class="tile" title="${T("Rule: the share of red among this place's alerts in the last 7 days. With only a few alerts it is a rough guide.", "Правило: частка червоних серед тривог тут за останні 7 днів. Якщо тривог мало, це лише грубий орієнтир.")}"><div class="v">${rv}</div><div class="k">${rk}</div></div>
    </div>
    <div class="muted" style="margin-top:8px">${T(`Next 24 hours (from ${fHour.format(S.tF)}): about <b>${n.cnt[0]}–${n.cnt[1]}</b> alerts and <b>${n.hrs[0]}–${n.hrs[1]} h</b> under alert expected.`, `Наступні 24 години (від ${fHour.format(S.tF)}): очікується приблизно <b>${n.cnt[0]}–${n.cnt[1]}</b> тривог і <b>${n.hrs[0]}–${n.hrs[1]} год</b> під тривогою.`)}</div>
    <h3>${T("Outlook: next 24 hours by 3-hour block (Kyiv time)", "Огляд: наступні 24 години по 3-годинних блоках (за Києвом)")}</h3>
    <div class="muted note">${older
      ? T(`Made at ${wMade}, refreshed at 00:00 and 12:00, so it is older than the hourly numbers above. In the dashed blocks, which overlap the next 3 hours, the hourly forecast is the better guide.`,
        `Зроблено о ${wMade}, оновлюється о 00:00 і 12:00, тож він старіший за щогодинні числа вгорі. У блоках із пунктиром, що перетинаються з наступними 3 годинами, кращий орієнтир — щогодинний прогноз.`)
      : T(`Made at ${wMade} together with the numbers above; refreshed at 00:00 and 12:00.`, `Зроблено о ${wMade} разом із числами вгорі; оновлюється о 00:00 і 12:00.`)}</div>
    <div class="cells" id="next24"></div>
    <h3>${T("This week: chance of a new alert per 3-hour block", "Цей тиждень: ймовірність нової тривоги в кожному 3-годинному блоці")}</h3><div id="heat"></div>
    <h3>${T("Week-ahead strip", "Смуга на тиждень")}</h3><div id="wstrip"></div>
    ${hist}`;
  const starts = S.D.week.block_starts_utc.map((s) => new Date(s));
  const wk = S.D.week[lv][id], until3 = +S.tF + 3 * 3600e3, c24 = $("#next24");
  // the next 8 blocks that have not started yet; a block that started before the forecast moment is left out
  starts.map((d, k) => k).filter((k) => starts[k] >= S.tF).slice(0, 8).forEach((k) => {
    const d = starts[k], p = wk[k], ov = older && +d < until3;
    const c = el("div", { className: "cell" + (ov ? " older" : ""), title: ov
      ? T(`${pct(p)} chance of a new alert (outlook made at ${wMade}). This block overlaps the next 3 hours: the hourly forecast above is newer.`, `${pct(p)} ймовірність нової тривоги (огляд зроблено о ${wMade}). Цей блок перетинається з наступними 3 годинами: щогодинний прогноз вгорі новіший.`)
      : T(`${pct(p)} chance of a new alert`, `${pct(p)} ймовірність нової тривоги`) }, `<span class="t">${fHour.format(d)}</span>${pct(p)}`);
    c.style.background = rampColor(p); c.style.color = textOn(p);
    c24.append(c);
  });
  drawHeat($("#heat"), starts, wk);
  drawWeekStrip($("#wstrip"), starts, wk);
  drawPanelHistory();
}
function drawPanelHistory() {
  const host = $("#hstrip"); if (!host) return;
  host.innerHTML = "";
  drawHistory(host, S.D.history, S.D.history[S.level][S.selected], missingHours(S.level, S.selected));
}
// Hours of the history strip without a saved forecast (no hourly run happened then). The export writes 0 for them, so they
// are found from the rolling log of the site's own forecasts: hours before the log starts come from a complete earlier
// export; from the log's first hour on, an hour with no log entry had no forecast. null = not known (log not loaded).
function missingHours(lv, id) {
  const L = S.D.p3log?.[lv], H = S.D.history;
  if (!L || !Object.keys(L).length) return null;
  const saved = new Map(Object.entries(L).map(([k, v]) => [new Date(k).getTime(), v]));
  const first = Math.min(...saved.keys()), t0 = new Date(H.start_utc).getTime();
  return H[lv][id].pred.map((_, h) => { const ms = t0 + h * 3600e3; return ms >= first && saved.get(ms)?.[id] == null; });
}

const tip = el("div", { className: "strip-tip" }); tip.hidden = true; document.body.append(tip);
function showTip(e, html) { tip.innerHTML = html; tip.style.left = `${e.clientX + 12}px`; tip.style.top = `${e.clientY + 10}px`; tip.hidden = false; }
const lateTip = () => `<br><i>${T("Started before this forecast: the hourly 1 h / 3 h forecast is newer", "Почався до цього прогнозу: щогодинний прогноз на 1 / 3 год новіший")}</i>`;

function drawHeat(host, starts, wk) {
  const days = [...new Set(starts.map((d) => fDay.format(d)))];
  const W = 400, cw = 38, ch = 20, left = 80, top = 16;
  const svg = svgEl("svg", { width: W, height: top + days.length * (ch + 2) + 4 });
  const blocks = ["00", "03", "06", "09", "12", "15", "18", "21"];
  blocks.forEach((b, j) => { const t = svgEl("text", { x: left + j * (cw + 2) + cw / 2, y: 11, "text-anchor": "middle" }); t.textContent = `${b}:00`; svg.append(t); });
  days.forEach((d, r) => { const t = svgEl("text", { x: 0, y: top + r * (ch + 2) + 14 }); t.textContent = d; svg.append(t); });
  starts.forEach((s, i) => {
    const r = days.indexOf(fDay.format(s)), late = s < S.tF;
    const j = Math.floor(Number(fmt({ hour: "2-digit", hourCycle: "h23" }).format(s)) / 3);
    const rect = svgEl("rect", { x: left + j * (cw + 2), y: top + r * (ch + 2), width: cw, height: ch, rx: 3, fill: rampColor(wk[i]), "fill-opacity": late ? 0.3 : 1 });
    rect.onmousemove = (e) => showTip(e, `${fDay.format(s)} ${fHour.format(s)}–${fHour.format(new Date(+s + 3 * 3600e3))}<br><b>${pct(wk[i])}</b> ${T("chance of a new alert", "ймовірність нової тривоги")}${late ? lateTip() : ""}`);
    rect.onmouseleave = () => (tip.hidden = true);
    svg.append(rect);
  });
  host.append(svg);
}

function drawWeekStrip(host, starts, wk) {
  const W = 400, H = 70, base = 52, n = starts.length, bw = W / n;
  const svg = svgEl("svg", { width: W, height: H });
  svg.append(svgEl("line", { x1: 0, x2: W, y1: base, y2: base, stroke: V.line }));
  starts.forEach((s, i) => {
    const h = Math.max(1, wk[i] * 44), late = s < S.tF;
    const r = svgEl("rect", { x: i * bw + 0.5, y: base - h, width: bw - 1, height: h, rx: 1.5, fill: rampColor(Math.max(wk[i], 0.35)), "fill-opacity": late ? 0.3 : 1 });
    r.onmousemove = (e) => showTip(e, `${fDay.format(s)} ${fHour.format(s)}<br><b>${pct(wk[i])}</b> ${T("chance of a new alert", "ймовірність нової тривоги")}${late ? lateTip() : ""}`);
    r.onmouseleave = () => (tip.hidden = true);
    svg.append(r);
    if (fHour.format(s) === "00:00") { const t = svgEl("text", { x: i * bw, y: H - 4 }); t.textContent = fShort.format(s); svg.append(t); }
  });
  host.append(svg);
}

function drawHistory(host, H, u, miss) {
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
  const base = 92, top = 52, gap = (h) => !!(miss && miss[h]);
  const xh = (h) => ((h + 0.5) / hours) * W, y = (p) => base - (p / 100) * (base - top);
  // the forecast line is drawn in pieces; hours without a saved forecast are a grey band, not a fake 0%
  for (let h = 0; h < hours;) {
    let k = h; while (k < hours && gap(k) === gap(h)) k++;
    const xa = (h / hours) * W, xb = (k / hours) * W;
    if (gap(h)) svg.append(svgEl("rect", { x: xa, y: top, width: xb - xa, height: base - top, fill: V.muted, "fill-opacity": 0.22 }));
    else {
      const pts = Array.from({ length: k - h }, (_, j) => `${xh(h + j)},${y(u.pred[h + j])}`).join(" ");
      svg.append(svgEl("polygon", { points: `${xa},${base} ${pts} ${xb},${base}`, fill: "#3987e5", "fill-opacity": 0.25 }));
      svg.append(svgEl("polyline", { points: pts, fill: "none", stroke: "#5598e7", "stroke-width": 2 }));
    }
    h = k;
  }
  svg.append(svgEl("line", { x1: 0, x2: W, y1: base, y2: base, stroke: V.line }));
  for (let d = 0; d <= hours; d += 24) {
    svg.append(svgEl("line", { x1: x(d * 60), x2: x(d * 60), y1: 12, y2: base, stroke: V.line, "stroke-dasharray": "2,3" }));
    if (d < hours) { const t = svgEl("text", { x: x(d * 60) + 2, y: 106 }); t.textContent = fShort.format(new Date(t0 + d * 3600e3)); svg.append(t); }
  }
  const hit = svgEl("rect", { x: 0, y: 50, width: W, height: 44, fill: "transparent" });
  hit.onmousemove = (e) => {
    const h = Math.min(hours - 1, Math.floor(((e.offsetX) / W) * hours));
    showTip(e, `${fDayTime.format(new Date(t0 + h * 3600e3))}<br>${gap(h) ? T("no forecast was saved for this hour", "для цієї години прогноз не збережено")
      : T(`forecast: <b>${u.pred[h]}%</b> chance of a new alert within 3 h`, `прогноз: <b>${u.pred[h]}%</b> ймовірність нової тривоги протягом 3 год`)}`);
  };
  hit.onmouseleave = () => (tip.hidden = true);
  svg.append(hit);
  host.append(svg);
  const gapKey = miss && miss.some(Boolean) ? ` <i class="sw" style="background:${V.muted};opacity:.45"></i>${T("no forecast saved", "прогноз не збережено")}` : "";
  host.append(el("div", { className: "muted" }, `<span class="chip red">${lvlName("red")}</span> <span class="chip yellow">${lvlName("yellow")}</span> <i class="sw" style="background:${COL.unknown}"></i>${T("level not recorded (before 6 Sep)", "рівень не фіксувався (до 6 вересня)")}${gapKey}`));
}

// ---------- replay ----------
function initReplay() {
  const R = S.D.replay;
  S.rmap = L.map("rmap", { attributionControl: false, zoomSnap: 0.25, minZoom: 5, maxZoom: 9 });
  S.rlayer = L.geoJSON(S.geo, { style: () => ({ fillColor: COL.nodata, fillOpacity: 1, color: V.bg, weight: 0.6 }) }).addTo(S.rmap);
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
      l.setStyle({ fillColor: rampColor(pr), color: y ? V.text : V.bg, weight: y ? 1.6 : 0.5 });
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
const CH = { chosen: "#3987e5", other: cv("--bar-other") || "#6b7a93", s2: "#d95926", s3: "#199e70", grid: V.line, ink: V.ink, muted: V.muted };
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
    svg.append(svgEl("line", { x1: sx(ref.v), x2: sx(ref.v), y1: top, y2: H - 18, stroke: V.text, "stroke-width": 1.5, "stroke-dasharray": "5,3" }));
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
    s.vals.forEach((v, i) => svg.append(svgEl("circle", { cx: sx(i), cy: sy(v), r: 4, fill: s.color, stroke: V.surface, "stroke-width": 2 })));
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
    svg.append(svgEl("line", { x1: sx(0), x2: sx(1), y1: sy(v), y2: sy(v), stroke: V.line }));
    const t = svgEl("text", { x: 2, y: sy(v) + 3 }); t.textContent = `${v * 100}%`; svg.append(t);
    const t2 = svgEl("text", { x: sx(v) - 8, y: H - m + 14 }); t2.textContent = `${v * 100}%`; svg.append(t2);
  }
  svg.append(svgEl("line", { x1: sx(0), y1: sy(0), x2: sx(1), y2: sy(1), stroke: V.muted, "stroke-dasharray": "4,4" }));
  const pts = cal.map((c) => `${sx(c.predicted)},${sy(c.observed)}`).join(" ");
  svg.append(svgEl("polyline", { points: pts, fill: "none", stroke: "#3987e5", "stroke-width": 2 }));
  cal.forEach((c) => {
    const d = svgEl("circle", { cx: sx(c.predicted), cy: sy(c.observed), r: 4.5, fill: "#3987e5", stroke: V.surface, "stroke-width": 2 });
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
  const known = (new Date(sn.known_until_utc).getTime() - t0) / 6e4;
  // per block: "new alert" (a new alert started), "still on" (no new start, but an earlier alert was running), "quiet"
  const running = (i) => u.alerts.some(([a, e]) => a < (i + 1) * 180 && e > i * 180);
  sn.block_starts_utc.forEach((b, i) => {
    const p = u.next24[i], y = u.actual_blocks[i];
    const mark = y == null ? `<span class="ckm unk">${T("not yet", "ще ні")}</span>`
      : y ? `<span class="ckm yes">${T("started", "нова")}</span>`
      : running(i) ? `<span class="ckm on">${T("still on", "триває")}</span>` : `<span class="ckm no">${T("quiet", "тихо")}</span>`;
    const c = el("div", { className: "cell" }, `${fHour.format(new Date(b))}<b>${pct(p)}</b>`);
    c.style.background = rampColor(p); c.style.color = textOn(p);
    const w = el("div", { className: "ckcol" }); w.append(c); w.append(el("div", {}, mark)); cells.append(w);
  });
  box.append(el("div", { className: "cnote" }, T("Forecast: chance that a new alert starts in each 3-hour block (Kyiv time). Below: what happened.", "Прогноз: ймовірність, що нова тривога почнеться в кожному 3-годинному блоці (за Києвом). Нижче: що сталося.")));
  box.append(cells);
  // 24 h timeline of the actual alerts, drawn on the same 8 columns as the blocks; a white mark = an alert started
  const W = 800, H = 26, x = (m) => (m / 1440) * W;
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, preserveAspectRatio: "none", class: "cktl" });
  svg.append(svgEl("rect", { x: 0, y: 4, width: W, height: 18, fill: V.surface, stroke: V.line }));
  u.alerts.forEach(([a, e, lvl]) => {
    const r = svgEl("rect", { x: x(a), y: 4, width: Math.max(2, x(e) - x(a)), height: 18, fill: COL[lvl] || COL.unknown });
    r.onmousemove = (ev) => showTip(ev, `${fDayTime.format(new Date(t0 + a * 6e4))} – ${fHour.format(new Date(t0 + e * 6e4))}${lvl === "red" || lvl === "yellow" ? `<br><span class="chip ${lvl}">${lvlName(lvl)}</span>` : ""}${a === 0 ? `<br>${T("started before the forecast", "почалася до прогнозу")}` : ""}`);
    r.onmouseleave = () => (tip.hidden = true);
    svg.append(r);
  });
  if (known < 1440) svg.append(svgEl("rect", { x: x(known), y: 4, width: W - x(known), height: 18, fill: "#3a3f47", opacity: 0.85 }));  // not known yet
  for (let k = 1; k < 8; k++) svg.append(svgEl("line", { x1: k * 100, x2: k * 100, y1: 0, y2: H, stroke: V.bg, "stroke-width": 3 }));
  u.alerts.forEach(([a]) => { if (a > 0) svg.append(svgEl("rect", { x: Math.min(x(a), W - 4), y: 0, width: 4, height: H, fill: V.text })); });  // starts, drawn on top
  box.append(svg);
  box.append(el("div", { className: "cnote" }, T(`Actual alerts in the 24 hours after the forecast, aligned with the blocks above. White mark = an alert <b>started</b>; <span class="ckm yes">started</span> a new alert started in the block, <span class="ckm on">still on</span> an earlier alert was still running, <span class="ckm no">quiet</span> no alert.`,
    `Фактичні тривоги за 24 години після прогнозу, вирівняні з блоками вгорі. Біла позначка = тривога <b>почалася</b>; <span class="ckm yes">нова</span> у блоці почалася нова тривога, <span class="ckm on">триває</span> ще тривала попередня, <span class="ckm no">тихо</span> тривоги не було.`)));
  const ok = (v, r) => (v == null ? `<span class="ckm unk">${T("not yet known", "ще невідомо")}</span>` : v >= r[0] && v <= r[1] ? `<span class="ckm yes2">${T("inside the range", "у діапазоні")}</span>` : `<span class="ckm out">${T("outside the range", "поза діапазоном")}</span>`);
  const hU = T("h", "год");
  box.append(el("div", { className: "tiles" }, `
    <div class="tile"><div class="v">${u.cnt[0]}–${u.cnt[1]} → ${u.actual_cnt ?? "?"}</div><div class="k">${T("alerts: forecast range → actual", "тривоги: прогнозний діапазон → факт")} · ${ok(u.actual_cnt, u.cnt)}</div></div>
    <div class="tile"><div class="v">${u.hrs[0]}–${u.hrs[1]} ${hU} → ${u.actual_hrs ?? "?"} ${hU}</div><div class="k">${T("hours under alert", "години під тривогою")} · ${ok(u.actual_hrs, u.hrs)}</div></div>`));
  host.append(box);
}

load().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<pre style="color:#f88">Failed to load data: ${e}</pre>`); console.error(e); });
