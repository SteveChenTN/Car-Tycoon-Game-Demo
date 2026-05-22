"""
测试脚本：完整的生产流程测试

测试流程：
1. 创建一个V8引擎设计
2. 创建一个引擎工厂
3. 购买100吨（100,000kg）钢材和其他材料
4. 生产50台V8引擎
5. 验证：
   - 引擎库存正确增加（+50台）
   - 钢材库存正确减少
   - 其他材料也相应减少
   - 工厂利用率更新
"""
import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.game_state import GameState
from backend.models.region import Region
from backend.models.engineering import Engine
from backend.models.production import Factory, MaterialMarket, Inventory, FactoryType
from backend.core.production.production_manager import ProductionManager
from backend.services.engineering_service import EngineeringService
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ProductionFlowTest:
    """生产流程测试类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.production_manager = ProductionManager(db)
        self.test_results: Dict[str, Any] = {}
        
    def run_test(self) -> bool:
        """运行完整测试流程"""
        
        logger.info("=" * 80)
        logger.info("开始生产流程测试")
        logger.info("=" * 80)
        
        try:
            # 步骤1: 准备测试环境
            if not self._setup_test_environment():
                return False
            
            # 步骤2: 创建V8引擎设计
            if not self._create_v8_engine():
                return False
            
            # 步骤3: 创建引擎工厂
            if not self._create_engine_factory():
                return False
            
            # 步骤4: 初始化材料市场
            if not self._initialize_material_market():
                return False
            
            # 步骤5: 购买100吨钢材和其他材料
            if not self._purchase_materials():
                return False
            
            # 步骤6: 记录生产前状态
            if not self._record_pre_production_state():
                return False
            
            # 步骤7: 生产50台V8引擎
            if not self._produce_engines():
                return False
            
            # 步骤8: 验证生产后状态
            if not self._verify_post_production_state():
                return False
            
            # 步骤9: 显示测试结果
            self._display_test_results()
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ 所有测试通过！")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ 测试失败: {str(e)}", exc_info=True)
            return False
    
    def _setup_test_environment(self) -> bool:
        """准备测试环境"""
        logger.info("\n【步骤1】准备测试环境")
        logger.info("-" * 80)
        
        # 获取游戏状态
        self.game = self.db.query(GameState).first()
        if not self.game:
            logger.error("❌ 未找到游戏状态，请先运行 init_world.py")
            return False
        
        logger.info(f"✅ 游戏状态: {self.game.current_year}年{self.game.current_month}月第{self.game.current_week}周")
        
        # 获取地区
        self.region = self.db.query(Region).first()
        if not self.region:
            logger.error("❌ 未找到地区数据")
            return False
        
        logger.info(f"✅ 测试地区: {self.region.name}")
        
        # 清理旧的测试数据
        logger.info("\n清理旧的测试数据...")
        
        # 删除旧的测试引擎
        old_engine = self.db.query(Engine).filter(Engine.code == "TEST_V8_5000").first()
        if old_engine:
            logger.info(f"   删除旧的测试引擎: {old_engine.name}")
            self.db.delete(old_engine)
        
        # 删除旧的测试工厂（级联删除会自动删除库存）
        old_factory = self.db.query(Factory).filter(
            Factory.company_id == 999,
            Factory.name == "Test V8 Engine Factory"
        ).first()
        if old_factory:
            logger.info(f"   删除旧的测试工厂: {old_factory.name}")
            self.db.delete(old_factory)
        
        self.db.commit()
        logger.info("✅ 测试环境准备完成")
        
        return True
    
    def _create_v8_engine(self) -> bool:
        """创建V8引擎设计"""
        logger.info("\n【步骤2】创建V8引擎设计")
        logger.info("-" * 80)
        
        try:
            # 创建一个经典的5.0L V8引擎
            self.engine = EngineeringService.create_engine_with_calculations(
                db=self.db,
                game_id=self.game.id,
                company_id=999,  # 测试公司ID
                name="PowerTech V8 5.0",
                code="TEST_V8_5000",
                bore_mm=94.0,
                stroke_mm=90.0,
                cylinder_count=8,
                configuration="V",
                compression_ratio=10.5,
                induction_type="NA",
                boost_pressure_bar=0.0,
                material="CAST_IRON",
                valvetrain="DOHC",
                fuel_type="GASOLINE",
                tech_level=5
            )
            
            logger.info(f"✅ 创建V8引擎: {self.engine.name}")
            logger.info(f"   - 代码: {self.engine.code}")
            logger.info(f"   - 配置: {self.engine.configuration}{self.engine.cylinder_count}")
            logger.info(f"   - 排量: {self.engine.displacement_cc}cc ({self.engine.displacement_cc/1000:.1f}L)")
            logger.info(f"   - 功率: {self.engine.max_horsepower}hp @ {self.engine.redline_rpm}rpm")
            logger.info(f"   - 扭矩: {self.engine.max_torque_nm}Nm")
            logger.info(f"   - 重量: {self.engine.weight_kg}kg")
            logger.info(f"   - 制造成本: ${self.engine.manufacturing_cost:,.2f}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建V8引擎失败: {str(e)}")
            self.db.rollback()
            return False
    
    def _create_engine_factory(self) -> bool:
        """创建引擎工厂"""
        logger.info("\n【步骤3】创建引擎工厂")
        logger.info("-" * 80)
        
        try:
            self.factory = Factory(
                game_id=self.game.id,
                company_id=999,  # 测试公司ID
                name="Test V8 Engine Factory",
                factory_type=FactoryType.COMPONENT.value,
                level=6,  # 6级工厂，足够生产5级引擎
                capacity_units_per_month=500,
                current_utilization_rate=0.0,
                region_id=self.region.id,
                efficiency_score=90.0,  # 90%效率
                labor_cost_per_unit=60.0,
                overhead_cost_per_month=150000.0,
                tech_level=6,
                is_operational=True
            )
            
            self.db.add(self.factory)
            self.db.flush()
            
            logger.info(f"✅ 创建工厂: {self.factory.name}")
            logger.info(f"   - 类型: {self.factory.factory_type}")
            logger.info(f"   - 等级: {self.factory.level}")
            logger.info(f"   - 技术等级: {self.factory.tech_level}")
            logger.info(f"   - 名义月产能: {self.factory.capacity_units_per_month} 件")
            logger.info(f"   - 有效月产能: {self.factory.get_effective_capacity()} 件 (效率{self.factory.efficiency_score}%)")
            logger.info(f"   - 单位劳动力成本: ${self.factory.labor_cost_per_unit:.2f}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建工厂失败: {str(e)}")
            self.db.rollback()
            return False
    
    def _initialize_material_market(self) -> bool:
        """初始化材料市场"""
        logger.info("\n【步骤4】初始化材料市场")
        logger.info("-" * 80)
        
        try:
            # 定义测试用材料价格
            materials_data = [
                ("STEEL", 0.70, 0.10),
                ("ALUMINUM", 2.80, 0.15),
                ("PLASTIC", 2.00, 0.20),
                ("ELECTRONICS", 6.00, 0.12),
                ("RUBBER", 1.60, 0.15),
            ]
            
            for material_type, price, volatility in materials_data:
                # 检查是否已存在
                existing = self.db.query(MaterialMarket).filter(
                    MaterialMarket.game_id == self.game.id,
                    MaterialMarket.region_id == self.region.id,
                    MaterialMarket.material_type == material_type
                ).first()
                
                if not existing:
                    market = MaterialMarket(
                        game_id=self.game.id,
                        region_id=self.region.id,
                        material_type=material_type,
                        current_price_per_kg=price,
                        historical_avg_price=price,
                        price_volatility=volatility,
                        supply_level=1.0,
                        last_update_turn=self.game.turn_number
                    )
                    self.db.add(market)
                    logger.info(f"   {material_type:12s}: ${price:.2f}/kg (波动率: {volatility:.0%})")
                else:
                    logger.info(f"   {material_type:12s}: ${existing.current_price_per_kg:.2f}/kg (已存在)")
            
            self.db.commit()
            logger.info("✅ 材料市场初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化材料市场失败: {str(e)}")
            self.db.rollback()
            return False
    
    def _purchase_materials(self) -> bool:
        """购买100吨钢材和其他必要材料"""
        logger.info("\n【步骤5】购买材料")
        logger.info("-" * 80)
        
        try:
            # 计算生产50台V8引擎所需材料
            materials_needed = self.production_manager.calculate_engine_material_requirements(self.engine)
            
            logger.info(f"单台V8引擎材料需求：")
            for material, amount in materials_needed.items():
                logger.info(f"   {material}: {amount:.2f}kg")
            
            logger.info(f"\n生产50台所需材料：")
            total_needed = {}
            for material, amount in materials_needed.items():
                total_needed[material] = amount * 50
                logger.info(f"   {material}: {total_needed[material]:.2f}kg ({total_needed[material]/1000:.2f}吨)")
            
            # 购买材料（多买一些以确保充足）
            materials_to_purchase = {
                "STEEL": 100000.0,  # 100吨钢材
                "ALUMINUM": max(total_needed.get("ALUMINUM", 0) * 1.2, 10000),  # 多买20%作为安全余量
                "PLASTIC": max(total_needed.get("PLASTIC", 0) * 1.2, 5000),
                "ELECTRONICS": max(total_needed.get("ELECTRONICS", 0) * 1.2, 500),
                "RUBBER": max(total_needed.get("RUBBER", 0) * 1.2, 1000),
            }
            
            logger.info(f"\n实际采购量（含安全余量）：")
            total_cost = 0.0
            for material, quantity in materials_to_purchase.items():
                success, msg, details = self.production_manager.purchase_materials(
                    self.factory, material, quantity, self.region.id
                )
                
                if success:
                    logger.info(f"✅ {material:12s}: {quantity:,.0f}kg ({quantity/1000:.2f}吨), 成本: ${details['total_cost']:,.2f}")
                    total_cost += details['total_cost']
                else:
                    logger.error(f"❌ {material} 采购失败: {msg}")
                    return False
            
            logger.info(f"\n💰 总采购成本: ${total_cost:,.2f}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 采购材料失败: {str(e)}")
            self.db.rollback()
            return False
    
    def _record_pre_production_state(self) -> bool:
        """记录生产前状态"""
        logger.info("\n【步骤6】记录生产前库存状态")
        logger.info("-" * 80)
        
        try:
            # 获取库存
            inventory = self.db.query(Inventory).filter(
                Inventory.factory_id == self.factory.id
            ).first()
            
            if not inventory:
                logger.error("❌ 未找到工厂库存记录")
                return False
            
            # 刷新数据库状态，确保获取最新数据
            self.db.refresh(inventory)
            
            # 记录各种材料的库存
            self.pre_production_state = {
                "STEEL": inventory.get_material_quantity("STEEL"),
                "ALUMINUM": inventory.get_material_quantity("ALUMINUM"),
                "PLASTIC": inventory.get_material_quantity("PLASTIC"),
                "ELECTRONICS": inventory.get_material_quantity("ELECTRONICS"),
                "RUBBER": inventory.get_material_quantity("RUBBER"),
                "engines": inventory.get_component_quantity(self.engine.id)
            }
            
            logger.info("生产前库存状态：")
            logger.info(f"   钢材（STEEL）: {self.pre_production_state['STEEL']:,.2f}kg ({self.pre_production_state['STEEL']/1000:.2f}吨)")
            logger.info(f"   铝材（ALUMINUM）: {self.pre_production_state['ALUMINUM']:,.2f}kg")
            logger.info(f"   塑料（PLASTIC）: {self.pre_production_state['PLASTIC']:,.2f}kg")
            logger.info(f"   电子元件（ELECTRONICS）: {self.pre_production_state['ELECTRONICS']:,.2f}kg")
            logger.info(f"   橡胶（RUBBER）: {self.pre_production_state['RUBBER']:,.2f}kg")
            logger.info(f"   V8引擎库存: {self.pre_production_state['engines']} 台")
            
            # 验证是否有足够的材料
            materials_needed = self.production_manager.calculate_engine_material_requirements(self.engine)
            total_needed = {material: amount * 50 for material, amount in materials_needed.items()}
            
            logger.info(f"\n生产50台所需 vs 当前库存对比：")
            has_sufficient = True
            for material in ["STEEL", "ALUMINUM", "PLASTIC", "ELECTRONICS", "RUBBER"]:
                needed = total_needed.get(material, 0)
                available = self.pre_production_state[material]
                sufficient = "✅" if available >= needed else "❌"
                logger.info(f"   {material:12s}: 需要 {needed:,.2f}kg, 库存 {available:,.2f}kg {sufficient}")
                if available < needed:
                    has_sufficient = False
            
            if not has_sufficient:
                logger.error("\n❌ 材料不足！这可能是因为之前的演示脚本已使用了部分材料")
                logger.info("💡 建议：重新初始化数据库或增加采购量")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 记录生产前状态失败: {str(e)}")
            return False
    
    def _produce_engines(self) -> bool:
        """生产50台V8引擎"""
        logger.info("\n【步骤7】生产50台V8引擎")
        logger.info("-" * 80)
        
        try:
            quantity = 50
            
            logger.info(f"开始生产 {quantity} 台 {self.engine.name}...")
            logger.info(f"工厂: {self.factory.name}")
            logger.info(f"引擎代码: {self.engine.code}")
            
            success, msg, details = self.production_manager.produce_component(
                self.factory,
                "engine",
                self.engine.id,
                quantity
            )
            
            if not success:
                logger.error(f"❌ 生产失败: {msg}")
                return False
            
            logger.info(f"\n✅ 生产成功！")
            logger.info(f"   生产数量: {details['quantity']} 台")
            logger.info(f"   生产成本: ${details['total_cost']:,.2f}")
            logger.info(f"   单位成本: ${details['total_cost']/details['quantity']:,.2f}/台")
            logger.info(f"   工厂利用率: {details['factory_utilization']}%")
            
            logger.info(f"\n消耗材料明细：")
            for material, amount in details['materials_used'].items():
                logger.info(f"   {material}: {amount:,.2f}kg ({amount/1000:.2f}吨)")
            
            self.production_details = details
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 生产引擎失败: {str(e)}")
            self.db.rollback()
            return False
    
    def _verify_post_production_state(self) -> bool:
        """验证生产后状态"""
        logger.info("\n【步骤8】验证生产后库存状态")
        logger.info("-" * 80)
        
        try:
            # 获取库存
            inventory = self.db.query(Inventory).filter(
                Inventory.factory_id == self.factory.id
            ).first()
            
            # 记录生产后状态
            post_production_state = {
                "STEEL": inventory.get_material_quantity("STEEL"),
                "ALUMINUM": inventory.get_material_quantity("ALUMINUM"),
                "PLASTIC": inventory.get_material_quantity("PLASTIC"),
                "ELECTRONICS": inventory.get_material_quantity("ELECTRONICS"),
                "RUBBER": inventory.get_material_quantity("RUBBER"),
                "engines": inventory.get_component_quantity(self.engine.id)
            }
            
            logger.info("生产后库存状态：")
            logger.info(f"   钢材（STEEL）: {post_production_state['STEEL']:,.2f}kg ({post_production_state['STEEL']/1000:.2f}吨)")
            logger.info(f"   铝材（ALUMINUM）: {post_production_state['ALUMINUM']:,.2f}kg")
            logger.info(f"   塑料（PLASTIC）: {post_production_state['PLASTIC']:,.2f}kg")
            logger.info(f"   电子元件（ELECTRONICS）: {post_production_state['ELECTRONICS']:,.2f}kg")
            logger.info(f"   橡胶（RUBBER）: {post_production_state['RUBBER']:,.2f}kg")
            logger.info(f"   V8引擎库存: {post_production_state['engines']} 台")
            
            # 验证变化
            logger.info("\n" + "=" * 80)
            logger.info("库存变化验证：")
            logger.info("=" * 80)
            
            all_passed = True
            
            # 验证引擎库存增加
            engine_increase = post_production_state['engines'] - self.pre_production_state['engines']
            expected_engine_increase = 50
            
            logger.info(f"\n1️⃣  V8引擎库存验证：")
            logger.info(f"   生产前: {self.pre_production_state['engines']} 台")
            logger.info(f"   生产后: {post_production_state['engines']} 台")
            logger.info(f"   实际增加: {engine_increase} 台")
            logger.info(f"   预期增加: {expected_engine_increase} 台")
            
            if engine_increase == expected_engine_increase:
                logger.info(f"   ✅ 引擎库存验证通过")
            else:
                logger.error(f"   ❌ 引擎库存不匹配！")
                all_passed = False
            
            # 验证材料消耗
            logger.info(f"\n2️⃣  材料消耗验证：")
            
            for material in ["STEEL", "ALUMINUM", "PLASTIC", "ELECTRONICS", "RUBBER"]:
                material_decrease = self.pre_production_state[material] - post_production_state[material]
                expected_decrease = self.production_details['materials_used'].get(material, 0)
                
                logger.info(f"\n   {material}:")
                logger.info(f"      生产前: {self.pre_production_state[material]:,.2f}kg")
                logger.info(f"      生产后: {post_production_state[material]:,.2f}kg")
                logger.info(f"      实际减少: {material_decrease:,.2f}kg ({material_decrease/1000:.2f}吨)")
                logger.info(f"      预期减少: {expected_decrease:,.2f}kg ({expected_decrease/1000:.2f}吨)")
                
                # 允许微小的浮点误差（0.01kg）
                if abs(material_decrease - expected_decrease) < 0.01:
                    logger.info(f"      ✅ {material}消耗验证通过")
                else:
                    logger.error(f"      ❌ {material}消耗不匹配！")
                    all_passed = False
            
            # 特别关注钢材（100吨采购）
            logger.info(f"\n3️⃣  钢材特别验证（100吨采购）：")
            steel_consumed_tons = (self.pre_production_state['STEEL'] - post_production_state['STEEL']) / 1000
            steel_remaining_tons = post_production_state['STEEL'] / 1000
            
            logger.info(f"   采购: 100.00吨")
            logger.info(f"   消耗: {steel_consumed_tons:.2f}吨")
            logger.info(f"   剩余: {steel_remaining_tons:.2f}吨")
            logger.info(f"   验证: {steel_consumed_tons:.2f} + {steel_remaining_tons:.2f} = {steel_consumed_tons + steel_remaining_tons:.2f}吨")
            
            if abs((steel_consumed_tons + steel_remaining_tons) - 100.0) < 0.01:
                logger.info(f"   ✅ 钢材质量守恒验证通过")
            else:
                logger.error(f"   ❌ 钢材质量不守恒！")
                all_passed = False
            
            # 保存测试结果
            self.test_results = {
                "engine_increase": engine_increase,
                "expected_engine_increase": expected_engine_increase,
                "materials_consumed": {
                    material: self.pre_production_state[material] - post_production_state[material]
                    for material in ["STEEL", "ALUMINUM", "PLASTIC", "ELECTRONICS", "RUBBER"]
                },
                "expected_materials_consumed": self.production_details['materials_used'],
                "all_tests_passed": all_passed
            }
            
            return all_passed
            
        except Exception as e:
            logger.error(f"❌ 验证失败: {str(e)}")
            return False
    
    def _display_test_results(self):
        """显示测试结果总结"""
        logger.info("\n" + "=" * 80)
        logger.info("测试结果总结")
        logger.info("=" * 80)
        
        logger.info(f"\n✅ 测试项目：")
        logger.info(f"   1. 创建V8引擎设计 - 通过")
        logger.info(f"   2. 创建引擎工厂 - 通过")
        logger.info(f"   3. 初始化材料市场 - 通过")
        logger.info(f"   4. 采购100吨钢材及其他材料 - 通过")
        logger.info(f"   5. 生产50台V8引擎 - 通过")
        logger.info(f"   6. 引擎库存增加验证 - {'通过' if self.test_results['engine_increase'] == 50 else '失败'}")
        logger.info(f"   7. 材料消耗验证 - {'通过' if self.test_results['all_tests_passed'] else '失败'}")
        
        logger.info(f"\n📊 数据统计：")
        logger.info(f"   V8引擎规格: {self.engine.configuration}{self.engine.cylinder_count}, {self.engine.displacement_cc}cc")
        logger.info(f"   引擎功率: {self.engine.max_horsepower}hp")
        logger.info(f"   工厂等级: {self.factory.level}")
        logger.info(f"   生产数量: 50台")
        logger.info(f"   生产成本: ${self.production_details['total_cost']:,.2f}")
        logger.info(f"   平均单价: ${self.production_details['total_cost']/50:,.2f}/台")


def main():
    """主函数"""
    db = SessionLocal()
    
    try:
        test = ProductionFlowTest(db)
        success = test.run_test()
        
        if success:
            logger.info("\n" + "🎉" * 40)
            logger.info("测试全部通过！生产系统工作正常。")
            logger.info("🎉" * 40)
            sys.exit(0)
        else:
            logger.error("\n" + "❌" * 40)
            logger.error("测试失败！请检查上述错误信息。")
            logger.error("❌" * 40)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n测试执行异常: {str(e)}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

