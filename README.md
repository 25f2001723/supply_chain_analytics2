# Supply Chain Analytics Platform

A Streamlit-based supply chain analytics dashboard for inventory, supplier, logistics, and forecasting operations.

## Overview

This project provides an end-to-end analytics application built with Python and Streamlit. It includes user authentication, an executive dashboard, demand forecasting, inventory management, logistics analytics, supplier performance reporting, and exportable reports.

## Key Features

- **User authentication** with demo accounts for Admin, Manager, and Analyst roles
- **Executive dashboard** showing revenue, orders, inventory value, forecast accuracy, supplier counts, and shipment delays
- **Demand forecasting** powered by a pre-trained ML model with product selection and scenario analysis
- **Inventory management** with stock health classification, warehouse utilization, and download support
- **Logistics analytics** for shipments, delays, route performance, and delay risk estimation
- **Supplier analytics** with ranking tiers, scorecards, and procurement recommendations
- **Reporting** with CSV, Excel, and PDF export for sales, inventory, supplier, logistics, and forecasting summaries
- **Seed data generation** for realistic sample data across suppliers, products, inventory, sales, orders, and shipments

## Tech Stack

- Python
- Streamlit
- SQLAlchemy + SQLite
- Pandas, NumPy
- Plotly
- Scikit-learn / XGBoost
- Faker for sample data generation
- bcrypt for password hashing

## Getting Started

### Requirements

- Python 3.12+ (virtual environment recommended)
- Dependencies listed in `supply_chain_analytics/requirements.txt`

### Installation

```bash
cd "e:/summer training/final_project"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r supply_chain_analytics/requirements.txt
```

### Run the App

```bash
cd "e:/summer training/final_project"
.\.venv\Scripts\python.exe -m streamlit run supply_chain_analytics/app.py
```

Then open the local URL displayed by Streamlit, typically `http://localhost:8502`.

## Demo Credentials

- Admin: `admin / admin123`
- Manager: `manager / manager123`
- Analyst: `analyst / analyst123`

## Project Structure

- `supply_chain_analytics/app.py` — Streamlit app entrypoint and sidebar router
- `supply_chain_analytics/database/` — SQLAlchemy database setup, models, and seed data
- `supply_chain_analytics/ml/` — forecasting model training and prediction logic
- `supply_chain_analytics/app_pages/` — page render functions for dashboard, forecasting, inventory, logistics, reports, and suppliers
- `supply_chain_analytics/services/` — business logic and analytics service classes
- `supply_chain_analytics/supply_chain.db` — SQLite database file with seeded sample data

## Notes

- If the forecasting page does not show data, ensure the ML model has been trained or the `ml/demand_forecasting_model.pkl` file is present.
- The project uses native Streamlit sidebar navigation configured in `app.py`.
- To regenerate or inspect seed data, use the seeding logic in `supply_chain_analytics/database/seed_data.py`.

## License

Add your chosen license here.
