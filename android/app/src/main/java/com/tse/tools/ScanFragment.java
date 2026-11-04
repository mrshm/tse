package com.tse.tools;

import androidx.recyclerview.widget.RecyclerView;

/** زبانهٔ اسکن: خلاصهٔ بازار + فهرست نمادهای برتر. */
public class ScanFragment extends BaseListFragment {

    @Override
    protected RecyclerView.Adapter<?> buildAdapter() {
        Store s = Store.peek();
        return new ScanAdapter(s.rows(), ScanAdapter.buildHeader(requireContext(), s));
    }

    @Override
    protected boolean hasData() {
        return Store.peek().scan != null && Store.peek().rows().length() > 0;
    }
}
