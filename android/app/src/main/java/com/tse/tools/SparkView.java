package com.tse.tools;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.View;

import androidx.core.content.ContextCompat;

/** نمودار خطی کوچک قیمت (sparkline) برای ردیف‌های اسکن. */
public class SparkView extends View {

    private float[] values;
    private double last;
    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path path = new Path();
    private final Path area = new Path();

    public SparkView(Context c, AttributeSet a) {
        super(c, a);
        line.setStyle(Paint.Style.STROKE);
        line.setStrokeWidth(Ui.dp(c, 1.6f));
        line.setStrokeCap(Paint.Cap.ROUND);
        line.setStrokeJoin(Paint.Join.ROUND);
        fill.setStyle(Paint.Style.FILL);
        setColor(R.color.text_muted);
    }

    public void setColor(int colorRes) {
        int c = ContextCompat.getColor(getContext(), colorRes);
        line.setColor(c);
        fill.setColor(c);
        fill.setAlpha(28);
        invalidate();
    }

    public void setData(float[] vals, double lastPrice) {
        this.values = vals;
        this.last = lastPrice;
        invalidate();
    }

    public void setData(float[] vals) {
        setData(vals, vals.length > 0 ? vals[vals.length - 1] : 0);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (values == null || values.length < 2) {
            return;
        }
        float w = getWidth();
        float h = getHeight();
        float pad = Ui.dp(getContext(), 2);
        float min = Float.MAX_VALUE, max = -Float.MAX_VALUE;
        for (float v : values) {
            if (v < min) min = v;
            if (v > max) max = v;
        }
        if (max - min < 1e-6f) {
            max = min + 1f;
        }
        float usableW = w - 2 * pad;
        float usableH = h - 2 * pad;

        path.reset();
        area.reset();
        for (int i = 0; i < values.length; i++) {
            float x = pad + usableW * i / (values.length - 1f);
            float y = pad + usableH * (1f - (values[i] - min) / (max - min));
            if (i == 0) {
                path.moveTo(x, y);
                area.moveTo(x, h);
                area.lineTo(x, y);
            } else {
                path.lineTo(x, y);
                area.lineTo(x, y);
            }
        }
        area.lineTo(pad + usableW, h);
        area.close();
        canvas.drawPath(area, fill);
        canvas.drawPath(path, line);
    }
}
