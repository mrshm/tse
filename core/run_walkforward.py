#!/usr/bin/env python3
"""اعتبارسنجی راه‌رونده: پارامترها روی بازهٔ آموزش انتخاب، روی بازهٔ آزمون اجرا.

مثال:
    python run_walkforward.py
    python run_walkforward.py --days 500 --train 150 --test 50 --rank calmar
    python run_walkforward.py --symbols 300 --days 450 --open
"""

from __future__ import annotations

import argparse
import os
import json
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
from tse.universe import build_universe  # noqa: E402
from tse.walkforward import (  # noqa: E402
    WalkConfig,
    default_grid,
    make_cfg,
    run_walkforward,
    slice_prepared,
    summarise,
)
from web.wf_report import render_walkforward  # noqa: E402

RIAL_PER_TOMAN = 10
WARMUP_DAYS = 60


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="اعتبارسنجی راه‌رونده استراتژی")
    p.add_argument("--days", type=int, default=450, help="طول تاریخچه (روز معاملاتی)")
    p.add_argument("--symbols", type=int, default=300,
                   help="محدودکردن به N نماد نقدشونده (۰ = همه)")
    p.add_argument("--train", type=int, default=120, help="طول بازهٔ آموزش هر فولد")
    p.add_argument("--test", type=int, default=40, help="طول بازهٔ آزمون هر فولد")
    p.add_argument("--rank", choices=("sharpe", "calmar", "total_return"),
                   default="sharpe", help="معیار انتخاب پارامتر در بازهٔ آموزش")
    p.add_argument("--top", default="3,5,8", help="شبکه: تعداد سهم هم‌زمان")
    p.add_argument("--hold", default="10,20", help="شبکه: روز نگهداری")
    p.add_argument("--stop", default="1.5,2.5", help="شبکه: حد ضرر بر حسب ATR")
    p.add_argument("--target", default="0,2.5", help="شبکه: هدف (۰ = بدون هدف)")
    p.add_argument("--capital", type=float, default=100.0, help="میلیون تومان")
    p.add_argument("--min-hold", type=int, default=2)
    p.add_argument("--min-value", type=float, default=2.0,
                   help="حداقل میانگین ارزش معاملات (میلیارد تومان)")
    p.add_argument("--buy-fee", type=float, default=0.45)
    p.add_argument("--sell-fee", type=float, default=0.95)
    p.add_argument("--etf", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--markets", default="بورس,فرابورس,پایه,کالا")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", default="walkforward.html")
    p.add_argument("--json-out", default="data/walkforward_latest.json")
    p.add_argument("--open", action="store_true")
    return p.parse_args()


def num_list(text: str) -> list[float]:
    return [float(x) for x in str(text).split(",") if x.strip()] or [0.0]


def jalali(d_even: int) -> str:
    try:
        d = datetime.strptime(str(int(d_even)), "%Y%m%d")
        return jdatetime.date.fromgregorian(date=d).strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        return "—"


def benchmark_series(client: TSEClient) -> pd.Series:
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
    print(f"  {panel['symbol'].nunique()} نماد · {len(panel):,} ردیف", flush=True)

    panel = score_panel(panel)
    prep = prepare(panel)
    try:
        bench = benchmark_series(client)
    except FetchError:
        bench = pd.Series(dtype="float64")

    base = dict(
        buy_fee=args.buy_fee / 100,
        sell_fee=args.sell_fee / 100,
        min_value=args.min_value * 1e9 * RIAL_PER_TOMAN,
        min_hold=args.min_hold,
        include_etf=args.etf,
        trail_atr=0.0,
    )

    grid = [
        {"top_n": int(t), "max_hold": int(h), "stop_atr": s, "target_atr": tg}
        for t in num_list(args.top)
        for h in num_list(args.hold)
        for s in num_list(args.stop)
        for tg in num_list(args.target)
    ]
    grid = [g for g in grid if g["max_hold"] >= args.min_hold + 1] or default_grid()

    cfg = WalkConfig(
        train_days=args.train,
        test_days=args.test,
        rank=args.rank,
        capital=args.capital * 1e6 * RIAL_PER_TOMAN,
        grid=grid,
        base=base,
    )

    print(f"→ {len(grid)} ترکیب در {args.train}+{args.test} روز …", flush=True)
    try:
        walk = run_walkforward(panel, prep, bench, cfg)
    except ValueError as exc:
        print(f"خطا: {exc}", file=sys.stderr)
        return 1

    summary = summarise(walk, bench, cfg)

    # ---- مقایسه با ترکیب‌های ثابت روی همان بازهٔ آزمون
    test_lo = walk["folds"][0]["test"][0]
    test_hi = walk["folds"][-1]["test"][1]
    span = slice_prepared(prep, test_lo, test_hi)

    baselines = []
    fixed_defs = [
        ("default", "پیش‌فرض ۵ روزه، هدف ۲.۵×ATR",
         {"top_n": 5, "max_hold": 5, "stop_atr": 2.0, "target_atr": 2.5}),
        ("patient", "نگهداری ۲۰ روزه، بدون هدف",
         {"top_n": 5, "max_hold": 20, "stop_atr": 2.0, "target_atr": 0.0}),
    ]
    for key, label, params in fixed_defs:
        if params["max_hold"] < args.min_hold + 1:
            params = dict(params, max_hold=args.min_hold + 1)
        c = make_cfg(params, base, cfg.capital)
        m = compute_metrics(simulate(panel, c, prepared=span), c, bench)
        if m:
            baselines.append({"key": key, "label": label, "params": params,
                              "total_return": m["total_return"], "sharpe": m["sharpe"],
                              "max_drawdown": m["max_drawdown"], "trades": m["trades"],
                              "benchmark_return": m["benchmark_return"]})

    # «بهترین ترکیب با علم به آینده» — عددی که نباید به آن امید بست
    oracle, oracle_score = None, -9e9
    for params in grid:
        c = make_cfg(params, base, cfg.capital)
        m = compute_metrics(simulate(panel, c, prepared=span), c, bench)
        if not m:
            continue
        s = m.get(cfg.rank) or -9e9
        if s > oracle_score:
            oracle_score, oracle = s, {
                "key": "oracle", "label": "بهترین ترکیب روی همین بازه (با علم به آینده)",
                "params": params, "total_return": m["total_return"], "sharpe": m["sharpe"],
                "max_drawdown": m["max_drawdown"], "trades": m["trades"],
                "benchmark_return": m["benchmark_return"],
            }
    if oracle:
        baselines.append(oracle)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_at_fa": jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
        "period": [jalali(summary["start_date"]), jalali(summary["end_date"])],
        "config": {
            "days": args.days,
            "symbols": len(universe),
            "train_days": args.train,
            "test_days": args.test,
            "rank": args.rank,
            "capital_toman": args.capital * 1e6,
            "min_hold": args.min_hold,
            "buy_fee_pct": args.buy_fee,
            "sell_fee_pct": args.sell_fee,
            "include_etf": args.etf,
            "grid_size": len(grid),
        },
        "summary": summary,
        "folds": [
            {**f, "train_fa": [jalali(f["train"][0]), jalali(f["train"][1])],
             "test_fa": [jalali(f["test"][0]), jalali(f["test"][1])]}
            for f in walk["folds"]
        ],
        "baselines": baselines,
        "curve": _curve_payload(walk, bench, cfg),
    }

    json_path = ROOT / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    html_path = Path(args.out)
    if not html_path.is_absolute():
        html_path = output_dir(ROOT) / html_path
    html_path.write_text(render_walkforward(payload), encoding="utf-8")

    elapsed = (datetime.now() - started).total_seconds()
    _print_summary(payload)
    print(f"✓ گزارش: {html_path}")
    print(f"  داده:  {json_path}")
    print(f"  {len(walk['folds'])} فولد · {len(grid) * len(walk['folds'])} شبیه‌سازی "
          f"در {elapsed:.1f} ثانیه")

    if args.open:
        import webbrowser

        webbrowser.open(html_path.as_uri())
    return 0


def _curve_payload(walk: dict, bench: pd.Series, cfg: WalkConfig) -> list[dict]:
    rows = [r for r in walk["curve"] if r.get("equity")]
    if not rows:
        return []
    df = pd.DataFrame(rows).drop_duplicates("date").sort_values("date").set_index("date")
    eq = df["equity"].astype(float)
    eq = eq / float(eq.iloc[0]) * 100
    b = bench.reindex(eq.index).ffill().bfill()
    b = b / float(b.iloc[0]) * 100 if b.notna().any() else b
    return [
        {"d": int(d), "fa": jalali(int(d)), "eq": float(eq.loc[d]),
         "b": float(b.loc[d]) if pd.notna(b.loc[d]) else None}
        for d in eq.index
    ]


def _print_summary(payload: dict) -> None:
    s = payload["summary"]
    print("\n" + "─" * 78)
    print(f"  اعتبارسنجی راه‌رونده · {payload['period'][0]} تا {payload['period'][1]} · "
          f"{s['folds']} فولد")
    print("─" * 78)
    print(f"  {'فولد':>5} {'آزمون':>12} {'سهم':>4} {'نگهداری':>8} {'تست':>9} "
          f"{'شاخص':>9} {'معامله':>7}")
    for f in payload["folds"]:
        print(f"  {f['fold']:>5} {f['test_fa'][0]:>12} {f['params']['top']:>4} "
              f"{f['params']['hold']:>8} {f['test_return'] * 100:>8.1f}% "
              f"{f['benchmark_return'] * 100:>8.1f}% {f['trades']:>7}")
    print("─" * 78)
    print(f"  بازده کل راه‌رونده: {s['total_return'] * 100:>7.1f}%   "
          f"شاخص کل: {s['benchmark_return'] * 100:>7.1f}%   "
          f"افت: {s['max_drawdown'] * 100:>6.1f}%")
    print(f"  فولدهای سودده: {s['folds_positive']} از {s['folds']} · "
          f"فولدهای بالاتر از شاخص: {s['folds_beat_bench']} از {s['folds']}")
    for b in payload["baselines"]:
        print(f"  · {b['label']}: {b['total_return'] * 100:>7.1f}% "
              f"(افت {b['max_drawdown'] * 100:.1f}%)")
    print("─" * 78)


if __name__ == "__main__":
    raise SystemExit(main())
