package com.tse.tools;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.DividerItemDecoration;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

/** پایهٔ همهٔ زبانه‌های فهرستی: فهرست + حالت خالی + کشیدن برای تازه‌سازی. */
public abstract class BaseListFragment extends Fragment implements MainActivity.Refreshable {

    protected RecyclerView list;
    protected SwipeRefreshLayout swipe;
    protected View empty;

    protected abstract RecyclerView.Adapter<?> buildAdapter();

    protected abstract boolean hasData();

    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_list, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        list = view.findViewById(R.id.list);
        swipe = view.findViewById(R.id.swipe);
        empty = view.findViewById(R.id.empty);

        list.setLayoutManager(new LinearLayoutManager(requireContext()));
        list.addItemDecoration(new DividerItemDecoration(requireContext(),
                DividerItemDecoration.VERTICAL));
        list.setAdapter(buildAdapter());

        swipe.setOnRefreshListener(() -> {
            swipe.setRefreshing(false);
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).startQuickSync();
            }
        });
        updateEmpty();
    }

    protected void updateEmpty() {
        boolean any = hasData();
        empty.setVisibility(any ? View.GONE : View.VISIBLE);
        list.setVisibility(any ? View.VISIBLE : View.GONE);
    }

    @Override
    public void onDataChanged() {
        if (list != null) {
            list.setAdapter(buildAdapter());
            updateEmpty();
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        onDataChanged();
    }
}
