package com.tse.tools;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.google.android.material.card.MaterialCardView;
import com.google.android.material.progressindicator.LinearProgressIndicator;

import org.json.JSONArray;
import org.json.JSONObject;

/** ریسک: احتمال ورشکستگی، رشد انتظاری و نردبان ریسک. */
public class RiskAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {

    private static final int TYPE_HEADER = 0;
    private static final int TYPE_ROW = 1;

    private final JSONArray ladder;
    private final View header;

    public RiskAdapter(JSONArray ladder, View header) {
        this.ladder = ladder == null ? new JSONArray() : ladder;
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
        return ladder.length() + 1;
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        if (viewType == TYPE_HEADER) {
            return new RecyclerView.ViewHolder(header) {
            };
        }
        View v = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_ladder, parent, false);
        return new RowHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        if (getItemViewType(position) != TYPE_ROW) {
            return;
        }
        JSONObject r = ladder.optJSONObject(position - 1);
        if (r == null) {
            return;
        }
        RowHolder h = (RowHolder) holder;
        Context c = h.itemView.getContext();

        double risk = r.optDouble("risk_pct");
        double profit = r.optDouble("p_profit") * 100;
        double ruin = r.optDouble("p_ruin") * 100;
        double median = (r.optDouble("median_final") - 1) * 100;

        h.risk.setText("ریسک هر معامله " + Fmt.pctPlain(risk, 2));
        h.profit.setText(Fmt.pctPlain(profit, 1) + " سوددهی");
        h.bar.setProgress((int) Math.round(Math.max(0, Math.min(100, profit))), true);
        h.ruin.setText("ورشکستگی " + Fmt.pctPlain(ruin, 1)
                + " · رشد میانه " + Fmt.signed(median, 1) + "٪");
    }

    static class RowHolder extends RecyclerView.ViewHolder {
        final TextView risk, profit, ruin;
        final LinearProgressIndicator bar;

        RowHolder(@NonNull View v) {
            super(v);
            risk = v.findViewById(R.id.risk);
            profit = v.findViewById(R.id.profit);
            ruin = v.findViewById(R.id.ruin);
            bar = v.findViewById(R.id.bar);
        }
    }

    public static View buildHeader(Context c, Store s) {
        MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 14);

        box.addView(Ui.text(c, "ریسک سرمایه", 15f, R.color.text_primary, true));

        JSONObject sum = s.riskSummary();
        if (sum == null) {
            box.addView(Ui.text(c, "هنوز محاسبه نشده — «به‌روزرسانی» را بزنید.",
                    13f, R.color.text_secondary, false));
            card.addView(box);
            return card;
        }

        LinearLayout kpis = Ui.hbox(c);
        kpis.setPadding(0, Ui.dp(c, 12), 0, 0);
        kpis.addView(kpi(c, "ورشکستگی", Fmt.pctPlain(sum.optDouble("p_ruin") * 100, 1),
                R.color.bad), Ui.weight(1f));
        kpis.addView(kpi(c, "سوددهی", Fmt.pctPlain(sum.optDouble("p_profit") * 100, 1),
                R.color.good), Ui.weight(1f));
        kpis.addView(kpi(c, "کاهش میانه", Fmt.pctPlain(sum.optDouble("median_dd") * 100, 1),
                R.color.warn), Ui.weight(1f));
        box.addView(kpis);

        JSONObject kelly = s.risk.optJSONObject("kelly");
        if (kelly != null) {
            box.addView(Ui.kv(c, "کِلی (کامل / نیم / ربع)",
                    Fmt.pctPlain(kelly.optDouble("full") * 100, 1) + " / "
                            + Fmt.pctPlain(kelly.optDouble("half") * 100, 1) + " / "
                            + Fmt.pctPlain(kelly.optDouble("quarter") * 100, 1)));
        }
        JSONObject cfg = s.risk.optJSONObject("config");
        if (cfg != null) {
            box.addView(Ui.kv(c, "فرض‌ها", "حد ضرر " + Fmt.pctPlain(cfg.optDouble("stop_pct"), 0)
                    + " · بازده/ریسک " + Fmt.n(cfg.optDouble("payoff_r"), 1)
                    + " · نرخ برد " + Fmt.pctPlain(cfg.optDouble("win_rate") * 100, 0)));
        }
        String src = s.risk.optString("source", "");
        TextView hint = Ui.text(c, "منبع برآورد: " + Fmt.orDash(src), 11.5f, R.color.text_muted, false);
        hint.setPadding(0, Ui.dp(c, 8), 0, 0);
        box.addView(hint);
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
