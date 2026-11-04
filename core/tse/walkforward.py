"""اعتبارسنجی راه‌رونده (walk-forward).

ایده: پارامترها را فقط روی یک بازهٔ آموزش انتخاب کن، بعد همان پارامترها را روی
بازهٔ آزمونِ دست‌نخورده اجرا کن. اگر نتیجه در بازهٔ آزمون هم تکرار شد، لبه واقعی
است؛ اگر نه، بهترین ترکیبِ جست‌وجو فقط بیش‌برازش بوده.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .backtest import (
    BacktestConfig,
    PreparedPanel,
    compute_metrics,
    simulate,
)

# حداقل تاریخچهٔ لازم برای گرم‌شدن اندیکاتورها
WARMUP_DAYS = 60


@dataclass
class WalkConfig:
    train_days: int = 120
    test_days: int = 40
    rank: str = "sharpe"          # sharpe | calmar | total_return
    capital: float = 1e10         # ریال
    grid: list[dict] = field(default_factory=list)
    base: dict = field(default_factory=dict)


def slice_prepared(prep: PreparedPanel, lo: int, hi: int) -> PreparedPanel:
    dates = prep.dates[(prep.dates >= lo) & (prep.dates <= hi)]
    return PreparedPanel(
        dates=dates,
        day_maps={int(d): prep.day_maps[int(d)] for d in dates if int(d) in prep.day_maps},
    )


def make_cfg(params: dict, base: dict, capital: float) -> BacktestConfig:
    kw = dict(base)
    kw.update(params)
    kw["capital"] = capital
    kw["warmup"] = 0
    return BacktestConfig(**kw)


def default_grid() -> list[dict]:
    """شبکهٔ کوچک: به‌اندازه‌ای کوچک که هر فولد در چند ثانیه تمام شود."""
    out = []
    for top, hold, stop, target in itertools.product(
        (3, 5, 8), (10, 20), (1.5, 2.5), (0.0, 2.5)
    ):
        out.append({"top_n": top, "max_hold": hold, "stop_atr": stop, "target_atr": target})
    return out


def _rank_value(m: dict, key: str) -> float:
    v = m.get(key)
    if v is None or not math.isfinite(v):
        return -9e9
    return float(v)


def run_walkforward(
    panel: pd.DataFrame,
    prep: PreparedPanel,
    benchmark: pd.Series,
    cfg: WalkConfig,
) -> dict:
    """فولدها را اجرا می‌کند و منحنی سرمایهٔ چسبیده + جزئیات هر فولد را برمی‌گرداند."""
    grid = cfg.grid or default_grid()
    usable = prep.dates[WARMUP_DAYS:]
    if len(usable) < cfg.train_days + 10:
        raise ValueError(
            f"دادهٔ کافی نیست: {len(usable)} روز قابل استفاده، "
            f"حداقل {cfg.train_days + 10} لازم است."
        )

    folds: list[dict] = []
    stitched: list[dict] = []
    all_trades: list[dict] = []
    capital = float(cfg.capital)

    pos = 0
    while pos + cfg.train_days + 10 <= len(usable):
        train_dates = usable[pos: pos + cfg.train_days]
        test_dates = usable[pos + cfg.train_days: pos + cfg.train_days + cfg.test_days]
        if len(test_dates) < 10:
            break

        train_lo, train_hi = int(train_dates[0]), int(train_dates[-1])
        test_lo, test_hi = int(test_dates[0]), int(test_dates[-1])
        train_prep = slice_prepared(prep, train_lo, train_hi)
        test_prep = slice_prepared(prep, test_lo, test_hi)

        # ----- انتخاب پارامترها فقط با دادهٔ آموزش
        best, best_score, best_metrics = None, -9e9, None
        for params in grid:
            c = make_cfg(params, cfg.base, cfg.capital)
            res = simulate(panel, c, prepared=train_prep)
            m = compute_metrics(res, c, benchmark)
            if not m:
                continue
            s = _rank_value(m, cfg.rank)
            if s > best_score:
                best, best_score, best_metrics = params, s, m

        if best is None:
            pos += cfg.test_days
            continue

        # ----- اجرای همان پارامترها روی بازهٔ آزمون، با سرمایهٔ جاری
        c_test = make_cfg(best, cfg.base, capital)
        res_test = simulate(panel, c_test, prepared=test_prep)
        m_test = compute_metrics(res_test, c_test, benchmark)
        if not m_test:
            pos += cfg.test_days
            continue

        for row in res_test["curve"]:
            stitched.append(dict(row))
        for t in res_test["trades"]:
            t = dict(t)
            t["fold"] = len(folds) + 1
            all_trades.append(t)

        end_capital = float(m_test["final_equity"])

        folds.append(
            {
                "fold": len(folds) + 1,
                "train": [train_lo, train_hi],
                "test": [test_lo, test_hi],
                "params": {
                    "top": best["top_n"],
                    "hold": best["max_hold"],
                    "stop": best["stop_atr"],
                    "target": best["target_atr"],
                },
                "train_return": best_metrics["total_return"],
                "train_sharpe": best_metrics["sharpe"],
                "test_return": m_test["total_return"],
                "test_sharpe": m_test["sharpe"],
                "test_dd": m_test["max_drawdown"],
                "benchmark_return": m_test["benchmark_return"],
                "trades": m_test["trades"],
                "win_rate": m_test["win_rate"],
                "start_capital": capital,
                "end_capital": end_capital,
            }
        )
        capital = end_capital
        pos += cfg.test_days

    if not folds:
        raise ValueError("هیچ فولدی اجرا نشد.")

    return {
        "folds": folds,
        "curve": stitched,
        "trades": all_trades,
        "final_equity": capital,
        "grid_size": len(grid),
    }


def summarise(walk: dict, benchmark: pd.Series, cfg: WalkConfig) -> dict:
    """متریک‌های کل مسیر آزمون + مقایسه با شاخص و با ترکیب ثابت."""
    curve = pd.DataFrame(walk["curve"])
    if curve.empty:
        return {}
    curve = curve.drop_duplicates("date").sort_values("date").set_index("date")

    # سرمایهٔ ابتدای مسیر به قیمت امروز مقیاس شود تا افت/بازده درست حساب شود
    scale = float(cfg.capital)
    eq = curve["equity"].astype(float)
    eq_norm = eq / float(eq.iloc[0]) * scale
    bench = benchmark.reindex(eq.index).ffill().bfill()

    total = float(eq_norm.iloc[-1] / scale - 1)
    rets = eq_norm.pct_change().fillna(0.0)
    std = float(rets.std())
    sharpe = float(rets.mean() / std * math.sqrt(252)) if std > 0 else 0.0
    dd = float((eq_norm / eq_norm.cummax() - 1).min())
    years = max(len(eq_norm) / 250.0, 1 / 250.0)
    cagr = (1 + total) ** (1 / years) - 1 if total > -1 else -1.0

    bench_total = 0.0
    if bench.notna().any():
        b = bench.dropna()
        bench_total = float(b.iloc[-1] / b.iloc[0] - 1)

    trades = pd.DataFrame(walk["trades"])
    wins = int((trades["pnl"] > 0).sum()) if not trades.empty else 0
    win_rate = wins / len(trades) if len(trades) else 0.0
    fees = float(trades["fees"].sum()) if not trades.empty else 0.0

    fold_returns = [f["test_return"] for f in walk["folds"]]
    bench_by_fold = [f["benchmark_return"] for f in walk["folds"]]

    return {
        "total_return": total,
        "cagr": cagr,
        "sharpe": sharpe,
        "calmar": cagr / abs(dd) if dd < 0 else 0.0,
        "max_drawdown": dd,
        "benchmark_return": bench_total,
        "excess_return": total - bench_total,
        "trades": int(len(trades)),
        "win_rate": win_rate,
        "fees_total": fees,
        "folds": len(walk["folds"]),
        "folds_positive": int(sum(1 for r in fold_returns if r > 0)),
        "folds_beat_bench": int(sum(1 for r, b in zip(fold_returns, bench_by_fold) if r > b)),
        "median_fold_return": float(np.median(fold_returns)) if fold_returns else 0.0,
        "worst_fold": float(min(fold_returns)) if fold_returns else 0.0,
        "best_fold": float(max(fold_returns)) if fold_returns else 0.0,
        "start_date": int(eq.index[0]),
        "end_date": int(eq.index[-1]),
    }
