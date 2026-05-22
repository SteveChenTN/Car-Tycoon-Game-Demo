"""
市场策略API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models import Region, CarTrim, Company, SalesHistory

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
        # 获取所有区域
        regions = db.query(Region).all()
        
        region_data = []
        for region in regions:
            # TODO: 实现实际的市场数据查询
            # 这里只是占位实现
            demand_level = 0.5  # 需求水平 0-1
            demand_tier = "MEDIUM"
            if demand_level > 0.7:
                demand_tier = "HIGH"
            elif demand_level < 0.4:
                demand_tier = "LOW"
            
            region_data.append({
                "region_id": region.id,
                "region_code": region.code,
                "region_name": region.name,
                "demand_level": demand_level,
                "demand_tier": demand_tier,  # 添加需求层级
                "rival_avg_price": 25000,  # 竞争对手平均价格（使用 rival_avg_price 匹配前端）
                "my_price": None,  # 我的价格（如果有）
                "market_share": 0.0,  # 市场份额
                "estimated_sales": 0,  # 预估销量
                "customer_feedback": ""  # 客户反馈
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
        # 获取该公司的所有车型
        cars = db.query(CarTrim).filter(CarTrim.company_id == company_id).all()
        
        # 获取所有区域
        regions = db.query(Region).all()
        
        cells = []
        for region in regions:
            # 为每个区域创建一个热力图单元格
            # TODO: 实现实际的销售数据查询
            # 这里只是占位实现
            sales_volume = 0  # 总销量
            for car in cars:
                sales_volume += 0  # 每个车型的销量
            
            # 根据销量计算颜色强度（0-1）
            intensity = min(sales_volume / 1000.0, 1.0) if sales_volume > 0 else 0.1
            
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
                "intensity": intensity
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

