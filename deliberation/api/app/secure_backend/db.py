from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


Base = declarative_base()


def build_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def build_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False, class_=Session)


def db_session(session_factory) -> Generator[Session, None, None]:
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()

