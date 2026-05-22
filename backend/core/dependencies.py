"""
FastAPI 依赖注入和中间件
包含游戏加载状态检查的守卫
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Generator
import logging

from backend.core.save_manager import GameSessionManager, get_db as base_get_db

logger = logging.getLogger(__name__)


# =============================================================================
# 依赖守卫：确保游戏已加载
# =============================================================================

def require_game_loaded(db: Session = Depends(base_get_db)) -> Session:
    """
    依赖守卫：确保游戏已加载
    
    如果没有加载游戏，返回 403 Forbidden
    用于所有需要游戏状态的端点
    
    使用示例：
    @router.get("/market/data")
    async def get_market(db: Session = Depends(require_game_loaded)):
        # 此处可以安全地访问数据库
        pass
    """
    if not GameSessionManager.is_game_loaded():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "NO_GAME_LOADED",
                "message": "请先创建或加载游戏存档",
                "action": "请使用 POST /api/v1/game/new 创建新游戏，或 POST /api/v1/game/load 加载存档"
            }
        )
    
    return db


def get_db_optional() -> Generator[Session | None, None, None]:
    """
    可选数据库会话
    
    如果没有加载游戏，返回 None 而不是抛出异常
    用于可以在"无游戏"状态下工作的端点（如列表存档）
    """
    if not GameSessionManager.is_game_loaded():
        yield None
        return
    
    # 如果已加载，返回正常会话
    for session in base_get_db():
        yield session


# =============================================================================
# 辅助函数
# =============================================================================

def is_game_loaded() -> bool:
    """
    检查游戏是否已加载
    
    可在路由函数内部使用进行条件判断
    """
    return GameSessionManager.is_game_loaded()


def get_current_save_info() -> dict:
    """
    获取当前加载的存档信息
    
    Returns:
        存档信息字典，如果未加载则返回空字典
    """
    if not GameSessionManager.is_game_loaded():
        return {
            "loaded": False,
            "save_path": None
        }
    
    return {
        "loaded": True,
        "save_path": str(GameSessionManager.get_current_save_path())
    }


__all__ = [
    "require_game_loaded",
    "get_db_optional",
    "is_game_loaded",
    "get_current_save_info"
]


