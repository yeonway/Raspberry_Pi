from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_db_and_tables(seed: bool = True) -> None:
    Base.metadata.create_all(engine)
    if seed:
        from app.seed import seed_initial_data

        with SessionLocal() as session:
            seed_initial_data(session)


def get_session() -> Session:
    with SessionLocal() as session:
        yield session
