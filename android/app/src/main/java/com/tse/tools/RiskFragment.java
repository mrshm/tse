package com.tse.tools;

import androidx.recyclerview.widget.RecyclerView;

/** زبانهٔ ریسک. */
public class RiskFragment extends BaseListFragment {

    @Override
    protected RecyclerView.Adapter<?> buildAdapter() {
        Store s = Store.peek();
        return new RiskAdapter(s.riskLadder(), RiskAdapter.buildHeader(requireContext(), s));
    }

    @Override
    protected boolean hasData() {
        return Store.peek().risk != null;
    }
}
