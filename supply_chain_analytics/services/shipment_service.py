"""
Shipment Service — logistics tracking, delay analysis, and cost analytics.
"""

import logging
from typing import Dict, List

import pandas as pd
import numpy as np

from database.database import get_engine

logger = logging.getLogger(__name__)


class ShipmentService:
    """Provides logistics analytics, shipment tracking, and delay prediction."""

    def __init__(self):
        self.engine = get_engine()

    def get_all_shipments(self) -> pd.DataFrame:
        """Get all shipments with order details."""
        query = """
            SELECT sh.shipment_id, sh.order_id, sh.origin, sh.destination,
                   sh.shipping_cost, sh.delivery_days, sh.status,
                   po.order_date, po.expected_delivery, po.actual_delivery,
                   po.quantity, po.status as order_status,
                   p.product_name, p.category
            FROM shipments sh
            JOIN purchase_orders po ON sh.order_id = po.order_id
            JOIN products p ON po.product_id = p.product_id
            ORDER BY sh.shipment_id DESC
        """
        return pd.read_sql(query, self.engine, parse_dates=["order_date", "expected_delivery", "actual_delivery"])

    def get_shipment_summary(self) -> Dict:
        """Get aggregated shipment statistics."""
        query = """
            SELECT
                COUNT(*) as total_shipments,
                SUM(shipping_cost) as total_cost,
                AVG(shipping_cost) as avg_cost,
                AVG(delivery_days) as avg_delivery_days,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN status = 'In Transit' THEN 1 ELSE 0 END) as in_transit,
                SUM(CASE WHEN status = 'Delayed' THEN 1 ELSE 0 END) as delayed,
                SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END) as returned
            FROM shipments
        """
        df = pd.read_sql(query, self.engine)
        row = df.iloc[0]

        return {
            "total_shipments": int(row["total_shipments"]),
            "total_cost": round(float(row["total_cost"]), 2),
            "avg_cost": round(float(row["avg_cost"]), 2),
            "avg_delivery_days": round(float(row["avg_delivery_days"]), 1),
            "delivered": int(row["delivered"]),
            "in_transit": int(row["in_transit"]),
            "delayed": int(row["delayed"]),
            "returned": int(row["returned"]),
        }

    def get_status_breakdown(self) -> pd.DataFrame:
        """Get shipment count by status."""
        query = """
            SELECT status, COUNT(*) as count
            FROM shipments
            GROUP BY status
            ORDER BY count DESC
        """
        return pd.read_sql(query, self.engine)

    def get_route_analysis(self) -> pd.DataFrame:
        """Analyze popular shipping routes and their performance."""
        query = """
            SELECT origin, destination,
                   COUNT(*) as shipment_count,
                   AVG(shipping_cost) as avg_cost,
                   AVG(delivery_days) as avg_days,
                   SUM(CASE WHEN status = 'Delayed' THEN 1 ELSE 0 END) as delayed_count
            FROM shipments
            GROUP BY origin, destination
            HAVING shipment_count >= 5
            ORDER BY shipment_count DESC
            LIMIT 30
        """
        df = pd.read_sql(query, self.engine)
        df["delay_rate"] = (df["delayed_count"] / df["shipment_count"] * 100).round(1)
        return df

    def get_monthly_cost_trend(self) -> pd.DataFrame:
        """Get monthly shipping cost trends."""
        query = """
            SELECT strftime('%Y-%m', po.order_date) as month,
                   SUM(sh.shipping_cost) as total_cost,
                   COUNT(*) as shipment_count,
                   AVG(sh.delivery_days) as avg_delivery_days
            FROM shipments sh
            JOIN purchase_orders po ON sh.order_id = po.order_id
            GROUP BY month
            ORDER BY month
        """
        return pd.read_sql(query, self.engine)

    def get_delivery_performance(self) -> pd.DataFrame:
        """Get monthly on-time delivery performance for shipments."""
        query = """
            SELECT strftime('%Y-%m', po.order_date) as month,
                   COUNT(*) as total,
                   SUM(CASE WHEN sh.status = 'Delivered' THEN 1 ELSE 0 END) as delivered,
                   SUM(CASE WHEN sh.status = 'Delayed' THEN 1 ELSE 0 END) as delayed
            FROM shipments sh
            JOIN purchase_orders po ON sh.order_id = po.order_id
            GROUP BY month
            ORDER BY month
        """
        df = pd.read_sql(query, self.engine)
        df["delivery_rate"] = (df["delivered"] / df["total"] * 100).round(1)
        return df

    def predict_delay_probability(self, origin: str, destination: str,
                                   shipping_cost: float) -> Dict:
        """
        Simple rule-based delay probability estimate.

        Based on historical route delay rates and cost thresholds.
        """
        route_data = self.get_route_analysis()
        route_match = route_data[
            (route_data["origin"] == origin) & (route_data["destination"] == destination)
        ]

        if route_match.empty:
            base_delay_rate = 15.0  # Default 15% if no history
        else:
            base_delay_rate = float(route_match["delay_rate"].iloc[0])

        # Adjust based on cost (lower cost → higher delay probability)
        avg_cost = float(route_data["avg_cost"].mean()) if not route_data.empty else 1000
        if shipping_cost < avg_cost * 0.5:
            base_delay_rate *= 1.3
        elif shipping_cost > avg_cost * 1.5:
            base_delay_rate *= 0.7

        delay_prob = min(100, base_delay_rate)

        if delay_prob > 30:
            risk = "High"
        elif delay_prob > 15:
            risk = "Medium"
        else:
            risk = "Low"

        return {
            "delay_probability": round(delay_prob, 1),
            "risk_level": risk,
            "message": f"{risk} risk of delay ({delay_prob:.1f}%) on {origin} → {destination} route.",
        }

    def get_origin_stats(self) -> pd.DataFrame:
        """Get shipment statistics by origin city."""
        query = """
            SELECT origin,
                   COUNT(*) as shipments,
                   AVG(shipping_cost) as avg_cost,
                   AVG(delivery_days) as avg_days
            FROM shipments
            GROUP BY origin
            ORDER BY shipments DESC
        """
        return pd.read_sql(query, self.engine)
