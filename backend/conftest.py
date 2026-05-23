from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import GameConstants
from backend.core.loader import GameDataLoader
from backend.database import Base
from backend.models.company import Company
from backend.models.game_state import GameState


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def assets_data_dir(project_root: Path) -> Path:
    data_dir = project_root / "assets" / "data"
    assert data_dir.exists(), f"Missing assets data directory: {data_dir}"
    return data_dir


@pytest.fixture(scope="session")
def game_data_loader(assets_data_dir: Path) -> GameDataLoader:
    loader = GameDataLoader(str(assets_data_dir))
    loader.load_all_data()
    return loader


@pytest.fixture
def isolated_db_session(tmp_path):
    import backend.models  # noqa: F401

    db_path = tmp_path / "automogul_test.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    try:
        game_state = GameState(
            save_name="pytest-isolated",
            current_year=GameConstants.STARTING_YEAR,
            current_month=GameConstants.STARTING_MONTH,
            current_week=GameConstants.STARTING_WEEK,
            turn_number=0,
            difficulty="normal",
            simulation_speed="weekly",
        )
        db.add(game_state)
        db.flush()

        player_company = Company(
            id=1,
            game_id=game_state.id,
            name="Pytest Motors",
            short_code="PYT",
            is_player=True,
            is_ai=False,
            founded_year=GameConstants.STARTING_YEAR,
            founded_turn=0,
            headquarters_region="NAM",
        )
        db.add(player_company)
        db.commit()

        yield db
    finally:
        db.close()
        engine.dispose()
