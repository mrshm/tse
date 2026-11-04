package com.tse.tools;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.Fragment;

import com.google.android.material.card.MaterialCardView;

import org.json.JSONArray;
import org.json.JSONObject;

/** زبانهٔ «امروز»: نمای کلی بازار، برگهٔ سفارش، پوزیشن‌ها و ریسک. */
public class TodayFragment extends Fragment implements MainActivity.Refreshable {

    private LinearLayout content;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_today, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        content = view.findViewById(R.id.content);
        rebuild();
    }

    @Override
    public void onDataChanged() {
        if (content != null) {
            rebuild();
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        if (content != null) {
            rebuild();
        }
    }

    private void rebuild() {
        content.removeAllViews();
        Store s = Store.peek();
        if (!s.hasAny()) {
            content.addView(emptyCard());
            return;
        }
        content.addView(marketCard(s));
        content.addView(planCard(s));
        content.addView(positionsCard(s));
        content.addView(riskCard(s));
    }

    private View emptyCard() {
        MaterialCardView card = Ui.card(requireContext());
        LinearLayout box = Ui.vbox(requireContext());
        Ui.pad(box, requireContext(), 18, 22, 18, 22);
        TextView t = Ui.text(requireContext(), getString(R.string.no_data_title), 16f,
                R.color.text_primary, true);
        t.setGravity(android.view.Gravity.CENTER);
        TextView b = Ui.text(requireContext(), getString(R.string.no_data_body), 13f,
                R.color.text_secondary, false);
        b.setGravity(android.view.Gravity.CENTER);
        b.setPadding(0, Ui.dp(requireContext(), 8), 0, 0);
        box.addView(t);
        box.addView(b);
        card.addView(box);
        return card;
    }

    private MaterialCardView marketCard(Store s) {
        android.content.Context c = requireContext();
        MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 16);

        box.addView(Ui.label(c, "بازار"));

        JSONObject m = s.market();
        if (m != null) {
            LinearLayout row = Ui.hbox(c);
            TextView idx = Ui.text(c, Fmt.n(m.optDouble("index"), 0), 27f, R.color.text_primary, true);
            row.addView(idx);
            double change = m.optDouble("index_change", 0);
            double prev = m.optDouble("index", 0) - change;
            double pct = prev > 0 ? change / prev * 100 : 0;
            TextView pill = Ui.pill(c, Fmt.pct(pct, 2),
                    pct >= 0 ? R.color.good : R.color.bad,
                    pct >= 0 ? R.color.good_bg : R.color.bad_bg);
            LinearLayout.LayoutParams lp = Ui.wrapWrap();
            lp.setMargins(Ui.dp(c, 10), 0, 0, 0);
            pill.setLayoutParams(lp);
            row.addView(pill);
            box.addView(row);
            box.addView(Ui.label(c, "شاخص کل · " + Fmt.faOrDash(m.optString("last_date_fa"))));
        }

        LinearLayout kpis = Ui.hbox(c);
        kpis.setPadding(0, Ui.dp(c, 16), 0, 0);

        JSONObject b = s.breadth();
        if (b != null) {
            kpis.addView(kpi(c, "ارزش معاملات", Fmt.tomanB(m != null ? m.optDouble("activity_value") : 0),
                    "میلیارد تومان", R.color.text_primary), Ui.weight(1f));
            kpis.addView(kpi(c, "مثبت", Fmt.n(b.optInt("up")), "نماد", R.color.good), Ui.weight(1f));
            kpis.addView(kpi(c, "منفی", Fmt.n(b.optInt("down")), "نماد", R.color.bad), Ui.weight(1f));
        }
        box.addView(kpis);
        card.addView(box);
        return card;
    }

    private LinearLayout kpi(android.content.Context c, String label, String value,
                             String unit, int colorRes) {
        LinearLayout col = Ui.vbox(c);
        col.addView(Ui.label(c, label));
        TextView v = Ui.text(c, value, 19f, colorRes, true);
        v.setPadding(0, Ui.dp(c, 2), 0, 0);
        col.addView(v);
        col.addView(Ui.text(c, unit, 10.5f, R.color.text_muted, false));
        return col;
    }

    private MaterialCardView planCard(Store s) {
        android.content.Context c = requireContext();
        MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 10);
        box.addView(Ui.text(c, "برگهٔ سفارش", 15f, R.color.text_primary, true));

        JSONObject sum = s.planSummary();
        if (sum == null) {
            box.addView(Ui.text(c, "هنوز ساخته نشده — «به‌روزرسانی» را بزنید.", 13f,
                    R.color.text_secondary, false));
            card.addView(box);
            return card;
        }
        int count = sum.optInt("count");
        box.addView(Ui.label(c, Fmt.n(count) + " سهم برای خرید"));
        box.addView(Ui.kv(c, "سرمایهٔ درگیر", Fmt.moneyM(sum.optDouble("invested"))));
        box.addView(Ui.kv(c, "نقد آزاد", Fmt.moneyM(sum.optDouble("cash"))));
        box.addView(Ui.kv(c, "ریسک کل", Fmt.moneyM(sum.optDouble("risk_total"))
                + "  (" + Fmt.pctPlain(sum.optDouble("risk_total_pct"), 1) + ")"));
        if (s.plan != null && s.plan.optBoolean("stale")) {
            box.addView(Ui.pill(c, "قیمت‌ها مربوط به اسکن قبلی است", R.color.warn, R.color.warn_bg));
        }
        card.addView(box);
        return card;
    }

    private MaterialCardView positionsCard(Store s) {
        android.content.Context c = requireContext();
        MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 10);
        box.addView(Ui.text(c, "پوزیشن‌های باز", 15f, R.color.text_primary, true));

        JSONArray pos = s.openPositions();
        if (pos.length() == 0) {
            box.addView(Ui.text(c, "هیچ پوزیشن بازی ثبت نشده.", 13f, R.color.text_secondary, false));
            card.addView(box);
            return card;
        }
        for (int i = 0; i < pos.length(); i++) {
            JSONObject p = pos.optJSONObject(i);
            if (p == null) continue;
            LinearLayout row = Ui.hbox(c);
            row.setPadding(0, Ui.dp(c, 6), 0, Ui.dp(c, 6));
            row.addView(Ui.value(c, Fmt.orDash(p.optString("symbol")), 14f), Ui.weight(1f));
            row.addView(Ui.label(c, "×" + Fmt.n(p.optDouble("qty"))), Ui.weight(1f));
            double pnl = p.optDouble("pnl", 0);
            row.addView(Ui.text(c, Fmt.signed(pnl, 0), 13.5f,
                    pnl >= 0 ? R.color.good : R.color.bad, true), Ui.weight(1f));
            box.addView(row);
        }
        card.addView(box);
        return card;
    }

    private MaterialCardView riskCard(Store s) {
        android.content.Context c = requireContext();
        MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 10);
        box.addView(Ui.text(c, "ریسک", 15f, R.color.text_primary, true));

        JSONObject r = s.riskSummary();
        if (r == null) {
            box.addView(Ui.text(c, "هنوز محاسبه نشده — «به‌روزرسانی» را بزنید.", 13f,
                    R.color.text_secondary, false));
            card.addView(box);
            return card;
        }
        double ruin = r.optDouble("p_ruin") * 100;
        double profit = r.optDouble("p_profit") * 100;
        box.addView(Ui.kv(c, "احتمال از دست دادن ۳۰٪ سرمایه", Fmt.pctPlain(ruin, 1)));
        box.addView(Ui.kv(c, "احتمال سوددهی", Fmt.pctPlain(profit, 1)));
        box.addView(Ui.kv(c, "سرمایهٔ میانه پس از ۲۰۰ معامله",
                Fmt.signed((r.optDouble("median_final") - 1) * 100, 1) + "٪"));
        card.addView(box);
        return card;
    }

    private static int color(android.content.Context c, int res) {
        return ContextCompat.getColor(c, res);
    }
}
