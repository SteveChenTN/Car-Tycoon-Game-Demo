"""
修复数据库架构：添加缺失的Region字段
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from backend.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


def fix_regions_table():
    """为regions表添加缺失的列"""
    db_path = project_root / "data" / "automogul.db"
    
    if not db_path.exists():
        logger.info(f"Database not found at {db_path}, creating new one...")
        return True
    
    logger.info(f"Fixing database schema at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查regions表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='regions'"
        )
        if not cursor.fetchone():
            logger.info("✓ regions table doesn't exist yet, no fix needed")
            conn.close()
            return True
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(regions)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        logger.info(f"Found {len(existing_columns)} existing columns in regions table")
        
        # 定义需要添加的列
        columns_to_add = [
            ("allow_used_export", "BOOLEAN NOT NULL DEFAULT 1"),
            ("allow_used_import", "BOOLEAN NOT NULL DEFAULT 1"),
        ]
        
        added_count = 0
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                logger.info(f"Adding column: {col_name}")
                cursor.execute(
                    f"ALTER TABLE regions ADD COLUMN {col_name} {col_type}"
                )
                added_count += 1
            else:
                logger.info(f"✓ Column already exists: {col_name}")
        
        conn.commit()
        
        if added_count > 0:
            logger.info(f"✅ Successfully added {added_count} columns to regions table")
        else:
            logger.info("✓ All columns already exist, no changes needed")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix schema: {e}", exc_info=True)
        conn.rollback()
        return False
        
    finally:
        conn.close()


def main():
    """主函数"""
    setup_logging()
    
    logger.info("=" * 80)
    logger.info("Database Schema Fix Tool")
    logger.info("=" * 80)
    
    if fix_regions_table():
        logger.info("\n" + "=" * 80)
        logger.info("✅ Schema fix completed successfully!")
        logger.info("=" * 80)
        logger.info("You can now run init_world.py to initialize the game")
    else:
        logger.error("\n" + "=" * 80)
        logger.error("❌ Schema fix failed!")
        logger.error("=" * 80)
        logger.error("Consider deleting the database and starting fresh")
        sys.exit(1)


if __name__ == "__main__":
    main()


