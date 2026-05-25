"""
Database connection and session management.

Provides SQLAlchemy engine creation, session factory, and helper functions
for the Supply Chain Analytics Platform.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

logger = logging.getLogger(__name__)

# Database path — store alongside this module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "supply_chain.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables defined in models.py."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def get_db() -> Session:
    """Return a new database session. Caller must close it."""
    return SessionLocal()


def get_engine():
    """Return the SQLAlchemy engine for raw pandas queries."""
    return engine
