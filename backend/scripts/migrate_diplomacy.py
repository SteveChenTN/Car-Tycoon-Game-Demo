"""
迁移脚本：添加外交系统表

添加：
- competitor_relations（公司间关系）
- diplomatic_actions（外交行动记录）
- patents（专利系统接口）

运行方式：
    python backend/scripts/migrate_diplomacy.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import create_engine, text
from backend.database import Base
from backend.models.diplomacy import CompetitorRelation, DiplomaticAction, Patent
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def run_migration(db_path: str = "data/automogul.db"):
    """
    执行外交系统迁移
    
    Args:
        db_path: 数据库文件路径
    """
    logger.info("=" * 60)
    logger.info("开始外交系统迁移")
    logger.info("=" * 60)
    
    # 连接数据库
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    try:
        # 创建外交系统表
        logger.info("创建外交系统表...")
        
        # 导入所有模型以确保它们被注册
        from backend.models import (
            game_state, company, engineering, staff,
            technology, production, supply, market,
            finance, legal, events, directive, history, testing
        )
        
        # 创建外交表
        Base.metadata.create_all(
            engine,
            tables=[
                CompetitorRelation.__table__,
                DiplomaticAction.__table__,
                Patent.__table__
            ]
        )
        
        logger.info("✓ 外交系统表创建成功")
        
        # 验证表创建
        with engine.connect() as conn:
            # 检查 competitor_relations 表
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='competitor_relations'"
            ))
            if result.fetchone():
                logger.info("  ✓ competitor_relations 表已创建")
            else:
                logger.error("  ✗ competitor_relations 表创建失败")
            
            # 检查 diplomatic_actions 表
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='diplomatic_actions'"
            ))
            if result.fetchone():
                logger.info("  ✓ diplomatic_actions 表已创建")
            else:
                logger.error("  ✗ diplomatic_actions 表创建失败")
            
            # 检查 patents 表
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='patents'"
            ))
            if result.fetchone():
                logger.info("  ✓ patents 表已创建")
            else:
                logger.error("  ✗ patents 表创建失败")
        
        logger.info("=" * 60)
        logger.info("外交系统迁移完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("新功能：")
        logger.info("  1. Executive Poaching（挖角高管）")
        logger.info("  2. PR Attack / Smear Campaign（公关攻击）")
        logger.info("  3. Competitor Relations Tracking（关系追踪）")
        logger.info("  4. Patent System (Interface Only)（专利系统接口）")
        logger.info("")
        logger.info("使用方式：")
        logger.info("  from backend.core.management.diplomacy import DiplomacyManager")
        logger.info("  mgr = DiplomacyManager(db)")
        logger.info("  mgr.attempt_poach_executive(...)")
        logger.info("  mgr.launch_smear_campaign(...)")
        logger.info("")
        
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="外交系统数据库迁移")
    parser.add_argument(
        "--db",
        default="data/automogul.db",
        help="数据库文件路径（默认：data/automogul.db）"
    )
    
    args = parser.parse_args()
    
    run_migration(args.db)


