"""
数据库连接和会话管理
重构说明：
- 移除静态 engine 和 SessionLocal
- 改用动态会话管理器（见 backend.core.save_manager）
- 保留 Base 类供模型继承
"""
from sqlalchemy.orm import DeclarativeBase
import logging

logger = logging.getLogger(__name__)


# SQLAlchemy 2.0 风格的基类
class Base(DeclarativeBase):
    """所有ORM模型的基类"""
    pass


# =============================================================================
# 向后兼容的辅助函数
# =============================================================================

def get_db():
    """
    已废弃：请直接从 backend.core.save_manager 导入 get_db
    
    此函数保留用于向后兼容，但会重定向到新实现
    注意：这是一个 generator 函数，FastAPI 的 Depends() 会自动处理
    """
    from backend.core.save_manager import get_db as new_get_db
    yield from new_get_db()


def init_db() -> None:
    """
    已废弃：数据库初始化现在由 SaveManager 处理
    
    保留此函数用于向后兼容
    """
    logger.warning("init_db() 已废弃。数据库由 SaveManager 动态管理。")
    logger.info("如果需要创建模板数据库，请使用 SaveManager.ensure_template_exists()")


def drop_all_tables() -> None:
    """
    已废弃：表管理现在由 SaveManager 处理
    """
    logger.error("drop_all_tables() 已废弃。请使用存档管理系统。")
    raise NotImplementedError(
        "此功能已被禁用。请通过 SaveManager 管理存档文件。"
    )


__all__ = [
    "Base",
    "get_db",  # 向后兼容
    "init_db",  # 向后兼容
    "drop_all_tables"  # 向后兼容
]

