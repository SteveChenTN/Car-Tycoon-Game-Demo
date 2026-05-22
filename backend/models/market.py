"""
市场相关数据模型
包含分销网络、营销活动、品牌认知、消费者细分和情报报告
"""
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, 
    ForeignKey, Text, CheckConstraint, Index, JSON
)
from sqlalchemy.orm import relationship, validates
from typing import Optional, Dict, Any, List
import json
from datetime import datetime
from enum import Enum

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


# ========== 枚举定义 ==========

class DistributionType(str, Enum):
    """分销网络类型"""
    OWNED = "OWNED"          # 自有经销商：高成本，高利润
    FRANCHISE = "FRANCHISE"  # 加盟商：低成本，利润分成


class MarketingFocus(str, Enum):
    """营销活动焦点"""
    BRAND_AWARENESS = "BRAND_AWARENESS"    # 品牌认知
    SALES_PUSH = "SALES_PUSH"              # 促销推动
    MOTORSPORT = "MOTORSPORT"              # 赛车运动
    ECO_FRIENDLY = "ECO_FRIENDLY"          # 环保形象
    LUXURY = "LUXURY"                      # 奢华定位
    RELIABILITY = "RELIABILITY"            # 可靠性宣传


class ConsumerSegment(str, Enum):
    """消费者细分类型"""
    YOUTH = "YOUTH"                      # 年轻人
    FAMILY = "FAMILY"                    # 家庭用户
    LUXURY = "LUXURY"                    # 奢华用户
    SPORTS = "SPORTS"                    # 运动爱好者
    PRACTICAL = "PRACTICAL"              # 实用主义
    ECO_CONSCIOUS = "ECO_CONSCIOUS"      # 环保意识


# ========== 数据模型 ==========

class DistributionNetwork(Base, TimestampMixin, BaseModel):
    """
    分销网络模型
    链接公司到地区的销售渠道
    """
    __tablename__ = "distribution_networks"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False, comment="公司ID（待添加外键）")
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    
    # 分销类型
    type = Column(
        String(20), nullable=False,
        comment="分销类型：OWNED（自有）/ FRANCHISE（加盟）"
    )
    
    # 覆盖度与质量
    coverage_level = Column(
        Float, nullable=False, default=0.0,
        comment="覆盖水平 0.0-1.0，决定潜在客户可触达率"
    )
    quality_score = Column(
        Float, nullable=False, default=50.0,
        comment="服务质量评分 0-100，影响客户满意度"
    )
    
    # 容量与成本
    monthly_capacity = Column(
        Integer, nullable=False,
        comment="月度销售容量（辆）"
    )
    setup_cost = Column(
        Float, nullable=False, default=0.0,
        comment="建设成本"
    )
    monthly_upkeep = Column(
        Float, nullable=False,
        comment="月度维护成本"
    )
    
    # 利润分成（仅加盟商）
    profit_split_dealer = Column(
        Float, nullable=True, default=0.3,
        comment="经销商分成比例（如0.3表示经销商拿30%）"
    )
    
    # 状态
    is_active = Column(Boolean, nullable=False, default=True)
    established_turn = Column(Integer, nullable=False, comment="建立回合")
    
    # 关系
    region = relationship("Region", foreign_keys=[region_id])
    
    # 约束
    __table_args__ = (
        CheckConstraint("coverage_level >= 0.0 AND coverage_level <= 1.0", name="check_coverage"),
        CheckConstraint("quality_score >= 0 AND quality_score <= 100", name="check_quality"),
        CheckConstraint("monthly_capacity > 0", name="check_capacity"),
        CheckConstraint("profit_split_dealer >= 0.0 AND profit_split_dealer <= 1.0", name="check_split"),
        Index("idx_distribution_company_region", "company_id", "region_id"),
        Index("idx_distribution_active", "is_active"),
    )
    
    @validates("type")
    def validate_type(self, key: str, value: str) -> str:
        """验证分销类型"""
        if value.upper() not in [e.value for e in DistributionType]:
            raise ValueError(f"分销类型必须是: {[e.value for e in DistributionType]}")
        return value.upper()
    
    def get_effective_margin(self) -> float:
        """
        计算有效利润率
        
        Returns:
            自有渠道返回1.0（100%利润），加盟商返回实际保留比例
        """
        if self.type == DistributionType.OWNED.value:
            return 1.0
        else:
            return 1.0 - (self.profit_split_dealer or 0.3)
    
    def __repr__(self) -> str:
        return (f"<DistributionNetwork(company={self.company_id}, "
                f"region={self.region_id}, type={self.type}, "
                f"coverage={self.coverage_level:.2f})>")


class MarketingCampaign(Base, TimestampMixin, BaseModel):
    """
    营销活动模型
    影响品牌认知和短期销量
    """
    __tablename__ = "marketing_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False, comment="公司ID")
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    
    # 活动基本信息
    name = Column(String(200), nullable=False, comment="活动名称")
    
    # 目标与焦点
    target_bucket = Column(
        String(50), nullable=False,
        comment="目标消费者细分：YOUTH/FAMILY/LUXURY等"
    )
    focus = Column(
        String(50), nullable=False,
        comment="营销焦点：BRAND_AWARENESS/SALES_PUSH/MOTORSPORT等"
    )
    
    # 预算与时间
    budget = Column(Float, nullable=False, comment="活动预算")
    start_turn = Column(Integer, nullable=False, comment="开始回合")
    end_turn = Column(Integer, nullable=False, comment="结束回合")
    
    # 效果追踪
    effectiveness_score = Column(
        Float, nullable=True,
        comment="效果评分 0-100（活动结束后计算）"
    )
    reach_count = Column(
        Integer, nullable=True,
        comment="触达人数"
    )
    conversion_boost = Column(
        Float, nullable=True,
        comment="转化率提升（%）"
    )
    
    # 状态
    is_active = Column(Boolean, nullable=False, default=True)
    
    # 关系
    region = relationship("Region", foreign_keys=[region_id])
    
    # 约束
    __table_args__ = (
        CheckConstraint("budget > 0", name="check_budget"),
        CheckConstraint("end_turn >= start_turn", name="check_turn_order"),
        CheckConstraint("effectiveness_score IS NULL OR (effectiveness_score >= 0 AND effectiveness_score <= 100)", 
                       name="check_effectiveness"),
        Index("idx_campaign_company_region", "company_id", "region_id"),
        Index("idx_campaign_active", "is_active"),
        Index("idx_campaign_turns", "start_turn", "end_turn"),
    )
    
    @validates("target_bucket")
    def validate_target(self, key: str, value: str) -> str:
        """验证目标细分"""
        if value.upper() not in [e.value for e in ConsumerSegment]:
            raise ValueError(f"目标细分必须是: {[e.value for e in ConsumerSegment]}")
        return value.upper()
    
    @validates("focus")
    def validate_focus(self, key: str, value: str) -> str:
        """验证营销焦点"""
        if value.upper() not in [e.value for e in MarketingFocus]:
            raise ValueError(f"营销焦点必须是: {[e.value for e in MarketingFocus]}")
        return value.upper()
    
    def __repr__(self) -> str:
        return (f"<MarketingCampaign(name='{self.name}', "
                f"company={self.company_id}, target={self.target_bucket}, "
                f"budget={self.budget:.0f})>")


class BrandPerception(Base, TimestampMixin, BaseModel):
    """
    品牌认知模型
    每个公司在每个地区的品牌形象向量
    """
    __tablename__ = "brand_perceptions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False, comment="公司ID")
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    
    # 品牌形象向量（0-100分）
    reliability_score = Column(
        Float, nullable=False, default=50.0,
        comment="可靠性形象"
    )
    sportiness_score = Column(
        Float, nullable=False, default=50.0,
        comment="运动性形象"
    )
    luxury_score = Column(
        Float, nullable=False, default=50.0,
        comment="奢华形象"
    )
    eco_friendly_score = Column(
        Float, nullable=False, default=50.0,
        comment="环保形象"
    )
    innovation_score = Column(
        Float, nullable=False, default=50.0,
        comment="创新形象"
    )
    value_for_money_score = Column(
        Float, nullable=False, default=50.0,
        comment="性价比形象"
    )
    
    # 总体品牌健康度
    overall_awareness = Column(
        Float, nullable=False, default=0.0,
        comment="品牌知名度 0.0-1.0"
    )
    
    # 粉丝基数（忠实客户）
    fanbase_count = Column(
        Integer, nullable=False, default=0,
        comment="忠实粉丝数量，可以缓冲负面评价"
    )
    
    # 历史表现（影响认知）
    avg_quality_rating = Column(
        Float, nullable=True,
        comment="历史平均质量评分（用户反馈）"
    )
    
    # 关系
    region = relationship("Region", foreign_keys=[region_id])
    
    # 约束
    __table_args__ = (
        CheckConstraint("reliability_score >= 0 AND reliability_score <= 100", name="check_reliability"),
        CheckConstraint("sportiness_score >= 0 AND sportiness_score <= 100", name="check_sportiness"),
        CheckConstraint("luxury_score >= 0 AND luxury_score <= 100", name="check_luxury"),
        CheckConstraint("eco_friendly_score >= 0 AND eco_friendly_score <= 100", name="check_eco"),
        CheckConstraint("innovation_score >= 0 AND innovation_score <= 100", name="check_innovation"),
        CheckConstraint("value_for_money_score >= 0 AND value_for_money_score <= 100", name="check_value"),
        CheckConstraint("overall_awareness >= 0.0 AND overall_awareness <= 1.0", name="check_awareness"),
        CheckConstraint("fanbase_count >= 0", name="check_fanbase"),
        Index("idx_brand_company_region", "company_id", "region_id", unique=True),
    )
    
    def to_vector(self) -> Dict[str, float]:
        """
        返回品牌向量字典
        
        Returns:
            品牌属性字典
        """
        return {
            "reliability": self.reliability_score,
            "sportiness": self.sportiness_score,
            "luxury": self.luxury_score,
            "eco_friendly": self.eco_friendly_score,
            "innovation": self.innovation_score,
            "value_for_money": self.value_for_money_score
        }
    
    def update_from_sales(self, quality_feedback: float, sales_volume: int) -> None:
        """
        根据销售反馈更新品牌认知
        
        Args:
            quality_feedback: 质量反馈评分 0-100
            sales_volume: 销量
        """
        # 更新可靠性评分（基于质量反馈）
        weight = min(sales_volume / 1000.0, 1.0)  # 销量权重
        self.reliability_score = (
            self.reliability_score * (1 - weight * 0.1) + 
            quality_feedback * weight * 0.1
        )
        
        # 更新平均质量
        if self.avg_quality_rating is None:
            self.avg_quality_rating = quality_feedback
        else:
            self.avg_quality_rating = (
                self.avg_quality_rating * 0.9 + quality_feedback * 0.1
            )
        
        # 增加粉丝基数（优质产品积累粉丝）
        if quality_feedback >= 75:
            self.fanbase_count += int(sales_volume * 0.05)  # 5%的高质量购买者成为粉丝
    
    def __repr__(self) -> str:
        return (f"<BrandPerception(company={self.company_id}, "
                f"region={self.region_id}, awareness={self.overall_awareness:.2f})>")


class ConsumerBucket(Base, TimestampMixin, BaseModel):
    """
    消费者细分桶模型
    代表一组具有相似偏好和购买力的消费者
    """
    __tablename__ = "consumer_buckets"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    
    # 基本信息
    bucket_code = Column(String(50), nullable=False, comment="桶代码，如'NAM_YOUTH_URBAN'")
    name = Column(String(200), nullable=False, comment="名称，如'年轻城市专业人士'")
    segment = Column(
        String(50), nullable=False,
        comment="所属细分：YOUTH/FAMILY/LUXURY等"
    )
    
    # 人口统计
    population_count = Column(Integer, nullable=False, comment="该细分人口数量")
    avg_income = Column(Float, nullable=False, comment="平均收入")
    avg_age = Column(Float, nullable=False, comment="平均年龄")
    
    # 购买行为
    purchase_frequency_years = Column(
        Float, nullable=False, default=8.0,
        comment="购车频率（年）"
    )
    price_sensitivity = Column(
        Float, nullable=False, default=0.5,
        comment="价格敏感度 0-1"
    )
    brand_loyalty = Column(
        Float, nullable=False, default=0.3,
        comment="品牌忠诚度 0-1"
    )
    early_adopter_score = Column(
        Float, nullable=False, default=0.3,
        comment="早期采用者得分 0-1"
    )
    
    # 效用权重（必须加起来等于1.0）
    weight_price = Column(Float, nullable=False, default=0.20, comment="价格权重")
    weight_performance = Column(Float, nullable=False, default=0.15, comment="性能权重")
    weight_comfort = Column(Float, nullable=False, default=0.15, comment="舒适性权重")
    weight_reliability = Column(Float, nullable=False, default=0.20, comment="可靠性权重")
    weight_safety = Column(Float, nullable=False, default=0.10, comment="安全权重")
    weight_prestige = Column(Float, nullable=False, default=0.05, comment="声望权重")
    weight_efficiency = Column(Float, nullable=False, default=0.10, comment="效率权重")
    weight_practicality = Column(Float, nullable=False, default=0.05, comment="实用性权重")
    
    # 偏好
    preferred_body_styles = Column(
        Text, nullable=False, default='["SEDAN", "HATCHBACK"]',
        comment="偏好车身类型（JSON数组）"
    )
    preferred_size = Column(
        String(20), nullable=False, default="MEDIUM",
        comment="偏好尺寸：SMALL/MEDIUM/LARGE/ANY"
    )
    min_acceptable_utility = Column(
        Float, nullable=False, default=0.5,
        comment="最低可接受效用，低于此值不购买"
    )
    
    # 动态状态
    current_demand = Column(
        Integer, nullable=False, default=0,
        comment="当前回合需求量"
    )
    satisfied_demand = Column(
        Integer, nullable=False, default=0,
        comment="已满足需求量"
    )
    
    # 关系
    region = relationship("Region", foreign_keys=[region_id])
    
    # 约束
    __table_args__ = (
        CheckConstraint("population_count > 0", name="check_population"),
        CheckConstraint("price_sensitivity >= 0.0 AND price_sensitivity <= 1.0", name="check_price_sens"),
        CheckConstraint("brand_loyalty >= 0.0 AND brand_loyalty <= 1.0", name="check_loyalty"),
        CheckConstraint("min_acceptable_utility >= 0.0 AND min_acceptable_utility <= 1.0", name="check_utility"),
        Index("idx_bucket_region", "region_id"),
        Index("idx_bucket_segment", "segment"),
        Index("idx_bucket_code", "bucket_code", unique=True),
    )
    
    @validates("segment")
    def validate_segment(self, key: str, value: str) -> str:
        """验证细分类型"""
        if value.upper() not in [e.value for e in ConsumerSegment]:
            raise ValueError(f"细分类型必须是: {[e.value for e in ConsumerSegment]}")
        return value.upper()
    
    def get_preferred_body_styles(self) -> List[str]:
        """获取偏好车身类型列表"""
        try:
            return json.loads(self.preferred_body_styles)
        except:
            return ["SEDAN"]
    
    def set_preferred_body_styles(self, styles: List[str]) -> None:
        """设置偏好车身类型"""
        self.preferred_body_styles = json.dumps(styles)
    
    def get_total_weights(self) -> float:
        """检查权重总和（应为1.0）"""
        return (
            self.weight_price + self.weight_performance + self.weight_comfort +
            self.weight_reliability + self.weight_safety + self.weight_prestige +
            self.weight_efficiency + self.weight_practicality
        )
    
    def __repr__(self) -> str:
        return (f"<ConsumerBucket(code='{self.bucket_code}', "
                f"population={self.population_count:,}, "
                f"segment={self.segment})>")


class IntelligenceReport(Base, TimestampMixin, BaseModel):
    """
    情报报告模型
    存储通过间谍/逆向工程获取的竞争对手信息
    """
    __tablename__ = "intelligence_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # 情报主体与客体
    company_id = Column(Integer, nullable=False, comment="情报所有者（谁获得的情报）")
    target_company_id = Column(Integer, nullable=False, comment="目标公司（被侦查者）")
    
    # 情报类型
    report_type = Column(
        String(50), nullable=False,
        comment="报告类型：FINANCIAL/TECH/STRATEGY/CAR_SPECS"
    )
    
    # 情报内容（JSON存储）
    data_snapshot = Column(
        Text, nullable=False,
        comment="情报快照（JSON格式）"
    )
    
    # 情报质量
    reliability = Column(
        Float, nullable=False, default=0.8,
        comment="情报可靠性 0-1，影响数据准确度"
    )
    
    # 时间与成本
    acquired_turn = Column(Integer, nullable=False, comment="获取回合")
    cost = Column(Float, nullable=False, comment="获取成本")
    
    # 有效期
    expires_turn = Column(
        Integer, nullable=True,
        comment="过期回合（NULL表示永久有效）"
    )
    
    # 约束
    __table_args__ = (
        CheckConstraint("reliability >= 0.0 AND reliability <= 1.0", name="check_reliability_range"),
        CheckConstraint("cost >= 0", name="check_cost"),
        Index("idx_intel_company_target", "company_id", "target_company_id"),
        Index("idx_intel_type", "report_type"),
        Index("idx_intel_turn", "acquired_turn"),
    )
    
    def get_data(self) -> Dict[str, Any]:
        """获取情报数据"""
        try:
            return json.loads(self.data_snapshot)
        except:
            return {}
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """设置情报数据"""
        self.data_snapshot = json.dumps(data)
    
    def is_expired(self, current_turn: int) -> bool:
        """检查情报是否过期"""
        if self.expires_turn is None:
            return False
        return current_turn > self.expires_turn
    
    def __repr__(self) -> str:
        return (f"<IntelligenceReport(company={self.company_id}, "
                f"target={self.target_company_id}, type={self.report_type}, "
                f"turn={self.acquired_turn})>")


# 导出所有模型
__all__ = [
    "DistributionType",
    "MarketingFocus",
    "ConsumerSegment",
    "DistributionNetwork",
    "MarketingCampaign",
    "BrandPerception",
    "ConsumerBucket",
    "IntelligenceReport"
]


