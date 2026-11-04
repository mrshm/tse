#!/usr/bin/env python3
"""ریسک ورشکستگی: با این اندازهٔ موقعیت، احتمال از دست دادن حساب چقدر است؟

مثال:
    python core/run_risk.py
    python core/run_risk.py --risk 1 --win 45 --payoff 1.8 --stop 7 --trades 200
    python core/run_risk.py --from-journal          # نرخ برد و R از دفتر معاملات
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

from tse.journal import load as load_journal  # noqa: E402
from tse.journal import stats as journal_stats  # noqa: E402
from tse.risk import RiskConfig, curve_bands, kelly, ladder, simulate  # noqa: E402
from web.risk_report import render_risk  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ریسک ورشکستگی و اندازهٔ موقعیت")
    p.add_argument("--capital", type=float, default=100.0, help="سرمایه (میلیون تومان)")
    p.add_argument("--risk", type=float, default=1.0,
                   help="درصد سرمایه که در هر معامله تا حد ضرر ریسک می‌شود")
    p.add_argument("--stop", type=float, default=7.0, help="فاصلهٔ حد ضرر از قیمت ورود (٪)")
    p.add_argument("--win", type=float, default=45.0, help="نرخ برد (٪)")
    p.add_argument("--payoff", type=float, default=1.8,
                   help="میانگین سود به زیان بر حسب R")
    p.add_argument("--fees", type=float, default=1.4,
                   help="کارمزد رفت‌وبرگشت (درصد ارزش معامله)")
    p.add_argument("--trades", type=int, default=200, help="تعداد معامله در افق")
    p.add_argument("--sims", type=int, default=10_000, help="تعداد شبیه‌سازی")
    p.add_argument("--ruin", type=float, default=30.0,
                   help="افت سرمایه (٪) که ورشکستگی حساب می‌شود")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--from-journal", action="store_true",
                   help="نرخ برد و R را از data/journal.json بخوان")
    p.add_argument("--journal", default="data/journal.json")
    p.add_argument("--out", default="risk.html")
    p.add_argument("--json-out", default="data/risk_latest.json")
    p.add_argument("--open", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    win, payoff, source = args.win, args.payoff, "پیش‌فرض"

    if args.from_journal:
        jp = Path(args.journal)
        jp = jp if jp.is_absolute() else ROOT / jp
        s = journal_stats(load_journal(jp))
        if s["closed"] >= 10 and s["avg_loss_pct"] < 0 and s["avg_win_pct"] > 0:
            win = s["win_rate"] * 100
            payoff = s["avg_win_pct"] / abs(s["avg_loss_pct"])
            source = f"دفتر معاملات ({s['closed']} معامله)"
        else:
            print("⚠ دفتر معاملات کمتر از ۱۰ معاملهٔ بسته‌شده دارد؛ "
                  "از مقادیر پیش‌فرض استفاده شد.", file=sys.stderr)

    cfg = RiskConfig(
        capital=args.capital * 1e6,
        risk_pct=args.risk,
        stop_pct=args.stop,
        payoff_r=payoff,
        win_rate=win / 100.0,
        fees_pct=args.fees,
        trades=args.trades,
        sims=args.sims,
        ruin_pct=args.ruin,
        seed=args.seed,
    )

    s = simulate(cfg)
    lad = ladder(cfg)
    k = kelly(cfg)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_at_fa": jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
        "source": source,
        "config": {
            "capital_toman": cfg.capital,
            "risk_pct": cfg.risk_pct,
            "stop_pct": cfg.stop_pct,
            "payoff_r": cfg.payoff_r,
            "win_rate": cfg.win_rate,
            "fees_pct": cfg.fees_pct,
            "trades": cfg.trades,
            "sims": cfg.sims,
            "ruin_pct": cfg.ruin_pct,
        },
        "summary": {
            "p_ruin": s["p_ruin"],
            "p_profit": s["p_profit"],
            "median_final": s["median_final"],
            "p05_final": s["p05_final"],
            "p95_final": s["p95_final"],
            "median_dd": s["median_dd"],
            "growth_per_trade": s["growth_per_trade"],
            "p_dd": s["p_dd"],
            "win_mult": s["win_mult"],
            "loss_mult": s["loss_mult"],
        },
        "kelly": k,
        "ladder": lad,
        "bands": curve_bands(s["paths"]),
    }

    json_path = ROOT / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    html_path = Path(args.out)
    if not html_path.is_absolute():
        html_path = output_dir(ROOT) / html_path
    html_path.write_text(render_risk(payload), encoding="utf-8")

    cap = cfg.capital
    print("\n" + "─" * 74)
    print(f"  ریسک ورشکستگی · {args.sims:,} مسیر × {args.trades} معامله "
          f"(نرخ برد و R از {source})")
    print("─" * 74)
    print(f"  ریسک {cfg.risk_pct:g}٪ سرمایه در هر معامله · حد ضرر {cfg.stop_pct:g}٪ · "
          f"موقعیت ≈ {cfg.risk_pct / cfg.stop_pct * 100:.0f}٪ سرمایه")
    print(f"  نرخ برد {cfg.win_rate * 100:g}٪ · R {cfg.payoff_r:g} · "
          f"کارمزد {cfg.fees_pct:g}٪")
    print("─" * 74)
    print(f"  احتمال سود:            {s['p_profit'] * 100:5.1f}%")
    print(f"  میانهٔ سرمایهٔ پایانی:   {s['median_final'] * cap / 1e6:8,.1f} م.ت "
          f"({(s['median_final'] - 1) * 100:+.1f}%)")
    print(f"  بدترین ۵٪:             {s['p05_final'] * cap / 1e6:8,.1f} م.ت "
          f"({(s['p05_final'] - 1) * 100:+.1f}%)")
    print(f"  احتمال افت ≥ ۲۰٪:      {s['p_dd']['20'] * 100:5.1f}%")
    print(f"  احتمال افت ≥ ۵۰٪:      {s['p_dd']['50'] * 100:5.1f}%")
    print(f"  احتمال ورشکستگی (↓{args.ruin:g}٪): {s['p_ruin'] * 100:5.1f}%")
    print(f"  رشد هندسی هر معامله:   {s['growth_per_trade'] * 100:+.2f}%")
    print(f"  کِلی: {k['full'] * 100:.1f}٪ (نصف {k['half'] * 100:.1f}٪)")
    print("─" * 74)
    print(f"  {'ریسک':>6} {'موقعیت':>7} {'ورشکستگی':>10} {'سود':>7} "
          f"{'میانه':>10} {'۵٪ بد':>10}")
    for r in lad:
        print(f"  {r['risk_pct']:>5.2f}% {r['position_pct']:>6.0f}% "
              f"{r['p_ruin'] * 100:>9.1f}% {r['p_profit'] * 100:>6.1f}% "
              f"{r['median_final'] * cap / 1e6:>9,.0f} {r['p05_final'] * cap / 1e6:>9,.0f}")
    print("─" * 74)
    print(f"✓ گزارش: {html_path}\n  داده:  {json_path}")

    if args.open:
        import webbrowser

        webbrowser.open(html_path.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
