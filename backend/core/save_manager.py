"""
存档管理器 - 支持多存档和动态数据库切换
核心职责：
1. 管理 /saves/ 目录下的所有存档文件
2. 提供动态数据库连接切换能力
3. 处理存档的创建、加载、列表、删除
"""
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging
import shutil
import uuid
from datetime import datetime
import sqlite3

from backend.config import settings
from backend.database import Base

logger = logging.getLogger(__name__)


# =============================================================================
# 全局状态：当前会话引擎（None = 未加载任何存档）
# =============================================================================

class GameSessionManager:
    """
    游戏会话管理器 - 单例模式
    负责管理当前活动的数据库引擎
    """
    
    _instance: Optional['GameSessionManager'] = None
    _current_engine = None
    _current_session_factory = None
    _current_save_path: Optional[Path] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_current_engine(cls):
        """获取当前引擎"""
        instance = cls()
        return instance._current_engine
    
    @classmethod
    def get_current_session_factory(cls):
        """获取当前会话工厂"""
        instance = cls()
        return instance._current_session_factory
    
    @classmethod
    def is_game_loaded(cls) -> bool:
        """检查是否有游戏被加载"""
        instance = cls()
        return instance._current_engine is not None
    
    @classmethod
    def get_current_save_path(cls) -> Optional[Path]:
        """获取当前存档路径"""
        instance = cls()
        return instance._current_save_path
    
    @classmethod
    def connect_to_save(cls, save_path: Path) -> bool:
        """
        连接到指定的存档文件
        
        Args:
            save_path: 存档文件路径
            
        Returns:
            是否成功连接
        """
        instance = cls()
        
        try:
            # 如果已有连接，先断开
            if instance._current_engine:
                logger.info(f"断开当前存档: {instance._current_save_path}")
                instance._current_engine.dispose()
            
            # 验证文件存在
            if not save_path.exists():
                logger.error(f"存档文件不存在: {save_path}")
                return False
            
            # 创建新引擎
            database_url = f"sqlite:///{save_path}"
            engine = create_engine(
                database_url,
                echo=settings.DATABASE_ECHO,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            
            # 启用SQLite外键约束
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
            
            # 确保所有表存在（自动迁移）
            # 导入所有模型以确保它们被注册到 Base.metadata
            import backend.models  # noqa: F401
            Base.metadata.create_all(bind=engine, checkfirst=True)
            
            # 创建会话工厂
            session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            )
            
            # 更新全局状态
            instance._current_engine = engine
            instance._current_session_factory = session_factory
            instance._current_save_path = save_path
            
            logger.info(f"✓ 已连接到存档: {save_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"连接存档失败: {e}", exc_info=True)
            instance._current_engine = None
            instance._current_session_factory = None
            instance._current_save_path = None
            return False
    
    @classmethod
    def disconnect(cls) -> None:
        """断开当前数据库连接"""
        instance = cls()
        
        if instance._current_engine:
            logger.info(f"断开存档: {instance._current_save_path}")
            instance._current_engine.dispose()
        
        instance._current_engine = None
        instance._current_session_factory = None
        instance._current_save_path = None


# =============================================================================
# 依赖注入函数（替代原来的 get_db）
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    
    如果没有加载游戏，会抛出 RuntimeError
    用于 FastAPI 的 Depends()
    """
    if not GameSessionManager.is_game_loaded():
        raise RuntimeError("NO_GAME_LOADED")
    
    session_factory = GameSessionManager.get_current_session_factory()
    if not session_factory:
        raise RuntimeError("SESSION_FACTORY_NOT_INITIALIZED")
    
    db = session_factory()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


# =============================================================================
# 存档管理器
# =============================================================================

class SaveManager:
    """
    存档管理器
    处理存档文件的创建、复制、列表、删除
    """
    
    def __init__(self, saves_directory: Optional[Path] = None):
        """
        初始化存档管理器
        
        Args:
            saves_directory: 存档目录路径，默认为 data/saves/
        """
        if saves_directory is None:
            self.saves_dir = settings.DATA_DIR / "saves"
        else:
            self.saves_dir = Path(saves_directory)
        
        # 确保存档目录存在
        self.saves_dir.mkdir(parents=True, exist_ok=True)
        
        # 模板数据库路径
        self.template_db_path = settings.DATA_DIR / "template.db"
    
    def list_saves(self) -> List[Dict[str, Any]]:
        """
        列出所有存档文件
        
        Returns:
            存档信息列表，每个元素包含：
            - file_name: 文件名
            - file_path: 完整路径
            - size_mb: 文件大小（MB）
            - created_time: 创建时间
            - modified_time: 修改时间
            - player_name: 玩家公司名称（从DB读取）
            - game_year: 游戏年份
            - turn_number: 回合数
        """
        saves = []
        
        for save_file in self.saves_dir.glob("*.db"):
            try:
                # 基本文件信息
                stat = save_file.stat()
                info: Dict[str, Any] = {
                    "file_name": save_file.name,
                    "file_path": str(save_file),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
                
                # 尝试读取游戏状态信息
                try:
                    conn = sqlite3.connect(str(save_file))
                    cursor = conn.cursor()
                    
                    # 读取游戏状态
                    cursor.execute("""
                        SELECT current_year, turn_number, difficulty 
                        FROM game_state 
                        LIMIT 1
                    """)
                    game_row = cursor.fetchone()
                    
                    if game_row:
                        info["game_year"] = game_row[0]
                        info["turn_number"] = game_row[1]
                        info["difficulty"] = game_row[2]
                    
                    # 读取玩家公司名称
                    # 注意：表名是 companies（复数），但为了向后兼容，先尝试 companies，再尝试 company
                    player_row = None
                    try:
                        cursor.execute("""
                            SELECT name, cash, prestige_score 
                            FROM companies 
                            WHERE is_player = 1 
                            LIMIT 1
                        """)
                        player_row = cursor.fetchone()
                    except sqlite3.OperationalError:
                        # 如果 companies 表不存在，尝试 company（旧版本可能使用）
                        try:
                            cursor.execute("""
                                SELECT name, cash, prestige_score 
                                FROM company 
                                WHERE is_player = 1 
                                LIMIT 1
                            """)
                            player_row = cursor.fetchone()
                        except sqlite3.OperationalError:
                            # 两个表都不存在，跳过
                            pass
                    
                    if player_row:
                        info["player_name"] = player_row[0]
                        info["player_cash"] = player_row[1]
                        info["player_prestige"] = player_row[2]
                    
                    conn.close()
                    
                except Exception as db_err:
                    # 只记录警告，不设置 error 字段，允许继续使用基本文件信息
                    logger.warning(f"无法读取存档元数据 {save_file.name}: {db_err}")
                
                saves.append(info)
                
            except Exception as e:
                logger.error(f"读取存档文件失败 {save_file}: {e}")
        
        # 按修改时间倒序排序
        saves.sort(key=lambda x: x.get("modified_time", ""), reverse=True)
        return saves
    
    def create_new_save(
        self, 
        save_name: Optional[str] = None,
        use_template: bool = True
    ) -> Dict[str, Any]:
        """
        创建新存档文件
        
        Args:
            save_name: 存档名称（可选，会生成UUID）
            use_template: 是否从模板复制（True=复制模板，False=创建空DB）
            
        Returns:
            结果字典，包含：
            - success: 是否成功
            - save_path: 存档路径
            - error: 错误信息（如果失败）
        """
        try:
            # 生成存档文件名
            if save_name:
                # 清理文件名
                clean_name = "".join(
                    c for c in save_name 
                    if c.isalnum() or c in (' ', '-', '_')
                ).strip()
                file_name = f"{clean_name}_{uuid.uuid4().hex[:8]}.db"
            else:
                file_name = f"save_{uuid.uuid4().hex}.db"
            
            save_path = self.saves_dir / file_name
            
            if use_template:
                # 从模板复制
                if not self.template_db_path.exists():
                    return {
                        "success": False,
                        "error": "TEMPLATE_NOT_FOUND",
                        "message": f"模板数据库不存在: {self.template_db_path}"
                    }
                
                shutil.copy2(self.template_db_path, save_path)
                logger.info(f"从模板创建存档: {save_path.name}")
            else:
                # 创建空数据库（只有表结构）
                from backend.database import Base
                
                temp_engine = create_engine(
                    f"sqlite:///{save_path}",
                    echo=False
                )
                Base.metadata.create_all(bind=temp_engine)
                temp_engine.dispose()
                logger.info(f"创建空白存档: {save_path.name}")
            
            return {
                "success": True,
                "save_path": str(save_path),
                "file_name": file_name
            }
            
        except Exception as e:
            logger.error(f"创建存档失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_save(self, save_path: str) -> Dict[str, Any]:
        """
        删除存档文件
        
        Args:
            save_path: 存档文件路径
            
        Returns:
            结果字典
        """
        try:
            path = Path(save_path)
            
            # 安全检查：确保文件在saves目录内
            if not path.is_relative_to(self.saves_dir):
                return {
                    "success": False,
                    "error": "INVALID_PATH",
                    "message": "只能删除 saves 目录内的文件"
                }
            
            if not path.exists():
                return {
                    "success": False,
                    "error": "FILE_NOT_FOUND"
                }
            
            # 如果是当前加载的存档，先断开
            current_save = GameSessionManager.get_current_save_path()
            if current_save and current_save == path:
                GameSessionManager.disconnect()
                logger.info("已断开当前存档连接")
            
            path.unlink()
            logger.info(f"存档已删除: {path.name}")
            
            return {
                "success": True,
                "message": "存档删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除存档失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def ensure_template_exists(self) -> bool:
        """
        确保模板数据库存在
        如果不存在，则创建一个只包含表结构的空白数据库
        
        Returns:
            是否成功
        """
        try:
            if self.template_db_path.exists():
                logger.info(f"模板数据库已存在: {self.template_db_path}")
                return True
            
            logger.info("创建模板数据库...")
            
            from backend.database import Base
            
            # ⚠️ 关键：必须导入所有模型，否则 Base.metadata 不会包含所有表
            # 这会触发所有模型类的注册
            import backend.models  # noqa: F401
            
            # 创建临时引擎
            temp_engine = create_engine(
                f"sqlite:///{self.template_db_path}",
                echo=False
            )
            
            # 启用外键约束
            @event.listens_for(temp_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
            
            # 创建所有表
            Base.metadata.create_all(bind=temp_engine)
            temp_engine.dispose()
            
            logger.info(f"✓ 模板数据库创建成功: {self.template_db_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建模板数据库失败: {e}", exc_info=True)
            return False


__all__ = [
    "GameSessionManager",
    "SaveManager",
    "get_db"
]

