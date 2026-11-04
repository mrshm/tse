#!/usr/bin/env python3
"""صفحهٔ یکپارچه: یک HTML با همهٔ ابزارها در یک جا.

مثال:
    python run_home.py            # ساخت index.html از آخرین خروجی‌ها
    python run_home.py --open     # و بازکردن آن در مرورگر
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

from web.home import render_home  # noqa: E402
from tse.journal import load as load_journal  # noqa: E402
from tse.journal import stats as journal_stats  # noqa: E402

# key, label, فایل گزارش، دستور ساخت
REPORTS = [
    ("today", "امروز", None, ""),
    ("scan", "اسکن", "dashboard.html", "./tse.sh scan"),
    ("plan", "برگهٔ سفارش", "plan.html", "./tse.sh plan"),
    ("journal", "دفتر", None, ""),
    ("risk", "ریسک", "risk.html", "./tse.sh risk"),
    ("backtest", "بک‌تست", "backtest.html", "./tse.sh backtest"),
    ("walkforward", "راه‌رونده", "walkforward.html", "./tse.sh walkforward"),
    ("sweep", "جست‌وجو", "sweep.html", "./tse.sh sweep"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="صفحهٔ یکپارچهٔ ابزارهای بورس")
    p.add_argument("--out", default="index.html")
    p.add_argument("--journal", default="data/journal.json")
    p.add_argument("--no-rebuild", action="store_true",
                   help="گزارش‌های HTML را از JSON دوباره نساز")
    p.add_argument("--open", action="store_true")
    return p.parse_args()


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# (json، html، ماژول، تابع) — گزارش‌ها از دادهٔ ذخیره‌شده دوباره ساخته می‌شوند
REBUILD = [
    ("data/scan_latest.json", "dashboard.html", "web.dashboard", "render"),
    ("data/plan_latest.json", "plan.html", "web.plan_report", "render_plan"),
    ("data/risk_latest.json", "risk.html", "web.risk_report", "render_risk"),
    ("data/backtest_latest.json", "backtest.html", "web.report", "render_report"),
    ("data/sweep_latest.json", "sweep.html", "web.sweep_report", "render_sweep"),
    ("data/walkforward_latest.json", "walkforward.html", "web.wf_report", "render_walkforward"),
]


def rebuild_reports() -> tuple[int, list[str]]:
    """گزارش‌های HTML را از JSONهای ذخیره‌شده دوباره می‌سازد (بدون شبکه).

    لازم است تا حالت «داخل صفحه» (embed) در همهٔ گزارش‌ها اعمال شود.
    """
    import importlib

    ok, failed = 0, []
    for json_rel, html_rel, mod_name, fn_name in REBUILD:
        data = read_json(ROOT / json_rel)
        if data is None:
            continue
        try:
            mod = importlib.import_module(mod_name)
            html = getattr(mod, fn_name)(data)
            (output_dir(ROOT) / html_rel).write_text(html, encoding="utf-8")
            ok += 1
        except Exception as exc:  # noqa: BLE001 - یک گزارش خراب نباید کل صفحه را ببرد
            failed.append(f"{html_rel}: {exc}")
    return ok, failed


def enrich_positions(journal: dict, today_iso: str) -> list[dict]:
    """وضعیت هر پوزیشن را از آخرین قیمت ذخیره‌شده حساب می‌کند."""
    out = []
    for p in journal.get("positions", []):
        rec = dict(p)
        ltp = rec.get("ltp")
        state = "ok"
        if ltp and rec.get("stop") and ltp <= rec["stop"]:
            state = "stop"
        elif ltp and rec.get("target") and ltp >= rec["target"]:
            state = "target"
        elif rec.get("planned_exit_iso") and today_iso >= rec["planned_exit_iso"]:
            state = "expired"
        rec["state"] = state
        out.append(rec)
    return out


def build_payload(journal_path: Path) -> dict:
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d")
    data_dir = ROOT / "data"

    scan = read_json(data_dir / "scan_latest.json")
    plan = read_json(data_dir / "plan_latest.json")
    risk = read_json(data_dir / "risk_latest.json")

    journal = load_journal(journal_path)
    positions = enrich_positions(journal, today_iso)
    jstats = journal_stats({"positions": positions, "closed": journal.get("closed", [])})

    alerts = []
    labels = {"stop": "حد ضرر لمس شد", "target": "هدف رسید", "expired": "مهلت تمام شد"}
    for p in positions:
        if p["state"] in labels:
            alerts.append({"symbol": p["symbol"], "kind": p["state"], "text": labels[p["state"]]})

    plan_stale = False
    if plan:
        src = str(plan.get("source_date") or "")[:10]
        plan_stale = bool(plan.get("stale")) or (src and src != today_iso)

    risk_slim = None
    if risk:
        c, s = risk.get("config", {}), risk.get("summary", {})
        risk_slim = {
            "p_ruin": s.get("p_ruin"),
            "p_profit": s.get("p_profit"),
            "median_final": s.get("median_final"),
            "p05_final": s.get("p05_final"),
            "ruin_pct": c.get("ruin_pct"),
            "risk_pct": c.get("risk_pct"),
            "sims": c.get("sims"),
            "trades": c.get("trades"),
            "source": risk.get("source"),
            "generated_at_fa": risk.get("generated_at_fa"),
        }

    reports = []
    for key, label, fname, cmd in REPORTS:
        reports.append({
            "key": key,
            "label": label,
            "file": fname,
            "cmd": cmd,
            "exists": bool(fname) and (output_dir(ROOT) / fname).exists(),
        })

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "generated_at_fa": jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
        "market": (scan or {}).get("market"),
        "breadth": (scan or {}).get("breadth"),
        "counts": (scan or {}).get("counts"),
        "scan_at_fa": (scan or {}).get("generated_at_fa"),
        "plan": plan,
        "plan_stale": plan_stale,
        "journal": {
            "positions": positions,
            "closed": journal.get("closed", []),
            "stats": jstats,
        },
        "alerts": alerts,
        "risk": risk_slim,
        "reports": reports,
    }


def main() -> int:
    args = parse_args()
    jp = Path(args.journal)
    jp = jp if jp.is_absolute() else ROOT / jp

    payload = build_payload(jp)
    built, failed = (0, []) if args.no_rebuild else rebuild_reports()
    out = Path(args.out)
    out = out if out.is_absolute() else output_dir(ROOT) / out
    out.write_text(render_home(payload), encoding="utf-8")

    m = payload["market"] or {}
    plan = payload["plan"]
    j = payload["journal"]["stats"]
    r = payload["risk"] or {}

    print("\n" + "─" * 72)
    print(f"  صفحهٔ یکپارچه · {payload['generated_at_fa']}")
    print("─" * 72)
    if m:
        chg = m.get("index_change") or 0
        prev = (m.get("index") or 0) - chg
        pct = chg / prev * 100 if prev else 0
        print(f"  شاخص: {m.get('index', 0):,.0f} ({pct:+.2f}%)")
    else:
        print("  شاخص: داده‌ای نیست (اسکن را اجرا کنید)")
    if plan:
        s = plan.get("summary", {})
        warn = " ⚠ دادهٔ قدیمی" if payload["plan_stale"] else ""
        print(f"  برگه: {len(plan.get('orders', []))} سهم · "
              f"{s.get('invested', 0) / 1e6:,.1f} م.ت · "
              f"خروج {plan.get('exit_date_fa', '—')}{warn}")
    else:
        print("  برگه: ساخته نشده")
    print(f"  دفتر: {j['open']} باز · {j['closed']} بسته · "
          f"{len(payload['alerts'])} نیاز به اقدام")
    if r:
        print(f"  ریسک: احتمال ورشکستگی {r['p_ruin'] * 100:.1f}% · "
              f"احتمال سود {r['p_profit'] * 100:.1f}%")
    missing = [x["label"] for x in payload["reports"] if not x["exists"] and x["file"]]
    if missing:
        print(f"  گزارش‌های ساخته‌نشده: {'، '.join(missing)}")
    if built:
        print(f"  گزارش‌ها از JSON دوباره ساخته شد: {built}")
    for f in failed:
        print(f"  ⚠ {f}")
    print("─" * 72)
    print(f"✓ صفحه: {out}")

    if args.open:
        import webbrowser

        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
