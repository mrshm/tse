"""گزارش HTML تک‌فایلی برای نتیجهٔ بک‌تست."""

from __future__ import annotations

import json

TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>گزارش بک‌تست</title>
<style>
  :root {
    color-scheme: light;
    --bg: #f4f3ef;
    --surface-1: #fcfcfb;
    --surface-2: #f1f0ec;
    --surface-3: #e9e7e0;
    --border: #e2e0d8;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #85837b;
    --accent: #2a78d6;
    --good: #0f7a0f;
    --good-bg: #e6f4e6;
    --critical: #b83030;
    --critical-bg: #fae9e9;
    --warning: #8a5a00;
    --series-1: #2a78d6;
    --series-2: #b06a1e;
    --shadow: 0 1px 2px rgba(20,20,10,.06), 0 4px 16px rgba(20,20,10,.04);
    --radius: 12px;
  }
  [data-theme="dark"] {
    color-scheme: dark;
    --bg: #121211;
    --surface-1: #1a1a19;
    --surface-2: #232322;
    --surface-3: #2c2c2a;
    --border: #34342f;
    --text-primary: #f0efec;
    --text-secondary: #c3c2b7;
    --text-muted: #918f86;
    --accent: #3987e5;
    --good: #3fc23f;
    --good-bg: #162b16;
    --critical: #e66767;
    --critical-bg: #331a1a;
    --warning: #fab219;
    --series-1: #3987e5;
    --series-2: #b8833c;
    --shadow: 0 1px 2px rgba(0,0,0,.4);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: "Vazirmatn", "Vazir", "IRANSansX", "IRANSans", "Segoe UI", Tahoma, sans-serif;
    background: var(--bg);
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 1120px; margin: 0 auto; padding: 24px 20px 56px; }
  .top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
  h1 { font-size: 22px; margin: 0 0 2px; letter-spacing: -.2px; }
  h2 { font-size: 15px; margin: 0; font-weight: 600; }
  .sub { color: var(--text-secondary); font-size: 13px; margin: 0; }
  .icon-btn { background: var(--surface-1); border: 1px solid var(--border); color: var(--text-secondary);
              border-radius: 9px; width: 36px; height: 36px; cursor: pointer; font-size: 15px;
              display: grid; place-items: center; }
  .icon-btn:hover { background: var(--surface-2); color: var(--text-primary); }
  .icon-btn:focus-visible, .chip:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
  .chip { background: var(--surface-1); border: 1px solid var(--border); color: var(--text-secondary);
          border-radius: 999px; padding: 3px 10px; font-size: 12px; white-space: nowrap; }
  .chip b { color: var(--text-primary); font-weight: 600; }

  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(126px, 1fr)); gap: 10px; margin-bottom: 16px; }
  .kpi { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius);
         padding: 12px 14px; box-shadow: var(--shadow); min-width: 0; }
  .kpi .label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis; }
  .kpi .value { font-size: 22px; font-weight: 650; letter-spacing: -.4px; font-variant-numeric: tabular-nums; }
  .kpi .value bdi, td.num bdi { unicode-bidi: isolate; direction: ltr; }
  .kpi .note { font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }
  .up { color: var(--good); }
  .down { color: var(--critical); }
  .flat { color: var(--text-secondary); }

  .card { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius);
          box-shadow: var(--shadow); padding: 16px; margin-bottom: 14px; }
  .card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
  .hint { font-size: 12px; color: var(--text-muted); }
  .chart { position: relative; width: 100%; }
  .chart svg { display: block; width: 100%; height: auto; overflow: visible; }
  .legend { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); margin: 2px 0 6px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend i { width: 10px; height: 3px; border-radius: 2px; display: inline-block; }
  .tip { position: absolute; pointer-events: none; background: var(--surface-1); border: 1px solid var(--border);
         box-shadow: var(--shadow); border-radius: 8px; padding: 7px 9px; font-size: 12px; min-width: 128px;
         opacity: 0; transition: opacity .08s; z-index: 5; }
  .tip .d { color: var(--text-muted); font-size: 11px; margin-bottom: 3px; }
  .tip .r { display: flex; justify-content: space-between; gap: 12px; font-variant-numeric: tabular-nums; }
  .tip .r b { font-weight: 600; }

  .table-wrap { overflow-x: auto; max-height: 460px; overflow-y: auto; border-radius: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  th, td { padding: 7px 9px; text-align: right; white-space: nowrap; border-bottom: 1px solid var(--border); }
  th { color: var(--text-secondary); font-weight: 600; font-size: 11.5px; position: sticky; top: 0;
       background: var(--surface-1); z-index: 1; }
  tbody tr:hover { background: var(--surface-2); }
  td.num { font-variant-numeric: tabular-nums; }
  .tag { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 999px;
         background: var(--surface-3); color: var(--text-secondary); }
  .tag.win { background: var(--good-bg); color: var(--good); }
  .tag.loss { background: var(--critical-bg); color: var(--critical); }

  details.card > summary { cursor: pointer; font-weight: 600; font-size: 14px; list-style: none; }
  details.card > summary::-webkit-details-marker { display: none; }
  details.card > summary::before { content: "▸"; color: var(--text-muted); margin-left: 6px; }
  details[open].card > summary::before { content: "▾"; }
  details.card[open] > summary { margin-bottom: 10px; }

  .notes { color: var(--text-secondary); font-size: 12.5px; line-height: 1.9; margin-top: 8px; }
  .notes h3 { font-size: 13px; margin: 0 0 6px; color: var(--text-primary); }
  .notes ul { margin: 0; padding-right: 18px; }
  .empty { color: var(--text-muted); text-align: center; padding: 28px 0; font-size: 13px; }
  @media (max-width: 600px) {
    .wrap { padding: 16px 12px 40px; }
    h1 { font-size: 19px; }
    .kpi .value { font-size: 19px; }
    /* روی موبایل قیمت‌های ورود/خروج حذف می‌شوند تا جدول جا شود */
    #trades th:nth-child(4), #trades td:nth-child(4),
    #trades th:nth-child(5), #trades td:nth-child(5) { display: none; }
  }
  body.embed .top { display: none; }
  body.embed .wrap { padding-top: 14px; }
</style>
</head>
<body>
<script>if(location.search.indexOf("embed")>=0)document.body.classList.add("embed")</script>
<div class="wrap">
  <div class="top">
    <div>
      <h1>گزارش بک‌تست</h1>
      <p class="sub">استراتژی اسکنر نوسان‌گیری · <span id="period">—</span></p>
    </div>
    <button class="icon-btn" id="theme" title="تغییر تم" aria-label="تغییر تم">◐</button>
  </div>

  <div class="chips" id="chips"></div>
  <div class="kpis" id="kpis"></div>

  <div class="card">
    <div class="card-head">
      <h2>رشد سرمایه</h2>
      <span class="hint">پایه = ۱۰۰ در شروع دوره</span>
    </div>
    <div class="legend" id="legend"></div>
    <div class="chart" id="equity"></div>
  </div>

  <div class="card">
    <div class="card-head">
      <h2>افت سرمایه</h2>
      <span class="hint">درصد از سقف قبلی</span>
    </div>
    <div class="chart" id="dd"></div>
  </div>

  <div class="card">
    <div class="card-head">
      <h2>معاملات</h2>
      <span class="hint" id="tsum"></span>
    </div>
    <div class="table-wrap" id="trades"></div>
  </div>

  <details class="card">
    <summary>داده‌های ماهانه</summary>
    <div class="table-wrap" id="monthly"></div>
  </details>

  <div class="notes">
    <h3>فرض‌ها و محدودیت‌ها</h3>
    <ul>
      <li>سیگنال هر روز در <b>بازگشایی روز معاملاتی بعد</b> اجرا می‌شود؛ استفاده از قیمت بستهٔ همان روز، نتیجه را خوش‌بینانه می‌کرد.</li>
      <li>فروش زودتر از <b>T+2</b> ممکن نیست، حتی اگر حد ضرر لمس شود.</li>
      <li>کارمزد خرید و فروش و اثر افزایش سرمایه با استفاده از قیمت پایانی تعدیل‌شده لحاظ شده است.</li>
      <li>امتیازدهی <b>مقطعی</b> است: هر روز نمادها فقط با هم‌روزهای خودشان مقایسه می‌شوند. دادهٔ حقیقی/حقوقی (وزن ۱۴٪ در اسکنر) در بک‌تست حذف و بقیهٔ وزن‌ها بازتوزیع شده‌اند.</li>
      <li>معاملات فرض می‌شوند در قیمت بازگشایی/حد ضرر کامل پر می‌شوند؛ صف خرید و فروش و عمق بازار مدل نشده است.</li>
      <li>این گزارش ابزار پژوهشی است، نه توصیهٔ سرمایه‌گذاری.</li>
    </ul>
  </div>
</div>

<script>
const DATA = __DATA__;

const $ = (s, r = document) => r.querySelector(s);
const fmt = (n, d = 0) => (n === null || n === undefined || !isFinite(n)) ? "—"
  : new Intl.NumberFormat("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }).format(n);
const pctTxt = (x, d = 1) => (x === null || x === undefined || !isFinite(x)) ? "—"
  : (x >= 0 ? "+" : "-") + Math.abs(x * 100).toFixed(d) + "%";
const pct = (x, d = 1) => pctTxt(x, d) === "—" ? "—" : `<bdi dir="ltr">${pctTxt(x, d)}</bdi>`;
const cls = x => x > 0 ? "up" : x < 0 ? "down" : "flat";

/* ---------- header ---------- */
(function initHeader() {
  const c = DATA.config, m = DATA.metrics;
  const first = DATA.curve[0], last = DATA.curve[DATA.curve.length - 1];
  $("#period").textContent = first && last ? `${first.date_fa} تا ${last.date_fa}` : "—";
  const chips = [
    [`سرمایه`, fmt(c.capital_toman / 1e6, 0) + " م.ت"],
    [`سهام هم‌زمان`, c.top_n],
    [`نگهداری`, `<bdi dir="ltr">${c.min_hold}–${c.max_hold}</bdi> روز`],
    [`حد ضرر`, c.stop_atr + "×ATR"],
    [`هدف`, c.target_atr > 0 ? c.target_atr + "×ATR" : "بدون هدف"],
    c.trail_atr > 0 ? [`حد ضرر متحرک`, c.trail_atr + "×ATR"] : null,
    [`کارمزد`, `<bdi dir="ltr">${c.buy_fee_pct}% / ${c.sell_fee_pct}%</bdi>`],
    [`دامنه`, fmt(c.symbols) + " نماد"],
    [`صندوق`, c.include_etf ? "بله" : "خیر"],
  ];
  $("#chips").innerHTML = chips.filter(Boolean)
    .map(([k, v]) => `<span class="chip">${k} <b>${v}</b></span>`).join("");

  const kpis = [
    ["بازده کل", pct(m.total_return), cls(m.total_return)],
    ["بازده شاخص کل", pct(m.benchmark_return), cls(m.benchmark_return)],
    ["بازده مازاد", pct(m.excess_return), cls(m.excess_return)],
    ["حداکثر افت", pct(m.max_drawdown), "down"],
    ["شارپ سالانه", fmt(m.sharpe, 2), "flat"],
    ["معاملات", fmt(m.trades), "flat"],
    ["کارمزد پرداختی", fmt(m.fees_total / 1e7, 0) + " م.ت", "flat"],
  ];
  $("#kpis").innerHTML = kpis.map(([l, v, k]) => {
    const vh = /^-/.test(v) ? `<bdi dir="ltr">${v}</bdi>` : v;
    return `<div class="kpi"><div class="label">${l}</div><div class="value ${k}">${vh}</div></div>`;
  }).join("");
  const wr = m.trades ? `نرخ برد ${(m.win_rate * 100).toFixed(0)}٪` : "بدون معامله";
  const tiles = $("#kpis").children;
  if (isFinite(m.gross_return_est)) tiles[0].insertAdjacentHTML("beforeend",
    `<div class="note">قبل از کارمزد ${pct(m.gross_return_est, 0)}</div>`);
  tiles[5].insertAdjacentHTML("beforeend",
    `<div class="note">${wr}${m.profit_factor ? " · سود/زیان " + m.profit_factor.toFixed(2) : ""}</div>`);
  if (tiles[6]) tiles[6].insertAdjacentHTML("beforeend",
    `<div class="note">${(m.fees_pct_of_capital * 100).toFixed(0)}٪ از سرمایه</div>`);

  $("#tsum").textContent = m.trades
    ? `میانگین نگهداری ${m.avg_holding_days.toFixed(1)} روز · در معرض بودن ${(m.exposure * 100).toFixed(0)}٪`
    : "";
})();

/* ---------- chart helpers ---------- */
function niceTicks(min, max, count = 5) {
  const span = max - min || 1;
  const raw = span / (count - 1);
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(s => s >= raw) || raw;
  const start = Math.ceil(min / step) * step;
  const out = [];
  for (let v = start; v <= max + step * 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

function buildChart(host, cfg) {
  host.innerHTML = "";
  const W = Math.max(300, host.clientWidth || 700);
  const H = cfg.height || 300;
  const P = { l: 8, r: 54, t: 12, b: 26 };
  const iw = W - P.l - P.r, ih = H - P.t - P.b;
  const n = cfg.n;

  const xs = i => P.l + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw);
  const ys = v => P.t + (1 - (v - cfg.min) / (cfg.max - cfg.min)) * ih;

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("height", H);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", cfg.label || "");
  host.appendChild(svg);

  const add = (tag, attrs) => {
    const e = document.createElementNS(ns, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    svg.appendChild(e);
    return e;
  };

  for (const t of niceTicks(cfg.min, cfg.max, 5)) {
    const y = ys(t);
    if (y < P.t - 1 || y > P.t + ih + 1) continue;
    add("line", { x1: P.l, x2: P.l + iw, y1: y, y2: y, stroke: "var(--border)", "stroke-width": 1 });
    const lbl = add("text", { x: W - 4, y: y + 4, fill: "var(--text-muted)",
      "font-size": 10.5, "text-anchor": "end", "font-family": "inherit",
      direction: "ltr", style: "unicode-bidi:isolate" });
    lbl.textContent = cfg.tickFmt(t);
  }

  const step = Math.max(1, Math.floor((n - 1) / 5));
  for (let i = 0; i < n; i += step) {
    const lbl = add("text", { x: xs(i), y: H - 8, fill: "var(--text-muted)", "font-size": 10.5,
      "text-anchor": i === 0 ? "start" : "middle", "font-family": "inherit" });
    lbl.textContent = cfg.xLabel(i);
  }

  if (cfg.zeroLine && cfg.min < 0 && cfg.max > 0) {
    add("line", { x1: P.l, x2: P.l + iw, y1: ys(0), y2: ys(0),
      stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "3 3" });
  }

  const defs = document.createElementNS(ns, "defs");
  svg.appendChild(defs);

  for (const s of cfg.series) {
    const pts = s.values;
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = pts[i];
      if (v === null || v === undefined || !isFinite(v)) { started = false; continue; }
      d += (started ? " L" : " M") + xs(i).toFixed(1) + " " + ys(v).toFixed(1);
      started = true;
    }
    if (s.area) {
      const gid = "g" + Math.random().toString(36).slice(2, 8);
      const grad = document.createElementNS(ns, "linearGradient");
      grad.setAttribute("id", gid);
      grad.setAttribute("x1", "0"); grad.setAttribute("y1", "0");
      grad.setAttribute("x2", "0"); grad.setAttribute("y2", "1");
      const st1 = document.createElementNS(ns, "stop");
      st1.setAttribute("offset", "0%"); st1.setAttribute("stop-color", s.color);
      st1.setAttribute("stop-opacity", "0.20");
      const st2 = document.createElementNS(ns, "stop");
      st2.setAttribute("offset", "100%"); st2.setAttribute("stop-color", s.color);
      st2.setAttribute("stop-opacity", "0.02");
      grad.appendChild(st1); grad.appendChild(st2); defs.appendChild(grad);
      const areaD = d + ` L${xs(n - 1).toFixed(1)} ${ys(cfg.baseY ?? cfg.min)} L${xs(0).toFixed(1)} ${ys(cfg.baseY ?? cfg.min)} Z`;
      add("path", { d: areaD, fill: `url(#${gid})`, stroke: "none" });
    }
    add("path", { d, fill: "none", stroke: s.color, "stroke-width": s.width || 2,
      "stroke-linejoin": "round", "stroke-linecap": "round" });
  }

  /* direct labels at the end of each series */
  if (cfg.endLabels) {
    const used = [];
    for (const s of cfg.series) {
      for (let i = n - 1; i >= 0; i--) {
        const v = s.values[i];
        if (v === null || v === undefined || !isFinite(v)) continue;
        let y = ys(v);
        for (const u of used) if (Math.abs(y - u) < 14) y = u + 14;
        used.push(y);
        add("circle", { cx: xs(i), cy: ys(v), r: 2.6, fill: s.color,
          stroke: "var(--surface-1)", "stroke-width": 2 });
        const t = add("text", { x: xs(i) - 9, y: y + 4, fill: "var(--text-secondary)",
          "font-size": 11, "text-anchor": "end", "font-family": "inherit",
          stroke: "var(--surface-1)", "stroke-width": 3, "paint-order": "stroke" });
        t.textContent = s.name;
        break;
      }
    }
  }

  /* crosshair + tooltip */
  if (cfg.tip !== false) {
    const cross = document.createElementNS(ns, "line");
    cross.setAttribute("stroke", "var(--text-muted)");
    cross.setAttribute("stroke-width", 1);
    cross.setAttribute("stroke-dasharray", "3 3");
    cross.setAttribute("y1", P.t); cross.setAttribute("y2", P.t + ih);
    cross.setAttribute("opacity", "0");
    svg.appendChild(cross);

    const dots = cfg.series.map(s => {
      const c = document.createElementNS(ns, "circle");
      c.setAttribute("r", 3.5);
      c.setAttribute("fill", s.color);
      c.setAttribute("stroke", "var(--surface-1)");
      c.setAttribute("stroke-width", 2);
      c.setAttribute("opacity", "0");
      svg.appendChild(c);
      return c;
    });

    const tip = document.createElement("div");
    tip.className = "tip";
    host.appendChild(tip);

    const hit = document.createElementNS(ns, "rect");
    hit.setAttribute("x", P.l); hit.setAttribute("y", P.t);
    hit.setAttribute("width", iw); hit.setAttribute("height", ih);
    hit.setAttribute("fill", "transparent");
    svg.appendChild(hit);

    hit.addEventListener("mousemove", ev => {
      const box = svg.getBoundingClientRect();
      const rel = (ev.clientX - box.left) * (W / box.width);
      const i = Math.max(0, Math.min(n - 1, Math.round((rel - P.l) / iw * (n - 1))));
      const x = xs(i);
      cross.setAttribute("x1", x); cross.setAttribute("x2", x);
      cross.setAttribute("opacity", "1");
      const rows = [];
      cfg.series.forEach((s, k) => {
        const v = s.values[i];
        const ok = v !== null && v !== undefined && isFinite(v);
        dots[k].setAttribute("opacity", ok ? "1" : "0");
        if (ok) { dots[k].setAttribute("cx", x); dots[k].setAttribute("cy", ys(v)); }
        rows.push(`<div class="r"><span>${s.name}</span><b style="color:${s.color}">${ok ? cfg.tipFmt(v) : "—"}</b></div>`);
      });
      tip.innerHTML = `<div class="d">${cfg.tipTitle(i)}</div>${rows.join("")}`;
      tip.style.opacity = "1";
      const scale = box.width / W;
      let left = x * scale;
      const tw = tip.offsetWidth;
      left = Math.min(Math.max(4, left - tw / 2), box.width - tw - 4);
      tip.style.left = left + "px";
      tip.style.top = "6px";
    });
    hit.addEventListener("mouseleave", () => {
      cross.setAttribute("opacity", "0");
      dots.forEach(d => d.setAttribute("opacity", "0"));
      tip.style.opacity = "0";
    });
  }
}

/* ---------- equity ---------- */
function renderEquity() {
  const curve = DATA.curve;
  const host = $("#equity");
  if (!curve.length) { host.innerHTML = '<div class="empty">داده‌ای نیست</div>'; return; }
  const base = curve[0].equity;
  const bbase = curve.find(r => r.benchmark)?.benchmark || null;
  const series = [
    { name: "استراتژی", color: "var(--series-1)", values: curve.map(r => r.equity / base * 100) },
  ];
  if (bbase) series.push({
    name: "شاخص کل", color: "var(--series-2)",
    values: curve.map(r => r.benchmark ? r.benchmark / bbase * 100 : null),
  });

  $("#legend").innerHTML = series.map(s =>
    `<span><i style="background:${s.color}"></i>${s.name}</span>`).join("");

  const vals = series.flatMap(s => s.values).filter(v => isFinite(v));
  let min = Math.min(...vals), max = Math.max(...vals);
  const pad = (max - min) * 0.08 || 1;
  min -= pad; max += pad;

  buildChart(host, {
    n: curve.length, min, max, height: 320,
    label: "رشد سرمایه استراتژی در برابر شاخص کل",
    series, endLabels: true, baseY: min,
    tickFmt: v => Math.round(v),
    tipFmt: v => v.toFixed(1),
    tipTitle: i => curve[i].date_fa,
    xLabel: i => curve[i].date_fa.slice(5),
  });
}

/* ---------- drawdown ---------- */
function renderDrawdown() {
  const curve = DATA.curve;
  const host = $("#dd");
  if (!curve.length) { host.innerHTML = '<div class="empty">داده‌ای نیست</div>'; return; }
  let peak = -Infinity;
  const dd = curve.map(r => {
    peak = Math.max(peak, r.equity);
    return (r.equity / peak - 1) * 100;
  });
  const min = Math.min(...dd, -1) * 1.08;
  buildChart(host, {
    n: curve.length, min, max: 1, height: 180,
    label: "افت سرمایه نسبت به سقف قبلی",
    series: [{ name: "افت", color: "var(--critical)", values: dd, area: true, width: 2 }],
    endLabels: false, baseY: 0, zeroLine: true,
    tickFmt: v => v.toFixed(0) + "%",
    tipFmt: v => v.toFixed(1) + "%",
    tipTitle: i => curve[i].date_fa,
    xLabel: i => curve[i].date_fa.slice(5),
  });
}

/* ---------- trades ---------- */
function renderTrades() {
  const host = $("#trades");
  const rows = DATA.trades.slice().reverse();
  if (!rows.length) { host.innerHTML = '<div class="empty">در این دوره معامله‌ای انجام نشد</div>'; return; }
  const head = `<table><thead><tr>
      <th>نماد</th><th>ورود</th><th>خروج</th><th>قیمت ورود</th><th>قیمت خروج</th>
      <th>بازده</th><th>روز</th><th>دلیل خروج</th></tr></thead><tbody>`;
  const body = rows.slice(0, 400).map(t => `<tr>
      <td><b>${t.symbol}</b></td>
      <td class="num">${t.entry_date_fa}</td>
      <td class="num">${t.exit_date_fa}</td>
      <td class="num">${fmt(t.entry_price)}</td>
      <td class="num">${fmt(t.exit_price)}</td>
      <td class="num ${t.ret_pct >= 0 ? "up" : "down"}"><bdi dir="ltr">${pctTxt(t.ret_pct / 100)}</bdi></td>
      <td class="num">${t.holding_days}</td>
      <td><span class="tag ${t.ret_pct >= 0 ? "win" : "loss"}">${t.reason}</span></td>
    </tr>`).join("");
  host.innerHTML = head + body + "</tbody></table>";
}

/* ---------- monthly ---------- */
function renderMonthly() {
  const host = $("#monthly");
  const curve = DATA.curve;
  if (!curve.length) { host.innerHTML = '<div class="empty">داده‌ای نیست</div>'; return; }
  const months = [];
  let cur = null;
  for (const r of curve) {
    const key = r.date_fa.slice(0, 7);
    if (!cur || cur.key !== key) {
      cur = { key, firstEq: r.equity, lastEq: r.equity, firstBench: r.benchmark, lastBench: r.benchmark };
      months.push(cur);
    } else {
      cur.lastEq = r.equity;
      if (r.benchmark) { if (!cur.firstBench) cur.firstBench = r.benchmark; cur.lastBench = r.benchmark; }
    }
  }
  const rows = months.map((m, i) => {
    const prevEq = i > 0 ? months[i - 1].lastEq : DATA.curve[0].equity;
    const prevB = i > 0 ? months[i - 1].lastBench : m.firstBench;
    const sr = m.lastEq / prevEq - 1;
    const br = prevB && m.lastBench ? m.lastBench / prevB - 1 : null;
    return { key: m.key, sr, br };
  });
  host.innerHTML = `<table><thead><tr><th>ماه</th><th>استراتژی</th><th>شاخص کل</th><th>مازاد</th></tr></thead><tbody>` +
    rows.map(r => `<tr>
      <td class="num">${r.key}</td>
      <td class="num ${cls(r.sr)}">${pct(r.sr)}</td>
      <td class="num ${r.br === null ? "flat" : cls(r.br)}">${r.br === null ? "—" : pct(r.br)}</td>
      <td class="num ${r.br === null ? "flat" : cls(r.sr - r.br)}">${r.br === null ? "—" : pct(r.sr - r.br)}</td>
    </tr>`).join("") + "</tbody></table>";
}

/* ---------- boot ---------- */
let raf = 0;
function renderAll() {
  cancelAnimationFrame(raf);
  raf = requestAnimationFrame(() => { renderEquity(); renderDrawdown(); });
}
renderTrades();
renderMonthly();
renderAll();
window.addEventListener("resize", renderAll);

document.getElementById("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.getAttribute("data-theme") === "dark";
  root.setAttribute("data-theme", dark ? "light" : "dark");
  try { localStorage.setItem("tse-theme", dark ? "light" : "dark"); } catch (e) {}
  renderAll();
});
try {
  const saved = localStorage.getItem("tse-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}
setTimeout(renderAll, 30);
</script>
</body>
</html>
"""


def render_report(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", data)


# قالب مشترک برای گزارش‌های دیگر (مثل جست‌وجوی پارامتر)
CSS = TEMPLATE.split("<style>", 1)[1].split("</style>", 1)[0]
