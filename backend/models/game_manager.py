"""
游戏管理器模型
用于存储游戏设置、模式、场景等
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from backend.database import Base


class EventLog(Base):
    """
    事件日志
    用于FM风格的滚动新闻ticker
    """
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    turn_number = Column(Integer, nullable=False)
    
    # 事件类型
    event_type = Column(String(50), nullable=False)
    # WORLD_UPDATE, PRODUCTION, MARKET, FINANCE, AI_ACTION, PLAYER_ACTION, NEWS, ALERT
    
    # 事件内容
    message = Column(Text, nullable=False)
    
    # 严重程度
    severity = Column(String(20), default="INFO")
    # INFO, SUCCESS, WARNING, ERROR, CRITICAL
    
    # 关联实体（可选）
    related_company_id = Column(Integer, nullable=True)
    related_region_code = Column(String(10), nullable=True)
    related_vehicle_id = Column(Integer, nullable=True)
    
    # 额外数据（JSON）
    extra_data = Column(JSON, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "turn": self.turn_number,
            "type": self.event_type,
            "message": self.message,
            "severity": self.severity,
            "related_company": self.related_company_id,
            "related_region": self.related_region_code,
            "related_vehicle": self.related_vehicle_id,
            "extra_data": self.extra_data
        }


class GameConfig(Base):
    """
    游戏配置
    存储游戏模式、难度、场景等设置
    """
    __tablename__ = "game_configs"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, unique=True, nullable=False)
    
    # 游戏模式
    mode = Column(String(50), default="SANDBOX")
    # SANDBOX, SCENARIO, CHALLENGE, HISTORICAL
    
    # 难度
    difficulty = Column(String(20), default="NORMAL")
    # EASY, NORMAL, HARD, BRUTAL
    
    # 场景名称（如果是SCENARIO模式）
    scenario_name = Column(String(100), nullable=True)
    
    # 起始年份
    start_year = Column(Integer, default=1950)
    
    # 结束年份（沙盒模式为NULL）
    end_year = Column(Integer, nullable=True)
    
    # 胜利条件（JSON）
    victory_conditions = Column(JSON, nullable=True)
    # 例如: {"market_share_global": 0.15, "prestige_score": 80}
    
    # 失败条件
    failure_conditions = Column(JSON, nullable=True)
    # 例如: {"bankruptcy": true, "max_debt": 1000000000}
    
    # 难度修正系数（JSON）
    difficulty_modifiers = Column(JSON, default={
        "starting_cash_multiplier": 1.0,
        "revenue_multiplier": 1.0,
        "cost_multiplier": 1.0,
        "ai_aggression_multiplier": 1.0,
        "random_event_frequency": 1.0,
        "recall_probability_multiplier": 1.0
    })
    
    # 启用的特性
    enabled_features = Column(JSON, default={
        "recalls": True,
        "espionage": False,
        "f1_racing": False,
        "merger_acquisition": False
    })
    
    # 是否允许存档
    allow_saves = Column(Boolean, default=True)
    
    # 是否启用铁人模式（单存档）
    ironman_mode = Column(Boolean, default=False)
    
    def to_dict(self):
        return {
            "game_id": self.game_id,
            "mode": self.mode,
            "difficulty": self.difficulty,
            "scenario": self.scenario_name,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "victory_conditions": self.victory_conditions,
            "failure_conditions": self.failure_conditions,
            "modifiers": self.difficulty_modifiers,
            "features": self.enabled_features,
            "ironman": self.ironman_mode
        }
    
    def apply_difficulty_modifiers(self, base_value: float, modifier_key: str) -> float:
        """
        应用难度修正
        
        Args:
            base_value: 基础值
            modifier_key: 修正键名（例如 'cost_multiplier'）
        
        Returns:
            修正后的值
        """
        if not self.difficulty_modifiers:
            return base_value
        
        multiplier = self.difficulty_modifiers.get(modifier_key, 1.0)
        return base_value * multiplier
    
    def check_victory_conditions(self, game_state_data: dict) -> bool:
        """
        检查是否达成胜利条件
        
        Args:
            game_state_data: 游戏状态数据字典
        
        Returns:
            是否胜利
        """
        if not self.victory_conditions:
            return False
        
        # 检查所有条件是否满足
        for condition_key, target_value in self.victory_conditions.items():
            current_value = game_state_data.get(condition_key, 0)
            
            if current_value < target_value:
                return False
        
        return True
    
    def check_failure_conditions(self, game_state_data: dict) -> bool:
        """
        检查是否触发失败条件
        
        Args:
            game_state_data: 游戏状态数据字典
        
        Returns:
            是否失败
        """
        if not self.failure_conditions:
            return False
        
        # 任意一个失败条件触发即失败
        for condition_key, trigger_value in self.failure_conditions.items():
            current_value = game_state_data.get(condition_key, False)
            
            if condition_key == "bankruptcy" and current_value is True:
                return True
            
            if condition_key == "max_debt" and current_value > trigger_value:
                return True
        
        return False


__all__ = ["EventLog", "GameConfig"]
