#!/usr/bin/env bash
# نصب شبیه‌ساز اندروید از فایل‌های دانلود‌شده در /tmp/emu (مخزن گوگل بسته است).
set -euo pipefail

SDK=/home/mrshm/android-sdk
AVD=tse34

echo "== emulator"
unzip -q -o /tmp/emu/emulator.zip -d "$SDK"

echo "== system image (android-34 default x86_64)"
mkdir -p "$SDK/system-images/android-34/default"
unzip -q -o /tmp/emu/sysimg.zip -d "$SDK/system-images/android-34/default"

echo "== cmdline-tools"
mkdir -p "$SDK/cmdline-tools"
unzip -q -o /tmp/emu/cmdline-tools.zip -d "$SDK/cmdline-tools"
if [ ! -d "$SDK/cmdline-tools/latest" ] && [ -d "$SDK/cmdline-tools/cmdline-tools" ]; then
  mv "$SDK/cmdline-tools/cmdline-tools" "$SDK/cmdline-tools/latest"
fi
chmod +x "$SDK/cmdline-tools/latest/bin/"* "$SDK/emulator/emulator" "$SDK/emulator/"*.so \
  "$SDK/emulator/qemu/linux-x86_64/"* 2>/dev/null || true

echo "== avd"
export ANDROID_SDK_ROOT="$SDK" ANDROID_HOME="$SDK"
if ! "$SDK/cmdline-tools/latest/bin/avdmanager" list avd | grep -q "$AVD"; then
  echo no | "$SDK/cmdline-tools/latest/bin/avdmanager" create avd -n "$AVD" \
    -k "system-images;android-34;default;x86_64" -d pixel_5 --force
fi

echo "== done"
"$SDK/emulator/emulator" -list-avds
