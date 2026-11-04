#!/usr/bin/env python3
"""بک‌تست استراتژی اسکنر روی تاریخچهٔ بورس تهران.

مثال:
    python core/run_backtest.py                       # ۴۰۰ روز، ۵ سهم، نگهداری ۵ روز
    python core/run_backtest.py --days 700 --top 3
    python core/run_backtest.py --max-hold 3 --target-atr 3
    python core/run_backtest.py --symbols 250 --open  # فقط نقدشونده‌ترین‌ها (سریع‌تر)
"""

from __future__ import annotations

import argparse
import os
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import jdatetime
import pandas as pd

CODE = Path(__file__).resolve().parent      # core/ — پکیج tse اینجاست
PROJECT = CODE.parent                       # ریشهٔ مخزن: core، web، data، android
# در اپ اندروید کد داخل APK فقط‌خواندنی است، پس ریشهٔ داده‌ها جدا می‌شود
ROOT = Path(os.environ.get("TSE_HOME") or PROJECT)
ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(CODE))                # import tse
sys.path.insert(0, str(PROJECT))             # import web
from tse import output_dir  # noqa: E402

from tse.backtest import (  # noqa: E402
    BacktestConfig,
    attach_benchmark,
    build_panel,
    compute_metrics,
    score_panel,
    simulate,
)
from tse.client import FetchError, TSEClient  # noqa: E402
from web.report import render_report  # noqa: E402
from tse.universe import build_universe  # noqa: E402

RIAL_PER_TOMAN = 10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="بک‌تست استراتژی اسکنر")
    p.add_argument("--days", type=int, default=400, help="طول تاریخچه (روز معاملاتی)")
    p.add_argument("--top", type=int, default=5, help="تعداد سهم هم‌زمان در پرتفوی")
    p.add_argument("--max-hold", type=int, default=5, help="حداکثر روز نگهداری")
    p.add_argument("--min-hold", type=int, default=2, help="حداقل روز نگهداری (T+2)")
    p.add_argument("--stop-atr", type=float, default=2.0)
    p.add_argument("--target-atr", type=float, default=2.5,
                   help="هدف سود بر حسب ATR (۰ = بدون هدف، فقط حد ضرر)")
    p.add_argument("--trail-atr", type=float, default=0.0,
                   help="حد ضرر متحرک بر حسب ATR (۰ = خاموش)")
    p.add_argument("--capital", type=float, default=100.0,
                   help="سرمایه اولیه به میلیون تومان")
    p.add_argument("--buy-fee", type=float, default=0.45, help="کارمزد خرید (درصد)")
    p.add_argument("--sell-fee", type=float, default=0.95, help="کارمزد فروش (درصد)")
    p.add_argument("--min-value", type=float, default=2.0,
                   help="حداقل میانگین ارزش روزانه (میلیارد تومان)")
    p.add_argument("--min-score", type=float, default=0.0, help="حداقل امتیاز ورود")
    p.add_argument("--symbols", type=int, default=0,
                   help="محدودکردن به N نماد نقدشونده (۰ = همه)")
    p.add_argument("--markets", default="بورس,فرابورس,پایه,کالا")
    p.add_argument("--etf", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--rights", action=argparse.BooleanOptionalAction, default=False,
                   help="شامل حق تقدم‌ها (پیش‌فرض: خیر)")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", default="backtest.html")
    p.add_argument("--json-out", default="data/backtest_latest.json")
    p.add_argument("--open", action="store_true")
    return p.parse_args()


def jalali(d_even: int) -> str:
    try:
        d = datetime.strptime(str(int(d_even)), "%Y%m%d")
        return jdatetime.date.fromgregorian(date=d).strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        return "—"


def benchmark_series(client: TSEClient) -> pd.Series:
    try:
        rows = client.index_history()
    except FetchError:
        return pd.Series(dtype="float64")
    out: dict[int, float] = {}
    for r in rows:
        try:
            d = int(r["dEven"])
        except (KeyError, TypeError, ValueError):
            continue
        v = r.get("xNivInuClMresIbs") or r.get("xNivInuTotMresIbs") or r.get("indexLastValue")
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v > 0:
            out[d] = v
    if not out:
        return pd.Series(dtype="float64")
    return pd.Series(out).sort_index()


def pct(x: float | None, digits: int = 1) -> str:
    if x is None or not math.isfinite(x):
        return "—"
    return f"{x * 100:+.{digits}f}%"


def main() -> int:
    args = parse_args()
    started = datetime.now()
    client = TSEClient(workers=args.workers)
    markets = {m.strip() for m in args.markets.split(",") if m.strip()}

    print("→ دریافت فهرست نمادها …", flush=True)
    try:
        mw_rows = client.market_watch()
    except FetchError as exc:
        print(f"خطا در دریافت داده: {exc}", file=sys.stderr)
        return 1

    universe = [
        u for u in build_universe(mw_rows)
        if u["market"] in markets
        and (args.etf or not u["is_etf"])
        and (args.rights or not u["is_rights"])
    ]
    if args.symbols > 0:
        universe.sort(key=lambda u: u["value"], reverse=True)
        universe = universe[: args.symbols]
    print(f"  {len(universe)} نماد در دامنه")

    print(f"→ دریافت تاریخچهٔ {args.days} روزه …", flush=True)
    panel = build_panel(client, universe, days=args.days)
    if panel.empty:
        print("داده‌ای برای بک‌تست پیدا نشد.", file=sys.stderr)
        return 1
    print(f"  {panel['symbol'].nunique()} نماد · {len(panel):,} ردیف")

    print("→ محاسبهٔ اندیکاتورها و امتیاز مقطعی …", flush=True)
    panel = score_panel(panel)

    cfg = BacktestConfig(
        top_n=args.top,
        max_hold=args.max_hold,
        min_hold=args.min_hold,
        stop_atr=args.stop_atr,
        target_atr=args.target_atr,
        trail_atr=args.trail_atr,
        capital=args.capital * 1e6 * RIAL_PER_TOMAN,
        buy_fee=args.buy_fee / 100,
        sell_fee=args.sell_fee / 100,
        min_value=args.min_value * 1e9 * RIAL_PER_TOMAN,
        min_score=args.min_score,
        include_rights=args.rights,
        include_etf=args.etf,
    )

    print("→ اجرای شبیه‌سازی …", flush=True)
    result = simulate(panel, cfg)
    bench = benchmark_series(client)
    attach_benchmark(result, bench, cfg)
    metrics = compute_metrics(result, cfg, bench)

    # پاک‌سازی خروجی
    curve = [
        {
            "date": int(r["date"]),
            "date_fa": jalali(r["date"]),
            "equity": round(float(r["equity"])),
            "benchmark": round(float(r["benchmark"])) if r.get("benchmark") else None,
        }
        for r in result["curve"]
    ]
    trades = []
    for t in result["trades"]:
        trades.append(
            {
                **t,
                "entry_date_fa": jalali(t["entry_date"]),
                "exit_date_fa": jalali(t["exit_date"]),
            }
        )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_at_fa": jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
        "config": {
            "days": args.days,
            "top_n": args.top,
            "max_hold": args.max_hold,
            "min_hold": args.min_hold,
            "stop_atr": args.stop_atr,
            "target_atr": args.target_atr,
            "trail_atr": args.trail_atr,
            "capital_toman": args.capital * 1e6,
            "buy_fee_pct": args.buy_fee,
            "sell_fee_pct": args.sell_fee,
            "min_value_btooman": args.min_value,
            "min_score": args.min_score,
            "include_etf": args.etf,
            "include_rights": args.rights,
            "symbols": len(universe),
        },
        "metrics": metrics,
        "curve": curve,
        "trades": trades,
    }

    json_path = ROOT / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    html_path = Path(args.out)
    if not html_path.is_absolute():
        html_path = output_dir(ROOT) / html_path
    html_path.write_text(render_report(payload), encoding="utf-8")

    elapsed = (datetime.now() - started).total_seconds()
    m = metrics
    print("\n" + "─" * 52)
    print(f"  بازده استراتژی      {pct(m.get('total_return'))}")
    print(f"  بازده قبل از کارمزد {pct(m.get('gross_return_est'))}  "
          f"(کارمزد: {m.get('fees_pct_of_capital', 0) * 100:.0f}٪ سرمایه)")
    print(f"  بازده شاخص کل       {pct(m.get('benchmark_return'))}")
    print(f"  بازده مازاد         {pct(m.get('excess_return'))}")
    print(f"  حداکثر افت سرمایه   {pct(m.get('max_drawdown'))}")
    print(f"  شارپ (سالانه)       {m.get('sharpe', 0):.2f}")
    print(f"  معاملات             {m.get('trades', 0)}  ·  برد {m.get('win_rate', 0) * 100:.1f}%")
    pf = m.get("profit_factor")
    print(f"  نسبت سود/زیان       {pf:.2f}" if pf else "  نسبت سود/زیان       —")
    print(f"  میانگین نگهداری     {m.get('avg_holding_days', 0):.1f} روز")
    print(f"  در معرض بودن        {m.get('exposure', 0) * 100:.0f}%")
    print("─" * 52)
    print(f"✓ گزارش: {html_path}")
    print(f"  داده:  {json_path}")
    print(f"  زمان:  {elapsed:.1f} ثانیه")

    if args.open:
        import webbrowser

        webbrowser.open(html_path.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
