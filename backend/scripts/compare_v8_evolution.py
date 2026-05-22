"""
V8引擎技术演进对比：1950 vs 2020

展示技术等级、材料和工艺的进步如何影响引擎性能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal, init_db
from backend.models.game_state import GameState
from backend.models.engineering import Engine
from backend.services.engineering_service import EngineeringService
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def compare_v8_engines():
    """对比1950年代和2020年代的V8引擎技术"""
    
    logger.info("=" * 80)
    logger.info("V8引擎技术演进对比：1950年 vs 2020年")
    logger.info("=" * 80)
    
    # 初始化数据库
    init_db()
    db = SessionLocal()
    
    try:
        # 获取游戏状态
        game = db.query(GameState).first()
        if not game:
            logger.error("未找到游戏状态，请先运行 init_world.py")
            return
        
        # ========== 1950年代V8引擎 ==========
        logger.info("\n" + "=" * 80)
        logger.info("创建 1950年代 V8引擎")
        logger.info("=" * 80)
        logger.info("技术特点：铸铁缸体、低压缩比、化油器、OHV配气")
        
        # 先检查是否已存在
        engine_1950_code = "ENG_V8_1950_CLASSIC"
        engine_1950 = db.query(Engine).filter(Engine.code == engine_1950_code).first()
        
        if engine_1950:
            logger.info(f"✓ 找到已存在的1950年代引擎: {engine_1950.code}")
        else:
            engine_1950 = EngineeringService.create_engine_with_calculations(
            db=db,
            game_id=game.id,
            company_id=None,
            name="Classic V8 5.7L (1950s)",
            code="ENG_V8_1950_CLASSIC",
            # 典型1950年代参数
            bore_mm=101.6,  # 4英寸
            stroke_mm=88.9,  # 3.5英寸
            cylinder_count=8,
            configuration="V",
            compression_ratio=8.0,  # 低压缩比（适应低标号汽油）
            induction_type="NA",
            boost_pressure_bar=0.0,
            material="CAST_IRON",  # 铸铁缸体（1950年代主流）
            valvetrain="OHV",  # 顶置气门（Overhead Valve）
            fuel_type="GASOLINE",
            tech_level=1,  # 1950年代技术水平
            development_cost=100.0
            )
            logger.info(f"\n✅ 1950年代V8引擎创建成功!")
        
        # 无论是新建还是已存在，都显示信息
        logger.info(f"   名称: {engine_1950.name}")
        logger.info(f"   代码: {engine_1950.code}")
        logger.info(f"   缸体材料: 铸铁")
        logger.info(f"   配气机构: OHV (顶置气门)")
        logger.info(f"   压缩比: {engine_1950.compression_ratio}:1")
        
        # ========== 2020年代V8引擎 ==========
        logger.info("\n" + "=" * 80)
        logger.info("创建 2020年代 V8引擎")
        logger.info("=" * 80)
        logger.info("技术特点：铝合金缸体、高压缩比、直喷、DOHC可变气门")
        
        # 先检查是否已存在
        engine_2020_code = "ENG_V8_2020_MODERN"
        engine_2020 = db.query(Engine).filter(Engine.code == engine_2020_code).first()
        
        if engine_2020:
            logger.info(f"✓ 找到已存在的2020年代引擎: {engine_2020.code}")
        else:
            engine_2020 = EngineeringService.create_engine_with_calculations(
            db=db,
            game_id=game.id,
            company_id=None,
            name="Modern V8 5.7L (2020s)",
            code="ENG_V8_2020_MODERN",
            # 相同排量，但现代技术
            bore_mm=101.6,  # 相同缸径
            stroke_mm=88.9,  # 相同行程
            cylinder_count=8,
            configuration="V",
            compression_ratio=12.5,  # 高压缩比（现代直喷技术）
            induction_type="NA",
            boost_pressure_bar=0.0,
            material="ALUMINUM",  # 铝合金缸体（轻量化）
            valvetrain="VARIABLE",  # 可变气门正时和升程
            fuel_type="GASOLINE",
            tech_level=10,  # 2020年代最高技术水平
            development_cost=500.0
            )
            logger.info(f"\n✅ 2020年代V8引擎创建成功!")
        
        # 无论是新建还是已存在，都显示信息
        logger.info(f"   名称: {engine_2020.name}")
        logger.info(f"   代码: {engine_2020.code}")
        logger.info(f"   缸体材料: 铝合金（轻量化）")
        logger.info(f"   配气机构: VARIABLE (可变气门)")
        logger.info(f"   压缩比: {engine_2020.compression_ratio}:1")
        
        # ========== 详细对比 ==========
        logger.info("\n" + "=" * 80)
        logger.info("详细性能对比")
        logger.info("=" * 80)
        
        # 排量对比
        logger.info(f"\n📏 排量:")
        logger.info(f"   1950年代: {engine_1950.displacement_cc} cc ({engine_1950.displacement_cc/1000:.2f}L)")
        logger.info(f"   2020年代: {engine_2020.displacement_cc} cc ({engine_2020.displacement_cc/1000:.2f}L)")
        logger.info(f"   差异: 相同排量（对比基准）")
        
        # 马力对比
        hp_diff = engine_2020.max_horsepower - engine_1950.max_horsepower
        hp_improvement = (hp_diff / engine_1950.max_horsepower) * 100
        logger.info(f"\n🔥 最大马力:")
        logger.info(f"   1950年代: {engine_1950.max_horsepower} HP @ {engine_1950.redline_rpm} RPM")
        logger.info(f"   2020年代: {engine_2020.max_horsepower} HP @ {engine_2020.redline_rpm} RPM")
        logger.info(f"   提升: +{hp_diff} HP ({hp_improvement:+.1f}%) ⚡")
        
        # 升功率对比
        logger.info(f"\n📊 升功率 (HP/L):")
        logger.info(f"   1950年代: {engine_1950.specific_output:.1f} HP/L")
        logger.info(f"   2020年代: {engine_2020.specific_output:.1f} HP/L")
        output_improvement = ((engine_2020.specific_output - engine_1950.specific_output) / engine_1950.specific_output) * 100
        logger.info(f"   提升: {output_improvement:+.1f}%")
        
        # 扭矩对比
        torque_diff = engine_2020.max_torque_nm - engine_1950.max_torque_nm
        torque_improvement = (torque_diff / engine_1950.max_torque_nm) * 100
        logger.info(f"\n💪 最大扭矩:")
        logger.info(f"   1950年代: {engine_1950.max_torque_nm} Nm")
        logger.info(f"   2020年代: {engine_2020.max_torque_nm} Nm")
        logger.info(f"   提升: +{torque_diff} Nm ({torque_improvement:+.1f}%)")
        
        # 重量对比
        weight_diff = engine_1950.weight_kg - engine_2020.weight_kg
        weight_reduction = (weight_diff / engine_1950.weight_kg) * 100
        logger.info(f"\n⚖️  引擎重量:")
        logger.info(f"   1950年代: {engine_1950.weight_kg:.1f} kg (铸铁)")
        logger.info(f"   2020年代: {engine_2020.weight_kg:.1f} kg (铝合金)")
        logger.info(f"   减重: -{weight_diff:.1f} kg ({weight_reduction:.1f}%) 🪶")
        
        # 尺寸对比
        vol_1950 = engine_1950.length_mm * engine_1950.width_mm * engine_1950.height_mm / 1_000_000
        vol_2020 = engine_2020.length_mm * engine_2020.width_mm * engine_2020.height_mm / 1_000_000
        vol_reduction = ((vol_1950 - vol_2020) / vol_1950) * 100
        logger.info(f"\n📦 体积 (长×宽×高):")
        logger.info(f"   1950年代: {engine_1950.length_mm:.0f} × {engine_1950.width_mm:.0f} × {engine_1950.height_mm:.0f} mm")
        logger.info(f"              体积: {vol_1950:.2f} 升")
        logger.info(f"   2020年代: {engine_2020.length_mm:.0f} × {engine_2020.width_mm:.0f} × {engine_2020.height_mm:.0f} mm")
        logger.info(f"              体积: {vol_2020:.2f} 升")
        logger.info(f"   体积减少: {vol_reduction:.1f}% (更紧凑的设计)")
        
        # 红线转速对比
        rpm_diff = engine_2020.redline_rpm - engine_1950.redline_rpm
        rpm_improvement = (rpm_diff / engine_1950.redline_rpm) * 100
        logger.info(f"\n🔄 红线转速:")
        logger.info(f"   1950年代: {engine_1950.redline_rpm:,} RPM")
        logger.info(f"   2020年代: {engine_2020.redline_rpm:,} RPM")
        logger.info(f"   提升: +{rpm_diff:,} RPM ({rpm_improvement:+.1f}%)")
        
        # 热负载对比
        thermal_diff = engine_2020.thermal_load - engine_1950.thermal_load
        logger.info(f"\n🌡️  热负载:")
        logger.info(f"   1950年代: {engine_1950.thermal_load:.1f}")
        logger.info(f"   2020年代: {engine_2020.thermal_load:.1f}")
        logger.info(f"   增加: +{thermal_diff:.1f} (高性能代价)")
        
        # 散热需求对比
        cooling_1950 = engine_1950.thermal_load * 2.0
        cooling_2020 = engine_2020.thermal_load * 2.0
        cooling_diff = cooling_2020 - cooling_1950
        logger.info(f"\n❄️  散热需求 (估算):")
        logger.info(f"   1950年代: {cooling_1950:.1f} kW")
        logger.info(f"   2020年代: {cooling_2020:.1f} kW")
        logger.info(f"   增加: +{cooling_diff:.1f} kW (需要更大散热器)")
        
        # 可靠性对比
        reliability_diff = engine_2020.reliability_base_score - engine_1950.reliability_base_score
        logger.info(f"\n🔧 基础可靠性:")
        logger.info(f"   1950年代: {engine_1950.reliability_base_score:.1f}/100")
        logger.info(f"   2020年代: {engine_2020.reliability_base_score:.1f}/100")
        logger.info(f"   提升: {reliability_diff:+.1f} 分 (现代材料和工艺)")
        
        # 燃油效率对比
        efficiency_diff = engine_2020.fuel_efficiency_rating - engine_1950.fuel_efficiency_rating
        bsfc_diff = engine_1950.bsfc_g_kwh - engine_2020.bsfc_g_kwh
        bsfc_improvement = (bsfc_diff / engine_1950.bsfc_g_kwh) * 100
        logger.info(f"\n⛽ 燃油效率:")
        logger.info(f"   1950年代: 评级 {engine_1950.fuel_efficiency_rating:.1f}/100, BSFC {engine_1950.bsfc_g_kwh:.1f} g/kWh")
        logger.info(f"   2020年代: 评级 {engine_2020.fuel_efficiency_rating:.1f}/100, BSFC {engine_2020.bsfc_g_kwh:.1f} g/kWh")
        logger.info(f"   改善: +{efficiency_diff:.1f} 分, BSFC降低 {bsfc_improvement:.1f}%")
        
        # 功重比对比
        pwr_1950 = engine_1950.max_horsepower / engine_1950.weight_kg
        pwr_2020 = engine_2020.max_horsepower / engine_2020.weight_kg
        pwr_improvement = ((pwr_2020 - pwr_1950) / pwr_1950) * 100
        logger.info(f"\n⚡ 功重比 (HP/kg):")
        logger.info(f"   1950年代: {pwr_1950:.3f} HP/kg")
        logger.info(f"   2020年代: {pwr_2020:.3f} HP/kg")
        logger.info(f"   提升: {pwr_improvement:+.1f}% (更轻更强)")
        
        # 制造成本对比
        cost_diff = engine_2020.manufacturing_cost - engine_1950.manufacturing_cost
        cost_increase = (cost_diff / engine_1950.manufacturing_cost) * 100
        logger.info(f"\n💰 制造成本:")
        logger.info(f"   1950年代: ${engine_1950.manufacturing_cost:,.2f}")
        logger.info(f"   2020年代: ${engine_2020.manufacturing_cost:,.2f}")
        logger.info(f"   增加: +${cost_diff:,.2f} ({cost_increase:+.1f}%) - 高科技的代价")
        
        # ========== 总结 ==========
        logger.info("\n" + "=" * 80)
        logger.info("技术演进总结")
        logger.info("=" * 80)
        
        logger.info("\n🚀 性能提升:")
        logger.info(f"   • 马力提升 {hp_improvement:.1f}% ({engine_1950.max_horsepower} → {engine_2020.max_horsepower} HP)")
        logger.info(f"   • 扭矩提升 {torque_improvement:.1f}% ({engine_1950.max_torque_nm} → {engine_2020.max_torque_nm} Nm)")
        logger.info(f"   • 功重比提升 {pwr_improvement:.1f}% ({pwr_1950:.2f} → {pwr_2020:.2f} HP/kg)")
        
        logger.info("\n♻️  效率改善:")
        logger.info(f"   • 燃效评级提升 {efficiency_diff:.1f} 分")
        logger.info(f"   • BSFC降低 {bsfc_improvement:.1f}%")
        logger.info(f"   • 可靠性提升 {reliability_diff:.1f} 分")
        
        logger.info("\n🪶 轻量化:")
        logger.info(f"   • 重量减少 {weight_reduction:.1f}% ({engine_1950.weight_kg:.1f} → {engine_2020.weight_kg:.1f} kg)")
        logger.info(f"   • 体积减少 {vol_reduction:.1f}%")
        
        logger.info("\n🔬 技术突破:")
        logger.info("   1950年代技术:")
        logger.info("     - 铸铁缸体（重但便宜）")
        logger.info("     - OHV配气（简单可靠）")
        logger.info("     - 低压缩比 8.0:1（低标号油）")
        logger.info("     - 化油器（技术成熟）")
        
        logger.info("\n   2020年代技术:")
        logger.info("     - 铝合金缸体（轻30-40%）")
        logger.info("     - 可变气门（优化全转速）")
        logger.info("     - 高压缩比 12.5:1（直喷技术）")
        logger.info("     - 电控系统（精确控制）")
        
        logger.info("\n💡 关键启示:")
        logger.info("   • 70年技术进步使同排量引擎性能提升50-70%")
        logger.info("   • 材料科学突破实现显著减重")
        logger.info("   • 燃效和可靠性同步提升")
        logger.info("   • 但制造成本大幅增加（高科技溢价）")
        logger.info("   • 散热需求随性能提升而增加")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ 对比完成！数据已保存到数据库")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"对比过程中出错: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    compare_v8_engines()

