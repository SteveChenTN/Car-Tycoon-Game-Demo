"""
日志系统配置
为游戏的关键操作提供详细的日志记录
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import colorlog

from backend.config import settings


class GameLogger:
    """游戏日志管理器"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取或创建logger实例
        
        Args:
            name: Logger名称（通常是模块名）
            
        Returns:
            配置好的Logger实例
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        # 避免重复添加handler
        if not logger.handlers:
            # 控制台handler（彩色输出）
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            
            # 彩色格式化器
            color_formatter = colorlog.ColoredFormatter(
                "%(log_color)s[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s%(reset)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_formatter)
            logger.addHandler(console_handler)
            
            # 文件handler（详细日志）
            log_file = settings.LOG_DIR / f"automogul_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            file_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def log_simulation_step(
        cls, 
        logger: logging.Logger, 
        step_name: str, 
        execution_time_ms: float,
        details: Optional[dict] = None
    ) -> None:
        """
        记录模拟步骤的执行情况
        
        Args:
            logger: Logger实例
            step_name: 步骤名称（如"Market Resolution"）
            execution_time_ms: 执行时间（毫秒）
            details: 额外的详细信息
        """
        msg = f"✓ {step_name} completed in {execution_time_ms:.2f}ms"
        
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            msg += f" | {detail_str}"
        
        logger.info(msg)
    
    @classmethod
    def log_game_event(
        cls,
        logger: logging.Logger,
        event_type: str,
        event_data: dict
    ) -> None:
        """
        记录游戏事件
        
        Args:
            logger: Logger实例
            event_type: 事件类型
            event_data: 事件数据
        """
        logger.info(f"📰 EVENT [{event_type}]: {event_data}")
    
    @classmethod
    def log_ai_decision(
        cls,
        logger: logging.Logger,
        company_name: str,
        decision_type: str,
        decision_data: dict
    ) -> None:
        """
        记录AI公司的决策
        
        Args:
            logger: Logger实例
            company_name: 公司名称
            decision_type: 决策类型
            decision_data: 决策数据
        """
        logger.info(f"🤖 AI [{company_name}] {decision_type}: {decision_data}")


def setup_logging() -> None:
    """
    初始化日志系统
    在应用启动时调用
    """
    # 确保日志目录存在
    settings.LOG_DIR.mkdir(exist_ok=True)
    
    # 创建主logger
    main_logger = GameLogger.get_logger("automogul")
    main_logger.info("=" * 80)
    main_logger.info(f"AutoMogul v{settings.VERSION} - Logging System Initialized")
    main_logger.info(f"Log Level: {settings.LOG_LEVEL}")
    main_logger.info(f"Log Directory: {settings.LOG_DIR}")
    main_logger.info("=" * 80)


# 便捷函数
def get_logger(name: str) -> logging.Logger:
    """获取logger的便捷函数"""
    return GameLogger.get_logger(name)


__all__ = ["GameLogger", "setup_logging", "get_logger"]

