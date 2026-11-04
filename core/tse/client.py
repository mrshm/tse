"""دسترسی به داده‌های TSETMC با کش روی دیسک.

منابع:
  - GetMarketWatch          : عکس لحظه‌ای کل بازار
  - GetMarketOverview       : شاخص کل و وضعیت بازار
  - GetClosingPriceDailyList: تاریخچه روزانه هر نماد
  - GetClientTypeHistory    : خرید/فروش حقیقی و حقوقی
  - BestLimits              : بهترین سفارش‌های خرید/فروش (۵ مظنه)
"""

from __future__ import annotations

import json
import random
import ssl
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

from . import data_dir, project_root


def _ssl_context() -> ssl.SSLContext:
    # روی اندروید مخزن گواهی سیستم در دسترس نیست، پس اگر certifi نصب باشد از آن
    # استفاده می‌کنیم و در غیر این صورت به مخزن پیش‌فرض پایتون تکیه می‌کنیم.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 - هر خطایی یعنی برگرد به پیش‌فرض
        return ssl.create_default_context()


ROOT = project_root(Path(__file__).resolve().parents[2])
CACHE = data_dir(ROOT) / "cache"
HIST_CACHE = CACHE / "hist"
CT_CACHE = CACHE / "ct"
for _d in (CACHE, HIST_CACHE, CT_CACHE):
    _d.mkdir(parents=True, exist_ok=True)

BASE = "https://cdn.tsetmc.com/api"
TEDPIX_CODE = "32097828799138957"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tsetmc.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}


class FetchError(RuntimeError):
    pass


class TSEClient:
    def __init__(self, workers: int = 8, timeout: int = 25, ttl: int = 300):
        self.workers = workers
        self.timeout = timeout
        self.ttl = ttl
        self._local = threading.local()
        self._batch_lock = threading.Lock()
        self._ssl = _ssl_context()

    # ------------------------------------------------------------------ http
    def _get(self, path: str, retries: int = 3, timeout: float | None = None) -> dict:
        url = f"{BASE}/{path}"
        last = "unknown"
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(
                    req, timeout=timeout or self.timeout, context=self._ssl
                ) as resp:
                    text = resp.read().decode("utf-8", "replace").strip()
                if not text:
                    return {}
                if text[0] == "<":
                    raise ValueError("blocked: HTML instead of JSON")
                return json.loads(text)
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code}"
                if exc.code == 404:
                    break
            except Exception as exc:  # noqa: BLE001 - retry any transport error
                last = str(exc)
            time.sleep(0.2 * (2**attempt) + random.random() * 0.15)
        raise FetchError(f"{path} → {last}")

    # ----------------------------------------------------------------- cache
    @staticmethod
    def _read_cache(path: Path, ttl: int) -> dict | None:
        try:
            if time.time() - path.stat().st_mtime > ttl:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write_cache(path: Path, payload: dict) -> None:
        tmp = path.with_suffix(path.suffix + f".{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    # ------------------------------------------------------------- endpoints
    def market_watch(self) -> list[dict]:
        path = CACHE / f"marketwatch_{date.today():%Y%m%d}.json"
        cached = self._read_cache(path, ttl=min(self.ttl, 120))
        if cached is not None:
            return cached["marketwatch"]
        data = self._get(
            "ClosingPrice/GetMarketWatch?market=0&paperTypes%5B0%5D=1"
            "&showTraded=false&withBestLimits=false&hEven=0&RefId=0"
        )
        rows = data.get("marketwatch", [])
        self._write_cache(path, {"marketwatch": rows})
        return rows

    def overview(self) -> dict:
        path = CACHE / f"overview_{date.today():%Y%m%d}.json"
        cached = self._read_cache(path, ttl=min(self.ttl, 120))
        if cached is not None:
            return cached["marketOverview"]
        data = self._get("MarketData/GetMarketOverview/1")
        row = data.get("marketOverview", {})
        self._write_cache(path, {"marketOverview": row})
        return row

    def history(self, ins_code: str, days: int = 130) -> list[dict]:
        path = HIST_CACHE / f"{ins_code}.json"
        cached = self._read_cache(path, ttl=max(self.ttl, 6 * 3600))
        if cached is not None:
            rows = cached.get("rows", [])
            cached_days = int(cached.get("days") or len(rows))
            if cached_days >= days:
                return rows[:days] if days < len(rows) else rows
        data = self._get(f"ClosingPrice/GetClosingPriceDailyList/{ins_code}/{days}")
        rows = data.get("closingPriceDaily", [])
        self._write_cache(path, {"rows": rows, "days": days})
        return rows

    def histories(self, ins_codes: list[str], days: int = 130) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self.history, c, days): c for c in ins_codes}
            for fut, code in futures.items():
                try:
                    out[code] = fut.result()
                except FetchError:
                    out[code] = []
        return out

    def client_type(self, ins_code: str, d_even: int) -> dict | None:
        path = CT_CACHE / f"{ins_code}_{d_even}.json"
        # دادهٔ روزهای گذشته ثابت است؛ فقط روز جاری ممکن است در حال تکمیل باشد
        today = int(date.today().strftime("%Y%m%d"))
        ttl = 600 if d_even >= today else 24 * 3600
        cached = self._read_cache(path, ttl=ttl)
        if cached is not None:
            return cached.get("row")
        try:
            data = self._get(
                f"ClientType/GetClientTypeHistory/{ins_code}/{d_even}",
                retries=2,
                timeout=8,
            )
        except FetchError:
            return None
        row = data.get("clientType")
        if isinstance(row, list):
            row = row[0] if row else None
        self._write_cache(path, {"row": row})
        return row

    def index_history(self, index_code: str = TEDPIX_CODE) -> list[dict]:
        """تاریخچهٔ شاخص کل (TEDPIX) — ردیف‌ها صعودی‌اند."""
        path = CACHE / f"index_{index_code}.json"
        cached = self._read_cache(path, ttl=max(self.ttl, 6 * 3600))
        if cached is not None:
            return cached["rows"]
        data = self._get(f"Index/GetIndexB2History/{index_code}")
        rows = data.get("indexB2", [])
        self._write_cache(path, {"rows": rows})
        return rows

    def best_limits(self, ins_code: str) -> list[dict]:
        try:
            data = self._get(f"BestLimits/{ins_code}", retries=2, timeout=8)
        except FetchError:
            return []
        return data.get("bestLimits", []) or []
