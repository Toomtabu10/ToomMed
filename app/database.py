"""
SQLite-backed persistence for patient records and chat history.

Everything lives in one local file (patients.db) — no external DB server
needed. Swap SQLALCHEMY_DATABASE_URL for Postgres/MySQL later without
touching any other code, same as the FastAPI+SQLAlchemy pattern elsewhere.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./patients.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI's threadpool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
