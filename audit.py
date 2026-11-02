"""Profitability Audit page — "where the money goes".

Two data sources feed the same views:
  * Upload Square's Sales Summary + Discounts CSV exports (summary-level).
  * Sync live from the Square API (transaction-level: real discount-by-type,
    cash-vs-card from payments, fees per order, and per-item margins).
"""
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from styling import inject_custom_css, render_page_header, style_fig, PALETTE
import audit_core

_MEASURE = {"start": "absolute", "delta": "relative", "subtotal": "total", "total": "total"}


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def _metric_row(kpis):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Net sales", f"£{kpis['net_sales']:,.0f}")
    c2.metric("Transactions", f"{kpis['transactions']:,}")
    c3.metric("Avg sale", f"£{kpis['avg_sale']:,.2f}")
    c4.metric("Discount rate", f"{kpis['discount_rate_pct']:.1f}%")
    c5.metric("Square fees", f"£{kpis['fees_total']:,.0f}")
    c6.metric("Take-home", f"£{kpis['take_home']:,.0f}")


def _bridge_chart(bridge):
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=[_MEASURE.get(b["kind"], "relative") for b in bridge],
        x=[b["label"] for b in bridge],
        y=[b["value"] for b in bridge],
        connector={"line": {"color": PALETTE["border"]}},
        decreasing={"marker": {"color": PALETTE["plum"]}},
        increasing={"marker": {"color": PALETTE["sky"]}},
        totals={"marker": {"color": PALETTE["slate"]}},
        texttemplate="£%{y:,.0f}", textposition="outside",
        textfont=dict(color=PALETTE["muted"], size=11),
    ))
    style_fig(fig)
    fig.update_layout(height=380, title="Gross sales → take-home")
    return fig


def _leakage_chart(disc):
    d = disc.sort_values("amount", ascending=True)
    fig = px.bar(d, x="amount", y="name", orientation="h")
    fig.update_traces(marker_color=PALETTE["slate"], texttemplate="£%{x:,.0f}",
                      textposition="outside", textfont=dict(color=PALETTE["muted"], size=11),
                      cliponaxis=False)
    style_fig(fig)
    fig.update_layout(height=max(300, len(d) * 56), title="Discount spend by type",
                      xaxis_title="£ discounted", yaxis_title="")
    return fig


def _tender_chart(tender):
    fig = go.Figure(go.Pie(
        labels=[t["method"] for t in tender], values=[t["amount"] for t in tender],
        hole=0.62, sort=False,
        marker=dict(colors=[PALETTE["slate"], PALETTE["periwinkle"]],
                    line=dict(color="#FFFFFF", width=2)),
        textinfo="label+percent", textfont=dict(color="#FFFFFF", size=13),
    ))
    style_fig(fig, legend=False)
    fig.update_layout(height=320, title="Cash vs card")
    return fig


def _items_chart(top_items):
    d = top_items.head(10).sort_values("net", ascending=True)
    fig = px.bar(d, x="net", y="name", orientation="h")
    fig.update_traces(marker_color=PALETTE["slate"], texttemplate="£%{x:,.0f}",
                      textposition="outside", textfont=dict(color=PALETTE["muted"], size=11),
                      cliponaxis=False)
    style_fig(fig)
    fig.update_layout(height=max(300, len(d) * 48), title="Top items by net revenue",
                      xaxis_title="£ net", yaxis_title="")
    return fig


def _render_insights(insights):
    for ins in insights:
        {"serious": st.error, "warning": st.warning}.get(ins["level"], st.info)(ins["text"])


# ---------------------------------------------------------------------------
# Shared render of a computed audit result
# ---------------------------------------------------------------------------
def _render(res):
    st.divider()
    _metric_row(res["kpis"])
    st.divider()

    st.subheader("What the numbers are saying")
    _render_insights(res["insights"])
    st.divider()

    left, right = st.columns([3, 2])
    left.plotly_chart(_bridge_chart(res["bridge"]), use_container_width=True)
    right.plotly_chart(_tender_chart(res["tender"]), use_container_width=True)

    if not res["discounts"].empty:
        st.plotly_chart(_leakage_chart(res["discounts"]), use_container_width=True)

    top = res.get("top_items")
    if top is not None and not top.empty:
        st.subheader("Per-item performance")
        st.plotly_chart(_items_chart(top), use_container_width=True)
        show = top.copy()
        rename = {"name": "Item", "units": "Units", "gross": "Gross £",
                  "discount": "Disc £", "net": "Net £",
                  "profit": "Profit £", "margin_pct": "Margin %"}
        for col in ("gross", "discount", "net", "profit"):
            if col in show:
                show[col] = show[col].map("£{:,.2f}".format)
        if "margin_pct" in show:
            show["margin_pct"] = show["margin_pct"].map("{:.1f}%".format)
        st.dataframe(show.rename(columns=rename), use_container_width=True, hide_index=True)

    if not res["discounts"].empty:
        st.subheader("Discount detail")
        table = res["discounts"].rename(columns={
            "name": "Discount", "count": "Uses", "amount": "£ discounted",
            "avg_per_use": "£ per use", "pct_of_discounts": "% of discounts",
            "pct_of_sales": "% of sales"})
        display = table.copy()
        for col in ("£ discounted", "£ per use"):
            display[col] = display[col].map("£{:,.2f}".format)
        display["% of discounts"] = display["% of discounts"].map("{:.1f}%".format)
        if "% of sales" in display:
            display["% of sales"] = display["% of sales"].map("{:.2f}%".format)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button("📥 Download audit detail (CSV)",
                           data=table.to_csv(index=False).encode("utf-8"),
                           file_name="ohh_crumbs_discount_audit.csv", mime="text/csv")


# ---------------------------------------------------------------------------
# Data-source branches
# ---------------------------------------------------------------------------
def _recipe_costs(session):
    try:
        from models import Recipe
        from utils import calculate_recipe_cost
        costs = {}
        for r in session.query(Recipe).all():
            c = calculate_recipe_cost(session, r.id)
            if c and c > 0:
                costs[r.name] = c
        return costs
    except Exception:
        return {}


def _csv_audit():
    st.caption("Square → Reports → Sales summary and Discounts, exported as CSV.")
    col_a, col_b = st.columns(2)
    summary_file = col_a.file_uploader("Sales Summary export (.csv)", type=["csv"], key="audit_summary")
    discounts_file = col_b.file_uploader("Discounts export (.csv)", type=["csv"], key="audit_discounts")

    if not (summary_file and discounts_file):
        st.info("⬆️ Add both exports to run the audit.")
        return
    try:
        summary = audit_core.load_sales_summary(summary_file)
        discounts = audit_core.load_discounts(discounts_file)
        res = audit_core.compute_audit(summary, discounts)
    except Exception as e:
        st.error(f"Couldn't read those files: {e}")
        return
    _render(res)


def _live_audit():
    from square_api import SquareAPI
    from database import get_session, close_session
    import square_sync
    from models import SalesOrder, SyncLog

    api = SquareAPI()
    session = get_session()
    try:
        configured = bool(api.is_configured and api.location_id)

        if configured:
            last = session.query(SyncLog).order_by(SyncLog.started_at.desc()).first()
            if last:
                st.caption(f"Last sync: {last.started_at:%Y-%m-%d %H:%M} · "
                           f"{last.orders_synced} new orders, {last.payments_synced} new payments.")
            col1, col2, col3 = st.columns([2, 2, 1])
            default_start = (datetime.utcnow() - timedelta(days=365)).date()
            start_date = col1.date_input("From", value=default_start, key="audit_from")
            end_date = col2.date_input("To", value=datetime.utcnow().date(), key="audit_to")
            col3.write("")
            if col3.button("🔄 Sync now", use_container_width=True):
                bar = st.progress(0.0, text="Starting…")
                try:
                    counts = square_sync.sync(
                        session, api.client, api.location_id,
                        datetime.combine(start_date, datetime.min.time()),
                        datetime.combine(end_date, datetime.max.time()),
                        progress=lambda f, m: bar.progress(f, text=m),
                    )
                    st.success(f"Synced {counts['orders_new']} new orders and "
                               f"{counts['payments_new']} new payments "
                               f"({counts['orders_seen']} orders seen).")
                except Exception as e:
                    st.error(f"Sync failed: {e}")
        else:
            st.caption("Square isn't connected in the app — showing already-synced data. "
                       "Connect on the 🔗 Square Setup page (or run `sync_cli.py`) to pull fresh data.")

        has_data = session.query(SalesOrder.id).first() is not None
        if not has_data:
            st.info("No synced sales yet — connect Square and sync, or run `sync_cli.py`.")
            return

        res = audit_core.compute_audit_live_from_db(session, recipe_costs=_recipe_costs(session))
        _render(res)
    finally:
        close_session(session)


def show_audit():
    inject_custom_css()
    render_page_header("Profitability Audit", "WHERE THE MONEY GOES")
    st.write("See discount leakage, cash-vs-card split and fee drag — and, on the live "
             "feed, per-item margins.")

    source = st.radio("Data source", ["Live Square sync", "Upload CSV exports"],
                      horizontal=True, label_visibility="collapsed")
    st.divider()
    if source == "Upload CSV exports":
        _csv_audit()
    else:
        _live_audit()
