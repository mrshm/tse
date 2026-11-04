"""تعیین دامنه نمادهای قابل معامله از فهرست MarketWatch.

TSETMC هر ابزار را با ترکیب (flow, cGrValCot) دسته‌بندی می‌کند. این ماژول
سه نوع ابزار را تشخیص می‌دهد:

  - سهام (stock)
  - حق تقدم (rights)
  - صندوق قابل معامله / ETF (etf)

صندوق‌ها با نامشان شناسایی می‌شوند چون در گروه‌های (flow, cGrValCot) با سهام
مشترک‌اند؛ مثلاً گروه (2, "1A") هم سهم دارد هم صندوق. اوراق، صکوک، اختیار
معامله و گواهی‌ها حذف می‌شوند.
"""

from __future__ import annotations

# (flow, cGrValCot) -> بازار
STOCK_GROUPS: dict[tuple[int, str], str] = {
    (1, "N1"): "بورس",
    (1, "N2"): "بورس",
    (1, "NS"): "بورس",
    (1, "91"): "بورس",
    (2, "Z1"): "فرابورس",
    (2, "1A"): "فرابورس",
    (2, "1Z"): "فرابورس",
    (2, "V1"): "فرابورس",
    (2, "D1"): "فرابورس",
    (2, "T1"): "فرابورس",
    (2, "19"): "فرابورس",
    (2, "71"): "فرابورس",
    (2, "W1"): "فرابورس",
    (2, "47"): "فرابورس",
    (4, "P1"): "پایه",
    (4, "C1"): "پایه",
    (4, "L1"): "پایه",
}

# حق تقدم‌ها (ریسک بالاتر، نقدشوندگی کمتر)
RIGHTS_GROUPS = {
    (1, "52"), (1, "1O"), (1, "O1"),
    (2, "T2"), (2, "16"), (2, "K2"), (2, "TL"), (2, "41"), (2, "2Z"),
    (4, "P2"),
}

FLOW_MARKET = {1: "بورس", 2: "فرابورس", 3: "پایه", 4: "پایه", 7: "کالا"}

EXCLUDE_NAME_PARTS = (
    "صكوك", "صکوک", "اوراق", "اختيار", "اختیار", "مرابحه",
    "اجاره", "مشاركت", "مشارکت", "سلف", "تسه", "گواهي", "گواهی",
)


def is_fund(name: str) -> bool:
    """شناسایی صندوق از روی نام کامل (لوی‌کد)."""
    n = str(name or "").strip()
    return "صندوق" in n or n.startswith("ص.") or n.startswith("ص ")


def classify(row: dict) -> tuple[str, str] | None:
    """(بازار، نوع) — نوع یکی از stock / rights / etf — یا None اگر سهم نباشد."""
    name = str(row.get("lvc") or "")
    if any(part in name for part in EXCLUDE_NAME_PARTS):
        return None

    if is_fund(name):
        market = FLOW_MARKET.get(row.get("flow"), "سایر")
        if market == "سایر":
            return None
        return market, "etf"

    key = (row.get("flow"), row.get("cGrValCot"))
    market = STOCK_GROUPS.get(key)
    if market is not None:
        return market, "stock"
    if key in RIGHTS_GROUPS:
        market = FLOW_MARKET.get(row.get("flow"), "سایر")
        return market, "rights"
    return None


def build_universe(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        cls = classify(r)
        if cls is None:
            continue
        market, kind = cls
        close = _num(r.get("pdv")) or _num(r.get("pClosing"))
        last = _num(r.get("pmd")) or close
        prev = _num(r.get("py"))
        if close <= 0 and last <= 0:
            continue
        price = close if close > 0 else last
        change_pct = ((close / prev - 1) * 100) if (prev > 0 and close > 0) else 0.0
        out.append(
            {
                "ins_code": str(r.get("insCode")),
                "symbol": str(r.get("lva") or "").strip(),
                "name": str(r.get("lvc") or "").strip(),
                "market": market,
                "kind": kind,
                "is_rights": kind == "rights",
                "is_etf": kind == "etf",
                "price": price,
                "last_price": last,
                "prev_close": prev,
                "change_pct": change_pct,
                "volume": _num(r.get("qtj")),
                "value": _num(r.get("qtc")),
                "trades": _num(r.get("ztt")),
                "price_min": _num(r.get("pmn")),
                "price_max": _num(r.get("pmx")),
                "limit_high": _num(r.get("pMax")),
                "limit_low": _num(r.get("pMin")),
                "eps": _num(r.get("eps")),
                "pe": _num(r.get("pe")),
            }
        )
    return out


def _num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
