"""
外交与竞争系统 - Dirty Tricks
Diplomacy & Competition - Corporate Espionage, Poaching, PR Warfare

核心机制：
- Executive Poaching（挖角高管）
- PR Attacks（公关战）
- Patent System（专利接口，逻辑待实现）
- Competitor Relations（关系追踪）
"""
from sqlalchemy import Column, Integer, Float, String, Boolean, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

from backend.database import Base
from backend.models.base import TimestampMixin


class CompetitorRelation(Base, TimestampMixin):
    """
    公司间关系追踪
    
    范围：-100（宿敌）到 +100（盟友）
    
    影响：
    - 负值：更容易被攻击，更难合作
    - 正值：合作机会，B2B优惠
    """
    __tablename__ = "competitor_relations"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # 主体公司与目标公司
    company_id = Column(Integer, nullable=False, comment="发起方公司ID")
    target_company_id = Column(Integer, nullable=False, comment="目标公司ID")
    
    # 关系值
    relation_score = Column(Float, nullable=False, default=0.0,
                           comment="关系分数：-100（宿敌）到 +100（盟友）")
    
    # 历史记录
    last_interaction_turn = Column(Integer, nullable=True)
    total_positive_actions = Column(Integer, default=0)
    total_negative_actions = Column(Integer, default=0)
    
    # 特殊状态
    is_embargo = Column(Boolean, default=False, comment="是否禁运（拒绝B2B交易）")
    is_alliance = Column(Boolean, default=False, comment="是否结盟")
    
    __table_args__ = (
        Index("idx_relation_company", "company_id"),
        Index("idx_relation_target", "target_company_id"),
    )
    
    def __repr__(self):
        return f"<CompetitorRelation(company={self.company_id}, target={self.target_company_id}, score={self.relation_score})>"


class DiplomaticAction(Base, TimestampMixin):
    """
    外交行动记录（包括 Dirty Tricks）
    
    记录所有竞争行为：
    - POACH_EXECUTIVE: 挖角高管
    - PR_ATTACK: 公关攻击
    - ESPIONAGE: 间谍活动（未来）
    - PATENT_LAWSUIT: 专利诉讼（未来）
    - COOPERATION: 合作行为（B2B、联合研发）
    """
    __tablename__ = "diplomatic_actions"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # 行动者与目标
    actor_company_id = Column(Integer, nullable=False, comment="发起方公司")
    target_company_id = Column(Integer, nullable=False, comment="目标公司")
    
    # 行动类型
    action_type = Column(
        String(30), nullable=False,
        comment="行动类型：POACH_EXECUTIVE/ PR_ATTACK/ ESPIONAGE/ PATENT_LAWSUIT/ COOPERATION"
    )
    
    # 行动细节（JSON）
    action_details = Column(Text, nullable=True, comment="行动详细信息（JSON）")
    
    # 行动结果
    success = Column(Boolean, nullable=True, comment="是否成功（NULL表示进行中）")
    outcome_description = Column(Text, nullable=True)
    
    # 成本与收益
    cost_paid = Column(Float, default=0.0)
    value_gained = Column(Float, default=0.0)
    
    # 关系影响
    relation_change = Column(Float, default=0.0, comment="对关系的影响（±分数）")
    
    # 时间
    executed_turn = Column(Integer, nullable=False)
    resolved_turn = Column(Integer, nullable=True)
    
    # 可见性
    is_public = Column(Boolean, default=True, comment="是否公开行动（间谍活动不公开）")
    discovered_by_target = Column(Boolean, default=False)
    
    __table_args__ = (
        Index("idx_action_actor", "actor_company_id"),
        Index("idx_action_target", "target_company_id"),
        Index("idx_action_type", "action_type"),
        Index("idx_action_turn", "executed_turn"),
    )
    
    def __repr__(self):
        status = "✓" if self.success else "✗" if self.success is False else "?"
        return (f"<DiplomaticAction({status} {self.action_type}, "
                f"actor={self.actor_company_id} → target={self.target_company_id})>")


class Patent(Base, TimestampMixin):
    """
    专利系统（Interface Only）
    
    当前仅存储数据，逻辑待实现
    
    未来功能：
    - 技术专利保护（竞争对手需授权）
    - 专利诉讼（侵权罚款）
    - 专利许可收入
    """
    __tablename__ = "patents"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # 专利所有者
    owner_company_id = Column(Integer, nullable=False, comment="专利持有公司")
    
    # 关联技术
    tech_node_id = Column(Integer, nullable=True, comment="关联技术节点ID（如有）")
    
    # 专利信息
    patent_name = Column(String(200), nullable=False)
    patent_description = Column(Text, nullable=True)
    
    # 保护范围
    protection_scope = Column(Text, nullable=True, comment="保护范围描述（JSON）")
    
    # 时间
    filed_turn = Column(Integer, nullable=False, comment="申请回合")
    granted_turn = Column(Integer, nullable=True, comment="授权回合")
    expiry_turn = Column(Integer, nullable=False, comment="过期回合")
    
    # 状态
    status = Column(
        String(20), nullable=False, default="PENDING",
        comment="专利状态：PENDING（审查中）/ GRANTED（已授权）/ EXPIRED（已过期）/ INVALIDATED（已失效）"
    )
    
    # 价值
    estimated_value = Column(Float, default=0.0, comment="估计价值")
    total_licensing_revenue = Column(Float, default=0.0, comment="累计授权收入")
    
    __table_args__ = (
        Index("idx_patent_owner", "owner_company_id"),
        Index("idx_patent_tech", "tech_node_id"),
        Index("idx_patent_status", "status"),
    )
    
    def is_active(self, current_turn: int) -> bool:
        """检查专利是否在保护期内"""
        return (
            self.status == "GRANTED" and
            self.granted_turn is not None and
            current_turn <= self.expiry_turn
        )
    
    def __repr__(self):
        return f"<Patent(name='{self.patent_name}', owner={self.owner_company_id}, status={self.status})>"


# 导出
__all__ = ["CompetitorRelation", "DiplomaticAction", "Patent"]


