"""ریسک ورشکستگی: شبیه‌سازی مونت‌کارلوی زنجیرهٔ معاملات.

سؤال: با این نرخ برد و این اندازهٔ موقعیت، احتمال اینکه سرمایه‌ات در N معامله
فلان‌قدر افت کند چقدر است؟ و چه اندازه‌ای از موقعیت، هم سود می‌دهد هم تو را
از بازی بیرون نمی‌کند؟
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RiskConfig:
    capital: float = 100_000_000     # تومان
    risk_pct: float = 1.0            # درصد سرمایه تا حد ضرر در هر معامله
    stop_pct: float = 7.0            # فاصلهٔ حد ضرر از قیمت ورود (درصد)
    payoff_r: float = 1.8            # میانگین سود به ازای هر واحد ریسک (R)
    win_rate: float = 0.45
    fees_pct: float = 1.4            # کارمزد رفت‌وبرگشت، درصد ارزش معامله
    trades: int = 200
    sims: int = 10_000
    ruin_pct: float = 30.0           # افت‌ای که «ورشکستگی» حساب می‌شود
    seed: int = 7


def _trade_outcomes(cfg: RiskConfig) -> tuple[float, float]:
    """ضریب سرمایه در معاملهٔ برنده و بازنده."""
    position = cfg.risk_pct / cfg.stop_pct          # سهم سرمایه در هر معامله
    fee = position * cfg.fees_pct / 100.0
    win = 1 + position * (cfg.stop_pct * cfg.payoff_r / 100.0) - fee
    loss = 1 - position * (cfg.stop_pct / 100.0) - fee
    return win, loss


def simulate(cfg: RiskConfig, risk_pct: float | None = None) -> dict:
    risk = cfg.risk_pct if risk_pct is None else risk_pct
    c = RiskConfig(**{**cfg.__dict__, "risk_pct": risk})
    win_mult, loss_mult = _trade_outcomes(c)
    rng = np.random.default_rng(cfg.seed)

    wins = rng.random((cfg.sims, cfg.trades)) < cfg.win_rate
    mult = np.where(wins, win_mult, loss_mult)
    paths = np.cumprod(mult, axis=1)

    peak = np.maximum.accumulate(paths, axis=1)
    dd = paths / peak - 1.0
    worst_dd = dd.min(axis=1)

    ruin = worst_dd <= -cfg.ruin_pct / 100.0
    final = paths[:, -1]

    # میانگین هندسی در هر معامله
    g = float(np.exp(np.log(paths[:, -1]).mean() / cfg.trades) - 1)

    return {
        "risk_pct": risk,
        "position_pct": c.risk_pct / c.stop_pct * 100,
        "win_mult": win_mult,
        "loss_mult": loss_mult,
        "paths": np.hstack([np.ones((cfg.sims, 1)), paths]),
        "final": final,
        "worst_dd": worst_dd,
        "p_ruin": float(ruin.mean()),
        "p_profit": float((final > 1).mean()),
        "median_final": float(np.median(final)),
        "p05_final": float(np.percentile(final, 5)),
        "p95_final": float(np.percentile(final, 95)),
        "median_dd": float(np.median(worst_dd)),
        "growth_per_trade": g,
        "p_dd": {
            f"{x}": float((worst_dd <= -x / 100.0).mean())
            for x in (10, 20, 30, 50, 75)
        },
    }


def kelly(cfg: RiskConfig) -> dict:
    """کسر کلی برای شرط‌بندی با شانس p و ضریب R؛ و نصف‌کلی که در عمل امن‌تر است."""
    p = cfg.win_rate
    q = 1 - p
    f = p - q / cfg.payoff_r if cfg.payoff_r > 0 else 0.0
    return {"full": f, "half": f / 2, "quarter": f / 4}


def ladder(cfg: RiskConfig, values: list[float] | None = None) -> list[dict]:
    """جدول: برای هر اندازهٔ ریسک، احتمال ورشکستگی و بازده میانه."""
    values = values or [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    out = []
    for v in values:
        s = simulate(cfg, risk_pct=v)
        out.append(
            {
                "risk_pct": v,
                "position_pct": s["position_pct"],
                "p_ruin": s["p_ruin"],
                "p_profit": s["p_profit"],
                "median_final": s["median_final"],
                "p05_final": s["p05_final"],
                "median_dd": s["median_dd"],
                "growth_per_trade": s["growth_per_trade"],
            }
        )
    return out


def curve_bands(paths: np.ndarray, groups: int = 120) -> dict:
    """میانه و باندهای درصدی مسیر سرمایه برای نمودار."""
    n = paths.shape[1]
    idx = np.unique(np.linspace(0, n - 1, min(groups, n)).astype(int))
    sub = paths[:, idx] * 100.0
    return {
        "t": idx.tolist(),
        "p05": np.percentile(sub, 5, axis=0).tolist(),
        "p25": np.percentile(sub, 25, axis=0).tolist(),
        "p50": np.percentile(sub, 50, axis=0).tolist(),
        "p75": np.percentile(sub, 75, axis=0).tolist(),
        "p95": np.percentile(sub, 95, axis=0).tolist(),
    }
