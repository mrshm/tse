package com.tse.tools;

import android.content.Context;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.RecyclerView;

import org.json.JSONArray;
import org.json.JSONObject;

/** فهرست نمادهای اسکن‌شده به‌ترتیب امتیاز. */
public class ScanAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {

    private static final int TYPE_HEADER = 0;
    private static final int TYPE_ROW = 1;

    private final JSONArray rows;
    private final View header;

    public ScanAdapter(JSONArray rows, View header) {
        this.rows = rows == null ? new JSONArray() : rows;
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
        return rows.length() + 1;
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        if (viewType == TYPE_HEADER) {
            return new RecyclerView.ViewHolder(header) {
            };
        }
        View v = android.view.LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_scan, parent, false);
        return new RowHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        if (getItemViewType(position) != TYPE_ROW) {
            return;
        }
        JSONObject r = rows.optJSONObject(position - 1);
        if (r == null) {
            return;
        }
        RowHolder h = (RowHolder) holder;
        Context c = h.itemView.getContext();

        h.symbol.setText(Fmt.orDash(r.optString("symbol")));
        String setup = r.optString("setup", "");
        String market = r.optString("market", "");
        String sub = setup.isEmpty() ? market : setup + (market.isEmpty() ? "" : " · " + market);
        h.sub.setText(sub);

        double score = r.optDouble("score", 0);
        h.score.setText(Fmt.n(score, 0));
        h.score.setTextColor(ContextCompat.getColor(c,
                score >= 75 ? R.color.primary : R.color.text_secondary));

        double close = r.optDouble("close", r.optDouble("last_price", 0));
        h.price.setText(Fmt.toman(close));
        double chg = r.optDouble("change_pct", 0);
        h.change.setText(Fmt.pct(chg, 2));
        h.change.setTextColor(ContextCompat.getColor(c, chg >= 0 ? R.color.good : R.color.bad));

        JSONArray spark = r.optJSONArray("spark");
        if (spark != null && spark.length() > 1) {
            float[] vals = new float[spark.length()];
            for (int i = 0; i < vals.length; i++) {
                vals[i] = (float) spark.optDouble(i);
            }
            h.spark.setColor(chg >= 0 ? R.color.good : R.color.bad);
            h.spark.setData(vals);
            h.spark.setVisibility(View.VISIBLE);
        } else {
            h.spark.setVisibility(View.INVISIBLE);
        }
    }

    static class RowHolder extends RecyclerView.ViewHolder {
        final TextView symbol, sub, price, change, score;
        final SparkView spark;

        RowHolder(@NonNull View v) {
            super(v);
            symbol = v.findViewById(R.id.symbol);
            sub = v.findViewById(R.id.sub);
            price = v.findViewById(R.id.price);
            change = v.findViewById(R.id.change);
            score = v.findViewById(R.id.score);
            spark = v.findViewById(R.id.spark);
        }
    }

    /** کارت خلاصهٔ بازار که بالای فهرست می‌آید. */
    public static View buildHeader(Context c, Store s) {
        com.google.android.material.card.MaterialCardView card = Ui.card(c);
        LinearLayout box = Ui.vbox(c);
        Ui.pad(box, c, 18, 16, 18, 14);

        JSONObject m = s.market();
        if (m != null) {
            LinearLayout row = Ui.hbox(c);
            TextView idx = Ui.text(c, Fmt.n(m.optDouble("index"), 0), 24f, R.color.text_primary, true);
            row.addView(idx);
            double change = m.optDouble("index_change", 0);
            double prev = m.optDouble("index") - change;
            double pct = prev > 0 ? change / prev * 100 : 0;
            TextView pill = Ui.pill(c, Fmt.pct(pct, 2),
                    pct >= 0 ? R.color.good : R.color.bad,
                    pct >= 0 ? R.color.good_bg : R.color.bad_bg);
            LinearLayout.LayoutParams lp = Ui.wrapWrap();
            lp.setMargins(Ui.dp(c, 10), 0, 0, 0);
            pill.setLayoutParams(lp);
            row.addView(pill);
            box.addView(row);
            box.addView(Ui.label(c, "شاخص کل · "
                    + Fmt.faOrDash(m.optString("last_date_fa"))
                    + " · " + Fmt.orDash(m.optString("state"))));
        }

        JSONObject counts = s.scan == null ? null : s.scan.optJSONObject("counts");
        if (counts != null) {
            TextView hint = Ui.text(c,
                    Fmt.n(counts.optInt("shown")) + " نماد از "
                            + Fmt.n(counts.optInt("liquid")) + " نماد نقدشونده",
                    12f, R.color.text_muted, false);
            hint.setPadding(0, Ui.dp(c, 8), 0, 0);
            box.addView(hint);
        }
        card.addView(box);
        return card;
    }
}
