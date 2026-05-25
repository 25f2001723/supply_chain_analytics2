"""
Logistics Analytics Page — shipment tracking, delays, costs, and route analysis.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from services.shipment_service import ShipmentService


def render_logistics():
    """Render the logistics analytics page."""
    service = ShipmentService()

    st.markdown("## 🚚 Logistics & Shipment Analytics")
    st.markdown("---")

    # ── KPIs ───────────────────────────────────────────────────────────────
    summary = service.get_shipment_summary()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Shipments</div>
            <div class="kpi-value">{summary['total_shipments']:,}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Cost</div>
            <div class="kpi-value">${summary['total_cost']:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Avg Transit Time</div>
            <div class="kpi-value">{summary['avg_delivery_days']:.1f} days</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #3b82f6;">
            <div class="kpi-label">In Transit</div>
            <div class="kpi-value">{summary['in_transit']:,}</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="kpi-card kpi-alert">
            <div class="kpi-label">Delayed</div>
            <div class="kpi-value">{summary['delayed']:,}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────────────────
    shipments = service.get_all_shipments()
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        status_opts = ["All"] + sorted(shipments["status"].unique().tolist())
        sel_status = st.selectbox("Filter by Status", status_opts, key="log_status")
    with fc2:
        origin_opts = ["All"] + sorted(shipments["origin"].unique().tolist())
        sel_origin = st.selectbox("Filter by Origin", origin_opts, key="log_origin")
    with fc3:
        dest_opts = ["All"] + sorted(shipments["destination"].unique().tolist())
        sel_dest = st.selectbox("Filter by Destination", dest_opts, key="log_dest")

    filtered = shipments.copy()
    if sel_status != "All":
        filtered = filtered[filtered["status"] == sel_status]
    if sel_origin != "All":
        filtered = filtered[filtered["origin"] == sel_origin]
    if sel_dest != "All":
        filtered = filtered[filtered["destination"] == sel_dest]

    # ── Charts Row 1 ──────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        status_df = service.get_status_breakdown()
        colors = {"Delivered": "#10b981", "In Transit": "#3b82f6",
                  "Delayed": "#ef4444", "Returned": "#f59e0b"}
        fig = px.pie(status_df, values="count", names="status",
                     title="Shipment Status Distribution",
                     color="status", color_discrete_map=colors,
                     hole=0.45)
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with ch2:
        cost_trend = service.get_monthly_cost_trend()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cost_trend["month"], y=cost_trend["total_cost"],
            mode="lines+markers", name="Total Cost",
            line=dict(color="#6366f1", width=2),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.15)"
        ))
        fig.update_layout(
            title="Monthly Shipping Cost Trend",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis_title="", yaxis_title="Cost ($)",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Charts Row 2 ──────────────────────────────────────────────────────
    ch3, ch4 = st.columns(2)

    with ch3:
        perf = service.get_delivery_performance()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=perf["month"], y=perf["delivered"],
                             name="Delivered", marker_color="#10b981"))
        fig.add_trace(go.Bar(x=perf["month"], y=perf["delayed"],
                             name="Delayed", marker_color="#ef4444"))
        fig.update_layout(
            title="Delivery Performance Over Time",
            barmode="stack",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with ch4:
        origin_stats = service.get_origin_stats()
        fig = px.bar(origin_stats.head(15), x="origin", y="shipments",
                     title="Shipments by Origin",
                     color="avg_cost", color_continuous_scale="Turbo")
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis_tickangle=-45,
            margin=dict(l=20, r=20, t=50, b=80),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Route Analysis ─────────────────────────────────────────────────────
    st.markdown("### 🗺️ Route Analysis")
    routes = service.get_route_analysis()

    if not routes.empty:
        fig = px.scatter(routes, x="avg_cost", y="avg_days",
                         size="shipment_count", color="delay_rate",
                         hover_data=["origin", "destination"],
                         title="Route Performance (Cost vs Time)",
                         labels={"avg_cost": "Avg Cost ($)", "avg_days": "Avg Transit Days",
                                 "delay_rate": "Delay Rate %"},
                         color_continuous_scale="RdYlGn_r")
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Delay Prediction Tool ──────────────────────────────────────────────
    st.markdown("### 🔮 Delay Risk Predictor")
    pc1, pc2, pc3 = st.columns(3)
    origins = shipments["origin"].unique().tolist()
    destinations = shipments["destination"].unique().tolist()

    with pc1:
        pred_origin = st.selectbox("Origin", origins, key="pred_orig")
    with pc2:
        pred_dest = st.selectbox("Destination",
                                  [d for d in destinations if d != pred_origin],
                                  key="pred_dest")
    with pc3:
        pred_cost = st.number_input("Shipping Cost ($)", 100, 10000, 1000, key="pred_cost")

    if st.button("Predict Delay Risk", key="predict_delay"):
        result = service.predict_delay_probability(pred_origin, pred_dest, pred_cost)

        risk_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}.get(
            result["risk_level"], "#6366f1")

        st.markdown(f"""
        <div class="insight-card" style="border-left: 4px solid {risk_color};">
            <strong>Risk Level: {result['risk_level']}</strong><br>
            Delay Probability: <strong>{result['delay_probability']:.1f}%</strong><br>
            {result['message']}
        </div>
        """, unsafe_allow_html=True)

    # ── Shipments Table ────────────────────────────────────────────────────
    st.markdown("### 📋 Shipment Records")
    if filtered.empty:
        st.warning("No shipments match the selected filters.")
    else:
        display_cols = [
            "shipment_id", "order_id", "origin", "destination",
            "ship_date", "delivery_date", "carrier", "cost", "status", "delay_risk"
        ]
        available_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(filtered[available_cols].head(500), use_container_width=True, height=400)

        # Download
        st.markdown("---")
        csv = filtered[available_cols].to_csv(index=False)
        st.download_button("📥 Download Logistics Report (CSV)", csv,
                           "logistics_report.csv", "text/csv")

