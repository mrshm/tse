#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  ابزار بورس تهران — یک فایل، همهٔ کارها
#
#  ./tse.sh                همه چیز: اسکن، برگه، دفتر، بک‌تست، راه‌رونده،
#                          جست‌وجو، ریسک و ساخت صفحهٔ یکپارچه
#  ./tse.sh fast           همان، بدون مراحل پژوهشی (بک‌تست/راه‌رونده/جست‌وجو)
#
#  تک‌مرحله‌ای‌ها (هر کدام آرگومان‌های خودش را می‌پذیرد):
#  ./tse.sh scan [--top 60]      ./tse.sh plan [--capital 50]
#  ./tse.sh journal status       ./tse.sh journal open
#  ./tse.sh journal close سبهان --price 800 --reason هدف
#  ./tse.sh risk [--risk 1]      ./tse.sh backtest [--days 400]
#  ./tse.sh walkforward          ./tse.sh sweep [--top 3,5,8]
#  ./tse.sh home
#
#  گزینه‌های حالت «همه»:  --symbols=300   --days=450   --no-open
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
cd "$(dirname "$0")" || exit 1

PY=${PY:-/home/mrshm/.venvs/market/bin/python}
CMD=all
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then CMD=$1; shift; fi

usage() {
  sed -n '3,17p' "$0" | sed 's/^# \{0,1\}//'
}

# ── تک‌مرحله‌ای ──────────────────────────────────────────────────────────────
single() {                # single <script> [args...] — مگر --no-open، خودش باز می‌کند
  local script=$1; shift
  local args=() open=1
  for a in "$@"; do
    if [ "$a" = "--no-open" ]; then open=0; else args+=("$a"); fi
  done
  [ "$open" -eq 1 ] && args+=(--open)
  exec "$PY" "$script" "${args[@]}"
}

case "$CMD" in
  scan)        single core/run_scan.py "$@" ;;
  plan)        single core/run_plan.py "$@" ;;
  backtest)    single core/run_backtest.py "$@" ;;
  walkforward|wf) single core/run_walkforward.py "$@" ;;
  sweep)       single core/run_sweep.py "$@" ;;
  risk)        single core/run_risk.py "$@" ;;
  home)        single core/run_home.py "$@" ;;
  journal)     exec "$PY" core/run_journal.py "$@" ;;
  -h|--help|help) usage; exit 0 ;;
  all|fast)    : ;;
  *)  echo "دستور ناشناخته: $CMD" >&2; echo; usage; exit 2 ;;
esac

# ── حالت کامل ───────────────────────────────────────────────────────────────
SYMBOLS=300
DAYS=""
NO_OPEN=0
for a in "$@"; do
  case "$a" in
    --no-open)  NO_OPEN=1 ;;
    --symbols=*) SYMBOLS="${a#*=}" ;;
    --days=*)   DAYS="${a#*=}" ;;
    *) echo "گزینهٔ ناشناخته: $a" >&2; exit 2 ;;
  esac
done

common=()
[ -n "$DAYS" ] && common+=(--days "$DAYS")

ok=0
failed=()
step() {
  local label=$1; shift
  printf '\n\033[1m▸ %s\033[0m\n' "$label"
  printf '%s\n' "──────────────────────────────────────────────────────────────"
  if "$@"; then
    ok=$((ok + 1))
  else
    failed+=("$label")
  fi
}

start=$(date +%s)

step "اسکن بازار"             "$PY" core/run_scan.py "${common[@]}"
step "برگهٔ سفارش"            "$PY" core/run_plan.py
step "وضعیت دفتر معاملات"     "$PY" core/run_journal.py status

if [ "$CMD" = "all" ]; then
  step "بک‌تست"                "$PY" core/run_backtest.py --symbols "$SYMBOLS" "${common[@]}"
  step "اعتبارسنجی راه‌رونده"  "$PY" core/run_walkforward.py --symbols "$SYMBOLS" "${common[@]}"
  step "جست‌وجوی پارامتر"      "$PY" core/run_sweep.py --symbols "$SYMBOLS" "${common[@]}"
fi

risk_args=()
CLOSED=$("$PY" -c 'import json;print(len(json.load(open("data/journal.json")).get("closed",[])))' 2>/dev/null)
if [ "${CLOSED:-0}" -ge 10 ]; then
  risk_args+=(--from-journal)
fi
step "ریسک ورشکستگی"          "$PY" core/run_risk.py "${risk_args[@]}"

home_args=()
[ "$NO_OPEN" -eq 0 ] && home_args+=(--open)
step "صفحهٔ یکپارچه"          "$PY" core/run_home.py "${home_args[@]}"

elapsed=$(( $(date +%s) - start ))
printf '\n\033[1m%s\033[0m\n' "══════════════════════════════════════════════════════════════"
printf '  %d مرحله موفق در %d ثانیه\n' "$ok" "$elapsed"
if [ ${#failed[@]} -gt 0 ]; then
  printf '  ⚠ ناموفق: %s\n' "$(IFS='، '; echo "${failed[*]}")"
fi
printf '  صفحه: %s\n' "$PWD/web/out/index.html"
printf '%s\n\n' "══════════════════════════════════════════════════════════════"

[ ${#failed[@]} -eq 0 ]
