"""
公司实体模型
包含财务、信用评级、声望等核心属性
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


DEFAULT_AI_PERSONALITY_TRAITS: Dict[str, int] = {
    "aggression": 50,
    "innovation": 50,
    "risk_tolerance": 50,
    "loyalty": 50,
    "foresight": 50,
}


class Company(Base, TimestampMixin, BaseModel):
    """
    汽车公司主模型
    管理财务、信用、声望、技术水平等核心属性
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 基础信息 ====================
    name = Column(String(100), nullable=False, comment="公司名称")
    short_code = Column(String(10), nullable=False, comment="公司简称代码")
    
    is_player = Column(Boolean, nullable=False, default=False, comment="是否为玩家公司")
    is_ai = Column(Boolean, nullable=False, default=True, comment="是否为AI公司")
    
    founded_year = Column(Integer, nullable=False, comment="成立年份")
    founded_turn = Column(Integer, nullable=False, comment="成立回合")
    
    headquarters_region = Column(
        String(10), nullable=False,
        comment="总部所在地区代码 (NAM/EUR/ASI/LAM/MEA)"
    )
    
    # ==================== 财务状况 ====================
    cash = Column(
        Float, nullable=False, default=100.0,
        comment="现金储备（百万游戏币）"
    )
    
    total_debt = Column(
        Float, nullable=False, default=0.0,
        comment="总债务（百万游戏币）"
    )
    
    quarterly_revenue = Column(
        Float, nullable=False, default=0.0,
        comment="季度营收（百万游戏币）"
    )
    
    quarterly_profit = Column(
        Float, nullable=False, default=0.0,
        comment="季度利润（百万游戏币）"
    )
    
    total_assets = Column(
        Float, nullable=False, default=100.0,
        comment="总资产（百万游戏币）"
    )
    
    # ==================== 月度累计指标（每回合重置）====================
    monthly_revenue = Column(Float, nullable=False, default=0.0, comment="月度营收")
    monthly_cost_manufacturing = Column(Float, nullable=False, default=0.0, comment="月度制造成本")
    monthly_cost_materials = Column(Float, nullable=False, default=0.0, comment="月度材料成本")
    monthly_cost_labor = Column(Float, nullable=False, default=0.0, comment="月度人工成本")
    monthly_cost_rd = Column(Float, nullable=False, default=0.0, comment="月度研发费用")
    monthly_cost_marketing = Column(Float, nullable=False, default=0.0, comment="月度营销费用")
    monthly_cost_admin = Column(Float, nullable=False, default=0.0, comment="月度管理费用")
    monthly_interest = Column(Float, nullable=False, default=0.0, comment="月度利息支出")
    monthly_profit = Column(Float, nullable=False, default=0.0, comment="月度净利润")
    monthly_units_sold = Column(Integer, nullable=False, default=0, comment="月度销量")
    monthly_units_produced = Column(Integer, nullable=False, default=0, comment="月度产量")
    
    # ==================== 信用评级系统 ====================
    credit_rating = Column(
        String(5), nullable=False, default="BBB",
        comment="信用评级: AAA/AA/A/BBB/BB/B/CCC/CC/C/D"
    )
    
    credit_score = Column(
        Float, nullable=False, default=50.0,
        comment="信用分数 0-100（内部计算用）"
    )
    
    bankruptcy_risk = Column(
        Float, nullable=False, default=0.0,
        comment="破产风险 0-1"
    )
    
    # ==================== 声望与品牌力 ====================
    prestige_score = Column(
        Float, nullable=False, default=10.0,
        comment="全局声望分数（0-100+）- 影响定价权和市场准入"
    )
    
    brand_power = Column(
        Float, nullable=False, default=0.5,
        comment="品牌力 0-1 - 影响消费者选择"
    )
    
    reputation_quality = Column(
        Float, nullable=False, default=50.0,
        comment="质量声誉 0-100 - 基于历史产品可靠性"
    )
    
    reputation_innovation = Column(
        Float, nullable=False, default=50.0,
        comment="创新声誉 0-100 - 基于技术突破数量"
    )
    
    # ==================== 技术能力 ====================
    tech_level = Column(
        Integer, nullable=False, default=1,
        comment="技术等级 1-10"
    )
    
    rd_efficiency = Column(
        Float, nullable=False, default=1.0,
        comment="研发效率倍数（受人才和设施影响）"
    )
    
    production_efficiency = Column(
        Float, nullable=False, default=0.8,
        comment="生产效率 0-1"
    )
    
    # ==================== 市场表现 ====================
    market_share_global = Column(
        Float, nullable=False, default=0.0,
        comment="全球市场份额 0-1"
    )
    
    total_vehicles_sold = Column(
        Integer, nullable=False, default=0,
        comment="历史累计销售量"
    )
    
    active_car_models = Column(
        Integer, nullable=False, default=0,
        comment="当前在售车型数量"
    )
    
    # ==================== 人力资源 ====================
    total_employees = Column(
        Integer, nullable=False, default=100,
        comment="员工总数"
    )
    
    employee_morale = Column(
        Float, nullable=False, default=0.7,
        comment="员工士气 0-1"
    )
    
    # ==================== AI策略（仅AI公司） ====================
    ai_strategy = Column(
        String(50), nullable=True,
        comment="AI战略类型: AGGRESSIVE/CONSERVATIVE/BALANCED/INNOVATION/MASS_MARKET"
    )
    
    ai_personality_traits = Column(
        Text, nullable=True,
        comment="AI个性特征（JSON格式）- 风险偏好、研发倾向等"
    )
    
    # ==================== 特殊设施解锁（声望奖励） ====================
    unlocked_facilities = Column(
        Text, nullable=False, default="[]",
        comment="已解锁特殊设施列表（JSON）- 如F1_TEAM, WIND_TUNNEL, PROVING_GROUND"
    )
    
    # ==================== 公司状态 ====================
    is_bankrupt = Column(
        Boolean, nullable=False, default=False,
        comment="是否破产"
    )
    
    bankruptcy_turn = Column(
        Integer, nullable=True,
        comment="破产回合（若已破产）"
    )
    
    is_acquired = Column(
        Boolean, nullable=False, default=False,
        comment="是否被收购"
    )
    
    acquired_by_company_id = Column(
        Integer, nullable=True,
        comment="收购方公司ID"
    )
    
    # ==================== 关系 ====================
    # factories = relationship("Factory", back_populates="company")
    # engines = relationship("Engine", back_populates="company")
    # chassis = relationship("Chassis", back_populates="company")
    # cars = relationship("CarTrim", back_populates="company")
    # loans = relationship("Loan", back_populates="company")
    supplier_relations = relationship("CompanySupplierRelation", back_populates="company")
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("cash >= 0 OR is_bankrupt = 1", name="check_cash_bankruptcy"),
        CheckConstraint("total_debt >= 0", name="check_debt"),
        CheckConstraint("credit_score >= 0 AND credit_score <= 100", name="check_credit_score"),
        CheckConstraint("prestige_score >= 0", name="check_prestige"),
        CheckConstraint("brand_power >= 0 AND brand_power <= 1", name="check_brand_power"),
        CheckConstraint("reputation_quality >= 0 AND reputation_quality <= 100", name="check_rep_quality"),
        CheckConstraint("reputation_innovation >= 0 AND reputation_innovation <= 100", name="check_rep_innovation"),
        CheckConstraint("tech_level >= 1 AND tech_level <= 10", name="check_tech_level"),
        CheckConstraint("rd_efficiency > 0", name="check_rd_efficiency"),
        CheckConstraint("production_efficiency >= 0 AND production_efficiency <= 1", name="check_prod_efficiency"),
        CheckConstraint("market_share_global >= 0 AND market_share_global <= 1", name="check_market_share"),
        CheckConstraint("total_employees >= 0", name="check_employees"),
        CheckConstraint("employee_morale >= 0 AND employee_morale <= 1", name="check_morale"),
        CheckConstraint("bankruptcy_risk >= 0 AND bankruptcy_risk <= 1", name="check_bankruptcy_risk"),
        Index("idx_company_game", "game_id"),
        Index("idx_company_player", "is_player"),
        Index("idx_company_bankrupt", "is_bankrupt"),
        Index("idx_company_hq", "headquarters_region"),
    )
    
    @validates("credit_rating")
    def validate_credit_rating(self, key: str, value: str) -> str:
        """验证信用评级"""
        valid_ratings = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
        if value not in valid_ratings:
            raise ValueError(f"Invalid credit rating: {value}. Must be one of {valid_ratings}")
        return value
    
    def get_unlocked_facilities(self) -> list[str]:
        """获取已解锁设施列表"""
        try:
            return json.loads(self.unlocked_facilities)
        except:
            return []
    
    def set_unlocked_facilities(self, facilities: list[str]) -> None:
        """设置已解锁设施列表"""
        self.unlocked_facilities = json.dumps(facilities)
    
    def unlock_facility(self, facility_name: str) -> bool:
        """
        解锁特殊设施
        
        Args:
            facility_name: 设施名称
        
        Returns:
            是否成功解锁（已解锁则返回False）
        """
        facilities = self.get_unlocked_facilities()
        if facility_name not in facilities:
            facilities.append(facility_name)
            self.set_unlocked_facilities(facilities)
            return True
        return False
    
    def get_ai_personality(self) -> Dict[str, Any]:
        """获取AI个性特征"""
        traits = DEFAULT_AI_PERSONALITY_TRAITS.copy()
        if not self.ai_personality_traits:
            return traits
        try:
            stored_traits = json.loads(self.ai_personality_traits)
            if isinstance(stored_traits, dict):
                traits.update(stored_traits)
        except:
            pass
        return traits
    
    def set_ai_personality(self, traits: Dict[str, Any]) -> None:
        """设置AI个性特征"""
        normalized_traits = DEFAULT_AI_PERSONALITY_TRAITS.copy()
        normalized_traits.update(traits or {})
        self.ai_personality_traits = json.dumps(normalized_traits)
    
    def calculate_debt_ratio(self) -> float:
        """计算负债比率"""
        if self.total_assets <= 0:
            return 999.0  # 资不抵债
        return self.total_debt / self.total_assets
    
    def calculate_interest_coverage(self) -> float:
        """
        计算利息保障倍数
        需要与Loan模型配合使用（暂时返回占位值）
        """
        # TODO: 实际实现需要查询所有贷款的利息总和
        return 0.0
    
    def update_credit_score(self) -> None:
        """
        更新信用分数和评级
        基于财务健康度、盈利能力、债务水平等因素
        """
        score = 50.0  # 基础分
        
        # 因素1: 负债比率（权重30%）
        debt_ratio = self.calculate_debt_ratio()
        if debt_ratio < 0.3:
            score += 15
        elif debt_ratio < 0.5:
            score += 10
        elif debt_ratio < 0.7:
            score += 5
        elif debt_ratio > 1.0:
            score -= 20
        else:
            score -= 10
        
        # 因素2: 盈利能力（权重25%）
        if self.quarterly_profit > 0:
            profit_margin = self.quarterly_profit / max(self.quarterly_revenue, 1.0)
            if profit_margin > 0.15:
                score += 12
            elif profit_margin > 0.08:
                score += 8
            elif profit_margin > 0.03:
                score += 4
        else:
            score -= 15  # 亏损
        
        # 因素3: 现金储备（权重20%）
        if self.cash > 100:
            score += 10
        elif self.cash > 50:
            score += 6
        elif self.cash > 20:
            score += 3
        elif self.cash < 10:
            score -= 10
        
        # 因素4: 市场表现（权重15%）
        if self.market_share_global > 0.1:
            score += 8
        elif self.market_share_global > 0.05:
            score += 5
        elif self.market_share_global > 0.01:
            score += 2
        
        # 因素5: 声望（权重10%）
        if self.prestige_score > 70:
            score += 5
        elif self.prestige_score > 40:
            score += 2
        
        # 限制范围
        self.credit_score = max(0.0, min(100.0, score))
        
        # 更新评级
        if self.credit_score >= 90:
            self.credit_rating = "AAA"
        elif self.credit_score >= 80:
            self.credit_rating = "AA"
        elif self.credit_score >= 70:
            self.credit_rating = "A"
        elif self.credit_score >= 60:
            self.credit_rating = "BBB"
        elif self.credit_score >= 50:
            self.credit_rating = "BB"
        elif self.credit_score >= 40:
            self.credit_rating = "B"
        elif self.credit_score >= 30:
            self.credit_rating = "CCC"
        elif self.credit_score >= 20:
            self.credit_rating = "CC"
        elif self.credit_score >= 10:
            self.credit_rating = "C"
        else:
            self.credit_rating = "D"
        
        # 更新破产风险
        self.bankruptcy_risk = max(0.0, min(1.0, (100 - self.credit_score) / 100))
    
    def __repr__(self) -> str:
        return (f"<Company(id={self.id}, name='{self.name}', "
                f"cash={self.cash:,.0f}, credit={self.credit_rating}, "
                f"prestige={self.prestige_score:.1f})>")

    def get_monthly_total_costs(self) -> float:
        """Return this period's total P&L costs in game currency."""
        return (
            self.monthly_cost_manufacturing +
            self.monthly_cost_materials +
            self.monthly_cost_labor +
            self.monthly_cost_rd +
            self.monthly_cost_marketing +
            self.monthly_cost_admin +
            self.monthly_interest
        )

    def refresh_monthly_profit(self) -> None:
        """Keep monthly profit derived from the monthly revenue/cost ledger."""
        self.monthly_profit = self.monthly_revenue - self.get_monthly_total_costs()

    def record_revenue(self, amount: float, units_sold: int = 0) -> None:
        """Record cash revenue in absolute game currency."""
        amount = max(0.0, float(amount or 0.0))
        units_sold = max(0, int(units_sold or 0))

        self.cash += amount
        self.monthly_revenue += amount
        self.quarterly_revenue += amount
        self.quarterly_profit += amount
        self.monthly_units_sold += units_sold
        self.total_vehicles_sold += units_sold
        self.refresh_monthly_profit()

    def record_cost(self, category: str, amount: float, affect_cash: bool = True) -> None:
        """Record a monthly cost in absolute game currency."""
        amount = max(0.0, float(amount or 0.0))
        if amount == 0.0:
            return

        field_by_category = {
            "manufacturing": "monthly_cost_manufacturing",
            "materials": "monthly_cost_materials",
            "labor": "monthly_cost_labor",
            "rd": "monthly_cost_rd",
            "marketing": "monthly_cost_marketing",
            "admin": "monthly_cost_admin",
            "interest": "monthly_interest",
        }
        field_name = field_by_category.get(category)
        if not field_name:
            raise ValueError(f"Unknown cost category: {category}")

        setattr(self, field_name, getattr(self, field_name) + amount)
        self.quarterly_profit -= amount

        if affect_cash:
            self.cash -= amount
            if self.cash < 0:
                self.is_bankrupt = True

        self.refresh_monthly_profit()
    
    def reset_monthly_stats(self) -> None:
        """
        重置月度累计统计
        每回合开始时调用
        """
        self.monthly_revenue = 0.0
        self.monthly_cost_manufacturing = 0.0
        self.monthly_cost_materials = 0.0
        self.monthly_cost_labor = 0.0
        self.monthly_cost_rd = 0.0
        self.monthly_cost_marketing = 0.0
        self.monthly_cost_admin = 0.0
        self.monthly_interest = 0.0
        self.monthly_profit = 0.0
        self.monthly_units_sold = 0
        self.monthly_units_produced = 0


__all__ = ["Company"]
