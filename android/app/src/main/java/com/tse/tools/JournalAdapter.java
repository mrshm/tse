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

/** دفتر معاملات: پوزیشن‌های باز و معاملات بسته‌شده. */
public class JournalAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {

    private static final int TYPE_HEADER = 0;
    private static final int TYPE_OPEN = 1;
    private static final int TYPE_CLOSED = 2;
    private static final int TYPE_SECTION = 3;

    private final JSONArray open;
    private final JSONArray closed;
    private final View header;

    public JournalAdapter(JSONArray open, JSONArray closed, View header) {
        this.open = open == null ? new JSONArray() : open;
        this.closed = closed == null ? new JSONArray() : closed;
        this.header = header;
        if (header != null) {
            Ui.asListHeader(header);
        }
    }

    @Override
    public int getItemViewType(int position) {
        if (position == 0) {
            return TYPE_HEADER;
        }
        if (open.length() > 0 && position <= open.length()) {
            return TYPE_OPEN;
        }
        if (closed.length() > 0 && position == open.length() + 1) {
            return TYPE_SECTION;
        }
        return TYPE_CLOSED;
    }

    @Override
    public int getItemCount() {
        int n = open.length() + closed.length() + 1;
        if (closed.length() > 0) {
            n += 1; // عنوان بخش بسته‌شده‌ها
        }
        return n;
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        Context c = parent.getContext();
        if (viewType == TYPE_HEADER) {
            return new RecyclerView.ViewHolder(header) {
            };
        }
        if (viewType == TYPE_SECTION) {
            TextView t = Ui.text(c, "معاملات بسته‌شده", 14f, R.color.text_secondary, true);
            t.setPadding(0, Ui.dp(c, 18), 0, Ui.dp(c, 6));
            return new RecyclerView.ViewHolder(t) {
            };
        }
        View v = LayoutInflater.from(c).inflate(R.layout.item_position, parent, false);
        return new RowHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        int type = getItemViewType(position);
        if (type != TYPE_OPEN && type != TYPE_CLOSED) {
            return;
        }
        RowHolder h = (RowHolder) holder;
        Context c = h.itemView.getContext();
        boolean isOpen = type == TYPE_OPEN;
        JSONObject p = isOpen
                ? open.optJSONObject(position - 1)
                : closed.optJSONObject(position - open.length() - 2);
        if (p == null) {
            return;
        }

        h.symbol.setText(Fmt.orDash(p.optString("symbol")));

        double pnl = p.optDouble("pnl", 0);
        boolean hasPnl = p.has("pnl") && !p.isNull("pnl");
        h.pnl.setText(hasPnl
                ? Fmt.signed(pnl, 0) + " (" + Fmt.signed(p.optDouble("pnl_pct"), 1) + "٪)"
                : "—");
        h.pnl.setTextColor(ContextCompat.getColor(c,
                !hasPnl ? R.color.text_muted : (pnl >= 0 ? R.color.good : R.color.bad)));

        double qty = p.optDouble("qty");
        double entry = p.optDouble("entry");
        if (isOpen) {
            h.line1.setText(Fmt.n(qty) + " سهم × " + Fmt.n(entry) + " تومان");
            StringBuilder sb = new StringBuilder();
            double ltp = p.optDouble("ltp", 0);
            sb.append("قیمت فعلی ").append(ltp > 0 ? Fmt.n(ltp) : "—");
            sb.append(" · حد ضرر ").append(Fmt.n(p.optDouble("stop")));
            if (p.has("target") && !p.isNull("target")) {
                sb.append(" · حد سود ").append(Fmt.n(p.optDouble("target")));
            }
            String exit = Fmt.faDigits(p.optString("planned_exit_fa", ""));
            if (!exit.isEmpty()) {
                sb.append(" · خروج ").append(exit);
            }
            h.line2.setText(sb.toString());
        } else {
            h.line1.setText("ورود " + Fmt.n(entry) + " → خروج " + Fmt.n(p.optDouble("exit"))
                    + " · " + Fmt.n(p.optDouble("holding_days")) + " روز");
            h.line2.setText("تاریخ خروج " + Fmt.faOrDash(p.optString("exit_fa"))
                    + " · " + Fmt.orDash(p.optString("reason")));
        }
    }

    static class RowHolder extends RecyclerView.ViewHolder {
        final TextView symbol, pnl, line1, line2;

        RowHolder(@NonNull View v) {
            super(v);
            symbol = v.findViewById(R.id.symbol);
            pnl = v.findViewById(R.id.pnl);
            line1 = v.findViewById(R.id.line1);
            line2 = v.findViewById(R.id.line2);
        }
    }

    /** خلاصهٔ آماری دفتر. */
    public static View buildHeader(Context c, Store s) {
        MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 14);

        box.addView(Ui.text(c, "دفتر معاملات", 15f, R.color.text_primary, true));

        JSONArray openArr = s.openPositions();
        JSONArray closedArr = s.closedPositions();
        double pnlSum = 0;
        for (int i = 0; i < closedArr.length(); i++) {
            JSONObject o = closedArr.optJSONObject(i);
            if (o != null) {
                pnlSum += o.optDouble("pnl", 0);
            }
        }

        LinearLayout kpis = Ui.hbox(c);
        kpis.setPadding(0, Ui.dp(c, 12), 0, 0);
        kpis.addView(kpi(c, "باز", Fmt.n(openArr.length()), R.color.text_primary), Ui.weight(1f));
        kpis.addView(kpi(c, "بسته", Fmt.n(closedArr.length()), R.color.text_primary), Ui.weight(1f));
        kpis.addView(kpi(c, "سود/زیان", Fmt.signed(pnlSum, 0), pnlSum >= 0 ? R.color.good : R.color.bad),
                Ui.weight(1f));
        box.addView(kpis);

        if (openArr.length() == 0 && closedArr.length() == 0) {
            TextView hint = Ui.text(c,
                    "هنوز معامله‌ای ثبت نشده. از نسخهٔ دسکتاپ با «journal open» سفارش‌های برگه را ثبت کنید.",
                    12f, R.color.text_muted, false);
            hint.setPadding(0, Ui.dp(c, 10), 0, 0);
            box.addView(hint);
        }
        card.addView(box);
        return card;
    }

    private static LinearLayout kpi(Context c, String label, String value, int colorRes) {
        LinearLayout col = Ui.vbox(c);
        col.addView(Ui.label(c, label));
        TextView v = Ui.text(c, value, 17f, colorRes, true);
        v.setPadding(0, Ui.dp(c, 2), 0, 0);
        col.addView(v);
        return col;
    }
}
