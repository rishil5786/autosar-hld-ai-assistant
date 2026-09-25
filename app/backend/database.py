"""
AUTOSAR HLD AI - Database Connection and Session Management
SQLite database setup with SQLAlchemy.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from app.utils.config import settings
from app.utils.logger import logger
from app.backend.models import Base

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables and create default data."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    # Create default admin user if not exists
    from app.backend.models import User, UserRole
    from app.utils.security import hash_password

    with get_db_session() as db:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@autosar-hld.local",
                password_hash=hash_password("admin123"),
                full_name="System Administrator",
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(admin)

            # Create demo engineer
            engineer = User(
                username="engineer",
                email="engineer@autosar-hld.local",
                password_hash=hash_password("engineer123"),
                full_name="Demo Engineer",
                role=UserRole.ENGINEER.value,
                is_active=True
            )
            db.add(engineer)

            # Create demo reviewer
            reviewer = User(
                username="reviewer",
                email="reviewer@autosar-hld.local",
                password_hash=hash_password("reviewer123"),
                full_name="Demo Reviewer",
                role=UserRole.REVIEWER.value,
                is_active=True
            )
            db.add(reviewer)

            db.commit()
            logger.info("Default users created: admin, engineer, reviewer")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session as a context manager."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI endpoints."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
