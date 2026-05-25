"""
Reports Page — export reports in CSV, Excel, and PDF formats.
"""

import io
import os
import logging
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px

from database.database import get_engine
from services.inventory_service import InventoryService
from services.supplier_service import SupplierService
from services.shipment_service import ShipmentService

logger = logging.getLogger(__name__)


def _generate_pdf_report(title: str, df: pd.DataFrame, summary: dict = None) -> bytes:
    """Generate a PDF report using fpdf2."""
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 15, title, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                 new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        # Summary KPIs
        if summary:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Key Metrics", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for key, value in summary.items():
                label = key.replace("_", " ").title()
                pdf.cell(0, 7, f"  {label}: {value}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

        # Table (limit columns for readability)
        cols = list(df.columns)[:8]
        data = df[cols].head(100)

        pdf.set_font("Helvetica", "B", 8)
        col_width = (pdf.w - 20) / len(cols)
        for col in cols:
            pdf.cell(col_width, 8, str(col)[:15], border=1, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 7)
        for _, row in data.iterrows():
            for col in cols:
                val = str(row[col])[:18]
                pdf.cell(col_width, 7, val, border=1)
            pdf.ln()

        return pdf.output()
    except ImportError:
        return b"PDF generation requires fpdf2. Install with: pip install fpdf2"


def render_reports():
    """Render the reporting page."""
    engine = get_engine()

    st.markdown("## 📄 Reports & Export")
    st.markdown("---")

    # ── Report Type Selection ──────────────────────────────────────────────
    report_type = st.selectbox(
        "Select Report Type",
        ["Sales Report", "Inventory Report", "Supplier Report",
         "Logistics Report", "Forecast Summary"],
        key="report_type"
    )

    # ── Date Range Filter ──────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date",
                                    value=datetime(2023, 1, 1),
                                    key="report_start")
    with col2:
        end_date = st.date_input("End Date",
                                  value=datetime(2025, 12, 31),
                                  key="report_end")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Generate Report ────────────────────────────────────────────────────
    if report_type == "Sales Report":
        query = f"""
            SELECT s.sale_id, p.product_name, p.category, s.sale_date,
                   s.quantity_sold, s.revenue, sup.supplier_name
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN suppliers sup ON p.supplier_id = sup.supplier_id
            WHERE s.sale_date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY s.sale_date DESC
        """
        df = pd.read_sql(query, engine)
        summary = {
            "total_revenue": f"${df['revenue'].sum():,.2f}",
            "total_units_sold": f"{df['quantity_sold'].sum():,}",
            "total_transactions": f"{len(df):,}",
            "avg_order_value": f"${df['revenue'].mean():,.2f}" if len(df) > 0 else "$0",
            "top_category": df.groupby("category")["revenue"].sum().idxmax() if len(df) > 0 else "N/A",
        }

        # Preview chart
        monthly = df.groupby(pd.to_datetime(df["sale_date"]).dt.to_period("M").astype(str)).agg(
            revenue=("revenue", "sum")).reset_index()
        fig = px.bar(monthly, x="sale_date", y="revenue",
                     title="Revenue by Month",
                     color_discrete_sequence=["#6366f1"])
        fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    elif report_type == "Inventory Report":
        inv_service = InventoryService()
        df = inv_service.get_inventory_overview()
        summary = inv_service.get_stock_summary()
        summary = {k: f"{v:,}" if isinstance(v, (int, float)) else v
                   for k, v in summary.items()}

        fig = px.pie(df, values="inventory_value", names="category",
                     title="Inventory Value by Category",
                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
        fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    elif report_type == "Supplier Report":
        sup_service = SupplierService()
        df = sup_service.get_supplier_rankings()
        summary = {
            "total_suppliers": f"{len(df)}",
            "gold_tier": f"{len(df[df['tier'].str.contains('Gold')])}",
            "silver_tier": f"{len(df[df['tier'].str.contains('Silver')])}",
            "bronze_tier": f"{len(df[df['tier'].str.contains('Bronze')])}",
            "avg_composite_score": f"{df['composite_score'].mean():.3f}",
        }

        fig = px.histogram(df, x="composite_score", nbins=20,
                           title="Supplier Score Distribution",
                           color_discrete_sequence=["#8b5cf6"])
        fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    elif report_type == "Logistics Report":
        ship_service = ShipmentService()
        df = ship_service.get_all_shipments()
        raw_summary = ship_service.get_shipment_summary()
        summary = {k: f"{v:,}" if isinstance(v, (int, float)) else v
                   for k, v in raw_summary.items()}

        fig = px.histogram(df, x="delivery_days", nbins=25,
                           title="Delivery Days Distribution",
                           color_discrete_sequence=["#10b981"])
        fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    elif report_type == "Forecast Summary":
        try:
            import joblib
            metrics_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                         "ml", "model_metrics.pkl")
            if os.path.exists(metrics_path):
                metrics = joblib.load(metrics_path)
                best = metrics.get("best_model", "N/A")
                rows = []
                for name, m in metrics.items():
                    if name == "best_model":
                        continue
                    rows.append({"Model": name, **m})
                df = pd.DataFrame(rows)
                summary = {"best_model": best, "models_compared": f"{len(rows)}"}
            else:
                df = pd.DataFrame({"Message": ["Model not yet trained."]})
                summary = {"status": "Not trained"}
        except Exception:
            df = pd.DataFrame({"Message": ["Error loading model metrics."]})
            summary = {"status": "Error"}

    # ── Summary Display ────────────────────────────────────────────────────
    st.markdown("### 📊 Report Summary")
    if summary:
        cols = st.columns(min(len(summary), 5))
        for i, (key, val) in enumerate(summary.items()):
            with cols[i % len(cols)]:
                label = key.replace("_", " ").title()
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value" style="font-size: 1.1rem;">{val}</div>
                </div>""", unsafe_allow_html=True)

    # ── Data Preview ───────────────────────────────────────────────────────
    st.markdown("### 📋 Data Preview")
    st.dataframe(df.head(200), use_container_width=True, height=350)
    st.caption(f"Showing {min(200, len(df))} of {len(df):,} records")

    # ── Export Buttons ─────────────────────────────────────────────────────
    st.markdown("### 📥 Export Options")
    ex1, ex2, ex3 = st.columns(3)

    with ex1:
        csv_data = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv_data,
            f"{report_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True,
        )

    with ex2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Report")
        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            f"{report_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with ex3:
        pdf_data = _generate_pdf_report(report_type, df, summary)
        st.download_button(
            "📥 Download PDF",
            pdf_data,
            f"{report_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            "application/pdf",
            use_container_width=True,
        )
