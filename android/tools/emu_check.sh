#!/usr/bin/env bash
# نصب و اجرای اپ روی شبیه‌ساز x86_64 و فشردن دکمهٔ «به‌روزرسانی» تا پایان سینک.
set -uo pipefail

ADB=/home/mrshm/android-sdk/platform-tools/adb
PKG=com.tse.tools
ANDROID="$(cd "$(dirname "$0")/.." && pwd)"
APK=${1:-"$ANDROID/app/build/outputs/apk/debug/app-debug.apk"}

echo "== install $APK"
"$ADB" install -r -g "$APK" || exit 1

echo "== start"
"$ADB" shell am force-stop "$PKG"
"$ADB" shell am start -W -n "$PKG/.MainActivity" | tail -3
sleep 6

echo "== find update button"
"$ADB" shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
"$ADB" pull /sdcard/ui.xml /tmp/emu/ui.xml >/dev/null 2>&1
BOUNDS=$(python3 - <<'PY'
import re
xml = open('/tmp/emu/ui.xml', encoding='utf-8').read()
for m in re.finditer(r'<node[^>]*>', xml):
    tag = m.group(0)
    if 'به‌روزرسانی' in tag and 'bounds=' in tag:
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if b:
            x1, y1, x2, y2 = map(int, b.groups())
            print((x1 + x2) // 2, (y1 + y2) // 2)
            break
PY
)
if [ -z "$BOUNDS" ]; then
  echo "update button not found in UI dump; nodes with text:"
  grep -o 'text="[^"]*"' /tmp/emu/ui.xml | sort -u | head -20
  exit 1
fi
echo "tap at $BOUNDS"
"$ADB" shell input tap $BOUNDS

echo "== sync in progress"
for i in $(seq 1 120); do
  st=$("$ADB" shell run-as $PKG cat files/status.json 2>/dev/null | tr -d '\r')
  if [ -n "$st" ]; then
    running=$(printf '%s' "$st" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("step"),"|pct",d.get("pct"),"|running",d.get("running"),"|err",d.get("error"))' 2>/dev/null)
    echo "[$((i*10))s] $running"
    case "$st" in
      *'"running": false'*|*'"running":false'*) break ;;
    esac
  fi
  sleep 10
done

echo "== files"
"$ADB" shell run-as $PKG ls -l files/data | tail -20
echo "== last status"
"$ADB" shell run-as $PKG cat files/status.json
