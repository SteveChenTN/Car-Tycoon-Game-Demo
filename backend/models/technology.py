"""
技术树和研发系统模型
包含技术节点(TechNode)和公司研发状态(CompanyTechnology)
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any, List, Optional
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class TechNode(Base, TimestampMixin, BaseModel):
    """
    技术节点模型
    
    技术树的DAG（有向无环图）节点
    每个节点代表一个可研发的技术
    """
    __tablename__ = "tech_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 基础信息 ====================
    tech_code = Column(
        String(50), nullable=False, unique=True,
        comment="技术唯一代码，如 'TECH_TURBO_V1'"
    )
    
    name = Column(String(100), nullable=False, comment="技术名称，如 '涡轮增压技术'")
    
    category = Column(
        String(30), nullable=False,
        comment="技术类别：ENGINE/ CHASSIS/ SAFETY/ ELECTRONICS/ MATERIALS/ MANUFACTURING"
    )
    
    description = Column(Text, nullable=True, comment="技术描述")
    
    # ==================== 前置条件 ====================
    prerequisite_techs = Column(
        Text, nullable=False, default="[]",
        comment="前置技术列表（JSON数组）- 必须先解锁这些技术"
    )
    
    min_year = Column(
        Integer, nullable=False, default=1950,
        comment="最早可解锁年份 - 反映历史技术发展"
    )
    
    min_tech_level = Column(
        Integer, nullable=False, default=1,
        comment="最低技术等级要求（Company.tech_level）"
    )
    
    # ==================== 研发参数 ====================
    base_research_cost = Column(
        Float, nullable=False,
        comment="基础研发成本（百万游戏币）"
    )
    
    base_research_time = Column(
        Integer, nullable=False,
        comment="基础研发时间（回合数/月数）"
    )
    
    difficulty_rating = Column(
        Float, nullable=False, default=1.0,
        comment="难度系数 0.5-2.0 - 影响突破概率"
    )
    
    # ==================== 解锁效果 ====================
    unlocks_parts = Column(
        Text, nullable=False, default="[]",
        comment="解锁的零部件列表（JSON数组）- 如 ['PART_TURBO_I4', 'PART_INTERCOOLER']"
    )
    
    unlocks_features = Column(
        Text, nullable=False, default="[]",
        comment="解锁的功能特性（JSON数组）- 如 ['FEATURE_VARIABLE_VALVE_TIMING']"
    )
    
    stat_modifiers = Column(
        Text, nullable=False, default="{}",
        comment="属性修正器（JSON对象）- 如 {\"reliability\": 1.05, \"efficiency\": 1.1}"
    )
    
    # ==================== 显示与UI ====================
    tree_position_x = Column(
        Float, nullable=True,
        comment="技术树UI位置X坐标（用于前端可视化）"
    )
    
    tree_position_y = Column(
        Float, nullable=True,
        comment="技术树UI位置Y坐标"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("difficulty_rating >= 0.1 AND difficulty_rating <= 5.0", name="check_difficulty"),
        CheckConstraint("base_research_cost > 0", name="check_research_cost"),
        CheckConstraint("base_research_time > 0", name="check_research_time"),
        CheckConstraint("min_tech_level >= 1 AND min_tech_level <= 10", name="check_min_tech_level"),
        CheckConstraint("min_year >= 1900 AND min_year <= 2100", name="check_min_year"),
        Index("idx_technode_game", "game_id"),
        Index("idx_technode_category", "category"),
        Index("idx_technode_year", "min_year"),
    )
    
    # ==================== 辅助方法 ====================
    
    def get_prerequisites(self) -> List[str]:
        """获取前置技术列表"""
        try:
            return json.loads(self.prerequisite_techs)
        except:
            return []
    
    def set_prerequisites(self, prerequisites: List[str]) -> None:
        """设置前置技术列表"""
        self.prerequisite_techs = json.dumps(prerequisites)
    
    def get_unlocks_parts(self) -> List[str]:
        """获取解锁的零部件列表"""
        try:
            return json.loads(self.unlocks_parts)
        except:
            return []
    
    def set_unlocks_parts(self, parts: List[str]) -> None:
        """设置解锁的零部件列表"""
        self.unlocks_parts = json.dumps(parts)
    
    def get_unlocks_features(self) -> List[str]:
        """获取解锁的功能特性列表"""
        try:
            return json.loads(self.unlocks_features)
        except:
            return []
    
    def set_unlocks_features(self, features: List[str]) -> None:
        """设置解锁的功能特性列表"""
        self.unlocks_features = json.dumps(features)
    
    def get_stat_modifiers(self) -> Dict[str, float]:
        """获取属性修正器"""
        try:
            return json.loads(self.stat_modifiers)
        except:
            return {}
    
    def set_stat_modifiers(self, modifiers: Dict[str, float]) -> None:
        """设置属性修正器"""
        self.stat_modifiers = json.dumps(modifiers)
    
    @validates("category")
    def validate_category(self, key: str, value: str) -> str:
        """验证技术类别"""
        valid_categories = [
            "ENGINE", "CHASSIS", "SAFETY", "ELECTRONICS", 
            "MATERIALS", "MANUFACTURING", "AERODYNAMICS", "PLATFORM"
        ]
        if value.upper() not in valid_categories:
            raise ValueError(f"Invalid category: {value}. Must be one of {valid_categories}")
        return value.upper()
    
    def __repr__(self) -> str:
        return (f"<TechNode(code='{self.tech_code}', "
                f"name='{self.name}', "
                f"category={self.category}, "
                f"cost={self.base_research_cost:.1f}M, "
                f"time={self.base_research_time}mo)>")


class CompanyTechnology(Base, TimestampMixin, BaseModel):
    """
    公司技术研发状态模型
    
    记录每个公司对每个技术的研发进度和状态
    """
    __tablename__ = "company_technologies"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    tech_node_id = Column(Integer, ForeignKey("tech_nodes.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 研发状态 ====================
    status = Column(
        String(20), nullable=False, default="LOCKED",
        comment="状态：LOCKED（锁定）/ AVAILABLE（可研发）/ RESEARCHING（研发中）/ COMPLETED（已完成）"
    )
    
    # ==================== 投资与进度 ====================
    total_invested = Column(
        Float, nullable=False, default=0.0,
        comment="累计投入资金（百万游戏币）"
    )
    
    monthly_investment = Column(
        Float, nullable=False, default=0.0,
        comment="当前每月投入（百万游戏币）"
    )
    
    # 注意：research_progress, research_started_turn, research_completed_turn, 
    # estimated_completion_turn 已移至 RDManager 管理
    
    # ==================== 突破追踪（概率模型）====================
    breakthrough_attempts = Column(
        Integer, nullable=False, default=0,
        comment="尝试突破次数"
    )
    
    last_breakthrough_check_turn = Column(
        Integer, nullable=True,
        comment="上次检查突破的回合"
    )
    
    # ==================== 人员分配 ====================
    assigned_engineers = Column(
        Integer, nullable=False, default=0,
        comment="分配的工程师数量"
    )
    
    assigned_executive_id = Column(
        Integer, nullable=True,
        comment="负责的高管ID（外键关联executives表，暂不设置约束）"
    )
    
    # ==================== 效率与质量 ====================
    research_efficiency = Column(
        Float, nullable=False, default=1.0,
        comment="研发效率倍数（受公司rd_efficiency和高管能力影响）"
    )
    
    completion_quality = Column(
        Float, nullable=True,
        comment="完成质量 0-1（影响解锁技术的有效性）"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("total_invested >= 0", name="check_invested"),
        CheckConstraint("monthly_investment >= 0", name="check_monthly"),
        CheckConstraint("assigned_engineers >= 0", name="check_engineers"),
        CheckConstraint("research_efficiency > 0", name="check_efficiency"),
        CheckConstraint("completion_quality IS NULL OR (completion_quality >= 0 AND completion_quality <= 1)", 
                       name="check_quality"),
        Index("idx_companytech_company", "company_id"),
        Index("idx_companytech_tech", "tech_node_id"),
        Index("idx_companytech_status", "status"),
        Index("idx_companytech_company_status", "company_id", "status"),
        # 确保每个公司对每个技术只有一条记录
        Index("idx_companytech_unique", "company_id", "tech_node_id", unique=True),
    )
    
    # ==================== 关系 ====================
    tech_node = relationship("TechNode", foreign_keys=[tech_node_id])
    # company 反向关系将由 Company 模型定义
    
    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        """验证状态"""
        valid_statuses = ["LOCKED", "AVAILABLE", "RESEARCHING", "COMPLETED"]
        if value.upper() not in valid_statuses:
            raise ValueError(f"Invalid status: {value}. Must be one of {valid_statuses}")
        return value.upper()
    
    def can_start_research(self) -> bool:
        """是否可以开始研发"""
        return self.status == "AVAILABLE"
    
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == "COMPLETED"
    
    def is_in_progress(self) -> bool:
        """是否正在研发中"""
        return self.status == "RESEARCHING"
    
    def finalize_design(self, payload: Dict[str, Any]) -> None:
        """
        完成设计（由RDManager调用）
        
        Args:
            payload: 设计完成时的额外数据
        """
        # 标记技术为已完成
        self.status = "COMPLETED"
        # completion_turn 由RDManager在payload中提供
        if "completion_turn" in payload:
            # 注意：research_completed_turn字段已移除，如果需要可以存储在payload中
            pass
    
    def __repr__(self) -> str:
        return (f"<CompanyTechnology(company_id={self.company_id}, "
                f"tech={self.tech_node_id}, "
                f"status={self.status})>")


__all__ = ["TechNode", "CompanyTechnology"]

