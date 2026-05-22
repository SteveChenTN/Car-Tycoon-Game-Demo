"""
报告API路由
提供月度报告、财务报告等数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.core.dependencies import get_db_optional
from backend.models import GameState, Company, EventLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MonthlyFinancials(BaseModel):
    """月度财务数据"""
    revenue: float
    costs: float
    net_profit: float
    cash_balance: float

    class Config:
        from_attributes = True


class MonthlyProduction(BaseModel):
    """月度生产数据"""
    cars_built: int
    components_produced: int
    utilization_rate: float

    class Config:
        from_attributes = True


class MonthlyAlert(BaseModel):
    """月度警告/通知"""
    type: str  # 'success' | 'warning' | 'info' | 'error'
    message: str

    class Config:
        from_attributes = True


class MonthlyReport(BaseModel):
    """月度报告"""
    turn_number: int
    year: int
    month: int
    financials: MonthlyFinancials
    production: MonthlyProduction
    alerts: List[MonthlyAlert]

    class Config:
        from_attributes = True


# ============================================================================
# 报告端点
# ============================================================================

@router.get("/latest", response_model=MonthlyReport)
async def get_latest_monthly_report(
    game_id: int = Query(..., description="游戏ID"),
    db: Session = Depends(get_db_optional)
) -> MonthlyReport:
    """
    获取最新月度报告
    
    从当前游戏状态和玩家公司的月度统计数据生成报告
    
    Args:
        game_id: 游戏ID
        db: 数据库会话
        
    Returns:
        最新月度报告
    """
    try:
        if db is None:
            raise HTTPException(
                status_code=404,
                detail="游戏未加载，请先创建或加载游戏存档"
            )
        
        # 获取游戏状态
        game = db.query(GameState).filter(GameState.id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=404,
                detail=f"游戏 {game_id} 不存在"
            )
        
        # 获取玩家公司
        player_company = db.query(Company).filter(
            Company.game_id == game_id,
            Company.is_player == True
        ).first()
        
        if not player_company:
            raise HTTPException(
                status_code=404,
                detail="未找到玩家公司"
            )
        
        # 计算总成本
        total_costs = (
            player_company.monthly_cost_manufacturing +
            player_company.monthly_cost_materials +
            player_company.monthly_cost_labor +
            player_company.monthly_cost_rd +
            player_company.monthly_cost_marketing +
            player_company.monthly_cost_admin +
            player_company.monthly_interest
        )
        
        # 构建财务数据
        financials = MonthlyFinancials(
            revenue=player_company.monthly_revenue * 1_000_000,  # 转换为游戏币
            costs=total_costs * 1_000_000,
            net_profit=player_company.monthly_profit * 1_000_000,
            cash_balance=player_company.cash * 1_000_000
        )
        
        # 构建生产数据
        # 查询公司的工厂和生产线
        from backend.models.production import Factory, ProductionLine
        
        # 查询公司的工厂
        factories = db.query(Factory).filter(
            Factory.company_id == player_company.id,
            Factory.is_operational == True
        ).all()
        
        # 查询这些工厂的生产线
        factory_ids = [f.id for f in factories]
        production_lines = []
        if factory_ids:
            production_lines = db.query(ProductionLine).filter(
                ProductionLine.factory_id.in_(factory_ids),
                ProductionLine.status == "RUNNING"
            ).all()
        
        # 计算总产能（从工厂或生产线）
        total_capacity = 0
        if production_lines:
            total_capacity = sum(line.monthly_capacity for line in production_lines)
        elif factories:
            # 如果没有生产线数据，使用工厂产能
            total_capacity = sum(f.capacity_units_per_month for f in factories if f.factory_type == "ASSEMBLY")
        
        # 计算利用率
        utilization_rate = 0.0
        if total_capacity > 0:
            utilization_rate = min(1.0, player_company.monthly_units_produced / total_capacity)
        
        production = MonthlyProduction(
            cars_built=player_company.monthly_units_produced,
            components_produced=0,  # TODO: 从库存或生产历史获取
            utilization_rate=utilization_rate
        )
        
        # 生成警告/通知
        alerts: List[MonthlyAlert] = []
        
        # 检查现金不足
        if player_company.cash < 10.0:
            alerts.append(MonthlyAlert(
                type="error",
                message=f"⚠️ 现金严重不足！当前余额 ${player_company.cash:.2f}M，建议申请贷款或减少支出"
            ))
        elif player_company.cash < 50.0:
            alerts.append(MonthlyAlert(
                type="warning",
                message=f"现金余额较低：${player_company.cash:.2f}M，建议关注财务状况"
            ))
        
        # 检查亏损
        if player_company.monthly_profit < 0:
            alerts.append(MonthlyAlert(
                type="warning",
                message=f"本月亏损 ${abs(player_company.monthly_profit):.2f}M，需要调整策略"
            ))
        
        # 检查生产利用率
        if utilization_rate < 0.5 and production_lines:
            alerts.append(MonthlyAlert(
                type="info",
                message=f"生产线利用率较低 ({utilization_rate*100:.0f}%)，考虑增加产量或关闭部分生产线"
            ))
        elif utilization_rate > 0.95:
            alerts.append(MonthlyAlert(
                type="success",
                message=f"生产线满负荷运行 ({utilization_rate*100:.0f}%)，考虑扩建产能"
            ))
        
        # 检查最近的重要事件
        recent_events = db.query(EventLog).filter(
            EventLog.game_id == game_id,
            EventLog.turn_number == game.turn_number
        ).order_by(EventLog.id.desc()).limit(3).all()
        
        for event in recent_events:
            if event.severity in ['warning', 'critical']:
                alerts.append(MonthlyAlert(
                    type=event.severity,
                    message=event.message[:100]  # 截断长消息
                ))
        
        # 如果没有警告，添加一个成功消息
        if not alerts:
            alerts.append(MonthlyAlert(
                type="success",
                message="本月运营正常，无重大事件"
            ))
        
        # 构建报告
        report = MonthlyReport(
            turn_number=game.turn_number,
            year=game.current_year,
            month=game.current_month,
            financials=financials,
            production=production,
            alerts=alerts
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取月度报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取月度报告失败: {str(e)}")


@router.get("/monthly", response_model=MonthlyReport)
async def get_monthly_report(
    game_id: int = Query(..., description="游戏ID"),
    turn_number: int = Query(..., description="回合数"),
    db: Session = Depends(get_db_optional)
) -> MonthlyReport:
    """
    获取指定回合的月度报告
    
    Args:
        game_id: 游戏ID
        turn_number: 回合数
        db: 数据库会话
        
    Returns:
        指定回合的月度报告
    """
    # 目前实现与 latest 相同，未来可以从历史记录中获取
    # 暂时返回最新报告
    return await get_latest_monthly_report(game_id=game_id, db=db)

