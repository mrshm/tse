"""اندیکاتورهای تکنیکال و امتیازدهی مقطعی برای نوسان‌گیری کوتاه‌مدت."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# سقف بازده روزانه برای خنثی‌کردن اثر افزایش سرمایه/تعدیل (بازده واقعی بازار < ۱۰٪)
DAILY_CLAMP = 0.15


def to_frame(rows: list[dict]) -> pd.DataFrame | None:
    if not rows:
        return None
    df = pd.DataFrame(rows)
    needed = {
        "dEven", "hEven", "pClosing", "pDrCotVal", "qTotTran5J", "qTotCap", "zTotTran",
        "priceMin", "priceMax", "priceFirst", "priceYesterday",
    }
    if not needed.issubset(df.columns):
        return None
    for col in needed - {"dEven", "hEven"}:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["dEven"] = pd.to_numeric(df["dEven"], errors="coerce").fillna(0).astype(int)
    df["hEven"] = pd.to_numeric(df["hEven"], errors="coerce").fillna(0).astype(int)
    df = (
        df.sort_values(["dEven", "hEven"])
        .drop_duplicates("dEven", keep="last")
        .reset_index(drop=True)
    )
    df = df[(df["pClosing"] > 0) & (df["qTotTran5J"] > 0)]
    if len(df) < 30:
        return None
    df["close"] = df["pClosing"]
    df["volume"] = df["qTotTran5J"]
    df["value"] = df["qTotCap"]
    return df.reset_index(drop=True)


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev = df["close"].shift()
    tr = pd.concat(
        [
            df["priceMax"] - df["priceMin"],
            (df["priceMax"] - prev).abs(),
            (df["priceMin"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def _compound_returns(series: pd.Series, window: int) -> float:
    if len(series) <= window:
        return 0.0
    rets = series.pct_change().tail(window)
    # جهش بزرگ‌تر از سقف روزانه تقریباً همیشه تعدیل افزایش سرمایه است، نه بازده واقعی
    rets = rets.where(rets.abs() <= DAILY_CLAMP, 0.0).fillna(0.0)
    return float((1 + rets).prod() - 1)


def _ema(series: pd.Series, span: int) -> float:
    return float(series.ewm(span=span, adjust=False).mean().iloc[-1])


def analyze(df: pd.DataFrame) -> dict:
    close = df["close"]
    volume = df["volume"]
    value = df["value"]
    last = float(close.iloc[-1])

    ema9, ema20, ema50 = _ema(close, 9), _ema(close, 20), _ema(close, 50)
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = float(macd.iloc[-1] - signal.iloc[-1])

    rsi14 = float(rsi(close).iloc[-1])
    atr14 = float(atr(df).iloc[-1])
    atr_pct = atr14 / last * 100 if last else 0.0

    vol_avg20 = float(volume.tail(21).iloc[:-1].mean()) or 1.0
    vol_ratio = float(volume.iloc[-1]) / vol_avg20
    value_avg20 = float(value.tail(20).mean())

    high20 = float(close.tail(20).max())
    high60 = float(close.tail(60).max())
    low20 = float(close.tail(20).min())
    low5 = float(close.tail(5).min())

    trend_parts = [
        last > ema20,
        ema20 > ema50,
        ema9 > ema20,
        macd_hist > 0,
    ]

    dist_high20 = (last / high20 - 1) * 100 if high20 else 0.0
    dist_ema20 = (last / ema20 - 1) * 100 if ema20 else 0.0
    ret1 = _compound_returns(close, 1) * 100
    ret5 = _compound_returns(close, 5) * 100
    ret20 = _compound_returns(close, 20) * 100

    if dist_high20 > -2 and ret1 > 0 and vol_ratio >= 1.0:
        setup = "شکست سقف"
    elif ret5 < 2 and ret20 > 5 and -2 <= dist_ema20 <= 8:
        setup = "پولبک"
    else:
        setup = "ادامه روند"

    return {
        "last_date": int(df["dEven"].iloc[-1]),
        "setup": setup,
        "close": last,
        "last_price": float(df["pDrCotVal"].iloc[-1]) or last,
        "ret1": ret1,
        "ret3": _compound_returns(close, 3) * 100,
        "ret5": ret5,
        "ret20": ret20,
        "ema9": ema9,
        "ema20": ema20,
        "ema50": ema50,
        "dist_ema20": dist_ema20,
        "macd_hist": macd_hist,
        "rsi14": rsi14,
        "atr14": atr14,
        "atr_pct": atr_pct,
        "vol_ratio": vol_ratio,
        "vol_avg20": vol_avg20,
        "value_avg20": value_avg20,
        "high20": high20,
        "high60": high60,
        "low20": low20,
        "low5": low5,
        "dist_high20": dist_high20,
        "range_pos": ((last - low20) / (high20 - low20) * 100) if high20 > low20 else 50.0,
        "trend_score": sum(bool(x) for x in trend_parts) / len(trend_parts),
        "spark": [round(float(x), 2) for x in close.tail(30).tolist()],
        "spark_dates": [int(x) for x in df["dEven"].tail(30).tolist()],
    }


def _pct_rank(values: list[float]) -> list[float]:
    if not values:
        return []
    s = pd.Series(values, dtype="float64")
    ranks = s.rank(pct=True, method="average").fillna(0.5)
    return [float(x) for x in ranks.tolist()]


WEIGHTS = {
    "ret5": 0.16,
    "ret3": 0.09,
    "ret20": 0.07,
    "vol_ratio": 0.16,
    "trend_score": 0.15,
    "range_pos": 0.08,
    "liquidity": 0.09,
    "rs20": 0.06,
    "real_flow": 0.14,
}


def score_universe(items: list[dict]) -> list[dict]:
    """امتیاز ۰..۱۰۰ بر پایه رتبه‌ی مقطعی هر متریک در کل بازار."""
    if not items:
        return items

    med_ret20 = float(np.median([x["ret20"] for x in items]))
    for x in items:
        x["rs20"] = x["ret20"] - med_ret20
        x["liquidity"] = math.log10(max(x["value_avg20"], 1.0))
        # اگر داده حقیقی/حقوقی نداریم، نگاه خنثی
        x.setdefault("real_flow", 0.0)

    ranks = {
        key: _pct_rank([x[key] for x in items])
        for key in ("ret5", "ret3", "ret20", "vol_ratio", "trend_score",
                    "range_pos", "liquidity", "rs20", "real_flow")
    }

    for i, x in enumerate(items):
        base = sum(WEIGHTS[k] * ranks[k][i] for k in WEIGHTS) * 100

        penalty = 0.0
        if x["dist_ema20"] > 10:
            penalty += min(12.0, (x["dist_ema20"] - 10) * 1.2)
        if x["atr_pct"] > 8:
            penalty += min(6.0, (x["atr_pct"] - 8) * 1.0)
        if x["value_avg20"] < 2e9:  # کمتر از ۲۰۰ میلیون تومان
            penalty += 8.0
        if x["rsi14"] > 80:
            penalty += 5.0

        x["score"] = round(max(0.0, min(100.0, base - penalty)), 1)
        x["base_score"] = round(base, 1)
        x["penalty"] = round(penalty, 1)
        x["tags"] = _tags(x)

    return items


def _tags(x: dict) -> list[str]:
    tags: list[str] = []
    if x["dist_high20"] > -1.5 and x["ret5"] > 0:
        tags.append("شکست سقف ۲۰ روزه")
    if x["vol_ratio"] >= 2:
        tags.append("حجم ۲ برابر میانگین")
    elif x["vol_ratio"] >= 1.4:
        tags.append("حجم بالاتر از میانگین")
    if x["trend_score"] == 1.0:
        tags.append("روند صعودی کامل")
    if x["real_flow"] > 0.15:
        tags.append("ورود پول حقیقی")
    elif x["real_flow"] < -0.15:
        tags.append("خروج پول حقیقی")
    if x["rsi14"] > 75:
        tags.append("اشباع خرید")
    elif x["rsi14"] < 35:
        tags.append("اشباع فروش")
    if x["dist_ema20"] > 10:
        tags.append("فاصله زیاد از میانگین")
    if x["value_avg20"] < 2e9:
        tags.append("نقدشوندگی کم")
    return tags


def risk_levels(x: dict) -> dict:
    """محدوده ورود، حد ضرر و اهداف بر پایه ATR."""
    price = float(x["close"])
    atr14 = float(x["atr14"])
    if not math.isfinite(atr14) or atr14 <= 0:
        atr14 = price * 0.02
    ema9 = float(x["ema9"]) if math.isfinite(float(x["ema9"])) else price
    low5 = float(x.get("low5") or 0)
    if not math.isfinite(low5):
        low5 = 0.0

    entry_low = min(price, max(ema9, price - 0.6 * atr14))
    # حد ضرر: نزدیک‌ترین کف معتبر (کف ۵ روزه یا ۲ ATR زیر قیمت)، ولی نه چسبیده به قیمت
    stop = max(low5 * 0.995 if low5 > 0 else price - 2 * atr14, price - 2.0 * atr14)
    stop = min(stop, price - 0.8 * atr14)
    stop = max(stop, price * 0.85)  # حداکثر ۱۵٪ ریسک
    target1 = price + 2.5 * atr14
    target2 = price + 4.0 * atr14
    risk = max(price - stop, price * 0.01)
    return {
        "entry_low": round(entry_low),
        "entry_high": round(price),
        "stop": round(stop),
        "target1": round(target1),
        "target2": round(target2),
        "rr1": round((target1 - price) / risk, 1),
        "rr2": round((target2 - price) / risk, 1),
    }
