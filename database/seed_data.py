"""
Seed Data Generator for Supply Chain Analytics Platform.

Generates realistic sample data using Faker:
- 100 suppliers
- 500 products (across 10 categories)
- 20 warehouses with inventory records
- 50,000 sales records (3 years, with seasonality)
- 10,000 purchase orders
- 10,000 shipment records
- Default users (Admin, Manager, Analyst)
"""

import os
import sys
import random
import logging
from datetime import datetime, timedelta, date
from typing import List

import bcrypt
from faker import Faker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import init_db, get_db
from database.models import (
    Base, Supplier, Product, Inventory, Sale, PurchaseOrder, Shipment, User
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()
Faker.seed(42)
random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────────

CATEGORIES = [
    "Electronics", "Clothing", "Home & Kitchen", "Sports & Outdoors",
    "Books & Stationery", "Health & Beauty", "Automotive", "Food & Beverages",
    "Toys & Games", "Industrial Supplies"
]

PRODUCT_PREFIXES = {
    "Electronics": ["Wireless", "Smart", "Digital", "Pro", "Ultra", "Nano", "Quantum"],
    "Clothing": ["Premium", "Classic", "Urban", "Elite", "Comfort", "Active", "Eco"],
    "Home & Kitchen": ["Deluxe", "Modern", "Chef's", "Artisan", "Essential", "Gourmet", "Compact"],
    "Sports & Outdoors": ["Pro", "Endurance", "Trailblazer", "Summit", "Velocity", "Titan", "Flex"],
    "Books & Stationery": ["Academic", "Creative", "Professional", "Student", "Executive", "Bright", "Scholar"],
    "Health & Beauty": ["Natural", "Radiance", "Vital", "Pure", "Glow", "Organic", "Luxe"],
    "Automotive": ["Turbo", "Precision", "Heavy-Duty", "Racing", "All-Terrain", "Carbon", "Iron"],
    "Food & Beverages": ["Organic", "Artisan", "Fresh", "Premium", "Harvest", "Golden", "Royal"],
    "Toys & Games": ["Adventure", "Magic", "Super", "Wonder", "Epic", "Power", "Star"],
    "Industrial Supplies": ["Industrial", "Commercial", "Heavy", "Precision", "Ultra", "Max", "Steel"],
}

PRODUCT_ITEMS = {
    "Electronics": ["Headphones", "Keyboard", "Mouse", "Monitor", "Speaker", "Camera", "Tablet", "Router", "Charger", "Drone"],
    "Clothing": ["Jacket", "T-Shirt", "Jeans", "Sneakers", "Hoodie", "Blazer", "Shorts", "Polo", "Sweater", "Cap"],
    "Home & Kitchen": ["Blender", "Cookware Set", "Knife Set", "Coffee Maker", "Toaster", "Vacuum", "Lamp", "Cushion", "Pan", "Mug Set"],
    "Sports & Outdoors": ["Yoga Mat", "Dumbbells", "Tent", "Bicycle", "Backpack", "Water Bottle", "Helmet", "Gloves", "Bat", "Racket"],
    "Books & Stationery": ["Notebook", "Pen Set", "Planner", "Textbook", "Markers", "Binder", "Calculator", "Ruler Set", "Eraser Pack", "Stapler"],
    "Health & Beauty": ["Moisturizer", "Sunscreen", "Shampoo", "Serum", "Face Wash", "Lip Balm", "Body Lotion", "Perfume", "Hair Oil", "Cream"],
    "Automotive": ["Brake Pads", "Engine Oil", "Tire", "Battery", "Air Filter", "Spark Plug", "Wiper Blade", "Horn", "Jack", "Toolkit"],
    "Food & Beverages": ["Tea Blend", "Coffee Beans", "Honey", "Protein Bar", "Juice", "Cereal", "Pasta", "Olive Oil", "Spice Set", "Snack Box"],
    "Toys & Games": ["Board Game", "Puzzle", "Action Figure", "Building Blocks", "Doll", "RC Car", "Card Game", "Plush Toy", "Science Kit", "Art Set"],
    "Industrial Supplies": ["Safety Goggles", "Drill Bit Set", "Cable Ties", "Welding Rod", "Bearing", "Valve", "Pump", "Generator Part", "Bolt Set", "Lubricant"],
}

WAREHOUSES = [
    "Mumbai Central", "Delhi NCR Hub", "Bangalore Tech Park", "Chennai Port",
    "Hyderabad Logistics", "Kolkata East", "Pune Distribution", "Ahmedabad West",
    "Jaipur Depot", "Lucknow Center", "Kochi Maritime", "Chandigarh North",
    "Bhopal Central", "Indore Industrial", "Nagpur Warehouse",
    "New York Hub", "London Distribution", "Singapore Port", "Dubai Logistics", "Tokyo Center"
]

COUNTRIES = [
    "India", "China", "USA", "Germany", "Japan", "South Korea", "Taiwan",
    "Vietnam", "Bangladesh", "Thailand", "Mexico", "Brazil", "Turkey",
    "Italy", "France", "UK", "Canada", "Australia", "Malaysia", "Indonesia"
]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Shanghai", "Shenzhen",
    "New York", "Los Angeles", "London", "Berlin", "Tokyo", "Seoul",
    "Singapore", "Dubai", "Sydney", "Toronto", "São Paulo", "Istanbul",
    "Bangkok", "Ho Chi Minh City"
]


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _get_seasonality_multiplier(sale_date: date, category: str) -> float:
    """
    Return a seasonality multiplier based on month and category.

    Electronics  → peak Oct-Dec (festivals/holidays)
    Clothing     → peaks in seasonal transitions (Mar-Apr, Sep-Nov)
    Sports       → peak summer (May-Aug)
    Books        → peak Jun-Aug (academic sessions)
    Food         → slight holiday bump (Nov-Dec)
    """
    month = sale_date.month

    multipliers = {
        "Electronics": {10: 1.6, 11: 2.0, 12: 2.2, 1: 1.3, 7: 1.4},
        "Clothing": {3: 1.4, 4: 1.5, 9: 1.6, 10: 1.8, 11: 1.5},
        "Sports & Outdoors": {5: 1.5, 6: 1.7, 7: 1.8, 8: 1.6},
        "Books & Stationery": {6: 1.8, 7: 2.0, 8: 1.6, 1: 1.3},
        "Food & Beverages": {11: 1.3, 12: 1.5, 1: 1.2},
        "Health & Beauty": {3: 1.3, 4: 1.4, 11: 1.3, 12: 1.5},
        "Toys & Games": {11: 1.8, 12: 2.5, 1: 1.2},
        "Home & Kitchen": {10: 1.4, 11: 1.6, 12: 1.3, 1: 1.2},
        "Automotive": {4: 1.3, 5: 1.4, 10: 1.3},
        "Industrial Supplies": {3: 1.2, 4: 1.3, 9: 1.2, 10: 1.3},
    }

    cat_mult = multipliers.get(category, {})
    return cat_mult.get(month, 1.0)


def _add_trend(sale_date: date, start_date: date) -> float:
    """Add a gentle upward trend over 3 years (simulates business growth)."""
    days_elapsed = (sale_date - start_date).days
    total_days = 365 * 3
    return 1.0 + 0.3 * (days_elapsed / total_days)


def seed_users(session) -> None:
    """Create default users with hashed passwords."""
    users = [
        User(
            username="admin",
            password_hash=_hash_password("admin123"),
            full_name="System Administrator",
            role="Admin",
            email="admin@supplychain.com",
        ),
        User(
            username="manager",
            password_hash=_hash_password("manager123"),
            full_name="Rajesh Kumar",
            role="Supply Chain Manager",
            email="rajesh.kumar@supplychain.com",
        ),
        User(
            username="analyst",
            password_hash=_hash_password("analyst123"),
            full_name="Priya Sharma",
            role="Analyst",
            email="priya.sharma@supplychain.com",
        ),
    ]
    session.add_all(users)
    session.commit()
    logger.info("✅ Created %d users.", len(users))


def seed_suppliers(session) -> List[Supplier]:
    """Generate 100 realistic suppliers."""
    suppliers: List[Supplier] = []
    for i in range(100):
        supplier = Supplier(
            supplier_name=fake.company(),
            contact_email=fake.company_email(),
            country=random.choice(COUNTRIES),
            on_time_delivery_rate=round(random.uniform(0.70, 0.99), 2),
            quality_score=round(random.uniform(3.0, 5.0), 1),
            rating=round(random.uniform(2.5, 5.0), 1),
        )
        suppliers.append(supplier)
    session.add_all(suppliers)
    session.commit()
    logger.info("✅ Created %d suppliers.", len(suppliers))
    return suppliers


def seed_products(session, suppliers: List[Supplier]) -> List[Product]:
    """Generate 500 products spread across categories."""
    products: List[Product] = []
    for i in range(500):
        category = CATEGORIES[i % len(CATEGORIES)]
        prefix = random.choice(PRODUCT_PREFIXES[category])
        item = random.choice(PRODUCT_ITEMS[category])
        variant = random.choice(["X1", "V2", "Pro", "Lite", "Max", "Plus", "SE", ""])
        product_name = f"{prefix} {item} {variant}".strip()

        product = Product(
            product_name=product_name,
            category=category,
            unit_price=round(random.uniform(5.0, 2500.0), 2),
            supplier_id=random.choice(suppliers).supplier_id,
            lead_time_days=random.randint(3, 30),
            reorder_point=random.randint(50, 300),
        )
        products.append(product)
    session.add_all(products)
    session.commit()
    logger.info("✅ Created %d products.", len(products))
    return products


def seed_inventory(session, products: List[Product]) -> None:
    """Generate inventory records — each product in 1-4 warehouses."""
    records = []
    for product in products:
        num_warehouses = random.randint(1, 4)
        chosen_warehouses = random.sample(WAREHOUSES, num_warehouses)
        for wh in chosen_warehouses:
            safety = random.randint(20, 150)
            # Some products low-stock to create interesting alerts
            if random.random() < 0.15:
                current = random.randint(0, safety)  # below safety stock
            else:
                current = random.randint(safety, safety * 5)

            inv = Inventory(
                product_id=product.product_id,
                warehouse=wh,
                current_stock=current,
                safety_stock=safety,
                last_updated=fake.date_time_between(start_date="-30d", end_date="now"),
            )
            records.append(inv)
    session.add_all(records)
    session.commit()
    logger.info("✅ Created %d inventory records.", len(records))


def seed_sales(session, products: List[Product]) -> None:
    """Generate 50,000 sales records spanning 3 years with seasonality."""
    end_date = date.today()
    start_date = end_date - timedelta(days=3 * 365)
    total_days = (end_date - start_date).days

    sales = []
    for i in range(50000):
        product = random.choice(products)
        sale_date = start_date + timedelta(days=random.randint(0, total_days))

        # Apply seasonality and trend
        base_qty = random.randint(1, 50)
        seasonal_mult = _get_seasonality_multiplier(sale_date, product.category)
        trend_mult = _add_trend(sale_date, start_date)
        quantity = max(1, int(base_qty * seasonal_mult * trend_mult))

        revenue = round(quantity * product.unit_price * random.uniform(0.85, 1.15), 2)

        sale = Sale(
            product_id=product.product_id,
            sale_date=sale_date,
            quantity_sold=quantity,
            revenue=revenue,
        )
        sales.append(sale)

        # Batch insert every 5000 records
        if len(sales) >= 5000:
            session.add_all(sales)
            session.commit()
            logger.info("  ... inserted %d / 50000 sales", i + 1)
            sales = []

    if sales:
        session.add_all(sales)
        session.commit()
    logger.info("✅ Created 50,000 sales records.")


def seed_purchase_orders(session, products: List[Product], suppliers: List[Supplier]) -> List[PurchaseOrder]:
    """Generate 10,000 purchase orders over 3 years."""
    end_date = date.today()
    start_date = end_date - timedelta(days=3 * 365)
    total_days = (end_date - start_date).days
    statuses = ["Delivered", "Delivered", "Delivered", "Delivered",
                "In Transit", "In Transit", "Pending", "Cancelled"]

    orders: List[PurchaseOrder] = []
    for i in range(10000):
        product = random.choice(products)
        order_date = start_date + timedelta(days=random.randint(0, total_days))
        lead = product.lead_time_days + random.randint(-3, 10)
        expected = order_date + timedelta(days=max(1, lead))
        status = random.choice(statuses)

        if status == "Delivered":
            delay = random.randint(-2, 8)
            actual = expected + timedelta(days=delay)
        else:
            actual = None

        order = PurchaseOrder(
            product_id=product.product_id,
            supplier_id=product.supplier_id,
            order_date=order_date,
            expected_delivery=expected,
            actual_delivery=actual,
            quantity=random.randint(50, 2000),
            status=status,
        )
        orders.append(order)

        if len(orders) >= 5000:
            session.add_all(orders)
            session.commit()
            logger.info("  ... inserted %d / 10000 orders", i + 1)
            orders_to_return = orders.copy() if i < 5000 else []
            orders = []

    if orders:
        session.add_all(orders)
        session.commit()
    logger.info("✅ Created 10,000 purchase orders.")

    # Re-query all orders for shipment generation
    from database.models import PurchaseOrder as PO
    all_orders = session.query(PO).all()
    return all_orders


def seed_shipments(session, orders: List[PurchaseOrder]) -> None:
    """Generate 10,000 shipment records linked to purchase orders."""
    shipment_statuses = ["Delivered", "Delivered", "Delivered",
                         "In Transit", "In Transit", "Delayed", "Returned"]

    # Take a sample of orders for shipments
    sampled_orders = random.sample(orders, min(10000, len(orders)))

    shipments = []
    for i, order in enumerate(sampled_orders):
        origin = random.choice(CITIES)
        destination = random.choice([c for c in CITIES if c != origin])
        status = random.choice(shipment_statuses)

        shipment = Shipment(
            order_id=order.order_id,
            origin=origin,
            destination=destination,
            shipping_cost=round(random.uniform(50.0, 5000.0), 2),
            delivery_days=random.randint(1, 25),
            status=status,
        )
        shipments.append(shipment)

        if len(shipments) >= 5000:
            session.add_all(shipments)
            session.commit()
            logger.info("  ... inserted %d / 10000 shipments", i + 1)
            shipments = []

    if shipments:
        session.add_all(shipments)
        session.commit()
    logger.info("✅ Created 10,000 shipment records.")


def main() -> None:
    """Run the complete database seeding pipeline."""
    logger.info("=" * 60)
    logger.info("  SUPPLY CHAIN ANALYTICS — Database Seeding")
    logger.info("=" * 60)

    init_db()
    session = get_db()

    try:
        # Check if data already exists
        existing = session.query(Product).first()
        if existing:
            logger.warning("Database already contains data. Clearing all tables...")
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())
            session.commit()
            logger.info("Tables cleared.")

        logger.info("\n📦 Seeding Users...")
        seed_users(session)

        logger.info("\n🏭 Seeding Suppliers...")
        suppliers = seed_suppliers(session)

        logger.info("\n📋 Seeding Products...")
        products = seed_products(session, suppliers)

        logger.info("\n📦 Seeding Inventory...")
        seed_inventory(session, products)

        logger.info("\n💰 Seeding Sales...")
        seed_sales(session, products)

        logger.info("\n📝 Seeding Purchase Orders...")
        orders = seed_purchase_orders(session, products, suppliers)

        logger.info("\n🚚 Seeding Shipments...")
        seed_shipments(session, orders)

        logger.info("\n" + "=" * 60)
        logger.info("  ✅ DATABASE SEEDING COMPLETE!")
        logger.info("=" * 60)

        # Summary
        logger.info("  Suppliers:        %d", session.query(Supplier).count())
        logger.info("  Products:         %d", session.query(Product).count())
        logger.info("  Inventory:        %d", session.query(Inventory).count())
        logger.info("  Sales:            %d", session.query(Sale).count())
        logger.info("  Purchase Orders:  %d", session.query(PurchaseOrder).count())
        logger.info("  Shipments:        %d", session.query(Shipment).count())
        logger.info("  Users:            %d", session.query(User).count())

    except Exception as e:
        session.rollback()
        logger.error("Seeding failed: %s", e)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
