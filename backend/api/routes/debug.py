"""
调试/上帝模式API路由
提供绕过迷雾的完整信息查看
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import logging

from backend.database import get_db
from backend.models import (
    GameState, Company, Engine, Chassis, CarTrim,
    Factory, Inventory, MaterialMarket, CompanyTechnology,
    EventLog, Loan, TaxRecord
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/debug", tags=["Debug"])


# ============================================================================
# 全局信息端点
# ============================================================================

@router.get("/all_companies", response_model=List[Dict[str, Any]])
async def get_all_companies_detailed(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    **上帝模式**: 获取所有公司的详细信息（包括AI公司）
    
    正常游戏中应该只能看到自己的详细信息和竞争对手的公开信息
    
    Returns:
        所有公司的完整财务、技术、生产数据
    """
    try:
        companies = db.query(Company).all()
        
        result = []
        for company in companies:
            # 获取技术树进度
            techs = db.query(CompanyTechnology).filter(
                CompanyTechnology.company_id == company.id
            ).all()
            
            unlocked_techs = [t.technology.name for t in techs if t.status == "COMPLETE"]
            researching_techs = [
                {
                    "name": t.technology.name,
                    "progress": t.progress_percentage
                }
                for t in techs if t.status == "RESEARCHING"
            ]
            
            # 获取车辆
            cars = db.query(CarTrim).filter(CarTrim.company_id == company.id).all()
            
            # 获取贷款
            loans = db.query(Loan).filter(Loan.company_id == company.id).all()
            total_debt = sum(loan.remaining_principal for loan in loans)
            
            result.append({
                "id": company.id,
                "name": company.name,
                "is_ai": company.is_ai,
                "is_player": company.is_player,
                "is_bankrupt": company.is_bankrupt,
                "finances": {
                    "cash": company.cash,
                    "total_debt": total_debt,
                    "credit_rating": company.credit_rating,
                    "total_assets": company.total_assets,
                    "quarterly_profit": company.quarterly_profit,
                    "annual_revenue": company.annual_revenue
                },
                "reputation": {
                    "prestige_score": company.prestige_score,
                    "reliability_reputation": company.reliability_reputation,
                    "innovation_reputation": company.innovation_reputation
                },
                "technology": {
                    "unlocked_count": len(unlocked_techs),
                    "unlocked_techs": unlocked_techs,
                    "researching": researching_techs
                },
                "products": {
                    "total_models": len(cars),
                    "in_production": len([c for c in cars if c.is_in_production])
                },
                "workforce": company.employee_count
            })
        
        return result
        
    except Exception as e:
        logger.error(f"获取所有公司失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}/full", response_model=Dict[str, Any])
async def get_company_full_details(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    **上帝模式**: 获取单个公司的完整详情
    
    Args:
        company_id: 公司ID
    
    Returns:
        公司的所有数据（财务、技术、生产、库存等）
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 发动机
        engines = db.query(Engine).filter(Engine.company_id == company_id).all()
        
        # 底盘
        chassis_list = db.query(Chassis).filter(Chassis.company_id == company_id).all()
        
        # 车辆
        cars = db.query(CarTrim).filter(CarTrim.company_id == company_id).all()
        
        # 工厂
        factories = db.query(Factory).filter(Factory.company_id == company_id).all()
        
        # 库存
        inventories = db.query(Inventory).filter(
            Inventory.factory_id.in_([f.id for f in factories])
        ).all() if factories else []
        
        # 贷款
        loans = db.query(Loan).filter(Loan.company_id == company_id).all()
        
        # 技术树
        techs = db.query(CompanyTechnology).filter(
            CompanyTechnology.company_id == company_id
        ).all()
        
        return {
            "company": {
                "id": company.id,
                "name": company.name,
                "is_ai": company.is_ai,
                "is_player": company.is_player,
                "headquarters": company.headquarters_region,
                "founded_year": company.founded_year
            },
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
                        "remaining": loan.remaining_principal,
                        "interest_rate": loan.interest_rate,
                        "monthly_payment": loan.monthly_payment
                    }
                    for loan in loans
                ]
            },
            "engineering": {
                "engines": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "displacement": e.displacement_cc,
                        "horsepower": e.max_horsepower,
                        "cost": e.manufacturing_cost
                    }
                    for e in engines
                ],
                "chassis": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "wheelbase": c.wheelbase_mm,
                        "is_platform": c.is_platform,
                        "cost": c.manufacturing_cost
                    }
                    for c in chassis_list
                ],
                "cars": [
                    {
                        "id": car.id,
                        "model": car.model_name,
                        "trim": car.name,
                        "segment": car.segment,
                        "msrp": car.msrp,
                        "in_production": car.is_in_production
                    }
                    for car in cars
                ]
            },
            "production": {
                "factories": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "type": f.factory_type,
                        "location": f.region_code,
                        "capacity": f.capacity_units_per_month,
                        "efficiency": f.efficiency_score
                    }
                    for f in factories
                ],
                "inventories": [
                    {
                        "factory_id": inv.factory_id,
                        "materials": inv.raw_materials_json,
                        "components": inv.finished_components_json,
                        "cars": inv.completed_cars_json
                    }
                    for inv in inventories
                ]
            },
            "technology": {
                "unlocked": [
                    {
                        "name": t.technology.name,
                        "completed_turn": t.research_completed_turn
                    }
                    for t in techs if t.status == "COMPLETE"
                ],
                "researching": [
                    {
                        "name": t.technology.name,
                        "progress": t.progress_percentage,
                        "monthly_investment": t.monthly_investment
                    }
                    for t in techs if t.status == "RESEARCHING"
                ]
            },
            "reputation": {
                "prestige": company.prestige_score,
                "reliability": company.reliability_reputation,
                "innovation": company.innovation_reputation
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取公司详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 市场透视端点
# ============================================================================

@router.get("/market/all_prices", response_model=Dict[str, Any])
async def get_all_market_prices(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    **上帝模式**: 查看所有地区的原材料价格
    
    正常游戏中可能需要通过市场调研才能看到
    
    Returns:
        全球原材料价格
    """
    try:
        materials = db.query(MaterialMarket).all()
        
        by_region = {}
        for material in materials:
            region = material.region_code
            if region not in by_region:
                by_region[region] = []
            
            by_region[region].append({
                "material": material.material_type,
                "price_per_kg": material.current_price_per_kg,
                "supply_level": material.supply_level,
                "volatility": material.price_volatility
            })
        
        return {
            "success": True,
            "by_region": by_region
        }
        
    except Exception as e:
        logger.error(f"获取市场价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 事件管理端点
# ============================================================================

@router.post("/events/trigger", response_model=Dict[str, Any])
async def trigger_manual_event(
    event_type: str,
    message: str,
    severity: str = "INFO",
    company_id: int = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    **上帝模式**: 手动触发事件
    
    用于测试事件系统
    
    Args:
        event_type: 事件类型
        message: 事件消息
        severity: 严重程度
        company_id: 关联公司
    
    Returns:
        事件创建结果
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        event = EventLog(
            game_id=game.id,
            turn_number=game.turn_number,
            event_type=event_type,
            message=message,
            severity=severity,
            related_company_id=company_id
        )
        
        db.add(event)
        db.commit()
        
        return {
            "success": True,
            "event_id": event.id,
            "message": "事件已创建"
        }
        
    except Exception as e:
        logger.error(f"创建事件失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/clear")
async def clear_event_logs(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    **上帝模式**: 清空所有事件日志
    
    用于测试
    
    Returns:
        清空结果
    """
    try:
        count = db.query(EventLog).delete()
        db.commit()
        
        return {
            "success": True,
            "deleted_count": count,
            "message": "事件日志已清空"
        }
        
    except Exception as e:
        logger.error(f"清空事件日志失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 数据库管理端点
# ============================================================================

@router.get("/database/stats", response_model=Dict[str, Any])
async def get_database_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    **上帝模式**: 获取数据库统计信息
    
    Returns:
        各表的记录数
    """
    try:
        stats = {
            "companies": db.query(Company).count(),
            "engines": db.query(Engine).count(),
            "chassis": db.query(Chassis).count(),
            "cars": db.query(CarTrim).count(),
            "factories": db.query(Factory).count(),
            "loans": db.query(Loan).count(),
            "event_logs": db.query(EventLog).count(),
            "tax_records": db.query(TaxRecord).count()
        }
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 金手指端点 (作弊)
# ============================================================================

@router.post("/cheat/add_money")
async def cheat_add_money(
    company_id: int,
    amount: float,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    **作弊**: 给公司增加现金
    
    Args:
        company_id: 公司ID
        amount: 金额
    
    Returns:
        操作结果
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        old_cash = company.cash
        company.cash += amount
        db.commit()
        
        return {
            "success": True,
            "company": company.name,
            "old_cash": old_cash,
            "new_cash": company.cash,
            "added": amount
        }
        
    except Exception as e:
        logger.error(f"增加现金失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cheat/unlock_all_tech")
async def cheat_unlock_all_tech(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    **作弊**: 解锁所有技术
    
    Args:
        company_id: 公司ID
    
    Returns:
        操作结果
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 获取所有技术
        techs = db.query(CompanyTechnology).filter(
            CompanyTechnology.company_id == company_id
        ).all()
        
        unlocked_count = 0
        for tech in techs:
            if tech.status != "COMPLETE":
                tech.status = "COMPLETE"
                tech.progress_percentage = 100
                unlocked_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "company": company.name,
            "unlocked_count": unlocked_count,
            "message": f"已解锁 {unlocked_count} 项技术"
        }
        
    except Exception as e:
        logger.error(f"解锁技术失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cheat/set_prestige")
async def cheat_set_prestige(
    company_id: int,
    prestige: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    **作弊**: 设置公司声望
    
    Args:
        company_id: 公司ID
        prestige: 声望值
    
    Returns:
        操作结果
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        old_prestige = company.prestige_score
        company.prestige_score = max(0, min(100, prestige))
        db.commit()
        
        return {
            "success": True,
            "company": company.name,
            "old_prestige": old_prestige,
            "new_prestige": company.prestige_score
        }
        
    except Exception as e:
        logger.error(f"设置声望失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]


