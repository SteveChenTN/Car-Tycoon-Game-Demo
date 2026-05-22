"""
供应链与制造核心数据模型

设计哲学：
- 分布式生产：区分零部件工厂（Engines）vs 整车装配厂
- 简化物流：自有工厂间运输抽象为成本/时间（MVP不需手动规划路线）
- 战略采购：原材料价格波动，需维持库存
- B2B能力：可从AI竞争对手处购买/出售零部件
"""
from sqlalchemy import (
    Column, Integer, Float, String, Boolean,
    ForeignKey, Text, Enum, CheckConstraint, Index, JSON
)
from sqlalchemy.orm import relationship, validates
from typing import Optional, Dict, Any
import enum
from datetime import datetime

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


# ========== 枚举定义 ==========

class FactoryType(enum.Enum):
    """工厂类型枚举"""
    COMPONENT = "COMPONENT"  # 零部件工厂（引擎、变速箱等）
    ASSEMBLY = "ASSEMBLY"    # 整车装配厂
    

class MaterialType(enum.Enum):
    """原材料类型枚举"""
    STEEL = "STEEL"              # 钢材
    ALUMINUM = "ALUMINUM"        # 铝材
    PLASTIC = "PLASTIC"          # 塑料
    ELECTRONICS = "ELECTRONICS"  # 电子元件
    RUBBER = "RUBBER"            # 橡胶
    GLASS = "GLASS"              # 玻璃


class ProcurementPolicy(enum.Enum):
    """采购策略枚举（AI使用）"""
    JUST_IN_TIME = "JUST_IN_TIME"  # 准时制：只买本周需要的
    HOARDER = "HOARDER"            # 囤积型：价格低于均值10%时大量采购
    BALANCED = "BALANCED"          # 平衡型：维持2周库存


# ========== 工厂模型 ==========

class Factory(Base, TimestampMixin, BaseModel):
    """
    工厂模型 - 生产设施
    
    核心设计：
    - 零部件工厂生产引擎/变速箱等Components
    - 装配厂组装完整车辆
    - 效率受等级和技术水平影响
    """
    __tablename__ = "factories"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False,
                       comment="所属公司ID（暂不使用外键，等companies表创建后再添加）")
    
    name = Column(String(100), nullable=False, comment="工厂名称，如 'Detroit Engine Plant #3'")
    
    # ========== 类型与能力 ==========
    factory_type = Column(
        String(20), nullable=False,
        comment="工厂类型：COMPONENT（零部件）/ ASSEMBLY（装配）"
    )
    
    level = Column(Integer, nullable=False, default=1,
                  comment="工厂等级 1-10，影响效率和成本")
    
    capacity_units_per_month = Column(Integer, nullable=False,
                                     comment="月产能（单位数）- 零部件工厂为件数，装配厂为车辆数")
    
    current_utilization_rate = Column(Float, nullable=False, default=0.0,
                                     comment="当前利用率 0.0-1.0")
    
    # ========== 地理位置 ==========
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="RESTRICT"), nullable=False,
                      comment="所在地区ID - 影响物流成本和劳动力成本")
    
    # ========== 效率与成本 ==========
    efficiency_score = Column(Float, nullable=False, default=80.0,
                             comment="效率评分 0-100，影响实际产能和单位成本")
    
    labor_cost_per_unit = Column(Float, nullable=False,
                                comment="单位劳动力成本 - 受地区和工厂等级影响")
    
    overhead_cost_per_month = Column(Float, nullable=False,
                                    comment="月固定开销（维护、管理、水电）")
    
    # ========== 技术能力 ==========
    tech_level = Column(Integer, nullable=False, default=1,
                       comment="技术等级 1-10，决定能生产的最高科技零部件")
    
    # ========== 状态 ==========
    is_operational = Column(Boolean, nullable=False, default=True,
                          comment="是否运营中（False表示停工/维护）")
    
    construction_completed_turn = Column(Integer, nullable=True,
                                        comment="建设完成回合数")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("level >= 1 AND level <= 10", name="check_factory_level"),
        CheckConstraint("capacity_units_per_month > 0", name="check_positive_capacity"),
        CheckConstraint("current_utilization_rate >= 0 AND current_utilization_rate <= 1.0", 
                       name="check_utilization_range"),
        CheckConstraint("efficiency_score >= 0 AND efficiency_score <= 100", 
                       name="check_efficiency_range"),
        CheckConstraint("tech_level >= 1 AND tech_level <= 10", name="check_factory_tech_level"),
        Index("idx_factory_company", "company_id"),
        Index("idx_factory_region", "region_id"),
        Index("idx_factory_type", "factory_type"),
        Index("idx_factory_operational", "is_operational"),
    )
    
    # ========== 关系 ==========
    region = relationship("Region", foreign_keys=[region_id])
    inventories = relationship("Inventory", back_populates="factory", cascade="all, delete-orphan")
    
    @validates("factory_type")
    def validate_factory_type(self, key: str, value: str) -> str:
        """验证工厂类型"""
        allowed = [ft.value for ft in FactoryType]
        if value.upper() not in allowed:
            raise ValueError(f"工厂类型必须是以下之一: {allowed}")
        return value.upper()
    
    def get_effective_capacity(self) -> int:
        """计算有效产能（考虑效率评分）"""
        if not self.is_operational:
            return 0
        return int(self.capacity_units_per_month * (self.efficiency_score / 100.0))
    
    def to_dict(self) -> Dict[str, Any]:
        """扩展基类方法"""
        base_dict = super().to_dict()
        base_dict.update({
            "effective_capacity": self.get_effective_capacity(),
            "utilization_percentage": round(self.current_utilization_rate * 100, 1),
        })
        return base_dict
    
    def __repr__(self) -> str:
        return (f"<Factory(name='{self.name}', "
                f"type={self.factory_type}, "
                f"level={self.level}, "
                f"capacity={self.capacity_units_per_month}/mo, "
                f"utilization={self.current_utilization_rate:.0%})>")


# ========== 原材料市场模型 ==========

class MaterialMarket(Base, TimestampMixin, BaseModel):
    """
    原材料市场价格跟踪
    
    设计说明：
    - 全局或地区级价格波动（由经济引擎驱动）
    - 玩家需要提前采购以锁定成本
    - 价格历史用于AI决策（趋势分析）
    """
    __tablename__ = "material_market"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=True,
                      comment="地区ID - NULL表示全球市场价格")
    
    # ========== 材料与价格 ==========
    material_type = Column(
        String(20), nullable=False,
        comment="材料类型：STEEL/ALUMINUM/PLASTIC/ELECTRONICS/RUBBER/GLASS"
    )
    
    current_price_per_kg = Column(Float, nullable=False,
                                  comment="当前价格（游戏币/公斤）")
    
    historical_avg_price = Column(Float, nullable=False,
                                  comment="历史平均价格（用于AI判断高低点）")
    
    price_volatility = Column(Float, nullable=False, default=0.1,
                             comment="价格波动率 0.0-1.0")
    
    # ========== 供应状况 ==========
    supply_level = Column(Float, nullable=False, default=1.0,
                         comment="供应水平 0.0-2.0，1.0为正常，<1.0为短缺，>1.0为过剩")
    
    # ========== 时间戳（记录价格更新周期） ==========
    last_update_turn = Column(Integer, nullable=False,
                             comment="最后更新的回合数")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("current_price_per_kg > 0", name="check_positive_price"),
        CheckConstraint("price_volatility >= 0 AND price_volatility <= 1.0", 
                       name="check_volatility_range"),
        CheckConstraint("supply_level >= 0", name="check_positive_supply"),
        Index("idx_material_game_region", "game_id", "region_id"),
        Index("idx_material_type", "material_type"),
    )
    
    # ========== 关系 ==========
    region = relationship("Region", foreign_keys=[region_id])
    
    @validates("material_type")
    def validate_material_type(self, key: str, value: str) -> str:
        """验证材料类型"""
        allowed = [mt.value for mt in MaterialType]
        if value.upper() not in allowed:
            raise ValueError(f"材料类型必须是以下之一: {allowed}")
        return value.upper()
    
    def is_below_average(self, threshold: float = 0.9) -> bool:
        """判断当前价格是否低于历史均值（用于AI采购决策）"""
        return self.current_price_per_kg < (self.historical_avg_price * threshold)
    
    def __repr__(self) -> str:
        return (f"<MaterialMarket(material={self.material_type}, "
                f"price={self.current_price_per_kg:.2f}, "
                f"supply_level={self.supply_level:.2f})>")


# ========== 库存模型 ==========

class Inventory(Base, TimestampMixin, BaseModel):
    """
    库存管理 - 每个工厂的库存记录
    
    库存类型：
    1. 原材料（Raw Materials）
    2. 零部件（Finished Components）- 如引擎、变速箱
    3. 成品车（Completed Cars）- 待发货的车辆
    
    简化设计：
    - 使用JSON字段存储灵活的库存数据
    - 避免为每种材料/零部件创建单独的表
    """
    __tablename__ = "inventories"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    factory_id = Column(Integer, ForeignKey("factories.id", ondelete="CASCADE"), nullable=False,
                       comment="所属工厂ID")
    
    # ========== 原材料库存（JSON格式） ==========
    raw_materials = Column(JSON, nullable=False, default=dict,
                          comment="""原材料库存（公斤）
                          格式: {
                              "STEEL": 50000,
                              "ALUMINUM": 10000,
                              "PLASTIC": 5000,
                              ...
                          }""")
    
    # ========== 零部件库存（JSON格式） ==========
    finished_components = Column(JSON, nullable=False, default=dict,
                                comment="""成品零部件库存（件数）
                                格式: {
                                    "engine_123": 150,    # 引擎ID: 数量
                                    "engine_456": 80,
                                    "transmission_789": 200,
                                    ...
                                }""")
    
    # ========== 成品车库存（JSON格式） ==========
    completed_cars = Column(JSON, nullable=False, default=dict,
                           comment="""成品车库存（辆数）
                           格式: {
                               "trim_101": 500,  # 车型Trim ID: 数量
                               "trim_102": 300,
                               ...
                           }""")
    
    # ========== 库存价值（缓存计算） ==========
    total_inventory_value = Column(Float, nullable=False, default=0.0,
                                   comment="库存总价值（游戏币）- 定期重新计算")
    
    last_valuation_turn = Column(Integer, nullable=True,
                                comment="最后一次估值的回合数")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("total_inventory_value >= 0", name="check_positive_value"),
        Index("idx_inventory_factory", "factory_id"),
        Index("idx_inventory_game", "game_id"),
    )
    
    # ========== 关系 ==========
    factory = relationship("Factory", back_populates="inventories")
    
    def get_material_quantity(self, material_type: str) -> float:
        """获取指定原材料的库存量（公斤）"""
        if not self.raw_materials:
            return 0.0
        return self.raw_materials.get(material_type.upper(), 0.0)
    
    def add_material(self, material_type: str, quantity: float) -> None:
        """增加原材料库存"""
        if not self.raw_materials:
            self.raw_materials = {}
        material_key = material_type.upper()
        current = self.raw_materials.get(material_key, 0.0)
        self.raw_materials[material_key] = current + quantity
        # 标记JSON字段为已修改（SQLAlchemy需要这个）
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'raw_materials')
    
    def deduct_material(self, material_type: str, quantity: float) -> bool:
        """扣减原材料库存，如果库存不足返回False"""
        current = self.get_material_quantity(material_type)
        if current < quantity:
            return False
        material_key = material_type.upper()
        self.raw_materials[material_key] = current - quantity
        # 标记JSON字段为已修改
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'raw_materials')
        return True
    
    def get_component_quantity(self, component_id: int) -> int:
        """获取指定零部件的库存量"""
        if not self.finished_components:
            return 0
        component_key = f"engine_{component_id}"  # 简化：假设主要是引擎
        return self.finished_components.get(component_key, 0)
    
    def add_component(self, component_type: str, component_id: int, quantity: int) -> None:
        """增加零部件库存
        
        Args:
            component_type: 组件类型 (engine, transmission, etc.)
            component_id: 组件ID
            quantity: 数量
        """
        if not self.finished_components:
            self.finished_components = {}
        component_key = f"{component_type}_{component_id}"
        current = self.finished_components.get(component_key, 0)
        self.finished_components[component_key] = current + quantity
        # 标记JSON字段为已修改
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'finished_components')
    
    def deduct_component(self, component_type: str, component_id: int, quantity: int) -> bool:
        """扣减零部件库存，如果库存不足返回False"""
        component_key = f"{component_type}_{component_id}"
        current = self.finished_components.get(component_key, 0) if self.finished_components else 0
        if current < quantity:
            return False
        self.finished_components[component_key] = current - quantity
        # 标记JSON字段为已修改
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'finished_components')
        return True
    
    def get_car_quantity(self, car_trim_id: int) -> int:
        """获取指定车型的库存量"""
        if not self.completed_cars:
            return 0
        car_key = f"trim_{car_trim_id}"
        return self.completed_cars.get(car_key, 0)
    
    def add_car(self, car_trim_id: int, quantity: int) -> None:
        """增加成品车库存"""
        if not self.completed_cars:
            self.completed_cars = {}
        car_key = f"trim_{car_trim_id}"
        current = self.completed_cars.get(car_key, 0)
        self.completed_cars[car_key] = current + quantity
        # 标记JSON字段为已修改
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'completed_cars')
    
    def deduct_car(self, car_trim_id: int, quantity: int) -> bool:
        """扣减成品车库存，如果库存不足返回False"""
        car_key = f"trim_{car_trim_id}"
        current = self.completed_cars.get(car_key, 0) if self.completed_cars else 0
        if current < quantity:
            return False
        self.completed_cars[car_key] = current - quantity
        # 标记JSON字段为已修改
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'completed_cars')
        return True
    
    def __repr__(self) -> str:
        material_count = len(self.raw_materials) if self.raw_materials else 0
        component_count = len(self.finished_components) if self.finished_components else 0
        car_count = len(self.completed_cars) if self.completed_cars else 0
        return (f"<Inventory(factory_id={self.factory_id}, "
                f"materials={material_count} types, "
                f"components={component_count} types, "
                f"cars={car_count} types, "
                f"value=${self.total_inventory_value:,.0f})>")


# ========== 生产线模型 ==========

class ProductionLine(Base, TimestampMixin, BaseModel):
    """
    生产线模型 - 工厂内的具体生产线
    
    设计说明：
    - 每个工厂可以有多个生产线
    - 每条生产线可以生产不同的车型
    - 切换车型需要重新配置（retooling）
    """
    __tablename__ = "production_lines"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    factory_id = Column(Integer, ForeignKey("factories.id", ondelete="CASCADE"), nullable=False,
                       comment="所属工厂ID")
    
    name = Column(String(100), nullable=True,
                 comment="生产线名称，如 'Line A', 'Line B'")
    
    # ========== 生产状态 ==========
    status = Column(String(20), nullable=False, default="IDLE",
                   comment="生产线状态：IDLE/RUNNING/RETOOLING/MAINTENANCE")
    
    current_design_id = Column(Integer, ForeignKey("car_trims.id", ondelete="SET NULL"), nullable=True,
                              comment="当前生产的车型ID（NULL表示空闲）")
    
    # ========== 产能 ==========
    monthly_capacity = Column(Integer, nullable=False, default=1000,
                             comment="月产能（车辆数）")
    
    # ========== 重新配置 ==========
    retooling_until_turn = Column(Integer, nullable=True,
                                 comment="重新配置完成回合数（NULL表示未在重新配置）")
    retooling_cost = Column(Float, nullable=True,
                           comment="重新配置成本（百万游戏币）")
    retooling_start_turn = Column(Integer, nullable=True,
                                 comment="开始重新配置的回合")
    previous_design_id = Column(Integer, ForeignKey("car_trims.id", ondelete="SET NULL"), nullable=True,
                                comment="之前生产的车型ID（用于计算切换成本）")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("monthly_capacity > 0", name="check_positive_line_capacity"),
        Index("idx_production_line_factory", "factory_id"),
        Index("idx_production_line_design", "current_design_id"),
        Index("idx_production_line_status", "status"),
    )
    
    # ========== 关系 ==========
    factory = relationship("Factory", foreign_keys=[factory_id])
    car_trim = relationship("CarTrim", foreign_keys=[current_design_id])
    
    def is_idle(self) -> bool:
        """检查生产线是否空闲"""
        return self.status == "IDLE" and self.current_design_id is None
    
    def is_retooling(self) -> bool:
        """检查生产线是否在重新配置"""
        return self.status == "RETOOLING" or self.retooling_until_turn is not None
    
    def __repr__(self) -> str:
        return (f"<ProductionLine(id={self.id}, "
                f"factory_id={self.factory_id}, "
                f"status={self.status}, "
                f"design_id={self.current_design_id})>")


# 导出所有模型和枚举
__all__ = [
    "Factory", 
    "MaterialMarket", 
    "Inventory",
    "ProductionLine",
    "FactoryType",
    "MaterialType",
    "ProcurementPolicy"
]

