"""
Forecasting Service — orchestrates ML pipeline, scenario analysis, and insights.
"""

import logging
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

from database.database import get_engine
from ml.predictor import DemandPredictor
from services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class ForecastingService:
    """Orchestrates forecasting, risk assessment, and business intelligence."""

    def __init__(self):
        self.engine = get_engine()
        self.predictor = DemandPredictor()
        self.inventory_service = InventoryService()

    def get_product_list(self) -> pd.DataFrame:
        """Get list of products available for forecasting."""
        query = """
            SELECT p.product_id, p.product_name, p.category, p.unit_price,
                   COUNT(s.sale_id) as total_sales
            FROM products p
            LEFT JOIN sales s ON p.product_id = s.product_id
            GROUP BY p.product_id
            HAVING total_sales > 10
            ORDER BY total_sales DESC
        """
        return pd.read_sql(query, self.engine)

    def run_forecast(self, product_id: int, horizon_days: int = 30,
                     category: str = "Electronics") -> Dict:
        """
        Run complete forecast pipeline for a product.

        Returns forecast data, risk assessment, and reorder recommendation.
        """
        # Generate forecast
        forecast_df = self.predictor.forecast(product_id, horizon_days, category)
        total_demand = float(forecast_df["predicted_demand"].sum()) if not forecast_df.empty else 0

        # Stockout risk
        product_query = f"SELECT lead_time_days FROM products WHERE product_id = {product_id}"
        prod = pd.read_sql(product_query, self.engine)
        lead_time = int(prod["lead_time_days"].iloc[0]) if not prod.empty else 7

        risk = self.inventory_service.get_stockout_risk(product_id, lead_time, total_demand)

        # Reorder recommendation
        reorder = self.inventory_service.get_reorder_recommendation(product_id, total_demand)

        # Model metrics
        metrics = self.predictor.get_model_metrics()

        return {
            "forecast": forecast_df,
            "total_demand": round(total_demand, 0),
            "risk": risk,
            "reorder": reorder,
            "metrics": metrics,
            "horizon_days": horizon_days,
        }

    def scenario_analysis(self, product_id: int, demand_change_pct: float = 0.0,
                          delay_change_days: int = 0, category: str = "Electronics") -> Dict:
        """
        What-if scenario analysis.

        Args:
            product_id: Target product
            demand_change_pct: Percentage change in demand (e.g., 20 for +20%)
            delay_change_days: Additional lead time delay in days
        """
        # Base forecast
        base_forecast = self.predictor.forecast(product_id, 90, category)
        if base_forecast.empty:
            return {"message": "Insufficient data for scenario analysis."}

        base_demand = float(base_forecast["predicted_demand"].sum())

        # Adjusted demand
        adjusted_demand = base_demand * (1 + demand_change_pct / 100)

        # Get current stock
        stock_query = f"""
            SELECT SUM(i.current_stock) as stock, MAX(i.safety_stock) as safety,
                   MAX(p.lead_time_days) as lead_time
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            WHERE i.product_id = {product_id}
        """
        sdf = pd.read_sql(stock_query, self.engine)

        if sdf.empty or sdf["stock"].iloc[0] is None:
            return {"message": "No inventory data for this product."}

        current_stock = float(sdf["stock"].iloc[0])
        safety_stock = float(sdf["safety"].iloc[0])
        lead_time = int(sdf["lead_time"].iloc[0]) + delay_change_days

        # Projected shortfall
        shortfall = adjusted_demand + safety_stock - current_stock
        days_cover = (current_stock / (adjusted_demand / 90)) if adjusted_demand > 0 else 999

        return {
            "base_demand_90d": round(base_demand, 0),
            "adjusted_demand_90d": round(adjusted_demand, 0),
            "demand_change_pct": demand_change_pct,
            "current_stock": current_stock,
            "safety_stock": safety_stock,
            "adjusted_lead_time": lead_time,
            "projected_shortfall": max(0, round(shortfall, 0)),
            "days_of_coverage": round(days_cover, 1),
            "recommended_order": max(0, round(shortfall, 0)),
            "impact": "HIGH" if days_cover < lead_time else ("MEDIUM" if days_cover < lead_time * 2 else "LOW"),
        }

    def generate_business_insights(self) -> List[Dict]:
        """Auto-generate executive-level business insights."""
        insights = []

        # 1. Top supplier performance
        try:
            sup_query = """
                SELECT supplier_name, on_time_delivery_rate
                FROM suppliers ORDER BY on_time_delivery_rate DESC LIMIT 1
            """
            top_sup = pd.read_sql(sup_query, self.engine)
            if not top_sup.empty:
                name = top_sup.iloc[0]["supplier_name"]
                rate = round(top_sup.iloc[0]["on_time_delivery_rate"] * 100, 1)
                insights.append({
                    "icon": "🏆",
                    "category": "Suppliers",
                    "message": f"{name} has {rate}% on-time delivery — best in network.",
                })
        except Exception:
            pass

        # 2. Revenue trend by category
        try:
            rev_query = """
                SELECT p.category,
                       SUM(CASE WHEN s.sale_date >= (SELECT date(MAX(sale_date), '-6 months') FROM sales) THEN s.revenue ELSE 0 END) as recent,
                       SUM(CASE WHEN s.sale_date < (SELECT date(MAX(sale_date), '-6 months') FROM sales)
                                 AND s.sale_date >= (SELECT date(MAX(sale_date), '-12 months') FROM sales) THEN s.revenue ELSE 0 END) as prev
                FROM sales s JOIN products p ON s.product_id = p.product_id
                GROUP BY p.category
            """
            rev = pd.read_sql(rev_query, self.engine)
            for _, row in rev.iterrows():
                if row["prev"] > 0:
                    change = ((row["recent"] - row["prev"]) / row["prev"]) * 100
                    if abs(change) > 10:
                        direction = "increased" if change > 0 else "decreased"
                        insights.append({
                            "icon": "📈" if change > 0 else "📉",
                            "category": "Revenue",
                            "message": f"{row['category']} revenue {direction} {abs(change):.0f}% vs prior period.",
                        })
        except Exception:
            pass

        # 3. Warehouse utilization
        try:
            wh_query = """
                SELECT i.warehouse, SUM(i.current_stock) as stock
                FROM inventory i GROUP BY i.warehouse ORDER BY stock DESC LIMIT 3
            """
            wh = pd.read_sql(wh_query, self.engine)
            if not wh.empty:
                top_wh = wh.iloc[0]
                insights.append({
                    "icon": "🏭",
                    "category": "Warehouses",
                    "message": f"{top_wh['warehouse']} has highest utilization with {int(top_wh['stock']):,} units.",
                })
        except Exception:
            pass

        # 4. Delayed shipments
        try:
            delay_query = """
                SELECT COUNT(*) as cnt FROM shipments WHERE status = 'Delayed'
            """
            delays = pd.read_sql(delay_query, self.engine)
            cnt = int(delays.iloc[0]["cnt"])
            if cnt > 0:
                insights.append({
                    "icon": "⚠️",
                    "category": "Logistics",
                    "message": f"{cnt} shipments currently marked as delayed — review required.",
                })
        except Exception:
            pass

        # 5. Low stock alerts
        try:
            low_query = """
                SELECT COUNT(*) as cnt FROM inventory
                WHERE current_stock <= safety_stock
            """
            low = pd.read_sql(low_query, self.engine)
            cnt = int(low.iloc[0]["cnt"])
            if cnt > 0:
                insights.append({
                    "icon": "🔴",
                    "category": "Inventory",
                    "message": f"{cnt} inventory records at or below safety stock levels.",
                })
        except Exception:
            pass

        # 6. Top-selling product
        try:
            top_query = """
                SELECT p.product_name, SUM(s.quantity_sold) as qty, SUM(s.revenue) as rev
                FROM sales s JOIN products p ON s.product_id = p.product_id
                GROUP BY p.product_id ORDER BY rev DESC LIMIT 1
            """
            top_prod = pd.read_sql(top_query, self.engine)
            if not top_prod.empty:
                insights.append({
                    "icon": "⭐",
                    "category": "Products",
                    "message": f"{top_prod.iloc[0]['product_name']} is the top revenue generator "
                               f"at ${top_prod.iloc[0]['rev']:,.0f}.",
                })
        except Exception:
            pass

        return insights
