package com.tse.tools;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Environment;
import android.view.View;

import androidx.test.core.app.ActivityScenario;

import com.google.android.material.bottomnavigation.BottomNavigationView;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * رندر واقعی صفحه‌ها با گرافیک بومی Robolectric و ذخیرهٔ تصویر،
 * تا بدون گوشی هم بتوانیم ظاهر را ببینیم.
 */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 34, qualifiers = "fa-rIR-w411dp-h891dp-xxhdpi")
public class ScreenshotTest {

    private static final int W = 1080;
    private static final int H = 2200;

    @Before
    public void seedData() throws Exception {
        File dir = new File(RuntimeEnvironment.getApplication().getFilesDir(), "data");
        if (!dir.exists()) {
            dir.mkdirs();
        }
        for (String name : new String[]{"scan_latest.json", "plan_latest.json", "risk_latest.json"}) {
            InputStream in = getClass().getClassLoader().getResourceAsStream("data/" + name);
            try (OutputStream out = new FileOutputStream(new File(dir, name))) {
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) > 0) {
                    out.write(buf, 0, n);
                }
            }
            if (in != null) {
                in.close();
            }
        }
    }

    @Test
    public void capture() {
        shoot("");
    }

    /** همان صفحه‌ها در حالت شب، تا از تم تاریک هم مطمئن شویم. */
    @Test
    @Config(sdk = 34, qualifiers = "fa-rIR-w411dp-h891dp-night-xxhdpi")
    public void captureNight() {
        shoot("-dark");
    }

    private void shoot(String suffix) {
        File out = new File("build/screenshots");
        if (!out.exists() && !out.mkdirs()) {
            throw new IllegalStateException("cannot create " + out);
        }
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(a -> {
                BottomNavigationView nav = a.findViewById(R.id.nav);
                Object[][] tabs = {
                        {R.id.nav_today, "today"},
                        {R.id.nav_scan, "scan"},
                        {R.id.nav_plan, "plan"},
                        {R.id.nav_journal, "journal"},
                        {R.id.nav_risk, "risk"},
                };
                for (Object[] tab : tabs) {
                    nav.setSelectedItemId((Integer) tab[0]);
                    a.getSupportFragmentManager().executePendingTransactions();
                    capture(a.getWindow().getDecorView(), new File(out, tab[1] + suffix + ".png"));
                }
            });
        }
    }

    private static void capture(View root, File file) {
        int w = View.MeasureSpec.makeMeasureSpec(W, View.MeasureSpec.EXACTLY);
        int h = View.MeasureSpec.makeMeasureSpec(H, View.MeasureSpec.EXACTLY);
        root.measure(w, h);
        root.layout(0, 0, W, H);
        Bitmap bmp = Bitmap.createBitmap(W, H, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bmp);
        root.draw(canvas);
        try (FileOutputStream fos = new FileOutputStream(file)) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, fos);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
