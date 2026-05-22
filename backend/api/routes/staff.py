"""
员工管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import Staff, Company, GameState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/staff", tags=["Staff"])


# ============================================================================
# Request Models
# ============================================================================

class FireStaffRequest(BaseModel):
    """解雇员工请求"""
    company_id: int
    staff_id: int


class HireStaffRequest(BaseModel):
    """招聘员工请求"""
    company_id: int
    candidate_id: int


# ============================================================================
# Staff Endpoints
# ============================================================================

@router.get("/list", response_model=List[Dict[str, Any]])
async def list_staff(
    company_id: int,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取公司所有员工
    
    Args:
        company_id: 公司ID
    
    Returns:
        员工列表
    """
    try:
        staff_list = db.query(Staff).filter(Staff.company_id == company_id).all()
        
        return [
            {
                "id": s.id,
                "role": s.position,  # 使用 position 字段作为 role
                "name": s.name,
                "portrait_icon": "👤",  # 默认图标
                "loyalty": s.loyalty or 50,
                "skill_engineering": s.skill_technical or 0,
                "skill_finance": s.skill_financial or 0,
                "skill_marketing": s.skill_marketing or 0,
                "skill_operations": s.skill_management or 0,
                "salary_monthly": s.salary or 0,
                "hire_date_turn": s.hire_date_turn or 0,
                "severance_cost": (s.salary or 0) * 2 if s.salary else 0  # 估算解雇成本
            }
            for s in staff_list
        ]
        
    except Exception as e:
        logger.error(f"获取员工列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fire", response_model=Dict[str, Any])
async def fire_staff(
    request: FireStaffRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    解雇员工
    
    Args:
        request: 解雇请求
    
    Returns:
        解雇结果
    """
    try:
        staff = db.query(Staff).filter(
            Staff.id == request.staff_id,
            Staff.company_id == request.company_id
        ).first()
        
        if not staff:
            raise HTTPException(status_code=404, detail="员工不存在或不属于该公司")
        
        # 计算解雇成本
        severance_cost = (staff.salary or 0) * 2
        
        # 更新员工状态
        staff.company_id = None  # 设置为自由员工
        staff.is_available = True
        
        db.commit()
        
        return {
            "success": True,
            "severance_paid": severance_cost,
            "message": f"已解雇 {staff.name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"解雇员工失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hire", response_model=Dict[str, Any])
async def hire_staff(
    request: HireStaffRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    招聘候选人
    
    Args:
        request: 招聘请求
    
    Returns:
        招聘结果
    """
    try:
        # 获取候选人（自由员工）
        candidate = db.query(Staff).filter(
            Staff.id == request.candidate_id,
            Staff.company_id == None  # 必须是自由员工
        ).first()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="候选人不存在或已被其他公司雇佣")
        
        # 验证公司存在
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 雇佣员工
        candidate.company_id = request.company_id
        candidate.is_available = False
        candidate.hire_date_turn = db.query(GameState).first().turn_number if db.query(GameState).first() else 0
        
        db.commit()
        
        return {
            "success": True,
            "staff_id": candidate.id,
            "message": f"已成功雇佣 {candidate.name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"招聘员工失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]


