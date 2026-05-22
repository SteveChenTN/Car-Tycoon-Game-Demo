"""
生产历史记录模型
跟踪每个车型的生产数量和质量爬坡阶段
"""
from sqlalchemy import Column, Integer, Float, String, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from typing import Dict, Any

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class ProductionHistory(Base, TimestampMixin, BaseModel):
    """
    生产历史记录 - 跟踪每个车型的生产数量和质量
    
    用于实现可靠性增长机制：
    - 早期生产（0-1000辆）：可靠性较低（学习曲线）
    - 稳定生产（1000-5000辆）：可靠性正常
    - 优化生产（5000-20000辆）：可靠性提升
    - 成熟生产（20000+辆）：可靠性最高
    """
    __tablename__ = "production_history"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    car_trim_id = Column(Integer, ForeignKey("car_trims.id", ondelete="CASCADE"), nullable=False)
    factory_id = Column(Integer, ForeignKey("factories.id", ondelete="CASCADE"), nullable=False,
                       comment="主要生产工厂ID")
    
    # ========== 生产统计 ==========
    total_units_produced = Column(Integer, nullable=False, default=0,
                                  comment="累计生产数量")
    
    # ========== 可靠性增长 ==========
    current_reliability_multiplier = Column(Float, nullable=False, default=1.0,
                                           comment="当前可靠性倍数（基于经验）0.95-1.10")
    
    quality_ramp_up_stage = Column(String(20), nullable=False, default="EARLY",
                                  comment="质量爬坡阶段：EARLY/MID/MATURE/OPTIMIZED")
    
    # ========== 时间追踪 ==========
    first_production_turn = Column(Integer, nullable=True,
                                  comment="首次生产回合")
    last_production_turn = Column(Integer, nullable=True,
                                 comment="最后生产回合")
    
    # ========== 质量指标 ==========
    average_defect_rate = Column(Float, nullable=False, default=0.02,
                                comment="平均缺陷率 0-1")
    
    quality_improvement_rate = Column(Float, nullable=False, default=0.0,
                                     comment="质量改进速率（每1000辆的改进）")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("total_units_produced >= 0", name="check_positive_units"),
        CheckConstraint("current_reliability_multiplier >= 0.5 AND current_reliability_multiplier <= 1.5", 
                       name="check_reliability_multiplier"),
        CheckConstraint("average_defect_rate >= 0 AND average_defect_rate <= 1", 
                       name="check_defect_rate"),
        Index("idx_production_history_company", "company_id"),
        Index("idx_production_history_car", "car_trim_id"),
        Index("idx_production_history_factory", "factory_id"),
        Index("idx_production_history_game", "game_id"),
        # 确保每个公司-车型-工厂组合只有一条记录
        Index("idx_production_history_unique", "company_id", "car_trim_id", "factory_id", unique=True),
    )
    
    # ========== 关系 ==========
    company = relationship("Company", foreign_keys=[company_id])
    car_trim = relationship("CarTrim", foreign_keys=[car_trim_id])
    factory = relationship("Factory", foreign_keys=[factory_id])
    
    def update_production(self, units_produced: int, current_turn: int, defect_rate: float = 0.02) -> None:
        """
        更新生产记录
        
        Args:
            units_produced: 本次生产数量
            current_turn: 当前回合
            defect_rate: 本次生产的缺陷率
        """
        if self.first_production_turn is None:
            self.first_production_turn = current_turn
        
        self.last_production_turn = current_turn
        self.total_units_produced += units_produced
        
        # 更新平均缺陷率（加权平均）
        if self.total_units_produced > 0:
            weight_old = (self.total_units_produced - units_produced) / self.total_units_produced
            weight_new = units_produced / self.total_units_produced
            self.average_defect_rate = (
                self.average_defect_rate * weight_old + 
                defect_rate * weight_new
            )
    
    def get_quality_stage(self) -> str:
        """
        根据生产数量计算质量爬坡阶段
        
        Returns:
            质量阶段：EARLY/MID/MATURE/OPTIMIZED
        """
        units = self.total_units_produced
        
        if units < 1000:
            return "EARLY"
        elif units < 5000:
            return "MID"
        elif units < 20000:
            return "MATURE"
        else:
            return "OPTIMIZED"
    
    def calculate_reliability_multiplier(self) -> float:
        """
        根据生产数量计算可靠性倍数
        
        Returns:
            可靠性倍数 0.95-1.10
        """
        units = self.total_units_produced
        
        # 增长曲线：
        # 0-1000辆：可靠性 × 0.95（早期问题）
        # 1000-5000辆：可靠性 × 1.0（稳定）
        # 5000-20000辆：可靠性 × 1.05（优化）
        # 20000+辆：可靠性 × 1.10（成熟）
        
        if units < 1000:
            # 线性从0.95到1.0
            multiplier = 0.95 + (units / 1000.0) * 0.05
        elif units < 5000:
            # 稳定在1.0
            multiplier = 1.0
        elif units < 20000:
            # 线性从1.0到1.05
            multiplier = 1.0 + ((units - 5000) / 15000.0) * 0.05
        else:
            # 线性从1.05到1.10（20000-50000）
            additional_units = min(units - 20000, 30000)
            multiplier = 1.05 + (additional_units / 30000.0) * 0.05
            multiplier = min(1.10, multiplier)  # 最多1.10
        
        return round(multiplier, 4)
    
    def update_reliability_from_production(self) -> None:
        """
        根据当前生产数量更新可靠性倍数和质量阶段
        """
        self.quality_ramp_up_stage = self.get_quality_stage()
        self.current_reliability_multiplier = self.calculate_reliability_multiplier()
    
    def to_dict(self) -> Dict[str, Any]:
        """扩展基类方法"""
        base_dict = super().to_dict()
        base_dict.update({
            "quality_stage": self.get_quality_stage(),
            "reliability_multiplier": self.current_reliability_multiplier,
            "defect_rate_percent": round(self.average_defect_rate * 100, 2)
        })
        return base_dict
    
    def __repr__(self) -> str:
        return (f"<ProductionHistory(company_id={self.company_id}, "
                f"car_trim_id={self.car_trim_id}, "
                f"units={self.total_units_produced}, "
                f"stage={self.quality_ramp_up_stage}, "
                f"multiplier={self.current_reliability_multiplier:.3f})>")


__all__ = ["ProductionHistory"]


