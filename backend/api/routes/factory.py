"""
工厂和生产管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import Factory, ProductionLine, CarTrim, Company

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/factory", tags=["Factory"])


# ============================================================================
# Request Models
# ============================================================================

class AssignProductionRequest(BaseModel):
    """分配生产请求"""
    line_id: int
    design_id: int


class StopProductionRequest(BaseModel):
    """停止生产请求"""
    line_id: int


# ============================================================================
# Factory Endpoints
# ============================================================================

@router.get("/list", response_model=Dict[str, Any])
async def list_factories(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取玩家的所有工厂
    
    Args:
        company_id: 公司ID
    
    Returns:
        工厂列表
    """
    try:
        factories = db.query(Factory).filter(Factory.company_id == company_id).all()
        
        factory_list = []
        for factory in factories:
            # 获取该工厂的生产线
            lines = db.query(ProductionLine).filter(
                ProductionLine.factory_id == factory.id
            ).all()
            
            factory_list.append({
                "id": factory.id,
                "name": factory.name,
                "type": factory.factory_type,
                "location": factory.region.code if factory.region else None,
                "region_id": factory.region_id,
                "capacity": factory.capacity_units_per_month,
                "efficiency": factory.efficiency_score,
                "production_lines": [
                    {
                        "id": line.id,
                        "name": line.name or f"Line {line.id}",
                        "status": line.status,
                        "current_design_id": line.current_design_id,
                        "current_design_name": line.car_trim.name if line.car_trim else None,
                        "monthly_capacity": line.monthly_capacity,
                        "retooling_until_turn": line.retooling_until_turn
                    }
                    for line in lines
                ]
            })
        
        return {
            "success": True,
            "factories": factory_list,
            "total": len(factory_list)
        }
        
    except Exception as e:
        logger.error(f"获取工厂列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{factory_id}", response_model=Dict[str, Any])
async def get_factory_details(
    factory_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取工厂详情（包括生产线状态）
    
    Args:
        factory_id: 工厂ID
    
    Returns:
        工厂详细信息
    """
    try:
        factory = db.query(Factory).filter(Factory.id == factory_id).first()
        if not factory:
            raise HTTPException(status_code=404, detail="工厂不存在")
        
        # 获取生产线
        lines = db.query(ProductionLine).filter(
            ProductionLine.factory_id == factory_id
        ).all()
        
        return {
            "success": True,
            "factory": {
                "id": factory.id,
                "name": factory.name,
                "type": factory.factory_type,
                "location": factory.region.code if factory.region else None,
                "region_id": factory.region_id,
                "capacity": factory.capacity_units_per_month,
                "efficiency": factory.efficiency_score,
                "production_lines": [
                    {
                        "id": line.id,
                        "name": line.name or f"Line {line.id}",
                        "status": line.status,
                        "current_design_id": line.current_design_id,
                        "current_design_name": line.car_trim.name if line.car_trim else None,
                        "monthly_capacity": line.monthly_capacity,
                        "retooling_until_turn": line.retooling_until_turn
                    }
                    for line in lines
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工厂详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assign", response_model=Dict[str, Any])
async def assign_production(
    request: AssignProductionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    分配车型到生产线
    
    Args:
        request: 分配生产请求
    
    Returns:
        分配结果
    """
    try:
        line = db.query(ProductionLine).filter(ProductionLine.id == request.line_id).first()
        if not line:
            raise HTTPException(status_code=404, detail="生产线不存在")
        
        design = db.query(CarTrim).filter(CarTrim.id == request.design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail="车型设计不存在")
        
        # 检查是否需要重新配置
        needs_retooling = (
            line.current_design_id is None or 
            line.current_design_id != request.design_id
        )
        
        if needs_retooling:
            # 使用 RetoolingCalculator 计算时间和成本
            from backend.core.production.retooling import RetoolingCalculator
            from backend.models.game_state import GameState
            
            # 获取当前回合
            game_state = db.query(GameState).filter(
                GameState.id == line.game_id
            ).first()
            if not game_state:
                raise HTTPException(status_code=404, detail="游戏状态不存在")
            
            current_turn = game_state.turn_number
            
            # 获取之前的设计
            previous_design = None
            if line.current_design_id:
                previous_design = db.query(CarTrim).filter(
                    CarTrim.id == line.current_design_id
                ).first()
            
            # 开始重新配置
            success, message, details = RetoolingCalculator.start_retooling(
                db, line, design, current_turn
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            db.commit()
            
            return {
                "success": True,
                "message": f"开始重新配置：{message}",
                "line": {
                    "id": line.id,
                    "status": line.status,
                    "current_design_id": line.current_design_id,
                    "previous_design_id": line.previous_design_id
                },
                "retooling_turns": details["retooling_turns"],
                "retooling_cost": details["retooling_cost"],
                "completion_turn": details["completion_turn"]
            }
        else:
            # 不需要重新配置，直接设置
            line.current_design_id = request.design_id
            line.status = "RUNNING"
            db.commit()
            
            return {
                "success": True,
                "message": "生产分配成功（无需重新配置）",
                "line": {
                    "id": line.id,
                    "status": line.status,
                    "current_design_id": line.current_design_id
                },
                "retooling_turns": 0,
                "retooling_cost": 0.0
            }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"分配生产失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=Dict[str, Any])
async def stop_production(
    request: StopProductionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    停止生产线
    
    Args:
        request: 停止生产请求
    
    Returns:
        停止结果
    """
    try:
        line = db.query(ProductionLine).filter(ProductionLine.id == request.line_id).first()
        if not line:
            raise HTTPException(status_code=404, detail="生产线不存在")
        
        line.status = "IDLE"
        line.current_design_id = None
        
        db.commit()
        
        return {
            "success": True,
            "message": "生产线已停止"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"停止生产失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]

