#!/usr/bin/env python3
"""جست‌وجوی پارامتر استراتژی: اجرای چند پیکربندی روی یک پنل و مقایسهٔ نتیجه.

مثال:
    python core/run_sweep.py --symbols 300 --days 450
    python core/run_sweep.py --top 3,5,8 --hold 5,10,20,40 --target 0,2.5
    python core/run_sweep.py --rank calmar --open
"""

from __future__ import annotations

import argparse
import os
import itertools
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
    build_panel,
    compute_metrics,
    prepare,
    score_panel,
    simulate,
)
from tse.client import FetchError, TSEClient  # noqa: E402
from web.sweep_report import render_sweep  # noqa: E402
from tse.universe import build_universe  # noqa: E402

RIAL_PER_TOMAN = 10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="جست‌وجوی پارامتر استراتژی")
    p.add_argument("--days", type=int, default=400)
    p.add_argument("--symbols", type=int, default=400,
                   help="محدودکردن به N نماد نقدشونده (۰ = همه)")
    p.add_argument("--top", default="3,5,8", help="تعداد سهم هم‌زمان (لیست با کاما)")
    p.add_argument("--hold", default="5,10,20,40", help="حداکثر روز نگهداری")
    p.add_argument("--stop", default="1.5,2.0,2.5", help="حد ضرر بر حسب ATR")
    p.add_argument("--target", default="0,2.5,4.0", help="هدف سود (۰ = بدون هدف)")
    p.add_argument("--trail", default="0", help="حد ضرر متحرک (۰ = خاموش)")
    p.add_argument("--min-score", type=float, default=0.0)
    p.add_argument("--min-hold", type=int, default=2)
    p.add_argument("--capital", type=float, default=100.0, help="میلیون تومان")
    p.add_argument("--buy-fee", type=float, default=0.45)
    p.add_argument("--sell-fee", type=float, default=0.95)
    p.add_argument("--min-value", type=float, default=2.0)
    p.add_argument("--markets", default="بورس,فرابورس,پایه,کالا")
    p.add_argument("--etf", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--rank", choices=("sharpe", "calmar", "return"), default="sharpe",
                   help="معیار رتبه‌بندی ترکیب‌ها")
    p.add_argument("--max-combos", type=int, default=400)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", default="sweep.html")
    p.add_argument("--json-out", default="data/sweep_latest.json")
    p.add_argument("--open", action="store_true")
    return p.parse_args()


def num_list(text: str) -> list[float]:
    out = []
    for part in str(text).split(","):
        part = part.strip()
        if part:
            out.append(float(part))
    return out or [0.0]


def jalali(d_even: int) -> str:
    try:
        d = datetime.strptime(str(int(d_even)), "%Y%m%d")
        return jdatetime.date.fromgregorian(date=d).strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        return "—"


def main() -> int:
    args = parse_args()
    started = datetime.now()
    client = TSEClient(workers=args.workers)
    markets = {m.strip() for m in args.markets.split(",") if m.strip()}

    tops = [int(x) for x in num_list(args.top)]
    holds = [int(x) for x in num_list(args.hold)]
    stops = num_list(args.stop)
    targets = num_list(args.target)
    trails = num_list(args.trail)

    grid = list(itertools.product(tops, holds, stops, targets, trails))
    grid = grid[: args.max_combos]
    print(f"→ {len(grid)} ترکیب برای آزمون")

    print("→ دریافت فهرست نمادها …", flush=True)
    try:
        mw_rows = client.market_watch()
    except FetchError as exc:
        print(f"خطا در دریافت داده: {exc}", file=sys.stderr)
        return 1

    universe = [
        u for u in build_universe(mw_rows)
        if u["market"] in markets and (args.etf or not u["is_etf"])
    ]
    if args.symbols > 0:
        universe.sort(key=lambda u: u["value"], reverse=True)
        universe = universe[: args.symbols]

    print(f"→ تاریخچهٔ {args.days} روزه برای {len(universe)} نماد …", flush=True)
    panel = build_panel(client, universe, days=args.days)
    if panel.empty:
        print("داده‌ای پیدا نشد.", file=sys.stderr)
        return 1
    print(f"  {panel['symbol'].nunique()} نماد · {len(panel):,} ردیف")

    panel = score_panel(panel)
    prepared = prepare(panel)
    warmup_date = int(prepared.dates[0]) if len(prepared.dates) else 0
    last_date = int(prepared.dates[-1]) if len(prepared.dates) else 0

    try:
        bench = _benchmark(client)
    except FetchError:
        bench = pd.Series(dtype="float64")

    base = dict(
        capital=args.capital * 1e6 * RIAL_PER_TOMAN,
        buy_fee=args.buy_fee / 100,
        sell_fee=args.sell_fee / 100,
        min_value=args.min_value * 1e9 * RIAL_PER_TOMAN,
        min_score=args.min_score,
        min_hold=args.min_hold,
        include_etf=args.etf,
    )

    combos: list[dict] = []
    for i, (top, hold, stop, target, trail) in enumerate(grid, 1):
        hold = max(hold, args.min_hold + 1)
        cfg = BacktestConfig(
            top_n=top, max_hold=hold, stop_atr=stop,
            target_atr=target, trail_atr=trail, **base,
        )
        result = simulate(panel, cfg, prepared=prepared)
        m = compute_metrics(result, cfg, bench)
        if not m:
            continue
        combos.append(
            {
                "top": top,
                "hold": hold,
                "stop": stop,
                "target": target,
                "trail": trail,
                "total_return": m["total_return"],
                "cagr": m["cagr"],
                "sharpe": m["sharpe"],
                "calmar": m["calmar"],
                "max_drawdown": m["max_drawdown"],
                "trades": m["trades"],
                "win_rate": m["win_rate"],
                "avg_hold": m["avg_holding_days"],
                "exposure": m["exposure"],
                "fees_pct": m["fees_pct_of_capital"],
                "benchmark_return": m["benchmark_return"],
            }
        )
        if i % 12 == 0 or i == len(grid):
            print(f"  {i}/{len(grid)}", flush=True)

    if not combos:
        print("هیچ ترکیبی نتیجه نداد.", file=sys.stderr)
        return 1

    key = {"sharpe": "sharpe", "calmar": "calmar", "return": "total_return"}[args.rank]
    ranked = sorted(combos, key=lambda c: (c[key] if c[key] is not None else -9e9), reverse=True)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_at_fa": jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
        "rank": args.rank,
        "period": [jalali(warmup_date), jalali(last_date)],
        "benchmark_return": combos[0]["benchmark_return"],
        "config": {
            "days": args.days,
            "symbols": len(universe),
            "min_hold": args.min_hold,
            "min_value_btooman": args.min_value,
            "capital_toman": args.capital * 1e6,
            "buy_fee_pct": args.buy_fee,
            "sell_fee_pct": args.sell_fee,
            "include_etf": args.etf,
            "grid": {
                "top": tops, "hold": holds, "stop": stops,
                "target": targets, "trail": trails,
            },
        },
        "combos": ranked,
        "best": ranked[0],
    }

    json_path = ROOT / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    html_path = Path(args.out)
    if not html_path.is_absolute():
        html_path = output_dir(ROOT) / html_path
    html_path.write_text(render_sweep(payload), encoding="utf-8")

    elapsed = (datetime.now() - started).total_seconds()
    print("\n" + "─" * 74)
    print(f"  {'top':>4} {'hold':>5} {'stop':>5} {'target':>7} {'trail':>6} "
          f"{'بازده':>9} {'شارپ':>7} {'افت':>8} {'معامله':>7}")
    for c in ranked[:10]:
        print(f"  {c['top']:>4} {c['hold']:>5} {c['stop']:>5.1f} {c['target']:>7.1f} "
              f"{c['trail']:>6.1f} {c['total_return'] * 100:>8.1f}% {c['sharpe']:>7.2f} "
              f"{c['max_drawdown'] * 100:>7.1f}% {c['trades']:>7}")
    print("─" * 74)
    print(f"✓ گزارش: {html_path}")
    print(f"  داده:  {json_path}")
    print(f"  {len(combos)} ترکیب در {elapsed:.1f} ثانیه")

    if args.open:
        import webbrowser

        webbrowser.open(html_path.as_uri())
    return 0


def _benchmark(client: TSEClient) -> pd.Series:
    rows = client.index_history()
    out: dict[int, float] = {}
    for r in rows:
        try:
            d = int(r["dEven"])
            v = float(r["xNivInuClMresIbs"] or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if v > 0:
            out[d] = v
    return pd.Series(out).sort_index() if out else pd.Series(dtype="float64")


if __name__ == "__main__":
    raise SystemExit(main())
