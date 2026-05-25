"""
Demand Forecasting Page — ML forecasts, model comparison, stockout risk,
reorder recommendations, and scenario analysis.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from services.forecasting_service import ForecastingService


def render_forecasting():
    """Render the demand forecasting page."""
    service = ForecastingService()

    st.markdown("## 🤖 AI Demand Forecasting")
    st.markdown("---")

    # Check if model is trained
    if not service.predictor.is_model_ready():
        st.warning("⚠️ Forecasting model not yet trained. Run `python ml/train_model.py` first.")
        st.info("Once trained, this page will display forecasts, risk analysis, and recommendations.")
        return

    # ── Product Selection ──────────────────────────────────────────────────
    products = service.get_product_list()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        product_options = products[["product_id", "product_name", "category"]].values.tolist()
        selected_product = st.selectbox(
            "Select Product",
            options=[p[0] for p in product_options],
            format_func=lambda x: next(f"{p[1]} ({p[2]})" for p in product_options if p[0] == x),
            key="fc_product"
        )
    with col2:
        horizon = st.selectbox("Forecast Horizon",
                                [30, 60, 90, 180],
                                format_func=lambda x: f"{x} days",
                                key="fc_horizon")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        run_forecast = st.button("🚀 Generate Forecast", key="run_fc", use_container_width=True)

    # Get product category
    product_info = products[products["product_id"] == selected_product].iloc[0]
    category = product_info["category"]

    # ── Model Comparison Table ─────────────────────────────────────────────
    st.markdown("### 📊 Model Performance Comparison")
    metrics = service.predictor.get_model_metrics()
    if metrics:
        best_model = metrics.get("best_model", "")
        rows = []
        for name, m in metrics.items():
            if name == "best_model":
                continue
            rows.append({
                "Model": name,
                "MAE": m["MAE"],
                "RMSE": m["RMSE"],
                "R² Score": m["R2"],
                "Selected": "✅" if name == best_model else "",
            })
        metrics_df = pd.DataFrame(rows)

        def highlight_best(row):
            if row["Selected"] == "✅":
                return ["background-color: rgba(99, 102, 241, 0.2);"] * len(row)
            return [""] * len(row)

        styled = metrics_df.style.apply(highlight_best, axis=1).format({
            "MAE": "{:.4f}",
            "RMSE": "{:.4f}",
            "R² Score": "{:.4f}",
        })
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption(f"🏆 Best Model: **{best_model}**")

    # ── Forecast Results ───────────────────────────────────────────────────
    if run_forecast or "forecast_result" in st.session_state:
        if run_forecast:
            with st.spinner("Generating forecast..."):
                result = service.run_forecast(selected_product, horizon, category)
                st.session_state["forecast_result"] = result
        else:
            result = st.session_state["forecast_result"]

        forecast_df = result["forecast"]

        if not forecast_df.empty:
            # KPI Row
            st.markdown("### 📈 Forecast Results")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Total Predicted Demand</div>
                    <div class="kpi-value">{result['total_demand']:,.0f}</div>
                </div>""", unsafe_allow_html=True)
            with k2:
                risk = result["risk"]
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Stockout Risk</div>
                    <div class="kpi-value">{risk['risk']}</div>
                </div>""", unsafe_allow_html=True)
            with k3:
                reorder = result["reorder"]
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Reorder Quantity</div>
                    <div class="kpi-value">{reorder['recommended_qty']:,.0f}</div>
                </div>""", unsafe_allow_html=True)
            with k4:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Forecast Horizon</div>
                    <div class="kpi-value">{horizon} days</div>
                </div>""", unsafe_allow_html=True)

            # Forecast Chart
            fig = go.Figure()

            # Confidence interval band
            fig.add_trace(go.Scatter(
                x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
                y=pd.concat([forecast_df["upper_bound"], forecast_df["lower_bound"][::-1]]),
                fill="toself",
                fillcolor="rgba(99, 102, 241, 0.15)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Confidence Interval",
                showlegend=True,
            ))

            # Prediction line
            fig.add_trace(go.Scatter(
                x=forecast_df["date"],
                y=forecast_df["predicted_demand"],
                mode="lines+markers",
                name="Predicted Demand",
                line=dict(color="#6366f1", width=3),
                marker=dict(size=4),
            ))

            # Trend line
            from numpy import polyfit, polyval
            x_num = range(len(forecast_df))
            z = polyfit(list(x_num), forecast_df["predicted_demand"].values, 1)
            trend = polyval(z, list(x_num))
            fig.add_trace(go.Scatter(
                x=forecast_df["date"],
                y=trend,
                mode="lines",
                name="Trend",
                line=dict(color="#f59e0b", width=2, dash="dash"),
            ))

            fig.update_layout(
                title=f"Demand Forecast — {product_info['product_name']} ({horizon} days)",
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                xaxis_title="Date", yaxis_title="Predicted Demand",
                margin=dict(l=20, r=20, t=50, b=20),
                height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)

            # ── Risk & Reorder Panel ───────────────────────────────────────
            r1, r2 = st.columns(2)

            with r1:
                st.markdown("#### 🚨 Stockout Risk Assessment")
                risk = result["risk"]
                risk_color = {"Critical": "#ef4444", "High": "#f59e0b",
                              "Medium": "#eab308", "Low": "#10b981"}.get(
                    risk["risk"].split()[-1], "#6366f1")
                st.markdown(f"""
                <div class="insight-card" style="border-left: 4px solid {risk_color};">
                    <strong>Risk Level: {risk['risk']}</strong><br>
                    Current Stock: <strong>{risk.get('current_stock', 'N/A'):,.0f}</strong> units<br>
                    Safety Stock: <strong>{risk.get('safety_stock', 'N/A'):,.0f}</strong> units<br>
                    Days Remaining: <strong>{risk.get('days_remaining', 'N/A')}</strong><br>
                    {risk['message']}
                </div>""", unsafe_allow_html=True)

            with r2:
                st.markdown("#### 📦 Reorder Recommendation")
                reorder = result["reorder"]
                st.markdown(f"""
                <div class="insight-card" style="border-left: 4px solid #6366f1;">
                    <strong>{reorder['message']}</strong><br><br>
                    <strong>Calculation:</strong><br>
                    Forecast Demand: {reorder['forecast_demand']:,.0f} units<br>
                    + Safety Stock: {reorder['safety_stock']:,.0f} units<br>
                    − Current Stock: {reorder['current_stock']:,.0f} units<br>
                    <hr style="border-color: rgba(255,255,255,0.1);">
                    = <strong>Recommended Order: {reorder['recommended_qty']:,.0f} units</strong>
                </div>""", unsafe_allow_html=True)

        else:
            st.warning("Not enough historical data for this product to generate a forecast.")

    # ── Scenario Analysis ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔬 Scenario Analysis (What-If)")

    sc1, sc2 = st.columns(2)
    with sc1:
        demand_change = st.slider("Demand Change (%)", -50, 100, 0, 5,
                                   key="sc_demand",
                                   help="Simulate demand increase or decrease")
    with sc2:
        delay_change = st.slider("Additional Supplier Delay (days)", 0, 30, 0, 1,
                                  key="sc_delay",
                                  help="Simulate extra lead time")

    if st.button("🔮 Run Scenario", key="run_scenario"):
        with st.spinner("Running scenario analysis..."):
            scenario = service.scenario_analysis(
                selected_product, demand_change, delay_change, category
            )

        if "message" in scenario and "Insufficient" in scenario["message"]:
            st.warning(scenario["message"])
        else:
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.metric("Base Demand (90d)", f"{scenario['base_demand_90d']:,.0f}")
            with s2:
                st.metric("Adjusted Demand", f"{scenario['adjusted_demand_90d']:,.0f}",
                          delta=f"{scenario['demand_change_pct']:+.0f}%")
            with s3:
                st.metric("Days of Coverage", f"{scenario['days_of_coverage']:.0f}")
            with s4:
                impact_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(
                    scenario["impact"], "⚪")
                st.metric("Impact", f"{impact_color} {scenario['impact']}")

            if scenario["projected_shortfall"] > 0:
                st.markdown(f"""
                <div class="insight-card" style="border-left: 4px solid #ef4444;">
                    ⚠️ <strong>Projected Shortfall: {scenario['projected_shortfall']:,.0f} units</strong><br>
                    With a {demand_change:+d}% demand change and {delay_change} extra delay days,
                    current stock will cover only <strong>{scenario['days_of_coverage']:.0f} days</strong>
                    against an adjusted lead time of <strong>{scenario['adjusted_lead_time']} days</strong>.<br>
                    💡 <strong>Recommended immediate order: {scenario['recommended_order']:,.0f} units</strong>
                </div>""", unsafe_allow_html=True)
            else:
                st.success(f"✅ Under this scenario, current inventory is sufficient "
                           f"({scenario['days_of_coverage']:.0f} days of coverage).")
