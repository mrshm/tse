package com.tse.tools;

import java.math.RoundingMode;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.Locale;

/** قالب‌بندی اعداد با ارقام فارسی، هم‌خوان با گزارش‌های دسکتاپ. */
public final class Fmt {

    private static final char ZWNJ = '‌';

    private static DecimalFormat make(int decimals) {
        DecimalFormatSymbols sym = new DecimalFormatSymbols(new Locale("fa", "IR"));
        sym.setZeroDigit('۰');
        sym.setGroupingSeparator('٬');
        sym.setDecimalSeparator('٫');
        DecimalFormat f = new DecimalFormat("#,##0", sym);
        f.setMinimumFractionDigits(decimals);
        f.setMaximumFractionDigits(decimals);
        f.setRoundingMode(RoundingMode.HALF_UP);
        return f;
    }

    public static String n(double v) {
        return make(0).format(v);
    }

    public static String n(double v, int decimals) {
        return make(decimals).format(v);
    }

    /** علامت را داخل خود عدد نگه می‌دارد تا در متن راست‌به‌چپ جابه‌جا نشود. */
    public static String signed(double v, int decimals) {
        String s = make(decimals).format(v);
        return v > 0 ? "+" + s : s;
    }

    public static String pct(double v, int decimals) {
        return signed(v, decimals) + "٪";
    }

    public static String pctPlain(double v, int decimals) {
        return n(v, decimals) + "٪";
    }

    /** ریال → تومان. */
    public static String toman(double rial) {
        return n(rial / 10.0);
    }

    /** ارزش معاملات به میلیارد تومان. */
    public static String tomanB(double rial) {
        return n(rial / 1e10);
    }

    /** جدا کردن اعداد لاتین از متن فارسی (جهت‌نمایی). */
    public static String iso(String s) {
        return "⁦" + s + "⁩";
    }

    public static String money(double tomanValue) {
        return n(tomanValue) + " تومان";
    }

    public static String moneyM(double tomanValue) {
        return n(tomanValue / 1e6, 1) + " م.ت";
    }

    /** رشتهٔ خالی/null → خط تیره. */
    public static String orDash(String s) {
        return s == null || s.isEmpty() || s.equals("null") ? "—" : s;
    }

    /** ارقام لاتین را به فارسی تبدیل می‌کند؛ برای تاریخ‌هایی که پایتون خام می‌نویسد. */
    public static String faDigits(String s) {
        if (s == null || s.isEmpty()) {
            return "";
        }
        StringBuilder out = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            out.append(ch >= '0' && ch <= '9' ? (char) ('۰' + (ch - '0')) : ch);
        }
        return out.toString();
    }

    /** مثل {@link #orDash} ولی ارقام را هم فارسی می‌کند. */
    public static String faOrDash(String s) {
        return faDigits(orDash(s));
    }
}
