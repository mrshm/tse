"""برگهٔ سفارش روزانه به شکل HTML قابل چاپ."""

from __future__ import annotations

from html import escape

from .report import CSS

EXTRA_CSS = r"""
  .summary-line { font-size: 13px; color: var(--text-secondary); margin: -6px 0 18px;
    line-height: 1.9; }
  .summary-line b { color: var(--text-primary); font-weight: 600; }
  .banner { display: flex; gap: 10px; align-items: flex-start; background: var(--critical-bg);
    color: var(--critical); border: 1px solid currentColor; border-radius: var(--radius);
    padding: 10px 14px; font-size: 12.5px; line-height: 1.8; margin-bottom: 16px; }
  .banner strong { font-weight: 650; }
  .orders { width: 100%; border-collapse: collapse; font-size: 13px; }
  .orders thead th { position: sticky; top: 0; background: var(--surface-2); z-index: 1; }
  .orders th, .orders td { padding: 9px 10px; border-bottom: 1px solid var(--border);
    text-align: right; white-space: nowrap; }
  .orders tbody tr:hover { background: var(--surface-2); }
  .orders td.sym { font-weight: 650; font-size: 13.5px; }
  .orders td.sym .nm { display: block; font-weight: 400; font-size: 11px; color: var(--text-muted);
    margin-top: 1px; }
  .orders tfoot td { background: var(--surface-2); font-weight: 600; border-bottom: none;
    padding: 10px; }
  .orders .goal { color: var(--good); }
  .orders .risk { color: var(--critical); font-size: 12.5px; }
  .orders .qty { font-weight: 650; }
  .order-cards { display: none; }
  @media (max-width: 720px) {
    .table-scroll { display: none; }
    .order-cards { display: grid; gap: 10px; }
    .order-card { border: 1px solid var(--border); border-radius: var(--radius);
      padding: 12px 14px; background: var(--surface-2); }
    .order-card .oc-head { display: flex; justify-content: space-between; align-items: baseline;
      margin-bottom: 8px; }
    .order-card .oc-head b { font-size: 15px; }
    .order-card .row { display: flex; justify-content: space-between; font-size: 12.5px;
      padding: 3px 0; color: var(--text-secondary); }
    .order-card .row b { color: var(--text-primary); font-weight: 600; }
  }
  .steps { counter-reset: step; list-style: none; padding: 0; margin: 0; }
  .steps li { counter-increment: step; position: relative; padding-right: 30px;
    margin-bottom: 7px; }
  .steps li::before { content: counter(step); position: absolute; right: 0; top: 1px;
    width: 19px; height: 19px; border-radius: 50%; background: var(--surface-3);
    color: var(--text-secondary); font-size: 11px; line-height: 19px; text-align: center; }
  .skipped { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
  .skipped summary { cursor: pointer; color: var(--text-secondary); }
  .skipped ul { margin: 6px 0 0; padding-right: 18px; }
  .print-row { display: flex; gap: 8px; }
  @media print {
    :root, :root[data-theme="dark"], :root[data-theme="light"] {
      --bg: #fff !important; --surface-1: #fff !important; --surface-2: #f6f6f4 !important;
      --surface-3: #eee !important; --border: #ccc !important;
      --text-primary: #000 !important; --text-secondary: #333 !important;
      --text-muted: #666 !important; --accent: #1a5fb4 !important;
      --good: #0a6b0a !important; --critical: #a02020 !important;
      --shadow: none !important;
    }
    @page { margin: 12mm; }
    body { background: #fff !important; }
    .wrap { max-width: none; padding: 0; }
    .no-print { display: none !important; }
    .card { box-shadow: none; break-inside: avoid; }
    .table-scroll { display: block !important; }
    .order-cards { display: none !important; }
    .orders thead th { position: static; }
    .orders tbody tr, .orders tfoot tr { break-inside: avoid; }
    .orders { font-size: 11px; }
    .orders th, .orders td { padding: 6px 7px; }
    .orders td.sym .nm { font-size: 9.5px; }
    .card { padding: 12px 14px; }
  }
"""

TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>برگهٔ سفارش · __AS_OF__</title>
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
      <h1>برگهٔ سفارش روزانه</h1>
      <p class="sub">سفارش مشخص برای امروز · __AS_OF__
        <span class="hint">· ساخته‌شده __GENERATED__</span></p>
    </div>
    <div class="print-row no-print">
      <button class="icon-btn" id="print" title="چاپ">⎙</button>
      <button class="icon-btn" id="theme" title="تغییر تم" aria-label="تغییر تم">◐</button>
    </div>
  </div>

  __BANNER__

  <div class="chips no-print">__CHIPS__</div>
  <div class="kpis">__KPIS__</div>

  <p class="summary-line">__SUMMARY__</p>

  <div class="card">
    <div class="card-head">
      <h2>سفارش‌ها</h2>
      <span class="hint">__COUNT_HINT__</span>
    </div>
    <div class="table-scroll">
      <table class="orders">
        <thead>
          <tr>__HEAD__</tr>
        </thead>
        <tbody>__ROWS__</tbody>
        <tfoot>
          <tr>__FOOT__</tr>
        </tfoot>
      </table>
    </div>
    <div class="order-cards">__CARDS__</div>
  </div>

  <div class="card">
    <div class="card-head"><h2>ترتیب اجرا</h2></div>
    <div class="notes">
      <ol class="steps">
        <li>پیش از ساعت ۹، قیمت پایانی امروزِ هر نماد را در سامانهٔ کارگزاری با این برگه مقایسه کنید.
          اگر نماد بیش از <b>۳٪ بالاتر</b> از قیمت این برگه باز شد، سفارش را کنسل کنید — هدف و حد ضرر
          به قیمت دیروز بسته شده‌اند.</li>
        <li>سفارش خرید را <b>محدود</b> بگذارید، نه بازار؛ سقف قیمت را همان ستون «قیمت خرید» قرار دهید.</li>
        <li>اگر تا پایان روز پر نشد، پیگیری نکنید. نبودِ معامله هم یک تصمیم است.</li>
        <li>حد ضرر و هدف را همان روز در سامانه ثبت کنید؛ هر دو سفارش محدود. با تسویهٔ <b>T+2</b> فروش
          تا دو روز کاری ممکن نیست، پس سفارش فروش از روز سوم به بعد معتبر است.</li>
        <li>اگر هیچ‌کدام از دو سطح تا <b>__EXIT__</b> فعال نشد، در آن روز با قیمت بازار بفروشید و
          برگهٔ سفارش تازه بسازید.</li>
      </ol>
    </div>
  </div>

  <div class="notes">
    <h3>این اعداد از کجا آمده‌اند</h3>
    <ul>
      <li><b>تعداد</b> = کمترینِ سه سقف: (ریسک مجاز ÷ فاصلهٔ قیمت تا حد ضرر)، (سهم هر نماد از سرمایه)،
        و (۱٪ میانگین ارزش معاملات روزانه — تا سفارش خودتان بازار را جابه‌جا نکند).</li>
      <li><b>حد ضرر</b> پایین‌ترین کف ۵ روزه یا قیمت منهای ۲×ATR است؛ <b>هدف</b> قیمت به‌علاوهٔ
        __TARGET_ATR__×ATR.</li>
      <li>قیمت‌ها از بستهٔ دادهٔ TSETMC و از خروجی اسکنر آمده‌اند؛ <b>تومان</b> است. کارمزد
        (~۱٫۴٪ رفت‌وبرگشت) در این اعداد نیست، در محاسبهٔ سود خودتان لحاظ کنید.</li>
      <li>__BT_NOTE__</li>
    </ul>
  </div>

  __SKIPPED__
</div>

<script>
document.getElementById("print").addEventListener("click", () => window.print());
document.getElementById("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.getAttribute("data-theme") === "dark";
  root.setAttribute("data-theme", dark ? "light" : "dark");
  try { localStorage.setItem("tse-theme", dark ? "light" : "dark"); } catch (e) {}
});
try {
  const saved = localStorage.getItem("tse-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}
</script>
</body>
</html>
"""


def _t(v: float | None, d: int = 0) -> str:
    if v is None:
        return "—"
    return f"{v:,.{d}f}"


def _bdi(text: str) -> str:
    return f'<bdi dir="ltr">{text}</bdi>'


def _money(v: float, d: int = 0) -> str:
    """مبلغ به میلیون تومان: عدد جدا از یکا تا ترتیب راست‌به‌چپ به‌هم نریزد."""
    return f'{_bdi(_t(v, d))} م.ت'


def _neg_money(v: float, d: int = 0) -> str:
    return f'{_bdi("−" + _t(abs(v), d))} م.ت'


def _row(o: dict, show_target: bool) -> str:
    name = escape(o.get("name") or "")
    tag = " · صندوق" if o.get("is_etf") else ""
    setup = escape(o.get("setup") or "")
    sub = escape(f"{name}{tag}") if name else escape(tag.lstrip(" ·"))
    if setup and sub:
        sub = f"{sub} · {setup}"
    elif setup:
        sub = setup

    dist = (o["entry"] - o["stop"]) / o["entry"] * 100 if o["entry"] else 0.0
    target_cells = ""
    if show_target:
        target = _bdi(_t(o["target"])) if o["target"] else "—"
        ret = _bdi(f"+{o['target_ret_pct']:.1f}%") if o.get("target_ret_pct") else "—"
        target_cells = (f'<td class="num goal">{target}</td>'
                        f'<td class="num goal">{ret}</td>')
    return (
        '<tr>'
        f'<td class="sym">{escape(str(o["symbol"]))}<span class="nm">{sub}</span></td>'
        f'<td class="num qty">{_bdi(_t(o["qty"]))}</td>'
        f'<td class="num">{_bdi(_t(o["entry"]))}</td>'
        f'<td class="num">{_money(o["cost"] / 1e6, 1)}</td>'
        f'<td class="num">{_bdi(_t(o["stop"]))}</td>'
        f'<td class="num">{_bdi(f"{dist:.1f}%")}</td>'
        f"{target_cells}"
        f'<td class="num risk">{_neg_money(o["risk"] / 1e6, 2)}</td>'
        f'<td class="num">{_bdi(_t(o["score"], 0))}</td>'
        "</tr>"
    )


def _card(o: dict, show_target: bool) -> str:
    target = _bdi(_t(o["target"])) if o["target"] else "—"
    ret = _bdi(f"+{o['target_ret_pct']:.1f}%") if o.get("target_ret_pct") else "—"
    rows = [
        ("تعداد", _bdi(_t(o["qty"]))),
        ("قیمت خرید", _bdi(_t(o["entry"])) + " تومان"),
        ("مبلغ", _money(o["cost"] / 1e6, 1)),
        ("حد ضرر", _bdi(_t(o["stop"])) + " تومان"),
    ]
    if show_target:
        rows.append(("هدف", target + (f" <span class='goal'>({ret})</span>" if o["target"] else "")))
    rows.append(("زیان تا حد ضرر", _neg_money(o["risk"] / 1e6, 2)))
    body = "".join(f'<div class="row"><span>{k}</span><b>{v}</b></div>' for k, v in rows)
    return (
        '<div class="order-card">'
        f'<div class="oc-head"><b>{escape(str(o["symbol"]))}</b>'
        f'<span class="hint">{escape(o.get("name") or "")}</span></div>'
        f"{body}</div>"
    )


def render_plan(plan: dict) -> str:
    s = plan["summary"]
    cfg = plan["config"]
    capital = cfg["capital_toman"]
    orders = plan["orders"]

    chips = [
        ("سرمایه", _money(capital / 1e6)),
        ("تعداد سهم", _bdi(str(cfg["positions"]))),
        ("ریسک هر معامله", _bdi(f"{cfg['risk_pct']:g}%")),
        ("نگهداری", _bdi(str(cfg["hold_days"])) + " روز"),
        ("هدف", "بدون هدف" if not cfg["target_atr"] else _bdi(f"{cfg['target_atr']:g}×ATR")),
        ("حد ضرر", "اسکنر" if not cfg["stop_atr"] else _bdi(f"{cfg['stop_atr']:g}×ATR")),
        ("حداقل R/R", _bdi(f"{cfg['min_rr']:g}")),
    ]
    chips_html = "".join(f'<span class="chip">{k} <b>{v}</b></span>' for k, v in chips)

    kpis = [
        ("تعداد سفارش", _bdi(str(s["count"])), f'از {cfg["positions"]} جایگاه', ""),
        ("مبلغ درگیر", _money(s["invested"] / 1e6),
         _bdi(f'{s["invested"] / capital * 100:.0f}%') + " سرمایه", ""),
        ("نقد باقی‌مانده", _money(s["cash"] / 1e6), "برای کارمزد و فرصت بعدی", ""),
        ("ریسک کل", _neg_money(s["risk_total"] / 1e6, 1),
         _bdi(f'{s["risk_total_pct"]:.1f}%') + " سرمایه", "down"),
        ("خروج زمانی", _bdi(plan["exit_date_fa"]),
         _bdi(str(cfg["hold_days"])) + " روز معاملاتی", ""),
    ]
    kpis_html = "".join(
        f'<div class="kpi"><div class="label">{k}</div>'
        f'<div class="value {clamp}">{v}</div>'
        f'<div class="note">{n}</div></div>'
        for k, v, n, clamp in kpis
    )

    banner = ""
    if plan.get("stale"):
        src = plan.get("source_date_fa") or plan.get("source_date") or "—"
        banner = (
            '<div class="banner no-print"><span>⚠</span><div>'
            "<strong>این برگه بر پایهٔ دادهٔ امروز نیست.</strong> "
            f"خروجی اسکنر مربوط به {_bdi(escape(str(src)))} است. "
            "قبل از معامله اسکنر را دوباره اجرا کنید."
            "</div></div>"
        )

    show_target = bool(cfg["target_atr"])
    target_heads = "<th>هدف</th><th>بازده هدف</th>" if show_target else ""
    target_foot = "<td>—</td><td>—</td>" if show_target else ""
    head_html = (
        "<th>نماد</th><th>تعداد</th><th>قیمت خرید</th><th>مبلغ (م.ت)</th>"
        "<th>حد ضرر</th><th>فاصلهٔ حد ضرر</th>" + target_heads
        + "<th>ریسک (م.ت)</th><th>امتیاز</th>"
    )
    foot_html = (
        "<td>جمع</td><td>—</td><td>—</td>"
        f"<td>{_money(s['invested'] / 1e6, 1)}</td><td>—</td><td>—</td>" + target_foot
        + f'<td class="risk">{_neg_money(s["risk_total"] / 1e6, 1)}</td><td>—</td>'
    )

    if orders:
        if show_target:
            exit_clause = "یا به‌محض رسیدن به هدف بفروشید"
        else:
            exit_clause = "بفروشید"
        summary = (
            f"امروز <b>{s['count']}</b> سهم بخرید، مجموعاً "
            f"<b>{_bdi(_t(s['invested'] / 1e6))} میلیون تومان</b>. "
            f"همه را در <b>{_bdi(plan['exit_date_fa'])}</b> {exit_clause}؛ "
            f"اگر به حد ضرر خورد، همان‌جا خارج شوید."
        )
        count_hint = (
            "اگر همهٔ حد ضررها فعال شوند روی هم "
            f"{_neg_money(s['risk_total'] / 1e6, 1)} از دست می‌رود."
        )
        rows_html = "".join(_row(o, show_target) for o in orders)
        cards_html = "".join(_card(o, show_target) for o in orders)
    else:
        summary = (
            "امروز هیچ نمادی از فیلترها رد نشد. معامله نکردن هم یک تصمیم است — "
            "فردا دوباره اسکن کنید یا آستانه‌ها را در <code>run_plan.py</code> کمی شل‌تر بگیرید."
        )
        count_hint = "همهٔ سفارش‌ها رد شدند"
        cols = 10 if show_target else 8
        rows_html = f'<tr><td colspan="{cols}" class="empty">سفارشی نیست</td></tr>'
        cards_html = '<div class="empty">سفارشی نیست</div>'

    skipped_html = ""
    if plan.get("skipped"):
        items = "".join(
            f"<li>{escape(str(x.get('symbol') or '—'))} — {escape(str(x.get('why') or ''))}</li>"
            for x in plan["skipped"]
        )
        skipped_html = (
            '<details class="skipped no-print"><summary>'
            f"{len(plan['skipped'])} نماد کنار گذاشته شد</summary>"
            f"<ul>{items}</ul></details>"
        )

    if cfg["target_atr"]:
        bt_note = (
            "در بک‌تست، نگهداری بلندمدت بدون هدف ثابت بهتر از هدف‌گذاری کوچک بود "
            "(<code>--hold 20 --target-atr 0</code>)."
        )
    else:
        bt_note = (
            "بدون هدف ثابت: فقط حد ضرر یا پایان مهلت، سهم را می‌بندد. "
            "این حالت در بک‌تست بهتر از هدف‌های کوچک بود."
        )

    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__EXTRA__", EXTRA_CSS)
        .replace("__AS_OF__", escape(plan["as_of_fa"]))
        .replace("__GENERATED__", escape(plan.get("generated_at_fa") or ""))
        .replace("__BANNER__", banner)
        .replace("__CHIPS__", chips_html)
        .replace("__KPIS__", kpis_html)
        .replace("__SUMMARY__", summary)
        .replace("__COUNT_HINT__", count_hint)
        .replace("__ROWS__", rows_html)
        .replace("__CARDS__", cards_html)
        .replace("__HEAD__", head_html)
        .replace("__FOOT__", foot_html)
        .replace("__EXIT__", escape(plan["exit_date_fa"]))
        .replace("__TARGET_ATR__", f"{cfg['target_atr']:g}")
        .replace("__BT_NOTE__", bt_note)
        .replace("__SKIPPED__", skipped_html)
    )
