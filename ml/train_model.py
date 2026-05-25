"""
Demand Forecasting Model Training Pipeline.

Feature engineering, model training (Linear Regression, Random Forest,
Gradient Boosting, XGBoost), comparison, and best-model persistence.
"""

import os
import sys
import logging
import warnings
from typing import Dict, Tuple, Any

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import get_engine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "demand_forecasting_model.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "model_metrics.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoders.pkl")


def load_sales_data() -> pd.DataFrame:
    """Load and join sales + products data from database."""
    engine = get_engine()
    query = """
        SELECT s.sale_id, s.product_id, s.sale_date, s.quantity_sold, s.revenue,
               p.category, p.unit_price, p.lead_time_days, p.reorder_point
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        ORDER BY s.sale_date
    """
    df = pd.read_sql(query, engine, parse_dates=["sale_date"])
    logger.info("Loaded %d sales records for training.", len(df))
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate time-series and categorical features for demand forecasting.

    Features:
    - Temporal: month, week, quarter, day_of_week, day_of_year, year
    - Lag: lag_7, lag_14, lag_30
    - Rolling: rolling_mean_7, rolling_mean_14, rolling_mean_30
    - Seasonality: is_quarter_end, is_month_start, is_month_end
    - Holiday flags: is_festival_season, is_summer, is_winter
    - Trend: days_since_start
    - Encoded: category_encoded
    """
    df = df.copy()
    df = df.sort_values("sale_date")

    # Aggregate to daily product-level demand
    daily = df.groupby(["product_id", "sale_date", "category", "unit_price",
                         "lead_time_days", "reorder_point"]).agg(
        quantity=("quantity_sold", "sum"),
        daily_revenue=("revenue", "sum")
    ).reset_index()

    # Temporal features
    daily["month"] = daily["sale_date"].dt.month
    daily["week"] = daily["sale_date"].dt.isocalendar().week.astype(int)
    daily["quarter"] = daily["sale_date"].dt.quarter
    daily["day_of_week"] = daily["sale_date"].dt.dayofweek
    daily["day_of_year"] = daily["sale_date"].dt.dayofyear
    daily["year"] = daily["sale_date"].dt.year

    # Lag features (per product)
    for lag in [7, 14, 30]:
        daily[f"lag_{lag}"] = daily.groupby("product_id")["quantity"].shift(lag)

    # Rolling features (per product)
    for window in [7, 14, 30]:
        daily[f"rolling_mean_{window}"] = (
            daily.groupby("product_id")["quantity"]
            .transform(lambda x: x.rolling(window=window, min_periods=1).mean())
        )

    # Seasonality indicators
    daily["is_quarter_end"] = daily["sale_date"].dt.is_quarter_end.astype(int)
    daily["is_month_start"] = daily["sale_date"].dt.is_month_start.astype(int)
    daily["is_month_end"] = daily["sale_date"].dt.is_month_end.astype(int)

    # Holiday / season flags
    daily["is_festival_season"] = daily["month"].isin([10, 11, 12]).astype(int)
    daily["is_summer"] = daily["month"].isin([5, 6, 7, 8]).astype(int)
    daily["is_winter"] = daily["month"].isin([12, 1, 2]).astype(int)

    # Trend variable
    start_date = daily["sale_date"].min()
    daily["days_since_start"] = (daily["sale_date"] - start_date).dt.days

    # Encode category
    le = LabelEncoder()
    daily["category_encoded"] = le.fit_transform(daily["category"])

    # Drop rows with NaN from lag features
    daily = daily.dropna()

    logger.info("Feature engineering complete. Shape: %s", daily.shape)
    return daily, le


def get_feature_columns() -> list:
    """Return the list of feature columns used for training."""
    return [
        "month", "week", "quarter", "day_of_week", "day_of_year", "year",
        "lag_7", "lag_14", "lag_30",
        "rolling_mean_7", "rolling_mean_14", "rolling_mean_30",
        "is_quarter_end", "is_month_start", "is_month_end",
        "is_festival_season", "is_summer", "is_winter",
        "days_since_start", "category_encoded",
        "unit_price", "lead_time_days", "reorder_point"
    ]


def train_and_compare() -> Dict[str, Any]:
    """
    Train all four models, compare metrics, save best model.

    Returns dict of model results with metrics.
    """
    df = load_sales_data()
    daily_df, label_encoder = engineer_features(df)

    feature_cols = get_feature_columns()
    X = daily_df[feature_cols].values
    y = daily_df["quantity"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False  # Time-series: no shuffle
    )

    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(
            n_estimators=100, max_depth=15, random_state=42, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42
        ),
        "XGBoost": XGBRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            random_state=42, n_jobs=-1, verbosity=0
        ),
    }

    results = {}
    best_model = None
    best_r2 = -float("inf")
    best_name = ""

    for name, model in models.items():
        logger.info("Training %s...", name)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        results[name] = {
            "model": model,
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "R2": round(r2, 4),
        }

        logger.info("  %s → MAE=%.4f, RMSE=%.4f, R²=%.4f", name, mae, rmse, r2)

        if r2 > best_r2:
            best_r2 = r2
            best_model = model
            best_name = name

    # Save best model
    joblib.dump(best_model, MODEL_PATH)
    logger.info("✅ Best model: %s (R²=%.4f) saved to %s", best_name, best_r2, MODEL_PATH)

    # Save metrics for display in the UI
    metrics_summary = {name: {k: v for k, v in res.items() if k != "model"}
                       for name, res in results.items()}
    metrics_summary["best_model"] = best_name
    joblib.dump(metrics_summary, METRICS_PATH)

    # Save label encoder
    joblib.dump(label_encoder, ENCODER_PATH)

    return results


def main() -> None:
    """Run the training pipeline."""
    logger.info("=" * 60)
    logger.info("  DEMAND FORECASTING — Model Training Pipeline")
    logger.info("=" * 60)
    results = train_and_compare()
    logger.info("\n📊 Model Comparison:")
    for name, metrics in results.items():
        logger.info("  %-25s MAE=%.4f  RMSE=%.4f  R²=%.4f",
                     name, metrics["MAE"], metrics["RMSE"], metrics["R2"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
