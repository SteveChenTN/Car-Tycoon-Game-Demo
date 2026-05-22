"""
数据库迁移脚本 - Patch 1.4
创建所有新表
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, SessionLocal
from backend.models import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database():
    """执行数据库迁移"""
    logger.info("=" * 80)
    logger.info("开始数据库迁移 - Patch 1.4")
    logger.info("=" * 80)
    
    try:
        # 初始化数据库（创建所有表）
        logger.info("创建新表...")
        init_db()
        logger.info("✓ 数据库表创建成功")
        
        # 验证新表是否存在
        db = SessionLocal()
        try:
            # 测试查询新表
            from backend.models.history import SalesHistory, FinancialHistory, UsedCarInventory
            from backend.models.supply import SupplierContract, MaterialMarket
            
            # 尝试查询（应该返回空列表）
            sales_count = db.query(SalesHistory).count()
            financial_count = db.query(FinancialHistory).count()
            used_car_count = db.query(UsedCarInventory).count()
            contract_count = db.query(SupplierContract).count()
            material_market_count = db.query(MaterialMarket).count()
            
            logger.info("\n验证新表:")
            logger.info(f"  ✓ sales_history: {sales_count} 条记录")
            logger.info(f"  ✓ financial_history: {financial_count} 条记录")
            logger.info(f"  ✓ used_car_inventory: {used_car_count} 条记录")
            logger.info(f"  ✓ supplier_contracts: {contract_count} 条记录")
            logger.info(f"  ✓ material_markets: {material_market_count} 条记录")
            
            # 验证新字段
            from backend.models.company import Company
            from backend.models.region import Region
            
            company = Company(
                game_id=999,
                name="Test Company",
                short_code="TEST",
                founded_year=1950,
                founded_turn=0,
                headquarters_region="NAM",
                monthly_revenue=0.0  # 新字段
            )
            
            region = Region(
                game_id=999,
                code="TEST",
                name="Test Region",
                population=1000000,
                gdp_per_capita=30000,
                gdp_growth_rate=0.02,
                purchasing_power_index=1.0,
                inflation_rate=0.03,
                unemployment_rate=0.05,
                car_ownership_rate=500,
                avg_vehicle_age=8.0,
                annual_sales_potential=100000,
                infrastructure_quality=0.8,
                road_quality=0.8,
                fuel_price=1.5,
                electricity_price=0.12,
                import_tariff_rate=0.1,
                emission_standard="EURO3",
                safety_standard="MODERATE",
                corporate_tax_rate=0.25,
                ev_subsidy_rate=0.0,
                steel_availability=0.8,
                aluminum_availability=0.7,
                rare_earth_availability=0.5,
                labor_cost_index=1.0,
                skilled_labor_availability=0.7,
                allow_used_export=True,  # 新字段
                allow_used_import=True   # 新字段
            )
            
            logger.info("\n验证新字段:")
            logger.info(f"  ✓ Company.monthly_revenue: {company.monthly_revenue}")
            logger.info(f"  ✓ Region.allow_used_export: {region.allow_used_export}")
            logger.info(f"  ✓ Region.allow_used_import: {region.allow_used_import}")
            
            logger.info("\n" + "=" * 80)
            logger.info("✓ 数据库迁移完成！")
            logger.info("=" * 80)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"✗ 数据库迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    migrate_database()


