"""
Dashboard Page — Executive KPI Dashboard with charts and metrics.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from database.database import get_engine


def render_dashboard():
    """Render the executive dashboard page."""
    engine = get_engine()

    st.markdown("## 📊 Executive Dashboard")
    st.markdown("---")

    # ── KPI Cards ──────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # Total Revenue
    rev_df = pd.read_sql("SELECT SUM(revenue) as total FROM sales", engine)
    total_revenue = rev_df["total"].iloc[0] or 0

    # Total Orders
    orders_df = pd.read_sql("SELECT COUNT(*) as total FROM purchase_orders", engine)
    total_orders = orders_df["total"].iloc[0] or 0

    # Inventory Value
    inv_df = pd.read_sql(
        "SELECT SUM(i.current_stock * p.unit_price) as val FROM inventory i JOIN products p ON i.product_id = p.product_id",
        engine
    )
    inv_value = inv_df["val"].iloc[0] or 0

    # Active Suppliers
    sup_df = pd.read_sql("SELECT COUNT(DISTINCT supplier_id) as cnt FROM suppliers", engine)
    active_sups = sup_df["cnt"].iloc[0] or 0

    # Delayed Shipments
    delay_df = pd.read_sql("SELECT COUNT(*) as cnt FROM shipments WHERE status = 'Delayed'", engine)
    delayed = delay_df["cnt"].iloc[0] or 0

    # Forecast Accuracy (use stored R² from model if available)
    try:
        import joblib, os
        metrics_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "model_metrics.pkl")
        if os.path.exists(metrics_path):
            metrics = joblib.load(metrics_path)
            best = metrics.get("best_model", "")
            accuracy = metrics.get(best, {}).get("R2", 0) * 100
        else:
            accuracy = 0
    except Exception:
        accuracy = 0

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">${total_revenue:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{total_orders:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Inventory Value</div>
            <div class="kpi-value">${inv_value:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Forecast Accuracy</div>
            <div class="kpi-value">{accuracy:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Active Suppliers</div>
            <div class="kpi-value">{active_sups}</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class="kpi-card kpi-alert">
            <div class="kpi-label">Delayed Shipments</div>
            <div class="kpi-value">{delayed}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Revenue Trend + Monthly Sales ───────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        rev_trend = pd.read_sql("""
            SELECT strftime('%Y-%m', sale_date) as month, SUM(revenue) as revenue
            FROM sales GROUP BY month ORDER BY month
        """, engine)
        fig = px.area(rev_trend, x="month", y="revenue",
                      title="Revenue Trend",
                      color_discrete_sequence=["#6366f1"])
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis_title="", yaxis_title="Revenue ($)",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        monthly_sales = pd.read_sql("""
            SELECT strftime('%Y-%m', sale_date) as month,
                   SUM(quantity_sold) as units_sold
            FROM sales GROUP BY month ORDER BY month
        """, engine)
        fig = px.bar(monthly_sales, x="month", y="units_sold",
                     title="Monthly Units Sold",
                     color_discrete_sequence=["#8b5cf6"])
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis_title="", yaxis_title="Units",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Inventory + Supplier ────────────────────────────────────────
    c3, c4 = st.columns(2)

    with c3:
        cat_inv = pd.read_sql("""
            SELECT p.category,
                   SUM(i.current_stock * p.unit_price) as value
            FROM inventory i JOIN products p ON i.product_id = p.product_id
            GROUP BY p.category ORDER BY value DESC
        """, engine)
        fig = px.pie(cat_inv, values="value", names="category",
                     title="Inventory Distribution by Category",
                     color_discrete_sequence=px.colors.qualitative.Set2,
                     hole=0.45)
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        sup_perf = pd.read_sql("""
            SELECT supplier_name, on_time_delivery_rate, quality_score, rating
            FROM suppliers ORDER BY rating DESC LIMIT 10
        """, engine)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=sup_perf["supplier_name"],
            y=sup_perf["on_time_delivery_rate"] * 100,
            name="On-Time %",
            marker_color="#10b981"
        ))
        fig.add_trace(go.Bar(
            x=sup_perf["supplier_name"],
            y=sup_perf["quality_score"] * 20,
            name="Quality (scaled)",
            marker_color="#f59e0b"
        ))
        fig.update_layout(
            title="Top 10 Supplier Performance",
            barmode="group",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis_tickangle=-45,
            margin=dict(l=20, r=20, t=50, b=80),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Warehouse Utilization + Shipment Status ─────────────────────
    c5, c6 = st.columns(2)

    with c5:
        wh_df = pd.read_sql("""
            SELECT warehouse, SUM(current_stock) as stock
            FROM inventory GROUP BY warehouse ORDER BY stock DESC
        """, engine)
        fig = px.bar(wh_df, x="stock", y="warehouse", orientation="h",
                     title="Warehouse Utilization",
                     color="stock",
                     color_continuous_scale="Viridis")
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            yaxis_title="", xaxis_title="Total Stock",
            margin=dict(l=20, r=20, t=50, b=20),
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        ship_status = pd.read_sql("""
            SELECT status, COUNT(*) as count
            FROM shipments GROUP BY status
        """, engine)
        colors = {"Delivered": "#10b981", "In Transit": "#3b82f6",
                  "Delayed": "#ef4444", "Returned": "#f59e0b"}
        fig = px.pie(ship_status, values="count", names="status",
                     title="Shipment Status Breakdown",
                     color="status",
                     color_discrete_map=colors,
                     hole=0.4)
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Top Products + Category Contribution ────────────────────────
    c7, c8 = st.columns(2)

    with c7:
        top_prods = pd.read_sql("""
            SELECT p.product_name, SUM(s.revenue) as revenue
            FROM sales s JOIN products p ON s.product_id = p.product_id
            GROUP BY p.product_id ORDER BY revenue DESC LIMIT 10
        """, engine)
        fig = px.bar(top_prods, x="revenue", y="product_name", orientation="h",
                     title="Top 10 Products by Revenue",
                     color_discrete_sequence=["#ec4899"])
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            yaxis_title="", xaxis_title="Revenue ($)",
            margin=dict(l=20, r=20, t=50, b=20),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with c8:
        cat_rev = pd.read_sql("""
            SELECT p.category, SUM(s.revenue) as revenue
            FROM sales s JOIN products p ON s.product_id = p.product_id
            GROUP BY p.category ORDER BY revenue DESC
        """, engine)
        fig = px.treemap(cat_rev, path=["category"], values="revenue",
                         title="Category Revenue Contribution",
                         color="revenue",
                         color_continuous_scale="RdYlGn")
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
