package com.tse.tools;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.core.content.ContextCompat;

import com.google.android.material.card.MaterialCardView;

/** ساخت تکه‌های رابط کاربری به سبک متریال، بدون تکرار XML. */
public final class Ui {

    public static int dp(Context c, float v) {
        return (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, v, c.getResources().getDisplayMetrics());
    }

    public static MaterialCardView card(Context c) {
        MaterialCardView card = new MaterialCardView(c);
        card.setRadius(dp(c, 18));
        card.setCardElevation(0);
        card.setStrokeWidth(dp(c, 1));
        card.setStrokeColor(ContextCompat.getColor(c, R.color.border));
        card.setCardBackgroundColor(ContextCompat.getColor(c, R.color.surface));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.bottomMargin = dp(c, 12);
        card.setLayoutParams(lp);
        return card;
    }

    public static LinearLayout vbox(Context c) {
        LinearLayout box = new LinearLayout(c);
        box.setOrientation(LinearLayout.VERTICAL);
        return box;
    }

    public static LinearLayout hbox(Context c) {
        LinearLayout box = new LinearLayout(c);
        box.setOrientation(LinearLayout.HORIZONTAL);
        box.setGravity(Gravity.CENTER_VERTICAL);
        return box;
    }

    public static TextView text(Context c, CharSequence s, float sp, int colorRes, boolean bold) {
        TextView t = new TextView(c);
        t.setText(s);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(ContextCompat.getColor(c, colorRes));
        if (bold) {
            t.setTypeface(t.getTypeface(), Typeface.BOLD);
        }
        return t;
    }

    public static TextView label(Context c, CharSequence s) {
        return text(c, s, 12f, R.color.text_secondary, false);
    }

    public static TextView value(Context c, CharSequence s, float sp) {
        return text(c, s, sp, R.color.text_primary, true);
    }

    /** برچسب کوچک رنگی (مثل «شکست سقف» یا وضعیت بازار). */
    public static TextView pill(Context c, CharSequence s, int fgRes, int bgRes) {
        TextView t = text(c, s, 11.5f, fgRes, false);
        t.setPadding(dp(c, 8), dp(c, 3), dp(c, 8), dp(c, 3));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(ContextCompat.getColor(c, bgRes));
        bg.setCornerRadius(dp(c, 999));
        t.setBackground(bg);
        return t;
    }

    /** ردیف «برچسب در راست، مقدار در چپ». */
    public static LinearLayout kv(Context c, CharSequence label, CharSequence value) {
        LinearLayout row = hbox(c);
        TextView l = label(c, label);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        l.setLayoutParams(lp);
        TextView v = value(c, value, 13.5f);
        row.addView(l);
        row.addView(v);
        row.setPadding(0, dp(c, 4), 0, dp(c, 4));
        return row;
    }

    public static LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    public static LinearLayout.LayoutParams wrapWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    public static LinearLayout.LayoutParams weight(float w) {
        return new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, w);
    }

    public static void pad(View v, Context c, float l, float t, float r, float b) {
        v.setPadding(dp(c, l), dp(c, t), dp(c, r), dp(c, b));
    }

    /** ویو سرصفحه را برای نشستن در RecyclerView آماده می‌کند. */
    public static void asListHeader(View v) {
        Context c = v.getContext();
        androidx.recyclerview.widget.RecyclerView.LayoutParams lp =
                new androidx.recyclerview.widget.RecyclerView.LayoutParams(
                        androidx.recyclerview.widget.RecyclerView.LayoutParams.MATCH_PARENT,
                        androidx.recyclerview.widget.RecyclerView.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(c, 4);
        lp.bottomMargin = dp(c, 4);
        v.setLayoutParams(lp);
    }
}
