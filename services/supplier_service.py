"""
Supplier Service — scorecards, rankings, and procurement recommendations.
"""

import logging
from typing import Dict, List

import pandas as pd
import numpy as np

from database.database import get_engine

logger = logging.getLogger(__name__)


class SupplierService:
    """Provides supplier analytics, scorecards, and rankings."""

    def __init__(self):
        self.engine = get_engine()

    def get_all_suppliers(self) -> pd.DataFrame:
        """Get all suppliers with computed scores."""
        query = """
            SELECT s.*,
                   COUNT(DISTINCT po.order_id) as total_orders,
                   COUNT(DISTINCT p.product_id) as product_count
            FROM suppliers s
            LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
            LEFT JOIN products p ON s.supplier_id = p.supplier_id
            GROUP BY s.supplier_id
            ORDER BY s.rating DESC
        """
        return pd.read_sql(query, self.engine)

    def get_supplier_scorecard(self, supplier_id: int) -> Dict:
        """
        Generate a detailed scorecard for a supplier.

        Metrics: delivery reliability, quality score, avg lead time, defect rate.
        """
        # Basic info
        info_query = f"""
            SELECT * FROM suppliers WHERE supplier_id = {supplier_id}
        """
        info_df = pd.read_sql(info_query, self.engine)

        if info_df.empty:
            return {"error": "Supplier not found."}

        supplier = info_df.iloc[0]

        # Delivery performance
        delivery_query = f"""
            SELECT
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN status = 'Delivered' AND actual_delivery <= expected_delivery
                    THEN 1 ELSE 0 END) as on_time,
                AVG(CASE WHEN status = 'Delivered'
                    THEN julianday(actual_delivery) - julianday(order_date)
                    ELSE NULL END) as avg_lead_time,
                AVG(CASE WHEN status = 'Delivered'
                    THEN julianday(actual_delivery) - julianday(expected_delivery)
                    ELSE NULL END) as avg_delay
            FROM purchase_orders
            WHERE supplier_id = {supplier_id}
        """
        del_df = pd.read_sql(delivery_query, self.engine)
        del_stats = del_df.iloc[0]

        total = int(del_stats["total_orders"]) if del_stats["total_orders"] else 0
        delivered = int(del_stats["delivered"]) if del_stats["delivered"] else 0
        on_time = int(del_stats["on_time"]) if del_stats["on_time"] else 0
        delivery_rate = round(on_time / delivered * 100, 1) if delivered > 0 else 0
        avg_lead = round(float(del_stats["avg_lead_time"]), 1) if del_stats["avg_lead_time"] else 0
        avg_delay = round(float(del_stats["avg_delay"]), 1) if del_stats["avg_delay"] else 0

        # Compute defect rate (simulated as inverse of quality score)
        quality = float(supplier["quality_score"])
        defect_rate = round(max(0, (5.0 - quality) / 5.0 * 10), 2)  # 0-10%

        return {
            "supplier_name": supplier["supplier_name"],
            "country": supplier["country"],
            "total_orders": total,
            "delivery_rate": delivery_rate,
            "quality_score": quality,
            "avg_lead_time": avg_lead,
            "avg_delay_days": avg_delay,
            "defect_rate": defect_rate,
            "rating": float(supplier["rating"]),
            "on_time_delivery_rate": float(supplier["on_time_delivery_rate"]) * 100,
        }

    def get_supplier_rankings(self) -> pd.DataFrame:
        """
        Rank all suppliers into Gold / Silver / Bronze tiers.

        Ranking is based on composite score:
        (on_time_delivery_rate * 0.4) + (quality_score / 5 * 0.3) + (rating / 5 * 0.3)
        """
        query = """
            SELECT s.supplier_id, s.supplier_name, s.country,
                   s.on_time_delivery_rate, s.quality_score, s.rating,
                   COUNT(DISTINCT po.order_id) as total_orders
            FROM suppliers s
            LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
            GROUP BY s.supplier_id
        """
        df = pd.read_sql(query, self.engine)

        # Composite score
        df["composite_score"] = (
            df["on_time_delivery_rate"] * 0.4 +
            (df["quality_score"] / 5.0) * 0.3 +
            (df["rating"] / 5.0) * 0.3
        )
        df["composite_score"] = df["composite_score"].round(3)

        # Tier assignment
        def assign_tier(score):
            if score >= 0.80:
                return "🥇 Gold"
            elif score >= 0.65:
                return "🥈 Silver"
            else:
                return "🥉 Bronze"

        df["tier"] = df["composite_score"].apply(assign_tier)
        df = df.sort_values("composite_score", ascending=False)
        return df

    def get_supplier_performance_trend(self) -> pd.DataFrame:
        """Get monthly supplier delivery performance."""
        query = """
            SELECT strftime('%Y-%m', po.order_date) as month,
                   s.supplier_name,
                   COUNT(*) as orders,
                   SUM(CASE WHEN po.status = 'Delivered' AND po.actual_delivery <= po.expected_delivery
                       THEN 1 ELSE 0 END) as on_time_orders
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            WHERE po.status = 'Delivered'
            GROUP BY month, s.supplier_name
            ORDER BY month
        """
        df = pd.read_sql(query, self.engine)
        df["on_time_pct"] = (df["on_time_orders"] / df["orders"] * 100).round(1)
        return df

    def get_recommendations(self) -> List[Dict]:
        """Generate procurement recommendations based on supplier performance."""
        rankings = self.get_supplier_rankings()
        recommendations = []

        # Top performers
        gold = rankings[rankings["tier"].str.contains("Gold")].head(5)
        for _, row in gold.iterrows():
            recommendations.append({
                "type": "positive",
                "message": f"✅ {row['supplier_name']} ({row['country']}) has a composite score "
                           f"of {row['composite_score']:.2f}. Consider increasing procurement volume.",
                "supplier": row["supplier_name"],
            })

        # Poor performers
        bronze = rankings[rankings["tier"].str.contains("Bronze")].head(3)
        for _, row in bronze.iterrows():
            recommendations.append({
                "type": "warning",
                "message": f"⚠️ {row['supplier_name']} scored {row['composite_score']:.2f}. "
                           f"Review performance and consider alternative suppliers.",
                "supplier": row["supplier_name"],
            })

        return recommendations

    def get_country_distribution(self) -> pd.DataFrame:
        """Get supplier distribution by country."""
        query = """
            SELECT country, COUNT(*) as count,
                   AVG(on_time_delivery_rate) as avg_delivery_rate,
                   AVG(quality_score) as avg_quality
            FROM suppliers
            GROUP BY country
            ORDER BY count DESC
        """
        return pd.read_sql(query, self.engine)
