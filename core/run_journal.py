#!/usr/bin/env python3
"""دفتر معاملات: ثبت سفارش‌های برگه، پیگیری روزانه، و آمار واقعی.

مثال:
    python run_journal.py open                 # سفارش‌های plan_latest.json را ثبت کن
    python run_journal.py status               # قیمت امروز، سود/زیان، هشدارها
    python run_journal.py close سبهان --price 800 --reason هدف
    python run_journal.py stats                # عملکرد واقعی بسته‌شده‌ها
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import jdatetime

CODE = Path(__file__).resolve().parent      # core/ — پکیج tse اینجاست
PROJECT = CODE.parent                       # ریشهٔ مخزن: core، web، data، android
# در اپ اندروید کد داخل APK فقط‌خواندنی است، پس ریشهٔ داده‌ها جدا می‌شود
ROOT = Path(os.environ.get("TSE_HOME") or PROJECT)
ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(CODE))                # import tse
sys.path.insert(0, str(PROJECT))             # import web
from tse import output_dir  # noqa: E402

from tse.journal import (  # noqa: E402
    SELL_FEE,
    close_position,
    load,
    mark_to_market,
    open_from_plan,
    quotes_from_market_watch,
    save,
    stats as journal_stats,
)

JOURNAL = ROOT / "data" / "journal.json"



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="دفتر معاملات")
    p.add_argument("--journal", default="data/journal.json", help="مسیر فایل دفتر")
    sub = p.add_subparsers(dest="cmd")

    o = sub.add_parser("open", help="ثبت سفارش‌های برگه به‌عنوان پوزیشن باز")
    o.add_argument("--plan", default="data/plan_latest.json")

    s = sub.add_parser("status", help="به‌روزرسانی با قیمت امروز")
    s.add_argument("--workers", type=int, default=4)

    c = sub.add_parser("close", help="بستن یک پوزیشن")
    c.add_argument("symbol")
    c.add_argument("--price", type=float, required=True, help="قیمت فروش (تومان)")
    c.add_argument("--reason", default="دستی")

    sub.add_parser("list", help="نمایش پوزیشن‌های باز بدون قیمت")
    sub.add_parser("stats", help="آمار معاملات بسته‌شده")
    return p.parse_args()


def toman(v: float) -> str:
    return f"{v:,.0f}"


def cmd_open(args) -> int:
    plan_path = Path(args.plan)
    if not plan_path.is_absolute():
        plan_path = ROOT / plan_path
    if not plan_path.exists():
        print(f"{plan_path} پیدا نشد. اول run_plan.py را اجرا کنید.", file=sys.stderr)
        return 1

    import json

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    journal = load(JOURNAL)
    added, skipped = open_from_plan(journal, plan)
    save(JOURNAL, journal)

    if added:
        print(f"✓ {len(added)} پوزیشن ثبت شد: {'، '.join(added)}")
    else:
        print("پوزیشن تازه‌ای ثبت نشد.")
    for s in skipped:
        print(f"  · {s}")
    print(f"  دفتر: {JOURNAL}")
    return 0


def _fetch_quotes(workers: int) -> dict[str, float]:
    from tse.client import FetchError, TSEClient

    try:
        rows = TSEClient(workers=workers).market_watch()
    except FetchError as exc:
        print(f"خطا در دریافت قیمت‌ها: {exc}", file=sys.stderr)
        return {}
    return quotes_from_market_watch(rows)


def cmd_status(args) -> int:
    journal = load(JOURNAL)
    if not journal["positions"]:
        print("هیچ پوزیشن بازی نیست. اول: python run_journal.py open")
        return 0

    quotes = _fetch_quotes(args.workers)
    rows = mark_to_market(journal, quotes)
    # قیمت آخر را در دفتر نگه می‌داریم تا صفحهٔ یکپارچه بدون شبکه بتواند آن را نشان دهد
    marks = {r["id"]: r for r in rows}
    for p in journal["positions"]:
        m = marks.get(p["id"])
        if not m:
            continue
        for k in ("ltp", "pnl", "pnl_pct", "value", "dist_stop_pct", "dist_target_pct"):
            if m.get(k) is not None:
                p[k] = m[k]
        p["ltp_at"] = datetime.now().isoformat(timespec="minutes")
    save(JOURNAL, journal)

    print("\n" + "─" * 92)
    print(f"  وضعیت پوزیشن‌ها · {jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')}")
    print("─" * 92)
    print(f"  {'نماد':<11}{'تعداد':>9}{'ورود':>9}{'آخرین':>9}{'سود ت':>10}"
          f"{'سود٪':>8}{'تا ضرر':>9}{'تا هدف':>9}   وضعیت")
    total_pnl = 0.0
    total_cost = 0.0
    for r in rows:
        ltp = toman(r["ltp"]) if r["ltp"] else "—"
        pnl = f"{r['pnl']:+,.0f}" if r["pnl"] is not None else "—"
        pct = f"{r['pnl_pct']:+.1f}%" if r["pnl_pct"] is not None else "—"
        ds = f"{r['dist_stop_pct']:.1f}%" if r.get("dist_stop_pct") is not None else "—"
        dt = f"{r['dist_target_pct']:.1f}%" if r.get("dist_target_pct") is not None else "—"
        flag = ""
        if "stop" in r["flags"]:
            flag = "⛔ حد ضرر لمس شد — بفروش"
        elif "target" in r["flags"]:
            flag = "🎯 هدف رسید — بفروش"
        elif "expired" in r["flags"]:
            flag = f"⏰ مهلت تمام شد ({r['planned_exit_fa']})"
        else:
            flag = f"مهلت {r['planned_exit_fa']}"
        print(f"  {r['symbol']:<11}{r['qty']:>9,}{toman(r['entry']):>9}{ltp:>9}"
              f"{pnl:>10}{pct:>8}{ds:>9}{dt:>9}   {flag}")
        if r["pnl"] is not None:
            total_pnl += r["pnl"]
            total_cost += r["cost"]

    print("─" * 92)
    if total_cost:
        print(f"  جمع سود/زیان باز: {total_pnl:+,.0f} تومان "
              f"({total_pnl / total_cost * 100:+.1f}%) روی {toman(total_cost)} تومان سرمایه")
    alerts = [r for r in rows if r["flags"]]
    if alerts:
        print(f"  ⚠ {len(alerts)} پوزیشن نیاز به اقدام دارد.")
    print(f"  بستن یک پوزیشن: python run_journal.py close <نماد> --price <قیمت>")
    return 0


def cmd_close(args) -> int:
    journal = load(JOURNAL)
    rec = close_position(journal, args.symbol, args.price, args.reason)
    if not rec:
        print(f"پوزیشن بازی برای «{args.symbol}» پیدا نشد.", file=sys.stderr)
        return 1
    save(JOURNAL, journal)
    print(f"✓ {rec['symbol']} بسته شد در {toman(rec['exit'])} تومان · "
          f"سود {rec['pnl']:+,.0f} تومان ({rec['pnl_pct']:+.1f}%) · "
          f"{rec['holding_days']} روز نگهداری · {rec['reason']}")
    return 0


def cmd_list(args) -> int:
    journal = load(JOURNAL)
    if not journal["positions"]:
        print("هیچ پوزیشن بازی نیست.")
        return 0
    print(f"\n  {'نماد':<11}{'تعداد':>9}{'ورود':>9}{'حد ضرر':>9}{'هدف':>9}"
          f"{'مبلغ م.ت':>11}   مهلت")
    for p in journal["positions"]:
        tgt = toman(p["target"]) if p.get("target") else "—"
        print(f"  {p['symbol']:<11}{p['qty']:>9,}{toman(p['entry']):>9}"
              f"{toman(p['stop']):>9}{tgt:>9}{p['cost'] / 1e6:>11,.1f}   "
              f"{p.get('planned_exit_fa') or '—'}")
    return 0


def cmd_stats(args) -> int:
    journal = load(JOURNAL)
    s = journal_stats(journal)
    print("\n" + "─" * 70)
    print("  عملکرد واقعی (بعد از کارمزد)")
    print("─" * 70)
    if not s["closed"]:
        print("  هنوز معامله‌ای بسته نشده است.")
        if s["open"]:
            print(f"  {s['open']} پوزیشن باز · {toman(s['invested_open'] / 1e6)} م.ت")
        return 0

    print(f"  معاملات بسته‌شده: {s['closed']} ({s['open']} باز)")
    print(f"  سود/زیان: {s['pnl']:+,.0f} تومان ({s['pnl_pct_of_cost']:+.1f}% روی سرمایهٔ درگیر)")
    print(f"  نرخ برد: {s['win_rate'] * 100:.0f}% ({s['wins']} برد / {s['losses']} باخت)")
    print(f"  میانگین برد: {s['avg_win_pct']:+.1f}% · میانگین باخت: {s['avg_loss_pct']:+.1f}%")
    if s["profit_factor"]:
        print(f"  نسبت سود به زیان: {s['profit_factor']:.2f}")
    print(f"  کارمزد پرداختی: {toman(s['fees'])} تومان ({s['fees_pct_of_cost']:.1f}% سرمایه)")
    print(f"  میانگین نگهداری: {s['avg_holding_days']:.1f} روز")
    if s["best"]:
        print(f"  بهترین: {s['best']['symbol']} {s['best']['pnl_pct']:+.1f}% · "
              f"بدترین: {s['worst']['symbol']} {s['worst']['pnl_pct']:+.1f}%")
    print("─" * 70)
    print(f"  {'نماد':<11}{'ورود':>9}{'خروج':>9}{'سود٪':>8}{'سود ت':>12}{'روز':>6}   دلیل")
    for c in journal["closed"][-15:]:
        print(f"  {c['symbol']:<11}{toman(c['entry']):>9}{toman(c['exit']):>9}"
              f"{c['pnl_pct']:>7.1f}%{c['pnl']:>12,.0f}{c['holding_days']:>6}   {c['reason']}")
    print(f"\n  کارمزد فروش در محاسبه: {SELL_FEE * 100:.2f}%")
    return 0


def main() -> int:
    global JOURNAL
    args = parse_args()
    jp = Path(args.journal)
    JOURNAL = jp if jp.is_absolute() else ROOT / jp
    cmd = args.cmd or "status"
    if cmd == "open":
        return cmd_open(args)
    if cmd == "status":
        args.workers = getattr(args, "workers", 4)
        return cmd_status(args)
    if cmd == "close":
        return cmd_close(args)
    if cmd == "list":
        return cmd_list(args)
    if cmd == "stats":
        return cmd_stats(args)
    print("دستور ناشناخته.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
