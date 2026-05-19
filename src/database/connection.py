# src/database/connection.py — SIMPLIFIED VERSION

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_database_url():
    # Try environment variable first, fall back to SQLite
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Default: SQLite file in project root — zero setup needed
    return "sqlite:///./disaster_ai.db"


DATABASE_URL = get_database_url()

# SQLite needs check_same_thread=False
connect_args = {"check_same_thread": False} \
               if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False  # Set True to see SQL queries during development
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all tables on startup.
    Replaces Alembic migrations for simple deployments.
    When you later move to PostgreSQL, switch back to Alembic.
    """
    from src.database import models  # Import so tables are registered
    Base.metadata.create_all(bind=engine)
    print(f"Database initialised: {DATABASE_URL}")
