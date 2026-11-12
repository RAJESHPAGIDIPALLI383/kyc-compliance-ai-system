
from pathlib import Path
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]

DEPLOYMENT_DATABASE = (
    ROOT_DIR / "deployment_data" / "kyc_compliance.db"
)

DEFAULT_DATABASE_URL = f"sqlite:///{DEPLOYMENT_DATABASE.as_posix()}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.app.models import entities

    Base.metadata.create_all(bind=engine)

    print("Database initialized successfully!")
    print("Database URL:", DATABASE_URL)
    print("Tables:", list(Base.metadata.tables.keys()))
