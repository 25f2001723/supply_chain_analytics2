"""
SQLAlchemy ORM Models for Supply Chain Analytics Platform.

Defines all database tables: Products, Suppliers, Inventory, Sales,
PurchaseOrders, Shipments, and Users.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Supplier(Base):
    """Supplier entity representing a vendor/manufacturer."""

    __tablename__ = "suppliers"

    supplier_id: int = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name: str = Column(String(200), nullable=False)
    contact_email: str = Column(String(200), nullable=True)
    country: str = Column(String(100), nullable=False)
    on_time_delivery_rate: float = Column(Float, default=0.0)
    quality_score: float = Column(Float, default=0.0)
    rating: float = Column(Float, default=0.0)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    # Relationships
    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier(id={self.supplier_id}, name='{self.supplier_name}')>"


class Product(Base):
    """Product entity representing items in the supply chain."""

    __tablename__ = "products"

    product_id: int = Column(Integer, primary_key=True, autoincrement=True)
    product_name: str = Column(String(300), nullable=False)
    category: str = Column(String(100), nullable=False)
    unit_price: float = Column(Float, nullable=False)
    supplier_id: int = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=False)
    lead_time_days: int = Column(Integer, default=7)
    reorder_point: int = Column(Integer, default=100)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    inventory = relationship("Inventory", back_populates="product")
    sales = relationship("Sale", back_populates="product")
    purchase_orders = relationship("PurchaseOrder", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product(id={self.product_id}, name='{self.product_name}')>"


class Inventory(Base):
    """Inventory entity tracking stock levels across warehouses."""

    __tablename__ = "inventory"

    inventory_id: int = Column(Integer, primary_key=True, autoincrement=True)
    product_id: int = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    warehouse: str = Column(String(100), nullable=False)
    current_stock: int = Column(Integer, default=0)
    safety_stock: int = Column(Integer, default=50)
    last_updated: datetime = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="inventory")

    def __repr__(self) -> str:
        return f"<Inventory(id={self.inventory_id}, warehouse='{self.warehouse}', stock={self.current_stock})>"


class Sale(Base):
    """Sale entity recording individual sales transactions."""

    __tablename__ = "sales"

    sale_id: int = Column(Integer, primary_key=True, autoincrement=True)
    product_id: int = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    sale_date: datetime = Column(Date, nullable=False)
    quantity_sold: int = Column(Integer, nullable=False)
    revenue: float = Column(Float, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="sales")

    def __repr__(self) -> str:
        return f"<Sale(id={self.sale_id}, product={self.product_id}, qty={self.quantity_sold})>"


class PurchaseOrder(Base):
    """Purchase order entity tracking procurement."""

    __tablename__ = "purchase_orders"

    order_id: int = Column(Integer, primary_key=True, autoincrement=True)
    product_id: int = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    supplier_id: int = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=False)
    order_date: datetime = Column(Date, nullable=False)
    expected_delivery: datetime = Column(Date, nullable=False)
    actual_delivery: datetime = Column(Date, nullable=True)
    quantity: int = Column(Integer, nullable=False)
    status: str = Column(String(50), default="Pending")

    # Relationships
    product = relationship("Product", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")
    shipments = relationship("Shipment", back_populates="order")

    def __repr__(self) -> str:
        return f"<PurchaseOrder(id={self.order_id}, status='{self.status}')>"


class Shipment(Base):
    """Shipment entity tracking logistics and delivery."""

    __tablename__ = "shipments"

    shipment_id: int = Column(Integer, primary_key=True, autoincrement=True)
    order_id: int = Column(Integer, ForeignKey("purchase_orders.order_id"), nullable=False)
    origin: str = Column(String(200), nullable=False)
    destination: str = Column(String(200), nullable=False)
    shipping_cost: float = Column(Float, default=0.0)
    delivery_days: int = Column(Integer, default=0)
    status: str = Column(String(50), default="In Transit")

    # Relationships
    order = relationship("PurchaseOrder", back_populates="shipments")

    def __repr__(self) -> str:
        return f"<Shipment(id={self.shipment_id}, status='{self.status}')>"


class User(Base):
    """User entity for authentication and role-based access."""

    __tablename__ = "users"

    user_id: int = Column(Integer, primary_key=True, autoincrement=True)
    username: str = Column(String(100), unique=True, nullable=False)
    password_hash: str = Column(String(255), nullable=False)
    full_name: str = Column(String(200), nullable=False)
    role: str = Column(String(50), nullable=False)  # Admin, Supply Chain Manager, Analyst
    email: str = Column(String(200), nullable=True)
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, username='{self.username}', role='{self.role}')>"
