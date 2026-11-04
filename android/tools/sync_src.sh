#!/usr/bin/env bash
# کدهای پایتون پروژه را از core/ و web/ داخل اپ کپی می‌کند.
# کد اصلی همچنان در پوشه‌های core/ و web/ است؛ نسخهٔ داخل اپ فقط برای ساخت APK
# تولید می‌شود و در گیت نگهداری نمی‌شود.
set -euo pipefail

ANDROID="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ANDROID/.." && pwd)"
DST="$ANDROID/app/src/main/python"

mkdir -p "$DST/tse" "$DST/web"
find "$DST/tse" "$DST/web" -mindepth 1 -delete

cp -a "$REPO/core/tse/." "$DST/tse/"
cp -a "$REPO/web/." "$DST/web/"
rm -rf "$DST/web/out"
find "$DST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$DST" -name '*.pyc' -delete
cp -p "$REPO"/core/run_*.py "$DST"/
rm -f "$DST/hello.py"

echo "synced: $(ls "$DST"/run_*.py | wc -l) scripts + tse/ ($(ls "$DST/tse"/*.py | wc -l) modules) + web/ ($(ls "$DST/web"/*.py | wc -l) modules)"
