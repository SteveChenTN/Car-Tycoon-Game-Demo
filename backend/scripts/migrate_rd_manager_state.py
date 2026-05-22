"""
数据库迁移：添加 rd_manager_state 字段到 game_state 表

执行此脚本来添加 R&D 管理器状态字段
"""
import sys
import os
import sqlite3
from pathlib import Path
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_game_state_table(db_path: str) -> bool:
    """
    迁移 game_state 表，添加 rd_manager_state 字段
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        是否成功
    """
    if not os.path.exists(db_path):
        logger.warning(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(game_state)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "rd_manager_state" in columns:
            logger.info(f"  ✓ {db_path}: rd_manager_state 字段已存在，跳过")
            conn.close()
            return True
        
        # 添加新列
        logger.info(f"  添加 rd_manager_state 字段到 game_state 表...")
        cursor.execute("""
            ALTER TABLE game_state 
            ADD COLUMN rd_manager_state TEXT
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"  ✓ {db_path}: 迁移成功")
        return True
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info(f"  ✓ {db_path}: 字段已存在（重复迁移）")
            return True
        logger.error(f"  ✗ {db_path}: 迁移失败 - {e}")
        return False
    except Exception as e:
        logger.error(f"  ✗ {db_path}: 迁移失败 - {e}", exc_info=True)
        return False


def migrate_all_databases():
    """迁移所有数据库文件"""
    from backend.core.save_manager import SaveManager
    
    save_mgr = SaveManager()
    databases_to_migrate = []
    
    # 1. 当前活动的数据库
    try:
        from backend.core.save_manager import GameSessionManager
        current_save_path = GameSessionManager.get_current_save_path()
        if current_save_path and current_save_path.exists():
            databases_to_migrate.append(("当前存档", str(current_save_path)))
    except:
        pass
    
    # 2. 模板数据库
    if save_mgr.template_db_path.exists():
        databases_to_migrate.append(("模板数据库", str(save_mgr.template_db_path)))
    
    # 3. 主数据库
    main_db_path = project_root / "data" / "automogul.db"
    if main_db_path.exists():
        databases_to_migrate.append(("主数据库", str(main_db_path)))
    
    # 4. 所有存档文件
    if save_mgr.saves_dir.exists():
        for save_file in save_mgr.saves_dir.glob("*.db"):
            if str(save_file) not in [db[1] for db in databases_to_migrate]:
                databases_to_migrate.append((f"存档: {save_file.name}", str(save_file)))
    
    if not databases_to_migrate:
        logger.warning("找不到任何数据库文件，仅迁移默认数据库")
        default_db = project_root / "data" / "automogul.db"
        if default_db.exists():
            databases_to_migrate.append(("默认数据库", str(default_db)))
        else:
            logger.error("默认数据库也不存在")
            return False
    
    logger.info("=" * 80)
    logger.info("开始迁移：添加 rd_manager_state 字段")
    logger.info("=" * 80)
    
    success_count = 0
    for db_name, db_path in databases_to_migrate:
        logger.info(f"\n迁移: {db_name}")
        if migrate_game_state_table(db_path):
            success_count += 1
    
    logger.info(f"\n迁移完成: {success_count}/{len(databases_to_migrate)} 个数据库成功")
    return success_count == len(databases_to_migrate)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="迁移 game_state 表，添加 rd_manager_state 字段")
    parser.add_argument(
        "--db",
        type=str,
        help="指定要迁移的数据库文件路径（如果不指定，则迁移所有数据库）"
    )
    
    args = parser.parse_args()
    
    if args.db:
        # 迁移单个数据库
        success = migrate_game_state_table(args.db)
        sys.exit(0 if success else 1)
    else:
        # 迁移所有数据库
        success = migrate_all_databases()
        sys.exit(0 if success else 1)


