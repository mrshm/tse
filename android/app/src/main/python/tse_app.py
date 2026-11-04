"""پل پایتون برای اپ اندروید.

لایهٔ جاوا فقط سه کار می‌کند: فراخوانی `run_sync`، خواندن فایل وضعیت، و نمایش
گزارش. همهٔ منطق همان کدهای دسکتاپ است که داخل APK اجرا می‌شوند.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
import traceback
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

STATUS_PATH = os.path.join(_HERE, "status.json")

STEPS = [
    ("scan", "اسکن بازار", "run_scan", []),
    ("plan", "برگهٔ سفارش", "run_plan", []),
    ("journal", "وضعیت دفتر", "run_journal", ["status"]),
    ("risk", "تحلیل ریسک", "run_risk", []),
]

FULL_STEPS = STEPS + [
    ("backtest", "بک‌تست", "run_backtest", []),
    ("walkforward", "اعتبارسنجی راه‌رونده", "run_walkforward", []),
]

_status = {
    "running": False,
    "done": False,
    "error": None,
    "step": "",
    "pct": 0,
    "log": [],
    "updated_at": "",
}


def set_home(path: str) -> None:
    """پوشهٔ قابل‌نوشتن اپ را به کدهای پایتون معرفی می‌کند."""
    os.environ["TSE_HOME"] = path
    os.environ["TSE_APP"] = "1"
    os.makedirs(path, exist_ok=True)


def set_status_path(path: str) -> None:
    global STATUS_PATH
    STATUS_PATH = path


def _save() -> None:
    _status["updated_at"] = datetime.now().strftime("%H:%M:%S")
    try:
        tmp = STATUS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(_status, fh, ensure_ascii=False)
        os.replace(tmp, STATUS_PATH)
    except OSError:
        pass


def status_json() -> str:
    return json.dumps(_status, ensure_ascii=False)


def _run_script(module_name: str, argv: list[str]) -> int:
    mod = importlib.import_module(module_name)
    old = sys.argv
    sys.argv = [module_name + ".py"] + list(argv)
    try:
        rc = mod.main()
        return 0 if rc is None else int(rc)
    finally:
        sys.argv = old


def run_sync(mode: str = "quick") -> str:
    steps = FULL_STEPS if mode == "full" else STEPS
    _status.update(running=True, done=False, error=None, step="آماده‌سازی", pct=0, log=[])
    _save()
    started = time.time()
    try:
        for i, (key, label, module, argv) in enumerate(steps):
            _status.update(step=label, pct=int(100 * i / len(steps)))
            _save()
            t0 = time.time()
            rc = _run_script(module, argv)
            _status["log"].append(
                {"step": key, "rc": rc, "secs": round(time.time() - t0, 1)}
            )
            if rc != 0:
                raise RuntimeError(f"{label} با کد خطای {rc} تمام شد")
        _status.update(step="انجام شد", pct=100, done=True)
        return "ok"
    except Exception:  # noqa: BLE001 - هر خطایی باید به کاربر نشان داده شود
        _status.update(
            error=traceback.format_exc(limit=6).strip().splitlines()[-1],
            step="خطا",
        )
        return "error"
    finally:
        _status["running"] = False
        _status["secs"] = round(time.time() - started, 1)
        _save()


def version() -> str:
    try:
        import tse

        return tse.__version__
    except Exception:  # noqa: BLE001
        return "?"
