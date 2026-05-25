"""
Inventory Management Page — stock levels, alerts, and reorder recommendations.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from services.inventory_service import InventoryService


def render_inventory():
    """Render the inventory management page."""
    service = InventoryService()

    st.markdown("## 📦 Inventory Management")
    st.markdown("---")

    # ── Summary KPIs ───────────────────────────────────────────────────────
    summary = service.get_stock_summary()
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Value</div>
            <div class="kpi-value">${summary['total_inventory_value']:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Items</div>
            <div class="kpi-value">{summary['total_items']:,}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card kpi-alert">
            <div class="kpi-label">Critical Items</div>
            <div class="kpi-value">{summary['critical_items']}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #f59e0b;">
            <div class="kpi-label">Low Stock Items</div>
            <div class="kpi-value">{summary['low_stock_items']}</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #10b981;">
            <div class="kpi-label">Healthy Items</div>
            <div class="kpi-value">{summary['healthy_items']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────────────────
    overview = service.get_inventory_overview()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        categories = ["All"] + sorted(overview["category"].unique().tolist())
        sel_cat = st.selectbox("Filter by Category", categories, key="inv_cat")
    with col_f2:
        warehouses = ["All"] + sorted(overview["warehouse"].unique().tolist())
        sel_wh = st.selectbox("Filter by Warehouse", warehouses, key="inv_wh")
    with col_f3:
        statuses = ["All", "🔴 Critical", "🟡 Low", "🟡 Approaching Reorder", "🟢 Healthy"]
        sel_status = st.selectbox("Filter by Status", statuses, key="inv_status")

    filtered = overview.copy()
    if sel_cat != "All":
        filtered = filtered[filtered["category"] == sel_cat]
    if sel_wh != "All":
        filtered = filtered[filtered["warehouse"] == sel_wh]
    if sel_status != "All":
        filtered = filtered[filtered["stock_status"] == sel_status]

    # ── Charts Row ─────────────────────────────────────────────────────────
    chart1, chart2 = st.columns(2)

    with chart1:
        cat_inv = service.get_category_inventory()
        fig = px.bar(cat_inv, x="category", y="total_value",
                     title="Inventory Value by Category",
                     color="category",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart2:
        wh_util = service.get_warehouse_utilization()
        fig = px.bar(wh_util, x="warehouse", y="total_stock",
                     title="Warehouse Stock Levels",
                     color="total_value",
                     color_continuous_scale="Plasma")
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis_tickangle=-45,
            margin=dict(l=20, r=20, t=50, b=80),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Inventory Table ────────────────────────────────────────────────────
    st.markdown("### 📋 Inventory Details")

    display_cols = [
        "product_name", "category", "warehouse", "current_stock",
        "safety_stock", "reorder_point", "stock_status", "inventory_value"
    ]

    def color_status(val):
        if "Critical" in str(val):
            return "background-color: rgba(239, 68, 68, 0.25); color: #fca5a5;"
        elif "Low" in str(val) or "Approaching" in str(val):
            return "background-color: rgba(245, 158, 11, 0.25); color: #fcd34d;"
        elif "Healthy" in str(val):
            return "background-color: rgba(16, 185, 129, 0.25); color: #6ee7b7;"
        return ""

    styled = filtered[display_cols].style.map(
        color_status, subset=["stock_status"]
    ).format({"inventory_value": "${:,.0f}", "current_stock": "{:,}", "safety_stock": "{:,}"})

    st.dataframe(styled, use_container_width=True, height=400)

    # ── Stockout Insights Panel ────────────────────────────────────────────
    st.markdown("### 🚨 Stockout Risk Alerts")

    critical = filtered[filtered["stock_status"].str.contains("Critical")].head(10)
    if critical.empty:
        st.success("✅ No critical inventory alerts at this time.")
    else:
        for _, row in critical.iterrows():
            days_est = service.estimate_days_until_stockout(row["product_id"])
            days_str = f"{days_est:.0f} days" if days_est is not None else "N/A"
            reorder = service.get_reorder_recommendation(row["product_id"])

            st.markdown(f"""
            <div class="insight-card" style="border-left: 4px solid #ef4444;">
                <strong>🔴 {row['product_name']}</strong> — {row['warehouse']}<br>
                Current: <strong>{row['current_stock']:,}</strong> | Safety: {row['safety_stock']:,} |
                Projected stockout in <strong>{days_str}</strong><br>
                💡 {reorder['message']}
            </div>
            """, unsafe_allow_html=True)

    # Download button
    st.markdown("---")
    csv = filtered[display_cols].to_csv(index=False)
    st.download_button("📥 Download Inventory Report (CSV)", csv,
                       "inventory_report.csv", "text/csv")
