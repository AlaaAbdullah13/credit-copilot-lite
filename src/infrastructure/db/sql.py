import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./credit_copilot.db")

Base = declarative_base()


def create_session_factory(database_url: str | None = None):
    url = database_url or DATABASE_URL
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


SessionLocal = create_session_factory()
