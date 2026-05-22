"""
创建模板数据库
生成一个只包含表结构的空白数据库，用于多存档系统
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.core.save_manager import SaveManager
from backend.utils.logger import setup_logging, get_logger

# 初始化日志
setup_logging()
logger = get_logger(__name__)


def create_template_database():
    """
    创建模板数据库
    """
    logger.info("=" * 80)
    logger.info("创建模板数据库")
    logger.info("=" * 80)
    
    save_mgr = SaveManager()
    
    if save_mgr.ensure_template_exists():
        logger.info(f"✓ 模板数据库创建成功: {save_mgr.template_db_path}")
        logger.info("")
        logger.info("模板数据库包含以下表结构：")
        
        # 列出所有表
        import sqlite3
        conn = sqlite3.connect(str(save_mgr.template_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        conn.close()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ 完成！")
        logger.info("=" * 80)
        return True
    else:
        logger.error("❌ 模板数据库创建失败")
        return False


if __name__ == "__main__":
    success = create_template_database()
    sys.exit(0 if success else 1)


