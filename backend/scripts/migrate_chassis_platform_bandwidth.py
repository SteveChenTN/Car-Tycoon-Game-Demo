"""
数据库迁移脚本 - 添加底盘平台带宽字段
为chassis表添加base_wheelbase_mm、bandwidth_wheelbase_mm、base_track_width_mm、bandwidth_track_mm字段
"""
import sys
import os
import sqlite3

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from backend.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def migrate_chassis_table(db_path: str = None):
    """为chassis表添加平台带宽字段"""
    if db_path is None:
        db_path = os.path.join(project_root, "data", "automogul.db")
    
    if not os.path.exists(db_path):
        logger.info(f"数据库不存在于 {db_path}，将在首次运行时自动创建")
        return True
    
    logger.info(f"开始迁移数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查chassis表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chassis'"
        )
        if not cursor.fetchone():
            logger.info("✓ chassis表不存在，将在首次运行时自动创建")
            conn.close()
            return True
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(chassis)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        logger.info(f"发现 {len(existing_columns)} 个现有列")
        
        # 定义需要添加的列（平台带宽字段）
        columns_to_add = [
            ("base_wheelbase_mm", "INTEGER"),
            ("bandwidth_wheelbase_mm", "INTEGER"),
            ("base_track_width_mm", "INTEGER"),
            ("bandwidth_track_mm", "INTEGER"),
        ]
        
        added_count = 0
        for column_name, column_def in columns_to_add:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE chassis ADD COLUMN {column_name} {column_def}")
                    logger.info(f"  ✓ 添加列: {column_name}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column" in str(e).lower():
                        logger.info(f"  - 列 {column_name} 已存在，跳过")
                    else:
                        logger.warning(f"  ⚠ 添加列 {column_name} 时出错: {e}")
            else:
                logger.info(f"  - 列 {column_name} 已存在，跳过")
        
        conn.commit()
        logger.info(f"\n✓ 迁移完成！添加了 {added_count} 个新列")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("底盘平台带宽字段迁移")
    logger.info("=" * 80)
    
    # 迁移主数据库
    main_db_path = os.path.join(project_root, "data", "automogul.db")
    success1 = migrate_chassis_table(main_db_path)
    
    # 迁移模板数据库
    template_db_path = os.path.join(project_root, "data", "template.db")
    success2 = migrate_chassis_table(template_db_path)
    
    # 迁移所有存档数据库
    saves_dir = os.path.join(project_root, "data", "saves")
    if os.path.exists(saves_dir):
        import glob
        save_files = glob.glob(os.path.join(saves_dir, "*.db"))
        logger.info(f"\n发现 {len(save_files)} 个存档文件，开始迁移...")
        for save_file in save_files:
            logger.info(f"迁移存档: {os.path.basename(save_file)}")
            migrate_chassis_table(save_file)
    
    success = success1 and success2
    sys.exit(0 if success else 1)


