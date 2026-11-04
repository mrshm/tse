"""موتور بک‌تست استراتژی اسکنر روی دادهٔ تاریخی TSETMC.

روش کار:
  ۱) پنل روزانهٔ همهٔ نمادها ساخته می‌شود (قیمت باز/بسته/کف/سقف، حجم، ارزش).
  ۲) بازدهٔ هر روز با «قیمت پایانی دیروزِ تعدیل‌شده» محاسبه می‌شود تا افزایش
     سرمایه سری قیمت را نشکند.
  ۳) اندیکاتورها و امتیاز مقطعی برای هر روز جداگانه محاسبه می‌شوند (بدون
     نگاه به آینده).
  ۴) سیگنال روز t در بازگشایی روز t+1 اجرا می‌شود؛ فروش زودتر از T+2 ممکن نیست.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .analysis import WEIGHTS, to_frame

# وزن‌ها بدون جریان حقیقی (دادهٔ تاریخی حقیقی/حقوقی برای همهٔ نمادها و روزها
# در دسترس نیست) و نرمال‌شده تا مجموع یک شود.
BT_WEIGHTS = {k: v for k, v in WEIGHTS.items() if k != "real_flow"}
_w = sum(BT_WEIGHTS.values())
BT_WEIGHTS = {k: v / _w for k, v in BT_WEIGHTS.items()}


@dataclass
class BacktestConfig:
    top_n: int = 5
    max_hold: int = 5
    min_hold: int = 2            # T+2
    stop_atr: float = 2.0
    target_atr: float = 2.5
    trail_atr: float = 0.0       # ۰ = بدون حد ضرر متحرک
    capital: float = 1_000_000_000   # ریال
    buy_fee: float = 0.005
    sell_fee: float = 0.010
    min_value: float = 2e9           # میانگین ارزش روزانه (ریال)
    min_score: float = 0.0
    include_rights: bool = False
    include_etf: bool = True
    warmup: int = 60


@dataclass
class Position:
    symbol: str
    shares: float
    entry_price: float
    entry_date: int
    entry_i: int
    cost: float
    stop: float
    target: float
    last_close: float
    atr: float = 0.0
    peak: float = 0.0


# ---------------------------------------------------------------- panel
def build_panel(client, universe: list[dict], days: int = 400) -> pd.DataFrame:
    hist = client.histories([u["ins_code"] for u in universe], days=days)
    frames: list[pd.DataFrame] = []
    for u in universe:
        df = to_frame(hist.get(u["ins_code"], []))
        if df is None or len(df) < 60:
            continue
        frames.append(_symbol_frame(df, u))
    if not frames:
        return pd.DataFrame()
    panel = pd.concat(frames, ignore_index=True)
    panel = panel[panel["close"] > 0].copy()
    return panel


def _symbol_frame(df: pd.DataFrame, u: dict) -> pd.DataFrame:
    close = df["pClosing"].astype(float)
    prev = df["priceYesterday"].astype(float)
    prev = prev.where(prev > 0, close.shift(1))
    raw_prev = close.shift(1)

    factor = (prev / raw_prev).replace([np.inf, -np.inf], np.nan)
    factor = factor.where(factor.between(0.5, 2.0), 1.0).fillna(1.0)

    ret = close / prev - 1.0
    ret = ret.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    # جهش غیرعادی بدون تعدیل اعلام‌شده را خنثی کن
    ret = ret.where(ret.abs() <= 0.2, 0.0)
    adj = (1.0 + ret).cumprod()

    out = pd.DataFrame(
        {
            "date": df["dEven"].astype(int).to_numpy(),
            "symbol": u["symbol"],
            "ins_code": u["ins_code"],
            "market": u["market"],
            "kind": u["kind"],
            "open": df["priceFirst"].astype(float).to_numpy(),
            "high": df["priceMax"].astype(float).to_numpy(),
            "low": df["priceMin"].astype(float).to_numpy(),
            "close": close.to_numpy(),
            "volume": df["qTotTran5J"].astype(float).to_numpy(),
            "value": df["qTotCap"].astype(float).to_numpy(),
            "factor": factor.to_numpy(),
            "adj": adj.to_numpy(),
        }
    )
    out["open"] = out["open"].where(out["open"] > 0, out["close"])
    out["high"] = out["high"].where(out["high"] > 0, out["close"])
    out["low"] = out["low"].where(out["low"] > 0, out["close"])
    return _indicators(out)


def _indicators(f: pd.DataFrame) -> pd.DataFrame:
    adj = f["adj"]
    close = f["close"]
    ratio = close / adj

    ema9 = adj.ewm(span=9, adjust=False).mean()
    ema20 = adj.ewm(span=20, adjust=False).mean()
    ema50 = adj.ewm(span=50, adjust=False).mean()
    macd = adj.ewm(span=12, adjust=False).mean() - adj.ewm(span=26, adjust=False).mean()
    macd_sig = macd.ewm(span=9, adjust=False).mean()

    delta = adj.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)

    tr = pd.concat(
        [f["high"] - f["low"], (f["high"] - close.shift()).abs(), (f["low"] - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()

    high20 = adj.rolling(20).max()
    low20 = adj.rolling(20).min()
    low5 = adj.rolling(5).min()

    f["ret1"] = adj.pct_change() * 100
    f["ret3"] = (adj / adj.shift(3) - 1) * 100
    f["ret5"] = (adj / adj.shift(5) - 1) * 100
    f["ret20"] = (adj / adj.shift(20) - 1) * 100
    f["rsi14"] = (100 - 100 / (1 + rs)).fillna(50.0)
    f["macd_hist"] = macd - macd_sig
    f["atr14"] = atr14
    f["atr_pct"] = atr14 / close * 100
    f["vol_ratio"] = f["volume"] / f["volume"].shift(1).rolling(20).mean()
    f["value_avg20"] = f["value"].rolling(20).mean()
    f["high20"] = high20
    f["dist_high20"] = (adj / high20 - 1) * 100
    f["dist_ema20"] = (adj / ema20 - 1) * 100
    span = (high20 - low20).replace(0, np.nan)
    f["range_pos"] = ((adj - low20) / span * 100).fillna(50.0)
    f["trend_score"] = (
        (adj > ema20).astype(float)
        + (ema20 > ema50).astype(float)
        + (ema9 > ema20).astype(float)
        + (f["macd_hist"] > 0).astype(float)
    ) / 4.0
    # سطوح واقعی (ریالی) برای معامله
    f["low5_raw"] = low5 * ratio
    f["high20_raw"] = high20 * ratio
    return f


def score_panel(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    g = panel.groupby("date", observed=True)
    panel["rs20"] = panel["ret20"] - g["ret20"].transform("median")
    panel["liquidity"] = np.log10(panel["value_avg20"].clip(lower=1.0))

    for key in BT_WEIGHTS:
        panel[f"p_{key}"] = g[key].rank(pct=True)

    base = sum(w * panel[f"p_{k}"] for k, w in BT_WEIGHTS.items()) * 100.0

    pen = np.zeros(len(panel))
    pen += np.where(panel["dist_ema20"] > 10, np.minimum(12, (panel["dist_ema20"] - 10) * 1.2), 0)
    pen += np.where(panel["atr_pct"] > 8, np.minimum(6, (panel["atr_pct"] - 8) * 1.0), 0)
    pen += np.where(panel["value_avg20"] < 2e9, 8.0, 0.0)
    pen += np.where(panel["rsi14"] > 80, 5.0, 0.0)

    panel["score"] = (base.to_numpy() - pen).clip(0, 100)
    return panel


# ------------------------------------------------------------ simulation
@dataclass
class PreparedPanel:
    """پنل مرتب‌شده + نقشهٔ هر روز؛ برای اجرای چند پیکربندی روی یک پنل."""

    dates: np.ndarray
    day_maps: dict


def prepare(panel: pd.DataFrame) -> PreparedPanel:
    panel = panel.sort_values(["date", "symbol"]).reset_index(drop=True)
    return PreparedPanel(
        dates=np.sort(panel["date"].unique()),
        day_maps={d: g.set_index("symbol") for d, g in panel.groupby("date", observed=True)},
    )


def simulate(panel: pd.DataFrame, cfg: BacktestConfig, prepared: PreparedPanel | None = None) -> dict:
    if prepared is None:
        prepared = prepare(panel)
    dates = prepared.dates
    day_maps = prepared.day_maps

    cash = float(cfg.capital)
    positions: dict[str, Position] = {}
    trades: list[dict] = []
    curve: list[dict] = []
    pending: list[str] = []
    equity_prev = cash

    start_i = cfg.warmup
    for i in range(start_i, len(dates)):
        d = int(dates[i])
        day = day_maps.get(d)
        if day is None:
            continue

        # ۱) تعدیل افزایش سرمایه برای پوزیشن‌های باز
        for pos in positions.values():
            if pos.symbol not in day.index:
                continue
            factor = float(day.at[pos.symbol, "factor"])
            if abs(factor - 1) > 0.005:
                pos.shares /= factor
                pos.entry_price *= factor
                pos.stop *= factor
                pos.target *= factor

        # ۲) اجرای سفارش‌های خرید دیروز در بازگشایی امروز
        for sym in pending:
            if sym in positions or sym not in day.index:
                continue
            price = float(day.at[sym, "open"])
            if price <= 0 or float(day.at[sym, "volume"]) <= 0:
                continue
            # صف قفل‌شده (بدون دامنهٔ قیمتی) یعنی امکان خرید واقعی نبوده
            if float(day.at[sym, "high"]) == float(day.at[sym, "low"]):
                continue
            slot = equity_prev / cfg.top_n
            budget = min(slot, cash)
            shares = math.floor(budget / (price * (1 + cfg.buy_fee)))
            if shares <= 0:
                continue
            cost = shares * price * (1 + cfg.buy_fee)
            if cost > cash:
                continue
            cash -= cost
            atr = float(day.at[sym, "atr14"])
            if not math.isfinite(atr) or atr <= 0:
                atr = price * 0.02
            low5 = float(day.at[sym, "low5_raw"])
            if not math.isfinite(low5) or low5 <= 0:
                low5 = price - cfg.stop_atr * atr
            stop = max(low5 * 0.995, price - cfg.stop_atr * atr)
            stop = min(stop, price - 0.8 * atr)
            stop = max(stop, price * 0.85)
            target = price + cfg.target_atr * atr if cfg.target_atr > 0 else float("inf")
            positions[sym] = Position(
                symbol=sym,
                shares=shares,
                entry_price=price,
                entry_date=d,
                entry_i=i,
                cost=cost,
                stop=stop,
                target=target,
                last_close=price,
                atr=atr,
                peak=price,
            )
        pending = []

        # ۳) بررسی خروج
        for sym in list(positions):
            pos = positions[sym]
            if sym not in day.index:
                continue
            close = float(day.at[sym, "close"])
            pos.last_close = close
            holding = i - pos.entry_i
            if holding < cfg.min_hold:
                continue

            exit_price = None
            reason = ""
            o = float(day.at[sym, "open"])
            h = float(day.at[sym, "high"])
            l = float(day.at[sym, "low"])
            if o <= pos.stop:
                exit_price, reason = o, "حد ضرر (گپ)"
            elif l <= pos.stop:
                exit_price, reason = pos.stop, "حد ضرر"
            elif o >= pos.target:
                exit_price, reason = o, "هدف (گپ)"
            elif h >= pos.target:
                exit_price, reason = pos.target, "هدف"
            elif holding >= cfg.max_hold:
                exit_price, reason = close, "پایان مهلت"

            if exit_price is not None and exit_price > 0:
                proceeds = pos.shares * exit_price * (1 - cfg.sell_fee)
                cash += proceeds
                pnl = proceeds - pos.cost
                fees = pos.cost * cfg.buy_fee / (1 + cfg.buy_fee) + pos.shares * exit_price * cfg.sell_fee
                trades.append(
                    {
                        "symbol": sym,
                        "entry_date": pos.entry_date,
                        "exit_date": d,
                        "entry_price": round(pos.entry_price, 2),
                        "exit_price": round(exit_price, 2),
                        "shares": int(pos.shares),
                        "pnl": round(pnl),
                        "fees": round(fees),
                        "ret_pct": round((proceeds / pos.cost - 1) * 100, 2),
                        "reason": reason,
                        "holding_days": holding,
                    }
                )
                del positions[sym]

        # ۳.۵) حد ضرر متحرک — در پایان روز به‌روز می‌شود تا اثر نگاه به آینده نباشد
        if cfg.trail_atr > 0:
            for pos in positions.values():
                if pos.symbol not in day.index:
                    continue
                pos.peak = max(pos.peak, float(day.at[pos.symbol, "high"]), pos.last_close)
                pos.stop = max(pos.stop, pos.peak - cfg.trail_atr * pos.atr)

        # ۴) ارزش پرتفوی در پایان روز
        invested = sum(p.shares * p.last_close for p in positions.values())
        equity = cash + invested
        curve.append({"date": d, "equity": equity, "invested": invested, "cash": cash})
        equity_prev = equity

        # ۵) انتخاب سیگنال برای اجرا در روز بعد
        if i < len(dates) - 1:
            pending = _select(day, positions, cfg)

    return {
        "curve": curve,
        "trades": trades,
        "final_equity": curve[-1]["equity"] if curve else cfg.capital,
    }


def _select(day: pd.DataFrame, positions: dict, cfg: BacktestConfig) -> list[str]:
    """کاندیدهای خرید بر پایهٔ امتیاز همین روز — بدون نگاه به آینده."""
    slots = cfg.top_n - len(positions)
    if slots <= 0:
        return []
    mask = (
        (day["score"] >= cfg.min_score)
        & (day["value_avg20"] >= cfg.min_value)
        & (day["volume"] > 0)
        & day["ret20"].notna()
        & day["atr14"].notna()
    )
    if not cfg.include_rights:
        mask &= day["kind"] != "rights"
    if not cfg.include_etf:
        mask &= day["kind"] != "etf"
    cand = day[mask].drop(index=[s for s in positions], errors="ignore")
    cand = cand.nlargest(slots, "score")
    return [str(s) for s in cand.index]


# --------------------------------------------------------------- metrics
def compute_metrics(result: dict, cfg: BacktestConfig, benchmark: pd.Series) -> dict:
    curve = pd.DataFrame(result["curve"]) if result["curve"] else pd.DataFrame()
    trades = pd.DataFrame(result["trades"]) if result["trades"] else pd.DataFrame()

    if curve.empty:
        return {}

    curve = curve.set_index("date")
    eq = curve["equity"].astype(float)
    rets = eq.pct_change().fillna(0.0)
    total = eq.iloc[-1] / cfg.capital - 1

    n_days = len(eq)
    years = max(n_days / 250.0, 1 / 250.0)
    cagr = (1 + total) ** (1 / years) - 1 if total > -1 else -1.0

    std = float(rets.std())
    sharpe = float(rets.mean() / std * math.sqrt(252)) if std > 0 else 0.0

    running_max = eq.cummax()
    drawdown = eq / running_max - 1
    max_dd = float(drawdown.min())

    bench = benchmark.reindex(eq.index).ffill().bfill()
    bench_values = bench.to_numpy(dtype=float) if bench.notna().any() else None
    bench_total = float(bench_values[-1] / bench_values[0] - 1) if bench_values is not None else 0.0

    if not trades.empty:
        wins = trades[trades["pnl"] > 0]
        losses = trades[trades["pnl"] <= 0]
        gross_win = float(wins["pnl"].sum())
        gross_loss = float(-losses["pnl"].sum())
        win_rate = len(wins) / len(trades)
        avg_win = float(wins["ret_pct"].mean()) if len(wins) else 0.0
        avg_loss = float(losses["ret_pct"].mean()) if len(losses) else 0.0
        profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")
        avg_hold = float(trades["holding_days"].mean())
    else:
        win_rate = avg_win = avg_loss = avg_hold = 0.0
        profit_factor = 0.0

    exposure = float((curve["invested"] / curve["equity"]).mean())
    fees_total = float(trades["fees"].sum()) if "fees" in trades.columns else 0.0

    return {
        "total_return": total,
        "cagr": cagr,
        "sharpe": sharpe,
        "calmar": (cagr / abs(max_dd)) if max_dd < 0 else 0.0,
        "max_drawdown": max_dd,
        "benchmark_return": bench_total,
        "excess_return": total - bench_total,
        "trades": int(len(trades)),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor if math.isfinite(profit_factor) else None,
        "avg_holding_days": avg_hold,
        "exposure": exposure,
        "fees_total": fees_total,
        "fees_pct_of_capital": fees_total / cfg.capital,
        # تقریبی: اگر کارمزدها پرداخت نمی‌شدند
        "gross_return_est": (float(eq.iloc[-1]) + fees_total) / cfg.capital - 1,
        "final_equity": float(eq.iloc[-1]),
        "days": n_days,
    }


def attach_benchmark(result: dict, benchmark: pd.Series, cfg: BacktestConfig) -> None:
    """شاخص کل را هم‌مقیاس با سرمایهٔ اولیه به منحنی پرتفوی اضافه می‌کند."""
    if not result["curve"] or benchmark is None or benchmark.empty:
        return
    curve = pd.DataFrame(result["curve"]).set_index("date")
    bench = benchmark.reindex(curve.index).ffill().bfill()
    if bench.isna().all():
        return
    base = float(bench.iloc[0])
    for row in result["curve"]:
        v = bench.get(row["date"], np.nan)
        row["benchmark"] = float(v) / base * cfg.capital if base and np.isfinite(v) else None


def equity_series(result: dict) -> pd.DataFrame:
    if not result["curve"]:
        return pd.DataFrame(columns=["equity", "benchmark"])
    curve = pd.DataFrame(result["curve"]).set_index("date")
    return curve
