"""
游戏全局配置
所有魔法数字都应在此定义，而非硬编码在逻辑中
"""
from typing import Dict, Any
from pathlib import Path
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置"""
    
    # 应用基础信息
    APP_NAME: str = "AutoMogul"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 游戏根目录（必须在DATABASE_URL之前定义）
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    # 数据库配置
    # 使用绝对路径，基于BASE_DIR（backend目录的父目录，即项目根目录）
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'automogul.db'}"
    DATABASE_ECHO: bool = False  # SQL 日志
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("logs")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 实例化配置
settings = Settings()

# 确保必要目录存在
settings.DATA_DIR.mkdir(exist_ok=True)
settings.LOG_DIR.mkdir(exist_ok=True)


# =============================================================================
# 游戏常量配置
# =============================================================================

class GameConstants:
    """游戏核心常量"""
    
    # 时间系统
    STARTING_YEAR: int = 1950
    STARTING_MONTH: int = 1
    STARTING_WEEK: int = 1
    WEEKS_PER_MONTH: int = 4
    MONTHS_PER_YEAR: int = 12
    
    # 地区代码
    REGION_CODES = {
        "NAM": "North America",
        "EUR": "Europe", 
        "ASI": "Asia-Pacific",
        "LAM": "Latin America",
        "MEA": "Middle East & Africa"
    }
    
    # 货币基准（游戏内货币单位）
    BASE_CURRENCY_NAME: str = "Credits"
    
    # 模拟速度
    SIMULATION_SPEEDS = ["weekly", "monthly"]
    
    # 难度等级
    DIFFICULTY_LEVELS = ["easy", "normal", "hard", "brutal"]


class EconomicConstants:
    """经济系统常量"""
    
    # GDP 基准
    BASE_GDP_PER_CAPITA_1950: float = 1500.0  # 1950年基准
    
    # 通货膨胀
    BASE_INFLATION_RATE: float = 0.03  # 3%
    
    # 失业率影响
    UNEMPLOYMENT_DEMAND_IMPACT: float = -0.5  # 失业率每增加1%，需求降低0.5%
    
    # 购买力指数基准
    PURCHASING_POWER_BASE: float = 1.0


class MarketConstants:
    """市场系统常量"""
    
    # 汽车保有量（每千人）
    BASE_CAR_OWNERSHIP_RATE: Dict[str, float] = {
        "NAM": 350.0,  # 北美：高
        "EUR": 250.0,  # 欧洲：中高
        "ASI": 50.0,   # 亚洲：低
        "LAM": 120.0,  # 拉美：中
        "MEA": 80.0    # 中东非：低
    }
    
    # 车辆平均使用年限
    AVG_VEHICLE_LIFETIME_YEARS: float = 12.0
    
    # 消费者效用权重（默认）
    DEFAULT_UTILITY_WEIGHTS = {
        "price": 0.25,
        "performance": 0.15,
        "comfort": 0.15,
        "reliability": 0.15,
        "safety": 0.10,
        "prestige": 0.10,
        "efficiency": 0.05,
        "practicality": 0.05
    }
    
    # 价格敏感度
    PRICE_ELASTICITY: float = -1.2  # 价格每提高1%，需求降低1.2%


class EngineeringConstants:
    """工程/技术常量"""
    
    # 基础研发成本（百万游戏币）
    BASE_RD_COST_PLATFORM: float = 500.0
    BASE_RD_COST_ENGINE: float = 200.0
    BASE_RD_COST_TECH: float = 50.0
    
    # 研发时间（周）
    BASE_RD_TIME_PLATFORM_WEEKS: int = 156  # ~3年
    BASE_RD_TIME_ENGINE_WEEKS: int = 104    # ~2年
    BASE_RD_TIME_TECH_WEEKS: int = 52       # ~1年
    
    # 质量分数基准
    QUALITY_SCORE_MIN: float = 0.0
    QUALITY_SCORE_MAX: float = 100.0
    QUALITY_SCORE_TARGET: float = 70.0  # 行业标准


class ProductionConstants:
    """生产系统常量"""
    
    # 工厂建设成本（百万游戏币）
    FACTORY_BUILD_COST_PER_UNIT_CAPACITY: float = 0.5
    
    # 工厂建设时间（周）
    FACTORY_BUILD_TIME_WEEKS: int = 104  # ~2年
    
    # 生产效率
    BASE_PRODUCTION_EFFICIENCY: float = 0.80  # 80%利用率
    
    # 材料成本（相对值）
    MATERIAL_COST_STEEL_KG: float = 0.5
    MATERIAL_COST_ALUMINUM_KG: float = 2.0
    MATERIAL_COST_PLASTICS_KG: float = 1.2


# 导出配置实例
__all__ = [
    "settings",
    "GameConstants",
    "EconomicConstants", 
    "MarketConstants",
    "EngineeringConstants",
    "ProductionConstants"
]

