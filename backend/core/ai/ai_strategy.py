"""
AI竞争对手决策系统
实现基于个性矩阵的AI CEO决策逻辑
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from enum import Enum
import random
import math

from backend.models.market import (
    MarketingCampaign, DistributionNetwork, BrandPerception,
    MarketingFocus, ConsumerSegment, DistributionType
)
from backend.models.production import Factory, FactoryType
from backend.models.engineering import Engine, Chassis, CarTrim
from backend.models.region import Region
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ========== AI人格特征 ==========

@dataclass
class CEOPersonality:
    """
    CEO人格矩阵
    每个特征0-100分
    """
    aggression: int      # 侵略性：价格战、快速扩张
    innovation: int      # 创新性：前沿技术、冒险
    risk_tolerance: int  # 风险承受：杠杆、大赌注
    loyalty: int         # 忠诚度：团队稳定性
    
    def __post_init__(self):
        """验证范围"""
        for attr in ['aggression', 'innovation', 'risk_tolerance', 'loyalty']:
            value = getattr(self, attr)
            if not 0 <= value <= 100:
                raise ValueError(f"{attr}必须在0-100之间，当前值: {value}")


@dataclass
class CompanySituation:
    """公司当前状况评估"""
    company_id: int
    cash_balance: float
    monthly_burn_rate: float
    cash_runway_months: float
    
    market_share_trend: float  # 近期市场份额变化（-1到+1）
    profit_margin: float
    brand_health: float        # 品牌健康度（0-100）
    
    production_utilization: float  # 产能利用率（0-1）
    competitor_threats: List[Dict]  # 竞争威胁列表
    market_opportunities: List[Dict]  # 市场机会列表


@dataclass
class AIDecision:
    """AI决策"""
    decision_type: str  # MARKETING/PRODUCTION/RD/PRICING/EXPANSION
    action: str         # 具体行动
    parameters: Dict    # 行动参数
    reasoning: str      # 决策理由（用于日志）
    priority: int       # 优先级（1-10）


# ========== 主AI决策类 ==========

class AI_CEO:
    """
    AI CEO决策引擎
    根据个性和公司状况做出战略决策
    """
    
    def __init__(
        self,
        db: Session,
        company_id: int,
        personality: CEOPersonality
    ):
        self.db = db
        self.company_id = company_id
        self.personality = personality
        self.logger = get_logger(f"AI_CEO_{company_id}")
    
    # ========== 主决策循环 ==========
    
    def make_turn_decisions(
        self,
        game_id: int,
        current_turn: int
    ) -> List[AIDecision]:
        """
        每回合决策入口
        
        Args:
            game_id: 游戏ID
            current_turn: 当前回合
        
        Returns:
            决策列表
        """
        self.logger.info(f"AI公司 {self.company_id} 开始第 {current_turn} 回合决策")
        
        # 阶段1：评估当前状况
        situation = self._assess_situation(game_id, current_turn)
        
        # 阶段2：生成决策
        decisions = []
        
        # 决策优先级（按顺序）
        # 1. 生存决策（现金危机）
        if situation.cash_runway_months < 6:
            decisions.extend(self._make_survival_decisions(situation))
        
        # 2. 市场营销决策
        marketing_decisions = self._make_marketing_decisions(situation, current_turn, game_id)
        decisions.extend(marketing_decisions)
        
        # 3. 生产与扩张决策
        production_decisions = self._make_production_decisions(situation, game_id)
        decisions.extend(production_decisions)
        
        # 4. 研发决策
        rd_decisions = self._make_rd_decisions(situation, game_id)
        decisions.extend(rd_decisions)
        
        # 5. 定价策略决策
        pricing_decisions = self._make_pricing_decisions(situation)
        decisions.extend(pricing_decisions)
        
        # 记录决策
        for decision in decisions:
            self.logger.info(
                f"  决策: {decision.decision_type} - {decision.action} | "
                f"理由: {decision.reasoning}"
            )
        
        return decisions
    
    # ========== 阶段1：状况评估 ==========
    
    def _assess_situation(self, game_id: int, current_turn: int) -> CompanySituation:
        """
        评估公司当前状况
        
        Returns:
            状况评估结果
        """
        # TODO: 这里需要Company模型，当前简化处理
        # 假设有基础数据
        
        # 简化版本：使用模拟数据
        situation = CompanySituation(
            company_id=self.company_id,
            cash_balance=50000000.0,  # 5000万
            monthly_burn_rate=1000000.0,  # 100万/月
            cash_runway_months=50.0,
            market_share_trend=random.uniform(-0.1, 0.1),
            profit_margin=0.10,
            brand_health=random.uniform(40.0, 80.0),
            production_utilization=random.uniform(0.5, 0.95),
            competitor_threats=[],
            market_opportunities=[]
        )
        
        # 计算产能利用率（真实数据）
        factories = self.db.query(Factory).filter(
            Factory.company_id == self.company_id,
            Factory.game_id == game_id,
            Factory.is_operational == True
        ).all()
        
        if factories:
            total_capacity = sum(f.get_effective_capacity() for f in factories)
            # TODO: 计算实际使用量
            # 这里简化为随机
            situation.production_utilization = random.uniform(0.6, 0.95)
        
        return situation
    
    # ========== 阶段2：决策生成 ==========
    
    def _make_survival_decisions(self, situation: CompanySituation) -> List[AIDecision]:
        """
        生存模式决策（现金危机）
        """
        decisions = []
        
        # 削减成本
        decisions.append(AIDecision(
            decision_type="COST_CUT",
            action="REDUCE_MARKETING",
            parameters={"reduction_ratio": 0.5},
            reasoning="现金跑道不足6个月，削减营销预算50%",
            priority=10
        ))
        
        # 降价促销
        if self.personality.aggression > 50:
            decisions.append(AIDecision(
                decision_type="PRICING",
                action="EMERGENCY_DISCOUNT",
                parameters={"discount_percent": 15.0},
                reasoning="现金危机，紧急降价促销回笼资金",
                priority=9
            ))
        
        return decisions
    
    def _make_marketing_decisions(
        self,
        situation: CompanySituation,
        current_turn: int,
        game_id: int
    ) -> List[AIDecision]:
        """
        市场营销决策
        """
        decisions = []
        
        # 检查是否需要启动营销活动
        # 条件1：市场份额下降
        if situation.market_share_trend < -0.05:
            if situation.cash_balance > 5000000:  # 有足够现金
                # 获取所有地区
                regions = self.db.query(Region).filter(
                    Region.game_id == game_id
                ).all()
                
                for region in regions:
                    # 检查是否已有活跃营销活动
                    existing_campaigns = self.db.query(MarketingCampaign).filter(
                        MarketingCampaign.company_id == self.company_id,
                        MarketingCampaign.region_id == region.id,
                        MarketingCampaign.is_active == True
                    ).count()
                    
                    if existing_campaigns == 0:
                        # 决定目标细分
                        target = self._choose_target_segment()
                        
                        # 决定营销焦点
                        focus = self._choose_marketing_focus()
                        
                        # 计算预算
                        budget = self._calculate_marketing_budget(situation)
                        
                        decisions.append(AIDecision(
                            decision_type="MARKETING",
                            action="LAUNCH_CAMPAIGN",
                            parameters={
                                "region_id": region.id,
                                "target_bucket": target,
                                "focus": focus,
                                "budget": budget,
                                "duration_turns": 3  # 3个月活动
                            },
                            reasoning=f"市场份额下降{abs(situation.market_share_trend)*100:.1f}%，启动营销反击",
                            priority=7
                        ))
        
        # 条件2：品牌健康度低
        elif situation.brand_health < 50:
            if situation.cash_balance > 3000000:
                decisions.append(AIDecision(
                    decision_type="MARKETING",
                    action="BRAND_REPAIR_CAMPAIGN",
                    parameters={
                        "focus": MarketingFocus.RELIABILITY.value,
                        "budget": 2000000
                    },
                    reasoning=f"品牌健康度仅{situation.brand_health:.1f}，启动品牌修复",
                    priority=8
                ))
        
        return decisions
    
    def _make_production_decisions(
        self,
        situation: CompanySituation,
        game_id: int
    ) -> List[AIDecision]:
        """
        生产与扩张决策
        """
        decisions = []
        
        # 产能利用率高 + 有现金 = 扩张
        if situation.production_utilization > 0.90:
            # 高风险承受度的CEO更愿意扩张
            expansion_threshold = 100 - self.personality.risk_tolerance
            
            if situation.cash_runway_months > expansion_threshold / 2.0:
                # 决定扩张地区
                best_region = self._find_best_expansion_region(game_id)
                
                if best_region:
                    decisions.append(AIDecision(
                        decision_type="EXPANSION",
                        action="BUILD_FACTORY",
                        parameters={
                            "region_id": best_region.id,
                            "factory_type": FactoryType.ASSEMBLY.value,
                            "capacity": 50000
                        },
                        reasoning=f"产能利用率{situation.production_utilization*100:.1f}%，在{best_region.name}建厂",
                        priority=6
                    ))
        
        # 产能闲置 + 侵略性高 = 价格战
        elif situation.production_utilization < 0.60 and self.personality.aggression > 70:
            decisions.append(AIDecision(
                decision_type="PRICING",
                action="AGGRESSIVE_PRICING",
                parameters={"discount_percent": 10.0},
                reasoning=f"产能闲置{(1-situation.production_utilization)*100:.1f}%，启动价格战",
                priority=7
            ))
        
        return decisions
    
    def _make_rd_decisions(
        self,
        situation: CompanySituation,
        game_id: int
    ) -> List[AIDecision]:
        """
        研发决策
        """
        decisions = []
        
        # 高创新性CEO更愿意投资R&D
        if self.personality.innovation > 60:
            # 检查是否有正在研发的项目
            # TODO: 需要RDProject模型
            
            # 简化：如果现金充足且没有最新技术引擎
            if situation.cash_balance > 20000000:
                # 随机决定是否启动新引擎研发
                if random.random() < self.personality.innovation / 200.0:
                    decisions.append(AIDecision(
                        decision_type="RD",
                        action="START_ENGINE_PROJECT",
                        parameters={
                            "tech_level": random.randint(5, 8),
                            "budget": 10000000
                        },
                        reasoning=f"创新性{self.personality.innovation}，启动新引擎研发",
                        priority=5
                    ))
        
        return decisions
    
    def _make_pricing_decisions(
        self,
        situation: CompanySituation
    ) -> List[AIDecision]:
        """
        定价策略决策
        """
        decisions = []
        
        # 根据市场份额和侵略性调整价格
        if situation.market_share_trend < 0 and self.personality.aggression > 60:
            # 侵略性反击：降价
            discount = min(15.0, self.personality.aggression / 100.0 * 15.0)
            
            decisions.append(AIDecision(
                decision_type="PRICING",
                action="INCREASE_DISCOUNTS",
                parameters={"discount_percent": discount},
                reasoning=f"市场份额下降，侵略性CEO发起降价反击",
                priority=7
            ))
        
        elif situation.market_share_trend > 0.05 and situation.profit_margin < 0.15:
            # 市场份额上升，提价增利
            decisions.append(AIDecision(
                decision_type="PRICING",
                action="INCREASE_PRICES",
                parameters={"increase_percent": 5.0},
                reasoning="市场份额上升，适度提价增加利润率",
                priority=4
            ))
        
        return decisions
    
    # ========== 辅助方法 ==========
    
    def _choose_target_segment(self) -> str:
        """根据个性选择目标市场细分"""
        if self.personality.innovation > 70:
            # 创新型CEO喜欢年轻市场
            return ConsumerSegment.YOUTH.value
        elif self.personality.risk_tolerance < 30:
            # 保守型CEO喜欢家庭市场
            return ConsumerSegment.FAMILY.value
        elif self.personality.aggression > 70:
            # 侵略型CEO喜欢运动市场
            return ConsumerSegment.SPORTS.value
        else:
            return ConsumerSegment.PRACTICAL.value
    
    def _choose_marketing_focus(self) -> str:
        """根据个性选择营销焦点"""
        if self.personality.aggression > 70:
            return MarketingFocus.SALES_PUSH.value
        elif self.personality.innovation > 70:
            return MarketingFocus.MOTORSPORT.value
        else:
            return MarketingFocus.BRAND_AWARENESS.value
    
    def _calculate_marketing_budget(self, situation: CompanySituation) -> float:
        """计算营销预算"""
        # 基于现金余额的比例
        base_budget = situation.cash_balance * 0.02  # 2%
        
        # 侵略性调整
        aggression_multiplier = 0.5 + (self.personality.aggression / 100.0)
        
        budget = base_budget * aggression_multiplier
        
        return min(budget, 5000000)  # 最高500万
    
    def _find_best_expansion_region(self, game_id: int) -> Optional[Region]:
        """
        寻找最佳扩张地区
        
        Returns:
            最佳地区或None
        """
        regions = self.db.query(Region).filter(
            Region.game_id == game_id
        ).all()
        
        # 检查哪些地区还没有工厂
        regions_without_factory = []
        
        for region in regions:
            factory_count = self.db.query(Factory).filter(
                Factory.company_id == self.company_id,
                Factory.region_id == region.id,
                Factory.game_id == game_id
            ).count()
            
            if factory_count == 0:
                regions_without_factory.append(region)
        
        if not regions_without_factory:
            return None
        
        # 选择最大市场
        best_region = max(
            regions_without_factory,
            key=lambda r: r.annual_sales_potential
        )
        
        return best_region
    
    def _identify_competitor_threats(
        self,
        game_id: int
    ) -> List[Dict]:
        """
        识别竞争对手威胁
        
        Returns:
            威胁列表
        """
        # TODO: 需要完整的Company模型和销售数据
        # 这里返回空列表作为占位
        return []
    
    def _identify_market_opportunities(
        self,
        game_id: int
    ) -> List[Dict]:
        """
        识别市场机会
        
        Returns:
            机会列表
        """
        # TODO: 分析未被满足的需求、空白市场等
        return []


# ========== AI决策执行器 ==========

class AIDecisionExecutor:
    """
    AI决策执行器
    将决策转换为实际的数据库操作
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger("AIDecisionExecutor")
    
    def execute_decision(
        self,
        decision: AIDecision,
        company_id: int,
        game_id: int,
        current_turn: int
    ) -> bool:
        """
        执行单个决策
        
        Returns:
            是否执行成功
        """
        try:
            if decision.decision_type == "MARKETING":
                return self._execute_marketing_decision(
                    decision, company_id, game_id, current_turn
                )
            elif decision.decision_type == "EXPANSION":
                return self._execute_expansion_decision(
                    decision, company_id, game_id, current_turn
                )
            elif decision.decision_type == "PRICING":
                return self._execute_pricing_decision(
                    decision, company_id, game_id
                )
            elif decision.decision_type == "RD":
                return self._execute_rd_decision(
                    decision, company_id, game_id, current_turn
                )
            elif decision.decision_type == "COST_CUT":
                return self._execute_cost_cut_decision(
                    decision, company_id, game_id
                )
            else:
                self.logger.warning(f"未知决策类型: {decision.decision_type}")
                return False
        
        except Exception as e:
            self.logger.error(f"执行决策失败: {decision.decision_type} - {str(e)}")
            return False
    
    def _execute_marketing_decision(
        self,
        decision: AIDecision,
        company_id: int,
        game_id: int,
        current_turn: int
    ) -> bool:
        """执行营销决策"""
        if decision.action == "LAUNCH_CAMPAIGN":
            params = decision.parameters
            
            campaign = MarketingCampaign(
                game_id=game_id,
                company_id=company_id,
                region_id=params["region_id"],
                name=f"AI Campaign {current_turn}",
                target_bucket=params["target_bucket"],
                focus=params["focus"],
                budget=params["budget"],
                start_turn=current_turn,
                end_turn=current_turn + params.get("duration_turns", 3),
                is_active=True
            )
            
            self.db.add(campaign)
            self.db.commit()
            
            self.logger.info(
                f"AI公司 {company_id} 启动营销活动: "
                f"地区{params['region_id']}, 预算{params['budget']:,.0f}"
            )
            return True
        
        return False
    
    def _execute_expansion_decision(
        self,
        decision: AIDecision,
        company_id: int,
        game_id: int,
        current_turn: int
    ) -> bool:
        """执行扩张决策"""
        # TODO: 实现工厂建设逻辑
        self.logger.info(f"AI公司 {company_id} 计划扩张（待实现）")
        return False
    
    def _execute_pricing_decision(
        self,
        decision: AIDecision,
        company_id: int,
        game_id: int
    ) -> bool:
        """执行定价决策"""
        # TODO: 实现价格调整逻辑
        self.logger.info(f"AI公司 {company_id} 调整价格（待实现）")
        return False
    
    def _execute_rd_decision(
        self,
        decision: AIDecision,
        company_id: int,
        game_id: int,
        current_turn: int
    ) -> bool:
        """执行研发决策"""
        # TODO: 实现R&D项目启动逻辑
        self.logger.info(f"AI公司 {company_id} 启动研发项目（待实现）")
        return False
    
    def _execute_cost_cut_decision(
        self,
        decision: AIDecision,
        company_id: int,
        game_id: int
    ) -> bool:
        """执行成本削减决策"""
        # TODO: 实现成本削减逻辑
        self.logger.info(f"AI公司 {company_id} 削减成本（待实现）")
        return False


# ========== 便捷函数 ==========

def create_random_personality() -> CEOPersonality:
    """创建随机CEO人格"""
    return CEOPersonality(
        aggression=random.randint(20, 80),
        innovation=random.randint(20, 80),
        risk_tolerance=random.randint(20, 80),
        loyalty=random.randint(20, 80)
    )


def run_ai_turn_for_company(
    db: Session,
    company_id: int,
    game_id: int,
    current_turn: int,
    personality: CEOPersonality
) -> List[AIDecision]:
    """
    便捷函数：运行单个AI公司的回合决策
    """
    ai_ceo = AI_CEO(db, company_id, personality)
    decisions = ai_ceo.make_turn_decisions(game_id, current_turn)
    
    # 执行决策
    executor = AIDecisionExecutor(db)
    for decision in decisions:
        executor.execute_decision(decision, company_id, game_id, current_turn)
    
    return decisions


__all__ = [
    "AI_CEO",
    "CEOPersonality",
    "CompanySituation",
    "AIDecision",
    "AIDecisionExecutor",
    "create_random_personality",
    "run_ai_turn_for_company"
]


