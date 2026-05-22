"""
数据库迁移：添加底盘深度工程字段
Database Migration: Add Chassis Depth Engineering Fields

添加7个新工程维度的字段：
- 物理结构组 (Rigidity/Corrosion/NVH)
- 包装与安全组 (Packaging/Safety)
- 制造与供应链组 (Manufacturing/Supply Chain)
- 认证组 (Homologation/Regulations)

执行方式：
    python backend/scripts/migrate_chassis_depth_fields.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_database(db_path: str = None):
    """
    执行底盘深度字段迁移
    
    Args:
        db_path: 数据库文件路径，如果为None则使用默认路径
    """
    if db_path is None:
        db_path = "data/automogul.db"
    
    logger.info("=" * 80)
    logger.info("开始数据库迁移：底盘深度工程字段")
    logger.info("=" * 80)
    logger.info(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    try:
        with engine.connect() as conn:
            # 检查chassis表是否存在
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chassis'"
            ))
            if not result.fetchone():
                logger.error("chassis表不存在，请先创建基础表")
                return False
            
            logger.info("✓ chassis表存在，开始添加新字段...")
            
            # ========== 物理结构组 (Group A) ==========
            if not check_column_exists(conn, "chassis", "torsional_rigidity_target"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN torsional_rigidity_target INTEGER DEFAULT 50
                """))
                logger.info("  ✓ 添加 torsional_rigidity_target")
            
            if not check_column_exists(conn, "chassis", "rust_protection_level"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN rust_protection_level VARCHAR(50) DEFAULT 'NONE'
                """))
                logger.info("  ✓ 添加 rust_protection_level")
            
            if not check_column_exists(conn, "chassis", "nvh_insulation_mass"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN nvh_insulation_mass REAL DEFAULT 0.0
                """))
                logger.info("  ✓ 添加 nvh_insulation_mass")
            
            # ========== 包装与安全组 (Group B & C) ==========
            if not check_column_exists(conn, "chassis", "engine_bay_volume"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN engine_bay_volume INTEGER
                """))
                logger.info("  ✓ 添加 engine_bay_volume")
            
            if not check_column_exists(conn, "chassis", "transmission_tunnel_fitted"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN transmission_tunnel_fitted BOOLEAN DEFAULT 0
                """))
                logger.info("  ✓ 添加 transmission_tunnel_fitted")
            
            if not check_column_exists(conn, "chassis", "crumple_zone_length"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN crumple_zone_length REAL DEFAULT 0.0
                """))
                logger.info("  ✓ 添加 crumple_zone_length")
            
            if not check_column_exists(conn, "chassis", "fuel_tank_location"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN fuel_tank_location VARCHAR(50) DEFAULT 'REAR_AXLE_BEHIND'
                """))
                logger.info("  ✓ 添加 fuel_tank_location")
            
            # ========== 制造与供应链组 (Group D & E) ==========
            if not check_column_exists(conn, "chassis", "manufacturing_complexity_score"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN manufacturing_complexity_score REAL DEFAULT 0.5
                """))
                logger.info("  ✓ 添加 manufacturing_complexity_score")
            
            if not check_column_exists(conn, "chassis", "parts_bin_sharing_ratio"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN parts_bin_sharing_ratio REAL DEFAULT 0.5
                """))
                logger.info("  ✓ 添加 parts_bin_sharing_ratio")
            
            # ========== 认证组 (Group F) ==========
            if not check_column_exists(conn, "chassis", "designed_bumper_height"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN designed_bumper_height REAL
                """))
                logger.info("  ✓ 添加 designed_bumper_height")
            
            if not check_column_exists(conn, "chassis", "overall_width_class"):
                conn.execute(text("""
                    ALTER TABLE chassis 
                    ADD COLUMN overall_width_class VARCHAR(50) DEFAULT 'STANDARD'
                """))
                logger.info("  ✓ 添加 overall_width_class")
            
            # 提交更改
            conn.commit()
            
            logger.info("=" * 80)
            logger.info("✅ 迁移完成！")
            logger.info("=" * 80)
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 迁移失败: {str(e)}", exc_info=True)
        return False
    finally:
        engine.dispose()


def migrate_all_databases():
    """迁移所有数据库文件"""
    from backend.core.save_manager import SaveManager
    
    save_mgr = SaveManager()
    databases_to_migrate = []
    
    # 1. 当前活动的数据库
    from backend.core.save_manager import GameSessionManager
    current_save_path = GameSessionManager.get_current_save_path()
    if current_save_path and current_save_path.exists():
        databases_to_migrate.append(("当前存档", str(current_save_path)))
    
    # 2. 模板数据库
    if save_mgr.template_db_path.exists():
        databases_to_migrate.append(("模板数据库", str(save_mgr.template_db_path)))
    
    # 3. 所有存档文件
    if save_mgr.saves_dir.exists():
        for save_file in save_mgr.saves_dir.glob("*.db"):
            if str(save_file) not in [db[1] for db in databases_to_migrate]:
                databases_to_migrate.append((f"存档: {save_file.name}", str(save_file)))
    
    if not databases_to_migrate:
        logger.warning("找不到任何数据库文件，仅迁移默认数据库")
        databases_to_migrate.append(("默认数据库", "data/automogul.db"))
    
    success_count = 0
    for db_name, db_path in databases_to_migrate:
        logger.info(f"\n迁移: {db_name}")
        if migrate_database(db_path):
            success_count += 1
    
    logger.info(f"\n迁移完成: {success_count}/{len(databases_to_migrate)} 个数据库成功")
    return success_count == len(databases_to_migrate)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="迁移底盘深度工程字段")
    parser.add_argument("--db", type=str, help="指定数据库路径")
    parser.add_argument("--all", action="store_true", help="迁移所有数据库")
    
    args = parser.parse_args()
    
    if args.all:
        success = migrate_all_databases()
    else:
        success = migrate_database(args.db)
    
    sys.exit(0 if success else 1)


