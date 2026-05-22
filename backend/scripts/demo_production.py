"""
演示脚本：生产与供应链系统

展示如何使用新的生产系统功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.game_state import GameState
from backend.models.region import Region
from backend.models.engineering import Engine, Chassis
from backend.models.production import Factory, MaterialMarket, Inventory, FactoryType, MaterialType
from backend.models.b2b import ComponentListing
from backend.core.production.production_manager import ProductionManager
from backend.core.ai.ai_procurement import AIProcurementDelegate
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def demo_production_system(db: Session):
    """演示生产系统功能"""
    
    logger.info("=" * 70)
    logger.info("生产与供应链系统演示")
    logger.info("=" * 70)
    
    # 获取游戏和地区
    game = db.query(GameState).first()
    if not game:
        logger.error("请先运行 init_world.py 初始化游戏")
        return
    
    region = db.query(Region).first()
    if not region:
        logger.error("找不到地区数据")
        return
    
    logger.info(f"\n当前游戏: {game.current_year}年{game.current_month}月第{game.current_week}周")
    logger.info(f"地区: {region.name}")
    
    # ========== 1. 创建工厂 ==========
    logger.info("\n" + "=" * 70)
    logger.info("步骤1: 创建零部件工厂和装配厂")
    logger.info("=" * 70)
    
    # 零部件工厂
    component_factory = Factory(
        game_id=game.id,
        company_id=1,  # 假设公司ID为1
        name="Detroit Engine Plant #1",
        factory_type=FactoryType.COMPONENT.value,
        level=5,
        capacity_units_per_month=1000,
        current_utilization_rate=0.0,
        region_id=region.id,
        efficiency_score=85.0,
        labor_cost_per_unit=50.0,
        overhead_cost_per_month=100000.0,
        tech_level=7,
        is_operational=True
    )
    db.add(component_factory)
    db.flush()
    
    logger.info(f"✅ 创建零部件工厂: {component_factory.name}")
    logger.info(f"   - 类型: {component_factory.factory_type}")
    logger.info(f"   - 等级: {component_factory.level}")
    logger.info(f"   - 月产能: {component_factory.capacity_units_per_month} 件")
    logger.info(f"   - 有效产能: {component_factory.get_effective_capacity()} 件")
    
    # 装配厂
    assembly_factory = Factory(
        game_id=game.id,
        company_id=1,
        name="Michigan Assembly Plant",
        factory_type=FactoryType.ASSEMBLY.value,
        level=4,
        capacity_units_per_month=800,
        current_utilization_rate=0.0,
        region_id=region.id,
        efficiency_score=80.0,
        labor_cost_per_unit=150.0,
        overhead_cost_per_month=200000.0,
        tech_level=6,
        is_operational=True
    )
    db.add(assembly_factory)
    db.flush()
    
    logger.info(f"\n✅ 创建装配厂: {assembly_factory.name}")
    logger.info(f"   - 类型: {assembly_factory.factory_type}")
    logger.info(f"   - 月产能: {assembly_factory.capacity_units_per_month} 辆")
    
    # ========== 2. 初始化材料市场 ==========
    logger.info("\n" + "=" * 70)
    logger.info("步骤2: 初始化原材料市场价格")
    logger.info("=" * 70)
    
    materials_data = [
        ("STEEL", 0.60, 0.10),
        ("ALUMINUM", 2.50, 0.15),
        ("PLASTIC", 1.80, 0.20),
        ("ELECTRONICS", 5.00, 0.12),
        ("RUBBER", 1.50, 0.15),
        ("GLASS", 0.80, 0.08)
    ]
    
    for material_type, price, volatility in materials_data:
        market = MaterialMarket(
            game_id=game.id,
            region_id=region.id,
            material_type=material_type,
            current_price_per_kg=price,
            historical_avg_price=price,
            price_volatility=volatility,
            supply_level=1.0,
            last_update_turn=game.turn_number
        )
        db.add(market)
        logger.info(f"   {material_type:12s}: ${price:.2f}/kg (波动率: {volatility:.0%})")
    
    db.flush()
    
    # ========== 3. 采购原材料 ==========
    logger.info("\n" + "=" * 70)
    logger.info("步骤3: 为工厂采购原材料")
    logger.info("=" * 70)
    
    production_manager = ProductionManager(db)
    
    # 为零部件工厂采购材料
    materials_to_purchase = [
        ("STEEL", 50000),
        ("ALUMINUM", 20000),
        ("PLASTIC", 5000),
        ("ELECTRONICS", 500),
        ("RUBBER", 2000)
    ]
    
    total_cost = 0.0
    for material, quantity in materials_to_purchase:
        success, msg, details = production_manager.purchase_materials(
            component_factory, material, quantity, region.id
        )
        if success:
            logger.info(f"✅ 采购 {material}: {quantity:.0f}kg, 成本: ${details['total_cost']:,.2f}")
            total_cost += details['total_cost']
        else:
            logger.error(f"❌ {msg}")
    
    logger.info(f"\n总采购成本: ${total_cost:,.2f}")
    
    # ========== 4. 生产引擎组件 ==========
    logger.info("\n" + "=" * 70)
    logger.info("步骤4: 生产引擎组件")
    logger.info("=" * 70)
    
    # 查找一个引擎（如果存在）
    engine = db.query(Engine).first()
    if engine:
        logger.info(f"使用引擎: {engine.name} ({engine.code})")
        logger.info(f"   规格: {engine.configuration}{engine.cylinder_count}, {engine.displacement_cc}cc")
        logger.info(f"   功率: {engine.max_horsepower}hp @ {engine.redline_rpm}rpm")
        
        # 生产50台引擎
        quantity = 50
        success, msg, details = production_manager.produce_component(
            component_factory, "engine", engine.id, quantity
        )
        
        if success:
            logger.info(f"\n✅ 生产成功!")
            logger.info(f"   数量: {details['quantity']} 台")
            logger.info(f"   使用材料: ")
            for material, amount in details['materials_used'].items():
                logger.info(f"      {material}: {amount:.2f}kg")
            logger.info(f"   总成本: ${details['total_cost']:,.2f}")
            logger.info(f"   工厂利用率: {details['factory_utilization']}%")
        else:
            logger.error(f"❌ {msg}")
    else:
        logger.warning("⚠️  数据库中没有引擎，跳过生产演示")
        logger.info("   提示: 运行 backend/scripts/demo_engineering.py 创建引擎")
    
    # ========== 5. AI采购策略演示 ==========
    logger.info("\n" + "=" * 70)
    logger.info("步骤5: AI自动采购策略")
    logger.info("=" * 70)
    
    ai_procurement = AIProcurementDelegate(db)
    
    # 模拟生产计划
    planned_production = {"ENGINE_TEST": 100}
    
    # 测试准时制策略
    logger.info("\n测试准时制（JIT）策略:")
    success, msg, purchases = ai_procurement.run_procurement_policy(
        component_factory, "JUST_IN_TIME", planned_production, game.turn_number
    )
    logger.info(f"   {msg}")
    logger.info(f"   采购批次: {len(purchases)}")
    
    # 测试囤积型策略
    logger.info("\n测试囤积型（Hoarder）策略:")
    success, msg, purchases = ai_procurement.run_procurement_policy(
        component_factory, "HOARDER", planned_production, game.turn_number
    )
    logger.info(f"   {msg}")
    logger.info(f"   采购批次: {len(purchases)}")
    
    # ========== 6. B2B市场挂牌 ==========
    if engine:
        logger.info("\n" + "=" * 70)
        logger.info("步骤6: B2B市场挂牌")
        logger.info("=" * 70)
        
        listing = ComponentListing(
            game_id=game.id,
            seller_company_id=1,
            component_type="ENGINE",
            component_id=engine.id,
            unit_price=engine.manufacturing_cost * 1.3,  # 30%溢价
            min_order_quantity=50,
            available_quantity=500,
            is_active=True,
            lead_time_weeks=4
        )
        db.add(listing)
        db.flush()
        
        logger.info(f"✅ 发布B2B挂牌:")
        logger.info(f"   组件: {engine.name}")
        logger.info(f"   单价: ${listing.unit_price:,.2f}")
        logger.info(f"   最小订购量: {listing.min_order_quantity}")
        logger.info(f"   可供应量: {listing.available_quantity}")
    
    # 提交所有更改
    db.commit()
    
    logger.info("\n" + "=" * 70)
    logger.info("演示完成！")
    logger.info("=" * 70)
    logger.info("\n已创建:")
    logger.info(f"  - {2} 个工厂")
    logger.info(f"  - {len(materials_data)} 种材料市场")
    logger.info(f"  - {1} 个B2B挂牌 (如果有引擎)")
    logger.info("\n数据已保存到数据库")


def main():
    """主函数"""
    db = SessionLocal()
    try:
        demo_production_system(db)
    except Exception as e:
        logger.error(f"演示失败: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()


