"""
工厂工艺和材料熟悉度模型
跟踪工厂对特定制造工艺和材料的加工经验
"""
from sqlalchemy import Column, Integer, Float, String, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from typing import Dict, Any

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class FactoryProcessFamiliarity(Base, TimestampMixin, BaseModel):
    """
    工厂工艺熟悉度 - 跟踪工厂对特定制造工艺的经验
    
    工艺类型示例：
    - CAST_IRON_ENGINE_V8
    - ALUMINUM_CHASSIS_FR
    - TURBO_ASSEMBLY
    """
    __tablename__ = "factory_process_familiarity"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    factory_id = Column(Integer, ForeignKey("factories.id", ondelete="CASCADE"), nullable=False)
    
    # ========== 工艺识别 ==========
    process_type = Column(String(50), nullable=False,
                         comment="工艺类型代码，如 'CAST_IRON_ENGINE_V8'")
    category = Column(String(20), nullable=False,
                     comment="类别：ENGINE_MANUFACTURING/CHASSIS_MANUFACTURING/ASSEMBLY")
    
    # ========== 经验值系统 ==========
    experience_points = Column(Integer, nullable=False, default=0,
                              comment="经验点数（累计）")
    familiarity_level = Column(Integer, nullable=False, default=1,
                             comment="熟悉度等级 1-10")
    
    # ========== 生产统计 ==========
    total_units_produced = Column(Integer, nullable=False, default=0,
                                 comment="累计生产数量")
    first_production_turn = Column(Integer, nullable=True,
                                  comment="首次生产回合")
    
    # ========== 效果加成（动态计算） ==========
    quality_bonus = Column(Float, nullable=False, default=0.0,
                          comment="质量加成（百分比）0-5%")
    reliability_bonus = Column(Float, nullable=False, default=0.0,
                              comment="可靠性加成（百分比）0-3%")
    defect_rate_reduction = Column(Float, nullable=False, default=0.0,
                                  comment="缺陷率降低（百分比）0-12%")
    production_efficiency_bonus = Column(Float, nullable=False, default=0.0,
                                        comment="生产效率加成（百分比）0-8%")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("experience_points >= 0", name="check_positive_exp"),
        CheckConstraint("familiarity_level >= 1 AND familiarity_level <= 10", 
                       name="check_process_level"),
        CheckConstraint("total_units_produced >= 0", name="check_positive_units"),
        CheckConstraint("quality_bonus >= 0 AND quality_bonus <= 0.05", 
                       name="check_quality_bonus"),
        CheckConstraint("reliability_bonus >= 0 AND reliability_bonus <= 0.03", 
                       name="check_reliability_bonus"),
        CheckConstraint("defect_rate_reduction >= 0 AND defect_rate_reduction <= 0.12", 
                       name="check_defect_reduction"),
        CheckConstraint("production_efficiency_bonus >= 0 AND production_efficiency_bonus <= 0.08", 
                       name="check_efficiency_bonus"),
        Index("idx_factory_process_factory", "factory_id"),
        Index("idx_factory_process_type", "process_type", "category"),
        Index("idx_factory_process_game", "game_id"),
        # 确保每个工厂-工艺组合只有一条记录
        Index("idx_factory_process_unique", "factory_id", "process_type", "category", unique=True),
    )
    
    # ========== 关系 ==========
    factory = relationship("Factory", foreign_keys=[factory_id])
    
    def add_experience(self, experience_points: int, current_turn: int) -> None:
        """增加经验值并更新等级和加成"""
        if self.first_production_turn is None:
            self.first_production_turn = current_turn
        
        self.experience_points += experience_points
        self._update_familiarity_level()
        self._update_bonuses()
    
    def _update_familiarity_level(self) -> None:
        """根据经验点数更新熟悉度等级"""
        if self.experience_points < 10:
            level = 1
        elif self.experience_points < 50:
            level = 2
        elif self.experience_points < 100:
            level = 3
        elif self.experience_points < 200:
            level = 4
        elif self.experience_points < 400:
            level = 5
        elif self.experience_points < 800:
            level = 6
        elif self.experience_points < 1500:
            level = 7
        elif self.experience_points < 3000:
            level = 8
        elif self.experience_points < 6000:
            level = 9
        else:
            level = 10
        
        self.familiarity_level = level
    
    def _update_bonuses(self) -> None:
        """根据熟悉度等级更新效果加成"""
        level = self.familiarity_level
        
        # 工艺熟悉度等级效果：
        # 等级1-2：无加成
        # 等级3-4：质量+1%，可靠性+0.5%，缺陷率-2%
        # 等级5-6：质量+2%，可靠性+1%，缺陷率-5%，效率+3%
        # 等级7-8：质量+3%，可靠性+2%，缺陷率-8%，效率+5%
        # 等级9-10：质量+5%，可靠性+3%，缺陷率-12%，效率+8%
        
        if level <= 2:
            self.quality_bonus = 0.0
            self.reliability_bonus = 0.0
            self.defect_rate_reduction = 0.0
            self.production_efficiency_bonus = 0.0
        elif level <= 4:
            self.quality_bonus = 0.01
            self.reliability_bonus = 0.005
            self.defect_rate_reduction = 0.02
            self.production_efficiency_bonus = 0.0
        elif level <= 6:
            self.quality_bonus = 0.02
            self.reliability_bonus = 0.01
            self.defect_rate_reduction = 0.05
            self.production_efficiency_bonus = 0.03
        elif level <= 8:
            self.quality_bonus = 0.03
            self.reliability_bonus = 0.02
            self.defect_rate_reduction = 0.08
            self.production_efficiency_bonus = 0.05
        else:  # 9-10
            self.quality_bonus = 0.05
            self.reliability_bonus = 0.03
            self.defect_rate_reduction = 0.12
            self.production_efficiency_bonus = 0.08
    
    def get_bonuses(self) -> Dict[str, float]:
        """获取所有加成效果"""
        return {
            "quality_bonus": self.quality_bonus,
            "reliability_bonus": self.reliability_bonus,
            "defect_rate_reduction": self.defect_rate_reduction,
            "production_efficiency_bonus": self.production_efficiency_bonus
        }
    
    def __repr__(self) -> str:
        return (f"<FactoryProcessFamiliarity(factory_id={self.factory_id}, "
                f"process='{self.process_type}', "
                f"level={self.familiarity_level}, "
                f"units={self.total_units_produced})>")


class FactoryMaterialFamiliarity(Base, TimestampMixin, BaseModel):
    """
    工厂材料熟悉度 - 跟踪工厂对特定材料的加工经验
    
    材料类型示例：
    - CAST_IRON (ENGINE_BLOCK)
    - ALUMINUM (CHASSIS)
    - STEEL (BODY)
    """
    __tablename__ = "factory_material_familiarity"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    factory_id = Column(Integer, ForeignKey("factories.id", ondelete="CASCADE"), nullable=False)
    
    # ========== 材料识别 ==========
    material_type = Column(String(30), nullable=False,
                          comment="材料类型：STEEL/ALUMINUM/CAST_IRON/CARBON等")
    application = Column(String(30), nullable=False,
                        comment="应用场景：ENGINE_BLOCK/CHASSIS/BODY等")
    
    # ========== 经验值系统 ==========
    experience_points = Column(Integer, nullable=False, default=0,
                              comment="经验点数（累计）")
    familiarity_level = Column(Integer, nullable=False, default=1,
                             comment="熟悉度等级 1-10")
    
    # ========== 加工统计 ==========
    total_kg_processed = Column(Float, nullable=False, default=0.0,
                               comment="累计加工材料重量（公斤）")
    first_use_turn = Column(Integer, nullable=True,
                           comment="首次使用回合")
    
    # ========== 效果加成（动态计算） ==========
    material_quality_bonus = Column(Float, nullable=False, default=0.0,
                                  comment="材料质量加成（百分比）0-5%")
    processing_cost_reduction = Column(Float, nullable=False, default=0.0,
                                      comment="加工成本降低（百分比）0-12%")
    reliability_bonus = Column(Float, nullable=False, default=0.0,
                             comment="可靠性加成（百分比）0-3%")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("experience_points >= 0", name="check_positive_exp_mat"),
        CheckConstraint("familiarity_level >= 1 AND familiarity_level <= 10", 
                       name="check_material_level"),
        CheckConstraint("total_kg_processed >= 0", name="check_positive_kg"),
        CheckConstraint("material_quality_bonus >= 0 AND material_quality_bonus <= 0.05", 
                       name="check_material_quality"),
        CheckConstraint("processing_cost_reduction >= 0 AND processing_cost_reduction <= 0.12", 
                       name="check_cost_reduction"),
        CheckConstraint("reliability_bonus >= 0 AND reliability_bonus <= 0.03", 
                       name="check_material_reliability"),
        Index("idx_factory_material_factory", "factory_id"),
        Index("idx_factory_material_type", "material_type", "application"),
        Index("idx_factory_material_game", "game_id"),
        # 确保每个工厂-材料-应用组合只有一条记录
        Index("idx_factory_material_unique", "factory_id", "material_type", "application", unique=True),
    )
    
    # ========== 关系 ==========
    factory = relationship("Factory", foreign_keys=[factory_id])
    
    def add_experience(self, experience_points: int, current_turn: int) -> None:
        """增加经验值并更新等级和加成"""
        if self.first_use_turn is None:
            self.first_use_turn = current_turn
        
        self.experience_points += experience_points
        self._update_familiarity_level()
        self._update_bonuses()
    
    def _update_familiarity_level(self) -> None:
        """根据经验点数更新熟悉度等级"""
        if self.experience_points < 10:
            level = 1
        elif self.experience_points < 50:
            level = 2
        elif self.experience_points < 100:
            level = 3
        elif self.experience_points < 200:
            level = 4
        elif self.experience_points < 400:
            level = 5
        elif self.experience_points < 800:
            level = 6
        elif self.experience_points < 1500:
            level = 7
        elif self.experience_points < 3000:
            level = 8
        elif self.experience_points < 6000:
            level = 9
        else:
            level = 10
        
        self.familiarity_level = level
    
    def _update_bonuses(self) -> None:
        """根据熟悉度等级更新效果加成"""
        level = self.familiarity_level
        
        # 材料熟悉度等级效果：
        # 等级1-2：无加成
        # 等级3-4：材料质量+1%，可靠性+0.5%，加工成本-2%
        # 等级5-6：材料质量+2%，可靠性+1%，加工成本-5%
        # 等级7-8：材料质量+3%，可靠性+2%，加工成本-8%
        # 等级9-10：材料质量+5%，可靠性+3%，加工成本-12%
        
        if level <= 2:
            self.material_quality_bonus = 0.0
            self.reliability_bonus = 0.0
            self.processing_cost_reduction = 0.0
        elif level <= 4:
            self.material_quality_bonus = 0.01
            self.reliability_bonus = 0.005
            self.processing_cost_reduction = 0.02
        elif level <= 6:
            self.material_quality_bonus = 0.02
            self.reliability_bonus = 0.01
            self.processing_cost_reduction = 0.05
        elif level <= 8:
            self.material_quality_bonus = 0.03
            self.reliability_bonus = 0.02
            self.processing_cost_reduction = 0.08
        else:  # 9-10
            self.material_quality_bonus = 0.05
            self.reliability_bonus = 0.03
            self.processing_cost_reduction = 0.12
    
    def get_bonuses(self) -> Dict[str, float]:
        """获取所有加成效果"""
        return {
            "material_quality_bonus": self.material_quality_bonus,
            "reliability_bonus": self.reliability_bonus,
            "processing_cost_reduction": self.processing_cost_reduction
        }
    
    def __repr__(self) -> str:
        return (f"<FactoryMaterialFamiliarity(factory_id={self.factory_id}, "
                f"material='{self.material_type}', "
                f"application='{self.application}', "
                f"level={self.familiarity_level}, "
                f"kg={self.total_kg_processed:.0f})>")


__all__ = ["FactoryProcessFamiliarity", "FactoryMaterialFamiliarity"]


