"""گزارش HTML اعتبارسنجی راه‌رونده."""

from __future__ import annotations

import json

from .report import CSS

EXTRA_CSS = r"""
  .chart { position: relative; width: 100%; }
  .chart svg { display: block; width: 100%; height: auto; overflow: visible; }
  .legend { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); margin: 2px 0 6px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend i { width: 10px; height: 3px; border-radius: 2px; display: inline-block; }
  .verdict { border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px;
    background: var(--surface-1); font-size: 13px; line-height: 1.9; color: var(--text-secondary);
    margin-bottom: 16px; }
  .verdict b { color: var(--text-primary); }
  .verdict.warn { border-color: var(--critical); background: var(--critical-bg); color: var(--text-primary); }
  .table-wrap { max-height: none; }
  table { font-size: 12.5px; }
  td.num bdi { unicode-bidi: isolate; }
  .oracle-row td { color: var(--text-muted); font-style: italic; }
  .params { display: inline-flex; gap: 6px; }
  .params span { background: var(--surface-2); border-radius: 6px; padding: 1px 6px; font-size: 11.5px; }
  .ok { color: var(--good); }
  .bad { color: var(--critical); }
"""

TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>اعتبارسنجی راه‌رونده</title>
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
      <h1>اعتبارسنجی راه‌رونده</h1>
      <p class="sub">پارامترها روی بازهٔ آموزش انتخاب، روی بازهٔ آزمونِ دست‌نخورده اجرا ·
        <span id="period">—</span></p>
    </div>
    <button class="icon-btn" id="theme" title="تغییر تم" aria-label="تغییر تم">◐</button>
  </div>

  <div class="chips" id="chips"></div>
  <div class="kpis" id="kpis"></div>
  <div class="verdict" id="verdict"></div>

  <div class="card">
    <div class="card-head">
      <h2>مسیر آزمون</h2>
      <span class="hint">هم‌مقیاس‌شده روی ۱۰۰ در شروع بازهٔ آزمون</span>
    </div>
    <div class="legend" id="legend"></div>
    <div class="chart" id="chart"></div>
    <p class="hint" style="margin:6px 0 0">محور افقی فقط روزهای آزمون است؛ بازه‌های آموزش
      (که در آن‌ها معامله‌ای انجام نشده) حذف شده‌اند.</p>
  </div>

  <div class="card">
    <div class="card-head">
      <h2>فولدها</h2>
      <span class="hint" id="tsum"></span>
    </div>
    <div class="table-wrap" id="folds"></div>
  </div>

  <div class="card">
    <div class="card-head">
      <h2>مقایسه با ترکیب‌های ثابت</h2>
      <span class="hint">همه روی همان بازهٔ آزمون</span>
    </div>
    <div class="table-wrap" id="baselines"></div>
  </div>

  <div class="notes">
    <h3>چطور بخوانیم</h3>
    <ul>
      <li>هر فولد دو بخش دارد: در <b>بازهٔ آموزش</b> بهترین ترکیب از میان همهٔ ترکیب‌ها انتخاب می‌شود،
        بعد همان ترکیب روی <b>بازهٔ آزمون</b> که پارامترها هرگز ندیده‌اند اجرا می‌شود. سرمایه از یک فولد
        به فولد بعد منتقل می‌شود.</li>
      <li>اگر بازده مسیر آزمون نزدیک شاخص کل باشد، «لبهٔ» اسکنر معنادار نیست. تفاوت زیاد به سود
        شاخص، یعنی استراتژی ارزش ریسکش را دارد؛ تفاوت زیاد به زیان، یعنی باید عوض شود.</li>
      <li><b>ردیف «با علم به آینده»</b> بهترین ترکیب روی همان بازه است، انتخاب‌شده با دانستن نتیجه.
        این عدد را هیچ‌وقت در واقعیت نمی‌گرفتی؛ اگر مسیر راه‌رونده خیلی پایین‌تر از آن است،
        یعنی جست‌وجوی پارامتر بیش‌برازش می‌کند.</li>
      <li>تعداد فولدهای سودده مهم‌تر از بازده کل است: استراتژی‌ای که در ۵ فولد از ۶ ضرر داده،
        اتفاقی سود نداده.</li>
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
const RANK = { sharpe: "شارپ", calmar: "کالمر", total_return: "بازده" };

/* ---------- header ---------- */
(function () {
  const c = DATA.config, s = DATA.summary;
  $("#period").textContent = DATA.period.join(" تا ");
  const chips = [
    [`فولد`, fmt(s.folds)],
    [`آموزش / آزمون`, `<bdi dir="ltr">${c.train_days} / ${c.test_days}</bdi> روز`],
    [`معیار انتخاب`, RANK[c.rank] || c.rank],
    [`ترکیب‌های آزمون‌شده`, fmt(c.grid_size)],
    [`نماد`, fmt(c.symbols)],
    [`کارمزد`, `<bdi dir="ltr">${c.buy_fee_pct}% / ${c.sell_fee_pct}%</bdi>`],
    [`صندوق`, c.include_etf ? "بله" : "خیر"],
  ];
  $("#chips").innerHTML = chips.map(([k, v]) => `<span class="chip">${k} <b>${v}</b></span>`).join("");

  const kpis = [
    ["بازده مسیر آزمون", pct(s.total_return), cls(s.total_return)],
    ["بازده شاخص کل", pct(s.benchmark_return), cls(s.benchmark_return)],
    ["بازده مازاد", pct(s.excess_return), cls(s.excess_return)],
    ["حداکثر افت", pct(s.max_drawdown), "down"],
    ["فولدهای سودده", `${fmt(s.folds_positive)} از ${fmt(s.folds)}`, "flat"],
    ["فولدهای بالاتر از شاخص", `${fmt(s.folds_beat_bench)} از ${fmt(s.folds)}`, "flat"],
    ["معاملات", fmt(s.trades), "flat"],
  ];
  $("#kpis").innerHTML = kpis.map(([l, v, k]) => {
    const vh = /^-/.test(v) ? `<bdi dir="ltr">${v}</bdi>` : v;
    return `<div class="kpi"><div class="label">${l}</div><div class="value ${k}">${vh}</div></div>`;
  }).join("");

  const v = $("#verdict");
  if (s.excess_return > 0) {
    v.innerHTML = `<b>در بازهٔ آزمون، استراتژی از شاخص کل جلو زد.</b> `
      + `بازده ${pct(s.total_return)} در برابر ${pct(s.benchmark_return)} شاخص، با حداکثر افت `
      + `${pct(s.max_drawdown)}. ${fmt(s.folds_beat_bench)} فولد از ${fmt(s.folds)} بالاتر از شاخص بود. `
      + `با این حال یک بازهٔ آزمونِ ${fmt(s.folds)} فولدی، هنوز نمونهٔ کوچکی است.`;
  } else {
    v.classList.add("warn");
    v.innerHTML = `<b>استراتژی در بازهٔ آزمون از شاخص کل عقب ماند.</b> `
      + `بازده ${pct(s.total_return)} در برابر ${pct(s.benchmark_return)} شاخص. `
      + `یعنی «انتخاب نماد» ارزش ریسکِ معاملهٔ فعال را در این دوره نداشته و کارمزدها بیشتر از لبهٔ `
      + `استراتژی بوده‌اند. این نتیجه را با یک دورهٔ دیگر هم تکرار کنید.`;
  }
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

function renderChart() {
  const host = $("#chart");
  const curve = DATA.curve;
  host.innerHTML = "";
  if (!curve.length) { host.innerHTML = '<div class="empty">داده‌ای نیست</div>'; return; }

  const series = [
    { name: "استراتژی", color: "var(--series-1)", values: curve.map(r => r.eq) },
  ];
  if (curve.some(r => r.b !== null && r.b !== undefined)) {
    series.push({ name: "شاخص کل", color: "var(--series-2)", values: curve.map(r => r.b) });
  }
  $("#legend").innerHTML = series.map(s =>
    `<span><i style="background:${s.color}"></i>${s.name}</span>`).join("");

  const vals = series.flatMap(s => s.values).filter(v => v !== null && isFinite(v));
  let min = Math.min(...vals), max = Math.max(...vals);
  const pad = (max - min) * 0.08 || 1;
  min -= pad; max += pad;

  const W = Math.max(300, host.clientWidth || 760), H = 320;
  const P = { l: 8, r: 52, t: 14, b: 26 };
  const iw = W - P.l - P.r, ih = H - P.t - P.b;
  const n = curve.length;
  const xs = i => P.l + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw);
  const ys = v => P.t + (1 - (v - min) / (max - min)) * ih;

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("height", H);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "مسیر سرمایهٔ استراتژی در برابر شاخص کل");
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

  const step = Math.max(1, Math.floor((n - 1) / 5));
  for (let i = 0; i < n; i += step) {
    const lbl = add("text", { x: xs(i), y: H - 8, fill: "var(--text-muted)", "font-size": 10.5,
      "text-anchor": i === 0 ? "start" : "middle", "font-family": "inherit",
      direction: "ltr", style: "unicode-bidi:isolate" });
    lbl.textContent = curve[i].fa || "";
  }

  if (min < 100 && max > 100) {
    add("line", { x1: P.l, x2: P.l + iw, y1: ys(100), y2: ys(100),
      stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "3 3" });
  }

  for (const s of series) {
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = s.values[i];
      if (v === null || v === undefined || !isFinite(v)) { started = false; continue; }
      d += (started ? " L" : " M") + xs(i).toFixed(1) + " " + ys(v).toFixed(1);
      started = true;
    }
    add("path", { d, fill: "none", stroke: s.color, "stroke-width": 2,
      "stroke-linejoin": "round", "stroke-linecap": "round" });
  }

  /* برچسب انتهای هر خط */
  const used = [];
  for (const s of series) {
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

  /* crosshair + tooltip */
  const cross = add("line", { x1: 0, x2: 0, y1: P.t, y2: P.t + ih,
    stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "3 3", opacity: 0 });
  const dots = series.map(s => add("circle", { r: 3.5, fill: s.color,
    stroke: "var(--surface-1)", "stroke-width": 2, opacity: 0 }));

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
    const rows = [];
    series.forEach((s, k) => {
      const v = s.values[i];
      const ok = v !== null && v !== undefined && isFinite(v);
      dots[k].setAttribute("opacity", ok ? "1" : "0");
      if (ok) { dots[k].setAttribute("cx", x); dots[k].setAttribute("cy", ys(v)); }
      rows.push(`<div class="r"><span>${s.name}</span><b>${ok ? (v - 100 >= 0 ? "+" : "") + (v - 100).toFixed(1) + "%" : "—"}</b></div>`);
    });
    tip.innerHTML = `<div class="d">${curve[i].fa || ""}</div>${rows.join("")}`;
    tip.style.opacity = "1";
    const scale = box.width / W;
    let left = x * scale - tip.offsetWidth / 2;
    left = Math.min(Math.max(4, left), box.width - tip.offsetWidth - 4);
    tip.style.left = left + "px";
    tip.style.top = "6px";
  });
  hit.addEventListener("mouseleave", () => {
    cross.setAttribute("opacity", "0");
    dots.forEach(d => d.setAttribute("opacity", "0"));
    tip.style.opacity = "0";
  });
}

/* ---------- tables ---------- */
function renderFolds() {
  const head = `<tr><th>#</th><th>بازهٔ آزمون</th><th>ترکیب انتخاب‌شده</th>
    <th>بازده آموزش</th><th>بازده آزمون</th><th>شاخص</th><th>اختلاف</th>
    <th>افت</th><th>معامله</th><th>برد</th></tr>`;
  const body = DATA.folds.map(f => {
    const diff = f.test_return - f.benchmark_return;
    const p = f.params;
    return `<tr>
      <td class="num">${f.fold}</td>
      <td>${f.test_fa[0]} تا ${f.test_fa[1]}</td>
      <td><span class="params"><span>${p.top} سهم</span><span>${p.hold} روز</span>
        <span>${p.stop}×ATR</span><span>${p.target > 0 ? p.target + "×" : "بدون هدف"}</span></span></td>
      <td class="num ${cls(f.train_return)}">${pct(f.train_return)}</td>
      <td class="num ${cls(f.test_return)}">${pct(f.test_return)}</td>
      <td class="num ${cls(f.benchmark_return)}">${pct(f.benchmark_return)}</td>
      <td class="num ${diff > 0 ? "ok" : "bad"}">${pct(diff)}</td>
      <td class="num down">${pct(f.test_dd)}</td>
      <td class="num">${fmt(f.trades)}</td>
      <td class="num">${(f.win_rate * 100).toFixed(0)}%</td>
    </tr>`;
  }).join("");
  $("#folds").innerHTML = `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
  const s = DATA.summary;
  $("#tsum").textContent = `میانهٔ بازده فولدها ${pctTxt(s.median_fold_return)} · `
    + `بدترین ${pctTxt(s.worst_fold)} · بهترین ${pctTxt(s.best_fold)}`;
}

function renderBaselines() {
  const head = `<tr><th>ترکیب</th><th>بازده</th><th>شاخص</th><th>افت</th>
    <th>شارپ</th><th>معامله</th></tr>`;
  const rows = [...DATA.baselines];
  const walkRow = {
    key: "walk", label: "راه‌رونده (انتخاب پویا)",
    total_return: DATA.summary.total_return, sharpe: DATA.summary.sharpe,
    max_drawdown: DATA.summary.max_drawdown, trades: DATA.summary.trades,
    benchmark_return: DATA.summary.benchmark_return,
  };
  rows.unshift(walkRow);
  const body = rows.map(b => {
    const p = b.params;
    const desc = p ? `<span class="params"><span>${p.top_n} سهم</span><span>${p.max_hold} روز</span>
      <span>${p.stop_atr}×ATR</span><span>${p.target_atr > 0 ? p.target_atr + "×" : "بدون هدف"}</span></span>`
      : "";
    const label = b.key === "walk"
      ? `<b>${b.label}</b>`
      : `${b.label}${p ? " " + desc : ""}`;
    return `<tr class="${b.key === "oracle" ? "oracle-row" : ""}">
      <td>${label}</td>
      <td class="num ${cls(b.total_return)}">${pct(b.total_return)}</td>
      <td class="num ${cls(b.benchmark_return)}">${pct(b.benchmark_return)}</td>
      <td class="num down">${pct(b.max_drawdown)}</td>
      <td class="num">${fmt(b.sharpe, 2)}</td>
      <td class="num">${fmt(b.trades)}</td>
    </tr>`;
  }).join("");
  $("#baselines").innerHTML = `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
}

/* ---------- boot ---------- */
let raf = 0;
function redraw() { cancelAnimationFrame(raf); raf = requestAnimationFrame(renderChart); }
renderFolds();
renderBaselines();
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


def render_walkforward(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__EXTRA__", EXTRA_CSS)
        .replace("__DATA__", data)
    )
