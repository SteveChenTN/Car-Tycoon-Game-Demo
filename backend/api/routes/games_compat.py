"""Future-facing game-scoped API compatibility routes.

This module keeps the current legacy handlers intact while exposing GDD-style
paths rooted at /api/v1/games/{game_id}. The wrappers are intentionally thin:
they validate the active game id, then delegate to the existing route handlers.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from backend.api.routes import (
    company,
    debug,
    diplomacy,
    engineering,
    factory,
    game,
    history,
    market,
    reports,
    staff,
)
from backend.core.dependencies import get_db_optional
from backend.core.save_manager import GameSessionManager, get_db
from backend.models import GameState


router = APIRouter(prefix="/api/v1/games")


LEGACY_PREFIXES: list[tuple[str, str]] = [
    ("/api/v1/game", "Game"),
    ("/api/v1/engineering", "Engineering"),
    ("/api/v1/factory", "Factory"),
    ("/api/v1/market", "Market"),
    ("/api/reports", "Reports"),
    ("/api/v1/history", "History"),
    ("/api/v1/staff", "Staff"),
    ("/api/v1/diplomacy", "Diplomacy"),
    ("/api/v1/company", "Company"),
    ("/api/v1/debug", "Debug"),
]


FUTURE_TAGS: list[str] = [
    "Future / Games",
    "Future / Engineering",
    "Future / Factory",
    "Future / Market",
    "Future / Reports",
    "Future / History",
    "Future / Staff",
    "Future / Diplomacy",
    "Future / Company",
    "Future / Debug",
]


def _no_game_loaded_detail() -> Dict[str, Any]:
    return {
        "error": "NO_GAME_LOADED",
        "message": "Create or load a game before using game-scoped API routes.",
        "legacy_actions": {
            "new": "POST /api/v1/game/new",
            "load": "POST /api/v1/game/load",
        },
        "future_actions": {
            "new": "POST /api/v1/games",
            "load": "POST /api/v1/games/load",
        },
    }


def validate_game_scope(game_id: int) -> None:
    """Ensure a future-facing path points at the currently loaded game."""
    if not GameSessionManager.is_game_loaded():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_no_game_loaded_detail(),
        )

    session_factory = GameSessionManager.get_current_session_factory()
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_no_game_loaded_detail(),
        )

    db = session_factory()
    try:
        current_game = db.query(GameState).first()
        if current_game is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NO_GAME_FOUND",
                    "message": "The active save does not contain a game state.",
                },
            )

        if current_game.id != game_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "GAME_ID_MISMATCH",
                    "message": (
                        f"Requested game_id {game_id} does not match the "
                        f"currently loaded game_id {current_game.id}."
                    ),
                    "current_game_id": current_game.id,
                    "requested_game_id": game_id,
                },
            )
    finally:
        db.close()


def _alias_description(route: APIRoute) -> str:
    legacy_path = route.path_format
    base = f"Future-facing alias for legacy `{legacy_path}`."
    if route.description:
        return f"{base}\n\n{route.description}"
    return base


def _add_alias_routes(
    source_router: APIRouter,
    source_prefix: str,
    target_prefix: str,
    tag: str,
    exclude_suffixes: set[str] | None = None,
) -> None:
    exclude_suffixes = exclude_suffixes or set()

    for route in source_router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(source_prefix):
            continue

        suffix = route.path[len(source_prefix):]
        if suffix in exclude_suffixes:
            continue

        router.add_api_route(
            path=f"{target_prefix}{suffix}",
            endpoint=route.endpoint,
            methods=list(route.methods or []),
            response_model=route.response_model,
            status_code=route.status_code,
            tags=[f"Future / {tag}"],
            dependencies=[Depends(validate_game_scope), *route.dependencies],
            summary=route.summary,
            description=_alias_description(route),
            response_description=route.response_description,
            responses=route.responses,
            deprecated=False,
            operation_id=None,
            response_class=route.response_class,
            name=f"future_{tag.lower()}_{route.name}",
            callbacks=route.callbacks,
            openapi_extra={
                **(route.openapi_extra or {}),
                "x-api-status": "future-facing",
                "x-legacy-path": route.path_format,
            },
        )


@router.post(
    "",
    response_model=Dict[str, Any],
    tags=["Future / Games"],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/game/new"},
)
async def create_game(request: game.NewGameRequest) -> Dict[str, Any]:
    """Create a new game save using the future-facing collection route."""
    return await game.create_new_game(request)


@router.post(
    "/load",
    response_model=Dict[str, Any],
    tags=["Future / Games"],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/game/load"},
)
async def load_game(request: game.LoadGameRequest) -> Dict[str, Any]:
    """Load a saved game using the future-facing collection route."""
    return await game.load_saved_game(request)


@router.get(
    "/saves",
    response_model=Dict[str, Any],
    tags=["Future / Games"],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/game/saves"},
)
async def list_game_saves() -> Dict[str, Any]:
    """List game saves using the future-facing collection route."""
    return await game.list_saved_games()


@router.delete(
    "/saves",
    response_model=Dict[str, Any],
    tags=["Future / Games"],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/game/save"},
)
async def delete_game_save(request: game.DeleteSaveRequest) -> Dict[str, Any]:
    """Delete a game save using the future-facing collection route."""
    return await game.delete_saved_game(request)


@router.get(
    "/{game_id}/reports/latest",
    response_model=reports.MonthlyReport,
    tags=["Future / Reports"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/reports/latest"},
)
async def get_latest_report_for_game(
    game_id: int,
    db: Optional[Session] = Depends(get_db_optional),
) -> reports.MonthlyReport:
    """Get the latest report without requiring query parameter game_id."""
    return await reports.get_latest_monthly_report(game_id=game_id, db=db)


@router.get(
    "/{game_id}/reports/monthly",
    response_model=reports.MonthlyReport,
    tags=["Future / Reports"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/reports/monthly"},
)
async def get_monthly_report_for_game(
    game_id: int,
    turn_number: int = Query(..., description="Turn number"),
    db: Optional[Session] = Depends(get_db_optional),
) -> reports.MonthlyReport:
    """Get a monthly report without requiring query parameter game_id."""
    return await reports.get_monthly_report(game_id=game_id, turn_number=turn_number, db=db)


@router.get(
    "/{game_id}/reports/financial",
    response_model=Dict[str, Any],
    tags=["Future / Reports"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/reports/financial"},
)
async def get_financial_report_for_game(
    game_id: int,
    company_id: int = Query(..., description="Company ID"),
    limit: int = Query(24, ge=1, le=120, description="Record limit"),
    db: Optional[Session] = Depends(get_db_optional),
) -> Dict[str, Any]:
    """Get the financial report page without requiring query parameter game_id."""
    return await reports.get_financial_report_page(
        game_id=game_id,
        company_id=company_id,
        limit=limit,
        db=db,
    )


@router.get(
    "/{game_id}/engineering/research-projects",
    response_model=List[Dict[str, Any]],
    tags=["Future / Engineering"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={
        "x-api-status": "future-facing",
        "x-legacy-path": "/api/v1/engineering/research-projects",
    },
)
async def list_research_projects_for_game(
    game_id: int,
    company_id: Optional[int] = Query(None, description="Company ID filter"),
    db: Optional[Session] = Depends(get_db_optional),
) -> List[Dict[str, Any]]:
    """List research projects without requiring query parameter game_id."""
    return await engineering.list_research_projects(
        company_id=company_id,
        game_id=game_id,
        db=db,
    )


@router.get(
    "/{game_id}/history/sales",
    response_model=List[history.SalesHistoryResponse],
    tags=["Future / History"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/history/sales"},
)
def get_sales_history_for_game(
    game_id: int,
    company_id: Optional[int] = Query(None, description="Company ID filter"),
    region_id: Optional[int] = Query(None, description="Region ID filter"),
    trim_id: Optional[int] = Query(None, description="Trim ID filter"),
    start_turn: Optional[int] = Query(None, description="Start turn"),
    end_turn: Optional[int] = Query(None, description="End turn"),
    limit: int = Query(100, ge=1, le=1000, description="Record limit"),
    db: Session = Depends(get_db),
) -> List[history.SalesHistoryResponse]:
    return history.get_sales_history(
        game_id=game_id,
        company_id=company_id,
        region_id=region_id,
        trim_id=trim_id,
        start_turn=start_turn,
        end_turn=end_turn,
        limit=limit,
        db=db,
    )


@router.get(
    "/{game_id}/history/financial",
    response_model=List[history.FinancialHistoryResponse],
    tags=["Future / History"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/history/financial"},
)
def get_financial_history_for_game(
    game_id: int,
    company_id: int = Query(..., description="Company ID"),
    start_turn: Optional[int] = Query(None, description="Start turn"),
    end_turn: Optional[int] = Query(None, description="End turn"),
    limit: int = Query(100, ge=1, le=1000, description="Record limit"),
    db: Session = Depends(get_db),
) -> List[history.FinancialHistoryResponse]:
    return history.get_financial_history(
        game_id=game_id,
        company_id=company_id,
        start_turn=start_turn,
        end_turn=end_turn,
        limit=limit,
        db=db,
    )


@router.get(
    "/{game_id}/history/used-cars",
    response_model=List[history.UsedCarListingResponse],
    tags=["Future / History"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/history/used-cars"},
)
def get_used_car_listings_for_game(
    game_id: int,
    region_id: Optional[int] = Query(None, description="Region ID filter"),
    car_trim_id: Optional[int] = Query(None, description="Car trim ID filter"),
    max_age: Optional[int] = Query(None, ge=0, le=20, description="Maximum age"),
    min_condition: Optional[float] = Query(None, ge=0, le=100, description="Minimum condition"),
    db: Session = Depends(get_db),
) -> List[history.UsedCarListingResponse]:
    return history.get_used_car_listings(
        game_id=game_id,
        region_id=region_id,
        car_trim_id=car_trim_id,
        max_age=max_age,
        min_condition=min_condition,
        db=db,
    )


@router.get(
    "/{game_id}/history/sales/summary",
    tags=["Future / History"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/history/sales/summary"},
)
def get_sales_summary_for_game(
    game_id: int,
    company_id: int = Query(..., description="Company ID"),
    period_turns: int = Query(12, ge=1, le=120, description="Period length in turns"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return history.get_sales_summary(
        game_id=game_id,
        company_id=company_id,
        period_turns=period_turns,
        db=db,
    )


@router.get(
    "/{game_id}/history/financial/summary",
    tags=["Future / History"],
    dependencies=[Depends(validate_game_scope)],
    openapi_extra={"x-api-status": "future-facing", "x-legacy-path": "/api/v1/history/financial/summary"},
)
def get_financial_summary_for_game(
    game_id: int,
    company_id: int = Query(..., description="Company ID"),
    period_turns: int = Query(12, ge=1, le=120, description="Period length in turns"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return history.get_financial_summary(
        game_id=game_id,
        company_id=company_id,
        period_turns=period_turns,
        db=db,
    )


_add_alias_routes(
    game.router,
    "/api/v1/game",
    "/{game_id}",
    "Games",
    exclude_suffixes={"/new", "/load", "/saves", "/save"},
)
_add_alias_routes(
    engineering.router,
    "/api/v1/engineering",
    "/{game_id}/engineering",
    "Engineering",
    exclude_suffixes={"/research-projects"},
)
_add_alias_routes(factory.router, "/api/v1/factory", "/{game_id}/factory", "Factory")
_add_alias_routes(market.router, "/api/v1/market", "/{game_id}/market", "Market")
_add_alias_routes(staff.router, "/api/v1/staff", "/{game_id}/staff", "Staff")
_add_alias_routes(diplomacy.router, "/api/v1/diplomacy", "/{game_id}/diplomacy", "Diplomacy")
_add_alias_routes(company.router, "/api/v1/company", "/{game_id}/companies", "Company")
_add_alias_routes(debug.router, "/api/v1/debug", "/{game_id}/debug", "Debug")


def configure_api_documentation(app: Any) -> None:
    """Mark legacy routes and register tag descriptions for Swagger."""
    app.openapi_tags = [
        {
            "name": tag,
            "description": "Future-facing GDD-aligned route group.",
        }
        for tag in FUTURE_TAGS
    ] + [
        {
            "name": f"Legacy / {name}",
            "description": f"Deprecated compatibility routes under `{prefix}`.",
        }
        for prefix, name in LEGACY_PREFIXES
    ]

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for prefix, name in LEGACY_PREFIXES:
            if route.path == prefix or route.path.startswith(f"{prefix}/"):
                route.deprecated = True
                route.tags = [f"Legacy / {name}"]
                route.openapi_extra = {
                    **(route.openapi_extra or {}),
                    "x-api-status": "legacy",
                }
                break


__all__ = ["router", "configure_api_documentation", "validate_game_scope"]
