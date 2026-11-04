#!/usr/bin/env python3
"""اسکن روزانه بورس تهران برای نوسان‌گیری کوتاه‌مدت.

مثال:
    python run_scan.py                     # اسکن کامل و ساخت داشبورد
    python run_scan.py --top 60 --open
    python run_scan.py --min-value 1.0     # حداقل ۱ میلیارد تومان ارزش معاملات روزانه
"""

from __future__ import annotations

import argparse
import os
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
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

from tse.analysis import analyze, risk_levels, score_universe, to_frame  # noqa: E402
from tse.client import FetchError, TSEClient  # noqa: E402
from web.dashboard import render  # noqa: E402
from tse.universe import build_universe  # noqa: E402

RIAL_PER_TOMAN = 10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="اسکنر بورس تهران")
    p.add_argument("--top", type=int, default=40, help="تعداد نماد در خروجی")
    p.add_argument("--min-value", type=float, default=2.0,
                   help="حداقل میانگین ارزش معاملات روزانه (میلیارد تومان)")
    p.add_argument("--markets", default="بورس,فرابورس,پایه,کالا",
                   help="بازارهای مجاز، جداشده با کاما")
    p.add_argument("--etf", action=argparse.BooleanOptionalAction, default=True,
                   help="شامل صندوق‌های قابل معامله (پیش‌فرض: بله)")
    p.add_argument("--days", type=int, default=130, help="تعداد روز تاریخچه")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", default="dashboard.html")
    p.add_argument("--json-out", default="data/scan_latest.json")
    p.add_argument("--open", action="store_true", help="بازکردن داشبورد در مرورگر")
    return p.parse_args()


def jalali(d_even: int) -> str:
    try:
        d = datetime.strptime(str(d_even), "%Y%m%d")
        return jdatetime.date.fromgregorian(date=d).strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        return "—"


def append_today(df, u: dict, market_date: int):
    """ردیف امروز در تاریخچه TSETMC نیست؛ از اسنپ‌شات MarketWatch اضافه‌اش می‌کنیم."""
    if market_date <= 0 or df is None or len(df) == 0:
        return df
    if int(df["dEven"].iloc[-1]) >= market_date:
        return df
    if u["volume"] <= 0 or u["price"] <= 0:
        return df
    today = {
        "dEven": market_date,
        "hEven": 999999,
        "pClosing": u["price"],
        "pDrCotVal": u["last_price"] or u["price"],
        "qTotTran5J": u["volume"],
        "qTotCap": u["value"],
        "zTotTran": u["trades"],
        "priceMin": u["price_min"] or u["price"],
        "priceMax": u["price_max"] or u["price"],
        # ستون‌های مشتق‌شده در to_frame
        "close": u["price"],
        "volume": u["volume"],
        "value": u["value"],
    }
    return pd.concat([df, pd.DataFrame([today])], ignore_index=True)


def fetch_real_flow(client: TSEClient, ins_code: str, dates: list[int]) -> dict:
    """جریان پول حقیقی در ۳ روز آخر، نرمال‌شده با ارزش کل معاملات."""
    weights = [1.0, 0.7, 0.4][: len(dates)]
    rows = []
    for d, w in zip(dates, weights):
        row = client.client_type(ins_code, d)
        if row:
            rows.append((w, row))
    if not rows:
        return {"real_flow": 0.0, "net_real_value": 0.0}
    net = 0.0
    total = 0.0
    for w, r in rows:
        buy_i = float(r.get("buy_I_Value") or 0)
        sell_i = float(r.get("sell_I_Value") or 0)
        buy_n = float(r.get("buy_N_Value") or 0)
        sell_n = float(r.get("sell_N_Value") or 0)
        net += w * (buy_i - sell_i)
        total += w * (buy_i + buy_n)
    return {
        "real_flow": (net / total) if total else 0.0,
        "net_real_value": net,
    }


def book_imbalance(levels: list[dict]) -> float:
    buy = sum(float(x.get("qTitMeDem") or 0) for x in levels)
    sell = sum(float(x.get("qTitMeOf") or 0) for x in levels)
    return (buy - sell) / (buy + sell) if (buy + sell) else 0.0


def main() -> int:
    args = parse_args()
    started = datetime.now()
    client = TSEClient(workers=args.workers)
    markets = {m.strip() for m in args.markets.split(",") if m.strip()}
    min_value_rial = args.min_value * 1e9 * RIAL_PER_TOMAN

    print("→ دریافت عکس بازار از TSETMC …", flush=True)
    try:
        overview = client.overview()
        mw_rows = client.market_watch()
    except FetchError as exc:
        print(f"خطا در دریافت داده: {exc}", file=sys.stderr)
        return 1

    universe = [
        u for u in build_universe(mw_rows)
        if u["market"] in markets and (args.etf or not u["is_etf"])
    ]
    print(f"  {len(universe)} نماد سهام/حق تقدم در دامنه")

    print("→ دریافت تاریخچه روزانه …", flush=True)
    hist = client.histories([u["ins_code"] for u in universe], days=args.days)

    market_date = int(overview.get("marketActivityDEven") or 0)
    items: list[dict] = []
    for u in universe:
        df = append_today(to_frame(hist.get(u["ins_code"], [])), u, market_date)
        if df is None:
            continue
        try:
            metrics = analyze(df)
        except (ValueError, IndexError, ZeroDivisionError):
            continue
        metrics.update(
            {
                "ins_code": u["ins_code"],
                "symbol": u["symbol"],
                "name": u["name"],
                "market": u["market"],
                "kind": u["kind"],
                "is_rights": u["is_rights"],
                "is_etf": u["is_etf"],
                "change_pct": u["change_pct"],
                "volume": u["volume"],
                "value": u["value"],
                "trades": u["trades"],
                "limit_high": u["limit_high"],
                "pe": u["pe"],
                "eps": u["eps"],
            }
        )
        metrics["dates"] = [int(x) for x in df["dEven"].tail(3).tolist()]
        metrics["spark_vol"] = [round(float(x), 0) for x in df["volume"].tail(30).tolist()]
        items.append(metrics)

    print(f"  {len(items)} نماد تاریخچه معتبر داشتند")

    candidates = [x for x in items if x["value_avg20"] >= min_value_rial]
    print(f"  {len(candidates)} نماد از فیلتر نقدشوندگی گذشتند")

    # مرحلهٔ اول: امتیاز بدون جریان حقیقی، فقط برای انتخاب کوتاه‌لیست
    for x in items:
        x["real_flow"] = 0.0
        x["net_real_value"] = 0.0
    score_universe(items)
    shortlist = sorted(candidates, key=lambda x: x["score"], reverse=True)[:200]
    print(f"→ دریافت حقیقی/حقوقی برای {len(shortlist)} نماد کوتاه‌لیست …", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(fetch_real_flow, client, x["ins_code"], x["dates"]): x
            for x in shortlist
        }
        for fut, x in futures.items():
            try:
                x.update(fut.result())
            except Exception:  # noqa: BLE001
                x["real_flow"] = 0.0
                x["net_real_value"] = 0.0

    all_scored = score_universe(items)
    ranked = sorted(all_scored, key=lambda x: x["score"], reverse=True)[: args.top]

    print("→ دریافت مظنه برای نمادهای منتخب …", flush=True)

    def enrich(x: dict) -> None:
        x["book_imbalance"] = book_imbalance(client.best_limits(x["ins_code"]))
        x.update(risk_levels(x))
        x["last_date_fa"] = jalali(x["last_date"])

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(enrich, ranked))

    breadth = {
        "up": sum(1 for x in items if x["change_pct"] > 0),
        "down": sum(1 for x in items if x["change_pct"] < 0),
        "flat": sum(1 for x in items if x["change_pct"] == 0),
        "total_value": sum(x["value"] for x in items),
    }

    last_date = max((x["last_date"] for x in items), default=0)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_at_fa": jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
        "market": {
            "index": overview.get("indexLastValue", 0),
            "index_change": overview.get("indexChange", 0),
            "state": overview.get("marketStateTitle", ""),
            "activity_value": overview.get("marketActivityQTotCap", 0),
            "last_date": last_date,
            "last_date_fa": jalali(last_date),
        },
        "breadth": breadth,
        "counts": {
            "universe": len(universe),
            "analyzed": len(items),
            "liquid": len(candidates),
            "shown": len(ranked),
        },
        "rows": [clean_row(x) for x in ranked],
        "all_scores": sorted(
            [
                {
                    "symbol": x["symbol"],
                    "market": x["market"],
                    "score": x["score"],
                    "change_pct": round(x["change_pct"], 2),
                    "value": x["value"],
                }
                for x in all_scored
            ],
            key=lambda r: r["score"],
            reverse=True,
        ),
    }

    json_path = ROOT / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    html_path = Path(args.out)
    if not html_path.is_absolute():
        html_path = output_dir(ROOT) / html_path
    html_path.write_text(render(payload), encoding="utf-8")

    elapsed = (datetime.now() - started).total_seconds()
    print(f"\n✓ داشبورد ساخته شد: {html_path}")
    print(f"  داده: {json_path}")
    print(f"  {len(ranked)} نماد · {elapsed:.1f} ثانیه")
    for x in ranked[:10]:
        print(f"   {x['symbol']:<12} امتیاز {x['score']:>5.1f}  "
              f"تغییر {x['change_pct']:>6.2f}%  {x['market']}")

    if args.open:
        import webbrowser

        webbrowser.open(html_path.as_uri())
    return 0


def clean_row(x: dict) -> dict:
    keep = (
        "symbol", "name", "market", "kind", "is_rights", "is_etf", "setup",
        "close", "last_price",
        "change_pct", "ret1",
        "ret3", "ret5", "ret20", "rsi14", "atr_pct", "vol_ratio", "value_avg20",
        "value", "score", "tags", "real_flow", "net_real_value", "book_imbalance",
        "entry_low", "entry_high", "stop", "target1", "target2", "rr1", "rr2",
        "spark", "spark_vol", "spark_dates", "last_date_fa", "pe", "eps",
        "trend_score", "dist_high20", "range_pos", "dist_ema20", "low20", "high20",
    )
    out = {}
    for k in keep:
        v = x.get(k)
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            v = 0.0
        out[k] = v
    out["spark_dates_fa"] = [jalali(d) for d in x.get("spark_dates", [])]
    return out


if __name__ == "__main__":
    raise SystemExit(main())
