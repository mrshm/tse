package com.tse.tools;

import android.view.View;

import androidx.recyclerview.widget.RecyclerView;

/** زبانهٔ دفتر معاملات. */
public class JournalFragment extends BaseListFragment {

    @Override
    protected RecyclerView.Adapter<?> buildAdapter() {
        Store s = Store.peek();
        return new JournalAdapter(s.openPositions(), s.closedPositions(),
                JournalAdapter.buildHeader(requireContext(), s));
    }

    @Override
    protected boolean hasData() {
        return true; // خلاصهٔ دفتر همیشه نمایش داده می‌شود
    }
}
