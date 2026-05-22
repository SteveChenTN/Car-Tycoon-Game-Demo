"""
数据库迁移：添加工程熟悉度表

执行此脚本来创建 engineering_familiarity 表
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.core.save_manager import SaveManager
from backend.models.engineering_familiarity import EngineeringFamiliarity
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def run_migration():
    """执行数据库迁移"""
    
    logger.info("=" * 70)
    logger.info("开始数据库迁移：工程熟悉度系统")
    logger.info("=" * 70)
    
    try:
        # 获取当前活动的数据库连接
        save_mgr = SaveManager()
        
        # 获取所有需要迁移的数据库
        databases_to_migrate = []
        
        # 1. 当前加载的存档
        from backend.core.save_manager import GameSessionManager
        current_save_path = GameSessionManager.get_current_save_path()
        if current_save_path and current_save_path.exists():
            databases_to_migrate.append(("当前存档", current_save_path))
        
        # 2. 模板数据库
        if save_mgr.template_db_path.exists():
            databases_to_migrate.append(("模板数据库", save_mgr.template_db_path))
        
        # 3. 所有存档文件
        for save_file in save_mgr.saves_dir.glob("*.db"):
            if save_file not in [db[1] for db in databases_to_migrate]:
                databases_to_migrate.append((f"存档: {save_file.name}", save_file))
        
        if not databases_to_migrate:
            logger.error("找不到任何数据库文件。请先创建游戏存档。")
            return False
        
        # 创建数据库引擎并迁移所有数据库
        from sqlalchemy import create_engine
        success_count = 0
        
        for db_name, db_path in databases_to_migrate:
            logger.info(f"\n处理 {db_name}: {db_path}")
            try:
                engine = create_engine(f"sqlite:///{db_path}", echo=False)
                
                # 创建表
                logger.info("  创建 engineering_familiarity 表...")
                EngineeringFamiliarity.__table__.create(bind=engine, checkfirst=True)
                
                # 验证表创建
                from sqlalchemy import inspect, text
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                if 'engineering_familiarity' in tables:
                    logger.info(f"  ✓ {db_name} - engineering_familiarity 表已创建")
                    success_count += 1
                else:
                    logger.error(f"  ✗ {db_name} - engineering_familiarity 表创建失败")
                
                engine.dispose()
            except Exception as e:
                logger.error(f"  ✗ {db_name} - 迁移失败: {e}")
        
        if success_count == 0:
            return False
        
        logger.info("✅ 迁移完成！")
        logger.info("\n新增表：")
        logger.info("  - engineering_familiarity (工程熟悉度)")
        
        # 验证表创建
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'engineering_familiarity' in tables:
            logger.info("  ✓ engineering_familiarity 表已创建")
            
            # 检查表结构
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(engineering_familiarity)"))
                columns = result.fetchall()
                logger.info(f"  ✓ 表包含 {len(columns)} 个列")
        else:
            logger.error("  ✗ engineering_familiarity 表创建失败")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        logger.info("\n✅ 迁移成功完成！")
        sys.exit(0)
    else:
        logger.error("\n❌ 迁移失败！")
        sys.exit(1)

