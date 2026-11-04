package com.tse.tools;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.RecyclerView;

import com.google.android.material.card.MaterialCardView;

import org.json.JSONArray;
import org.json.JSONObject;

/** برگهٔ سفارش: چند سهم، با چه حجمی، کجا بفروش. */
public class PlanAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {

    private static final int TYPE_HEADER = 0;
    private static final int TYPE_ROW = 1;

    private final JSONArray orders;
    private final View header;

    public PlanAdapter(JSONArray orders, View header) {
        this.orders = orders == null ? new JSONArray() : orders;
        this.header = header;
        if (header != null) {
            Ui.asListHeader(header);
        }
    }

    @Override
    public int getItemViewType(int position) {
        return position == 0 ? TYPE_HEADER : TYPE_ROW;
    }

    @Override
    public int getItemCount() {
        return orders.length() + 1;
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        if (viewType == TYPE_HEADER) {
            return new RecyclerView.ViewHolder(header) {
            };
        }
        View v = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_order, parent, false);
        return new RowHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        if (getItemViewType(position) != TYPE_ROW) {
            return;
        }
        JSONObject o = orders.optJSONObject(position - 1);
        if (o == null) {
            return;
        }
        RowHolder h = (RowHolder) holder;
        Context c = h.itemView.getContext();

        h.symbol.setText(Fmt.orDash(o.optString("symbol")));
        String setup = o.optString("setup", "");
        h.setup.setText(setup);
        h.setup.setVisibility(setup.isEmpty() ? View.GONE : View.VISIBLE);

        h.qty.setText(Fmt.n(o.optDouble("qty")) + " سهم");

        double entry = o.optDouble("entry");
        double stop = o.optDouble("stop");
        double target = o.optDouble("target");
        double cost = o.optDouble("cost");

        h.line1.setText("خرید " + Fmt.n(entry) + " · حدود " + Fmt.n(o.optDouble("entry_low"))
                + " تا " + Fmt.n(entry) + " تومان · هزینه " + Fmt.moneyM(cost));
        h.line2.setText("حد ضرر " + Fmt.n(stop) + " · حد سود " + Fmt.n(target)
                + " · بازده " + Fmt.pctPlain(o.optDouble("target_ret_pct"), 1));
        String exit = o.optString("exit_date_fa", "");
        h.line3.setText("خروج: " + Fmt.faOrDash(exit)
                + " · ریسک " + Fmt.moneyM(o.optDouble("risk")));
    }

    static class RowHolder extends RecyclerView.ViewHolder {
        final TextView symbol, setup, qty, line1, line2, line3;

        RowHolder(@NonNull View v) {
            super(v);
            symbol = v.findViewById(R.id.symbol);
            setup = v.findViewById(R.id.setup);
            qty = v.findViewById(R.id.qty);
            line1 = v.findViewById(R.id.line1);
            line2 = v.findViewById(R.id.line2);
            line3 = v.findViewById(R.id.line3);
        }
    }

    /** کارت خلاصهٔ برگه: سرمایه، نقد، ریسک. */
    public static View buildHeader(Context c, Store s) {
        MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 12);

        JSONObject sum = s.planSummary();
        if (sum == null) {
            box.addView(Ui.text(c, "برگهٔ سفارش هنوز ساخته نشده.", 13f, R.color.text_secondary, false));
            card.addView(box);
            return card;
        }

        LinearLayout row = Ui.hbox(c);
        TextView big = Ui.text(c, Fmt.n(sum.optInt("count")), 28f, R.color.text_primary, true);
        row.addView(big);
        TextView lbl = Ui.label(c, "  سهم برای خرید");
        row.addView(lbl);
        box.addView(row);

        LinearLayout kpis = Ui.hbox(c);
        kpis.setPadding(0, Ui.dp(c, 12), 0, 0);
        kpis.addView(kpi(c, "سرمایه", Fmt.moneyM(sum.optDouble("invested")), R.color.text_primary),
                Ui.weight(1f));
        kpis.addView(kpi(c, "نقد", Fmt.moneyM(sum.optDouble("cash")), R.color.text_secondary),
                Ui.weight(1f));
        kpis.addView(kpi(c, "ریسک", Fmt.pctPlain(sum.optDouble("risk_total_pct"), 1),
                R.color.warn), Ui.weight(1f));
        box.addView(kpis);

        String source = s.plan == null ? "" : s.plan.optString("source_date_fa", "");
        String exit = s.plan == null ? "" : s.plan.optString("exit_date_fa", "");
        TextView hint = Ui.text(c, "مبنای قیمت: " + Fmt.faOrDash(source) + " · خروج پیشنهادی: "
                + Fmt.faOrDash(exit), 11.5f, R.color.text_muted, false);
        hint.setPadding(0, Ui.dp(c, 10), 0, 0);
        box.addView(hint);

        if (s.plan != null && s.plan.optBoolean("stale")) {
            TextView warn = Ui.pill(c, "قیمت‌ها مربوط به اسکن قبلی است", R.color.warn, R.color.warn_bg);
            warn.setPadding(Ui.dp(c, 8), Ui.dp(c, 3), Ui.dp(c, 8), Ui.dp(c, 3));
            LinearLayout.LayoutParams lp = Ui.wrapWrap();
            lp.topMargin = Ui.dp(c, 8);
            warn.setLayoutParams(lp);
            box.addView(warn);
        }
        card.addView(box);
        return card;
    }

    private static LinearLayout kpi(Context c, String label, String value, int colorRes) {
        LinearLayout col = Ui.vbox(c);
        col.addView(Ui.label(c, label));
        TextView v = Ui.text(c, value, 15f, colorRes, true);
        v.setPadding(0, Ui.dp(c, 2), 0, 0);
        col.addView(v);
        return col;
    }
}
