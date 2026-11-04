#!/usr/bin/env python3
"""برگهٔ سفارش روزانه: از خروجی اسکنر، سفارش مشخص می‌سازد.

خروجی برای هر نماد: چند سهم، با چه قیمتی، حد ضرر کجا، هدف کجا، و کِی بفروش.

مثال:
    python run_scan.py                       # اول اسکن امروز
    python run_plan.py                       # برگهٔ سفارش با ۱۰۰ میلیون تومان
    python run_plan.py --capital 300 --positions 4 --risk 1.5
    python run_plan.py --target-atr 0 --hold 20   # بدون هدف ثابت (طبق بک‌تست)
"""

from __future__ import annotations

import argparse
import os
import json
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

from tse.plan import PlanConfig, build_plan  # noqa: E402
from web.plan_report import render_plan  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ساخت برگهٔ سفارش روزانه")
    p.add_argument("--source", default="data/scan_latest.json", help="خروجی اسکنر")
    p.add_argument("--capital", type=float, default=100.0, help="سرمایه (میلیون تومان)")
    p.add_argument("--positions", type=int, default=5, help="تعداد سهم هم‌زمان")
    p.add_argument("--risk", type=float, default=1.0,
                   help="درصد سرمایه که در هر معامله تا حد ضرر ریسک می‌شود")
    p.add_argument("--hold", type=int, default=20, help="روز معاملاتی تا خروج زمانی")
    p.add_argument("--target-atr", type=float, default=2.5,
                   help="هدف = قیمت + n×ATR (۰ = بدون هدف)")
    p.add_argument("--stop-atr", type=float, default=0.0,
                   help="حد ضرر = قیمت − n×ATR (۰ = حد ضرر اسکنر)")
    p.add_argument("--min-score", type=float, default=0.0)
    p.add_argument("--min-rr", type=float, default=1.0, help="حداقل بازده/ریسک")
    p.add_argument("--max-adv", type=float, default=1.0,
                   help="سقف سهم از میانگین ارزش معاملات روزانه (درصد)")
    p.add_argument("--out", default="plan.html")
    p.add_argument("--json-out", default="data/plan_latest.json")
    p.add_argument("--open", action="store_true")
    p.add_argument("--print", dest="do_print", action="store_true",
                   help="چاپ مستقیم برگه")
    return p.parse_args()


def toman(v: float) -> str:
    return f"{v:,.0f}"


def mill(v: float) -> str:
    """عدد به میلیون تومان، با اعشار متناسب با بزرگی."""
    v /= 1e6
    if abs(v) < 10:
        return f"{v:,.2f}"
    if abs(v) < 100:
        return f"{v:,.1f}"
    return f"{v:,.0f}"


def main() -> int:
    args = parse_args()
    src = Path(args.source)
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        print(f"فایل {src} پیدا نشد. اول اسکنر را اجرا کنید:\n"
              f"  {ROOT}/scan.sh", file=sys.stderr)
        return 1

    payload = json.loads(src.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if not rows:
        print("خروجی اسکنر خالی است.", file=sys.stderr)
        return 1

    generated = str(payload.get("generated_at", ""))[:10]
    today = datetime.now().strftime("%Y-%m-%d")
    if generated and generated != today:
        print(f"هشدار: خروجی اسکنر مربوط به {generated} است، نه امروز. "
              f"برای قیمت‌های تازه اول «{ROOT}/scan.sh» را اجرا کنید.",
              file=sys.stderr)

    cfg = PlanConfig(
        capital_toman=args.capital * 1e6,
        positions=args.positions,
        risk_pct=args.risk,
        hold_days=args.hold,
        target_atr=args.target_atr,
        stop_atr=args.stop_atr,
        max_adv_pct=args.max_adv,
        min_score=args.min_score,
        min_rr=args.min_rr,
    )
    plan = build_plan(rows, cfg)
    plan["generated_at_fa"] = jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    plan["source_generated_fa"] = payload.get("generated_at_fa", "")
    plan["source_date"] = generated
    if generated:
        try:
            gd = datetime.strptime(generated, "%Y-%m-%d")
            plan["source_date_fa"] = jdatetime.date.fromgregorian(date=gd).strftime("%Y/%m/%d")
        except ValueError:
            plan["source_date_fa"] = generated
    else:
        plan["source_date_fa"] = ""
    plan["stale"] = bool(generated and generated != today)
    plan["market"] = payload.get("market", {})

    json_path = ROOT / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    html_path = Path(args.out)
    if not html_path.is_absolute():
        html_path = output_dir(ROOT) / html_path
    html_path.write_text(render_plan(plan), encoding="utf-8")

    s = plan["summary"]
    print("\n" + "─" * 78)
    print(f"  برگهٔ سفارش · {plan['as_of_fa']}  (خروج زمانی: پایان {plan['exit_date_fa']})")
    print(f"  سرمایه {mill(s['capital_toman'])} م.ت · "
          f"درگیر {mill(s['invested'])} م.ت · نقد {mill(s['cash'])} م.ت")
    print("─" * 78)
    print(f"  {'نماد':<12}{'تعداد':>10}{'خرید':>11}{'مبلغ م.ت':>12}"
          f"{'حد ضرر':>11}{'هدف':>11}{'بازده هدف':>11}")
    for o in plan["orders"]:
        tgt = toman(o["target"]) if o["target"] else "—"
        ret = f"{o['target_ret_pct']:.1f}%" if o["target_ret_pct"] is not None else "—"
        print(f"  {o['symbol']:<12}{o['qty']:>10,}{toman(o['entry']):>11}"
              f"{mill(o['cost']):>12}{toman(o['stop']):>11}{tgt:>11}{ret:>11}")
    print("─" * 78)
    print(f"  ریسک کل تا حد ضررها: {mill(s['risk_total'])} م.ت "
          f"({s['risk_total_pct']:.1f}% سرمایه)")
    print(f"✓ برگه: {html_path}")
    print(f"  داده: {json_path}")

    if args.do_print:
        import subprocess

        subprocess.run(["xdg-open", str(html_path)], check=False)
    if args.open:
        import webbrowser

        webbrowser.open(html_path.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
