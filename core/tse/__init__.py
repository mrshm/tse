"""ابزار تحلیل بازار بورس تهران."""
from __future__ import annotations

import os
from pathlib import Path

__version__ = "0.1.0"


def project_root(default: Path | str) -> Path:
    """ریشهٔ پروژه — جایی که پوشهٔ data ساخته می‌شود.

    به‌صورت پیش‌فرض کنار خود کد است، ولی در اپ اندروید کد داخل APK فقط‌خواندنی
    است، بنابراین اپ متغیر محیطی TSE_HOME را به حافظهٔ قابل‌نوشتن گوشی تنظیم می‌کند.
    """
    env = os.environ.get("TSE_HOME")
    return Path(env) if env else Path(default)


def data_dir(root: Path) -> Path:
    """پوشهٔ داده‌های اجرا (JSONها، کش، دفتر معاملات)."""
    d = (Path(root) / "data").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def output_dir(root: Path) -> Path:
    """پوشهٔ خروجی‌های HTML (`web/out`) — بخش وب پروژه."""
    d = (Path(root) / "web" / "out").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d
