"""گزارش HTML مقایسهٔ ترکیب‌های پارامتر."""

from __future__ import annotations

import json

from .report import CSS

EXTRA_CSS = r"""
  .scatter { position: relative; width: 100%; }
  .scatter svg { display: block; width: 100%; height: auto; overflow: visible; }
  .axis-title { font-size: 11px; fill: var(--text-muted); }
  .dot { cursor: pointer; }
  .dot circle { transition: r .1s, fill-opacity .1s; }
  .dot:hover circle { fill-opacity: 1; }
  .best-row { background: var(--accent-soft); }
  .best-row:hover { background: var(--accent-soft); }
  th.sortable { cursor: pointer; user-select: none; }
  th.sortable:hover { color: var(--text-primary); }
  th .arrow { color: var(--accent); font-size: 10px; margin-right: 3px; }
  .table-wrap table { font-size: 12px; }
  .hintline { font-size: 12px; color: var(--text-muted); margin: 8px 0 0; }
"""

TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>جست‌وجوی پارامتر</title>
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
      <h1>جست‌وجوی پارامتر</h1>
      <p class="sub">مقایسهٔ ترکیب‌های استراتژی · <span id="period">—</span></p>
    </div>
    <button class="icon-btn" id="theme" title="تغییر تم" aria-label="تغییر تم">◐</button>
  </div>

  <div class="chips" id="chips"></div>
  <div class="kpis" id="kpis"></div>

  <div class="card">
    <div class="card-head">
      <h2>نقشهٔ ریسک و بازده</h2>
      <span class="hint">هر نقطه یک ترکیب پارامتر است</span>
    </div>
    <div class="scatter" id="scatter"></div>
    <p class="hintline" id="readhint">بالا و چپ بهتر است: بازده بیشتر با افت کمتر.</p>
  </div>

  <div class="card">
    <div class="card-head">
      <h2>همهٔ ترکیب‌ها</h2>
      <span class="hint" id="tsum"></span>
    </div>
    <div class="table-wrap" id="table"></div>
  </div>

  <div class="notes">
    <h3>چطور بخوانیم</h3>
    <ul>
      <li><b>شارپ</b> = بازده تعدیل‌شده با نوسان روزانه؛ <b>کالمر</b> = CAGR ÷ حداکثر افت. کالمر برای مقایسهٔ دوره‌های پرنوسان منصفانه‌تر است.</li>
      <li>ترکیبی که فقط در یک بازهٔ صعودی خوب است، لزوماً پایدار نیست. با <code>--days</code>های مختلف و دامنه‌های مختلف نماد تکرارش کنید.</li>
      <li>«کارمزد» سهم سرمایه‌ای است که صرف هزینهٔ معاملات شده — با کاهش تعداد معاملات پایین می‌آید.</li>
      <li>بهترین ردیف بر اساس معیار انتخابی (<span id="rankname"></span>) مشخص شده است، نه بر اساس بازده صرف.</li>
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
const bdi = s => `<bdi dir="ltr">${s}</bdi>`;
const cls = x => x > 0 ? "up" : x < 0 ? "down" : "flat";

const RANK_LABEL = { sharpe: "شارپ", calmar: "کالمر", return: "بازده" };

/* ---------- header ---------- */
(function () {
  const c = DATA.config, g = c.grid, b = DATA.best;
  $("#period").textContent = DATA.period.join(" تا ");
  $("#rankname").textContent = RANK_LABEL[DATA.rank] || DATA.rank;
  const chips = [
    [`دوره`, `${c.days} روز`],
    [`نمادها`, fmt(c.symbols)],
    [`نگهداری`, bdi(g.hold.join(" · ")) + " روز"],
    [`حد ضرر`, bdi(g.stop.join(" · ")) + "×ATR"],
    [`هدف`, bdi(g.target.map(t => t > 0 ? t + "×" : "بدون هدف").join(" · "))],
    [`سهم هم‌زمان`, bdi(g.top.join(" · "))],
    [`کارمزد`, bdi(`${c.buy_fee_pct}% / ${c.sell_fee_pct}%`)],
    [`صندوق`, c.include_etf ? "بله" : "خیر"],
  ];
  $("#chips").innerHTML = chips.map(([k, v]) => `<span class="chip">${k} <b>${v}</b></span>`).join("");

  const minDd = Math.max(...DATA.combos.map(x => x.max_drawdown));
  const wins = DATA.combos.filter(x => x.total_return > 0).length;
  const kpis = [
    [`بهترین ${RANK_LABEL[DATA.rank] || DATA.rank}`,
     DATA.rank === "return" ? pctTxt(b.total_return) : fmt(b[DATA.rank], 2),
     DATA.rank === "return" ? cls(b.total_return) : "flat"],
    [`بازده بهترین ترکیب`, pctTxt(b.total_return), cls(b.total_return)],
    [`بازده شاخص کل`, pctTxt(DATA.benchmark_return), cls(DATA.benchmark_return)],
    [`ترکیب‌های سودده`, `${wins} از ${DATA.combos.length}`, "flat"],
    [`کمترین افت`, bdi(pctTxt(minDd)), "down"],
    [`ترکیب‌ها`, fmt(DATA.combos.length), "flat"],
  ];
  $("#kpis").innerHTML = kpis.map(([l, v, k]) => {
    const vh = /^-/.test(v) ? bdi(v) : v;
    return `<div class="kpi"><div class="label">${l}</div><div class="value ${k}">${vh}</div></div>`;
  }).join("");
  const tiles = $("#kpis").children;
  tiles[0].insertAdjacentHTML("beforeend",
    `<div class="note">${b.top} سهم · نگهداری ${b.hold}${b.target > 0 ? " · هدف " + b.target : ""}</div>`);
})();

/* ---------- scatter ---------- */
function renderScatter() {
  const host = $("#scatter");
  const pts = DATA.combos;
  host.innerHTML = "";
  if (!pts.length) return;

  const W = Math.max(300, host.clientWidth || 700), H = 380;
  const P = { l: 10, r: 56, t: 16, b: 42 };
  const iw = W - P.l - P.r, ih = H - P.t - P.b;

  const xs0 = pts.map(p => p.max_drawdown * 100);
  const ys0 = pts.map(p => p.total_return * 100);
  const xMin = Math.min(...xs0, 0) * 1.08 || -1;
  const xMax = Math.max(...xs0, 0) + 1;
  const ySpan = (Math.max(...ys0) - Math.min(...ys0)) || 10;
  const yMin = Math.min(...ys0) - ySpan * 0.12;
  const yMax = Math.max(...ys0) + ySpan * 0.12;

  const X = v => P.l + (v - xMin) / (xMax - xMin) * iw;
  const Y = v => P.t + (1 - (v - yMin) / (yMax - yMin)) * ih;

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("height", H);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "نقشه ریسک و بازده ترکیب‌ها");
  host.appendChild(svg);

  const add = (tag, attrs, parent) => {
    const e = document.createElementNS(ns, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    (parent || svg).appendChild(e);
    return e;
  };

  const ticksX = niceTicks(xMin, xMax, 5);
  const ticksY = niceTicks(yMin, yMax, 5);
  for (const t of ticksY) {
    const y = Y(t);
    add("line", { x1: P.l, x2: P.l + iw, y1: y, y2: y, stroke: "var(--border)", "stroke-width": 1 });
    const e = add("text", { x: W - 4, y: y + 4, fill: "var(--text-muted)", "font-size": 10.5,
      "text-anchor": "end", "font-family": "inherit", direction: "ltr",
      style: "unicode-bidi:isolate" });
    e.textContent = t.toFixed(0) + "%";
  }
  for (const t of ticksX) {
    const x = X(t);
    add("line", { x1: x, x2: x, y1: P.t, y2: P.t + ih, stroke: "var(--border)", "stroke-width": 1 });
    const e = add("text", { x, y: H - 20, fill: "var(--text-muted)", "font-size": 10.5,
      "text-anchor": "middle", "font-family": "inherit", direction: "ltr",
      style: "unicode-bidi:isolate" });
    e.textContent = t.toFixed(0) + "%";
  }

  const bench = DATA.benchmark_return * 100;
  const benchIn = bench >= yMin && bench <= yMax;
  if (benchIn) {
    add("line", { x1: P.l, x2: P.l + iw, y1: Y(bench), y2: Y(bench), stroke: "var(--series-2)",
      "stroke-width": 1.5, "stroke-dasharray": "5 4" });
    const bl = add("text", { x: P.l + 4, y: Y(bench) - 6, fill: "var(--text-secondary)",
      "font-size": 10.5, "font-family": "inherit" });
    bl.textContent = "شاخص کل " + (bench >= 0 ? "+" : "") + bench.toFixed(0) + "%";
  } else {
    const bl = add("text", { x: P.l + iw, y: P.t + 10, fill: "var(--series-2)",
      "font-size": 10.5, "text-anchor": "end", "font-family": "inherit" });
    bl.textContent = "شاخص کل " + (bench >= 0 ? "+" : "") + bench.toFixed(0) + "% ↑";
    const hint = $("#readhint");
    if (hint) hint.textContent = "بالا و چپ بهتر است: بازده بیشتر با افت کمتر. "
      + "بازده شاخص کل (" + (bench >= 0 ? "+" : "") + bench.toFixed(0)
      + "٪) بالاتر از محدودهٔ نمودار است.";
  }

  const tip = document.createElement("div");
  tip.className = "tip";
  host.appendChild(tip);

  const best = DATA.best;
  const isBest = p => p.top === best.top && p.hold === best.hold && p.stop === best.stop
    && p.target === best.target && p.trail === best.trail;

  for (const p of pts) {
    const cx = X(p.max_drawdown * 100), cy = Y(p.total_return * 100);
    const b = isBest(p);
    const g = add("g", { class: "dot" });
    if (b) add("circle", { cx, cy, r: 9, fill: "none", stroke: "var(--accent)",
      "stroke-width": 2, "fill-opacity": 1 }, g);
    add("circle", { cx, cy, r: 5, fill: "var(--accent)", "fill-opacity": 0.72,
      stroke: "var(--surface-1)", "stroke-width": 1.5 }, g);
    g.addEventListener("mouseenter", () => {
      tip.innerHTML =
        `<div class="d">${p.top} سهم · نگهداری ${p.hold} · حد ضرر ${p.stop}×ATR` +
        `${p.target > 0 ? " · هدف " + p.target + "×ATR" : " · بدون هدف"}` +
        `${p.trail > 0 ? " · تریل " + p.trail + "×ATR" : ""}</div>` +
        `<div class="r"><span>بازده</span><b class="${cls(p.total_return)}">${pctTxt(p.total_return)}</b></div>` +
        `<div class="r"><span>حداکثر افت</span><b>${pctTxt(p.max_drawdown)}</b></div>` +
        `<div class="r"><span>شارپ</span><b>${fmt(p.sharpe, 2)}</b></div>` +
        `<div class="r"><span>معاملات</span><b>${fmt(p.trades)}</b></div>`;
      tip.style.opacity = "1";
      const box = svg.getBoundingClientRect(), scale = box.width / W;
      let left = cx * scale - tip.offsetWidth / 2;
      left = Math.min(Math.max(4, left), box.width - tip.offsetWidth - 4);
      tip.style.left = left + "px";
      tip.style.top = Math.max(0, cy * scale - tip.offsetHeight - 10) + "px";
    });
    g.addEventListener("mouseleave", () => { tip.style.opacity = "0"; });
  }

}

function niceTicks(min, max, count) {
  const span = max - min || 1;
  const raw = span / (count - 1);
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(s => s >= raw) || raw;
  const out = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) out.push(+v.toFixed(4));
  return out;
}

/* ---------- table ---------- */
const COLS = [
  { key: "rank", label: "#", sort: false },
  { key: "top", label: "سهم" },
  { key: "hold", label: "نگهداری" },
  { key: "stop", label: "حد ضرر", d: 1, suffix: "×" },
  { key: "target", label: "هدف", d: 1, suffix: "×", zero: "—" },
  { key: "trail", label: "تریل", d: 1, suffix: "×", zero: "—" },
  { key: "total_return", label: "بازده", pct: true, color: true },
  { key: "cagr", label: "CAGR", pct: true },
  { key: "sharpe", label: "شارپ", d: 2 },
  { key: "calmar", label: "کالمر", d: 2 },
  { key: "max_drawdown", label: "افت", pct: true },
  { key: "trades", label: "معاملات" },
  { key: "win_rate", label: "برد", pct: true },
  { key: "fees_pct", label: "کارمزد", pct: true },
];

let sortKey = DATA.rank === "return" ? "total_return" : DATA.rank;
let sortDir = -1;

function cell(c, col) {
  const v = c[col.key];
  if (col.key === "rank") return c._rank;
  if (v === null || v === undefined) return "—";
  if (col.pct) return `<bdi dir="ltr">${pctTxt(v)}</bdi>`;
  if (col.key === "target" || col.key === "trail") {
    return v > 0 ? `<bdi dir="ltr">${v.toFixed(col.d || 0)}×</bdi>` : "—";
  }
  if (col.suffix) return `<bdi dir="ltr">${v.toFixed(col.d || 0)}${col.suffix}</bdi>`;
  if (col.d !== undefined) return `<bdi dir="ltr">${fmt(v, col.d)}</bdi>`;
  return `<bdi dir="ltr">${fmt(v)}</bdi>`;
}

function renderTable() {
  const host = $("#table");
  const rows = DATA.combos.map((c, i) => ({ ...c, _rank: i + 1 }));
  const best = DATA.best;
  const sorted = rows.slice().sort((a, b) => sortDir * ((a[sortKey] ?? -9e9) - (b[sortKey] ?? -9e9)));

  const isBest = p => p.top === best.top && p.hold === best.hold && p.stop === best.stop
    && p.target === best.target && p.trail === best.trail;

  const head = COLS.map(col => {
    if (col.sort === false) return `<th>${col.label}</th>`;
    const arrow = sortKey === col.key ? `<span class="arrow">${sortDir < 0 ? "▼" : "▲"}</span>` : "";
    return `<th class="sortable" data-key="${col.key}">${col.label}${arrow}</th>`;
  }).join("");

  const body = sorted.map(c => {
    const tds = COLS.map(col => {
      const v = c[col.key];
      const k = col.color ? cls(v) : "";
      return `<td class="num ${k}">${cell(c, col)}</td>`;
    }).join("");
    return `<tr class="${isBest(c) ? "best-row" : ""}">${tds}</tr>`;
  }).join("");

  host.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  host.querySelectorAll("th.sortable").forEach(th => {
    th.addEventListener("click", () => {
      const k = th.dataset.key;
      if (sortKey === k) sortDir *= -1; else { sortKey = k; sortDir = -1; }
      renderTable();
    });
  });
}

$("#tsum").textContent = (() => {
  const tot = DATA.combos.length;
  const win = DATA.combos.filter(c => c.total_return > DATA.benchmark_return).length;
  return `${tot} ترکیب · ${win} ترکیب بالاتر از شاخص`;
})();

/* ---------- boot ---------- */
let raf = 0;
function renderCharts() {
  cancelAnimationFrame(raf);
  raf = requestAnimationFrame(renderScatter);
}
renderTable();
renderCharts();
window.addEventListener("resize", renderCharts);

document.getElementById("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.getAttribute("data-theme") === "dark";
  root.setAttribute("data-theme", dark ? "light" : "dark");
  try { localStorage.setItem("tse-theme", dark ? "light" : "dark"); } catch (e) {}
  renderCharts();
});
try {
  const saved = localStorage.getItem("tse-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}
setTimeout(renderCharts, 30);
</script>
</body>
</html>
"""


def render_sweep(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__EXTRA__", EXTRA_CSS)
        .replace("__DATA__", data)
    )
