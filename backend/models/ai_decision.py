"""
AI decision queue models.

AI CEOs create decisions now, but organization size determines when those
decisions become executable. This table stores the delayed work.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import validates

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class AIDecisionQueue(Base, TimestampMixin, BaseModel):
    """Queued AI decision with a due turn and execution status."""

    __tablename__ = "ai_decision_queue"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    decision_type = Column(String(30), nullable=False)
    action = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False, default=dict)
    reasoning = Column(Text, nullable=False, default="")
    priority = Column(Integer, nullable=False, default=1)
    target_key = Column(String(120), nullable=False, default="global")

    created_turn = Column(Integer, nullable=False)
    due_turn = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    executed_turn = Column(Integer, nullable=True)
    failure_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ai_decision_game_status_due", "game_id", "status", "due_turn"),
        Index("idx_ai_decision_company_status", "company_id", "status"),
        Index(
            "idx_ai_decision_dedupe",
            "company_id",
            "decision_type",
            "action",
            "target_key",
            "status",
        ),
    )

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        allowed = {"PENDING", "EXECUTED", "FAILED", "CANCELED"}
        value = value.upper()
        if value not in allowed:
            raise ValueError(f"Invalid AI decision status: {value}")
        return value

    def get_parameters(self) -> Dict[str, Any]:
        if isinstance(self.parameters, dict):
            return self.parameters
        if isinstance(self.parameters, str):
            try:
                parsed = json.loads(self.parameters)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def mark_executed(self, turn: int) -> None:
        self.status = "EXECUTED"
        self.executed_turn = turn
        self.failure_reason = None

    def mark_failed(self, turn: int, reason: str) -> None:
        self.status = "FAILED"
        self.executed_turn = turn
        self.failure_reason = reason


__all__ = ["AIDecisionQueue"]
