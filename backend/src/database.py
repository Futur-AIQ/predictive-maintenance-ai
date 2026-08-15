from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from loguru import logger
import os

from src.config import settings


def get_engine(database_url: str = None):
    url = database_url or settings.database_url
    connect_args = {}
    kwargs = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # For in-memory SQLite used in tests
        if url == "sqlite:///:memory:":
            kwargs["poolclass"] = StaticPool

    return create_engine(url, connect_args=connect_args, **kwargs)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and seed default users if DB is empty."""
    from src.models.user import User
    from src.models.work_order import WorkOrder, DiagnosticSession  # noqa: F401

    # Ensure data directory exists
    if not settings.database_url.startswith("sqlite:///:memory:"):
        os.makedirs("./data", exist_ok=True)

    Base.metadata.create_all(bind=engine)
    _seed_users()


def _seed_users():
    from src.models.user import User, UserRole
    from src.auth.password import hash_password

    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return

        seed_users = [
            {
                "email": "admin@pm-system.com",
                "hashed_password": hash_password("Admin@123"),
                "full_name": "System Admin",
                "role": UserRole.admin,
            },
            {
                "email": "engineer@pm-system.com",
                "hashed_password": hash_password("Engineer@123"),
                "full_name": "John Engineer",
                "role": UserRole.engineer,
            },
        ]

        for data in seed_users:
            user = User(**data)
            db.add(user)

        db.commit()
        logger.info("Seeded default users: admin@pm-system.com, engineer@pm-system.com")
    except Exception as e:
        logger.error(f"Failed to seed users: {e}")
        db.rollback()
    finally:
        db.close()
