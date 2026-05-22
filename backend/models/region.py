"""
地区和市场特征模型
"""
from sqlalchemy import (
    Column, Integer, String, Float, BigInteger, Text, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from typing import Dict, Any
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class Region(Base, TimestampMixin, BaseModel):
    """
    地区模型
    代表一个经济区域（如北美、欧洲等）
    包含经济指标、市场特征、政策法规等
    """
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(
        Integer, 
        ForeignKey("game_state.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的游戏ID"
    )
    
    # 基础信息
    code = Column(
        String(10),
        nullable=False,
        index=True,
        comment="地区代码 (NAM, EUR, ASI, etc.)"
    )
    name = Column(
        String(255),
        nullable=False,
        comment="地区名称"
    )
    
    # ==================== 经济指标 ====================
    population = Column(
        BigInteger,
        nullable=False,
        comment="总人口"
    )
    gdp_per_capita = Column(
        Float,
        nullable=False,
        comment="人均GDP（游戏货币）"
    )
    gdp_growth_rate = Column(
        Float,
        nullable=False,
        default=0.02,
        comment="年度GDP增长率（如0.02 = 2%）"
    )
    purchasing_power_index = Column(
        Float,
        nullable=False,
        comment="购买力指数（相对于基准）"
    )
    inflation_rate = Column(
        Float,
        nullable=False,
        default=0.03,
        comment="通货膨胀率"
    )
    unemployment_rate = Column(
        Float,
        nullable=False,
        default=0.05,
        comment="失业率"
    )
    
    # ==================== 市场特征 ====================
    car_ownership_rate = Column(
        Float,
        nullable=False,
        comment="汽车保有量（每千人拥有汽车数量）"
    )
    avg_vehicle_age = Column(
        Float,
        nullable=False,
        comment="平均车龄（年）"
    )
    annual_sales_potential = Column(
        Integer,
        nullable=False,
        comment="年度最大市场容量（辆）"
    )
    
    # ==================== 基础设施与环境 ====================
    infrastructure_quality = Column(
        Float,
        nullable=False,
        comment="基础设施质量 (0-1)"
    )
    road_quality = Column(
        Float,
        nullable=False,
        comment="道路质量 (0-1)"
    )
    fuel_price = Column(
        Float,
        nullable=False,
        comment="燃油价格（每升，游戏货币）"
    )
    electricity_price = Column(
        Float,
        nullable=False,
        comment="电价（每kWh，游戏货币）"
    )
    
    # ==================== 政策与法规 ====================
    import_tariff_rate = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="进口关税率"
    )
    emission_standard = Column(
        String(50),
        nullable=False,
        comment="排放标准 (NONE, EURO1, EURO2, etc.)"
    )
    safety_standard = Column(
        String(50),
        nullable=False,
        comment="安全标准 (BASIC, MODERATE, STRICT)"
    )
    corporate_tax_rate = Column(
        Float,
        nullable=False,
        comment="企业税率"
    )
    ev_subsidy_rate = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="电动车补贴率"
    )
    
    # ==================== 二手车交易政策（Patch 1.4新增）====================
    allow_used_export = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="允许二手车出口"
    )
    allow_used_import = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="允许二手车进口"
    )
    
    # ==================== 资源可用性（影响工厂建设） ====================
    steel_availability = Column(
        Float,
        nullable=False,
        comment="钢铁供应 (0-1)"
    )
    aluminum_availability = Column(
        Float,
        nullable=False,
        comment="铝材供应 (0-1)"
    )
    rare_earth_availability = Column(
        Float,
        nullable=False,
        comment="稀土供应 (0-1)"
    )
    labor_cost_index = Column(
        Float,
        nullable=False,
        comment="劳动力成本指数（相对基准）"
    )
    skilled_labor_availability = Column(
        Float,
        nullable=False,
        comment="技术工人可用性 (0-1)"
    )
    
    # ==================== 文化偏好（基础修正值） ====================
    pref_size_small = Column(Float, nullable=False, default=0.33, comment="偏好小型车")
    pref_size_medium = Column(Float, nullable=False, default=0.34, comment="偏好中型车")
    pref_size_large = Column(Float, nullable=False, default=0.33, comment="偏好大型车")
    
    pref_body_sedan = Column(Float, nullable=False, default=0.40, comment="偏好轿车")
    pref_body_suv = Column(Float, nullable=False, default=0.30, comment="偏好SUV")
    pref_body_hatchback = Column(Float, nullable=False, default=0.15, comment="偏好掀背车")
    pref_body_coupe = Column(Float, nullable=False, default=0.10, comment="偏好轿跑")
    pref_body_wagon = Column(Float, nullable=False, default=0.05, comment="偏好旅行车")
    
    pref_fuel_efficiency_weight = Column(
        Float, 
        nullable=False, 
        default=0.5,
        comment="燃油经济性权重"
    )
    pref_power_weight = Column(
        Float,
        nullable=False,
        default=0.5,
        comment="动力性能权重"
    )
    
    # ==================== 关系 ====================
    game = relationship("GameState", back_populates="regions")
    
    # 索引
    __table_args__ = (
        {"comment": "地区数据表：存储各经济区域的特征和参数"}
    )
    
    def get_total_gdp(self) -> float:
        """
        计算总GDP
        
        Returns:
            总GDP = 人口 × 人均GDP
        """
        return self.population * self.gdp_per_capita
    
    def get_addressable_market_size(self) -> int:
        """
        计算可触及的市场规模（潜在购车人群）
        
        Returns:
            潜在年度购车量
        """
        # 基于人口、汽车保有量和更新周期计算
        total_cars = (self.population / 1000) * self.car_ownership_rate
        replacement_rate = 1.0 / max(self.avg_vehicle_age, 1.0)
        return int(total_cars * replacement_rate)
    
    def calculate_demand_modifier(self) -> float:
        """
        计算需求修正系数
        基于经济状况（失业率、GDP增长等）
        
        Returns:
            需求修正系数 (0.5 - 1.5)
        """
        modifier = 1.0
        
        # GDP增长影响
        modifier += (self.gdp_growth_rate - 0.03) * 2.0
        
        # 失业率影响（每1%失业率降低0.5%需求）
        modifier -= self.unemployment_rate * 0.5
        
        # 限制在合理范围
        return max(0.5, min(1.5, modifier))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（增强版）
        包含计算字段
        """
        data = super().to_dict()
        data["total_gdp"] = self.get_total_gdp()
        data["addressable_market"] = self.get_addressable_market_size()
        data["demand_modifier"] = self.calculate_demand_modifier()
        return data


__all__ = ["Region"]

