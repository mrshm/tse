"""ساخت برگهٔ سفارش روزانه از خروجی اسکنر.

ورودی: ردیف‌های `data/scan_latest.json` (قیمت‌ها به ریال).
خروجی: برای هر نماد — تعداد سهم، قیمت خرید، حد ضرر، هدف، مبلغ، و تاریخ تقریبی خروج.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import jdatetime

RIAL_PER_TOMAN = 10


@dataclass
class PlanConfig:
    capital_toman: float = 100_000_000      # کل سرمایه به تومان (۱۰۰ میلیون)
    positions: int = 5                     # چند سهم هم‌زمان
    risk_pct: float = 1.0                  # درصد سرمایه که در هر معامله ریسک می‌شود
    hold_days: int = 20                    # روز معاملاتی تا خروج زمانی
    target_atr: float = 2.5                # هدف = قیمت + n×ATR (۰ = بدون هدف)
    stop_atr: float = 0.0                  # ۰ = از حد ضرر اسکنر استفاده کن
    max_adv_pct: float = 1.0               # سقف سهم از میانگین ارزش معاملات روزانه
    min_score: float = 0.0
    min_rr: float = 1.0                    # حداقل نسبت بازده/ریسک برای پذیرش
    include_etf: bool = True


def _trading_days_later(start: jdatetime.date, n: int) -> jdatetime.date:
    """n روز معاملاتی بعد (شنبه–چهارشنبه). تعطیلات رسمی لحاظ نشده است."""
    d = start
    left = n
    while left > 0:
        d += jdatetime.timedelta(days=1)
        if d.weekday() not in (5, 6):  # پنجشنبه و جمعه
            left -= 1
    return d


def build_plan(rows: list[dict], cfg: PlanConfig, as_of: jdatetime.date | None = None) -> dict:
    as_of = as_of or jdatetime.date.today()
    capital = float(cfg.capital_toman)             # تومان
    risk_budget = capital * cfg.risk_pct / 100.0
    slot = capital / max(cfg.positions, 1)

    exit_date = _trading_days_later(as_of, cfg.hold_days)
    orders: list[dict] = []
    skipped: list[dict] = []
    cash = capital

    for r in rows:
        if len(orders) >= cfg.positions:
            break
        try:
            entry = float(r["entry_high"]) / RIAL_PER_TOMAN      # تومان
            entry_low = float(r.get("entry_low") or entry) / RIAL_PER_TOMAN
            stop = float(r.get("stop") or 0) / RIAL_PER_TOMAN
            atr = entry * float(r.get("atr_pct") or 0) / 100.0
            score = float(r.get("score") or 0)
        except (TypeError, ValueError, KeyError):
            continue

        if score < cfg.min_score:
            continue
        if r.get("is_etf") and not cfg.include_etf:
            continue
        if entry <= 0 or atr <= 0:
            skipped.append({"symbol": r.get("symbol"), "why": "دادهٔ ناکافی"})
            continue

        if cfg.stop_atr > 0:
            stop = entry - cfg.stop_atr * atr
        if stop <= 0 or stop >= entry:
            skipped.append({"symbol": r.get("symbol"), "why": "حد ضرر نامعتبر"})
            continue

        target = entry + cfg.target_atr * atr if cfg.target_atr > 0 else None
        risk_per_share = entry - stop
        reward_per_share = (target - entry) if target else 0.0
        rr = reward_per_share / risk_per_share if risk_per_share else 0.0
        if target and rr < cfg.min_rr:
            skipped.append({"symbol": r.get("symbol"), "why": f"نسبت بازده/ریسک {rr:.1f} < {cfg.min_rr}"})
            continue

        qty_risk = risk_budget / risk_per_share
        qty_slot = slot / entry
        adv = float(r.get("value_avg20") or 0) / RIAL_PER_TOMAN
        qty_adv = (adv * cfg.max_adv_pct / 100.0) / entry if adv > 0 else qty_slot
        qty = int(math.floor(min(qty_risk, qty_slot, qty_adv)))
        if qty < 1:
            skipped.append({"symbol": r.get("symbol"), "why": "سرمایه برای یک سهم کافی نیست"})
            continue

        cost = qty * entry
        if cost > cash:
            qty = int(math.floor(cash / entry))
            cost = qty * entry
            if qty < 1:
                skipped.append({"symbol": r.get("symbol"), "why": "نقدینگی تمام شد"})
                continue

        cash -= cost
        loss_at_stop = qty * (entry - stop)
        orders.append(
            {
                "symbol": r.get("symbol"),
                "name": r.get("name") or "",
                "market": r.get("market") or "",
                "is_etf": bool(r.get("is_etf")),
                "score": round(score, 1),
                "setup": r.get("setup") or "",
                "qty": qty,
                "entry": round(entry),
                "entry_low": round(entry_low),
                "stop": round(stop),
                "target": round(target) if target else None,
                "cost": round(cost),
                "risk": round(loss_at_stop),
                "risk_pct": round(loss_at_stop / capital * 100, 2),
                "target_ret_pct": round((target / entry - 1) * 100, 1) if target else None,
                "rr": round(rr, 1) if target else None,
                "hold_days": cfg.hold_days,
                "exit_date_fa": exit_date.strftime("%Y/%m/%d"),
                "planned_exit_iso": exit_date.togregorian().strftime("%Y-%m-%d"),
                "value_avg20": round(adv),
                "rsi14": round(float(r.get("rsi14") or 0), 0),
                "atr_pct": round(float(r.get("atr_pct") or 0), 1),
            }
        )

    invested = sum(o["cost"] for o in orders)
    return {
        "as_of_fa": as_of.strftime("%Y/%m/%d"),
        "exit_date_fa": exit_date.strftime("%Y/%m/%d"),
        "config": {
            "capital_toman": cfg.capital_toman,
            "positions": cfg.positions,
            "risk_pct": cfg.risk_pct,
            "hold_days": cfg.hold_days,
            "target_atr": cfg.target_atr,
            "stop_atr": cfg.stop_atr,
            "min_score": cfg.min_score,
            "min_rr": cfg.min_rr,
        },
        "summary": {
            "count": len(orders),
            "invested": round(invested),
            "cash": round(cash),
            "risk_total": round(sum(o["risk"] for o in orders)),
            "risk_total_pct": round(sum(o["risk"] for o in orders) / capital * 100, 2),
            "capital_toman": cfg.capital_toman,
        },
        "orders": orders,
        "skipped": skipped[:10],
    }
