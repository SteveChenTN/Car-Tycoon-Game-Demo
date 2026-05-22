"""
公司高管和人力资源模型
包含高管(Staff/Executive)的个性、技能、忠诚度等
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any, Optional
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class Staff(Base, TimestampMixin, BaseModel):
    """
    高管/员工模型（Executive/Staff）
    
    代表公司的C-suite高管：CEO, CTO, CFO, CMO, COO
    影响公司决策质量和执行效率
    """
    __tablename__ = "staff"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(
        Integer, nullable=True,
        comment="所属公司ID（NULL表示待业/人才市场）"
    )
    
    # ==================== 基础信息 ====================
    first_name = Column(String(50), nullable=False, comment="名")
    last_name = Column(String(50), nullable=False, comment="姓")
    
    age = Column(Integer, nullable=False, comment="年龄")
    nationality = Column(String(10), nullable=False, comment="国籍代码")
    
    # ==================== 职位信息 ====================
    position = Column(
        String(20), nullable=False,
        comment="职位：CEO/ CTO/ CFO/ CMO/ COO/ ENGINEER/ DESIGNER"
    )
    
    hire_turn = Column(Integer, nullable=True, comment="雇佣回合")
    fire_turn = Column(Integer, nullable=True, comment="解雇回合")
    
    # ==================== 核心技能属性（0-100） ====================
    skill_engineering = Column(
        Float, nullable=False, default=50.0,
        comment="工程技能 - 影响研发效率和质量"
    )
    
    skill_finance = Column(
        Float, nullable=False, default=50.0,
        comment="财务技能 - 影响成本控制和融资条件"
    )
    
    skill_marketing = Column(
        Float, nullable=False, default=50.0,
        comment="营销技能 - 影响品牌力和市场份额"
    )
    
    skill_operations = Column(
        Float, nullable=False, default=50.0,
        comment="运营技能 - 影响生产效率和质量控制"
    )
    
    skill_leadership = Column(
        Float, nullable=False, default=50.0,
        comment="领导力 - 影响团队士气和决策质量"
    )
    
    # ==================== 个性特征（0-100） ====================
    trait_aggression = Column(
        Float, nullable=False, default=50.0,
        comment="进攻性 - 高值=激进定价/快速扩张，低值=保守策略"
    )
    
    trait_innovation = Column(
        Float, nullable=False, default=50.0,
        comment="创新性 - 高值=追求前沿技术，低值=稳健可靠"
    )
    
    trait_risk_tolerance = Column(
        Float, nullable=False, default=50.0,
        comment="风险容忍度 - 高值=高杠杆/大赌注，低值=保守债务"
    )
    
    trait_loyalty = Column(
        Float, nullable=False, default=50.0,
        comment="忠诚度基础值 - 影响是否跳槽和泄密风险"
    )
    
    # ==================== 动态状态 ====================
    current_morale = Column(
        Float, nullable=False, default=70.0,
        comment="当前士气 0-100 - 影响执行质量"
    )
    
    current_loyalty = Column(
        Float, nullable=False, default=70.0,
        comment="当前忠诚度 0-100 - 低于30可能跳槽"
    )
    
    fatigue_level = Column(
        Float, nullable=False, default=0.0,
        comment="疲劳度 0-100 - 过高导致效率下降"
    )
    
    # ==================== 薪酬 ====================
    annual_salary = Column(
        Float, nullable=False, default=0.1,
        comment="年薪（百万游戏币）"
    )
    
    market_value = Column(
        Float, nullable=False, default=0.1,
        comment="市场价值/期望薪资（百万游戏币）"
    )
    
    bonus_percentage = Column(
        Float, nullable=False, default=0.0,
        comment="奖金比例 0-1（基于公司业绩）"
    )
    
    # ==================== 职业生涯 ====================
    years_experience = Column(
        Integer, nullable=False, default=0,
        comment="工作年限"
    )
    
    career_success_score = Column(
        Float, nullable=False, default=50.0,
        comment="职业成功度 0-100 - 影响声望和市场价值"
    )
    
    projects_completed = Column(
        Integer, nullable=False, default=0,
        comment="完成的项目数"
    )
    
    projects_failed = Column(
        Integer, nullable=False, default=0,
        comment="失败的项目数"
    )
    
    # ==================== 关系与背景 ====================
    relationships = Column(
        Text, nullable=False, default="{}",
        comment="与其他高管的关系（JSON）- {staff_id: relationship_score}"
    )
    
    education_level = Column(
        String(20), nullable=False, default="BACHELOR",
        comment="教育水平：HIGH_SCHOOL/ BACHELOR/ MASTER/ PHD"
    )
    
    specialization = Column(
        Text, nullable=True,
        comment="专业领域（JSON数组）- 如 ['TURBO_ENGINES', 'LIGHTWEIGHT_MATERIALS']"
    )
    
    # ==================== 状态标记 ====================
    is_available = Column(
        Boolean, nullable=False, default=True,
        comment="是否在人才市场可雇佣"
    )
    
    is_retired = Column(
        Boolean, nullable=False, default=False,
        comment="是否已退休"
    )
    
    retirement_age = Column(
        Integer, nullable=False, default=65,
        comment="计划退休年龄"
    )
    
    # ==================== AI行为（针对AI公司的高管） ====================
    ai_decision_style = Column(
        Text, nullable=True,
        comment="AI决策风格（JSON）- 影响AI公司的行为模式"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("age >= 22 AND age <= 80", name="check_age"),
        CheckConstraint("skill_engineering >= 0 AND skill_engineering <= 100", name="check_skill_eng"),
        CheckConstraint("skill_finance >= 0 AND skill_finance <= 100", name="check_skill_fin"),
        CheckConstraint("skill_marketing >= 0 AND skill_marketing <= 100", name="check_skill_mkt"),
        CheckConstraint("skill_operations >= 0 AND skill_operations <= 100", name="check_skill_ops"),
        CheckConstraint("skill_leadership >= 0 AND skill_leadership <= 100", name="check_skill_lead"),
        CheckConstraint("trait_aggression >= 0 AND trait_aggression <= 100", name="check_trait_agg"),
        CheckConstraint("trait_innovation >= 0 AND trait_innovation <= 100", name="check_trait_inno"),
        CheckConstraint("trait_risk_tolerance >= 0 AND trait_risk_tolerance <= 100", name="check_trait_risk"),
        CheckConstraint("trait_loyalty >= 0 AND trait_loyalty <= 100", name="check_trait_loyalty"),
        CheckConstraint("current_morale >= 0 AND current_morale <= 100", name="check_morale"),
        CheckConstraint("current_loyalty >= 0 AND current_loyalty <= 100", name="check_loyalty"),
        CheckConstraint("fatigue_level >= 0 AND fatigue_level <= 100", name="check_fatigue"),
        CheckConstraint("annual_salary >= 0", name="check_salary"),
        CheckConstraint("market_value >= 0", name="check_market_value"),
        CheckConstraint("bonus_percentage >= 0 AND bonus_percentage <= 1", name="check_bonus"),
        CheckConstraint("years_experience >= 0", name="check_experience"),
        CheckConstraint("career_success_score >= 0 AND career_success_score <= 100", name="check_success"),
        Index("idx_staff_company", "company_id"),
        Index("idx_staff_position", "position"),
        Index("idx_staff_available", "is_available"),
        Index("idx_staff_game", "game_id"),
    )
    
    # ==================== 辅助方法 ====================
    
    @property
    def full_name(self) -> str:
        """获取全名"""
        return f"{self.first_name} {self.last_name}"
    
    def get_primary_skill(self) -> float:
        """根据职位获取主要技能分数"""
        skill_map = {
            "CEO": self.skill_leadership,
            "CTO": self.skill_engineering,
            "CFO": self.skill_finance,
            "CMO": self.skill_marketing,
            "COO": self.skill_operations,
            "ENGINEER": self.skill_engineering,
            "DESIGNER": self.skill_engineering,
        }
        return skill_map.get(self.position, 50.0)
    
    def calculate_effectiveness(self) -> float:
        """
        计算当前工作有效性
        综合考虑技能、士气、疲劳度
        
        Returns:
            有效性倍数 0-2.0
        """
        base_skill = self.get_primary_skill() / 100.0
        morale_factor = self.current_morale / 100.0
        fatigue_penalty = 1.0 - (self.fatigue_level / 200.0)  # 疲劳最多减50%
        
        effectiveness = base_skill * morale_factor * fatigue_penalty
        return max(0.1, min(2.0, effectiveness))
    
    def is_underpaid(self) -> bool:
        """是否薪资低于市场价值"""
        return self.annual_salary < self.market_value * 0.9
    
    def is_overpaid(self) -> bool:
        """是否薪资高于市场价值"""
        return self.annual_salary > self.market_value * 1.2
    
    def calculate_turnover_risk(self) -> float:
        """
        计算跳槽风险 0-1
        
        Returns:
            跳槽概率 0-1
        """
        base_risk = 0.05  # 基础5%年跳槽率
        
        # 忠诚度影响（低忠诚度增加风险）
        loyalty_factor = 1.0 + (50.0 - self.current_loyalty) / 50.0
        
        # 薪酬影响
        salary_factor = 1.0
        if self.is_underpaid():
            salary_factor = 1.5 + (self.market_value - self.annual_salary) / self.market_value
        
        # 士气影响
        morale_factor = 1.0 + (50.0 - self.current_morale) / 100.0
        
        risk = base_risk * loyalty_factor * salary_factor * morale_factor
        return max(0.0, min(1.0, risk))
    
    def update_morale(self, company_performance: float, salary_satisfied: bool) -> None:
        """
        更新士气
        
        Args:
            company_performance: 公司业绩评分 0-100
            salary_satisfied: 薪资是否满意
        """
        # 基于公司业绩
        target_morale = company_performance * 0.7
        
        # 薪资满意度影响
        if salary_satisfied:
            target_morale += 15
        elif self.is_underpaid():
            target_morale -= 20
        
        # 疲劳影响
        target_morale -= self.fatigue_level * 0.3
        
        # 平滑变化（每回合只变化一部分）
        self.current_morale += (target_morale - self.current_morale) * 0.3
        self.current_morale = max(0.0, min(100.0, self.current_morale))
    
    def update_market_value(self) -> None:
        """根据技能、经验和成就更新市场价值"""
        base_value = 0.05  # 基础50K
        
        # 主要技能影响
        skill_value = self.get_primary_skill() / 100.0 * 0.3
        
        # 经验影响
        experience_value = min(self.years_experience / 20.0, 1.0) * 0.2
        
        # 职业成功度影响
        success_value = self.career_success_score / 100.0 * 0.4
        
        # 职位基础薪资
        position_multiplier = {
            "CEO": 5.0,
            "CTO": 3.0,
            "CFO": 3.0,
            "CMO": 2.5,
            "COO": 2.5,
            "ENGINEER": 1.0,
            "DESIGNER": 1.0,
        }.get(self.position, 1.0)
        
        self.market_value = (base_value + skill_value + experience_value + success_value) * position_multiplier
    
    def get_relationships(self) -> Dict[int, float]:
        """获取与其他高管的关系"""
        try:
            return json.loads(self.relationships)
        except:
            return {}
    
    def set_relationships(self, relationships: Dict[int, float]) -> None:
        """设置与其他高管的关系"""
        self.relationships = json.dumps(relationships)
    
    def get_specializations(self) -> list[str]:
        """获取专业领域列表"""
        if not self.specialization:
            return []
        try:
            return json.loads(self.specialization)
        except:
            return []
    
    def set_specializations(self, specs: list[str]) -> None:
        """设置专业领域列表"""
        self.specialization = json.dumps(specs)
    
    @validates("position")
    def validate_position(self, key: str, value: str) -> str:
        """验证职位"""
        valid_positions = ["CEO", "CTO", "CFO", "CMO", "COO", "ENGINEER", "DESIGNER"]
        if value.upper() not in valid_positions:
            raise ValueError(f"Invalid position: {value}. Must be one of {valid_positions}")
        return value.upper()
    
    @validates("education_level")
    def validate_education(self, key: str, value: str) -> str:
        """验证教育水平"""
        valid_levels = ["HIGH_SCHOOL", "BACHELOR", "MASTER", "PHD"]
        if value.upper() not in valid_levels:
            raise ValueError(f"Invalid education level: {value}. Must be one of {valid_levels}")
        return value.upper()
    
    def __repr__(self) -> str:
        return (f"<Staff(id={self.id}, "
                f"name='{self.full_name}', "
                f"position={self.position}, "
                f"company_id={self.company_id}, "
                f"skill={self.get_primary_skill():.0f}, "
                f"morale={self.current_morale:.0f})>")


__all__ = ["Staff"]


