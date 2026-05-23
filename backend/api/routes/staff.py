"""
Staff management API routes.

This module is the canonical public API for staff and executive management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import Company, GameState, Staff
from backend.core.management.hr import HRSystem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/staff", tags=["Staff"])


class FireStaffRequest(BaseModel):
    company_id: int
    staff_id: int
    severance_multiplier: float = 1.0


class HireStaffRequest(BaseModel):
    company_id: int
    candidate_id: int
    offered_salary: Optional[float] = None


def _serialize_staff(staff: Staff, severance_multiplier: float = 1.0) -> Dict[str, Any]:
    """Return the public staff contract based on the current Staff model."""
    return {
        "id": staff.id,
        "full_name": staff.full_name,
        "position": staff.position,
        "current_loyalty": staff.current_loyalty,
        "current_morale": staff.current_morale,
        "annual_salary": staff.annual_salary,
        "market_value": staff.market_value,
        "hire_turn": staff.hire_turn,
        "fire_turn": staff.fire_turn,
        "skill_engineering": staff.skill_engineering,
        "skill_finance": staff.skill_finance,
        "skill_marketing": staff.skill_marketing,
        "skill_operations": staff.skill_operations,
        "skill_leadership": staff.skill_leadership,
        "effectiveness": staff.calculate_effectiveness(),
        "severance_cost": staff.annual_salary * severance_multiplier,
    }


def _current_turn(db: Session) -> int:
    game = db.query(GameState).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game has not been initialized")
    return game.turn_number


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_staff(
    company_id: int,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List staff currently employed by a company."""
    try:
        staff_list = (
            db.query(Staff)
            .filter(Staff.company_id == company_id)
            .order_by(Staff.position, Staff.id)
            .all()
        )
        return [_serialize_staff(staff) for staff in staff_list]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list staff: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/candidates", response_model=List[Dict[str, Any]])
async def list_candidates(
    company_id: int,
    position: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List available staff candidates for the requesting company's game."""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        query = db.query(Staff).filter(
            Staff.game_id == company.game_id,
            Staff.company_id.is_(None),
            Staff.is_available == True,
            Staff.is_retired == False,
        )

        if position:
            query = query.filter(Staff.position == position.upper())

        candidates = query.order_by(Staff.position, Staff.market_value.desc()).all()
        return [_serialize_staff(candidate) for candidate in candidates]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list staff candidates: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fire", response_model=Dict[str, Any])
async def fire_staff(
    request: FireStaffRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Fire a staff member from a company."""
    try:
        current_turn = _current_turn(db)
        staff = db.query(Staff).filter(
            Staff.id == request.staff_id,
            Staff.company_id == request.company_id,
        ).first()

        if not staff:
            raise HTTPException(status_code=404, detail="Staff member not found for this company")

        severance_paid = staff.annual_salary * request.severance_multiplier
        success, message = HRSystem.fire_staff(
            db=db,
            company_id=request.company_id,
            staff_id=request.staff_id,
            current_turn=current_turn,
            severance_multiplier=request.severance_multiplier,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "staff_id": request.staff_id,
            "severance_paid": severance_paid,
            "message": message,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Failed to fire staff: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/hire", response_model=Dict[str, Any])
async def hire_staff(
    request: HireStaffRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Hire an available staff candidate."""
    try:
        current_turn = _current_turn(db)
        candidate = db.query(Staff).filter(Staff.id == request.candidate_id).first()

        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        offered_salary = (
            request.offered_salary
            if request.offered_salary is not None
            else candidate.market_value
        )

        success, message = HRSystem.hire_staff(
            db=db,
            company_id=request.company_id,
            staff_id=request.candidate_id,
            offered_salary=offered_salary,
            current_turn=current_turn,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        db.refresh(candidate)

        return {
            "success": True,
            "staff_id": candidate.id,
            "message": message,
            "staff": _serialize_staff(candidate),
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Failed to hire staff: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


__all__ = ["router"]
