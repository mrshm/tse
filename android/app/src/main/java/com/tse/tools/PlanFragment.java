package com.tse.tools;

import androidx.recyclerview.widget.RecyclerView;

/** زبانهٔ برگهٔ سفارش. */
public class PlanFragment extends BaseListFragment {

    @Override
    protected RecyclerView.Adapter<?> buildAdapter() {
        Store s = Store.peek();
        return new PlanAdapter(s.orders(), PlanAdapter.buildHeader(requireContext(), s));
    }

    @Override
    protected boolean hasData() {
        Store s = Store.peek();
        return s.plan != null && s.orders().length() > 0;
    }
}
