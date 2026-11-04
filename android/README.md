# اپ اندروید بورس تهران

اپ بومی (Material 3) که همان موتور پایتونی `core/` را **روی خود گوشی** اجرا
می‌کند؛ نه WebView، نه وابستگی به کامپیوتر. داده‌ها با Chaquopy 17.2.0
(CPython 3.13) از TSETMC گرفته و در حافظهٔ اپ ذخیره می‌شوند. دکمهٔ شناور
«به‌روزرسانی» کل چرخه (اسکن → برگه → دفتر → ریسک) را اجرا می‌کند.

## ساختار

```text
android/
├── app/
│   ├── build.gradle            # Chaquopy، امضا، ABI
│   └── src/
│       ├── main/java/…         # رابط بومی (Fragment + RecyclerView)
│       ├── main/res/           # چیدمان‌ها، تم روشن/تیره، آیکون‌ها
│       ├── main/python/        # تولیدشده: کپی core/ و web/ (در گیت نیست)
│       └── test/java/…         # تست‌های Robolectric + اسکرین‌شات
├── keystore/                   # کلید امضا (در گیت نیست)
├── keystore.properties         # رمز کلید (در گیت نیست)
├── tools/
│   ├── sync_src.sh             # همگام‌سازی core/ و web/ با APK
│   ├── emu_check.sh            # نصب و اجرا روی شبیه‌ساز
│   ├── setup_emulator.sh       # نصب شبیه‌ساز از آینهٔ تنسنت
│   └── dl.py                   # دانلود موازی (هاست کند)
└── local.properties            # مسیر SDK (در گیت نیست)
```

`app/src/main/python/` پیش از هر ساخت به‌طور خودکار با
`tools/sync_src.sh` از `core/` و `web/` پر می‌شود؛ کار دستی لازم نیست.

## پیش‌نیازهای این سیستم

| مورد | مسیر |
|---|---|
| JDK 21 (JDK 25 برای Robolectric کار نمی‌کند) | `/home/mrshm/toolchains/jdk-21.0.13+9` |
| Gradle 8.9 | `/home/mrshm/toolchains/gradle-8.9/bin/gradle` |
| Android SDK (platform 35، build-tools 34) | `/home/mrshm/android-sdk` |
| پایتون ۳٫۱۳ برای Chaquopy | `/home/mrshm/toolchains/py313/python/bin/python3` |
| wheelhouse آفلاین (numpy، pandas، jdatetime، certifi) | `/home/mrshm/wheelhouse` |

## ساخت

```bash
bash tools/build_apk.sh
```

این اسکریپت با JDK 21 و Gradle 8.9 می‌سازد، APK امضاشده را در
`dist/tse-tools-v2.0.apk` می‌گذارد و پوشه‌های `build/` را پاک می‌کند
(`KEEP_BUILD=1` نگهشان می‌دارد). معادل دستی:

```bash
cd android
JAVA_HOME=/home/mrshm/toolchains/jdk-21.0.13+9 \
  /home/mrshm/toolchains/gradle-8.9/bin/gradle --no-daemon assembleRelease
```

پیش‌فرض فقط `arm64-v8a` است؛ برای شبیه‌ساز x86_64:

```bash
ABIS=arm64-v8a,x86_64 bash tools/build_apk.sh
```

> ⚠️ دیسک اکسترنال تقریباً پر است؛ یک ساخت کامل حدود ۰٫۴ گیگابایت فضا لازم
> دارد و پس از ساخت پاک می‌شود. اگر `No space left on device` دیدید،
> `rm -rf app/build build .gradle` و `dist/*.apk` را پاک کنید.

## امضا

`keystore.properties` و `keystore/tse-release.jks` محلی‌اند و در گیت نیستند.
برای کلید تازه:

```bash
keytool -genkeypair -v -keystore keystore/tse-release.jks -alias tse \
  -keyalg RSA -keysize 2048 -validity 10000
```

سپس `keystore.properties` را با `storeFile`، `storePassword`، `keyAlias` و
`keyPassword` بسازید. اگر این فایل نباشد، نسخهٔ release بدون امضا ساخته می‌شود.

## تست و بررسی ظاهر

```bash
JAVA_HOME=/home/mrshm/toolchains/jdk-21.0.13+9 gradle --no-daemon testDebugUnitTest
```

`ScreenshotTest` با Robolectric (`@GraphicsMode(NATIVE)`) ده تصویر روشن/تیره در
`app/build/screenshots/` می‌سازد و پنج زبانه را بدون گوشی بررسی می‌کند.

## شبیه‌ساز

```bash
bash tools/setup_emulator.sh      # یک‌بار: نصب emulator + ایمیج از آینهٔ تنسنت
bash tools/emu_check.sh           # نصب APK، زدن «به‌روزرسانی»، گزارش وضعیت
```

AVD دستی در `~/.android/avd/tse34.avd` تعریف شده است (avdmanager بدون
`package.xml` ایموج را قبول نمی‌کند). برای خاموش‌کردن: `adb emu kill`.
