"""
外交与竞争API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import CompetitorRelation, Company, GameState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/diplomacy", tags=["Diplomacy"])


# ============================================================================
# Request Models
# ============================================================================

class DiplomacyActionRequest(BaseModel):
    """外交行动请求"""
    company_id: int
    action_type: str  # 'insult' | 'praise' | 'propose_alliance' | 'spy' | 'headhunt'
    target_company_id: int
    description: Optional[str] = None
    cost: Optional[float] = None
    success_chance: Optional[float] = None


# ============================================================================
# Diplomacy Endpoints
# ============================================================================

@router.get("/relations", response_model=List[Dict[str, Any]])
async def get_company_relations(
    company_id: int,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取与其他公司的关系
    
    Args:
        company_id: 公司ID
    
    Returns:
        公司关系列表
    """
    try:
        # 获取该公司的所有关系
        relations = db.query(CompetitorRelation).filter(
            CompetitorRelation.company_id == company_id
        ).all()
        
        result = []
        for rel in relations:
            # 获取目标公司信息
            target_company = db.query(Company).filter(Company.id == rel.target_company_id).first()
            
            # 根据关系分数确定状态
            score = rel.relation_score
            if score <= -50:
                status = 'hostile'
            elif score <= -10:
                status = 'rival'
            elif score <= 10:
                status = 'neutral'
            elif score <= 50:
                status = 'friendly'
            else:
                status = 'allied'
            
            result.append({
                "company_id": rel.target_company_id,
                "company_name": target_company.name if target_company else f"Company {rel.target_company_id}",
                "relation_score": score,
                "status": status,
                "last_interaction_turn": rel.last_interaction_turn or 0,
                "alliance_level": 1 if rel.is_alliance else 0
            })
        
        return result
        
    except Exception as e:
        logger.error(f"获取公司关系失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action", response_model=Dict[str, Any])
async def perform_diplomacy_action(
    request: DiplomacyActionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    执行外交行动
    
    Args:
        request: 外交行动请求
    
    Returns:
        行动结果
    """
    try:
        # 验证公司存在
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        target_company = db.query(Company).filter(Company.id == request.target_company_id).first()
        if not target_company:
            raise HTTPException(status_code=404, detail="目标公司不存在")
        
        # 获取或创建关系记录
        relation = db.query(CompetitorRelation).filter(
            CompetitorRelation.company_id == request.company_id,
            CompetitorRelation.target_company_id == request.target_company_id
        ).first()
        
        if not relation:
            game = db.query(GameState).first()
            relation = CompetitorRelation(
                game_id=game.id if game else 1,
                company_id=request.company_id,
                target_company_id=request.target_company_id,
                relation_score=0.0
            )
            db.add(relation)
        
        # 根据行动类型计算关系变化
        relation_change = 0.0
        result_message = ""
        
        if request.action_type == 'insult':
            relation_change = -10.0
            result_message = f"公开批评 {target_company.name}，关系恶化"
        elif request.action_type == 'praise':
            relation_change = 5.0
            result_message = f"公开赞扬 {target_company.name}，关系改善"
        elif request.action_type == 'propose_alliance':
            relation_change = 15.0
            result_message = f"向 {target_company.name} 提出联盟，关系显著改善"
        elif request.action_type == 'spy':
            relation_change = -20.0
            result_message = f"对 {target_company.name} 进行间谍活动，关系严重恶化"
        elif request.action_type == 'headhunt':
            relation_change = -15.0
            result_message = f"试图挖角 {target_company.name} 的员工，关系恶化"
        
        # 更新关系分数
        relation.relation_score = max(-100.0, min(100.0, relation.relation_score + relation_change))
        relation.last_interaction_turn = db.query(GameState).first().turn_number if db.query(GameState).first() else 0
        
        # 更新行动计数
        if relation_change > 0:
            relation.total_positive_actions += 1
        else:
            relation.total_negative_actions += 1
        
        db.commit()
        
        return {
            "success": True,
            "result": result_message,
            "relation_change": relation_change,
            "new_relation_score": relation.relation_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"执行外交行动失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]


