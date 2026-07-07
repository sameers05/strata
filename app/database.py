import os
from pathlib import Path
from collections.abc import Generator

from sqlmodel import Session, create_engine

DEFAULT_DATABASE_URL = "sqlite:///./data/strata.db"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

if DATABASE_URL.startswith("sqlite:///./"):
    db_path = Path(DATABASE_URL.removeprefix("sqlite:///./"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
