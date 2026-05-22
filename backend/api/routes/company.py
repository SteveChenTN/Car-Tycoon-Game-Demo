"""
公司管理API路由
处理公司查询、财务管理、员工管理等
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import GameState, Company, Staff, Loan
from backend.core.management.finance import FinanceLogic
from backend.core.management.hr import HRSystem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/company", tags=["Company"])


# ============================================================================
# Request Models
# ============================================================================

class LoanApplicationRequest(BaseModel):
    """贷款申请请求"""
    company_id: int
    loan_type: str  # SHORT_TERM/LONG_TERM/BOND/SUBSIDY
    amount: float
    duration_months: int

    class Config:
        from_attributes = True


# ============================================================================
# 公司信息端点
# ============================================================================

@router.get("/{company_id}", response_model=Dict[str, Any])
async def get_company(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取公司信息
    
    Args:
        company_id: 公司ID
    
    Returns:
        公司详细信息
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 获取员工
        staff = db.query(Staff).filter(Staff.company_id == company_id).all()
        
        # 获取贷款
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
                    "annual_revenue": company.annual_revenue,
                    "total_debt": sum(loan.remaining_principal for loan in loans)
                },
                "reputation": {
                    "prestige_score": company.prestige_score,
                    "reliability_reputation": company.reliability_reputation,
                    "innovation_reputation": company.innovation_reputation
                },
                "staff": {
                    "total_employees": company.employee_count,
                    "executives": len([s for s in staff if s.position in ["CEO", "CTO", "CFO", "CMO", "COO"]])
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取公司信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}/finances", response_model=Dict[str, Any])
async def get_company_finances(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取公司财务详情
    
    Args:
        company_id: 公司ID
    
    Returns:
        财务详细信息
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 获取所有贷款
        loans = db.query(Loan).filter(Loan.company_id == company_id).all()
        
        return {
            "success": True,
            "finances": {
                "cash": company.cash,
                "total_assets": company.total_assets,
                "credit_rating": company.credit_rating,
                "quarterly_profit": company.quarterly_profit,
                "annual_revenue": company.annual_revenue,
                "loans": [
                    {
                        "id": loan.id,
                        "type": loan.loan_type,
                        "original_amount": loan.original_amount,
                        "remaining_principal": loan.remaining_principal,
                        "interest_rate": loan.interest_rate,
                        "monthly_payment": loan.monthly_payment,
                        "start_turn": loan.start_turn,
                        "end_turn": loan.end_turn,
                        "status": loan.status
                    }
                    for loan in loans
                ],
                "total_debt": sum(loan.remaining_principal for loan in loans),
                "monthly_debt_payment": sum(loan.monthly_payment for loan in loans if loan.status == "ACTIVE")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取财务信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 员工管理端点
# ============================================================================

@router.get("/{company_id}/staff", response_model=List[Dict[str, Any]])
async def get_company_staff(
    company_id: int,
    position: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取公司员工列表
    
    Args:
        company_id: 公司ID
        position: 筛选职位
    
    Returns:
        员工列表
    """
    try:
        query = db.query(Staff).filter(Staff.company_id == company_id)
        
        if position:
            query = query.filter(Staff.position == position)
        
        staff_list = query.all()
        
        return [
            {
                "id": s.id,
                "name": s.name,
                "position": s.position,
                "salary": s.salary,
                "hire_date_turn": s.hire_date_turn,
                "skills": {
                    "technical": s.skill_technical,
                    "management": s.skill_management,
                    "creativity": s.skill_creativity,
                    "financial": s.skill_financial,
                    "marketing": s.skill_marketing
                },
                "traits": s.traits,
                "morale": s.morale,
                "loyalty": s.loyalty,
                "effectiveness": s.calculate_effectiveness()
            }
            for s in staff_list
        ]
        
    except Exception as e:
        logger.error(f"获取员工列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/market", response_model=List[Dict[str, Any]])
async def get_staff_market(
    position: Optional[str] = None,
    min_skill: int = 0,
    max_salary: float = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取人才市场（可招聘的员工）
    
    Args:
        position: 筛选职位
        min_skill: 最低技能要求
        max_salary: 最高薪资预算
    
    Returns:
        可招聘员工列表
    """
    try:
        game = db.query(GameState).first()
        if not game:
            return []
        
        # 获取自由员工（company_id为NULL的）
        query = db.query(Staff).filter(Staff.company_id == None)
        
        if position:
            query = query.filter(Staff.position == position)
        
        staff_list = query.all()
        
        # 过滤技能和薪资
        result = []
        for s in staff_list:
            avg_skill = (
                s.skill_technical + s.skill_management + 
                s.skill_creativity + s.skill_financial + s.skill_marketing
            ) / 5
            
            if avg_skill < min_skill:
                continue
            
            market_value = HRSystem.calculate_market_value(s, game.current_year)
            if max_salary and market_value > max_salary:
                continue
            
            result.append({
                "id": s.id,
                "name": s.name,
                "position": s.position,
                "age": game.current_year - s.birth_year,
                "skills": {
                    "technical": s.skill_technical,
                    "management": s.skill_management,
                    "creativity": s.skill_creativity,
                    "financial": s.skill_financial,
                    "marketing": s.skill_marketing,
                    "average": avg_skill
                },
                "traits": s.traits,
                "market_value": market_value,
                "years_experience": s.years_experience
            })
        
        return result
        
    except Exception as e:
        logger.error(f"获取人才市场失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{company_id}/staff/hire/{staff_id}")
async def hire_staff(
    company_id: int,
    staff_id: int,
    salary: float,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    招聘员工
    
    Args:
        company_id: 公司ID
        staff_id: 员工ID
        salary: 提供的薪资
    
    Returns:
        招聘结果
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="员工不存在")
        
        if staff.company_id is not None:
            raise HTTPException(status_code=400, detail="该员工已被雇佣")
        
        # 使用HR逻辑招聘
        hr_system = HRSystem(db)
        success = hr_system.hire_staff(
            company_id=company_id,
            staff_id=staff_id,
            salary=salary,
            current_turn=game.turn_number
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="招聘失败")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"成功招聘 {staff.name}",
            "staff": {
                "id": staff.id,
                "name": staff.name,
                "position": staff.position,
                "salary": staff.salary
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"招聘员工失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{company_id}/staff/fire/{staff_id}")
async def fire_staff(
    company_id: int,
    staff_id: int,
    severance_multiplier: float = 1.0,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    解雇员工
    
    Args:
        company_id: 公司ID
        staff_id: 员工ID
        severance_multiplier: 遣散费倍数
    
    Returns:
        解雇结果
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        staff = db.query(Staff).filter(
            Staff.id == staff_id,
            Staff.company_id == company_id
        ).first()
        
        if not staff:
            raise HTTPException(status_code=404, detail="员工不存在或不属于该公司")
        
        hr_system = HRSystem(db)
        severance_cost = hr_system.fire_staff(
            staff_id=staff_id,
            severance_multiplier=severance_multiplier,
            current_turn=game.turn_number
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"已解雇 {staff.name}",
            "severance_cost": severance_cost
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解雇员工失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 贷款管理端点
# ============================================================================

@router.post("/{company_id}/loan/apply", response_model=Dict[str, Any])
async def apply_for_loan(
    request: LoanApplicationRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    申请贷款
    
    Args:
        request: 贷款申请参数
    
    Returns:
        申请结果
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        finance_logic = FinanceLogic(db)
        result = finance_logic.apply_for_loan(
            company_id=request.company_id,
            loan_type=request.loan_type,
            amount=request.amount,
            duration_months=request.duration_months,
            current_turn=game.turn_number,
            current_year=game.current_year
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "贷款申请失败"))
        
        db.commit()
        
        return {
            "success": True,
            "loan": result["loan"],
            "message": "贷款申请成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"贷款申请失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{company_id}/loan/{loan_id}/repay")
async def repay_loan_early(
    company_id: int,
    loan_id: int,
    amount: float = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    提前还款
    
    Args:
        company_id: 公司ID
        loan_id: 贷款ID
        amount: 还款金额（None表示全额还款）
    
    Returns:
        还款结果
    """
    try:
        loan = db.query(Loan).filter(
            Loan.id == loan_id,
            Loan.company_id == company_id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="贷款不存在")
        
        if loan.status != "ACTIVE":
            raise HTTPException(status_code=400, detail="贷款状态不允许还款")
        
        company = db.query(Company).filter(Company.id == company_id).first()
        
        # 如果未指定金额，全额还款
        if amount is None:
            amount = loan.remaining_principal
        
        # 检查余额
        if company.cash < amount:
            raise HTTPException(status_code=400, detail="余额不足")
        
        # 计算提前还款罚金（简化版：2%）
        penalty = amount * 0.02
        total_cost = amount + penalty
        
        if company.cash < total_cost:
            raise HTTPException(status_code=400, detail=f"余额不足（需要 {total_cost}，含罚金）")
        
        # 执行还款
        company.cash -= total_cost
        loan.remaining_principal -= amount
        
        if loan.remaining_principal <= 0:
            loan.status = "PAID_OFF"
            loan.remaining_principal = 0
        
        db.commit()
        
        return {
            "success": True,
            "repaid_principal": amount,
            "penalty": penalty,
            "total_cost": total_cost,
            "remaining_principal": loan.remaining_principal,
            "loan_status": loan.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"还款失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 公司列表端点
# ============================================================================

@router.get("/", response_model=List[Dict[str, Any]])
async def list_companies(
    active_only: bool = True,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    列出所有公司
    
    Args:
        active_only: 仅显示活跃公司
    
    Returns:
        公司列表
    """
    try:
        query = db.query(Company)
        
        if active_only:
            query = query.filter(Company.is_bankrupt == False)
        
        companies = query.all()
        
        return [
            {
                "id": c.id,
                "name": c.name,
                "is_player": c.is_player,
                "is_ai": c.is_ai,
                "is_bankrupt": c.is_bankrupt,
                "prestige": c.prestige_score,
                "cash": c.cash if c.is_player else None,  # AI公司不显示现金
                "headquarters": c.headquarters_region
            }
            for c in companies
        ]
        
    except Exception as e:
        logger.error(f"列出公司失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]

