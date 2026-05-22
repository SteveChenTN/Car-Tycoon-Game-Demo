"""
游戏状态和时间系统模型
"""
from sqlalchemy import Column, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from typing import Tuple, Dict, Any, Optional
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel
from backend.config import GameConstants


class GameState(Base, TimestampMixin, BaseModel):
    """
    游戏状态表
    记录游戏的全局信息和当前时间
    """
    __tablename__ = "game_state"
    
    id = Column(Integer, primary_key=True, index=True)
    save_name = Column(String(255), nullable=False, comment="存档名称")
    
    # 时间系统 (Weekly-based)
    current_year = Column(
        Integer, 
        nullable=False, 
        default=GameConstants.STARTING_YEAR,
        comment="当前年份"
    )
    current_month = Column(
        Integer,
        nullable=False,
        default=GameConstants.STARTING_MONTH,
        comment="当前月份 (1-12)"
    )
    current_week = Column(
        Integer,
        nullable=False,
        default=GameConstants.STARTING_WEEK,
        comment="当前周数 (1-4)"
    )
    turn_number = Column(
        Integer,
        nullable=False,
        default=0,
        comment="回合数（从0开始）"
    )
    
    # 游戏配置
    difficulty = Column(
        String(20),
        nullable=False,
        default="normal",
        comment="难度: easy/normal/hard/brutal"
    )
    simulation_speed = Column(
        String(20),
        nullable=False,
        default="weekly",
        comment="模拟速度: weekly/monthly"
    )
    random_seed = Column(
        Integer,
        nullable=True,
        comment="随机数种子（可选）"
    )
    
    # R&D管理器状态（存储所有公司的R&D状态）
    # 格式: {company_id: {departments: {...}, ...}, ...}
    rd_manager_state = Column(
        JSON,
        nullable=True,
        comment="R&D管理器状态（JSON）- 存储所有公司的研发部门状态和活跃项目"
    )
    
    # 关系
    regions = relationship("Region", back_populates="game", cascade="all, delete-orphan")
    
    def advance_turn(self) -> None:
        """
        推进一个回合
        根据simulation_speed更新时间
        """
        self.turn_number += 1
        
        if self.simulation_speed == "weekly":
            self._advance_week()
        elif self.simulation_speed == "monthly":
            self._advance_month()
    
    def _advance_week(self) -> None:
        """推进一周"""
        self.current_week += 1
        
        if self.current_week > GameConstants.WEEKS_PER_MONTH:
            self.current_week = 1
            self._advance_month()
    
    def _advance_month(self) -> None:
        """推进一个月"""
        self.current_month += 1
        
        if self.current_month > GameConstants.MONTHS_PER_YEAR:
            self.current_month = 1
            self.current_year += 1
    
    def get_current_date(self) -> Tuple[int, int, int]:
        """
        获取当前游戏日期
        
        Returns:
            (year, month, week)
        """
        return (self.current_year, self.current_month, self.current_week)
    
    def get_date_string(self) -> str:
        """
        获取格式化的日期字符串
        
        Returns:
            格式化日期，如 "1950-01-W1"
        """
        return f"{self.current_year}-{self.current_month:02d}-W{self.current_week}"
    
    def get_total_weeks_elapsed(self) -> int:
        """
        计算从游戏开始经过的总周数
        
        Returns:
            总周数
        """
        years_elapsed = self.current_year - GameConstants.STARTING_YEAR
        months_elapsed = years_elapsed * 12 + (self.current_month - GameConstants.STARTING_MONTH)
        weeks_elapsed = months_elapsed * 4 + (self.current_week - GameConstants.STARTING_WEEK)
        return weeks_elapsed
    
    def get_rd_manager_state_for_company(self, company_id: int) -> Optional[Dict[str, Any]]:
        """
        获取指定公司的R&D管理器状态
        
        Args:
            company_id: 公司ID
            
        Returns:
            R&D状态字典，如果不存在则返回None
        """
        if not self.rd_manager_state:
            return None
        
        return self.rd_manager_state.get(str(company_id))
    
    def set_rd_manager_state_for_company(self, company_id: int, state: Dict[str, Any]) -> None:
        """
        设置指定公司的R&D管理器状态
        
        Args:
            company_id: 公司ID
            state: R&D状态字典
        """
        if not self.rd_manager_state:
            self.rd_manager_state = {}
        
        self.rd_manager_state[str(company_id)] = state


__all__ = ["GameState"]

