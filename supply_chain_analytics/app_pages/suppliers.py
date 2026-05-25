"""
Supplier Analytics Page — scorecards, rankings, and recommendations.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from services.supplier_service import SupplierService


def render_suppliers():
    """Render the supplier analytics page."""
    service = SupplierService()

    st.markdown("## 🏭 Supplier Analytics")
    st.markdown("---")

    # ── Supplier Rankings ──────────────────────────────────────────────────
    rankings = service.get_supplier_rankings()

    gold_count = len(rankings[rankings["tier"].str.contains("Gold")])
    silver_count = len(rankings[rankings["tier"].str.contains("Silver")])
    bronze_count = len(rankings[rankings["tier"].str.contains("Bronze")])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Suppliers</div>
            <div class="kpi-value">{len(rankings)}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #fbbf24;">
            <div class="kpi-label">🥇 Gold Tier</div>
            <div class="kpi-value">{gold_count}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #9ca3af;">
            <div class="kpi-label">🥈 Silver Tier</div>
            <div class="kpi-value">{silver_count}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #b45309;">
            <div class="kpi-label">🥉 Bronze Tier</div>
            <div class="kpi-value">{bronze_count}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        tier_filter = st.selectbox("Filter by Tier",
                                    ["All", "🥇 Gold", "🥈 Silver", "🥉 Bronze"],
                                    key="sup_tier")
    with fc2:
        country_opts = ["All"] + sorted(rankings["country"].unique().tolist())
        country_filter = st.selectbox("Filter by Country", country_opts, key="sup_country")

    filtered = rankings.copy()
    if tier_filter != "All":
        filtered = filtered[filtered["tier"] == tier_filter]
    if country_filter != "All":
        filtered = filtered[filtered["country"] == country_filter]

    # ── Charts ─────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        fig = px.scatter(filtered, x="on_time_delivery_rate", y="quality_score",
                         size="total_orders", color="tier",
                         hover_name="supplier_name",
                         title="Supplier Performance Map",
                         labels={"on_time_delivery_rate": "On-Time Rate",
                                 "quality_score": "Quality Score"},
                         color_discrete_map={"🥇 Gold": "#fbbf24", "🥈 Silver": "#9ca3af",
                                             "🥉 Bronze": "#b45309"})
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with ch2:
        country_dist = service.get_country_distribution()
        fig = px.bar(country_dist.head(15), x="country", y="count",
                     title="Suppliers by Country",
                     color="avg_quality",
                     color_continuous_scale="RdYlGn")
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Rankings Table ─────────────────────────────────────────────────────
    st.markdown("### 🏆 Supplier Rankings")

    display_cols = ["supplier_name", "country", "tier", "composite_score",
                    "on_time_delivery_rate", "quality_score", "rating", "total_orders"]

    def color_tier(val):
        if "Gold" in str(val):
            return "background-color: rgba(251, 191, 36, 0.2); color: #fbbf24;"
        elif "Silver" in str(val):
            return "background-color: rgba(156, 163, 175, 0.2); color: #d1d5db;"
        elif "Bronze" in str(val):
            return "background-color: rgba(180, 83, 9, 0.2); color: #d97706;"
        return ""

    styled = filtered[display_cols].style.map(
        color_tier, subset=["tier"]
    ).format({
        "composite_score": "{:.3f}",
        "on_time_delivery_rate": "{:.1%}",
        "quality_score": "{:.1f}",
        "rating": "{:.1f}",
    })
    st.dataframe(styled, use_container_width=True, height=400)

    # ── Supplier Scorecard ─────────────────────────────────────────────────
    st.markdown("### 📋 Supplier Scorecard")

    suppliers_list = filtered[["supplier_id", "supplier_name"]].values.tolist()
    if suppliers_list:
        selected = st.selectbox(
            "Select Supplier",
            options=[s[0] for s in suppliers_list],
            format_func=lambda x: next(s[1] for s in suppliers_list if s[0] == x),
            key="sup_scorecard"
        )

        card = service.get_supplier_scorecard(selected)
        if "error" not in card:
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.metric("Delivery Rate", f"{card['delivery_rate']:.1f}%")
            with sc2:
                st.metric("Quality Score", f"{card['quality_score']:.1f}/5.0")
            with sc3:
                st.metric("Avg Lead Time", f"{card['avg_lead_time']:.0f} days")
            with sc4:
                st.metric("Defect Rate", f"{card['defect_rate']:.1f}%")

            # Radar chart
            fig = go.Figure(data=go.Scatterpolar(
                r=[card["delivery_rate"], card["quality_score"] * 20,
                   card["rating"] * 20, (100 - card["defect_rate"]),
                   card["on_time_delivery_rate"]],
                theta=["Delivery Rate", "Quality", "Rating", "Low Defects", "On-Time %"],
                fill="toself",
                fillcolor="rgba(99, 102, 241, 0.3)",
                line_color="#6366f1",
            ))
            fig.update_layout(
                title=f"Scorecard: {card['supplier_name']}",
                polar=dict(bgcolor="rgba(0,0,0,0)",
                           radialaxis=dict(range=[0, 100], showticklabels=True,
                                           gridcolor="rgba(255,255,255,0.1)")),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                margin=dict(l=40, r=40, t=60, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Recommendations ────────────────────────────────────────────────────
    st.markdown("### 💡 Procurement Recommendations")
    recs = service.get_recommendations()
    for rec in recs:
        if rec["type"] == "positive":
            st.markdown(f"""
            <div class="insight-card" style="border-left: 4px solid #10b981;">
                {rec['message']}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="insight-card" style="border-left: 4px solid #f59e0b;">
                {rec['message']}
            </div>""", unsafe_allow_html=True)

    # Download
    st.markdown("---")
    csv = filtered[display_cols].to_csv(index=False)
    st.download_button("📥 Download Supplier Report (CSV)", csv,
                       "supplier_report.csv", "text/csv")
