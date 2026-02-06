"""
Database configuration and session management
"""

import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Generator
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create sync engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=10,
    pool_pre_ping=True,  # Enable connection health checks
    echo=settings.DEBUG,
)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Prevent lazy loading issues after commit
)


# Base class for all models
class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Get database session dependency for FastAPI.

    IMPORTANT: This does NOT auto-commit. Each endpoint must explicitly
    call db.commit() when changes should be persisted.
    This prevents accidental commits when HTTPExceptions are raised.

    Usage:
        @router.post("/items")
        async def create_item(item: Item, db: Session = Depends(get_db)):
            db_item = DBItem(**item.dict())
            db.add(db_item)
            db.commit()  # Explicit commit required
            db.refresh(db_item)
            return db_item
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions (for use outside FastAPI).

    Usage:
        with get_db_session() as db:
            user = db.query(User).first()
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Check if database connection is available.
    Returns True if connected, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def check_redis_connection() -> bool:
    """
    Check if Redis connection is available.
    Returns True if connected, False otherwise.
    """
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        r.ping()
        r.close()
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def get_health_status() -> dict:
    """
    Get health status of all database connections.
    Returns a dictionary with connection statuses.
    """
    db_connected = check_database_connection()
    redis_connected = check_redis_connection()

    return {
        "database": "connected" if db_connected else "disconnected",
        "redis": "connected" if redis_connected else "disconnected",
        "healthy": db_connected and redis_connected
    }
