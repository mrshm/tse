"""صفحهٔ یکپارچه: امروز + اسکن + برگه + دفتر + ریسک + بک‌تست + راه‌رونده + جست‌وجو.

یک صفحه، هشت زبانه. زبانهٔ «امروز» از JSONها ساخته می‌شود (بدون شبکه)؛ بقیهٔ
گزارش‌های موجود را در همان صفحه نمایش می‌دهند.
"""

from __future__ import annotations

import json
import os

from .report import CSS

EXTRA_CSS = r"""
  html, body { height: 100%; }
  body { display: flex; flex-direction: column; overflow: hidden; }
  .wrap { max-width: 1180px; }
  .wrap.head { padding-bottom: 0; }
  .top { margin-bottom: 10px; }
  h1 { font-size: 21px; }
  .tabs { display: flex; gap: 2px; overflow-x: auto; border-bottom: 1px solid var(--border);
    scrollbar-width: none; }
  .tabs::-webkit-scrollbar { display: none; }
  .tabs button { appearance: none; background: none; border: 0; border-bottom: 2px solid transparent;
    color: var(--text-secondary); font: inherit; font-size: 13.5px; padding: 8px 12px; cursor: pointer;
    white-space: nowrap; border-radius: 6px 6px 0 0; }
  .tabs button:hover { background: var(--surface-2); color: var(--text-primary); }
  .tabs button.on { color: var(--accent); border-bottom-color: var(--accent); font-weight: 650; }
  .tabs button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .stage { flex: 1 1 auto; min-height: 0; }
  .pane { display: none; height: 100%; }
  .pane.on { display: block; }
  .pane > iframe { display: block; width: 100%; height: 100%; border: 0; background: var(--bg); }
  .pane .scroll { height: 100%; overflow-y: auto; overscroll-behavior: contain; }
  .pane .scroll > .wrap { padding-top: 16px; }
  .pane .card + .card { margin-top: 14px; }
  .banner { border-radius: var(--radius); padding: 10px 13px; font-size: 13px; margin-bottom: 12px;
    border: 1px solid var(--border); background: var(--surface-2); color: var(--text-secondary);
    display: flex; gap: 8px; align-items: flex-start; line-height: 1.7; }
  .banner + .banner { margin-top: -6px; }
  .banner b { color: var(--text-primary); font-weight: 650; }
  .banner.warn { border-color: var(--warning); background: var(--surface-1); }
  .banner.bad { border-color: var(--critical); background: var(--critical-bg); }
  .banner .ic { flex: 0 0 auto; }
  table.t { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  table.t th { text-align: right; font-weight: 600; color: var(--text-secondary); font-size: 11.5px;
    padding: 6px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  table.t td { padding: 7px 8px; border-bottom: 1px solid var(--border); }
  table.t tr:last-child td { border-bottom: 0; }
  table.t td.num, table.t th.num { text-align: left; font-variant-numeric: tabular-nums; white-space: nowrap; }
  table.t td.num bdi { unicode-bidi: isolate; direction: ltr; }
  table.t tr.tot td { font-weight: 650; background: var(--surface-2); }
  table.t tbody tr:hover td { background: var(--surface-2); }
  .tw { overflow-x: auto; }
  .sym b { font-weight: 650; }
  .sym span { display: block; font-size: 10.5px; color: var(--text-muted); margin-top: 1px;
    max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pill { display: inline-block; font-size: 11px; padding: 1px 8px; border-radius: 999px;
    background: var(--surface-2); color: var(--text-secondary); border: 1px solid var(--border);
    white-space: nowrap; }
  .pill.stop { background: var(--critical-bg); color: var(--critical); border-color: transparent; }
  .pill.target { background: var(--good-bg); color: var(--good); border-color: transparent; }
  .pill.over { background: var(--surface-3); color: var(--warning); border-color: transparent; }
  .cmd { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; direction: ltr; text-align: left;
    background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px;
    padding: 7px 10px; font-size: 12px; color: var(--text-primary); display: block; margin: 6px 0 0;
    overflow-x: auto; }
  .cmd .c { color: var(--text-muted); }
  .missing { text-align: center; padding: 54px 20px; color: var(--text-secondary); }
  .missing h3 { margin: 0 0 6px; color: var(--text-primary); font-size: 15px; }
  .missing p { margin: 0; font-size: 13px; }
  .missing .cmd { display: inline-block; text-align: left; margin-top: 12px; }
  .grid2 { display: grid; grid-template-columns: 1fr; gap: 14px; margin-top: 14px; }
  @media (min-width: 900px) { .grid2 { grid-template-columns: 1fr 1fr; } }
  @media (max-width: 720px) {
    .wrap { padding: 14px 12px 28px; }
    h1 { font-size: 18px; }
    .sub { font-size: 11.5px; }
    .kpi .value { font-size: 18px; }
    table.t td, table.t th { padding: 6px; font-size: 11.5px; }
    .tabs button { padding: 8px 9px; font-size: 12.5px; }
  }
  /* فقط داخل اپ اندروید دیده می‌شود؛ در مرورگر مخفی است */
  .sync-fab { position: fixed; inset-inline-start: 14px; bottom: 14px; z-index: 60;
    display: flex; align-items: center; gap: 7px; padding: 10px 15px; border: 0;
    border-radius: 999px; background: var(--accent); color: #fff; font: inherit; font-size: 13.5px;
    font-weight: 650; cursor: pointer; box-shadow: 0 6px 22px rgba(0,0,0,.3);
    padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px)); }
  .sync-fab[disabled] { opacity: .65; cursor: default; }
  .sync-fab .ico { font-size: 15px; line-height: 1; }
  .sync-fab.busy .ico { animation: spin 1.1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
"""

TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>بورس تهران — یک صفحه</title>
<style>
__CSS__
__EXTRA__
</style>
</head>
<body>
<button class="sync-fab" id="syncFab" hidden>
  <span class="ico">⟳</span><span id="syncTxt">به‌روزرسانی</span>
</button>
<div class="wrap head">
  <div class="top">
    <div>
      <h1>بورس تهران — یک صفحه</h1>
      <p class="sub">اسکن، برگهٔ سفارش، دفتر معاملات، ریسک و اعتبارسنجی · <span id="gen">—</span></p>
    </div>
    <button class="icon-btn" id="theme" title="تغییر تم" aria-label="تغییر تم">◐</button>
  </div>
  <nav class="tabs" id="tabs">__TABS__</nav>
</div>

<div class="stage">
  <section class="pane on" id="pane-today">
    <div class="scroll">
      <div class="wrap">
        <div id="banners"></div>
        <div class="kpis" id="kpis"></div>

        <div class="card">
          <div class="card-head">
            <h2>برگهٔ سفارش</h2>
            <span class="hint" id="planHint">—</span>
          </div>
          <div id="orders"></div>
        </div>

        <div class="card">
          <div class="card-head">
            <h2>پوزیشن‌های باز</h2>
            <span class="hint" id="posHint">—</span>
          </div>
          <div id="positions"></div>
        </div>

        <div class="grid2">
          <div class="card">
            <div class="card-head"><h2>ریسک</h2>
              <span class="hint" id="riskHint">—</span></div>
            <div id="riskBox"></div>
          </div>
          <div class="card">
            <div class="card-head"><h2>به‌روزرسانی</h2>
              <span class="hint">به ترتیب</span></div>
            <div class="cmd">python run_daily.py</div>
            <div class="cmd">python run_journal.py open <span class="c"># بعد از خرید</span></div>
            <div class="cmd">python run_journal.py status <span class="c"># هر روز</span></div>
            <p class="assume" style="margin:10px 0 0;font-size:12px;color:var(--text-secondary)">
              این صفحه خودش به بازار وصل نمی‌شود؛ اعداد همان چیزی است که آخرین
              اجرای ابزارها ذخیره کرده‌اند.</p>
          </div>
        </div>
      </div>
    </div>
  </section>
__PANES__
</div>

<script>
const DATA = __DATA__;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = (n, d = 0) => (n === null || n === undefined || !isFinite(n)) ? "—"
  : new Intl.NumberFormat("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }).format(n);
const bdi = (n, d = 0) => `<bdi dir="ltr">${fmt(n, d)}</bdi>`;
const sgn = (n, d = 0) => `<bdi dir="ltr">${n > 0 ? "+" : ""}${fmt(n, d)}</bdi>`;
const pctTxt = (x, d = 1) => (x === null || x === undefined || !isFinite(x)) ? "—"
  : (x > 0 ? "+" : "") + fmt(x * 100, d) + "%";
const pct = (x, d = 1) => `<bdi dir="ltr">${pctTxt(x, d)}</bdi>`;
const prob = x => (x === null || x === undefined || !isFinite(x)) ? "—"
  : `<bdi dir="ltr">${fmt(x * 100, 1)}%</bdi>`;
const mon = (v, d = 1) => `${bdi(v / 1e6, d)} م.ت`;
const cls = x => x > 0 ? "up" : x < 0 ? "down" : "flat";
const empty = (txt, cmd) => `<div class="empty">${txt}${cmd ? `<div class="cmd">${cmd}</div>` : ""}</div>`;

/* ---------- امروز ---------- */
function renderBanners() {
  const out = [];
  const a = DATA.alerts || [];
  if (a.length) {
    const list = a.map(x => `${x.symbol} (${x.text})`).join("، ");
    out.push([`<span class="ic">⛔</span>`,
      `<b>${a.length} پوزیشن نیاز به اقدام دارد:</b> ${list}. ` +
      `با <code>python run_journal.py status</code> ببینید.`, "bad"]);
  }
  const p = DATA.plan;
  if (!p) {
    out.push([`<span class="ic">📄</span>`,
      `برگهٔ سفارشی وجود ندارد. <b>python run_plan.py</b> را اجرا کنید.`, "warn"]);
  } else if (DATA.plan_stale) {
    out.push([`<span class="ic">🕒</span>`,
      `دادهٔ اسکنِ برگه مال <b>${p.source_date_fa || "—"}</b> است، نه امروز. ` +
      `قبل از معامله <b>python run_scan.py</b> و بعد <b>python run_plan.py</b>.`, "warn"]);
  }
  if (!DATA.market) {
    out.push([`<span class="ic">📊</span>`,
      `اسکن امروز موجود نیست. <b>python run_scan.py</b>`, "warn"]);
  }
  $("#banners").innerHTML = out.map(([ic, html, k]) =>
    `<div class="banner ${k}">${ic}<div>${html}</div></div>`).join("");
}

function renderKpis() {
  const m = DATA.market || {}, b = DATA.breadth || {}, j = DATA.journal || {}, r = DATA.risk;
  const st = j.stats || {};
  const chgAbs = m.index_change || 0;
  const chgPct = m.index ? chgAbs / (m.index - chgAbs) : null;
  const openPnl = (j.positions || []).reduce((s, p) => s + (p.pnl || 0), 0);
  const hasPnl = (j.positions || []).some(p => p.pnl !== null && p.pnl !== undefined);

  const k = [];
  k.push(["شاخص کل", m.index ? bdi(m.index) : "—", cls(chgPct),
    m.index ? pct(chgPct) + " · " + (m.state || "") : "داده‌ای نیست"]);
  k.push(["ارزش معاملات", m.activity_value ? bdi(m.activity_value / 1e10) : "—", "flat",
    "میلیارد تومان"]);
  k.push(["مثبت / منفی", b.up !== undefined
    ? `<span class="up">${bdi(b.up)}</span> / <span class="down">${bdi(b.down)}</span>` : "—",
    "flat", "نماد"]);
  k.push(["پوزیشن باز", bdi(st.open || 0, 0), "flat",
    st.invested_open ? mon(st.invested_open) : "سرمایهٔ درگیر"]);
  k.push(["سود باز", hasPnl ? sgn(openPnl) : "—",
    hasPnl ? cls(openPnl) : "flat",
    hasPnl ? "بعد از کارمزد، تومان"
      : ((j.positions || []).length ? "وضعیت را به‌روز کنید" : "پوزیشنی ثبت نشده")]);
  k.push(["ریسک ورشکستگی", r ? prob(r.p_ruin) : "—",
    r && r.p_ruin > 0.1 ? "down" : "flat", r ? `افت ${r.ruin_pct}٪ · ریسک ${r.risk_pct}٪` : "ساخته نشده"]);

  $("#kpis").innerHTML = k.map(([l, v, c, n]) =>
    `<div class="kpi"><div class="label">${l}</div>
      <div class="value ${c}">${v}</div><div class="note">${n}</div></div>`).join("");
}

function ordersTable(p) {
  const rows = p.orders.map(o => {
    const tgt = o.target ? `${bdi(o.target)}` : "—";
    const ret = o.target_ret_pct ? pct(o.target_ret_pct / 100) : "—";
    return `<tr>
      <td class="sym"><b>${o.symbol}</b><span>${o.name || ""}</span></td>
      <td class="num">${bdi(o.qty)}</td>
      <td class="num">${bdi(o.entry)}</td>
      <td class="num">${mon(o.cost)}</td>
      <td class="num">${bdi(o.stop)}</td>
      <td class="num">${tgt}</td>
      <td class="num ${o.target_ret_pct > 0 ? "up" : ""}">${ret}</td>
      <td class="num">${mon(o.risk)}</td>
      <td class="num">${bdi(o.score, 0)}</td>
    </tr>`;
  }).join("");
  const s = p.summary || {};
  return `<div class="tw"><table class="t">
    <thead><tr><th>نماد</th><th class="num">تعداد</th><th class="num">خرید</th>
      <th class="num">مبلغ</th><th class="num">حد ضرر</th><th class="num">هدف</th>
      <th class="num">بازده هدف</th><th class="num">ریسک</th><th class="num">امتیاز</th></tr></thead>
    <tbody>${rows}
      <tr class="tot"><td>جمع سفارش</td><td class="num"></td><td class="num"></td>
        <td class="num">${mon(s.invested || 0)}</td><td class="num">نقد</td><td class="num"></td>
        <td class="num"></td><td class="num">${mon(s.risk_total || 0)}</td><td class="num"></td></tr>
    </tbody></table></div>`;
}

function posTable(j) {
  const rows = j.positions.map(p => {
    const st = p.state || "ok";
    const pill = st === "stop" ? `<span class="pill stop">حد ضرر لمس شد</span>`
      : st === "target" ? `<span class="pill target">هدف رسید</span>`
      : st === "expired" ? `<span class="pill over">مهلت تمام شد</span>`
      : `<span class="pill">باز</span>`;
    const pnl = (p.pnl === null || p.pnl === undefined) ? "—"
      : sgn(p.pnl);
    const pp = (p.pnl_pct === null || p.pnl_pct === undefined) ? "—" : pct(p.pnl_pct / 100, 2);
    return `<tr>
      <td class="sym"><b>${p.symbol}</b><span>${p.name || ""}</span></td>
      <td class="num">${bdi(p.qty)}</td>
      <td class="num">${bdi(p.entry)}</td>
      <td class="num">${p.ltp ? bdi(p.ltp) : "—"}</td>
      <td class="num ${cls(p.pnl)}">${pnl}</td>
      <td class="num ${cls(p.pnl)}">${pp}</td>
      <td>${pill}</td>
      <td class="num">${p.planned_exit_fa || "—"}</td>
    </tr>`;
  }).join("");
  return `<div class="tw"><table class="t">
    <thead><tr><th>نماد</th><th class="num">تعداد</th><th class="num">ورود</th>
      <th class="num">آخرین</th><th class="num">سود (ت)</th><th class="num">سود٪</th>
      <th>وضعیت</th><th class="num">مهلت</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function renderToday() {
  renderBanners();
  renderKpis();

  const p = DATA.plan;
  if (p && p.orders && p.orders.length) {
    $("#orders").innerHTML = ordersTable(p);
    const cfg = p.config || {};
    $("#planHint").innerHTML = `خروج زمانی ${p.exit_date_fa || "—"} · ` +
      `${cfg.positions || 0} سهم · ریسک ${bdi(cfg.risk_pct || 0)}٪ هر معامله` +
      (p.stale ? ` · <b class="down">دادهٔ قدیمی</b>` : "");
  } else {
    $("#orders").innerHTML = empty("برگه‌ای برای امروز ساخته نشده است.", "python run_plan.py");
    $("#planHint").textContent = "—";
  }

  const j = DATA.journal;
  if (j && j.positions && j.positions.length) {
    $("#positions").innerHTML = posTable(j);
    const cnt = j.positions.length;
    $("#posHint").textContent = `${cnt} پوزیشن · ${(DATA.alerts || []).length} نیاز به اقدام`;
  } else {
    $("#positions").innerHTML = empty(
      "هیچ پوزیشن بازی ثبت نشده. سفارش‌های بالا فقط پیشنهادند؛ بعد از خرید ثبتشان کنید.",
      "python run_journal.py open");
    $("#posHint").textContent = "—";
  }

  const r = DATA.risk;
  if (r) {
    const cap = (DATA.plan && DATA.plan.config && DATA.plan.config.capital_toman) || 1e8;
    const tiles = [
      ["احتمال سود", prob(r.p_profit), r.p_profit > 0.5 ? "up" : "down"],
      ["میانهٔ سرمایهٔ پایانی", mon(r.median_final * cap), cls(r.median_final - 1)],
      ["بدترین ۵٪", mon(r.p05_final * cap), "down"],
    ];
    $("#riskBox").innerHTML = `<div class="kpis" style="margin:0">` + tiles.map(([l, v, c]) =>
      `<div class="kpi"><div class="label">${l}</div>
        <div class="value ${c}" style="font-size:18px">${v}</div></div>`).join("") + `</div>
      <p style="font-size:11.5px;color:var(--text-muted);margin:8px 0 0">
        ${r.sims ? `${fmt(r.sims)} مسیر × ${fmt(r.trades)} معامله` : ""} ·
        نرخ برد و R از ${r.source || "پیش‌فرض"}</p>`;
    $("#riskHint").textContent = r.generated_at_fa || "";
  } else {
    $("#riskBox").innerHTML = empty("گزارش ریسک ساخته نشده.", "python run_risk.py");
    $("#riskHint").textContent = "—";
  }
}

/* ---------- دفتر ---------- */
function renderJournal() {
  const j = DATA.journal;
  if (!j) return;
  const st = j.stats || {};
  const tiles = [
    ["معاملات بسته‌شده", bdi(st.closed || 0), "flat", `${bdi(st.open || 0)} باز`],
    ["نرخ برد", st.closed ? prob(st.win_rate) : "—", st.win_rate >= 0.5 ? "up" : "down",
      `${bdi(st.wins || 0)} برد / ${bdi(st.losses || 0)} باخت`],
    ["سود/زیان", st.closed ? sgn(st.pnl) : "—",
      cls(st.pnl || 0), "تومان، بعد از کارمزد"],
    ["نسبت سود به زیان", st.profit_factor ? bdi(st.profit_factor, 2) : "—", "flat", "PF"],
    ["کارمزد پرداختی", st.fees ? bdi(st.fees) : "—", "down",
      st.closed ? prob(st.fees_pct_of_cost / 100) + " سرمایه" : "تومان"],
    ["میانگین نگهداری", st.closed ? bdi(st.avg_holding_days, 1) : "—", "flat", "روز"],
  ];
  $("#jStats").innerHTML = tiles.map(([l, v, c, n]) =>
    `<div class="kpi"><div class="label">${l}</div>
      <div class="value ${c}">${v}</div><div class="note">${n}</div></div>`).join("");

  $("#jOpen").innerHTML = (j.positions && j.positions.length)
    ? posTable(j)
    : empty("پوزیشن بازی نیست.", "python run_journal.py open");
  $("#jOpenHint").textContent = j.positions && j.positions.length
    ? `${j.positions.length} پوزیشن` : "—";

  if (j.closed && j.closed.length) {
    const rows = j.closed.slice().reverse().slice(0, 30).map(c => `<tr>
      <td class="sym"><b>${c.symbol}</b><span>${c.reason || ""}</span></td>
      <td class="num">${bdi(c.qty)}</td>
      <td class="num">${bdi(c.entry)}</td>
      <td class="num">${bdi(c.exit)}</td>
      <td class="num ${cls(c.pnl)}">${sgn(c.pnl)}</td>
      <td class="num ${cls(c.pnl)}">${pct(c.pnl_pct / 100, 2)}</td>
      <td class="num">${bdi(c.holding_days)}</td>
      <td class="num">${c.exit_fa || "—"}</td></tr>`).join("");
    $("#jClosed").innerHTML = `<div class="tw"><table class="t">
      <thead><tr><th>نماد</th><th class="num">تعداد</th><th class="num">ورود</th>
        <th class="num">خروج</th><th class="num">سود (ت)</th><th class="num">سود٪</th>
        <th class="num">روز</th><th class="num">تاریخ</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  } else {
    $("#jClosed").innerHTML = empty("هنوز معامله‌ای بسته نشده است.");
  }
  $("#jClosedHint").textContent = j.closed && j.closed.length
    ? `${j.closed.length} معامله` : "—";
}

/* ---------- زبانه‌ها و تم ---------- */
function showTab(name, push) {
  const btn = $(`.tabs button[data-tab="${name}"]`);
  if (!btn) name = "today";
  $$(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === name));
  $$(".pane").forEach(p => p.classList.toggle("on", p.id === "pane-" + name));
  const f = $(`#pane-${name} iframe[data-src]`);
  if (f) { f.src = f.dataset.src; f.removeAttribute("data-src"); }
  if (push) history.replaceState(null, "", "#" + name);
}

$("#tabs").addEventListener("click", e => {
  const b = e.target.closest("button[data-tab]");
  if (b) showTab(b.dataset.tab, true);
});

function setTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("tse-theme", t); } catch (e) {}
  $$(".pane iframe").forEach(f => { if (f.src) f.src = f.src; });
}
$("#theme").addEventListener("click", () => {
  const dark = document.documentElement.getAttribute("data-theme") === "dark";
  setTheme(dark ? "light" : "dark");
});
try {
  const saved = localStorage.getItem("tse-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}

$("#gen").textContent = DATA.generated_at_fa || "—";
renderToday();
renderJournal();
showTab((location.hash || "").slice(1) || "today", false);

// دکمهٔ به‌روزرسانی فقط وقتی اپ اندروید پل جاوااسکریپت را تزریق کرده باشد ظاهر می‌شود
(function () {
  const fab = document.getElementById("syncFab");
  const txt = document.getElementById("syncTxt");
  if (!fab || !window.TseApp) return;
  fab.hidden = false;
  fab.addEventListener("click", () => {
    if (fab.disabled) return;
    fab.disabled = true;
    fab.classList.add("busy");
    txt.textContent = "شروع…";
    try { TseApp.sync(); } catch (e) { fab.disabled = false; fab.classList.remove("busy"); }
  });
  window.onTseStatus = (raw) => {
    let s = raw;
    if (typeof raw === "string") { try { s = JSON.parse(raw); } catch (e) { return; } }
    if (!s) return;
    if (s.running) {
      fab.disabled = true;
      fab.classList.add("busy");
      txt.textContent = s.step || "به‌روزرسانی…";
    } else if (s.error) {
      fab.disabled = false;
      fab.classList.remove("busy");
      txt.textContent = "خطا — تلاش دوباره";
    } else if (s.done) {
      fab.disabled = false;
      fab.classList.remove("busy");
      txt.textContent = "به‌روزرسانی";
    }
  };
})();
</script>
</body>
</html>
"""


def _pane(key: str, rep: dict) -> str:
    if rep.get("exists"):
        return (
            f'<section class="pane" id="pane-{key}">'
            f'<iframe data-src="{rep["file"]}?embed=1" title="{rep["label"]}" loading="lazy"></iframe>'
            f"</section>"
        )
    hint = (
        "<p>برای ساختش دکمهٔ «به‌روزرسانی» را بزنید.</p>"
        if os.environ.get("TSE_APP")
        else f'<p>برای ساختش اجرا کنید:</p><div class="cmd">{rep["cmd"]}</div>'
    )
    return (
        f'<section class="pane" id="pane-{key}"><div class="scroll"><div class="wrap">'
        f'<div class="missing"><h3>این گزارش هنوز ساخته نشده</h3>'
        f"{hint}</div>"
        f"</div></div></section>"
    )


def _tab(key: str, label: str, on: bool = False) -> str:
    cls = ' class="on"' if on else ""
    return f'<button data-tab="{key}"{cls}>{label}</button>'


JOURNAL_PANE = r"""
  <section class="pane" id="pane-journal"><div class="scroll"><div class="wrap">
    <div class="kpis" id="jStats"></div>
    <div class="card">
      <div class="card-head"><h2>پوزیشن‌های باز</h2>
        <span class="hint" id="jOpenHint">—</span></div>
      <div id="jOpen"></div>
    </div>
    <div class="card">
      <div class="card-head"><h2>معاملات بسته‌شده</h2>
        <span class="hint" id="jClosedHint">—</span></div>
      <div id="jClosed"></div>
    </div>
  </div></div></section>"""


def render_home(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tabs, panes = [], []
    for i, rep in enumerate(payload["reports"]):
        tabs.append(_tab(rep["key"], rep["label"], on=(i == 0)))
        if rep["key"] == "today":
            continue
        panes.append(JOURNAL_PANE if rep["key"] == "journal" else _pane(rep["key"], rep))
    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__EXTRA__", EXTRA_CSS)
        .replace("__TABS__", "".join(tabs))
        .replace("__PANES__", "\n  ".join(panes))
        .replace("__DATA__", data)
    )
