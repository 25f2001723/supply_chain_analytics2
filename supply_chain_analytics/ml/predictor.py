"""
Demand Forecasting Predictor.

Loads trained model and generates demand forecasts with confidence intervals
for specified products and horizons.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import joblib

from database.database import get_engine

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "demand_forecasting_model.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "model_metrics.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoders.pkl")


class DemandPredictor:
    """Generates demand forecasts using the trained ML model."""

    def __init__(self):
        """Load the trained model and encoders."""
        self.model = None
        self.label_encoder = None
        self.metrics = None
        self._load_model()

    def _load_model(self) -> None:
        """Load model, encoder, and metrics from disk."""
        try:
            if os.path.exists(MODEL_PATH):
                self.model = joblib.load(MODEL_PATH)
                logger.info("Model loaded from %s", MODEL_PATH)
            if os.path.exists(ENCODER_PATH):
                self.label_encoder = joblib.load(ENCODER_PATH)
            if os.path.exists(METRICS_PATH):
                self.metrics = joblib.load(METRICS_PATH)
        except Exception as e:
            logger.error("Failed to load model: %s", e)

    def is_model_ready(self) -> bool:
        """Check if a trained model is available."""
        return self.model is not None

    def get_model_metrics(self) -> Optional[Dict]:
        """Return stored model comparison metrics."""
        return self.metrics

    def _get_product_history(self, product_id: int) -> pd.DataFrame:
        """Fetch historical sales data for a product."""
        engine = get_engine()
        query = f"""
            SELECT s.sale_date, s.quantity_sold, s.revenue,
                   p.category, p.unit_price, p.lead_time_days, p.reorder_point
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            WHERE s.product_id = {product_id}
            ORDER BY s.sale_date
        """
        df = pd.read_sql(query, engine, parse_dates=["sale_date"])
        return df

    def forecast(
        self,
        product_id: int,
        horizon_days: int = 30,
        category: str = "Electronics"
    ) -> pd.DataFrame:
        """
        Generate demand forecast for a product over the given horizon.

        Args:
            product_id: Target product ID
            horizon_days: Number of days to forecast (30, 60, 90, 180)
            category: Product category for encoding

        Returns:
            DataFrame with columns: date, predicted_demand, lower_bound, upper_bound
        """
        if not self.is_model_ready():
            logger.warning("Model not trained yet. Returning empty forecast.")
            return pd.DataFrame()

        history = self._get_product_history(product_id)
        if history.empty:
            logger.warning("No history for product %d", product_id)
            return pd.DataFrame()

        # Aggregate daily
        daily = history.groupby("sale_date").agg(
            quantity=("quantity_sold", "sum"),
        ).reset_index()
        daily = daily.sort_values("sale_date")

        # Get product meta
        meta = history.iloc[0]
        unit_price = meta["unit_price"]
        lead_time = meta["lead_time_days"]
        reorder_pt = meta["reorder_point"]

        # Category encoding
        if self.label_encoder is not None:
            try:
                cat_encoded = self.label_encoder.transform([category])[0]
            except ValueError:
                cat_encoded = 0
        else:
            cat_encoded = 0

        # Build recent stats for lag / rolling features
        recent_qty = daily["quantity"].values
        lag_7 = float(np.mean(recent_qty[-7:])) if len(recent_qty) >= 7 else float(np.mean(recent_qty))
        lag_14 = float(np.mean(recent_qty[-14:])) if len(recent_qty) >= 14 else float(np.mean(recent_qty))
        lag_30 = float(np.mean(recent_qty[-30:])) if len(recent_qty) >= 30 else float(np.mean(recent_qty))
        rolling_7 = lag_7
        rolling_14 = lag_14
        rolling_30 = lag_30

        start_date = daily["sale_date"].min()
        last_date = daily["sale_date"].max()

        # Generate future dates
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=horizon_days,
            freq="D"
        )

        predictions = []
        for fdate in forecast_dates:
            features = {
                "month": fdate.month,
                "week": fdate.isocalendar()[1],
                "quarter": (fdate.month - 1) // 3 + 1,
                "day_of_week": fdate.dayofweek,
                "day_of_year": fdate.timetuple().tm_yday,
                "year": fdate.year,
                "lag_7": lag_7,
                "lag_14": lag_14,
                "lag_30": lag_30,
                "rolling_mean_7": rolling_7,
                "rolling_mean_14": rolling_14,
                "rolling_mean_30": rolling_30,
                "is_quarter_end": int(fdate.month in [3, 6, 9, 12] and fdate.day >= 28),
                "is_month_start": int(fdate.day == 1),
                "is_month_end": int(fdate.day >= 28),
                "is_festival_season": int(fdate.month in [10, 11, 12]),
                "is_summer": int(fdate.month in [5, 6, 7, 8]),
                "is_winter": int(fdate.month in [12, 1, 2]),
                "days_since_start": (fdate - start_date).days,
                "category_encoded": cat_encoded,
                "unit_price": unit_price,
                "lead_time_days": lead_time,
                "reorder_point": reorder_pt,
            }
            X = np.array([list(features.values())])
            pred = max(0, float(self.model.predict(X)[0]))

            # Confidence interval (±20% as heuristic; a proper model would use prediction intervals)
            lower = max(0, pred * 0.80)
            upper = pred * 1.20

            predictions.append({
                "date": fdate,
                "predicted_demand": round(pred, 1),
                "lower_bound": round(lower, 1),
                "upper_bound": round(upper, 1),
            })

            # Update rolling stats with prediction for next iteration
            lag_7 = pred
            rolling_7 = (rolling_7 * 6 + pred) / 7

        result = pd.DataFrame(predictions)
        logger.info("Forecast generated for product %d: %d days", product_id, horizon_days)
        return result

    def get_total_forecast_demand(self, product_id: int, horizon_days: int = 30,
                                   category: str = "Electronics") -> float:
        """Return total predicted demand over the forecast horizon."""
        forecast = self.forecast(product_id, horizon_days, category)
        if forecast.empty:
            return 0.0
        return float(forecast["predicted_demand"].sum())
