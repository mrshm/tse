"""گزارش HTML ریسک ورشکستگی (شبیه‌سازی مونت‌کارلو)."""

from __future__ import annotations

import json

from .report import CSS

EXTRA_CSS = r"""
  .chart { position: relative; width: 100%; }
  .chart svg { display: block; width: 100%; height: auto; overflow: visible; }
  .legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px;
    color: var(--text-secondary); margin: 2px 0 6px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend i { width: 12px; height: 8px; border-radius: 2px; display: inline-block; }
  .table-wrap { max-height: none; }
  .row-hi { background: var(--accent-soft, var(--surface-2)); }
  .bad-strong { color: var(--critical); font-weight: 650; }
  .good-strong { color: var(--good); font-weight: 650; }
  .assume { font-size: 12.5px; color: var(--text-secondary); line-height: 1.9; }
"""

TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ریسک ورشکستگی</title>
<style>
__CSS__
__EXTRA__
  body.embed .top { display: none; }
  body.embed .wrap { padding-top: 14px; }
</style>
</head>
<body>
<script>if(location.search.indexOf("embed")>=0)document.body.classList.add("embed")</script>
<div class="wrap">
  <div class="top">
    <div>
      <h1>ریسک ورشکستگی</h1>
      <p class="sub">شبیه‌سازی <span id="sims">—</span> مسیر از <span id="trades">—</span>
        معامله · بدون فرض دربارهٔ روند بازار</p>
    </div>
    <button class="icon-btn" id="theme" title="تغییر تم" aria-label="تغییر تم">◐</button>
  </div>

  <div class="chips" id="chips"></div>
  <div class="kpis" id="kpis"></div>
  <p class="assume" id="lead"></p>

  <div class="card">
    <div class="card-head">
      <h2>مسیر سرمایه</h2>
      <span class="hint">باندهای درصدی از ۱۰٬۰۰۰ مسیر · شروع = ۱۰۰</span>
    </div>
    <div class="legend" id="legend"></div>
    <div class="chart" id="chart"></div>
  </div>

  <div class="card">
    <div class="card-head">
      <h2>اندازهٔ موقعیت و ریسک</h2>
      <span class="hint">بقیهٔ پارامترها ثابت</span>
    </div>
    <div class="table-wrap" id="ladder"></div>
  </div>

  <div class="notes">
    <h3>این اعداد چه فرض‌هایی دارند</h3>
    <ul>
      <li>هر معامله مستقل از قبلی است؛ نه روند بازار، نه خبر، نه همبستگی نمادها مدل نشده.</li>
      <li>برد و باخت همیشه یک اندازه‌اند (میانگین R). در واقعیت توزیع بردها چوله است و
        چند برد بزرگ، نتیجه را می‌سازد.</li>
      <li>گپ قیمتی و صف خرید/فروش مدل نشده؛ در بازار واقعی حد ضرر می‌تواند بدتر از
        قیمتِ تعیین‌شده پر شود.</li>
      <li>«ورشکستگی» یعنی افت سرمایه از سطح مشخص‌شده، نه صفرشدن حساب. در عمل همان‌جا
        باید برگه را ببندی و استراتژی را بازبینی کنی.</li>
      <li>نرخ برد و R را از <b>دفتر معاملات خودت</b> بگیر، نه از بک‌تست. اگر ۲۰ معامله
        بیشتر نداری، عددها فقط حدس‌اند.</li>
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
const prob = x => `<bdi dir="ltr">${(x * 100).toFixed(1)}%</bdi>`;
const cls = x => x > 0 ? "up" : x < 0 ? "down" : "flat";

(function () {
  const c = DATA.config, s = DATA.summary;
  $("#sims").textContent = fmt(c.sims);
  $("#trades").textContent = fmt(c.trades);
  const chips = [
    [`سرمایه`, `<bdi dir="ltr">${fmt(c.capital_toman / 1e6)}</bdi> م.ت`],
    [`ریسک هر معامله`, `<bdi dir="ltr">${c.risk_pct}%</bdi>`],
    [`فاصلهٔ حد ضرر`, `<bdi dir="ltr">${c.stop_pct}%</bdi>`],
    [`نرخ برد`, `<bdi dir="ltr">${(c.win_rate * 100).toFixed(0)}%</bdi>`],
    [`R (سود/ریسک)`, `<bdi dir="ltr">${c.payoff_r}</bdi>`],
    [`کارمزد`, `<bdi dir="ltr">${c.fees_pct}%</bdi>`],
    [`آستانهٔ ورشکستگی`, `<bdi dir="ltr">−${c.ruin_pct}%</bdi>`],
  ];
  $("#chips").innerHTML = chips.map(([k, v]) => `<span class="chip">${k} <b>${v}</b></span>`).join("");

  const kpis = [
    ["احتمال ورشکستگی", prob(s.p_ruin), s.p_ruin > 0.1 ? "down" : "flat",
     `افت ${c.ruin_pct}٪ از اوج`],
    ["احتمال سود", prob(s.p_profit), s.p_profit > 0.5 ? "up" : "down", "پایان دوره"],
    ["میانهٔ سرمایهٔ پایانی", `<bdi dir="ltr">${fmt(s.median_final * c.capital_toman / 1e6)}</bdi> م.ت`,
     cls(s.median_final - 1), pct(s.median_final - 1)],
    ["بدترین ۵٪", `<bdi dir="ltr">${fmt(s.p05_final * c.capital_toman / 1e6)}</bdi> م.ت`,
     "down", pct(s.p05_final - 1)],
    ["رشد هر معامله", pct(s.growth_per_trade, 2), cls(s.growth_per_trade), "هندسی"],
    ["افت میانه", pct(s.median_dd), "down", "بدترین افت مسیر"],
  ];
  $("#kpis").innerHTML = kpis.map(([l, v, k, note]) => {
    const vh = /^-/.test(v) ? `<bdi dir="ltr">${v}</bdi>` : v;
    return `<div class="kpi"><div class="label">${l}</div>
      <div class="value ${k}">${vh}</div><div class="note">${note}</div></div>`;
  }).join("");

  const k = DATA.kelly;
  const kellyPos = k.full / (c.stop_pct / 100) * 100;
  $("#lead").innerHTML = `با ریسک <b>${c.risk_pct}٪</b> سرمایه در هر معامله، موقعیت هر سهم
    حدود <b>${(c.risk_pct / c.stop_pct * 100).toFixed(0)}٪</b> سرمایه است. کِلیِ ریاضی
    ${(k.full * 100).toFixed(1)}٪ است — که معادل موقعیت
    <b>${kellyPos.toFixed(0)}٪</b> سرمایه می‌شود و بدون اعتبار ممکن نیست؛ پس سقف واقعی،
    فاصلهٔ حد ضرر است (${c.stop_pct}٪). مهم‌تر از سقف، احتمال ورشکستگی است:
    با عدد فعلی <b>${(DATA.summary.p_ruin * 100).toFixed(1)}٪</b> است.`;
})();

/* ---------- chart ---------- */
function niceTicks(min, max, count = 5) {
  const span = max - min || 1;
  const raw = span / (count - 1);
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(s => s >= raw) || raw;
  const out = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) out.push(+v.toFixed(4));
  return out;
}

function bandPath(t, lo, hi, xs, ys) {
  let d = "";
  for (let i = 0; i < t.length; i++) d += (i ? " L" : "M") + xs(i).toFixed(1) + " " + ys(hi[i]).toFixed(1);
  for (let i = t.length - 1; i >= 0; i--) d += " L" + xs(i).toFixed(1) + " " + ys(lo[i]).toFixed(1);
  return d + " Z";
}

function renderChart() {
  const host = $("#chart");
  const b = DATA.bands;
  host.innerHTML = "";
  if (!b.t.length) { host.innerHTML = '<div class="empty">داده‌ای نیست</div>'; return; }

  const n = b.t.length;
  const vals = [...b.p05, ...b.p95, 100];
  let min = Math.min(...vals), max = Math.max(...vals);
  const pad = (max - min) * 0.06 || 1;
  min -= pad; max += pad;

  const W = Math.max(300, host.clientWidth || 760), H = 340;
  const P = { l: 8, r: 54, t: 14, b: 26 };
  const iw = W - P.l - P.r, ih = H - P.t - P.b;
  const xs = i => P.l + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw);
  const ys = v => P.t + (1 - (v - min) / (max - min)) * ih;

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("height", H);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "باندهای سرمایه در شبیه‌سازی");
  host.appendChild(svg);
  const add = (tag, attrs) => {
    const e = document.createElementNS(ns, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    svg.appendChild(e);
    return e;
  };

  for (const t of niceTicks(min, max, 5)) {
    const y = ys(t);
    add("line", { x1: P.l, x2: P.l + iw, y1: y, y2: y, stroke: "var(--border)", "stroke-width": 1 });
    const lbl = add("text", { x: W - 4, y: y + 4, fill: "var(--text-muted)", "font-size": 10.5,
      "text-anchor": "end", "font-family": "inherit", direction: "ltr",
      style: "unicode-bidi:isolate" });
    lbl.textContent = t.toFixed(0);
  }
  const stepX = Math.max(1, Math.floor((n - 1) / 5));
  for (let i = 0; i < n; i += stepX) {
    const lbl = add("text", { x: xs(i), y: H - 8, fill: "var(--text-muted)", "font-size": 10.5,
      "text-anchor": i === 0 ? "start" : "middle", "font-family": "inherit",
      direction: "ltr", style: "unicode-bidi:isolate" });
    lbl.textContent = b.t[i];
  }

  add("path", { d: bandPath(b.t, b.p05, b.p95, xs, ys), fill: "var(--series-1)", "fill-opacity": 0.13 });
  add("path", { d: bandPath(b.t, b.p25, b.p75, xs, ys), fill: "var(--series-1)", "fill-opacity": 0.22 });

  let d = "";
  for (let i = 0; i < n; i++) d += (i ? " L" : "M") + xs(i).toFixed(1) + " " + ys(b.p50[i]).toFixed(1);
  add("path", { d, fill: "none", stroke: "var(--series-1)", "stroke-width": 2.2,
    "stroke-linejoin": "round" });
  add("line", { x1: P.l, x2: P.l + iw, y1: ys(100), y2: ys(100),
    stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "3 3" });

  $("#legend").innerHTML =
    `<span><i style="background:var(--series-1);opacity:.13"></i>باند ۵–۹۵٪</span>
     <span><i style="background:var(--series-1);opacity:.22"></i>باند ۲۵–۷۵٪</span>
     <span><i style="background:var(--series-1);height:3px"></i>میانه</span>
     <span><i style="background:var(--text-muted);height:1px"></i>سرمایهٔ اولیه</span>`;

  /* crosshair */
  const cross = add("line", { x1: 0, x2: 0, y1: P.t, y2: P.t + ih,
    stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "3 3", opacity: 0 });
  const dot = add("circle", { r: 3.5, fill: "var(--series-1)",
    stroke: "var(--surface-1)", "stroke-width": 2, opacity: 0 });
  const tip = document.createElement("div");
  tip.className = "tip";
  host.appendChild(tip);
  const hit = add("rect", { x: P.l, y: P.t, width: iw, height: ih, fill: "transparent" });
  hit.addEventListener("mousemove", ev => {
    const box = svg.getBoundingClientRect();
    const rel = (ev.clientX - box.left) * (W / box.width);
    const i = Math.max(0, Math.min(n - 1, Math.round((rel - P.l) / iw * (n - 1))));
    const x = xs(i);
    cross.setAttribute("x1", x); cross.setAttribute("x2", x);
    cross.setAttribute("opacity", "1");
    dot.setAttribute("cx", x); dot.setAttribute("cy", ys(b.p50[i]));
    dot.setAttribute("opacity", "1");
    tip.innerHTML = `<div class="d">معاملهٔ ${b.t[i]}</div>`
      + `<div class="r"><span>میانه</span><b>${b.p50[i].toFixed(0)}</b></div>`
      + `<div class="r"><span>۲۵–۷۵٪</span><b>${b.p25[i].toFixed(0)} – ${b.p75[i].toFixed(0)}</b></div>`
      + `<div class="r"><span>۵–۹۵٪</span><b>${b.p05[i].toFixed(0)} – ${b.p95[i].toFixed(0)}</b></div>`;
    tip.style.opacity = "1";
    const scale = box.width / W;
    let left = x * scale - tip.offsetWidth / 2;
    left = Math.min(Math.max(4, left), box.width - tip.offsetWidth - 4);
    tip.style.left = left + "px";
    tip.style.top = "6px";
  });
  hit.addEventListener("mouseleave", () => {
    cross.setAttribute("opacity", "0");
    dot.setAttribute("opacity", "0");
    tip.style.opacity = "0";
  });
}

/* ---------- ladder ---------- */
function renderLadder() {
  const head = `<tr><th>ریسک هر معامله</th><th>موقعیت</th><th>احتمال ورشکستگی</th>
    <th>احتمال سود</th><th>میانهٔ سرمایه</th><th>بدترین ۵٪</th><th>افت میانه</th>
    <th>رشد هر معامله</th></tr>`;
  const cap = DATA.config.capital_toman;
  const cur = DATA.config.risk_pct;
  const body = DATA.ladder.map(r => {
    const hi = Math.abs(r.risk_pct - cur) < 1e-9;
    return `<tr class="${hi ? "row-hi" : ""}">
      <td class="num"><bdi dir="ltr">${r.risk_pct.toFixed(2)}%</bdi></td>
      <td class="num"><bdi dir="ltr">${r.position_pct.toFixed(0)}%</bdi></td>
      <td class="num ${r.p_ruin > 0.15 ? "bad-strong" : ""}">${prob(r.p_ruin)}</td>
      <td class="num">${prob(r.p_profit)}</td>
      <td class="num">${fmt(r.median_final * cap / 1e6)}</td>
      <td class="num down">${fmt(r.p05_final * cap / 1e6)}</td>
      <td class="num down">${pct(r.median_dd)}</td>
      <td class="num ${cls(r.growth_per_trade)}">${pct(r.growth_per_trade, 2)}</td>
    </tr>`;
  }).join("");
  $("#ladder").innerHTML = `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
}

let raf = 0;
function redraw() { cancelAnimationFrame(raf); raf = requestAnimationFrame(renderChart); }
renderLadder();
redraw();
window.addEventListener("resize", redraw);

document.getElementById("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.getAttribute("data-theme") === "dark";
  root.setAttribute("data-theme", dark ? "light" : "dark");
  try { localStorage.setItem("tse-theme", dark ? "light" : "dark"); } catch (e) {}
  redraw();
});
try {
  const saved = localStorage.getItem("tse-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}
setTimeout(redraw, 30);
</script>
</body>
</html>
"""


def render_risk(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__EXTRA__", EXTRA_CSS)
        .replace("__DATA__", data)
    )
