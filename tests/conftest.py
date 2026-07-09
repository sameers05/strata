from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.models import GroupTask, Project  # noqa: F401 — ensures the tables are registered on SQLModel.metadata


def _isolated_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = _isolated_engine()
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = _isolated_engine()

    def override_get_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_session, None)
    engine.dispose()
