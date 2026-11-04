package com.tse.tools;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import android.app.Activity;
import android.view.View;
import android.widget.TextView;

import androidx.test.core.app.ActivityScenario;

import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/** آزمون دودی رابط کاربری: Activity بالا می‌آید، زبانه‌ها ساخته می‌شوند، دکمه دیده می‌شود. */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34)
public class MainActivityTest {

    @Before
    public void seedData() throws Exception {
        File dir = new File(RuntimeEnvironment.getApplication().getFilesDir(), "data");
        assertTrue(dir.exists() || dir.mkdirs());
        for (String name : new String[]{"scan_latest.json", "plan_latest.json", "risk_latest.json"}) {
            InputStream in = getClass().getClassLoader().getResourceAsStream("data/" + name);
            assertNotNull("missing test resource " + name, in);
            try (OutputStream out = new FileOutputStream(new File(dir, name))) {
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) > 0) {
                    out.write(buf, 0, n);
                }
            }
            in.close();
        }
    }

    @Test
    public void launchesAndShowsUpdateButton() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(a -> {
                ExtendedFloatingActionButton fab = a.findViewById(R.id.fab);
                assertNotNull(fab);
                assertEquals(View.VISIBLE, fab.getVisibility());
                assertEquals("به‌روزرسانی", fab.getText().toString());
                assertEquals(View.VISIBLE, fab.isShown() ? View.VISIBLE : View.GONE);
            });
        }
    }

    @Test
    public void everyTabRenders() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(a -> {
                BottomNavigationView nav = a.findViewById(R.id.nav);
                int[] ids = {R.id.nav_today, R.id.nav_scan, R.id.nav_plan,
                        R.id.nav_journal, R.id.nav_risk};
                for (int id : ids) {
                    nav.setSelectedItemId(id);
                    FragmentCheck.check(a);
                }
            });
        }
    }

    private static final class FragmentCheck {
        static void check(Activity a) {
            androidx.fragment.app.Fragment f =
                    ((androidx.fragment.app.FragmentActivity) a)
                            .getSupportFragmentManager().getFragments().get(0);
            assertNotNull("no fragment added", f);
            View v = f.getView();
            assertNotNull("fragment view is null for " + f.getClass().getSimpleName(), v);
            assertTrue(f.getClass().getSimpleName() + " is hidden",
                    v.getVisibility() == View.VISIBLE);
            TextView any = findText(v);
            assertNotNull("empty fragment: " + f.getClass().getSimpleName(), any);
        }

        static TextView findText(View v) {
            if (v instanceof TextView && ((TextView) v).getText().length() > 0) {
                return (TextView) v;
            }
            if (v instanceof android.view.ViewGroup) {
                android.view.ViewGroup g = (android.view.ViewGroup) v;
                for (int i = 0; i < g.getChildCount(); i++) {
                    TextView t = findText(g.getChildAt(i));
                    if (t != null) {
                        return t;
                    }
                }
            }
            return null;
        }
    }
}
