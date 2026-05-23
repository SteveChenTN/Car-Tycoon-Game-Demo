"""
Company management API routes.

Staff management is intentionally exposed only through /api/v1/staff/*.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import Company, GameState, Loan, LoanStatus, LoanType, Staff
from backend.core.management.finance import FinanceLogic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/company", tags=["Company"])


class LoanApplicationRequest(BaseModel):
    company_id: int
    loan_type: str
    amount: float
    duration_months: int

    class Config:
        from_attributes = True


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _serialize_loan(loan: Loan) -> Dict[str, Any]:
    payment_amount = loan.calculate_current_payment_amount()
    return {
        "id": loan.id,
        "type": _enum_value(loan.loan_type),
        "loan_type": _enum_value(loan.loan_type),
        "original_amount": loan.principal_amount,
        "principal_amount": loan.principal_amount,
        "remaining_principal": loan.remaining_principal,
        "interest_rate": loan.interest_rate,
        "monthly_payment": payment_amount,
        "payment_amount": payment_amount,
        "start_turn": loan.issued_turn,
        "issued_turn": loan.issued_turn,
        "end_turn": loan.maturity_turn,
        "maturity_turn": loan.maturity_turn,
        "next_payment_turn": loan.next_payment_turn,
        "status": _enum_value(loan.status),
    }


@router.get("/{company_id}", response_model=Dict[str, Any])
async def get_company(
    company_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get company details."""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        staff = db.query(Staff).filter(Staff.company_id == company_id).all()
        loans = db.query(Loan).filter(Loan.company_id == company_id).all()

        return {
            "success": True,
            "company": {
                "id": company.id,
                "name": company.name,
                "is_player": company.is_player,
                "is_ai": company.is_ai,
                "headquarters": company.headquarters_region,
                "founded_year": company.founded_year,
                "finances": {
                    "cash": company.cash,
                    "total_assets": company.total_assets,
                    "credit_rating": company.credit_rating,
                    "quarterly_profit": company.quarterly_profit,
                    "annual_revenue": company.quarterly_revenue * 4,
                    "total_debt": sum(loan.remaining_principal for loan in loans),
                },
                "reputation": {
                    "prestige_score": company.prestige_score,
                    "reliability_reputation": company.reputation_quality,
                    "innovation_reputation": company.reputation_innovation,
                },
                "staff": {
                    "total_employees": company.total_employees,
                    "executives": len(
                        [
                            member
                            for member in staff
                            if member.position in ["CEO", "CTO", "CFO", "CMO", "COO"]
                        ]
                    ),
                },
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get company details: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{company_id}/finances", response_model=Dict[str, Any])
async def get_company_finances(
    company_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get company financial details."""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        loans = db.query(Loan).filter(Loan.company_id == company_id).all()

        return {
            "success": True,
            "finances": {
                "cash": company.cash,
                "total_assets": company.total_assets,
                "credit_rating": company.credit_rating,
                "quarterly_profit": company.quarterly_profit,
                "annual_revenue": company.quarterly_revenue * 4,
                "loans": [
                    _serialize_loan(loan) for loan in loans
                ],
                "total_debt": sum(loan.remaining_principal for loan in loans),
                "monthly_debt_payment": sum(
                    loan.calculate_current_payment_amount()
                    for loan in loans
                    if loan.status == LoanStatus.ACTIVE
                ),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get company finances: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{company_id}/loan/apply", response_model=Dict[str, Any])
async def apply_for_loan(
    company_id: int,
    request: LoanApplicationRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Apply for a company loan."""
    try:
        if request.company_id != company_id:
            raise HTTPException(status_code=400, detail="Company ID mismatch")

        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game has not been initialized")

        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        try:
            loan_type = LoanType(request.loan_type)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in LoanType)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid loan_type. Expected one of: {allowed}",
            ) from exc

        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Loan amount must be positive")
        if request.duration_months <= 0:
            raise HTTPException(status_code=400, detail="Loan duration must be positive")

        finance_logic = FinanceLogic(db)
        result = finance_logic.apply_for_loan(
            company_id=company_id,
            loan_type=loan_type,
            principal_amount=request.amount,
            duration_turns=request.duration_months * 4,
            payment_frequency_turns=12,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Loan application failed"),
            )

        loan = db.query(Loan).filter(Loan.id == result["loan_id"]).first()

        return {
            "success": True,
            "loan": _serialize_loan(loan) if loan else result,
            "message": "Loan application approved",
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Failed to apply for loan: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{company_id}/loan/{loan_id}/repay", response_model=Dict[str, Any])
async def repay_loan_early(
    company_id: int,
    loan_id: int,
    amount: Optional[float] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Repay part or all of an active company loan."""
    try:
        loan = db.query(Loan).filter(
            Loan.id == loan_id,
            Loan.company_id == company_id,
        ).first()

        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")

        if loan.status != LoanStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Loan is not active")

        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        repayment_amount = loan.remaining_principal if amount is None else amount
        if repayment_amount <= 0:
            raise HTTPException(status_code=400, detail="Repayment amount must be positive")

        penalty = repayment_amount * 0.02
        total_cost = repayment_amount + penalty

        if company.cash < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient cash")

        company.cash -= repayment_amount
        company.record_cost("admin", penalty)
        loan.remaining_principal -= repayment_amount

        if loan.remaining_principal <= 0:
            loan.status = LoanStatus.PAID_OFF
            loan.remaining_principal = 0

        active_loans = db.query(Loan).filter(
            Loan.company_id == company_id,
            Loan.status == LoanStatus.ACTIVE
        ).all()
        company.total_debt = sum(active_loan.remaining_principal for active_loan in active_loans)

        db.commit()

        return {
            "success": True,
            "repaid_principal": repayment_amount,
            "penalty": penalty,
            "total_cost": total_cost,
            "remaining_principal": loan.remaining_principal,
            "loan_status": _enum_value(loan.status),
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Failed to repay loan: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=List[Dict[str, Any]])
async def list_companies(
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List companies."""
    try:
        query = db.query(Company)

        if active_only:
            query = query.filter(Company.is_bankrupt == False)

        companies = query.all()

        return [
            {
                "id": company.id,
                "name": company.name,
                "is_player": company.is_player,
                "is_ai": company.is_ai,
                "is_bankrupt": company.is_bankrupt,
                "prestige": company.prestige_score,
                "cash": company.cash if company.is_player else None,
                "headquarters": company.headquarters_region,
            }
            for company in companies
        ]
    except Exception as exc:
        logger.error("Failed to list companies: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


__all__ = ["router"]
