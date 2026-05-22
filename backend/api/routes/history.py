"""
历史数据与二手车市场API路由
提供图表数据和二手车列表
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.history import SalesHistory, FinancialHistory, UsedCarInventory
from backend.models.game_state import GameState
from backend.core.economics.used_market import UsedCarMarket

router = APIRouter(
    prefix="/api/v1/history",
    tags=["history", "analytics"]
)


# ========== Pydantic响应模型 ==========

class SalesHistoryResponse(BaseModel):
    """销售历史响应"""
    turn_number: int
    year: int
    month: int
    region_id: int
    trim_id: int
    company_id: int
    units_sold: int
    revenue_total: float
    avg_transaction_price: float
    market_share_percent: Optional[float]
    
    class Config:
        from_attributes = True


class FinancialHistoryResponse(BaseModel):
    """财务历史响应"""
    turn_number: int
    year: int
    month: int
    company_id: int
    
    # 收入
    revenue_vehicles: float
    revenue_total: float
    
    # 利润
    gross_profit: float
    operating_profit: float
    net_income: float
    
    # 资产负债
    cash_end: float
    total_assets: float
    total_liabilities: float
    
    # 关键指标
    units_sold: int
    units_produced: int
    market_share_global: Optional[float]
    credit_rating: Optional[str]
    
    class Config:
        from_attributes = True
    
    @property
    def revenue_total(self) -> float:
        """计算总收入"""
        return self.revenue_vehicles + getattr(self, 'revenue_licensing', 0.0) + getattr(self, 'revenue_other', 0.0)


class UsedCarListingResponse(BaseModel):
    """二手车列表响应"""
    id: int
    region_id: int
    car_trim_id: int
    age_years: int
    condition_score: float
    quantity: int
    base_price: float
    avg_asking_price: float
    depreciation_rate: float
    
    class Config:
        from_attributes = True


# ========== API端点 ==========

@router.get("/sales", response_model=List[SalesHistoryResponse])
def get_sales_history(
    game_id: int = Query(..., description="游戏ID"),
    company_id: Optional[int] = Query(None, description="公司ID筛选"),
    region_id: Optional[int] = Query(None, description="地区ID筛选"),
    trim_id: Optional[int] = Query(None, description="车型ID筛选"),
    start_turn: Optional[int] = Query(None, description="起始回合"),
    end_turn: Optional[int] = Query(None, description="结束回合"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """
    获取销售历史
    
    用于绘制销量趋势图表
    """
    try:
        query = db.query(SalesHistory).filter(SalesHistory.game_id == game_id)
        
        if company_id is not None:
            query = query.filter(SalesHistory.company_id == company_id)
        
        if region_id is not None:
            query = query.filter(SalesHistory.region_id == region_id)
        
        if trim_id is not None:
            query = query.filter(SalesHistory.trim_id == trim_id)
        
        if start_turn is not None:
            query = query.filter(SalesHistory.turn_number >= start_turn)
        
        if end_turn is not None:
            query = query.filter(SalesHistory.turn_number <= end_turn)
        
        # 按时间倒序
        query = query.order_by(SalesHistory.turn_number.desc())
        
        records = query.limit(limit).all()
        
        return records
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取销售历史失败: {str(e)}")


@router.get("/financial", response_model=List[FinancialHistoryResponse])
def get_financial_history(
    game_id: int = Query(..., description="游戏ID"),
    company_id: int = Query(..., description="公司ID"),
    start_turn: Optional[int] = Query(None, description="起始回合"),
    end_turn: Optional[int] = Query(None, description="结束回合"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """
    获取财务历史
    
    用于绘制利润曲线、现金流图表
    """
    try:
        query = db.query(FinancialHistory).filter(
            FinancialHistory.game_id == game_id,
            FinancialHistory.company_id == company_id
        )
        
        if start_turn is not None:
            query = query.filter(FinancialHistory.turn_number >= start_turn)
        
        if end_turn is not None:
            query = query.filter(FinancialHistory.turn_number <= end_turn)
        
        query = query.order_by(FinancialHistory.turn_number.desc())
        
        records = query.limit(limit).all()
        
        return records
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取财务历史失败: {str(e)}")


@router.get("/used-cars", response_model=List[UsedCarListingResponse])
def get_used_car_listings(
    game_id: int = Query(..., description="游戏ID"),
    region_id: Optional[int] = Query(None, description="地区ID筛选"),
    car_trim_id: Optional[int] = Query(None, description="车型ID筛选"),
    max_age: Optional[int] = Query(None, ge=0, le=20, description="最大车龄筛选"),
    min_condition: Optional[float] = Query(None, ge=0, le=100, description="最低车况筛选"),
    db: Session = Depends(get_db)
):
    """
    获取二手车市场列表
    
    用于玩家查看二手车竞争情况
    """
    try:
        used_market = UsedCarMarket(db)
        
        listings = used_market.get_used_car_listings(
            game_id=game_id,
            region_id=region_id,
            car_trim_id=car_trim_id,
            max_age_years=max_age,
            min_condition=min_condition
        )
        
        # 转换为响应模型
        return [
            UsedCarListingResponse(
                id=listing["id"],
                region_id=listing["region_id"],
                car_trim_id=listing["car_trim_id"],
                age_years=listing["age_years"],
                condition_score=listing["condition_score"],
                quantity=listing["quantity"],
                base_price=listing["base_price"],
                avg_asking_price=listing["avg_asking_price"],
                depreciation_rate=0.15  # 默认值
            )
            for listing in listings
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取二手车列表失败: {str(e)}")


@router.get("/sales/summary")
def get_sales_summary(
    game_id: int = Query(..., description="游戏ID"),
    company_id: int = Query(..., description="公司ID"),
    period_turns: int = Query(12, ge=1, le=120, description="统计周期（回合数）"),
    db: Session = Depends(get_db)
):
    """
    获取销售汇总统计
    
    返回最近N个回合的总计数据
    """
    try:
        # 获取游戏当前回合
        game_state = db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            raise HTTPException(status_code=404, detail="游戏不存在")
        
        current_turn = game_state.turn_number
        start_turn = max(0, current_turn - period_turns)
        
        # 查询销售记录
        records = db.query(SalesHistory).filter(
            SalesHistory.game_id == game_id,
            SalesHistory.company_id == company_id,
            SalesHistory.turn_number >= start_turn,
            SalesHistory.turn_number <= current_turn
        ).all()
        
        # 汇总计算
        total_units = sum(r.units_sold for r in records)
        total_revenue = sum(r.revenue_total for r in records)
        total_profit = sum(r.gross_profit_total for r in records)
        
        avg_price = total_revenue / total_units if total_units > 0 else 0
        avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            "period_start_turn": start_turn,
            "period_end_turn": current_turn,
            "period_length_turns": period_turns,
            "total_units_sold": total_units,
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "avg_transaction_price": avg_price,
            "avg_margin_percent": avg_margin,
            "record_count": len(records)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取销售汇总失败: {str(e)}")


@router.get("/financial/summary")
def get_financial_summary(
    game_id: int = Query(..., description="游戏ID"),
    company_id: int = Query(..., description="公司ID"),
    period_turns: int = Query(12, ge=1, le=120, description="统计周期（回合数）"),
    db: Session = Depends(get_db)
):
    """
    获取财务汇总统计
    
    返回最近N个回合的平均/累计财务指标
    """
    try:
        # 获取游戏当前回合
        game_state = db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            raise HTTPException(status_code=404, detail="游戏不存在")
        
        current_turn = game_state.turn_number
        start_turn = max(0, current_turn - period_turns)
        
        # 查询财务记录
        records = db.query(FinancialHistory).filter(
            FinancialHistory.game_id == game_id,
            FinancialHistory.company_id == company_id,
            FinancialHistory.turn_number >= start_turn,
            FinancialHistory.turn_number <= current_turn
        ).all()
        
        if not records:
            return {
                "period_start_turn": start_turn,
                "period_end_turn": current_turn,
                "message": "无财务数据"
            }
        
        # 累计数据
        total_revenue = sum(r.revenue_vehicles for r in records)
        total_profit = sum(r.net_income for r in records)
        total_units_sold = sum(r.units_sold for r in records)
        
        # 平均数据
        avg_cash = sum(r.cash_end for r in records) / len(records)
        avg_assets = sum(r.total_assets for r in records) / len(records)
        avg_liabilities = sum(r.total_liabilities for r in records) / len(records)
        
        # 最新值
        latest = records[-1] if records else None
        
        return {
            "period_start_turn": start_turn,
            "period_end_turn": current_turn,
            "period_length_turns": period_turns,
            
            # 累计
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "total_units_sold": total_units_sold,
            
            # 平均
            "avg_cash_balance": avg_cash,
            "avg_total_assets": avg_assets,
            "avg_total_liabilities": avg_liabilities,
            
            # 最新
            "latest_cash": latest.cash_end if latest else 0,
            "latest_credit_rating": latest.credit_rating if latest else None,
            
            "record_count": len(records)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取财务汇总失败: {str(e)}")


# 导出路由
__all__ = ["router"]


