from pathlib import Path

import pytest
import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import GameConstants
from backend.core.save_manager import GameSessionManager
from backend.database import Base
from backend.main import app
from backend.models.company import Company
from backend.models.game_state import GameState
from backend.models.history import FinancialHistory


pytestmark = pytest.mark.integration


def get_response(path: str) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path)

    import asyncio

    return asyncio.run(request())


@pytest.fixture
def loaded_game_save(tmp_path: Path):
    import backend.models  # noqa: F401

    GameSessionManager.disconnect()

    db_path = tmp_path / "api_compat.db"
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
            save_name="api-compat-test",
            current_year=GameConstants.STARTING_YEAR,
            current_month=GameConstants.STARTING_MONTH,
            current_week=GameConstants.STARTING_WEEK,
            turn_number=1,
            difficulty="normal",
            simulation_speed="weekly",
        )
        db.add(game_state)
        db.flush()

        player_company = Company(
            id=1,
            game_id=game_state.id,
            name="Compat Motors",
            short_code="CMP",
            is_player=True,
            is_ai=False,
            founded_year=GameConstants.STARTING_YEAR,
            founded_turn=0,
            headquarters_region="NAM",
            cash=100.0,
        )
        db.add(player_company)
        db.flush()

        db.add(
            FinancialHistory(
                game_id=game_state.id,
                company_id=player_company.id,
                turn_number=1,
                year=GameConstants.STARTING_YEAR,
                month=GameConstants.STARTING_MONTH,
                revenue_vehicles=10_000.0,
                gross_profit=2_000.0,
                operating_profit=1_000.0,
                net_income=750.0,
                cash_end=100_000.0,
                total_assets=150_000.0,
                total_liabilities=25_000.0,
                shareholder_equity=125_000.0,
            )
        )
        db.commit()
        game_id = game_state.id
    finally:
        db.close()
        engine.dispose()

    assert GameSessionManager.connect_to_save(db_path)

    try:
        yield game_id
    finally:
        GameSessionManager.disconnect()


def test_openapi_labels_legacy_and_future_routes():
    schema = app.openapi()

    assert "/api/v1/games/{game_id}/state" in schema["paths"]
    assert "/api/v1/games/{game_id}/debug/all_companies" in schema["paths"]
    assert schema["paths"]["/api/v1/game/state"]["get"]["deprecated"] is True
    assert schema["paths"]["/api/v1/game/state"]["get"]["tags"] == ["Legacy / Game"]
    assert schema["paths"]["/api/v1/games/{game_id}/state"]["get"]["tags"] == ["Future / Games"]


def test_future_game_state_alias_matches_legacy_shape(loaded_game_save: int):
    legacy_response = get_response("/api/v1/game/state")
    future_response = get_response(f"/api/v1/games/{loaded_game_save}/state")

    assert legacy_response.status_code == 200
    assert future_response.status_code == 200
    assert future_response.json()["game_id"] == legacy_response.json()["game_id"] == loaded_game_save


def test_future_routes_reject_mismatched_game_id(loaded_game_save: int):
    response = get_response(f"/api/v1/games/{loaded_game_save + 999}/state")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "GAME_ID_MISMATCH"


def test_future_history_uses_path_game_id(loaded_game_save: int):
    response = get_response(f"/api/v1/games/{loaded_game_save}/history/sales")

    assert response.status_code == 200
    assert response.json() == []


def test_future_reports_use_path_game_id(loaded_game_save: int):
    response = get_response(f"/api/v1/games/{loaded_game_save}/reports/latest")

    assert response.status_code == 200
    assert response.json()["turn_number"] == 1
