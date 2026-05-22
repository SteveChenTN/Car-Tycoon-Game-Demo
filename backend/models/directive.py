"""
公司指令系统模型
包含玩家发布的各类指令：战略哲学、KPI目标、自然语言指令
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index, DateTime
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any, Optional
import json
from datetime import datetime

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class Directive(Base, TimestampMixin, BaseModel):
    """
    公司指令模型
    
    玩家可以通过多种方式给公司下达指令：
    1. 战略哲学（PHILOSOPHY）- 如"质量优先"
    2. KPI目标（KPI）- 如"市场份额达到15%"
    3. 自然语言指令（NATURAL_LANGUAGE）- 如"开发一款便宜的跑车"
    4. 具体任务（SPECIFIC）- 如"将Fusion生产线产能提升到10000/月"
    """
    __tablename__ = "directives"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 指令类型 ====================
    directive_type = Column(
        String(30), nullable=False,
        comment="指令类型：PHILOSOPHY/ KPI/ NATURAL_LANGUAGE/ SPECIFIC"
    )
    
    category = Column(
        String(30), nullable=True,
        comment="指令类别：DESIGN/ PRODUCTION/ MARKETING/ RD/ HR/ FINANCE"
    )
    
    priority = Column(
        String(10), nullable=False, default="MEDIUM",
        comment="优先级：LOW/ MEDIUM/ HIGH/ CRITICAL"
    )
    
    # ==================== 自然语言指令 ====================
    original_text = Column(
        Text, nullable=True,
        comment="原始自然语言指令文本"
    )
    
    parsed_parameters = Column(
        Text, nullable=True,
        comment="解析后的参数（JSON）- NLP处理结果"
    )
    
    parsing_confidence = Column(
        Float, nullable=True,
        comment="解析置信度 0-1 - 低于0.7需要玩家确认"
    )
    
    # ==================== KPI指令 ====================
    kpi_metric = Column(
        String(50), nullable=True,
        comment="KPI指标名称 - 如 'MARKET_SHARE', 'PROFIT_MARGIN', 'RELIABILITY_SCORE'"
    )
    
    kpi_target_value = Column(
        Float, nullable=True,
        comment="KPI目标值"
    )
    
    kpi_current_value = Column(
        Float, nullable=True,
        comment="KPI当前值（动态更新）"
    )
    
    kpi_deadline_turn = Column(
        Integer, nullable=True,
        comment="KPI截止回合"
    )
    
    # ==================== 战略哲学指令 ====================
    philosophy_key = Column(
        String(50), nullable=True,
        comment="哲学维度 - 如 'QUALITY_VS_QUANTITY', 'INNOVATION_VS_RELIABILITY'"
    )
    
    philosophy_value = Column(
        Float, nullable=True,
        comment="哲学取向值 0-1 - 0=左端（如成本优先），1=右端（如质量优先）"
    )
    
    # ==================== 具体任务指令 ====================
    specific_action = Column(
        String(50), nullable=True,
        comment="具体动作 - 如 'INCREASE_PRODUCTION', 'HIRE_EXECUTIVE', 'RESEARCH_TECH'"
    )
    
    specific_target_id = Column(
        Integer, nullable=True,
        comment="目标对象ID - 如工厂ID、车型ID、技术ID"
    )
    
    specific_parameters = Column(
        Text, nullable=True,
        comment="具体参数（JSON）- 如 {'target_capacity': 10000}"
    )
    
    # ==================== 指令分配 ====================
    assigned_staff_id = Column(
        Integer, nullable=True,
        comment="负责执行的高管ID（外键到staff表）"
    )
    
    auto_assigned = Column(
        Boolean, nullable=False, default=False,
        comment="是否由系统自动分配（而非玩家手动指定）"
    )
    
    # ==================== 执行状态 ====================
    status = Column(
        String(20), nullable=False, default="ACTIVE",
        comment="状态：PENDING/ ACTIVE/ IN_PROGRESS/ COMPLETED/ FAILED/ CANCELLED"
    )
    
    created_turn = Column(
        Integer, nullable=False,
        comment="创建回合"
    )
    
    activated_turn = Column(
        Integer, nullable=True,
        comment="激活回合（开始执行）"
    )
    
    completed_turn = Column(
        Integer, nullable=True,
        comment="完成回合"
    )
    
    # ==================== 执行进度 ====================
    progress_percent = Column(
        Float, nullable=False, default=0.0,
        comment="完成进度 0-100"
    )
    
    execution_quality = Column(
        Float, nullable=True,
        comment="执行质量 0-1 - 受高管能力和士气影响"
    )
    
    estimated_completion_turn = Column(
        Integer, nullable=True,
        comment="预计完成回合（动态更新）"
    )
    
    # ==================== 反馈与结果 ====================
    feedback_notes = Column(
        Text, nullable=True,
        comment="执行反馈（JSON数组）- 高管或AI的进度报告"
    )
    
    execution_log = Column(
        Text, nullable=True,
        comment="执行日志（JSON数组）- 记录关键事件"
    )
    
    outcome_metrics = Column(
        Text, nullable=True,
        comment="结果指标（JSON）- 完成后的实际效果"
    )
    
    success_rating = Column(
        Float, nullable=True,
        comment="成功评分 0-1 - 完成后评估"
    )
    
    # ==================== 依赖关系 ====================
    depends_on_directive_id = Column(
        Integer, nullable=True,
        comment="依赖的前置指令ID - 必须等前置完成"
    )
    
    blocks_directives = Column(
        Text, nullable=True,
        comment="阻塞的后续指令ID列表（JSON数组）"
    )
    
    # ==================== 资源需求（预算） ====================
    estimated_cost = Column(
        Float, nullable=True,
        comment="预计成本（百万游戏币）"
    )
    
    actual_cost = Column(
        Float, nullable=True,
        comment="实际成本（百万游戏币）"
    )
    
    budget_approved = Column(
        Boolean, nullable=False, default=False,
        comment="是否已批准预算"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_progress"),
        CheckConstraint("execution_quality IS NULL OR (execution_quality >= 0 AND execution_quality <= 1)", 
                       name="check_exec_quality"),
        CheckConstraint("success_rating IS NULL OR (success_rating >= 0 AND success_rating <= 1)", 
                       name="check_success"),
        CheckConstraint("philosophy_value IS NULL OR (philosophy_value >= 0 AND philosophy_value <= 1)", 
                       name="check_philosophy"),
        CheckConstraint("parsing_confidence IS NULL OR (parsing_confidence >= 0 AND parsing_confidence <= 1)", 
                       name="check_confidence"),
        CheckConstraint("estimated_cost IS NULL OR estimated_cost >= 0", name="check_estimated_cost"),
        CheckConstraint("actual_cost IS NULL OR actual_cost >= 0", name="check_actual_cost"),
        Index("idx_directive_company", "company_id"),
        Index("idx_directive_status", "status"),
        Index("idx_directive_type", "directive_type"),
        Index("idx_directive_staff", "assigned_staff_id"),
        Index("idx_directive_company_status", "company_id", "status"),
        Index("idx_directive_game", "game_id"),
    )
    
    # ==================== 辅助方法 ====================
    
    @validates("directive_type")
    def validate_directive_type(self, key: str, value: str) -> str:
        """验证指令类型"""
        valid_types = ["PHILOSOPHY", "KPI", "NATURAL_LANGUAGE", "SPECIFIC"]
        if value.upper() not in valid_types:
            raise ValueError(f"Invalid directive type: {value}. Must be one of {valid_types}")
        return value.upper()
    
    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        """验证状态"""
        valid_statuses = ["PENDING", "ACTIVE", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"]
        if value.upper() not in valid_statuses:
            raise ValueError(f"Invalid status: {value}. Must be one of {valid_statuses}")
        return value.upper()
    
    @validates("priority")
    def validate_priority(self, key: str, value: str) -> str:
        """验证优先级"""
        valid_priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if value.upper() not in valid_priorities:
            raise ValueError(f"Invalid priority: {value}. Must be one of {valid_priorities}")
        return value.upper()
    
    def get_parsed_parameters(self) -> Dict[str, Any]:
        """获取解析后的参数"""
        if not self.parsed_parameters:
            return {}
        try:
            return json.loads(self.parsed_parameters)
        except:
            return {}
    
    def set_parsed_parameters(self, params: Dict[str, Any]) -> None:
        """设置解析后的参数"""
        self.parsed_parameters = json.dumps(params)
    
    def get_specific_parameters(self) -> Dict[str, Any]:
        """获取具体任务参数"""
        if not self.specific_parameters:
            return {}
        try:
            return json.loads(self.specific_parameters)
        except:
            return {}
    
    def set_specific_parameters(self, params: Dict[str, Any]) -> None:
        """设置具体任务参数"""
        self.specific_parameters = json.dumps(params)
    
    def get_feedback_notes(self) -> list[str]:
        """获取反馈笔记列表"""
        if not self.feedback_notes:
            return []
        try:
            return json.loads(self.feedback_notes)
        except:
            return []
    
    def add_feedback_note(self, note: str) -> None:
        """添加反馈笔记"""
        notes = self.get_feedback_notes()
        notes.append({
            "timestamp": datetime.utcnow().isoformat(),
            "note": note
        })
        self.feedback_notes = json.dumps(notes)
    
    def get_execution_log(self) -> list[Dict[str, Any]]:
        """获取执行日志"""
        if not self.execution_log:
            return []
        try:
            return json.loads(self.execution_log)
        except:
            return []
    
    def add_execution_event(self, event_type: str, description: str, data: Optional[Dict] = None) -> None:
        """添加执行事件"""
        log = self.get_execution_log()
        log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "description": description,
            "data": data or {}
        })
        self.execution_log = json.dumps(log)
    
    def get_outcome_metrics(self) -> Dict[str, Any]:
        """获取结果指标"""
        if not self.outcome_metrics:
            return {}
        try:
            return json.loads(self.outcome_metrics)
        except:
            return {}
    
    def set_outcome_metrics(self, metrics: Dict[str, Any]) -> None:
        """设置结果指标"""
        self.outcome_metrics = json.dumps(metrics)
    
    def get_blocked_directives(self) -> list[int]:
        """获取被阻塞的指令ID列表"""
        if not self.blocks_directives:
            return []
        try:
            return json.loads(self.blocks_directives)
        except:
            return []
    
    def set_blocked_directives(self, directive_ids: list[int]) -> None:
        """设置被阻塞的指令ID列表"""
        self.blocks_directives = json.dumps(directive_ids)
    
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in ["COMPLETED", "FAILED", "CANCELLED"]
    
    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.status in ["ACTIVE", "IN_PROGRESS"]
    
    def calculate_kpi_progress(self) -> float:
        """
        计算KPI完成进度
        
        Returns:
            进度百分比 0-100
        """
        if self.directive_type != "KPI" or not self.kpi_target_value:
            return 0.0
        
        if not self.kpi_current_value:
            return 0.0
        
        # 假设起始值为0，目标值为target
        progress = (self.kpi_current_value / self.kpi_target_value) * 100.0
        return min(100.0, max(0.0, progress))
    
    def get_summary(self) -> str:
        """获取指令摘要（用于UI显示）"""
        if self.directive_type == "PHILOSOPHY":
            return f"战略哲学: {self.philosophy_key} = {self.philosophy_value:.0%}"
        elif self.directive_type == "KPI":
            return f"KPI目标: {self.kpi_metric} → {self.kpi_target_value}"
        elif self.directive_type == "NATURAL_LANGUAGE":
            return f"指令: {self.original_text[:50]}..."
        elif self.directive_type == "SPECIFIC":
            return f"任务: {self.specific_action}"
        return "Unknown Directive"
    
    def __repr__(self) -> str:
        return (f"<Directive(id={self.id}, "
                f"type={self.directive_type}, "
                f"company_id={self.company_id}, "
                f"status={self.status}, "
                f"progress={self.progress_percent:.0f}%)>")


__all__ = ["Directive"]


