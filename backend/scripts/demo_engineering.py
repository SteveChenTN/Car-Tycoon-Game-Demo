"""
工程系统演示脚本

展示如何使用工程核心系统创建引擎、底盘和车辆配置
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal, init_db
from backend.models.game_state import GameState
from backend.services.engineering_service import EngineeringService
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def demo_engineering_system():
    """演示工程系统的完整流程"""
    
    logger.info("=" * 80)
    logger.info("工程系统演示 - 硬核物理驱动的车辆设计")
    logger.info("=" * 80)
    
    # 初始化数据库
    init_db()
    db = SessionLocal()
    
    try:
        # 获取或创建游戏状态
        game = db.query(GameState).first()
        if not game:
            logger.error("未找到游戏状态，请先运行 init_world.py")
            return
        
        logger.info(f"\n游戏状态: {game.current_year}年 第{game.current_month}月")
        
        # ========== 示例1: 创建经济型4缸引擎 ==========
        logger.info("\n" + "=" * 80)
        logger.info("示例1: 创建经济型 2.0L 自然吸气 直列4缸引擎")
        logger.info("=" * 80)
        
        engine_eco = EngineeringService.create_engine_with_calculations(
            db=db,
            game_id=game.id,
            company_id=None,  # 通用引擎
            name="EcoLine 2.0 NA",
            code="ENG_ECO_2000_NA",
            bore_mm=86.0,
            stroke_mm=86.0,  # 方形设计（bore = stroke）
            cylinder_count=4,
            configuration="INLINE",
            compression_ratio=11.0,  # 高压缩比提升效率
            induction_type="NA",
            boost_pressure_bar=0.0,
            material="ALUMINUM",
            valvetrain="DOHC",
            fuel_type="GASOLINE",
            tech_level=6,
            development_cost=150.0
        )
        
        logger.info(f"\n✅ 引擎创建成功!")
        logger.info(f"   代码: {engine_eco.code}")
        logger.info(f"   排量: {engine_eco.displacement_cc} cc ({engine_eco.displacement_cc/1000:.1f}L)")
        logger.info(f"   功率: {engine_eco.max_horsepower} HP @ {engine_eco.redline_rpm} RPM")
        logger.info(f"   扭矩: {engine_eco.max_torque_nm} Nm")
        logger.info(f"   升功率: {engine_eco.specific_output:.1f} HP/L")
        logger.info(f"   重量: {engine_eco.weight_kg} kg")
        logger.info(f"   尺寸: {engine_eco.length_mm:.0f} × {engine_eco.width_mm:.0f} × {engine_eco.height_mm:.0f} mm")
        logger.info(f"   热负载: {engine_eco.thermal_load:.1f}")
        logger.info(f"   可靠性: {engine_eco.reliability_base_score:.1f}/100")
        logger.info(f"   燃效评级: {engine_eco.fuel_efficiency_rating:.1f}/100")
        logger.info(f"   制造成本: ${engine_eco.manufacturing_cost:.2f}")
        
        # ========== 示例2: 创建高性能涡轮增压引擎 ==========
        logger.info("\n" + "=" * 80)
        logger.info("示例2: 创建高性能 2.0L 涡轮增压 直列4缸引擎")
        logger.info("=" * 80)
        
        engine_turbo = EngineeringService.create_engine_with_calculations(
            db=db,
            game_id=game.id,
            company_id=None,
            name="PowerBoost 2.0T",
            code="ENG_SPORT_2000_TURBO",
            bore_mm=86.0,
            stroke_mm=86.0,
            cylinder_count=4,
            configuration="INLINE",
            compression_ratio=9.5,  # 涡轮引擎需要较低压缩比
            induction_type="TURBO",
            boost_pressure_bar=1.5,  # 1.5 bar增压
            material="ALUMINUM",
            valvetrain="DOHC",
            fuel_type="GASOLINE",
            tech_level=8,  # 高科技等级
            development_cost=300.0
        )
        
        logger.info(f"\n✅ 涡轮引擎创建成功!")
        logger.info(f"   代码: {engine_turbo.code}")
        logger.info(f"   排量: {engine_turbo.displacement_cc} cc ({engine_turbo.displacement_cc/1000:.1f}L)")
        logger.info(f"   功率: {engine_turbo.max_horsepower} HP @ {engine_turbo.redline_rpm} RPM")
        logger.info(f"   扭矩: {engine_turbo.max_torque_nm} Nm")
        logger.info(f"   升功率: {engine_turbo.specific_output:.1f} HP/L ⚡")
        logger.info(f"   重量: {engine_turbo.weight_kg} kg")
        logger.info(f"   尺寸: {engine_turbo.length_mm:.0f} × {engine_turbo.width_mm:.0f} × {engine_turbo.height_mm:.0f} mm")
        logger.info(f"   热负载: {engine_turbo.thermal_load:.1f} 🔥")
        logger.info(f"   可靠性: {engine_turbo.reliability_base_score:.1f}/100")
        logger.info(f"   制造成本: ${engine_turbo.manufacturing_cost:.2f}")
        
        # ========== 示例3: 创建V6引擎 ==========
        logger.info("\n" + "=" * 80)
        logger.info("示例3: 创建豪华 3.5L V6引擎")
        logger.info("=" * 80)
        
        engine_v6 = EngineeringService.create_engine_with_calculations(
            db=db,
            game_id=game.id,
            company_id=None,
            name="Luxury V6 3.5",
            code="ENG_LUXURY_3500_V6",
            bore_mm=94.0,
            stroke_mm=84.0,
            cylinder_count=6,
            configuration="V",  # V型配置
            compression_ratio=11.5,
            induction_type="NA",
            boost_pressure_bar=0.0,
            material="ALUMINUM",
            valvetrain="DOHC",
            fuel_type="GASOLINE",
            tech_level=7,
            development_cost=250.0
        )
        
        logger.info(f"\n✅ V6引擎创建成功!")
        logger.info(f"   代码: {engine_v6.code}")
        logger.info(f"   排量: {engine_v6.displacement_cc} cc ({engine_v6.displacement_cc/1000:.1f}L)")
        logger.info(f"   功率: {engine_v6.max_horsepower} HP @ {engine_v6.redline_rpm} RPM")
        logger.info(f"   扭矩: {engine_v6.max_torque_nm} Nm")
        logger.info(f"   升功率: {engine_v6.specific_output:.1f} HP/L")
        logger.info(f"   重量: {engine_v6.weight_kg} kg")
        logger.info(f"   尺寸: {engine_v6.length_mm:.0f} × {engine_v6.width_mm:.0f} × {engine_v6.height_mm:.0f} mm")
        logger.info(f"   可靠性: {engine_v6.reliability_base_score:.1f}/100")
        
        # ========== 示例4: 创建紧凑型底盘 ==========
        logger.info("\n" + "=" * 80)
        logger.info("示例4: 创建紧凑型前驱底盘")
        logger.info("=" * 80)
        
        chassis_compact = EngineeringService.create_chassis(
            db=db,
            game_id=game.id,
            company_id=None,
            name="Compact FWD Platform",
            code="CHS_COMPACT_FWD",
            wheelbase_mm=2650,
            track_front_mm=1520,
            track_rear_mm=1510,
            layout="FF",  # 前置前驱
            engine_bay_length_mm=750,  # 紧凑引擎舱
            engine_bay_width_mm=650,
            engine_bay_height_mm=550,
            max_cooling_capacity_kw=80,  # 中等冷却容量
            material="STEEL",
            rigidity_rating=60.0,
            crash_test_rating=70.0,
            tech_level=5,
            development_cost=400.0
        )
        
        logger.info(f"\n✅ 底盘创建成功!")
        logger.info(f"   代码: {chassis_compact.code}")
        logger.info(f"   轴距: {chassis_compact.wheelbase_mm} mm")
        logger.info(f"   布局: {chassis_compact.layout}")
        logger.info(f"   引擎舱: {chassis_compact.engine_bay_length_mm:.0f} × {chassis_compact.engine_bay_width_mm:.0f} × {chassis_compact.engine_bay_height_mm:.0f} mm")
        logger.info(f"   冷却容量: {chassis_compact.max_cooling_capacity_kw} kW")
        logger.info(f"   重量: {chassis_compact.weight_kg} kg")
        logger.info(f"   刚性: {chassis_compact.rigidity_rating}/100")
        logger.info(f"   制造成本: ${chassis_compact.manufacturing_cost:.2f}")
        db.commit()  # 提交底盘创建
        
        # ========== 示例5: 创建运动型底盘 ==========
        logger.info("\n" + "=" * 80)
        logger.info("示例5: 创建运动型后驱底盘")
        logger.info("=" * 80)
        
        chassis_sport = EngineeringService.create_chassis(
            db=db,
            game_id=game.id,
            company_id=None,
            name="Sport RWD Platform",
            code="CHS_SPORT_RWD",
            wheelbase_mm=2750,
            track_front_mm=1560,
            track_rear_mm=1580,
            layout="FR",  # 前置后驱
            engine_bay_length_mm=900,  # 更大引擎舱
            engine_bay_width_mm=750,
            engine_bay_height_mm=650,
            max_cooling_capacity_kw=120,  # 高冷却容量
            material="ALUMINUM",  # 铝合金底盘
            rigidity_rating=80.0,
            crash_test_rating=75.0,
            tech_level=7,
            development_cost=600.0
        )
        
        logger.info(f"\n✅ 运动底盘创建成功!")
        logger.info(f"   代码: {chassis_sport.code}")
        logger.info(f"   轴距: {chassis_sport.wheelbase_mm} mm")
        logger.info(f"   布局: {chassis_sport.layout}")
        logger.info(f"   引擎舱: {chassis_sport.engine_bay_length_mm:.0f} × {chassis_sport.engine_bay_width_mm:.0f} × {chassis_sport.engine_bay_height_mm:.0f} mm")
        logger.info(f"   冷却容量: {chassis_sport.max_cooling_capacity_kw} kW")
        logger.info(f"   重量: {chassis_sport.weight_kg} kg (铝合金)")
        logger.info(f"   刚性: {chassis_sport.rigidity_rating}/100")
        
        # ========== 示例6: 兼容性检查 ==========
        logger.info("\n" + "=" * 80)
        logger.info("示例6: 兼容性检查")
        logger.info("=" * 80)
        
        # 检查经济引擎 + 紧凑底盘
        logger.info(f"\n检查: {engine_eco.name} + {chassis_compact.name}")
        compat1, msg1, details1 = EngineeringService.check_compatibility(
            db, engine_eco.id, chassis_compact.id
        )
        logger.info(f"   结果: {'✅ ' + msg1 if compat1 else '❌ ' + msg1}")
        logger.info(f"   长度余量: {details1['clearances']['length_mm']:.0f} mm")
        logger.info(f"   宽度余量: {details1['clearances']['width_mm']:.0f} mm")
        logger.info(f"   高度余量: {details1['clearances']['height_mm']:.0f} mm")
        logger.info(f"   冷却余量: {details1['clearances']['cooling_margin_kw']:.1f} kW")
        
        # 检查涡轮引擎 + 紧凑底盘（可能不兼容）
        logger.info(f"\n检查: {engine_turbo.name} + {chassis_compact.name}")
        compat2, msg2, details2 = EngineeringService.check_compatibility(
            db, engine_turbo.id, chassis_compact.id
        )
        logger.info(f"   结果: {'✅ ' + msg2 if compat2 else '❌ ' + msg2}")
        if compat2:
            logger.info(f"   冷却余量: {details2['clearances']['cooling_margin_kw']:.1f} kW")
        
        # 检查涡轮引擎 + 运动底盘
        logger.info(f"\n检查: {engine_turbo.name} + {chassis_sport.name}")
        compat3, msg3, details3 = EngineeringService.check_compatibility(
            db, engine_turbo.id, chassis_sport.id
        )
        logger.info(f"   结果: {'✅ ' + msg3 if compat3 else '❌ ' + msg3}")
        logger.info(f"   冷却余量: {details3['clearances']['cooling_margin_kw']:.1f} kW")
        
        # ========== 示例7: 创建车辆配置 ==========
        logger.info("\n" + "=" * 80)
        logger.info("示例7: 组装完整车辆")
        logger.info("=" * 80)
        
        # 创建经济型轿车
        logger.info(f"\n组装: 经济型紧凑轿车")
        car_eco, car_msg1 = EngineeringService.create_car_trim(
            db=db,
            game_id=game.id,
            company_id=1,  # 虚拟公司ID（演示用）
            name="Base",
            model_name="Civic",
            trim_code="CIVIC_BASE_2024",
            engine_id=engine_eco.id,
            chassis_id=chassis_compact.id,
            body_style="SEDAN",
            body_weight_kg=380,
            drag_coefficient=0.28,
            frontal_area_sqm=2.3,
            seating_capacity=5,
            cargo_volume_liters=450,
            segment="COMPACT",
            msrp=22000,
            tire_grip=0.95
        )
        
        if car_eco:
            logger.info(f"\n✅ 车辆创建成功!")
            logger.info(f"   型号: {car_eco.model_name} {car_eco.name}")
            logger.info(f"   代码: {car_eco.trim_code}")
            logger.info(f"   总重: {car_eco.total_weight_kg:.0f} kg")
            logger.info(f"   推重比: {car_eco.power_to_weight_ratio:.3f} hp/kg")
            logger.info(f"   0-100km/h: {car_eco.zero_to_hundred_kph_sec:.2f} 秒")
            logger.info(f"   最高速度: {car_eco.top_speed_kph:.0f} km/h")
            logger.info(f"   1/4英里: {car_eco.quarter_mile_sec:.2f} 秒")
            logger.info(f"   刹车距离: {car_eco.braking_100_0_meters:.1f} 米")
            logger.info(f"   横向G值: {car_eco.lateral_g_force:.2f} G")
            logger.info(f"   油耗: {car_eco.fuel_economy_l_100km:.1f} L/100km")
            logger.info(f"   可靠性: {car_eco.final_reliability_score:.1f}/100")
            logger.info(f"   制造成本: ${car_eco.manufacturing_cost:.2f}")
            logger.info(f"   建议零售价: ${car_eco.msrp:.2f}")
            logger.info(f"   利润率: {((car_eco.msrp - car_eco.manufacturing_cost) / car_eco.msrp * 100):.1f}%")
        else:
            logger.error(f"❌ 车辆创建失败: {car_msg1}")
        
        # 创建运动型轿车
        logger.info(f"\n组装: 运动型轿车")
        car_sport, car_msg2 = EngineeringService.create_car_trim(
            db=db,
            game_id=game.id,
            company_id=1,  # 虚拟公司ID（演示用）
            name="Sport",
            model_name="Mustang",
            trim_code="MUSTANG_SPORT_2024",
            engine_id=engine_turbo.id,
            chassis_id=chassis_sport.id,
            body_style="COUPE",
            body_weight_kg=420,
            drag_coefficient=0.32,
            frontal_area_sqm=2.4,
            seating_capacity=4,
            cargo_volume_liters=350,
            segment="SPORTS",
            msrp=38000,
            tire_grip=1.1  # 高性能轮胎
        )
        
        if car_sport:
            logger.info(f"\n✅ 运动车型创建成功!")
            logger.info(f"   型号: {car_sport.model_name} {car_sport.name}")
            logger.info(f"   代码: {car_sport.trim_code}")
            logger.info(f"   总重: {car_sport.total_weight_kg:.0f} kg")
            logger.info(f"   推重比: {car_sport.power_to_weight_ratio:.3f} hp/kg ⚡")
            logger.info(f"   0-100km/h: {car_sport.zero_to_hundred_kph_sec:.2f} 秒 🚀")
            logger.info(f"   最高速度: {car_sport.top_speed_kph:.0f} km/h")
            logger.info(f"   横向G值: {car_sport.lateral_g_force:.2f} G")
            logger.info(f"   油耗: {car_sport.fuel_economy_l_100km:.1f} L/100km")
            logger.info(f"   可靠性: {car_sport.final_reliability_score:.1f}/100")
            logger.info(f"   建议零售价: ${car_sport.msrp:.2f}")
        else:
            logger.error(f"❌ 车辆创建失败: {car_msg2}")
        
        # ========== 总结 ==========
        logger.info("\n" + "=" * 80)
        logger.info("演示完成!")
        logger.info("=" * 80)
        logger.info(f"\n创建的组件:")
        logger.info(f"   ✅ {3} 个引擎")
        logger.info(f"   ✅ {2} 个底盘")
        logger.info(f"   ✅ {2 if car_eco and car_sport else 1 if car_eco or car_sport else 0} 个车辆配置")
        logger.info(f"\n所有数据已保存到数据库: {db.bind.url}")
        logger.info(f"\n关键特性:")
        logger.info(f"   🔬 基于真实物理公式，无随机数")
        logger.info(f"   ⚙️  自动计算所有派生参数")
        logger.info(f"   🔍 严格的兼容性检查")
        logger.info(f"   📊 详细的性能指标")
        logger.info(f"   💰 成本和定价分析")
        
    except Exception as e:
        logger.error(f"演示过程中出错: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    demo_engineering_system()

