"""
工程熟悉度模型
跟踪公司对特定引擎布局和底盘配置的设计经验
"""
from sqlalchemy import Column, Integer, Float, String, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from typing import Dict, Any

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class EngineeringFamiliarity(Base, TimestampMixin, BaseModel):
    """
    工程熟悉度 - 跟踪公司对特定布局的设计经验
    
    实现专长积累机制：
    - 公司设计第1个V8引擎：正常难度
    - 公司设计第10个V8引擎：研发成本降低，可靠性提升
    
    布局类型示例：
    - 引擎：V8_TURBO, I4_NA, V6_SUPERCHARGED
    - 底盘：FR_ALUMINUM, FF_STEEL, AWD_CARBON
    """
    __tablename__ = "engineering_familiarity"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # ========== 布局识别 ==========
    layout_type = Column(String(50), nullable=False,
                        comment="布局类型代码，如 'V8_TURBO', 'FR_ALUMINUM'")
    category = Column(String(20), nullable=False,
                     comment="类别：ENGINE/CHASSIS")
    
    # ========== 经验值系统 ==========
    experience_points = Column(Integer, nullable=False, default=0,
                              comment="经验点数（累计）")
    familiarity_level = Column(Integer, nullable=False, default=1,
                             comment="熟悉度等级 1-10")
    
    # ========== 设计统计 ==========
    designs_completed = Column(Integer, nullable=False, default=0,
                              comment="完成的设计数量")
    total_units_produced = Column(Integer, nullable=False, default=0,
                                 comment="累计生产数量（使用此布局的车型）")
    
    # ========== 效果加成（动态计算） ==========
    r_d_cost_reduction = Column(Float, nullable=False, default=0.0,
                               comment="研发成本降低（百分比）0-15%")
    reliability_bonus = Column(Float, nullable=False, default=0.0,
                             comment="可靠性加成（百分比）0-8%")
    development_time_reduction = Column(Float, nullable=False, default=0.0,
                                       comment="研发时间缩短（百分比）0-15%")
    
    # ========== 时间追踪 ==========
    first_design_turn = Column(Integer, nullable=True,
                              comment="首次设计回合")
    last_design_turn = Column(Integer, nullable=True,
                             comment="最后设计回合")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("experience_points >= 0", name="check_positive_experience"),
        CheckConstraint("familiarity_level >= 1 AND familiarity_level <= 10", 
                       name="check_familiarity_level"),
        CheckConstraint("designs_completed >= 0", name="check_positive_designs"),
        CheckConstraint("total_units_produced >= 0", name="check_positive_units"),
        CheckConstraint("r_d_cost_reduction >= 0 AND r_d_cost_reduction <= 0.15", 
                       name="check_cost_reduction"),
        CheckConstraint("reliability_bonus >= 0 AND reliability_bonus <= 0.08", 
                       name="check_reliability_bonus"),
        CheckConstraint("development_time_reduction >= 0 AND development_time_reduction <= 0.15", 
                       name="check_time_reduction"),
        Index("idx_eng_familiarity_company", "company_id"),
        Index("idx_eng_familiarity_layout", "layout_type", "category"),
        Index("idx_eng_familiarity_game", "game_id"),
        # 确保每个公司-布局组合只有一条记录
        Index("idx_eng_familiarity_unique", "company_id", "layout_type", "category", unique=True),
    )
    
    # ========== 关系 ==========
    company = relationship("Company", foreign_keys=[company_id])
    
    def add_experience(self, experience_points: int, current_turn: int) -> None:
        """
        增加经验值
        
        Args:
            experience_points: 经验点数
            current_turn: 当前回合
        """
        if self.first_design_turn is None:
            self.first_design_turn = current_turn
        
        self.last_design_turn = current_turn
        self.experience_points += experience_points
        
        # 重新计算熟悉度等级和加成
        self._update_familiarity_level()
        self._update_bonuses()
    
    def _update_familiarity_level(self) -> None:
        """
        根据经验点数更新熟悉度等级（1-10）
        """
        # 经验值到等级的映射（对数增长）
        import math
        
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
        """
        根据熟悉度等级更新效果加成
        """
        level = self.familiarity_level
        
        # 熟悉度等级效果：
        # 等级1-3：无加成
        # 等级4-6：研发成本-5%，可靠性+2%
        # 等级7-8：研发成本-10%，可靠性+5%，研发时间-10%
        # 等级9-10：研发成本-15%，可靠性+8%，研发时间-15%
        
        if level <= 3:
            self.r_d_cost_reduction = 0.0
            self.reliability_bonus = 0.0
            self.development_time_reduction = 0.0
        elif level <= 6:
            self.r_d_cost_reduction = 0.05
            self.reliability_bonus = 0.02
            self.development_time_reduction = 0.0
        elif level <= 8:
            self.r_d_cost_reduction = 0.10
            self.reliability_bonus = 0.05
            self.development_time_reduction = 0.10
        else:  # 9-10
            self.r_d_cost_reduction = 0.15
            self.reliability_bonus = 0.08
            self.development_time_reduction = 0.15
    
    def get_bonuses(self) -> Dict[str, float]:
        """
        获取所有加成效果
        
        Returns:
            加成字典
        """
        return {
            "r_d_cost_reduction": self.r_d_cost_reduction,
            "reliability_bonus": self.reliability_bonus,
            "development_time_reduction": self.development_time_reduction
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """扩展基类方法"""
        base_dict = super().to_dict()
        base_dict.update({
            "bonuses": self.get_bonuses(),
            "level_description": self._get_level_description()
        })
        return base_dict
    
    def _get_level_description(self) -> str:
        """获取等级描述"""
        descriptions = {
            1: "新手",
            2: "初学者",
            3: "入门",
            4: "熟练",
            5: "精通",
            6: "专家",
            7: "大师",
            8: "传奇",
            9: "宗师",
            10: "神话"
        }
        return descriptions.get(self.familiarity_level, "未知")
    
    def __repr__(self) -> str:
        return (f"<EngineeringFamiliarity(company_id={self.company_id}, "
                f"layout='{self.layout_type}', "
                f"category={self.category}, "
                f"level={self.familiarity_level}, "
                f"exp={self.experience_points}, "
                f"designs={self.designs_completed})>")


__all__ = ["EngineeringFamiliarity"]


