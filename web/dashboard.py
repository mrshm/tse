"""ساخت داشبورد HTML تک‌فایلی از خروجی اسکن."""

from __future__ import annotations

import json

TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>اسکنر بورس تهران</title>
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
    --accent-soft: #dce9fa;
    --good: #0f7a0f;
    --good-bg: #e6f4e6;
    --critical: #b83030;
    --critical-bg: #fae9e9;
    --warning: #8a5a00;
    --warning-bg: #fdf1d8;
    --shadow: 0 1px 2px rgba(20,20,10,.06), 0 4px 16px rgba(20,20,10,.04);
    --radius: 12px;
  }
  :root[data-theme="dark"] {
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
    --accent-soft: #1c2f47;
    --good: #3fc23f;
    --good-bg: #162b16;
    --critical: #e66767;
    --critical-bg: #331a1a;
    --warning: #fab219;
    --warning-bg: #33280d;
    --shadow: 0 1px 2px rgba(0,0,0,.4);
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text-primary);
    font-family: "Vazirmatn", "Vazir", "IRANSansX", "IRANSans", "Segoe UI", Tahoma, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 1440px; margin: 0 auto; padding: 24px 20px 64px; }

  header.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
  h1 { font-size: 22px; font-weight: 700; margin: 0 0 4px; letter-spacing: -.2px; }
  .sub { color: var(--text-secondary); font-size: 13px; margin: 0; }
  .sub b { color: var(--text-primary); font-weight: 600; }
  .pill { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px;
          background: var(--surface-2); border: 1px solid var(--border); font-size: 12px; color: var(--text-secondary); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
  .dot.open { background: var(--good); box-shadow: 0 0 0 3px var(--good-bg); }

  .icon-btn { background: var(--surface-1); border: 1px solid var(--border); color: var(--text-secondary);
              border-radius: 10px; padding: 8px 12px; cursor: pointer; font: inherit; font-size: 13px; }
  .icon-btn:hover { background: var(--surface-2); color: var(--text-primary); }
  .icon-btn:focus-visible, .chip:focus-visible, input:focus-visible, th:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  /* KPI row */
  .kpis { display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 12px; margin-bottom: 20px; }
  .kpi { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius);
         padding: 14px 16px; box-shadow: var(--shadow); min-width: 0; }
  .kpi .label { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .kpi .value { font-size: 22px; font-weight: 700; letter-spacing: -.4px; font-variant-numeric: tabular-nums; }
  .kpi .delta { font-size: 12px; margin-top: 2px; color: var(--text-secondary); display: flex; gap: 6px; align-items: center; }
  .up { color: var(--good); }
  .down { color: var(--critical); }
  .flat { color: var(--text-muted); }
  .breadth-bar { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; display: flex; margin-top: 8px; gap: 2px; }
  .breadth-bar span { display: block; height: 100%; }
  .breadth-bar .b-up { background: var(--good); border-radius: 3px 0 0 3px; }
  .breadth-bar .b-down { background: var(--critical); border-radius: 0 3px 3px 0; }
  .breadth-bar .b-flat { background: var(--text-muted); }

  /* controls */
  .controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
  .search { position: relative; flex: 1 1 220px; max-width: 320px; }
  .search input { width: 100%; background: var(--surface-1); border: 1px solid var(--border); color: var(--text-primary);
                  border-radius: 10px; padding: 9px 34px 9px 12px; font: inherit; font-size: 13px; }
  .search svg { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); color: var(--text-muted); }
  .chip { background: var(--surface-1); border: 1px solid var(--border); color: var(--text-secondary);
          border-radius: 999px; padding: 6px 12px; font: inherit; font-size: 12.5px; cursor: pointer; }
  .chip:hover { background: var(--surface-2); }
  .chip.active { background: var(--accent-soft); border-color: var(--accent); color: var(--text-primary); font-weight: 600; }
  .range-wrap { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--text-secondary); }
  input[type=range] { accent-color: var(--accent); width: 110px; }
  .check { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--text-secondary); cursor: pointer; user-select: none; }
  .check input { accent-color: var(--accent); }

  /* table */
  .card { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius);
          box-shadow: var(--shadow); overflow: hidden; }
  .table-scroll { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  thead th { position: sticky; top: 0; z-index: 2; background: var(--surface-2); color: var(--text-secondary);
             font-weight: 600; font-size: 12px; text-align: right; padding: 10px 10px; white-space: nowrap;
             border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; }
  thead th:hover { color: var(--text-primary); }
  thead th .arrow { opacity: .45; font-size: 10px; margin-inline-start: 3px; }
  thead th[aria-sort="ascending"] .arrow, thead th[aria-sort="descending"] .arrow { opacity: 1; color: var(--accent); }
  tbody td { padding: 9px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; white-space: nowrap; }
  tbody tr.main-row { cursor: pointer; }
  tbody tr.main-row:hover { background: var(--surface-2); }
  tbody tr.main-row.open { background: var(--surface-2); }
  tbody tr:last-child td { border-bottom: none; }

  .rank { color: var(--text-muted); font-variant-numeric: tabular-nums; width: 34px; }
  .sym { font-weight: 700; font-size: 13.5px; }
  .sym small { display: block; font-weight: 400; font-size: 11px; color: var(--text-muted); max-width: 170px;
               overflow: hidden; text-overflow: ellipsis; }
  .mkt { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: var(--surface-3); color: var(--text-secondary); }
  .num { font-variant-numeric: tabular-nums; }
  .price { font-weight: 600; }
  .spark-cell svg { display: block; }
  .score-cell { display: flex; align-items: center; gap: 8px; min-width: 96px; }
  .score-val { font-weight: 700; font-variant-numeric: tabular-nums; width: 34px; }
  .meter { flex: 1; height: 5px; background: var(--surface-3); border-radius: 3px; overflow: hidden; min-width: 40px; }
  .meter span { display: block; height: 100%; border-radius: 3px; background: var(--accent); }
  .tags { display: flex; gap: 4px; flex-wrap: wrap; max-width: 260px; }
  .tag { font-size: 10.5px; padding: 1px 7px; border-radius: 999px; background: var(--surface-2);
         border: 1px solid var(--border); color: var(--text-secondary); white-space: nowrap; }
  .tag.etf { background: var(--accent-soft); border-color: transparent; color: var(--accent); }
  .tag.pos { background: var(--good-bg); border-color: transparent; color: var(--good); }
  .tag.neg { background: var(--critical-bg); border-color: transparent; color: var(--critical); }
  .tag.warn { background: var(--warning-bg); border-color: transparent; color: var(--warning); }

  /* detail */
  tr.detail-row > td { padding: 0; background: var(--surface-2); border-bottom: 1px solid var(--border); }
  .detail { display: grid; grid-template-columns: 1.4fr 1fr; gap: 20px; padding: 16px 18px 20px; }
  .detail h3 { font-size: 12px; color: var(--text-secondary); font-weight: 600; margin: 0 0 10px; }
  .chart-box { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; position: relative; }
  .chart-tip { position: absolute; top: 10px; display: none; background: var(--surface-1); border: 1px solid var(--border);
               border-radius: 8px; padding: 5px 9px; font-size: 11px; box-shadow: var(--shadow); pointer-events: none;
               white-space: nowrap; z-index: 5; color: var(--text-primary); font-variant-numeric: tabular-nums; }
  .setup-badge { font-size: 10.5px; font-weight: 500; color: var(--accent); background: var(--accent-soft);
                 border-radius: 999px; padding: 0 7px; margin-inline-start: 4px; }
  .chart-box svg { display: block; width: 100%; height: auto; }
  .axis-label { font-size: 10px; fill: var(--text-muted); }
  .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px 14px; }
  .metric { background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 7px 10px; }
  .metric .k { font-size: 10.5px; color: var(--text-muted); }
  .metric .v { font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .levels { margin-top: 12px; }
  .levels table { font-size: 12px; }
  .levels td { border: none; padding: 3px 0; white-space: nowrap; }
  .levels td:first-child { color: var(--text-muted); padding-inline-end: 14px; }
  .hint { color: var(--text-muted); font-size: 11px; margin-top: 8px; line-height: 1.7; }

  footer.note { margin-top: 18px; color: var(--text-muted); font-size: 11.5px; line-height: 1.9; }
  footer.note b { color: var(--text-secondary); }

  .empty { padding: 40px 20px; text-align: center; color: var(--text-muted); }

  @media (max-width: 1100px) {
    .kpis { grid-template-columns: repeat(3, minmax(0,1fr)); }
    .detail { grid-template-columns: 1fr; }
  }
  @media (max-width: 720px) {
    .wrap { padding: 16px 12px 48px; }
    .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); }
    .col-hide-sm { display: none; }
    .tags { max-width: 150px; }
  }
  body.embed .top { display: none; }
  body.embed .wrap { padding-top: 14px; }
</style>
</head>
<body>
<script>if(location.search.indexOf("embed")>=0)document.body.classList.add("embed")</script>
<div class="wrap">
  <header class="top">
    <div>
      <h1>اسکنر نوسان‌گیری بورس تهران</h1>
      <p class="sub">
        تاریخ داده: <b id="lastDate">—</b>
        <span class="pill" style="margin-inline-start:8px">
          <span class="dot" id="stateDot"></span><span id="stateText">—</span>
        </span>
        <span class="pill" style="margin-inline-start:6px">ساخت: <span id="genAt">—</span></span>
        <span class="pill" style="margin-inline-start:6px" id="setupHint">ستاپ: —</span>
      </p>
    </div>
    <button class="icon-btn" id="themeBtn" type="button" aria-label="تغییر تم">◐ تم</button>
  </header>

  <section class="kpis" id="kpis"></section>

  <section class="controls" aria-label="فیلترها">
    <div class="search">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="search" placeholder="جستجوی نماد یا نام شرکت…" autocomplete="off">
    </div>
    <button class="chip active" data-mkt="all" type="button">همه</button>
    <button class="chip" data-mkt="بورس" type="button">بورس</button>
    <button class="chip" data-mkt="فرابورس" type="button">فرابورس</button>
    <button class="chip" data-mkt="پایه" type="button">پایه</button>
    <button class="chip" data-mkt="کالا" type="button">کالا</button>
    <label class="range-wrap">
      حداقل امتیاز <input id="minScore" type="range" min="0" max="90" step="5" value="0">
      <b id="minScoreVal" class="num">۰</b>
    </label>
    <label class="check"><input id="hideRights" type="checkbox" checked> پنهان‌کردن حق تقدم</label>
    <label class="check"><input id="hideEtf" type="checkbox"> پنهان‌کردن صندوق‌ها</label>
    <span class="sub" id="resultCount"></span>
  </section>
  <section class="controls" aria-label="فیلتر ستاپ" style="margin-top:-4px">
    <span class="sub" style="font-size:12px">نوع ستاپ:</span>
    <button class="chip active" data-setup="all" type="button">همه</button>
    <button class="chip" data-setup="شکست سقف" type="button">شکست سقف</button>
    <button class="chip" data-setup="پولبک" type="button">پولبک</button>
    <button class="chip" data-setup="ادامه روند" type="button">ادامه روند</button>
  </section>

  <div class="card">
    <div class="table-scroll">
      <table id="tbl">
        <thead>
          <tr>
            <th data-sort="rank" style="width:34px">#</th>
            <th data-sort="symbol">نماد</th>
            <th data-sort="market" class="col-hide-sm">بازار</th>
            <th data-sort="close">قیمت (تومان)</th>
            <th data-sort="change_pct">تغییر ٪</th>
            <th data-sort="spark" class="col-hide-sm">۳۰ روز</th>
            <th data-sort="vol_ratio" class="col-hide-sm">حجم نسبی</th>
            <th data-sort="rsi14" class="col-hide-sm">RSI</th>
            <th data-sort="score">امتیاز</th>
            <th data-sort="tags" class="col-hide-sm">سیگنال‌ها</th>
            <th data-sort="value_avg20" class="col-hide-sm">میانگین ارزش (میلیارد تومان)</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div class="empty" id="empty" style="display:none">نمادی با این فیلترها پیدا نشد.</div>
  </div>

  <footer class="note">
    <b>یادآوری مهم:</b> این ابزار فقط تحلیل کمکی است و توصیه به خرید یا فروش نیست؛ خروجی آن بر پایه دادهٔ تاریخی است و آینده را تضمین نمی‌کند.
    در بورس تهران تسویهٔ معاملات <b>T+2</b> است، بنابراین فروش سهمی که امروز خریده‌اید در همان روز ممکن نیست؛ «نوسان‌گیری روزانه» عملاً یعنی نگهداری یک تا چند روز.
    دادهٔ TSETMC ممکن است با تأخیر باشد. حد ضرر و اندازهٔ موقعیت را همیشه خودتان تعیین کنید.
  </footer>
</div>

<script>
const DATA = __DATA__;

const fa = (n, d=0) => Number(n).toLocaleString('fa-IR', {minimumFractionDigits:d, maximumFractionDigits:d});
const toman = v => fa(Math.round(v/10));
const billionToman = v => fa(v/1e10, 1);
const pct = v => (v>0?'+':'') + fa(v, 2) + '٪';

const state = { mkt: 'all', setup: 'all', q: '', minScore: 0, hideRights: true, hideEtf: false, sort: 'score', dir: -1, open: new Set() };
const CHART = { W: 640, H: 190, padL: 8, padR: 46, padT: 12, priceH: 120 };

function sparkPath(vals, w=110, h=30, pad=3) {
  if (!vals || vals.length < 2) return '';
  const min = Math.min(...vals), max = Math.max(...vals), rng = (max-min)||1;
  const step = (w-pad*2)/(vals.length-1);
  return vals.map((v,i) => {
    const x = pad + i*step;
    const y = h-pad - ((v-min)/rng)*(h-pad*2);
    return (i? 'L':'M') + x.toFixed(1) + ',' + y.toFixed(1);
  }).join(' ');
}

function sparkline(vals) {
  const d = sparkPath(vals);
  if (!d) return '';
  return `<svg width="110" height="30" viewBox="0 0 110 30" aria-hidden="true">
    <path d="${d}" fill="none" stroke="var(--text-muted)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

function scoreMeter(score) {
  return `<div class="score-cell"><span class="score-val">${fa(score,1)}</span>
    <span class="meter"><span style="width:${Math.max(2,Math.min(100,score))}%"></span></span></div>`;
}

function tagClass(t) {
  if (t.includes('ورود پول')) return 'pos';
  if (t.includes('خروج پول') || t.includes('نقدشوندگی کم') || t.includes('فاصله زیاد')) return 'neg';
  if (t.includes('اشباع خرید') || t.includes('اشباع فروش')) return 'warn';
  return '';
}

function rows() {
  let r = DATA.rows.slice();
  if (state.mkt !== 'all') r = r.filter(x => x.market === state.mkt);
  if (state.setup !== 'all') r = r.filter(x => x.setup === state.setup);
  if (state.hideRights) r = r.filter(x => !x.is_rights);
  if (state.hideEtf) r = r.filter(x => !x.is_etf);
  if (state.minScore > 0) r = r.filter(x => x.score >= state.minScore);
  if (state.q) {
    const q = state.q.trim().toLowerCase();
    r = r.filter(x => (x.symbol||'').toLowerCase().includes(q) || (x.name||'').toLowerCase().includes(q));
  }
  const k = state.sort;
  r.sort((a,b) => {
    const av = k === 'symbol' || k === 'market' ? String(a[k]) : Number(a[k]||0);
    const bv = k === 'symbol' || k === 'market' ? String(b[k]) : Number(b[k]||0);
    if (typeof av === 'string') return av.localeCompare(bv,'fa') * state.dir;
    return (av - bv) * state.dir;
  });
  return r;
}

function detailHtml(x) {
  const L = [
    {k:'بازده ۱ روزه', v: pct(x.ret1)}, {k:'بازده ۵ روزه', v: pct(x.ret5)}, {k:'بازده ۲۰ روزه', v: pct(x.ret20)},
    {k:'نوسان (ATR)', v: fa(x.atr_pct,1)+'٪'}, {k:'فاصله از سقف ۲۰ روزه', v: fa(Math.abs(x.dist_high20)<0.05?0:x.dist_high20,1)+'٪'},
    {k:'جریان حقیقی', v: pct(x.real_flow*100)},
    {k:'عدم‌تعادل مظنه', v: fa(x.book_imbalance*100,1)+'٪'}, {k:'P/E', v: x.pe ? fa(x.pe,1) : '—'},
    {k:'EPS', v: x.eps ? fa(x.eps) : '—'},
    {k:'آخرین معامله', v: x.last_price ? toman(x.last_price) : '—'},
    {k:'ارزش معاملات امروز', v: billionToman(x.value)+' میلیارد تومان'},
  ].map(m => `<div class="metric"><div class="k">${m.k}</div><div class="v">${m.v}</div></div>`).join('');

  const price = x.close, stop = x.stop, t1 = x.target1, t2 = x.target2;
  return `<div class="detail">
    <div class="chart-box">
      <h3>روند قیمت پایانی — ۳۰ روز (تومان)</h3>
      ${bigChart(x)}
      <div class="chart-tip"></div>
      <div class="hint">خط: قیمت پایانی · ستون‌ها: حجم معاملات · برای دیدن مقدار هر روز، نشانگر را روی نمودار ببرید</div>
    </div>
    <div>
      <h3>مشخصات و سطوح پیشنهادی</h3>
      <div class="metrics">${L}</div>
      <div class="levels">
        <table>
          <tr><td>محدودهٔ ورود</td><td class="num">${toman(x.entry_low)} – ${toman(x.entry_high)} تومان</td></tr>
          <tr><td>حد ضرر</td><td class="num down">${toman(stop)} تومان (${fa((stop/price-1)*100,1)}٪)</td></tr>
          <tr><td>هدف ۱</td><td class="num up">${toman(t1)} تومان (${fa((t1/price-1)*100,1)}٪)</td></tr>
          <tr><td>هدف ۲</td><td class="num up">${toman(t2)} تومان (${fa((t2/price-1)*100,1)}٪)</td></tr>
          <tr><td>نسبت سود به ریسک</td><td class="num">${fa(x.rr1,1)} تا ${fa(x.rr2,1)}</td></tr>
        </table>
      </div>
      <div class="hint">سطوح بر پایهٔ ATR و کف ۲۰ روزه محاسبه شده‌اند؛ پیش از معامله با نمودار خودتان تطبیق دهید.</div>
    </div>
  </div>`;
}

function bigChart(x) {
  const vals = x.spark || [], vols = x.spark_vol || [];
  if (vals.length < 2) return '';
  const W = 640, H = 190, padL = 8, padR = 46, padT = 12, priceH = 120, gap = 16, volH = 34;
  const min = Math.min(...vals), max = Math.max(...vals), rng = (max-min)||1;
  const step = (W-padL-padR)/(vals.length-1);
  const px = i => padL + i*step;
  const py = v => padT + priceH - ((v-min)/rng)*priceH;
  let d = vals.map((v,i)=> (i?'L':'M')+px(i).toFixed(1)+','+py(v).toFixed(1)).join(' ');
  let area = `M${padL},${padT+priceH} ` + vals.map((v,i)=>`L${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(' ') + ` L${px(vals.length-1).toFixed(1)},${padT+priceH} Z`;
  const vmax = Math.max(...vols, 1);
  const vBase = padT + priceH + gap + volH;
  const bw = Math.max(2, step*0.55);
  const bars = vols.map((v,i) => {
    const h = (v/vmax)*volH;
    return `<rect x="${(px(i)-bw/2).toFixed(1)}" y="${(vBase-h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="1" fill="var(--text-muted)" opacity=".55"/>`;
  }).join('');
  const gid = 'g-' + (x.symbol||'x').replace(/[^A-Za-z0-9]/g,'');
  return `<svg class="big-chart" data-sym="${x.symbol}" viewBox="0 0 ${W} ${H}" role="img" aria-label="نمودار قیمت و حجم">
    <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="var(--accent)" stop-opacity=".18"/>
      <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
    </linearGradient></defs>
    <path d="${area}" fill="url(#${gid})"/>
    <path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <line class="crosshair" x1="0" x2="0" y1="${padT}" y2="${H-6}" stroke="var(--text-muted)" stroke-width="1" style="display:none"/>
    <text x="${W-padR+6}" y="${py(max)+4}" class="axis-label">${toman(max)}</text>
    <text x="${W-padR+6}" y="${py(min)+4}" class="axis-label">${toman(min)}</text>
    <text x="${W-padR+6}" y="${vBase}" class="axis-label">حجم</text>
    ${bars}
  </svg>`;
}

function render() {
  const r = rows();
  const tbody = document.getElementById('tbody');
  document.getElementById('resultCount').textContent = `${fa(r.length)} نماد`;
  document.getElementById('empty').style.display = r.length ? 'none' : 'block';

  tbody.innerHTML = r.map((x, i) => {
    const cls = x.change_pct > 0 ? 'up' : x.change_pct < 0 ? 'down' : 'flat';
    const tags = (x.tags||[]).map(t => `<span class="tag ${tagClass(t)}">${t}</span>`).join('');
    const isOpen = state.open.has(x.symbol);
    return `<tr class="main-row ${isOpen?'open':''}" data-sym="${x.symbol}" tabindex="0">
      <td class="rank num">${fa(i+1)}</td>
      <td><div class="sym">${x.symbol}${x.is_rights?' <span class="tag warn">حق تقدم</span>':''}${x.is_etf?' <span class="tag etf">صندوق</span>':''}<span class="setup-badge">${x.setup||''}</span><small>${x.name||''}</small></div></td>
      <td class="col-hide-sm"><span class="mkt">${x.market}</span></td>
      <td class="num price">${toman(x.close)}</td>
      <td class="num ${cls}">${pct(x.change_pct)}</td>
      <td class="spark-cell col-hide-sm">${sparkline(x.spark)}</td>
      <td class="num col-hide-sm">${fa(x.vol_ratio,1)}×</td>
      <td class="num col-hide-sm">${fa(x.rsi14,0)}</td>
      <td>${scoreMeter(x.score)}</td>
      <td class="col-hide-sm"><div class="tags">${tags}</div></td>
      <td class="num col-hide-sm">${billionToman(x.value_avg20)}</td>
    </tr>
    ${isOpen ? `<tr class="detail-row"><td colspan="11">${detailHtml(x)}</td></tr>` : ''}`;
  }).join('');

  tbody.querySelectorAll('tr.main-row').forEach(tr => {
    const toggle = () => {
      const s = tr.dataset.sym;
      state.open.has(s) ? state.open.delete(s) : state.open.add(s);
      try { history.replaceState(null, '', state.open.has(s) ? '#' + encodeURIComponent(s) : location.pathname); } catch (e) {}
      render();
    };
    tr.addEventListener('click', toggle);
    tr.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
  });
  attachChartHover();
}

function attachChartHover() {
  document.querySelectorAll('svg.big-chart').forEach(svg => {
    const sym = svg.dataset.sym;
    const x = DATA.rows.find(r => r.symbol === sym);
    if (!x) return;
    const vals = x.spark || [], vols = x.spark_vol || [], dates = x.spark_dates_fa || [];
    if (vals.length < 2) return;
    const box = svg.closest('.chart-box');
    const tip = box.querySelector('.chart-tip');
    const line = svg.querySelector('.crosshair');
    const { W, padL, padR, padT, priceH } = CHART;
    const step = (W - padL - padR) / (vals.length - 1);
    const min = Math.min(...vals), max = Math.max(...vals), rng = (max - min) || 1;

    svg.addEventListener('mousemove', e => {
      const r = svg.getBoundingClientRect();
      const vx = (e.clientX - r.left) / r.width * W;
      let i = Math.max(0, Math.min(vals.length - 1, Math.round((vx - padL) / step)));
      const px = padL + i * step;
      line.setAttribute('x1', px); line.setAttribute('x2', px);
      line.style.display = 'block';
      tip.style.display = 'block';
      tip.textContent = `${dates[i] || ''} · ${toman(vals[i])} تومان · حجم ${fa(vols[i] || 0)}`;
      const cx = (px / W) * r.width;
      const tw = tip.offsetWidth;
      tip.style.left = Math.max(4, Math.min(r.width - tw - 4, cx - tw / 2)) + 'px';
    });
    svg.addEventListener('mouseleave', () => {
      tip.style.display = 'none';
      line.style.display = 'none';
    });
  });
}

function renderKpis() {
  const m = DATA.market, b = DATA.breadth, c = DATA.counts;
  const idxPct = m.index ? (m.index_change / Math.max(m.index - m.index_change, 1)) * 100 : 0;
  const cls = m.index_change > 0 ? 'up' : m.index_change < 0 ? 'down' : 'flat';
  const tot = Math.max(b.up + b.down + b.flat, 1);
  const avg = DATA.rows.length ? DATA.rows.reduce((s,x)=>s+x.score,0)/DATA.rows.length : 0;
  document.getElementById('kpis').innerHTML = `
    <div class="kpi">
      <div class="label">شاخص کل</div>
      <div class="value num">${fa(m.index)}</div>
      <div class="delta ${cls}">${pct(idxPct)} · ${fa(m.index_change)} واحد</div>
    </div>
    <div class="kpi">
      <div class="label">ارزش معاملات بازار</div>
      <div class="value num">${fa(m.activity_value/1e13, 1)}</div>
      <div class="delta">هزار میلیارد تومان</div>
    </div>
    <div class="kpi">
      <div class="label">نمادهای مثبت / منفی</div>
      <div class="value num"><span class="up">${fa(b.up)}</span> <span style="color:var(--text-muted)">/</span> <span class="down">${fa(b.down)}</span></div>
      <div class="breadth-bar" role="img" aria-label="${b.up} مثبت و ${b.down} منفی">
        <span class="b-up" style="width:${(b.up/tot*100).toFixed(1)}%"></span>
        <span class="b-down" style="width:${(b.down/tot*100).toFixed(1)}%"></span>
        <span class="b-flat" style="width:${(b.flat/tot*100).toFixed(1)}%"></span>
      </div>
    </div>
    <div class="kpi">
      <div class="label">دامنهٔ اسکن</div>
      <div class="value num">${fa(c.analyzed)}</div>
      <div class="delta">${fa(c.liquid)} نقدشونده · ${fa(c.shown)} منتخب</div>
    </div>
    <div class="kpi">
      <div class="label">میانگین امتیاز منتخب</div>
      <div class="value num">${fa(avg,1)}</div>
      <div class="delta">از ۱۰۰</div>
    </div>`;
}

function init() {
  document.getElementById('lastDate').textContent = DATA.market.last_date_fa || '—';
  document.getElementById('genAt').textContent = DATA.generated_at_fa || (DATA.generated_at||'').replace('T',' ');
  document.getElementById('setupHint').textContent = 'ستاپ: ' + (
    Object.entries(DATA.rows.reduce((a,x)=>{a[x.setup||'—']=(a[x.setup||'—']||0)+1;return a;},{}))
      .map(([k,v])=>`${k} ${fa(v)}`).join(' · ') || '—');
  const st = document.getElementById('stateText');
  st.textContent = DATA.market.state || '—';
  if ((DATA.market.state||'').includes('باز')) document.getElementById('stateDot').classList.add('open');
  renderKpis();

  document.getElementById('q').addEventListener('input', e => { state.q = e.target.value; render(); });
  document.getElementById('minScore').addEventListener('input', e => {
    state.minScore = Number(e.target.value);
    document.getElementById('minScoreVal').textContent = fa(state.minScore);
    render();
  });
  document.getElementById('hideRights').addEventListener('change', e => { state.hideRights = e.target.checked; render(); });
  document.getElementById('hideEtf').addEventListener('change', e => { state.hideEtf = e.target.checked; render(); });
  document.querySelectorAll('.chip[data-setup]').forEach(ch => ch.addEventListener('click', () => {
    document.querySelectorAll('.chip[data-setup]').forEach(c => c.classList.remove('active'));
    ch.classList.add('active');
    state.setup = ch.dataset.setup;
    render();
  }));
  document.querySelectorAll('.chip[data-mkt]').forEach(ch => ch.addEventListener('click', () => {
    document.querySelectorAll('.chip[data-mkt]').forEach(c => c.classList.remove('active'));
    ch.classList.add('active');
    state.mkt = ch.dataset.mkt;
    render();
  }));

  const ths = document.querySelectorAll('thead th[data-sort]');
  ths.forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.sort;
    if (state.sort === k) state.dir *= -1; else { state.sort = k; state.dir = -1; }
    ths.forEach(t => t.removeAttribute('aria-sort'));
    th.setAttribute('aria-sort', state.dir === -1 ? 'descending' : 'ascending');
    render();
  }));
  document.querySelector('th[data-sort="score"]').setAttribute('aria-sort','descending');

  const btn = document.getElementById('themeBtn');
  const saved = localStorage.getItem('tse-theme');
  if (saved) document.documentElement.dataset.theme = saved;
  btn.addEventListener('click', () => {
    const cur = document.documentElement.dataset.theme;
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('tse-theme', next);
  });

  try {
    const h = decodeURIComponent((location.hash || '').slice(1));
    if (h) state.open.add(h);
  } catch (e) {}

  render();
}

init();
</script>
</body>
</html>
"""


def render(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    data_json = data_json.replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", data_json)
