"""
事件系统模型
管理游戏中的新闻、危机、教程触发器等事件
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index, Enum
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any, List
import enum
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class EventType(enum.Enum):
    """事件类型"""
    NEWS = "NEWS"                    # 新闻事件
    CRISIS = "CRISIS"                # 危机事件
    OPPORTUNITY = "OPPORTUNITY"      # 机遇事件
    TUTORIAL = "TUTORIAL"            # 教程提示
    MILESTONE = "MILESTONE"          # 里程碑成就
    RANDOM_EVENT = "RANDOM_EVENT"    # 随机事件


class EventSeverity(enum.Enum):
    """事件严重程度"""
    INFO = "INFO"          # 信息提示
    LOW = "LOW"            # 轻微影响
    MEDIUM = "MEDIUM"      # 中等影响
    HIGH = "HIGH"          # 重大影响
    CRITICAL = "CRITICAL"  # 危机级别


class EventStatus(enum.Enum):
    """事件状态"""
    TRIGGERED = "TRIGGERED"    # 已触发
    ACTIVE = "ACTIVE"          # 生效中
    RESOLVED = "RESOLVED"      # 已解决
    EXPIRED = "EXPIRED"        # 已过期
    IGNORED = "IGNORED"        # 已忽略


class GameEvent(Base, TimestampMixin, BaseModel):
    """
    游戏事件模型
    记录游戏中发生的所有事件（新闻、危机、机遇等）
    """
    __tablename__ = "game_events"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 事件基础信息 ====================
    event_type = Column(
        Enum(EventType), nullable=False,
        comment="事件类型"
    )
    
    severity = Column(
        Enum(EventSeverity), nullable=False, default=EventSeverity.INFO,
        comment="严重程度"
    )
    
    status = Column(
        Enum(EventStatus), nullable=False, default=EventStatus.TRIGGERED,
        comment="事件状态"
    )
    
    # ==================== 事件内容 ====================
    title = Column(
        String(200), nullable=False,
        comment="事件标题"
    )
    
    description = Column(
        Text, nullable=False,
        comment="事件描述"
    )
    
    icon = Column(
        String(50), nullable=True,
        comment="图标名称（前端使用）"
    )
    
    # ==================== 影响范围 ====================
    affected_company_id = Column(
        Integer, nullable=True,
        comment="受影响公司ID（NULL表示全局事件）"
    )
    
    affected_region_code = Column(
        String(10), nullable=True,
        comment="受影响地区代码（NULL表示全球）"
    )
    
    # ==================== 时间 ====================
    triggered_turn = Column(
        Integer, nullable=False,
        comment="触发回合"
    )
    
    expires_turn = Column(
        Integer, nullable=True,
        comment="过期回合（NULL表示永久或立即生效）"
    )
    
    # ==================== 效果（JSON格式） ====================
    effects = Column(
        Text, nullable=True,
        comment="事件效果（JSON格式）- 如{'cash_change': -10, 'reputation_change': -5}"
    )
    
    # ==================== 玩家选择（可选） ====================
    requires_player_action = Column(
        Boolean, nullable=False, default=False,
        comment="是否需要玩家响应"
    )
    
    player_choices = Column(
        Text, nullable=True,
        comment="玩家可选择的选项（JSON数组）- 如[{'id': 'accept', 'label': '接受', 'effects': {...}}]"
    )
    
    player_choice_made = Column(
        String(50), nullable=True,
        comment="玩家选择的选项ID"
    )
    
    # ==================== 触发条件与上下文 ====================
    trigger_condition = Column(
        Text, nullable=True,
        comment="触发条件（JSON格式）- 用于记录为何触发此事件"
    )
    
    related_entity_id = Column(
        Integer, nullable=True,
        comment="相关实体ID（如车型ID、工厂ID）"
    )
    
    related_entity_type = Column(
        String(50), nullable=True,
        comment="相关实体类型（如'CarTrim', 'Factory'）"
    )
    
    # ==================== 新闻特有字段 ====================
    news_category = Column(
        String(50), nullable=True,
        comment="新闻分类: INDUSTRY/POLITICS/ECONOMY/TECHNOLOGY/COMPANY"
    )
    
    is_public = Column(
        Boolean, nullable=False, default=True,
        comment="是否公开（玩家可见）"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        Index("idx_event_game_turn", "game_id", "triggered_turn"),
        Index("idx_event_type", "event_type"),
        Index("idx_event_company", "affected_company_id"),
        Index("idx_event_status", "status"),
        Index("idx_event_public", "is_public"),
    )
    
    def get_effects(self) -> Dict[str, Any]:
        """获取事件效果"""
        if not self.effects:
            return {}
        try:
            return json.loads(self.effects)
        except:
            return {}
    
    def set_effects(self, effects: Dict[str, Any]) -> None:
        """设置事件效果"""
        self.effects = json.dumps(effects)
    
    def get_player_choices(self) -> List[Dict[str, Any]]:
        """获取玩家选项"""
        if not self.player_choices:
            return []
        try:
            return json.loads(self.player_choices)
        except:
            return []
    
    def set_player_choices(self, choices: List[Dict[str, Any]]) -> None:
        """设置玩家选项"""
        self.player_choices = json.dumps(choices)
    
    def get_trigger_condition(self) -> Dict[str, Any]:
        """获取触发条件"""
        if not self.trigger_condition:
            return {}
        try:
            return json.loads(self.trigger_condition)
        except:
            return {}
    
    def set_trigger_condition(self, condition: Dict[str, Any]) -> None:
        """设置触发条件"""
        self.trigger_condition = json.dumps(condition)
    
    def __repr__(self) -> str:
        return (f"<GameEvent(id={self.id}, type={self.event_type.value}, "
                f"title='{self.title}', turn={self.triggered_turn})>")


class EventTemplate(Base, TimestampMixin, BaseModel):
    """
    事件模板
    定义可重复触发的事件类型（如工人罢工、石油危机）
    """
    __tablename__ = "event_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ==================== 模板信息 ====================
    template_name = Column(
        String(100), nullable=False, unique=True,
        comment="模板名称（唯一标识）"
    )
    
    event_type = Column(
        Enum(EventType), nullable=False,
        comment="事件类型"
    )
    
    severity = Column(
        Enum(EventSeverity), nullable=False,
        comment="严重程度"
    )
    
    # ==================== 内容模板 ====================
    title_template = Column(
        String(200), nullable=False,
        comment="标题模板（可含变量如{company_name}）"
    )
    
    description_template = Column(
        Text, nullable=False,
        comment="描述模板"
    )
    
    # ==================== 触发条件 ====================
    trigger_conditions = Column(
        Text, nullable=False,
        comment="触发条件（JSON格式）- 如{'min_turn': 100, 'max_oil_price': 50}"
    )
    
    trigger_probability = Column(
        Float, nullable=False, default=0.1,
        comment="每回合触发概率 0-1"
    )
    
    cooldown_turns = Column(
        Integer, nullable=False, default=0,
        comment="冷却时间（回合）- 防止短期内重复触发"
    )
    
    # ==================== 效果模板 ====================
    effects_template = Column(
        Text, nullable=False,
        comment="效果模板（JSON格式）"
    )
    
    # ==================== 启用状态 ====================
    is_enabled = Column(
        Boolean, nullable=False, default=True,
        comment="是否启用此模板"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("trigger_probability >= 0 AND trigger_probability <= 1", name="check_trigger_prob"),
        CheckConstraint("cooldown_turns >= 0", name="check_cooldown"),
        Index("idx_template_type", "event_type"),
        Index("idx_template_enabled", "is_enabled"),
    )
    
    def get_trigger_conditions(self) -> Dict[str, Any]:
        """获取触发条件"""
        try:
            return json.loads(self.trigger_conditions)
        except:
            return {}
    
    def set_trigger_conditions(self, conditions: Dict[str, Any]) -> None:
        """设置触发条件"""
        self.trigger_conditions = json.dumps(conditions)
    
    def get_effects_template(self) -> Dict[str, Any]:
        """获取效果模板"""
        try:
            return json.loads(self.effects_template)
        except:
            return {}
    
    def set_effects_template(self, effects: Dict[str, Any]) -> None:
        """设置效果模板"""
        self.effects_template = json.dumps(effects)
    
    def __repr__(self) -> str:
        return (f"<EventTemplate(name='{self.template_name}', "
                f"type={self.event_type.value}, enabled={self.is_enabled})>")


__all__ = [
    "GameEvent", "EventType", "EventSeverity", "EventStatus",
    "EventTemplate"
]


