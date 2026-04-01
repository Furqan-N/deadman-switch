import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()


def get_database_url():
    """Build database URL from environment variables."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    database = os.environ.get("DB_NAME")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
