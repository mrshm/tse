#!/usr/bin/env bash
# ساخت APK امضاشده و کپی آن به dist/.
#
# دیسک اکسترنال تقریباً پر است، بنابراین بعد از ساخت پوشه‌های build پاک می‌شوند
# تا فضای آزاد بماند. برای نگه‌داشتن خروجی ساخت: KEEP_BUILD=1
set -euo pipefail

ANDROID="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ANDROID/.." && pwd)"
GRADLE="${GRADLE:-/home/mrshm/toolchains/gradle-8.9/bin/gradle}"
export JAVA_HOME="${JAVA_HOME:-/home/mrshm/toolchains/jdk-21.0.13+9}"
ABIS="${ABIS:-arm64-v8a}"

cd "$ANDROID"
"$GRADLE" --no-daemon -Pabis="$ABIS" assembleRelease

VERSION=$(sed -n 's/.*versionName "\([^"]*\)".*/\1/p' app/build.gradle | head -1)
mkdir -p "$REPO/dist"
OUT="$REPO/dist/tse-tools-v${VERSION:-latest}.apk"
cp app/build/outputs/apk/release/app-release.apk "$OUT"
echo "APK: $OUT"

if [ "${KEEP_BUILD:-0}" != "1" ]; then
  rm -rf app/build build .gradle
  echo "build dirs cleaned (KEEP_BUILD=1 to keep them)"
fi
