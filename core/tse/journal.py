"""دفتر معاملات: پیگیری سفارش‌های برگه تا بسته‌شدن.

هر معامله با تعداد، قیمت ورود، حد ضرر، هدف و تاریخ خروجِ برنامه‌ریزی‌شده ثبت
می‌شود. وضعیت هر روز با قیمت بازار به‌روز می‌شود و در پایان، سود/زیان واقعی
(بعد از کارمزد) با بک‌تست مقایسه می‌شود.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import jdatetime

RIAL_PER_TOMAN = 10
BUY_FEE = 0.0045
SELL_FEE = 0.0095


# ------------------------------------------------------------------ storage
def empty() -> dict:
    return {"positions": [], "closed": [], "created_at": datetime.now().isoformat(timespec="seconds")}


def load(path: Path) -> dict:
    if not path.exists():
        return empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty()
    data.setdefault("positions", [])
    data.setdefault("closed", [])
    return data


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ actions
def open_from_plan(journal: dict, plan: dict) -> tuple[list[str], list[str]]:
    """سفارش‌های برگه را به‌عنوان پوزیشن باز ثبت می‌کند. (افزوده‌شده، رد‌شده)"""
    today = datetime.now()
    today_iso = today.strftime("%Y-%m-%d")
    today_fa = jdatetime.date.fromgregorian(date=today).strftime("%Y/%m/%d")
    open_syms = {p["symbol"] for p in journal["positions"]}
    added, skipped = [], []

    for o in plan.get("orders", []):
        sym = str(o.get("symbol") or "")
        if not sym:
            continue
        if sym in open_syms:
            skipped.append(f"{sym} (از قبل باز است)")
            continue
        qty = int(o.get("qty") or 0)
        entry = float(o.get("entry") or 0)
        if qty <= 0 or entry <= 0:
            skipped.append(f"{sym} (تعداد یا قیمت نامعتبر)")
            continue

        cost = qty * entry
        journal["positions"].append(
            {
                "id": f"{sym}-{today_iso}",
                "symbol": sym,
                "name": o.get("name") or "",
                "qty": qty,
                "entry": round(entry, 2),
                "stop": round(float(o.get("stop") or 0), 2),
                "target": round(float(o["target"]), 2) if o.get("target") else None,
                "cost": round(cost),
                "fees_buy": round(cost * BUY_FEE),
                "opened_iso": today_iso,
                "opened_fa": today_fa,
                "planned_exit_iso": o.get("planned_exit_iso") or "",
                "planned_exit_fa": o.get("exit_date_fa") or plan.get("exit_date_fa") or "",
                "status": "open",
                "note": "",
            }
        )
        open_syms.add(sym)
        added.append(sym)
    return added, skipped


def mark_to_market(journal: dict, quotes: dict[str, float], today: datetime | None = None) -> list[dict]:
    """قیمت‌های لحظه‌ای را روی پوزیشن‌های باز می‌گذارد و وضعیت را برمی‌گرداند."""
    today = today or datetime.now()
    today_iso = today.strftime("%Y-%m-%d")
    out = []
    for p in journal["positions"]:
        ltp = quotes.get(p["symbol"])
        row = dict(p)
        row["ltp"] = round(ltp, 2) if ltp else None
        if ltp and ltp > 0:
            value = p["qty"] * ltp
            net = value * (1 - SELL_FEE) - p["cost"] - p["fees_buy"]
            row["value"] = round(value)
            row["pnl"] = round(net)
            row["pnl_pct"] = round(net / (p["cost"] + p["fees_buy"]) * 100, 2)
            row["dist_stop_pct"] = round((ltp - p["stop"]) / ltp * 100, 2) if p["stop"] else None
            row["dist_target_pct"] = round((p["target"] - ltp) / ltp * 100, 2) if p["target"] else None
        else:
            row.update({"value": None, "pnl": None, "pnl_pct": None,
                        "dist_stop_pct": None, "dist_target_pct": None})

        flags = []
        if ltp and p["stop"] and ltp <= p["stop"]:
            flags.append("stop")
        if ltp and p["target"] and ltp >= p["target"]:
            flags.append("target")
        if p.get("planned_exit_iso") and today_iso >= p["planned_exit_iso"]:
            flags.append("expired")
        row["flags"] = flags
        out.append(row)
    return out


def close_position(journal: dict, symbol: str, price: float, reason: str = "دستی") -> dict | None:
    """پوزیشن باز نماد را با قیمت داده‌شده می‌بندد و به بخش بسته‌شده‌ها منتقل می‌کند."""
    today = datetime.now()
    for i, p in enumerate(journal["positions"]):
        if p["symbol"] != symbol:
            continue
        proceeds = p["qty"] * price * (1 - SELL_FEE)
        net = proceeds - p["cost"] - p["fees_buy"]
        entry_dt = datetime.strptime(p["opened_iso"], "%Y-%m-%d")
        holding = (today - entry_dt).days
        rec = dict(p)
        rec.update(
            {
                "status": "closed",
                "exit": round(price, 2),
                "exit_iso": today.strftime("%Y-%m-%d"),
                "exit_fa": jdatetime.date.fromgregorian(date=today).strftime("%Y/%m/%d"),
                "proceeds": round(proceeds),
                "fees_sell": round(p["qty"] * price * SELL_FEE),
                "pnl": round(net),
                "pnl_pct": round(net / (p["cost"] + p["fees_buy"]) * 100, 2),
                "reason": reason,
                "holding_days": holding,
            }
        )
        journal["positions"].pop(i)
        journal["closed"].append(rec)
        return rec
    return None


def stats(journal: dict) -> dict:
    closed = journal["closed"]
    open_pos = journal["positions"]
    n = len(closed)
    wins = [c for c in closed if c.get("pnl", 0) > 0]
    losses = [c for c in closed if c.get("pnl", 0) <= 0]
    gross_win = sum(c["pnl"] for c in wins)
    gross_loss = -sum(c["pnl"] for c in losses)
    pnl = sum(c.get("pnl", 0) for c in closed)
    fees = sum(c.get("fees_buy", 0) + c.get("fees_sell", 0) for c in closed)
    cost = sum(c.get("cost", 0) for c in closed)

    return {
        "closed": n,
        "open": len(open_pos),
        "invested_open": sum(p["qty"] * p["entry"] for p in open_pos),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / n if n else 0.0,
        "avg_win_pct": (sum(c["pnl_pct"] for c in wins) / len(wins)) if wins else 0.0,
        "avg_loss_pct": (sum(c["pnl_pct"] for c in losses) / len(losses)) if losses else 0.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
        "pnl": pnl,
        "pnl_pct_of_cost": pnl / cost * 100 if cost else 0.0,
        "fees": fees,
        "fees_pct_of_cost": fees / cost * 100 if cost else 0.0,
        "avg_holding_days": (sum(c.get("holding_days", 0) for c in closed) / n) if n else 0.0,
        "best": max(closed, key=lambda c: c.get("pnl", 0)) if closed else None,
        "worst": min(closed, key=lambda c: c.get("pnl", 0)) if closed else None,
    }


def quotes_from_market_watch(rows: list[dict]) -> dict[str, float]:
    """نماد → آخرین قیمت به تومان."""
    out: dict[str, float] = {}
    for r in rows:
        sym = str(r.get("lva") or "").strip()
        if not sym:
            continue
        price = float(r.get("pdv") or r.get("pClosing") or 0)
        if price <= 0:
            continue
        out[sym] = price / RIAL_PER_TOMAN
    return out
