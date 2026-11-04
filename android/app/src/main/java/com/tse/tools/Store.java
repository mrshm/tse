package com.tse.tools;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;

/** خواندن خروجی‌های JSON که کد پایتون روی گوشی می‌نویسد. */
public final class Store {

    private static Store instance;

    public JSONObject scan;
    public JSONObject plan;
    public JSONObject risk;
    public JSONObject journal;

    public static synchronized Store get(Context ctx) {
        if (instance == null) {
            instance = new Store();
        }
        instance.reload(ctx);
        return instance;
    }

    public static synchronized Store peek() {
        if (instance == null) {
            instance = new Store();
        }
        return instance;
    }

    public void reload(Context ctx) {
        File dir = new File(ctx.getFilesDir(), "data");
        scan = read(new File(dir, "scan_latest.json"));
        plan = read(new File(dir, "plan_latest.json"));
        risk = read(new File(dir, "risk_latest.json"));
        journal = read(new File(dir, "journal.json"));
    }

    public boolean hasAny() {
        return scan != null;
    }

    public static JSONObject read(File f) {
        if (!f.exists()) {
            return null;
        }
        try (FileInputStream in = new FileInputStream(f)) {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            int n;
            while ((n = in.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
            return new JSONObject(new String(bos.toByteArray(), StandardCharsets.UTF_8));
        } catch (Exception e) {
            return null;
        }
    }

    // ------------------------------------------------------------- accessors

    public JSONObject market() {
        return scan == null ? null : scan.optJSONObject("market");
    }

    public JSONObject breadth() {
        return scan == null ? null : scan.optJSONObject("breadth");
    }

    public JSONArray rows() {
        return scan == null ? new JSONArray() : scan.optJSONArray("rows");
    }

    public JSONArray orders() {
        return plan == null ? new JSONArray() : plan.optJSONArray("orders");
    }

    public JSONObject planSummary() {
        return plan == null ? null : plan.optJSONObject("summary");
    }

    public JSONArray openPositions() {
        return journal == null ? new JSONArray() : journal.optJSONArray("positions");
    }

    public JSONArray closedPositions() {
        return journal == null ? new JSONArray() : journal.optJSONArray("closed");
    }

    public JSONObject riskSummary() {
        return risk == null ? null : risk.optJSONObject("summary");
    }

    public JSONArray riskLadder() {
        return risk == null ? new JSONArray() : risk.optJSONArray("ladder");
    }

    public String generatedAt() {
        for (JSONObject o : new JSONObject[]{scan, plan, risk}) {
            if (o != null && o.has("generated_at_fa")) {
                return Fmt.faDigits(o.optString("generated_at_fa"));
            }
        }
        return "";
    }
}
