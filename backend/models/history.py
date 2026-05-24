"""
历史数据模型 - 销售历史与财务历史快照
用于图表展示和趋势分析
"""
from sqlalchemy import (
    Column, Integer, Float, String, Boolean,
    ForeignKey, Text, CheckConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from typing import Dict, Any
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class SalesHistory(Base, TimestampMixin, BaseModel):
    """
    销售历史记录
    每回合记录每个车型在每个地区的销量
    """
    __tablename__ = "sales_history"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # 时间戳
    turn_number = Column(Integer, nullable=False, comment="回合数")
    year = Column(Integer, nullable=False, comment="游戏内年份")
    month = Column(Integer, nullable=False, comment="游戏内月份")
    
    # 关联实体
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    trim_id = Column(Integer, nullable=False, comment="CarTrim ID")
    company_id = Column(Integer, nullable=False, comment="Company ID")
    
    # 销售数据
    units_sold = Column(Integer, nullable=False, default=0, comment="销售数量")
    revenue_total = Column(Float, nullable=False, default=0.0, comment="总收入")
    avg_transaction_price = Column(Float, nullable=False, default=0.0, comment="平均成交价")
    avg_discount_percent = Column(Float, nullable=False, default=0.0, comment="平均折扣率")
    
    # 市场竞争背景
    market_share_percent = Column(Float, nullable=True, comment="市场份额（%）")
    segment_rank = Column(Integer, nullable=True, comment="细分市场排名")
    
    # 盈利数据
    gross_profit_total = Column(Float, nullable=False, default=0.0, comment="毛利润")
    gross_margin_percent = Column(Float, nullable=False, default=0.0, comment="毛利率（%）")
    
    # 关系
    region = relationship("Region", foreign_keys=[region_id])
    
    # 约束
    __table_args__ = (
        CheckConstraint("units_sold >= 0", name="check_units_sold"),
        CheckConstraint("revenue_total >= 0", name="check_revenue"),
        CheckConstraint("avg_discount_percent >= 0.0 AND avg_discount_percent <= 1.0", name="check_discount"),
        Index("idx_sales_history_turn", "turn_number"),
        Index("idx_sales_history_trim", "trim_id"),
        Index("idx_sales_history_company", "company_id"),
        Index("idx_sales_history_region", "region_id"),
        Index("idx_sales_history_composite", "turn_number", "region_id", "trim_id"),
    )
    
    def __repr__(self) -> str:
        return (f"<SalesHistory(turn={self.turn_number}, "
                f"trim={self.trim_id}, region={self.region_id}, "
                f"units={self.units_sold})>")


class FinancialHistory(Base, TimestampMixin, BaseModel):
    """
    财务历史快照
    每回合记录每个公司的财务状况
    """
    __tablename__ = "financial_history"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False, comment="Company ID")
    
    # 时间戳
    turn_number = Column(Integer, nullable=False, comment="回合数")
    year = Column(Integer, nullable=False, comment="游戏内年份")
    month = Column(Integer, nullable=False, comment="游戏内月份")
    
    # 损益表 (Income Statement)
    revenue_vehicles = Column(Float, nullable=False, default=0.0, comment="车辆销售收入")
    revenue_licensing = Column(Float, nullable=False, default=0.0, comment="技术授权收入")
    revenue_other = Column(Float, nullable=False, default=0.0, comment="其他收入")
    
    cost_manufacturing = Column(Float, nullable=False, default=0.0, comment="制造成本")
    cost_materials = Column(Float, nullable=False, default=0.0, comment="材料成本")
    cost_labor = Column(Float, nullable=False, default=0.0, comment="人工成本")
    cost_rd = Column(Float, nullable=False, default=0.0, comment="研发费用")
    cost_marketing = Column(Float, nullable=False, default=0.0, comment="营销费用")
    cost_admin = Column(Float, nullable=False, default=0.0, comment="管理费用")
    cost_depreciation = Column(Float, nullable=False, default=0.0, comment="折旧费用")
    cost_interest = Column(Float, nullable=False, default=0.0, comment="利息支出")
    
    gross_profit = Column(Float, nullable=False, default=0.0, comment="毛利润")
    operating_profit = Column(Float, nullable=False, default=0.0, comment="营业利润")
    net_income = Column(Float, nullable=False, default=0.0, comment="净利润")
    
    # 资产负债表快照 (Balance Sheet Snapshot)
    cash_end = Column(Float, nullable=False, default=0.0, comment="期末现金")
    inventory_value = Column(Float, nullable=False, default=0.0, comment="库存价值")
    total_assets = Column(Float, nullable=False, default=0.0, comment="总资产")
    total_liabilities = Column(Float, nullable=False, default=0.0, comment="总负债")
    shareholder_equity = Column(Float, nullable=False, default=0.0, comment="股东权益")
    
    # 关键指标
    units_sold = Column(Integer, nullable=False, default=0, comment="总销量")
    units_produced = Column(Integer, nullable=False, default=0, comment="总产量")
    market_share_global = Column(Float, nullable=True, comment="全球市场份额（%）")
    
    # 信用评级快照
    credit_score = Column(Float, nullable=True, comment="信用评分")
    credit_rating = Column(String(10), nullable=True, comment="信用评级（AAA-D）")
    
    # 约束
    __table_args__ = (
        Index("idx_financial_history_turn", "turn_number"),
        Index("idx_financial_history_company", "company_id"),
        Index("idx_financial_history_composite", "company_id", "turn_number", unique=True),
    )
    
    def calculate_totals(self) -> None:
        """计算总收入和总成本"""
        total_revenue = (
            self.revenue_vehicles + 
            self.revenue_licensing + 
            self.revenue_other
        )
        
        total_costs = (
            self.cost_manufacturing + 
            self.cost_materials + 
            self.cost_labor + 
            self.cost_rd + 
            self.cost_marketing + 
            self.cost_admin + 
            self.cost_depreciation + 
            self.cost_interest
        )
        
        self.gross_profit = total_revenue - (
            self.cost_manufacturing + 
            self.cost_materials + 
            self.cost_labor
        )
        
        self.operating_profit = total_revenue - total_costs + self.cost_interest
        self.net_income = total_revenue - total_costs
    
    def __repr__(self) -> str:
        return (f"<FinancialHistory(turn={self.turn_number}, "
                f"company={self.company_id}, "
                f"net_income={self.net_income:,.0f})>")


class MarketDemandHistory(Base, TimestampMixin, BaseModel):
    """
    市场需求结算历史
    每回合记录地区需求、新车满足量、二手车承接量和流失原因。
    """
    __tablename__ = "market_demand_history"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)

    # 时间窗口
    turn_number = Column(Integer, nullable=False, comment="回合数")
    year = Column(Integer, nullable=False, comment="游戏内年份")
    month = Column(Integer, nullable=False, comment="游戏内月份")

    # 地区
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)

    # 需求分解
    total_demand = Column(Integer, nullable=False, default=0, comment="总需求")
    new_car_sales = Column(Integer, nullable=False, default=0, comment="新车成交")
    used_car_sales = Column(Integer, nullable=False, default=0, comment="二手车成交")
    lost_demand = Column(Integer, nullable=False, default=0, comment="最终流失需求")
    lost_reasons = Column(JSON, nullable=False, default=dict, comment="流失原因计数")

    # 关系
    region = relationship("Region", foreign_keys=[region_id])

    __table_args__ = (
        CheckConstraint("total_demand >= 0", name="check_market_demand_total"),
        CheckConstraint("new_car_sales >= 0", name="check_market_new_sales"),
        CheckConstraint("used_car_sales >= 0", name="check_market_used_sales"),
        CheckConstraint("lost_demand >= 0", name="check_market_lost_demand"),
        Index("idx_market_demand_game_turn", "game_id", "turn_number"),
        Index("idx_market_demand_region", "region_id"),
        Index("idx_market_demand_composite", "game_id", "turn_number", "region_id", unique=True),
    )

    def __repr__(self) -> str:
        return (f"<MarketDemandHistory(turn={self.turn_number}, "
                f"region={self.region_id}, demand={self.total_demand}, "
                f"new={self.new_car_sales}, used={self.used_car_sales})>")


class UsedCarInventory(Base, TimestampMixin, BaseModel):
    """
    二手车库存 - 统计桶方法 (Option A)
    按地区、车型、车况分组统计
    """
    __tablename__ = "used_car_inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # 地区与车型
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    car_trim_id = Column(Integer, nullable=False, comment="原始CarTrim ID")
    
    # 车况评分（合并指标）
    condition_score = Column(
        Float, nullable=False, default=75.0,
        comment="综合车况评分 0-100（考虑年龄、里程、维护）"
    )
    
    # 车龄（年）
    age_years = Column(
        Integer, nullable=False, default=0,
        comment="车龄（年）- 用于折旧计算"
    )
    
    # 数量
    quantity = Column(Integer, nullable=False, default=0, comment="可售数量")
    
    # 定价
    base_price = Column(
        Float, nullable=False,
        comment="基准价格（已考虑折旧）"
    )
    
    avg_asking_price = Column(
        Float, nullable=False,
        comment="平均要价（市场浮动后）"
    )
    
    # 折旧率（每年）
    depreciation_rate = Column(
        Float, nullable=False, default=0.15,
        comment="年度折旧率（0-1）"
    )
    
    # 关系
    region = relationship("Region", foreign_keys=[region_id])
    
    # 约束
    __table_args__ = (
        CheckConstraint("condition_score >= 0 AND condition_score <= 100", name="check_condition"),
        CheckConstraint("age_years >= 0", name="check_age"),
        CheckConstraint("quantity >= 0", name="check_quantity"),
        CheckConstraint("base_price >= 0", name="check_base_price"),
        CheckConstraint("depreciation_rate >= 0.0 AND depreciation_rate <= 1.0", name="check_depreciation"),
        Index("idx_used_car_region", "region_id"),
        Index("idx_used_car_trim", "car_trim_id"),
        Index("idx_used_car_composite", "region_id", "car_trim_id", "age_years", unique=True),
    )
    
    def apply_monthly_depreciation(self) -> None:
        """
        应用月度折旧
        """
        monthly_rate = self.depreciation_rate / 12.0
        self.base_price *= (1.0 - monthly_rate)
        self.avg_asking_price *= (1.0 - monthly_rate)
        
        # 车况随时间下降（每月-0.2分）
        self.condition_score = max(0.0, self.condition_score - 0.2)
    
    def calculate_utility_penalty(self) -> float:
        """
        计算二手车的效用惩罚系数
        
        Returns:
            效用惩罚系数（0-1），用于市场竞争
        """
        # 车况影响（线性）
        condition_factor = self.condition_score / 100.0
        
        # 车龄影响（对数衰减）
        age_penalty = 1.0 - (self.age_years * 0.08)  # 每年-8%
        age_penalty = max(0.3, age_penalty)  # 最低保留30%
        
        # 综合系数
        return condition_factor * age_penalty
    
    def __repr__(self) -> str:
        return (f"<UsedCarInventory(region={self.region_id}, "
                f"trim={self.car_trim_id}, age={self.age_years}y, "
                f"qty={self.quantity}, price={self.base_price:,.0f})>")


# 导出所有模型
__all__ = [
    "SalesHistory",
    "FinancialHistory",
    "MarketDemandHistory",
    "UsedCarInventory"
]


