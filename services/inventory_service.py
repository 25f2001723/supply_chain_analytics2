"""
Inventory Service — stock analysis, stockout risk, reorder recommendations.
"""

import logging
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

from database.database import get_engine

logger = logging.getLogger(__name__)


class InventoryService:
    """Provides inventory analytics, risk assessment, and reorder recommendations."""

    def __init__(self):
        self.engine = get_engine()

    def get_inventory_overview(self) -> pd.DataFrame:
        """
        Get complete inventory overview with product details and status.

        Returns DataFrame with columns including stock_status (Green/Yellow/Red).
        """
        query = """
            SELECT i.inventory_id, i.product_id, i.warehouse, i.current_stock,
                   i.safety_stock, i.last_updated,
                   p.product_name, p.category, p.unit_price, p.lead_time_days,
                   p.reorder_point,
                   s.supplier_name
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            ORDER BY i.current_stock ASC
        """
        df = pd.read_sql(query, self.engine, parse_dates=["last_updated"])

        # Stock status classification
        def classify_stock(row):
            if row["current_stock"] <= row["safety_stock"] * 0.5:
                return "🔴 Critical"
            elif row["current_stock"] <= row["safety_stock"]:
                return "🟡 Low"
            elif row["current_stock"] <= row["reorder_point"]:
                return "🟡 Approaching Reorder"
            else:
                return "🟢 Healthy"

        df["stock_status"] = df.apply(classify_stock, axis=1)
        df["inventory_value"] = df["current_stock"] * df["unit_price"]
        return df

    def get_stock_summary(self) -> Dict:
        """Get aggregated inventory statistics."""
        df = self.get_inventory_overview()
        total_value = df["inventory_value"].sum()
        total_items = df["current_stock"].sum()
        critical_count = len(df[df["stock_status"].str.contains("Critical")])
        low_count = len(df[df["stock_status"].str.contains("Low")])
        healthy_count = len(df[df["stock_status"].str.contains("Healthy")])

        return {
            "total_inventory_value": round(total_value, 2),
            "total_items": int(total_items),
            "critical_items": critical_count,
            "low_stock_items": low_count,
            "healthy_items": healthy_count,
            "total_records": len(df),
            "warehouses": df["warehouse"].nunique(),
        }

    def get_warehouse_utilization(self) -> pd.DataFrame:
        """Get stock distribution across warehouses."""
        query = """
            SELECT i.warehouse,
                   COUNT(DISTINCT i.product_id) as product_count,
                   SUM(i.current_stock) as total_stock,
                   SUM(i.current_stock * p.unit_price) as total_value
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            GROUP BY i.warehouse
            ORDER BY total_value DESC
        """
        return pd.read_sql(query, self.engine)

    def estimate_days_until_stockout(self, product_id: int) -> Optional[float]:
        """
        Estimate days until stockout based on average daily sales.

        Returns None if no sales data is available.
        """
        # Get current total stock
        stock_query = f"""
            SELECT SUM(current_stock) as total_stock
            FROM inventory WHERE product_id = {product_id}
        """
        stock_df = pd.read_sql(stock_query, self.engine)
        current_stock = stock_df["total_stock"].iloc[0]
        if current_stock is None or current_stock == 0:
            return 0.0

        # Get average daily sales (last 90 days)
        sales_query = f"""
            SELECT AVG(daily_qty) as avg_daily
            FROM (
                SELECT sale_date, SUM(quantity_sold) as daily_qty
                FROM sales
                WHERE product_id = {product_id}
                  AND sale_date >= (SELECT date(MAX(sale_date), '-90 days') FROM sales)
                GROUP BY sale_date
            )
        """
        sales_df = pd.read_sql(sales_query, self.engine)
        avg_daily = sales_df["avg_daily"].iloc[0]

        if avg_daily is None or avg_daily == 0:
            return None

        return round(float(current_stock) / float(avg_daily), 1)

    def get_stockout_risk(self, product_id: int, lead_time_days: int = 7,
                          forecast_demand: float = 0.0) -> Dict:
        """
        Assess stockout risk for a product.

        Returns risk level: Low, Medium, High, Critical.
        """
        stock_query = f"""
            SELECT SUM(i.current_stock) as total_stock,
                   MAX(i.safety_stock) as safety_stock
            FROM inventory i WHERE i.product_id = {product_id}
        """
        df = pd.read_sql(stock_query, self.engine)

        if df.empty or df["total_stock"].iloc[0] is None:
            return {"risk": "Unknown", "days_remaining": None, "message": "No inventory data."}

        current_stock = float(df["total_stock"].iloc[0])
        safety_stock = float(df["safety_stock"].iloc[0]) if df["safety_stock"].iloc[0] else 50

        days_remaining = self.estimate_days_until_stockout(product_id)

        if days_remaining is None:
            return {"risk": "Unknown", "days_remaining": None,
                    "message": "Insufficient sales data to assess risk."}

        if days_remaining <= lead_time_days * 0.5:
            risk = "🔴 Critical"
            msg = f"High probability of stockout within {int(days_remaining)} days."
        elif days_remaining <= lead_time_days:
            risk = "🟠 High"
            msg = f"Stock may run out in {int(days_remaining)} days — order immediately."
        elif days_remaining <= lead_time_days * 2:
            risk = "🟡 Medium"
            msg = f"Stock projected to last {int(days_remaining)} days. Plan reorder soon."
        else:
            risk = "🟢 Low"
            msg = f"Stock sufficient for approximately {int(days_remaining)} days."

        return {
            "risk": risk,
            "days_remaining": days_remaining,
            "current_stock": current_stock,
            "safety_stock": safety_stock,
            "message": msg,
        }

    def get_reorder_recommendation(self, product_id: int,
                                    forecast_demand: float = 0.0) -> Dict:
        """
        Calculate recommended reorder quantity.

        Formula: Recommended Qty = Forecast Demand + Safety Stock - Current Inventory
        """
        stock_query = f"""
            SELECT SUM(i.current_stock) as total_stock,
                   MAX(i.safety_stock) as safety_stock,
                   MAX(p.reorder_point) as reorder_point,
                   MAX(p.lead_time_days) as lead_time,
                   MAX(p.product_name) as product_name
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            WHERE i.product_id = {product_id}
        """
        df = pd.read_sql(stock_query, self.engine)

        if df.empty or df["total_stock"].iloc[0] is None:
            return {"recommended_qty": 0, "message": "No inventory data."}

        current = float(df["total_stock"].iloc[0])
        safety = float(df["safety_stock"].iloc[0]) if df["safety_stock"].iloc[0] else 50
        product_name = df["product_name"].iloc[0]

        if forecast_demand == 0:
            # Use average monthly demand as fallback
            sales_query = f"""
                SELECT AVG(monthly_qty) as avg_monthly FROM (
                    SELECT strftime('%Y-%m', sale_date) as month,
                           SUM(quantity_sold) as monthly_qty
                    FROM sales WHERE product_id = {product_id}
                    GROUP BY month
                )
            """
            sdf = pd.read_sql(sales_query, self.engine)
            forecast_demand = float(sdf["avg_monthly"].iloc[0]) if sdf["avg_monthly"].iloc[0] else 100

        recommended = max(0, forecast_demand + safety - current)

        return {
            "product_name": product_name,
            "current_stock": current,
            "safety_stock": safety,
            "forecast_demand": round(forecast_demand, 0),
            "recommended_qty": round(recommended, 0),
            "message": f"Recommended reorder quantity for {product_name}: {int(recommended)} units.",
        }

    def get_category_inventory(self) -> pd.DataFrame:
        """Get inventory breakdown by category."""
        query = """
            SELECT p.category,
                   SUM(i.current_stock) as total_stock,
                   SUM(i.current_stock * p.unit_price) as total_value,
                   COUNT(DISTINCT i.product_id) as product_count
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            GROUP BY p.category
            ORDER BY total_value DESC
        """
        return pd.read_sql(query, self.engine)
