"""
数据库迁移：添加生产与供应链表

执行此脚本来创建 factories, material_market, inventories, 
b2b_component_listings, b2b_transactions 表
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import engine, Base
from backend.models.production import Factory, MaterialMarket, Inventory
from backend.models.b2b import ComponentListing, B2BTransaction
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def run_migration():
    """执行数据库迁移"""
    
    logger.info("=" * 70)
    logger.info("开始数据库迁移：生产与供应链系统")
    logger.info("=" * 70)
    
    try:
        # 创建所有表
        logger.info("创建新表...")
        Base.metadata.create_all(bind=engine, checkfirst=True)
        
        logger.info("✅ 迁移完成！")
        logger.info("\n新增表：")
        logger.info("  - factories (工厂)")
        logger.info("  - material_market (原材料市场)")
        logger.info("  - inventories (库存)")
        logger.info("  - b2b_component_listings (B2B挂牌)")
        logger.info("  - b2b_transactions (B2B交易记录)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)


