"""
测试脚本：演示程序化车辆设计和外交系统

演示内容：
1. 创建程序化车身（连续参数）
2. 验证引擎兼容性
3. Executive Poaching（挖角高管）
4. PR Attack（公关攻击）
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy.orm import Session
from backend.database import get_db, engine
from backend.services.engineering_service import EngineeringService
from backend.core.engineering.chassis_math import MATERIALS, BodyDimensions
from backend.core.management.diplomacy import DiplomacyManager
from backend.models.game_state import GameState
from backend.models.company import Company
from backend.models.staff import Staff
from backend.models.engineering import Engine, Chassis
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def demo_procedural_vehicle(db: Session):
    """演示程序化车辆设计"""
    logger.info("\n" + "=" * 60)
    logger.info("演示 1: 程序化车身设计（Procedural Vehicle Design）")
    logger.info("=" * 60)
    
    # 获取游戏状态
    game = db.query(GameState).first()
    if not game:
        logger.error("未找到游戏状态，请先初始化游戏")
        return
    
    company = db.query(Company).filter(Company.is_player == True).first()
    if not company:
        logger.warning("未找到玩家公司，使用第一个公司")
        company = db.query(Company).first()
    
    logger.info(f"\n公司: {company.name}")
    
    # 场景1：创建紧凑型轿车（钢制车身）
    logger.info("\n--- 场景 1: 紧凑型轿车（钢制车身）---")
    
    try:
        chassis_steel, stats_steel = EngineeringService.create_procedural_body_chassis(
            db=db,
            game_id=game.id,
            company_id=company.id,
            name="Compact Steel Platform",
            code=f"PLAT_STEEL_COMPACT_{game.current_turn}",
            # 几何参数
            wheelbase_mm=2600,
            track_width_mm=1520,
            front_overhang_mm=800,
            rear_overhang_mm=850,
            bonnet_height_mm=680,
            roof_height_mm=1420,
            width_mm=1750,
            # 材料与技术
            panel_material="STEEL",
            body_style="SEDAN",
            layout="FF",
            tech_level=5
        )
        
        logger.info(f"✓ 钢制底盘创建成功: {chassis_steel.code}")
        logger.info(f"  - 总长: {stats_steel['total_length_mm']:.0f} mm")
        logger.info(f"  - 白车身重量: {stats_steel['biw_weight_kg']:.1f} kg")
        logger.info(f"  - 制造成本: ${stats_steel['biw_cost']:,.0f}")
        logger.info(f"  - 引擎舱容积: {stats_steel['engine_bay_volume_liters']:.1f} L")
        logger.info(f"  - 座舱容积: {stats_steel['cabin_volume_liters']:.1f} L")
        logger.info(f"  - 风阻系数: {stats_steel['drag_coefficient']:.3f}")
        
    except Exception as e:
        logger.error(f"钢制底盘创建失败: {e}", exc_info=True)
        return
    
    # 场景2：创建同样尺寸的铝制车身（对比）
    logger.info("\n--- 场景 2: 同款车型（铝制车身）---")
    
    try:
        chassis_alu, stats_alu = EngineeringService.create_procedural_body_chassis(
            db=db,
            game_id=game.id,
            company_id=company.id,
            name="Compact Aluminum Platform",
            code=f"PLAT_ALU_COMPACT_{game.current_turn}",
            # 相同几何参数
            wheelbase_mm=2600,
            track_width_mm=1520,
            front_overhang_mm=800,
            rear_overhang_mm=850,
            bonnet_height_mm=680,
            roof_height_mm=1420,
            width_mm=1750,
            # 铝制材料
            panel_material="ALUMINUM",
            body_style="SEDAN",
            layout="FF",
            tech_level=5
        )
        
        logger.info(f"✓ 铝制底盘创建成功: {chassis_alu.code}")
        logger.info(f"  - 白车身重量: {stats_alu['biw_weight_kg']:.1f} kg "
                   f"({stats_steel['biw_weight_kg'] - stats_alu['biw_weight_kg']:.1f} kg 更轻！)")
        logger.info(f"  - 制造成本: ${stats_alu['biw_cost']:,.0f} "
                   f"(+${stats_alu['biw_cost'] - stats_steel['biw_cost']:,.0f} vs 钢制)")
        
        weight_saving_pct = (1 - stats_alu['biw_weight_kg'] / stats_steel['biw_weight_kg']) * 100
        cost_increase_pct = (stats_alu['biw_cost'] / stats_steel['biw_cost'] - 1) * 100
        
        logger.info(f"\n权衡分析:")
        logger.info(f"  - 重量节省: {weight_saving_pct:.1f}%")
        logger.info(f"  - 成本增加: {cost_increase_pct:.1f}%")
        
    except Exception as e:
        logger.error(f"铝制底盘创建失败: {e}", exc_info=True)
    
    # 场景3：引擎兼容性检查
    logger.info("\n--- 场景 3: 引擎兼容性检查 ---")
    
    # 获取一个引擎
    engine = db.query(Engine).first()
    if engine:
        logger.info(f"\n测试引擎: {engine.name} ({engine.code})")
        logger.info(f"  尺寸: {engine.length_mm:.0f} × {engine.width_mm:.0f} × {engine.height_mm:.0f} mm")
        logger.info(f"  热负载: {engine.thermal_load:.1f}")
        
        # 测试钢制底盘
        compat_steel, msg_steel = EngineeringService.validate_engine_fits_procedural_body(
            engine, chassis_steel
        )
        logger.info(f"\n钢制底盘兼容性: {msg_steel}")
        
        # 测试铝制底盘
        compat_alu, msg_alu = EngineeringService.validate_engine_fits_procedural_body(
            engine, chassis_alu
        )
        logger.info(f"铝制底盘兼容性: {msg_alu}")
    else:
        logger.warning("未找到引擎，跳过兼容性测试")


def demo_diplomacy(db: Session):
    """演示外交系统"""
    logger.info("\n" + "=" * 60)
    logger.info("演示 2: 外交系统（Diplomacy & Dirty Tricks）")
    logger.info("=" * 60)
    
    # 获取游戏状态
    game = db.query(GameState).first()
    if not game:
        logger.error("未找到游戏状态")
        return
    
    # 获取两个公司
    companies = db.query(Company).limit(2).all()
    if len(companies) < 2:
        logger.error("需要至少2个公司进行演示")
        return
    
    company_a = companies[0]
    company_b = companies[1]
    
    logger.info(f"\n公司 A: {company_a.name} (Cash: ${company_a.cash_balance:,.0f})")
    logger.info(f"公司 B: {company_b.name} (Cash: ${company_b.cash_balance:,.0f})")
    
    # 初始化外交管理器
    diplomacy_mgr = DiplomacyManager(db)
    
    # 场景1：Executive Poaching
    logger.info("\n--- 场景 1: 挖角高管（Executive Poaching）---")
    
    # 获取公司B的一个高管
    target_executive = db.query(Staff).filter(
        Staff.company_id == company_b.id,
        Staff.position.in_(["CEO", "CTO", "CFO", "CMO", "COO"])
    ).first()
    
    if target_executive:
        logger.info(f"\n目标高管: {target_executive.first_name} {target_executive.last_name} ({target_executive.position})")
        logger.info(f"  当前薪资: ${target_executive.salary:,.0f}/年")
        logger.info(f"  忠诚度: {target_executive.loyalty:.1f}/100")
        logger.info(f"  士气: {target_executive.morale:.1f}/100")
        
        # 尝试挖角（提供1.5倍薪资）
        offer = target_executive.salary * 1.5
        logger.info(f"\n公司 A 出价: ${offer:,.0f}/年 (1.5倍)")
        
        try:
            success, message, details = diplomacy_mgr.attempt_poach_executive(
                poaching_company_id=company_a.id,
                target_executive_id=target_executive.id,
                salary_offer=offer,
                game_id=game.id,
                current_turn=game.current_turn
            )
            
            logger.info(f"\n结果: {message}")
            if success:
                logger.info(f"  ✓ 高管成功跳槽！")
                logger.info(f"  - 新雇主: 公司 {company_a.id}")
                logger.info(f"  - 关系影响: {details['relation_impact']:.0f}")
            else:
                logger.info(f"  ✗ 挖角失败，高管拒绝")
                logger.info(f"  - 高管忠诚度提升: +10")
                logger.info(f"  - 关系影响: {details['relation_impact']:.0f}")
            
        except Exception as e:
            logger.error(f"挖角失败: {e}", exc_info=True)
    else:
        logger.warning("未找到可挖角的高管")
    
    # 场景2：PR Attack
    logger.info("\n--- 场景 2: 公关攻击（PR Attack / Smear Campaign）---")
    
    logger.info(f"\n公司 B 品牌声望: {company_b.brand_prestige:.1f}")
    
    # 公司A对公司B发起200万预算的公关攻击
    budget = 2_000_000
    logger.info(f"\n公司 A 发起公关攻击，预算: ${budget:,.0f}")
    logger.info(f"  预期伤害: {(budget / 1_000_000) * 5.0:.1f} 品牌声望点")
    logger.info(f"  反噬风险: 10%")
    
    try:
        success, message, details = diplomacy_mgr.launch_smear_campaign(
            attacker_company_id=company_a.id,
            target_company_id=company_b.id,
            budget=budget,
            target_region_id=None,  # 全球攻击
            game_id=game.id,
            current_turn=game.current_turn
        )
        
        logger.info(f"\n结果: {message}")
        
        if details.get("backfired"):
            logger.info(f"  ✗ 攻击反噬！")
            logger.info(f"  - 公司 A 自身品牌受损: {details['self_damage']:.1f}")
            logger.info(f"  - 预算浪费: ${details['budget_wasted']:,.0f}")
        else:
            logger.info(f"  ✓ 攻击成功！")
            logger.info(f"  - 目标品牌伤害: {details['damage_dealt']:.1f}")
            logger.info(f"  - 目标新声望: {details['target_new_prestige']:.1f}")
            logger.info(f"  - 关系影响: {details['relation_impact']:.0f}")
        
    except Exception as e:
        logger.error(f"公关攻击失败: {e}", exc_info=True)
    
    # 查询关系
    logger.info("\n--- 公司关系查询 ---")
    
    relation = diplomacy_mgr.get_or_create_relation(
        company_a.id, company_b.id, game.id
    )
    
    logger.info(f"\n公司 A → 公司 B 关系: {relation.relation_score:.1f}")
    logger.info(f"  - 正面行动: {relation.total_positive_actions}")
    logger.info(f"  - 负面行动: {relation.total_negative_actions}")
    logger.info(f"  - 禁运状态: {'是' if relation.is_embargo else '否'}")
    logger.info(f"  - 结盟状态: {'是' if relation.is_alliance else '否'}")


def main():
    """主函数"""
    logger.info("\n" + "=" * 80)
    logger.info("AutoMogul v1.4 新功能演示")
    logger.info("Procedural Vehicle Design & Diplomacy System")
    logger.info("=" * 80)
    
    # 显示可用材料
    logger.info("\n可用材料特性:")
    for mat_code, mat in MATERIALS.items():
        logger.info(f"\n  {mat_code}:")
        logger.info(f"    - 密度: {mat.density_kg_m3} kg/m³")
        logger.info(f"    - 成本: ${mat.cost_per_m2}/m²")
        logger.info(f"    - 强度系数: {mat.strength_multiplier}")
        logger.info(f"    - 所需技术等级: {mat.tech_level_required}")
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 演示1：程序化车辆
        demo_procedural_vehicle(db)
        
        # 演示2：外交系统
        demo_diplomacy(db)
        
        logger.info("\n" + "=" * 80)
        logger.info("演示完成！")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"演示失败: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()

