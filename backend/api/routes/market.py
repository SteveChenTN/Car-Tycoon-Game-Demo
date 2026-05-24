"""
市场策略API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import (
    Region, CarTrim, Company, SalesHistory, MarketDemandHistory,
    ConsumerBucket, DealershipInventory, GameState
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/market", tags=["Market"])


# ============================================================================
# Request Models
# ============================================================================

class MarketPricingRequest(BaseModel):
    """市场定价请求"""
    company_id: int
    design_id: int
    regional_prices: Dict[int, float]  # region_id -> price


def _latest_sales_turn(db: Session, game_id: int) -> Optional[int]:
    return db.query(func.max(SalesHistory.turn_number)).filter(
        SalesHistory.game_id == game_id
    ).scalar()


def _latest_demand_turn(db: Session, game_id: int) -> Optional[int]:
    return db.query(func.max(MarketDemandHistory.turn_number)).filter(
        MarketDemandHistory.game_id == game_id
    ).scalar()


def _demand_level(
    region: Region,
    demand: int,
    game_state: Optional[GameState]
) -> float:
    if demand <= 0:
        return 0.0

    periods_per_year = 48 if game_state and game_state.simulation_speed == "weekly" else 12
    expected_period_demand = max(region.annual_sales_potential / periods_per_year, 1.0)
    return max(0.0, min(1.0, demand / expected_period_demand))


def _demand_tier(level: float) -> str:
    if level > 0.7:
        return "HIGH"
    if level < 0.4:
        return "LOW"
    return "MEDIUM"


def _weighted_avg_price(records: List[SalesHistory]) -> float:
    total_units = sum(record.units_sold for record in records)
    if total_units <= 0:
        return 0.0
    return sum(record.avg_transaction_price * record.units_sold for record in records) / total_units


def _inventory_price(db: Session, game_id: int, company_id: int, region_id: int) -> Optional[float]:
    inventories = db.query(DealershipInventory).filter(
        DealershipInventory.game_id == game_id,
        DealershipInventory.company_id == company_id,
        DealershipInventory.region_id == region_id,
        DealershipInventory.quantity_new > 0
    ).all()
    if not inventories:
        return None

    total_units = sum(inventory.quantity_new for inventory in inventories)
    if total_units <= 0:
        return None

    return sum(inventory.effective_price * inventory.quantity_new for inventory in inventories) / total_units


# ============================================================================
# Market Endpoints
# ============================================================================

@router.get("/overview", response_model=Dict[str, Any])
async def get_market_overview(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取当前市场状况（各区域需求、竞争对手价格）
    
    Args:
        company_id: 公司ID
    
    Returns:
        市场概览数据
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")

        game_id = company.game_id
        game_state = db.query(GameState).filter(GameState.id == game_id).first()
        sales_turn = _latest_sales_turn(db, game_id)
        demand_turn = _latest_demand_turn(db, game_id)

        regions = db.query(Region).filter(Region.game_id == game_id).all()
        
        region_data = []
        for region in regions:
            company_sales_records = []
            all_sales_records = []
            rival_sales_records = []

            if sales_turn is not None:
                all_sales_records = db.query(SalesHistory).filter(
                    SalesHistory.game_id == game_id,
                    SalesHistory.turn_number == sales_turn,
                    SalesHistory.region_id == region.id
                ).all()
                company_sales_records = [
                    record for record in all_sales_records
                    if record.company_id == company_id
                ]
                rival_sales_records = [
                    record for record in all_sales_records
                    if record.company_id != company_id
                ]

            total_region_sales = sum(record.units_sold for record in all_sales_records)
            company_region_sales = sum(record.units_sold for record in company_sales_records)
            company_revenue = sum(record.revenue_total for record in company_sales_records)
            company_profit = sum(record.gross_profit_total for record in company_sales_records)
            market_share = (
                company_region_sales / total_region_sales
                if total_region_sales > 0 else 0.0
            )

            demand_record = None
            if demand_turn is not None:
                demand_record = db.query(MarketDemandHistory).filter(
                    MarketDemandHistory.game_id == game_id,
                    MarketDemandHistory.turn_number == demand_turn,
                    MarketDemandHistory.region_id == region.id
                ).first()

            if demand_record:
                total_demand = demand_record.total_demand
                used_car_sales = demand_record.used_car_sales
                lost_demand = demand_record.lost_demand
                lost_reasons = demand_record.lost_reasons or {}
            else:
                total_demand = sum(
                    row[0] or 0 for row in db.query(ConsumerBucket.current_demand).filter(
                        ConsumerBucket.game_id == game_id,
                        ConsumerBucket.region_id == region.id
                    ).all()
                )
                used_car_sales = 0
                lost_demand = 0
                lost_reasons = {}

            demand_level = _demand_level(region, total_demand, game_state)
            demand_tier = _demand_tier(demand_level)

            rival_avg_price = _weighted_avg_price(rival_sales_records)
            if rival_avg_price == 0.0:
                rival_inventory_prices = [
                    inventory.effective_price
                    for inventory in db.query(DealershipInventory).filter(
                        DealershipInventory.game_id == game_id,
                        DealershipInventory.region_id == region.id,
                        DealershipInventory.company_id != company_id,
                        DealershipInventory.quantity_new > 0
                    ).all()
                    if inventory.effective_price
                ]
                rival_avg_price = (
                    sum(rival_inventory_prices) / len(rival_inventory_prices)
                    if rival_inventory_prices else 0.0
                )

            my_price = _inventory_price(db, game_id, company_id, region.id)
            if my_price is None:
                my_trims = db.query(CarTrim).filter(
                    CarTrim.game_id == game_id,
                    CarTrim.company_id == company_id,
                    CarTrim.is_in_production == True
                ).all()
                my_price = (
                    sum(trim.msrp for trim in my_trims) / len(my_trims)
                    if my_trims else None
                )

            stock_available = int(db.query(func.sum(DealershipInventory.quantity_new)).filter(
                DealershipInventory.game_id == game_id,
                DealershipInventory.company_id == company_id,
                DealershipInventory.region_id == region.id
            ).scalar() or 0)

            if company_region_sales > 0:
                customer_feedback = f"本回合售出 {company_region_sales:,} 辆，区域份额 {market_share * 100:.1f}%"
            elif lost_reasons.get("NO_NEW_STOCK"):
                customer_feedback = "有需求但可售库存不足"
            elif lost_reasons.get("NO_DISTRIBUTION"):
                customer_feedback = "缺少有效分销网络"
            elif lost_demand > 0:
                customer_feedback = "部分需求转向二手车或流失"
            else:
                customer_feedback = "暂无成交记录"
            
            region_data.append({
                "region_id": region.id,
                "region_code": region.code,
                "region_name": region.name,
                "demand_level": demand_level,
                "demand_tier": demand_tier,
                "rival_avg_price": rival_avg_price,
                "my_price": my_price,
                "market_share": market_share,
                "estimated_sales": company_region_sales,
                "actual_sales": company_region_sales,
                "used_car_sales": used_car_sales,
                "lost_demand": lost_demand,
                "lost_reasons": lost_reasons,
                "revenue": company_revenue,
                "estimated_profit": company_profit,
                "gross_profit": company_profit,
                "stock_available": stock_available,
                "customer_feedback": customer_feedback
            })
        
        return {
            "success": True,
            "regions": region_data
        }
        
    except Exception as e:
        logger.error(f"获取市场概览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap", response_model=Dict[str, Any])
async def get_sales_heatmap(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取销售热力图数据
    
    Args:
        company_id: 公司ID
    
    Returns:
        热力图数据
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")

        game_id = company.game_id
        sales_turn = _latest_sales_turn(db, game_id)
        
        regions = db.query(Region).filter(Region.game_id == game_id).all()
        sales_by_region: Dict[int, int] = {}

        if sales_turn is not None:
            rows = db.query(
                SalesHistory.region_id,
                func.sum(SalesHistory.units_sold)
            ).filter(
                SalesHistory.game_id == game_id,
                SalesHistory.company_id == company_id,
                SalesHistory.turn_number == sales_turn
            ).group_by(SalesHistory.region_id).all()
            sales_by_region = {region_id: int(units or 0) for region_id, units in rows}

        max_sales = max(sales_by_region.values(), default=0)
        
        cells = []
        for region in regions:
            sales_volume = sales_by_region.get(region.id, 0)
            intensity = (sales_volume / max_sales) if max_sales > 0 else 0.0
            
            # 计算颜色（从红色到青色）
            red = int(255 * (1 - intensity))
            green = int(255 * intensity)
            blue = int(128 + 127 * intensity)
            color = f"rgb({red}, {green}, {blue})"
            
            cells.append({
                "region_id": region.id,
                "region_code": region.code,
                "sales_volume": sales_volume,
                "color": color,
                "intensity": intensity,
                "sales_intensity": intensity
            })
        
        return {
            "success": True,
            "cells": cells
        }
        
    except Exception as e:
        logger.error(f"获取销售热力图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pricing", response_model=Dict[str, Any])
async def submit_regional_pricing(
    request: MarketPricingRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    提交区域定价策略
    
    Args:
        request: 定价请求
    
    Returns:
        定价结果和预估数据
    """
    try:
        design = db.query(CarTrim).filter(CarTrim.id == request.design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail="车型设计不存在")
        
        # TODO: 实现实际的定价逻辑和市场预测
        # 这里只是占位实现
        total_estimated_sales = 0
        total_estimated_revenue = 0.0
        
        for region_id, price in request.regional_prices.items():
            # 简单的估算逻辑（实际应该考虑需求、竞争等）
            estimated_volume = 100  # 假设每月100辆
            total_estimated_sales += estimated_volume
            total_estimated_revenue += price * estimated_volume
        
        return {
            "success": True,
            "message": "定价策略已提交",
            "estimated_monthly_sales": total_estimated_sales,
            "estimated_revenue": total_estimated_revenue
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交定价策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
