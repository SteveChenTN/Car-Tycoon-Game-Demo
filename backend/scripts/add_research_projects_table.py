"""
迁移脚本：添加 research_projects 表
用于更新现有数据库，添加新的 ResearchProject 模型表
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from backend.database import Base
from backend.models import ResearchProject  # 确保模型被导入
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_research_projects_table(db_path: str) -> bool:
    """
    为现有数据库添加 research_projects 表
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        是否成功
    """
    try:
        engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False
        )
        
        # 检查表是否已存在
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='research_projects'"
            ))
            if result.fetchone():
                logger.info(f"表 research_projects 已存在于 {db_path}")
                return True
        
        # 创建表
        logger.info(f"正在为 {db_path} 添加 research_projects 表...")
        Base.metadata.create_all(bind=engine, tables=[ResearchProject.__table__])
        
        logger.info(f"✓ 成功添加 research_projects 表到 {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"添加表失败: {e}", exc_info=True)
        return False
    finally:
        engine.dispose()


def migrate_all_saves():
    """迁移所有存档文件"""
    from backend.config import settings
    
    saves_dir = Path(settings.SAVES_DIRECTORY)
    template_db_path = Path(settings.TEMPLATE_DB_PATH)
    
    # 迁移模板数据库
    if template_db_path.exists():
        logger.info(f"迁移模板数据库: {template_db_path}")
        add_research_projects_table(str(template_db_path))
    
    # 迁移所有存档
    if saves_dir.exists():
        save_files = list(saves_dir.glob("*.db"))
        logger.info(f"找到 {len(save_files)} 个存档文件")
        
        for save_file in save_files:
            logger.info(f"迁移存档: {save_file.name}")
            add_research_projects_table(str(save_file))
    
    logger.info("✓ 所有数据库迁移完成")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="添加 research_projects 表到数据库")
    parser.add_argument(
        "--db-path",
        type=str,
        help="要迁移的数据库文件路径（如果未指定，则迁移所有存档）"
    )
    
    args = parser.parse_args()
    
    if args.db_path:
        # 迁移单个数据库
        success = add_research_projects_table(args.db_path)
        sys.exit(0 if success else 1)
    else:
        # 迁移所有存档
        migrate_all_saves()


