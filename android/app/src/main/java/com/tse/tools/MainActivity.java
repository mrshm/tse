package com.tse.tools;

import android.content.Context;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.fragment.app.Fragment;
import androidx.fragment.app.FragmentManager;
import androidx.fragment.app.FragmentTransaction;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.google.android.material.dialog.MaterialAlertDialogBuilder;
import com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton;
import com.google.android.material.progressindicator.LinearProgressIndicator;
import com.google.android.material.snackbar.Snackbar;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/**
 * اپ بومی بورس تهران: هیچ WebView ای در کار نیست.
 * کدهای پایتون پروژه داخل گوشی اجرا می‌شوند و این Activity فقط خروجی JSON آن‌ها
 * را با ویجت‌های اندروید نمایش می‌دهد.
 */
public class MainActivity extends AppCompatActivity {

    /** فرگمنت‌هایی که بعد از به‌روزرسانی داده را از نو می‌خوانند. */
    public interface Refreshable {
        void onDataChanged();
    }

    private BottomNavigationView nav;
    private ExtendedFloatingActionButton fab;
    private MaterialToolbar toolbar;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile boolean syncing = false;
    private androidx.appcompat.app.AlertDialog syncDialog;
    private TextView dialogStep;
    private TextView dialogDetail;
    private LinearProgressIndicator dialogBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        toolbar = findViewById(R.id.toolbar);
        toolbar.setOnMenuItemClickListener(this::onMenu);
        toolbar.setSubtitle("آماده");

        nav = findViewById(R.id.nav);
        nav.setOnItemSelectedListener(item -> {
            select(item.getItemId());
            return true;
        });

        fab = findViewById(R.id.fab);
        fab.setOnClickListener(v -> startSync("quick"));

        if (savedInstanceState == null) {
            nav.setSelectedItemId(R.id.nav_today);
        }
        refreshSubtitle();
    }

    private boolean onMenu(@NonNull MenuItem item) {        if (item.getItemId() == R.id.action_full) {
            startSync("full");
            return true;
        }
        return false;
    }

    // ------------------------------------------------------------ fragments

    private Fragment fragmentFor(int id) {
        String tag = "f" + id;
        Fragment existing = getSupportFragmentManager().findFragmentByTag(tag);
        if (existing != null) {
            return existing;
        }
        if (id == R.id.nav_scan) {
            return new ScanFragment();
        }
        if (id == R.id.nav_plan) {
            return new PlanFragment();
        }
        if (id == R.id.nav_journal) {
            return new JournalFragment();
        }
        if (id == R.id.nav_risk) {
            return new RiskFragment();
        }
        return new TodayFragment();
    }

    private void select(int id) {
        FragmentManager fm = getSupportFragmentManager();
        FragmentTransaction ft = fm.beginTransaction();
        for (Fragment f : fm.getFragments()) {
            ft.hide(f);
        }
        String tag = "f" + id;
        Fragment target = fm.findFragmentByTag(tag);
        if (target == null) {
            target = fragmentFor(id);
            ft.add(R.id.container, target, tag);
        } else {
            ft.show(target);
        }
        ft.commit();
    }

    private void refreshSubtitle() {
        String at = Store.peek().generatedAt();
        if (at.isEmpty()) {
            Store.get(this);
            at = Store.peek().generatedAt();
        }
        if (at.isEmpty()) {
            toolbar.setSubtitle(R.string.no_data_short);
            return;
        }
        // «۱۴۰۵/۰۸/۱۳ ۱۲:۵۳» → فقط ساعت، وگرنه زیرنویس سرصفحه بریده می‌شود
        int space = at.indexOf(' ');
        String time = space > 0 ? at.substring(space + 1).trim() : at;
        toolbar.setSubtitle(getString(R.string.last_update) + " " + time);
    }

    private void onDataChanged() {
        Store.get(this);
        refreshSubtitle();
        for (Fragment f : getSupportFragmentManager().getFragments()) {
            if (f instanceof Refreshable) {
                ((Refreshable) f).onDataChanged();
            }
        }
    }

    // ----------------------------------------------------------------- sync

    private File statusFile() {
        return new File(getFilesDir(), "status.json");
    }

    /** برای «کشیدن برای تازه‌سازی» در فهرست‌ها. */
    public void startQuickSync() {
        startSync("quick");
    }

    private void startSync(String mode) {
        if (syncing) {
            return;
        }
        syncing = true;
        fab.setEnabled(false);
        fab.setText(R.string.syncing);

        View body = getLayoutInflater().inflate(R.layout.dialog_sync, null);
        dialogStep = body.findViewById(R.id.step);
        dialogDetail = body.findViewById(R.id.detail);
        dialogBar = body.findViewById(R.id.bar);
        dialogDetail.setText(mode.equals("full") ? R.string.sync_full_hint : R.string.sync_hint);

        syncDialog = new MaterialAlertDialogBuilder(this)
                .setTitle(R.string.sync_title)
                .setView(body)
                .setCancelable(false)
                .create();
        syncDialog.show();

        new Thread(() -> {
            try {
                if (!Python.isStarted()) {
                    Python.start(new AndroidPlatform(getApplicationContext()));
                }
                PyObject app = Python.getInstance().getModule("tse_app");
                app.callAttr("set_home", getFilesDir().getAbsolutePath());
                app.callAttr("set_status_path", statusFile().getAbsolutePath());
                app.callAttr("run_sync", mode);
            } catch (Throwable t) {
                writeFailure(t.toString());
            }
            ui.post(this::onSyncFinished);
        }, "tse-sync").start();

        ui.postDelayed(pollStatus, 500);
    }

    private final Runnable pollStatus = new Runnable() {
        @Override
        public void run() {
            JSONObject s = readStatus();
            if (s != null) {
                String step = s.optString("step", "");
                if (!step.isEmpty() && dialogStep != null) {
                    dialogStep.setText(step);
                    dialogBar.setProgress(s.optInt("pct", 0), true);
                }
            }
            if (syncing) {
                ui.postDelayed(this, 600);
            }
        }
    };

    private void onSyncFinished() {
        syncing = false;
        fab.setEnabled(true);
        fab.setText(R.string.sync);

        JSONObject s = readStatus();
        boolean failed = s != null && s.has("error") && !s.isNull("error");
        if (failed) {
            String err = s.optString("error", "?");
            if (syncDialog != null) {
                dialogStep.setText(R.string.sync_failed);
                dialogDetail.setText(err);
                dialogBar.setVisibility(View.GONE);
                syncDialog.setCancelable(true);
                syncDialog.setButton(androidx.appcompat.app.AlertDialog.BUTTON_POSITIVE,
                        getString(R.string.close), (d, w) -> d.dismiss());
                syncDialog.setButton(androidx.appcompat.app.AlertDialog.BUTTON_NEGATIVE,
                        getString(R.string.sync_retry), (d, w) -> {
                            d.dismiss();
                            startSync("quick");
                        });
            }
            return;
        }

        if (syncDialog != null && syncDialog.isShowing()) {
            syncDialog.dismiss();
        }
        onDataChanged();
        View root = findViewById(R.id.root);
        Snackbar.make(root, R.string.sync_done, Snackbar.LENGTH_SHORT)
                .setAnchorView(fab)
                .show();
    }

    private void writeFailure(String msg) {
        try (FileOutputStream fos = new FileOutputStream(statusFile());
             OutputStreamWriter w = new OutputStreamWriter(fos, StandardCharsets.UTF_8)) {
            JSONObject o = new JSONObject();
            o.put("running", false);
            o.put("done", false);
            o.put("error", msg);
            o.put("step", "خطا");
            o.put("pct", 0);
            w.write(o.toString());
        } catch (Exception ignored) {
        }
    }

    private JSONObject readStatus() {
        File f = statusFile();
        if (!f.exists()) {
            return null;
        }
        try (FileInputStream in = new FileInputStream(f)) {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
            return new JSONObject(new String(bos.toByteArray(), StandardCharsets.UTF_8));
        } catch (Exception e) {
            return null;
        }
    }

    @Override
    protected void onDestroy() {
        ui.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
