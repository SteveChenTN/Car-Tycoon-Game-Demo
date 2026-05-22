"""
工程物理计算引擎 - 硬核模拟的数学核心

基于真实物理公式，无随机数
所有性能参数从基础物理量派生

数据驱动：所有常量从 GameDataLoader 加载
"""
import math
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# 导入工程核心物理引擎
try:
    from backend.logic.engineering_core import EngineeringCore, MATERIAL_GRADES
    ENGINEERING_CORE_AVAILABLE = True
except ImportError:
    ENGINEERING_CORE_AVAILABLE = False
    logger.warning("EngineeringCore 未找到，将使用旧的计算方法")


@dataclass
class EngineSpecs:
    """引擎规格数据类"""
    bore_mm: float
    stroke_mm: float
    cylinder_count: int
    configuration: str
    compression_ratio: float
    induction_type: str
    boost_pressure_bar: float
    material: str
    valvetrain: str
    fuel_type: str
    tech_level: int


@dataclass
class ChassisSpecs:
    """底盘规格数据类"""
    wheelbase_mm: int
    layout: str
    engine_bay_length_mm: float
    engine_bay_width_mm: float
    engine_bay_height_mm: float
    max_cooling_capacity_kw: float
    material: str
    rigidity_rating: float
    weight_kg: float


@dataclass
class PerformanceResult:
    """性能计算结果"""
    zero_to_hundred_kph_sec: float
    top_speed_kph: float
    quarter_mile_sec: float
    braking_100_0_meters: float
    lateral_g_force: float
    fuel_economy_l_100km: float


class EngineeringCalculator:
    """
    工程计算器 - 所有物理计算的中心
    
    设计原则：
    1. 所有方法都是静态的，无状态
    2. 每个方法都有详细的物理公式注释
    3. 使用SI单位进行内部计算，输入输出可以是其他单位
    4. 考虑边界条件和物理限制
    5. 数据驱动：从 GameDataLoader 加载常量
    """
    
    # 数据加载器引用（在初始化时设置）
    _data_loader = None
    
    @classmethod
    def set_data_loader(cls, loader):
        """
        设置数据加载器（服务器启动时调用）
        
        Args:
            loader: GameDataLoader 实例
        """
        cls._data_loader = loader
        logger.info("EngineeringCalculator: 数据加载器已设置")
    
    @classmethod
    def _get_constant(cls, name: str, default=None):
        """从数据加载器获取物理常数"""
        if cls._data_loader:
            return cls._data_loader.get_physics_constant(name, default)
        # 如果数据未加载，使用默认值（向后兼容）
        logger.warning(f"数据加载器未初始化，使用默认值: {name}")
        return default
    
    # ========== 物理常量（懒加载属性）==========
    @property
    def PI(self) -> float:
        return self._get_constant("PI", math.pi)
    
    @property
    def GRAVITY(self) -> float:
        return self._get_constant("GRAVITY", 9.81)
    
    @property
    def AIR_DENSITY(self) -> float:
        return self._get_constant("AIR_DENSITY", 1.225)
    
    @classmethod
    def _get_engine_material_data(cls, material: str, key: str, default):
        """从数据加载器获取引擎材料属性"""
        if cls._data_loader:
            mat_data = cls._data_loader.get_engine_material(material)
            if mat_data:
                return mat_data.get(key, default)
        return default
    
    @classmethod
    def _get_fuel_property(cls, fuel: str, key: str, default):
        """从数据加载器获取燃料属性"""
        if cls._data_loader:
            fuel_data = cls._data_loader.get_fuel_properties(fuel)
            if fuel_data:
                return fuel_data.get(key, default)
        return default
    
    @staticmethod
    def calculate_displacement(bore_mm: float, stroke_mm: float, cylinder_count: int) -> int:
        """
        计算排量（cc）
        
        公式：V = π × (bore/2)² × stroke × cylinders
        
        Args:
            bore_mm: 缸径（毫米）
            stroke_mm: 行程（毫米）
            cylinder_count: 缸数
            
        Returns:
            排量（立方厘米）
        """
        bore_m = bore_mm / 1000.0
        stroke_m = stroke_mm / 1000.0
        
        # 单缸排量（立方米）
        single_cylinder_volume = math.pi * (bore_m / 2.0) ** 2 * stroke_m
        
        # 总排量（立方厘米）
        total_displacement_cc = single_cylinder_volume * cylinder_count * 1_000_000
        
        return int(round(total_displacement_cc))
    
    @staticmethod
    def calculate_engine_dimensions(
        bore_mm: float,
        stroke_mm: float,
        cylinder_count: int,
        configuration: str,
        induction_type: str
    ) -> Tuple[float, float, float]:
        """
        计算引擎尺寸（长×宽×高，毫米）
        
        基于配置类型的几何约束：
        - INLINE（直列）: 长，窄
        - V型: 短，宽
        - BOXER（水平对置）: 短，宽，矮
        - 涡轮增压增加高度和长度
        
        Args:
            bore_mm: 缸径
            stroke_mm: 行程
            cylinder_count: 缸数
            configuration: 配置类型
            induction_type: 进气类型
            
        Returns:
            (length_mm, width_mm, height_mm)
        """
        # 基础尺寸估算（基于缸径和行程）
        base_cylinder_length = stroke_mm * 1.5  # 包含连杆空间
        base_width = bore_mm * 1.3  # 包含缸壁和水道
        base_height = stroke_mm * 2.0 + bore_mm  # 曲轴箱 + 行程 + 缸头
        
        # 根据配置调整
        if configuration == "INLINE":
            length = base_cylinder_length * cylinder_count
            width = base_width
            height = base_height
            
        elif configuration == "V":
            # V型引擎：缸数减半，宽度增加
            length = base_cylinder_length * (cylinder_count / 2)
            width = base_width * 2.2  # V角度导致宽度增加
            height = base_height * 1.1
            
        elif configuration == "BOXER":
            # 水平对置：最短最宽最矮
            length = base_cylinder_length * (cylinder_count / 2)
            width = base_width * 3.0  # 左右分开
            height = base_height * 0.6  # 低重心
            
        elif configuration == "VR":
            # VR型：介于直列和V之间
            length = base_cylinder_length * (cylinder_count * 0.7)
            width = base_width * 1.5
            height = base_height * 1.05
            
        elif configuration == "W":
            # W型：非常紧凑
            length = base_cylinder_length * (cylinder_count / 3)
            width = base_width * 2.5
            height = base_height * 1.2
            
        else:
            # 默认按直列处理
            length = base_cylinder_length * cylinder_count
            width = base_width
            height = base_height
        
        # 涡轮增压增加尺寸
        if induction_type in ["TURBO", "TWINTURBO"]:
            length *= 1.15  # 涡轮和管路
            height *= 1.25  # 进气歧管高度
        elif induction_type == "SUPERCHARGED":
            length *= 1.10
            height *= 1.20
        
        return (round(length, 1), round(width, 1), round(height, 1))
    
    @staticmethod
    def calculate_engine_weight(
        displacement_cc: int,
        configuration: str,
        material: str,
        induction_type: str,
        tech_level: int,
        material_grade_id: Optional[str] = None,
        process_id: Optional[str] = None,
        current_year: Optional[int] = None,
        stroke_mm: Optional[float] = None
    ) -> float:
        """
        计算引擎重量（kg）
        
        现在使用 EngineeringCore 物理引擎进行硬核模拟计算。
        如果提供了 material_grade_id 和 process_id，将使用新的物理引擎。
        否则，使用向后兼容的旧方法。
        
        基于：
        - 排量（主要因素）
        - 材料密度
        - 配置复杂度
        - 增压系统重量
        - 技术等级（高科技 = 更轻）
        - 制造工艺（锻造 vs 铸造）
        
        经验公式：Weight ≈ Displacement × Material_Factor × Config_Factor
        """
        # 如果提供了新参数且 EngineeringCore 可用，使用新的物理引擎
        if (ENGINEERING_CORE_AVAILABLE and 
            material_grade_id and 
            process_id and 
            current_year is not None and
            stroke_mm is not None):
            
            try:
                # 使用 EngineeringCore 评估引擎缸体
                result = EngineeringCore.evaluate_engine_block(
                    displacement_cc=displacement_cc,
                    layout=configuration,
                    material_grade_id=material_grade_id,
                    process_id=process_id,
                    current_year=current_year,
                    stroke_mm=stroke_mm,
                    tech_intro_year=current_year - tech_level * 2
                )
                
                block_weight = result["block_weight_kg"]
                
                # 增压系统重量（仍然使用旧方法，因为这是附加组件）
                displacement_liters = displacement_cc / 1000.0
                induction_weight = {
                    "NA": 0,
                    "TURBO": 15 + displacement_liters * 5,
                    "TWINTURBO": 25 + displacement_liters * 8,
                    "SUPERCHARGED": 20 + displacement_liters * 6,
                }.get(induction_type, 0)
                
                total_weight = block_weight + induction_weight
                
                return round(total_weight, 1)
                
            except Exception as e:
                logger.warning(f"使用 EngineeringCore 计算引擎重量失败，回退到旧方法: {e}")
                # 继续使用旧方法
        
        # 向后兼容：使用旧的计算方法
        # 基础重量：每升排量约50-80kg（铸铁）
        base_weight_per_liter = 65.0
        displacement_liters = displacement_cc / 1000.0
        
        base_weight = displacement_liters * base_weight_per_liter
        
        # 材料系数（从数据加载器获取）
        material_factor = EngineeringCalculator._get_engine_material_data(
            material, "weight_factor", 1.0
        )
        
        # 配置系数（复杂配置更重）
        config_factor = {
            "INLINE": 1.0,
            "V": 1.15,  # V型需要更多结构件
            "BOXER": 1.20,  # 水平对置结构复杂
            "VR": 1.12,
            "W": 1.25,
        }.get(configuration, 1.0)
        
        # 增压系统重量
        induction_weight = {
            "NA": 0,
            "TURBO": 15 + displacement_liters * 5,  # 涡轮+管路
            "TWINTURBO": 25 + displacement_liters * 8,
            "SUPERCHARGED": 20 + displacement_liters * 6,
        }.get(induction_type, 0)
        
        # 技术等级减重（高科技材料和工艺）
        tech_factor = 1.0 - (tech_level - 1) * 0.03  # 每级减重3%
        
        total_weight = (base_weight * material_factor * config_factor + induction_weight) * tech_factor
        
        return round(total_weight, 1)
    
    @staticmethod
    def get_fuel_octane_limit(current_year: int, fuel_type: str) -> float:
        """
        根据年份和燃料类型获取最大允许压缩比
        
        历史数据：
        - 1940s: 75 Octane → Max CR 7.0:1
        - 1950s: 80 Octane → Max CR 8.0:1
        - 1960s: 90 Octane → Max CR 9.0:1
        - 1970s+: 91 Octane → Max CR 10.0:1
        
        Args:
            current_year: 当前游戏年份
            fuel_type: 燃料类型
            
        Returns:
            最大允许压缩比
        """
        # 从数据加载器获取燃料辛烷值
        octane_rating = EngineeringCalculator._get_fuel_property(
            fuel_type, "octane_rating", 91
        )
        
        # 历史燃料质量（年份影响）
        if current_year < 1950:
            # 1940s: 低质量燃料
            historical_octane = 75
        elif current_year < 1960:
            # 1950s: 改进
            historical_octane = 80
        elif current_year < 1970:
            # 1960s: 进一步改进
            historical_octane = 90
        else:
            # 1970s+: 现代燃料
            historical_octane = 91
        
        # 使用历史辛烷值和燃料类型辛烷值中的较小值
        effective_octane = min(octane_rating, historical_octane)
        
        # 辛烷值到压缩比的转换（经验公式）
        # 大致关系：每10个辛烷值单位支持约1.0的压缩比
        # 基础压缩比6.0，每10辛烷值+1.0
        max_cr = 6.0 + (effective_octane - 60) * 0.1
        
        # 限制在合理范围
        max_cr = max(6.0, min(max_cr, 12.0))
        
        return round(max_cr, 1)
    
    @staticmethod
    def calculate_thermal_efficiency(
        current_year: int,
        compression_ratio: float,
        fuel_type: str = "GASOLINE"
    ) -> float:
        """
        计算热效率因子
        
        基于历史技术水平和压缩比：
        - 1946年: 0.18 (18%热效率，早期内燃机)
        - 2020年: 0.35 (35%热效率，现代高效引擎)
        - 压缩比影响: 更高压缩比提升效率（递减收益）
        - 爆震惩罚: 如果压缩比超过燃料限制，大幅降低效率
        
        Args:
            current_year: 当前游戏年份
            compression_ratio: 压缩比
            fuel_type: 燃料类型
            
        Returns:
            热效率因子 (0.0-1.0)
        """
        # 基于年份的线性插值
        year_min = 1946
        year_max = 2020
        efficiency_min = 0.18
        efficiency_max = 0.35
        
        # 限制年份范围
        year_clamped = max(year_min, min(current_year, year_max))
        
        # 线性插值
        year_factor = (year_clamped - year_min) / (year_max - year_min)
        base_efficiency = efficiency_min + (efficiency_max - efficiency_min) * year_factor
        
        # 检查压缩比限制（爆震检测）
        max_cr = EngineeringCalculator.get_fuel_octane_limit(current_year, fuel_type)
        knock_penalty = 1.0
        
        if compression_ratio > max_cr:
            # 压缩比超过限制，应用爆震惩罚
            # 每超过0.1，效率降低15%
            excess_cr = compression_ratio - max_cr
            knock_penalty = max(0.3, 1.0 - 0.15 * excess_cr)
        
        # 压缩比影响（递减收益）
        # 压缩比从8.0开始，每增加1.0提升1%效率，但收益递减
        cr_effect = (compression_ratio - 8.0) * 0.01
        # 限制压缩比影响在合理范围（最多+10%）
        cr_effect = min(cr_effect, 0.10)
        
        thermal_efficiency = base_efficiency * (1.0 + cr_effect) * knock_penalty
        
        # 限制在合理范围
        thermal_efficiency = max(0.15, min(thermal_efficiency, 0.40))
        
        return round(thermal_efficiency, 4)
    
    @staticmethod
    def calculate_volumetric_efficiency(
        rpm: int,
        redline_rpm: int,
        valvetrain: str,
        induction_type: str,
        boost_pressure_bar: float = 0.0
    ) -> float:
        """
        计算特定RPM下的容积效率（VE）
        
        实现真实的VE曲线，形成驼峰形状：
        - 低RPM（<30%红线）：低VE（0.3-0.5）
        - 中等RPM（50-60%红线）：峰值VE（0.85-1.0）
        - 高RPM（>80%红线）：VE下降（0.7-0.85）
        
        老式配气机构（OHV/2气门）在中等RPM表现最好
        现代配气机构（DOHC/4气门）在高RPM表现更好
        
        Args:
            rpm: 当前转速
            redline_rpm: 红线转速
            valvetrain: 配气机构
            induction_type: 进气类型
            boost_pressure_bar: 增压压力
            
        Returns:
            容积效率因子 (0.0-1.5)
        """
        rpm_ratio = rpm / redline_rpm if redline_rpm > 0 else 0.0
        
        # 基础VE曲线形状（驼峰）
        if rpm_ratio < 0.3:
            # 低转：从低值线性上升
            ve_curve = 0.3 + (rpm_ratio / 0.3) * 0.2  # 0.3到0.5
        elif rpm_ratio < 0.55:
            # 中低转：快速上升
            ve_curve = 0.5 + ((rpm_ratio - 0.3) / 0.25) * 0.35  # 0.5到0.85
        elif rpm_ratio < 0.65:
            # 中高转：达到峰值
            ve_curve = 0.85 + ((rpm_ratio - 0.55) / 0.1) * 0.15  # 0.85到1.0
        elif rpm_ratio < 0.85:
            # 高转：缓慢下降
            ve_curve = 1.0 - ((rpm_ratio - 0.65) / 0.2) * 0.15  # 1.0到0.85
        else:
            # 极高转：快速下降
            ve_curve = 0.85 - ((rpm_ratio - 0.85) / 0.15) * 0.15  # 0.85到0.7
        
        # 配气机构修正
        valvetrain_multiplier = {
            "OHV": 0.85,  # 老式2气门，中低转好，高转差
            "SOHC": 0.92,
            "DOHC": 1.0,  # 现代4气门，高转好
            "VARIABLE": 1.05,  # 可变气门，全转速优化
        }.get(valvetrain, 0.92)
        
        # 老式配气机构在中等RPM有优势，现代配气机构在高RPM有优势
        if valvetrain == "OHV" and 0.4 < rpm_ratio < 0.7:
            valvetrain_multiplier = 0.95  # OHV在中等RPM表现更好
        elif valvetrain in ["DOHC", "VARIABLE"] and rpm_ratio > 0.6:
            valvetrain_multiplier = 1.05  # 现代配气机构在高RPM表现更好
        
        ve_base = ve_curve * valvetrain_multiplier
        
        # 增压提升容积效率（增压可超过1.0）
        if induction_type == "NA":
            ve = ve_base
        elif induction_type == "TURBO":
            # 涡轮在低转时增压不足
            if rpm < 2000:
                boost_factor = 0.7
            elif rpm < 3000:
                boost_factor = 0.85
            else:
                boost_factor = 1.0
            ve = ve_base * (1.0 + boost_pressure_bar * 0.5 * boost_factor)
        elif induction_type == "TWINTURBO":
            if rpm < 2000:
                boost_factor = 0.75
            elif rpm < 3000:
                boost_factor = 0.90
            else:
                boost_factor = 1.0
            ve = ve_base * (1.0 + boost_pressure_bar * 0.55 * boost_factor)
        elif induction_type == "SUPERCHARGED":
            # 机械增压全转速增压
            ve = ve_base * (1.0 + boost_pressure_bar * 0.45)
        else:
            ve = ve_base
        
        return max(0.2, min(ve, 1.5))
    
    @staticmethod
    def calculate_horsepower(
        displacement_cc: int,
        compression_ratio: float,
        induction_type: str,
        boost_pressure_bar: float,
        valvetrain: str,
        fuel_type: str,
        tech_level: int,
        redline_rpm: int,
        current_year: int,
        max_safe_rpm: Optional[int] = None
    ) -> Tuple[int, float]:
        """
        计算最大马力（HP）和热效率
        
        重构后的计算流程：
        1. 计算基础扭矩（基于排量、压缩比、技术等级）
        2. 在峰值RPM应用VE曲线（基于MPS上限，而不是用户设定的redline）
        3. 从扭矩计算马力：HP = (Torque * RPM) / 7121
        
        重要：VE曲线基于MPS上限计算，这样降低redline时功率不会改变，只是曲线被截断
        
        Args:
            displacement_cc: 排量（cc）
            compression_ratio: 压缩比
            induction_type: 进气类型
            boost_pressure_bar: 增压压力
            valvetrain: 配气机构
            fuel_type: 燃料类型
            tech_level: 技术等级
            redline_rpm: 用户设定的红线转速（用于限制，但VE基于MPS上限）
            current_year: 当前游戏年份
            max_safe_rpm: MPS上限（用于VE曲线计算）
            
        Returns:
            (max_horsepower, thermal_efficiency) 元组
        """
        displacement_liters = displacement_cc / 1000.0
        
        # 计算热效率（包含爆震惩罚）
        thermal_efficiency = EngineeringCalculator.calculate_thermal_efficiency(
            current_year, compression_ratio, fuel_type
        )
        
        # 使用MPS上限作为VE曲线的参考（如果提供了）
        # 如果没有提供，使用redline_rpm（向后兼容）
        ve_reference_redline = max_safe_rpm if max_safe_rpm else redline_rpm
        
        # 计算峰值功率RPM（基于VE参考redline，但不超过用户设定的redline）
        if induction_type in ["TURBO", "TWINTURBO"]:
            peak_power_rpm = int(ve_reference_redline * 0.90)
        else:
            peak_power_rpm = int(ve_reference_redline * 0.95)
        
        # 确保峰值功率RPM不超过用户设定的redline
        peak_power_rpm = min(peak_power_rpm, redline_rpm)
        
        # 在峰值功率RPM计算VE（基于MPS上限）
        ve_at_peak = EngineeringCalculator.calculate_volumetric_efficiency(
            peak_power_rpm, ve_reference_redline, valvetrain, induction_type, boost_pressure_bar
        )
        
        # BMEP基础值（bar）
        # 调整系数以匹配历史引擎性能：1946年2.0L引擎应产生~130 Nm
        bmep_base = 10.0 + (compression_ratio - 8.0) * 0.6
        
        # 增压提升BMEP
        if induction_type == "NA":
            bmep_multiplier = 1.0
        elif induction_type == "TURBO":
            bmep_multiplier = 1.0 + boost_pressure_bar * 0.8
        elif induction_type == "TWINTURBO":
            bmep_multiplier = 1.0 + boost_pressure_bar * 0.85
        elif induction_type == "SUPERCHARGED":
            bmep_multiplier = 1.0 + boost_pressure_bar * 0.75
        else:
            bmep_multiplier = 1.0
        
        bmep = bmep_base * bmep_multiplier
        
        # 燃料类型影响
        fuel_factor = EngineeringCalculator._get_fuel_property(
            fuel_type, "torque_factor", 1.0
        )
        
        # 技术等级因子（调整以匹配1946年2.0L引擎目标值）
        tech_factor = 1.0 + (tech_level - 1) * 0.02
        
        # 计算峰值扭矩：Torque = (BMEP × Displacement × 100 × VE × Tech_Factor × Fuel_Factor × ThermalEfficiency) / π
        base_torque_nm = (bmep * displacement_liters * 100.0 * ve_at_peak * 
                         tech_factor * fuel_factor * thermal_efficiency) / math.pi
        
        # 从扭矩计算马力：HP = (Torque (Nm) × RPM) / 7121
        # 使用正确的单位转换常数 7121
        power_hp = (base_torque_nm * peak_power_rpm) / 7121.0
        
        return (int(round(power_hp)), thermal_efficiency)
    
    @staticmethod
    def calculate_torque(
        displacement_cc: int,
        compression_ratio: float,
        induction_type: str,
        boost_pressure_bar: float,
        fuel_type: str,
        tech_level: int,
        current_year: Optional[int] = None,
        valvetrain: Optional[str] = None,
        redline_rpm: Optional[int] = None,
        max_safe_rpm: Optional[int] = None
    ) -> int:
        """
        计算最大扭矩（牛·米）
        
        扭矩主要由排量和BMEP决定，在峰值扭矩RPM（通常50-60%红线）计算
        
        重要：VE曲线基于MPS上限计算，这样降低redline时扭矩不会改变
        
        公式：Torque (Nm) = (BMEP × Displacement × VE × Tech_Factor × Fuel_Factor × ThermalEfficiency) / π
        """
        displacement_liters = displacement_cc / 1000.0
        
        # 计算热效率（包含爆震惩罚）
        thermal_efficiency = 1.0
        if current_year:
            thermal_efficiency = EngineeringCalculator.calculate_thermal_efficiency(
                current_year, compression_ratio, fuel_type
            )
        
        # BMEP基础值（bar）
        # 调整系数以匹配历史引擎性能：1946年2.0L引擎应产生~130 Nm
        bmep_base = 10.0 + (compression_ratio - 8.0) * 0.6
        
        # 增压大幅提升BMEP
        if induction_type == "NA":
            bmep_multiplier = 1.0
        elif induction_type == "TURBO":
            bmep_multiplier = 1.0 + boost_pressure_bar * 0.8
        elif induction_type == "TWINTURBO":
            bmep_multiplier = 1.0 + boost_pressure_bar * 0.85
        elif induction_type == "SUPERCHARGED":
            bmep_multiplier = 1.0 + boost_pressure_bar * 0.75
        else:
            bmep_multiplier = 1.0
        
        bmep = bmep_base * bmep_multiplier
        
        # 燃料类型（从数据加载器获取）
        fuel_factor = EngineeringCalculator._get_fuel_property(
            fuel_type, "torque_factor", 1.0
        )
        
        # 技术等级
        tech_factor = 1.0 + (tech_level - 1) * 0.02
        
        # 计算峰值扭矩RPM的VE（如果提供了valvetrain和redline）
        # 使用MPS上限作为VE参考，而不是用户设定的redline
        ve_at_peak = 1.0
        if valvetrain and redline_rpm:
            # 使用MPS上限作为VE曲线的参考（如果提供了）
            ve_reference_redline = max_safe_rpm if max_safe_rpm else redline_rpm
            
            # 峰值扭矩通常在50-60%VE参考redline
            if induction_type in ["TURBO", "TWINTURBO"]:
                peak_torque_rpm = int(ve_reference_redline * 0.40)
            else:
                peak_torque_rpm = int(ve_reference_redline * 0.55)
            
            # 确保峰值扭矩RPM不超过用户设定的redline
            peak_torque_rpm = min(peak_torque_rpm, redline_rpm)
            
            ve_at_peak = EngineeringCalculator.calculate_volumetric_efficiency(
                peak_torque_rpm, ve_reference_redline, valvetrain, induction_type, boost_pressure_bar
            )
        
        # 扭矩计算（Nm）
        # 公式：Torque = (BMEP [bar] × Displacement [L] × 100 × VE × Tech_Factor × Fuel_Factor × ThermalEfficiency) / π
        torque_nm = (bmep * displacement_liters * 100.0 * ve_at_peak * 
                     fuel_factor * tech_factor * thermal_efficiency) / math.pi
        
        return int(round(torque_nm))
    
    @staticmethod
    def calculate_redline_rpm(
        stroke_mm: float,
        material: str,
        configuration: str,
        tech_level: int,
        valvetrain: Optional[str] = None,
        current_year: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        计算最大安全转速和红线转速（RPM）
        
        基于Mean Piston Speed (MPS)物理限制：
        - 公式：RPM_Limit = (Max_MPS * 60) / (2 * Stroke_in_Meters)
        - 材料限制：铸铁(1940s) ~15-18 m/s, 现代锻造 ~25 m/s
        
        主要限制因素：
        - 活塞平均速度（Mean Piston Speed）不应超过材料极限
        - Valvetrain技术限制（Flathead/OHV等）
        - 短行程引擎可以转得更快
        
        公式：MPS (m/s) = (Stroke × RPM × 2) / 60,000
        
        Args:
            stroke_mm: 行程（毫米）
            material: 材料类型
            configuration: 配置类型
            tech_level: 技术等级
            valvetrain: 配气机构类型（可选，用于限制）
            
        Returns:
            (max_safe_rpm, redline_rpm) 元组
            - max_safe_rpm: 最大安全转速（基于MPS）
            - redline_rpm: 红线转速（max_safe * 0.95，考虑Valvetrain限制）
        """
        stroke_m = stroke_mm / 1000.0
        
        # 材料允许的最大平均活塞速度（m/s）
        # 历史约束：1940s铸铁 ~15-18 m/s, 现代锻造 ~25 m/s
        base_speed = EngineeringCalculator._get_engine_material_data(
            material, "max_piston_speed_ms", 18.0
        )
        tech_bonus = EngineeringCalculator._get_engine_material_data(
            material, "piston_speed_tech_bonus", 0.5
        )
        
        # 根据年份限制tech_level（历史约束）
        # 40年代的发动机技术更原始，不应该有太高的tech_level
        effective_tech_level = tech_level
        if current_year:
            if current_year < 1950:
                # 1940s: 技术非常原始，tech_level上限为2
                effective_tech_level = min(tech_level, 2)
            elif current_year < 1960:
                # 1950s: 技术改进，上限为4
                effective_tech_level = min(tech_level, 4)
            elif current_year < 1970:
                # 1960s: 进一步改进，上限为6
                effective_tech_level = min(tech_level, 6)
            elif current_year < 1980:
                # 1970s: 上限为8
                effective_tech_level = min(tech_level, 8)
            # 1980s及以后：无限制
        
        # 技术等级提升MPS限制（使用有效tech_level）
        max_piston_speed = base_speed + effective_tech_level * tech_bonus
        
        # 配置影响（某些配置平衡性更好）
        config_factor = {
            "INLINE": 1.0,
            "V": 1.05,  # V型平衡性好
            "BOXER": 1.10,  # 水平对置最平衡
            "VR": 1.02,
            "W": 1.08,
        }.get(configuration, 1.0)
        
        max_piston_speed *= config_factor
        
        # 反推RPM：RPM = (MPS × 60,000) / (Stroke_mm × 2)
        # 注意：使用stroke_mm（毫米）而不是stroke_m（米）
        max_safe_rpm = (max_piston_speed * 60000.0) / (stroke_mm * 2.0)
        
        # Valvetrain限制（气门浮动限制）
        valvetrain_limit = None
        if valvetrain:
            if valvetrain == "FLATHEAD" or valvetrain == "SIDE_VALVE":
                # Flathead/Side Valve: 气门浮动严重，最大 ~4500 RPM
                valvetrain_limit = 4500
            elif valvetrain == "OHV":
                # OHV: 气门机构限制，最大 ~6000 RPM
                valvetrain_limit = 6000
            elif valvetrain == "SOHC":
                # SOHC: 单顶置凸轮轴，最大 ~7000 RPM
                valvetrain_limit = 7000
            elif valvetrain == "DOHC":
                # DOHC: 双顶置凸轮轴，最大 ~9000 RPM
                valvetrain_limit = 9000
            elif valvetrain == "VARIABLE":
                # 可变气门正时，最大 ~9500 RPM
                valvetrain_limit = 9500
        
        # 应用Valvetrain限制（如果存在）
        if valvetrain_limit:
            max_safe_rpm = min(max_safe_rpm, valvetrain_limit)
        
        # 红线转速通常是最大安全转速的95%（留出安全余量）
        redline_rpm = int(max_safe_rpm * 0.95)
        
        # 四舍五入到百位
        max_safe_rpm = int((max_safe_rpm + 50) // 100 * 100)
        redline_rpm = int((redline_rpm + 50) // 100 * 100)
        
        # 确保最小值
        max_safe_rpm = max(3000, max_safe_rpm)
        redline_rpm = max(2500, redline_rpm)
        
        return (max_safe_rpm, redline_rpm)
    
    @staticmethod
    def get_max_tech_level_for_year(current_year: int) -> int:
        """
        根据年份获取最大允许的技术等级
        
        Args:
            current_year: 当前游戏年份
            
        Returns:
            最大允许的技术等级
        """
        if current_year < 1950:
            return 2  # 1940s
        elif current_year < 1960:
            return 4  # 1950s
        elif current_year < 1970:
            return 6  # 1960s
        elif current_year < 1980:
            return 8  # 1970s
        else:
            return 10  # 1980s及以后
    
    @staticmethod
    def validate_component_availability(
        component_type: str,
        component_id: str,
        current_year: int,
        effective_tech_level: int
    ) -> Tuple[bool, Optional[str]]:
        """
        验证组件是否可用（基于年份和技术等级）
        
        Args:
            component_type: 组件类型（'material', 'valvetrain', 'induction', 'fuel'）
            component_id: 组件ID
            current_year: 当前游戏年份
            effective_tech_level: 有效技术等级（已考虑年份限制）
            
        Returns:
            (是否可用, 错误消息)
        """
        import json
        from pathlib import Path
        
        # 直接从JSON文件读取（避免循环依赖）
        data_file = Path("assets/data/component_stats.json")
        if not data_file.exists():
            # 如果文件不存在，默认允许（向后兼容）
            return (True, None)
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            return (True, None)  # 读取失败时默认允许
        
        # 获取组件所需的技术等级
        required_tech_level = None
        
        if component_type == 'material':
            # 检查引擎材料
            if "engine_materials" in data:
                for mat in data["engine_materials"]:
                    if mat.get("id") == component_id:
                        required_tech_level = mat.get("tech_level_required", 1)
                        break
        elif component_type == 'valvetrain':
            # 检查配气机构
            if "valvetrain_types" in data:
                for vt in data["valvetrain_types"]:
                    if vt.get("id") == component_id:
                        required_tech_level = vt.get("tech_level_required", 1)
                        break
        elif component_type == 'induction':
            # 检查进气方式
            # 基础进气方式（NA）总是可用
            if component_id == 'NA':
                return (True, None)
            # 其他进气方式需要技术解锁（从components中查找）
            if "components" in data:
                for comp in data["components"]:
                    comp_type = comp.get("type", "").upper()
                    if (comp_type == component_id or 
                        (component_id == "TURBO" and comp_type in ["TURBO", "turbo"]) or
                        (component_id == "TWINTURBO" and comp_type in ["TWINTURBO", "twinturbo"]) or
                        (component_id == "SUPERCHARGED" and comp_type in ["SUPERCHARGER", "supercharger"])):
                        required_tech_level = comp.get("tech_level_required", 5)
                        break
            # 如果没有找到，使用默认值
            if required_tech_level is None:
                if component_id == 'TURBO':
                    required_tech_level = 5  # 约1970s
                elif component_id == 'TWINTURBO':
                    required_tech_level = 7  # 约1980s
                elif component_id == 'SUPERCHARGED':
                    required_tech_level = 4  # 约1960s
        elif component_type == 'fuel':
            # 基础燃料（GASOLINE）总是可用
            if component_id == 'GASOLINE':
                return (True, None)
            # 其他燃料目前没有tech_level_required字段，使用历史年份判断
            # 这些燃料通常需要特殊技术解锁，但暂时不强制验证
            return (True, None)  # 燃料暂时不验证技术等级
        
        # 如果没有找到所需技术等级，默认允许（向后兼容）
        if required_tech_level is None:
            return (True, None)
        
        # 检查技术等级是否足够
        if effective_tech_level < required_tech_level:
            max_tech_for_year = EngineeringCalculator.get_max_tech_level_for_year(current_year)
            component_name_map = {
                'material': '材料',
                'valvetrain': '配气机构',
                'induction': '进气方式',
                'fuel': '燃料'
            }
            component_name = component_name_map.get(component_type, component_type)
            return (False, 
                f"{component_name} '{component_id}' 需要技术等级 {required_tech_level}，"
                f"但当前年份({current_year})最大允许 {max_tech_for_year}，"
                f"有效技术等级为 {effective_tech_level}")
        
        return (True, None)
        
        # 技术等级提升MPS限制（使用有效tech_level）
        max_piston_speed = base_speed + effective_tech_level * tech_bonus
        
        # 配置影响（某些配置平衡性更好）
        config_factor = {
            "INLINE": 1.0,
            "V": 1.05,  # V型平衡性好
            "BOXER": 1.10,  # 水平对置最平衡
            "VR": 1.02,
            "W": 1.08,
        }.get(configuration, 1.0)
        
        max_piston_speed *= config_factor
        
        # 反推RPM：RPM = (MPS × 60,000) / (Stroke_mm × 2)
        # 注意：使用stroke_mm（毫米）而不是stroke_m（米）
        max_safe_rpm = (max_piston_speed * 60000.0) / (stroke_mm * 2.0)
        
        # Valvetrain限制（气门浮动限制）
        valvetrain_limit = None
        if valvetrain:
            if valvetrain == "FLATHEAD" or valvetrain == "SIDE_VALVE":
                # Flathead/Side Valve: 气门浮动严重，最大 ~4500 RPM
                valvetrain_limit = 4500
            elif valvetrain == "OHV":
                # OHV: 气门机构限制，最大 ~6000 RPM
                valvetrain_limit = 6000
            # SOHC/DOHC/VARIABLE: 无额外限制，基于MPS
        
        # 应用Valvetrain限制
        if valvetrain_limit:
            max_safe_rpm = min(max_safe_rpm, valvetrain_limit)
        
        # 圆整到100的倍数
        max_safe_rpm = int(round(max_safe_rpm / 100.0) * 100)
        
        # 限制在合理范围（最小3000，最大12000）
        max_safe_rpm = max(3000, min(max_safe_rpm, 12000))
        
        # 红线转速 = 最大安全转速 * 0.95（安全余量）
        redline_rpm = int(round(max_safe_rpm * 0.95 / 100.0) * 100)
        
        return (max_safe_rpm, redline_rpm)
    
    @staticmethod
    def calculate_thermal_load(
        horsepower: int,
        displacement_cc: int,
        induction_type: str,
        boost_pressure_bar: float,
        compression_ratio: float
    ) -> float:
        """
        计算热负载系数（无量纲）
        
        高升功率 + 高增压 + 高压缩比 = 高热负载
        热负载过高会降低可靠性，需要更好的冷却
        
        Returns:
            热负载系数（0-100+，正常范围20-60）
        """
        # 升功率（HP/L）
        specific_output = horsepower / (displacement_cc / 1000.0)
        
        # 基础热负载（升功率越高，热量越大）
        base_thermal = specific_output * 0.3
        
        # 增压额外热量
        boost_thermal = 0
        if induction_type in ["TURBO", "TWINTURBO"]:
            boost_thermal = boost_pressure_bar * 8.0  # 涡轮产生大量热
        elif induction_type == "SUPERCHARGED":
            boost_thermal = boost_pressure_bar * 6.0
        
        # 压缩比影响
        compression_thermal = (compression_ratio - 8.0) * 2.0
        
        total_thermal = base_thermal + boost_thermal + compression_thermal
        
        return round(total_thermal, 2)
    
    @staticmethod
    def calculate_reliability_score(
        specific_output: float,
        thermal_load: float,
        tech_level: int,
        material: str,
        stress_factor: float = 1.0,
        compression_ratio: Optional[float] = None,
        current_year: Optional[int] = None,
        fuel_type: Optional[str] = None
    ) -> float:
        """
        计算基础可靠性分数（0-100）
        
        影响因素：
        - 升功率过高 → 降低可靠性
        - 热负载过高 → 降低可靠性
        - 技术等级高 → 提升可靠性
        - 材料质量 → 影响耐久性
        - 压缩比超过燃料限制 → 大幅降低可靠性（爆震）
        
        Args:
            specific_output: 升功率（HP/L）
            thermal_load: 热负载系数
            tech_level: 技术等级 1-10
            material: 材料类型
            stress_factor: 应力系数（可选）
            compression_ratio: 压缩比（可选，用于爆震检测）
            current_year: 当前年份（可选，用于爆震检测）
            fuel_type: 燃料类型（可选，用于爆震检测）
            
        Returns:
            可靠性分数 0-100
        """
        # 基础可靠性（技术等级）
        base_reliability = 50.0 + tech_level * 4.0  # 1级=54, 10级=90
        
        # 升功率惩罚（自然吸气>80 HP/L，涡轮>120 HP/L开始显著下降）
        if specific_output < 80:
            output_penalty = 0
        elif specific_output < 120:
            output_penalty = (specific_output - 80) * 0.3
        else:
            output_penalty = 12 + (specific_output - 120) * 0.5
        
        # 热负载惩罚
        if thermal_load < 30:
            thermal_penalty = 0
        elif thermal_load < 60:
            thermal_penalty = (thermal_load - 30) * 0.2
        else:
            thermal_penalty = 6 + (thermal_load - 60) * 0.4
        
        # 压缩比限制惩罚（爆震）
        knock_penalty = 0.0
        if compression_ratio and current_year and fuel_type:
            max_cr = EngineeringCalculator.get_fuel_octane_limit(current_year, fuel_type)
            if compression_ratio > max_cr:
                # 每超过0.1压缩比，可靠性降低30分
                excess_cr = compression_ratio - max_cr
                knock_penalty = 30.0 * excess_cr
        
        # 材料加成（从数据加载器获取）
        material_bonus = EngineeringCalculator._get_engine_material_data(
            material, "reliability_bonus", 0
        )
        
        # 应力系数
        stress_penalty = (stress_factor - 1.0) * 10.0
        
        # 最终可靠性
        reliability = base_reliability + material_bonus - output_penalty - thermal_penalty - stress_penalty - knock_penalty
        
        # 限制在0-100
        reliability = max(0.0, min(100.0, reliability))
        
        return round(reliability, 2)
    
    @staticmethod
    def calculate_fuel_efficiency(
        displacement_cc: int,
        horsepower: int,
        compression_ratio: float,
        induction_type: str,
        fuel_type: str,
        tech_level: int
    ) -> Tuple[float, float]:
        """
        计算燃油效率
        
        Returns:
            (fuel_efficiency_rating, bsfc_g_kwh)
            - fuel_efficiency_rating: 效率评分 0-100
            - bsfc_g_kwh: 制动燃油消耗率（克/千瓦时）
        """
        # BSFC基础值（g/kWh）- 越低越好（从数据加载器获取）
        bsfc_base = EngineeringCalculator._get_fuel_property(
            fuel_type, "bsfc_base_g_kwh", 270
        )
        
        # 压缩比提升效率
        compression_factor = 1.0 - (compression_ratio - 8.0) * 0.02  # 高压缩比降低BSFC
        
        # 增压效率影响（涡轮在高负荷下更高效，但低负荷差）
        if induction_type == "NA":
            induction_factor = 1.0
        elif induction_type in ["TURBO", "TWINTURBO"]:
            induction_factor = 0.95  # 涡轮略微提升效率
        elif induction_type == "SUPERCHARGED":
            induction_factor = 1.05  # 机械增压消耗功率
        else:
            induction_factor = 1.0
        
        # 技术等级提升效率
        tech_factor = 1.0 - (tech_level - 1) * 0.015  # 每级降低1.5% BSFC
        
        # 计算BSFC
        bsfc = bsfc_base * compression_factor * induction_factor * tech_factor
        
        # 效率评分（BSFC越低，评分越高）
        # 200 g/kWh = 100分，350 g/kWh = 0分
        efficiency_rating = 100.0 - (bsfc - 200.0) * 0.67
        efficiency_rating = max(0.0, min(100.0, efficiency_rating))
        
        return (round(efficiency_rating, 2), round(bsfc, 1))
    
    @staticmethod
    def calculate_manufacturing_cost(
        displacement_cc: int,
        cylinder_count: int,
        configuration: str,
        material: str,
        induction_type: str,
        valvetrain: str,
        tech_level: int,
        material_grade_id: Optional[str] = None,
        process_id: Optional[str] = None,
        current_year: Optional[int] = None,
        stroke_mm: Optional[float] = None
    ) -> float:
        """
        计算引擎制造成本（游戏币）
        
        现在使用 EngineeringCore 物理引擎进行硬核模拟计算。
        如果提供了 material_grade_id 和 process_id，将使用新的物理引擎。
        否则，使用向后兼容的旧方法。
        
        成本因素：
        - 排量（材料用量）
        - 缸数（加工复杂度）
        - 配置（V型比直列贵）
        - 材料（铝比铸铁贵）
        - 增压系统
        - 配气机构
        - 制造工艺（锻造 vs 铸造）
        """
        # 如果提供了新参数且 EngineeringCore 可用，使用新的物理引擎
        if (ENGINEERING_CORE_AVAILABLE and 
            material_grade_id and 
            process_id and 
            current_year is not None and
            stroke_mm is not None):
            
            try:
                # 使用 EngineeringCore 评估引擎缸体（获取基础成本）
                # 注意：这里我们主要用 EngineeringCore 计算缸体成本
                # 其他组件（增压、配气）仍然使用旧方法
                
                # 估算缸体体积
                displacement_m3 = displacement_cc / 1_000_000.0
                block_volume_m3 = displacement_m3 * 2.0
                
                # 获取材料等级
                material_grade = MATERIAL_GRADES.get(material_grade_id)
                if not material_grade:
                    material_grade = MATERIAL_GRADES.get("CAST_IRON_STANDARD", 
                                                          MATERIAL_GRADES["STEEL_LOW_CARBON"])
                
                # 基础材料成本
                base_material_cost = block_volume_m3 * material_grade.density * 2.0
                base_material_cost *= material_grade.base_cost_multiplier
                
                # 使用 EngineeringCore 计算制造成本
                # 缸数影响零件数和集成复杂度
                part_count = cylinder_count * 15  # 每缸约15个零件
                integration_complexity = 5.0 + (tech_level - 1) * 0.3
                
                block_cost = EngineeringCore.calculate_manufacturing_cost(
                    base_material_cost=base_material_cost,
                    part_count=part_count,
                    integration_complexity=integration_complexity,
                    process_id=process_id,
                    volume_m3=block_volume_m3
                )
                
                # 应用技术成熟度修正
                tech_intro_year = current_year - tech_level * 2
                maturity = EngineeringCore.get_maturity_modifier(tech_intro_year, current_year)
                block_cost *= maturity["cost_mod"]
                
                # 配置复杂度（仍然使用旧方法）
                config_multiplier = {
                    "INLINE": 1.0,
                    "V": 1.3,
                    "BOXER": 1.4,
                    "VR": 1.35,
                    "W": 1.6,
                }.get(configuration, 1.0)
                
                block_cost *= config_multiplier
                
                # 增压系统成本（仍然使用旧方法）
                induction_cost = {
                    "NA": 0,
                    "TURBO": 800,
                    "TWINTURBO": 1500,
                    "SUPERCHARGED": 1200,
                }.get(induction_type, 0)
                
                # 配气机构成本（仍然使用旧方法）
                valvetrain_cost = {
                    "OHV": 0,
                    "SOHC": 150,
                    "DOHC": 300,
                    "VARIABLE": 600,
                }.get(valvetrain, 0)
                
                total_cost = block_cost + induction_cost + valvetrain_cost
                
                return round(total_cost, 2)
                
            except Exception as e:
                logger.warning(f"使用 EngineeringCore 计算成本失败，回退到旧方法: {e}")
                # 继续使用旧方法
        
        # 向后兼容：使用旧的计算方法
        # 基础成本：每升排量约500-1000游戏币
        base_cost_per_liter = 700
        displacement_liters = displacement_cc / 1000.0
        base_cost = displacement_liters * base_cost_per_liter
        
        # 缸数成本（更多缸 = 更多加工）
        cylinder_cost = cylinder_count * 80
        
        # 配置复杂度
        config_multiplier = {
            "INLINE": 1.0,
            "V": 1.3,
            "BOXER": 1.4,
            "VR": 1.35,
            "W": 1.6,
        }.get(configuration, 1.0)
        
        # 材料成本
        material_multiplier = {
            "CAST_IRON": 1.0,
            "ALUMINUM": 1.5,
            "MAGNESIUM": 2.2,
        }.get(material, 1.0)
        
        # 增压系统成本
        induction_cost = {
            "NA": 0,
            "TURBO": 800,
            "TWINTURBO": 1500,
            "SUPERCHARGED": 1200,
        }.get(induction_type, 0)
        
        # 配气机构成本
        valvetrain_cost = {
            "OHV": 0,
            "SOHC": 150,
            "DOHC": 300,
            "VARIABLE": 600,
        }.get(valvetrain, 0)
        
        # 技术等级成本（高科技更贵）
        tech_multiplier = 1.0 + (tech_level - 1) * 0.1
        
        total_cost = (base_cost + cylinder_cost) * config_multiplier * material_multiplier * tech_multiplier
        total_cost += induction_cost + valvetrain_cost
        
        return round(total_cost, 2)
    
    @staticmethod
    def check_engine_chassis_compatibility(
        engine_length: float,
        engine_width: float,
        engine_height: float,
        thermal_load: float,
        bay_length: float,
        bay_width: float,
        bay_height: float,
        cooling_capacity: float
    ) -> Tuple[bool, str]:
        """
        检查引擎与底盘的兼容性
        
        Args:
            engine_*: 引擎尺寸（mm）和热负载
            bay_*: 引擎舱尺寸（mm）
            cooling_capacity: 冷却容量（kW）
            
        Returns:
            (is_compatible, reason)
        """
        # 尺寸检查（留5%余量）
        clearance_factor = 1.05
        
        if engine_length * clearance_factor > bay_length:
            return (False, f"引擎过长：需要{engine_length:.0f}mm，引擎舱仅{bay_length:.0f}mm")
        
        if engine_width * clearance_factor > bay_width:
            return (False, f"引擎过宽：需要{engine_width:.0f}mm，引擎舱仅{bay_width:.0f}mm")
        
        if engine_height * clearance_factor > bay_height:
            return (False, f"引擎过高：需要{engine_height:.0f}mm，引擎舱仅{bay_height:.0f}mm")
        
        # 冷却容量检查（热负载转换为kW，粗略估算）
        required_cooling = thermal_load * 2.0  # 简化：热负载系数 × 2 = 所需冷却kW
        
        if required_cooling > cooling_capacity:
            return (False, f"冷却不足：需要{required_cooling:.0f}kW，底盘仅支持{cooling_capacity:.0f}kW")
        
        # 如果冷却接近极限，给出警告
        if required_cooling > cooling_capacity * 0.9:
            return (True, f"警告：冷却容量接近极限（{required_cooling:.0f}/{cooling_capacity:.0f}kW）")
        
        return (True, "完全兼容")
    
    @staticmethod
    def calculate_vehicle_performance(
        total_weight_kg: float,
        horsepower: int,
        torque_nm: int,
        drag_coefficient: float,
        frontal_area_sqm: float,
        drivetrain: str,
        tire_grip: float = 1.0
    ) -> PerformanceResult:
        """
        计算整车性能
        
        基于物理公式计算加速、极速、刹车等
        
        Args:
            total_weight_kg: 总重量
            horsepower: 马力
            torque_nm: 扭矩
            drag_coefficient: 风阻系数
            frontal_area_sqm: 正面投影面积
            drivetrain: 驱动形式
            tire_grip: 轮胎抓地力系数
            
        Returns:
            PerformanceResult对象
        """
        # 功率（kW）
        power_kw = horsepower / 1.341
        
        # 推重比（kW/kg）
        power_to_weight = power_kw / total_weight_kg
        
        # ===== 0-100 km/h 加速时间 =====
        # 简化模型：考虑推重比和驱动形式
        # 基础公式：t ≈ k / (P/m)，其中k是常数
        
        # 驱动形式影响起步（四驱最好，前驱最差）
        drivetrain_factor = {
            "AWD": 1.0,
            "FR": 1.1,
            "MR": 1.05,
            "RR": 1.08,
            "FF": 1.15,
        }.get(drivetrain, 1.1)
        
        # 轮胎抓地力影响
        grip_factor = 2.0 - tire_grip  # grip=1.0 -> factor=1.0
        
        # 0-100加速时间（秒）
        # 经验公式：t = 140 / (P/m) × drivetrain × grip
        zero_to_hundred = (140.0 / power_to_weight) * drivetrain_factor * grip_factor / 1000.0
        zero_to_hundred = max(2.5, min(zero_to_hundred, 30.0))  # 限制在合理范围
        
        # ===== 最高速度 =====
        # 当驱动力 = 空气阻力时达到最高速
        # Drag Force = 0.5 × ρ × Cd × A × v²
        # Power = Force × Velocity
        # v_max = (2 × Power / (ρ × Cd × A))^(1/3)
        
        # 获取物理常数
        air_density = EngineeringCalculator._get_constant("AIR_DENSITY", 1.225)
        drag_force_coefficient = 0.5 * air_density * drag_coefficient * frontal_area_sqm
        
        # 最高速度（m/s）
        v_max_ms = (power_kw * 1000.0 / drag_force_coefficient) ** (1.0/3.0)
        
        # 转换为km/h
        top_speed_kph = v_max_ms * 3.6
        top_speed_kph = max(80, min(top_speed_kph, 450))  # 限制范围
        
        # ===== 1/4英里加速时间 =====
        # 经验公式（基于0-100时间）
        quarter_mile = zero_to_hundred * 1.8 + 3.0
        
        # ===== 刹车距离（100-0 km/h）=====
        # 基于重量和轮胎抓地力
        # d = v² / (2 × μ × g)
        v_initial = 100.0 / 3.6  # m/s
        mu = 0.8 * tire_grip  # 制动摩擦系数
        gravity = EngineeringCalculator._get_constant("GRAVITY", 9.81)
        
        braking_distance = (v_initial ** 2) / (2 * mu * gravity)
        braking_distance = max(30, min(braking_distance, 100))
        
        # ===== 横向G值 =====
        # 基于重心高度、轮距、抓地力
        # 简化：主要由轮胎决定
        lateral_g = 0.9 * tire_grip
        lateral_g = max(0.6, min(lateral_g, 1.5))
        
        # ===== 燃油经济性 =====
        # 基于功率、重量、风阻
        # 简化公式：L/100km = k × (weight + drag) / efficiency
        
        # 基础油耗（L/100km）
        base_consumption = total_weight_kg / 1000.0 * 3.5
        
        # 风阻影响
        drag_consumption = drag_coefficient * frontal_area_sqm * 2.0
        
        # 功率影响（大马力通常更费油）
        power_consumption = horsepower / 100.0 * 0.5
        
        fuel_economy = base_consumption + drag_consumption + power_consumption
        fuel_economy = max(3.0, min(fuel_economy, 30.0))
        
        return PerformanceResult(
            zero_to_hundred_kph_sec=round(zero_to_hundred, 2),
            top_speed_kph=round(top_speed_kph, 1),
            quarter_mile_sec=round(quarter_mile, 2),
            braking_100_0_meters=round(braking_distance, 1),
            lateral_g_force=round(lateral_g, 2),
            fuel_economy_l_100km=round(fuel_economy, 1)
        )
    
    @staticmethod
    def calculate_manufacturing_impact(tolerance: float) -> Dict[str, float]:
        """
        计算制造公差对工程时间和成本的影响
        
        高公差 (0.8-1.0): 高精度制造
        - 工程时间: +50%
        - 单位成本: +30%
        - 可靠性: +5%
        - 性能: +2%
        
        低公差 (0.0-0.3): 快速制造
        - 工程时间: -20%
        - 单位成本: -15%
        - 可靠性: -3%
        - 性能: -1%
        
        Args:
            tolerance: 制造公差 (0.0-1.0)
            
        Returns:
            影响字典: {
                "engineering_time_multiplier": float,
                "unit_cost_multiplier": float,
                "reliability_bonus": float,  # 百分比加成
                "performance_bonus": float    # 百分比加成
            }
        """
        tolerance = max(0.0, min(1.0, tolerance))  # 限制范围
        
        # 线性插值
        if tolerance <= 0.3:
            # 低公差：快速制造
            time_mult = 0.8  # -20%
            cost_mult = 0.85  # -15%
            reliability_bonus = -0.03  # -3%
            performance_bonus = -0.01  # -1%
        elif tolerance >= 0.8:
            # 高公差：高精度制造
            time_mult = 1.5  # +50%
            cost_mult = 1.3  # +30%
            reliability_bonus = 0.05  # +5%
            performance_bonus = 0.02  # +2%
        else:
            # 中等公差：线性插值
            # 在0.3和0.8之间插值
            ratio = (tolerance - 0.3) / (0.8 - 0.3)
            time_mult = 0.8 + (1.5 - 0.8) * ratio
            cost_mult = 0.85 + (1.3 - 0.85) * ratio
            reliability_bonus = -0.03 + (0.05 - (-0.03)) * ratio
            performance_bonus = -0.01 + (0.02 - (-0.01)) * ratio
        
        return {
            "engineering_time_multiplier": round(time_mult, 3),
            "unit_cost_multiplier": round(cost_mult, 3),
            "reliability_bonus": round(reliability_bonus, 4),
            "performance_bonus": round(performance_bonus, 4)
        }
    
    @staticmethod
    def generate_power_curve(
        displacement_cc: int,
        compression_ratio: float,
        induction_type: str,
        boost_pressure_bar: float,
        valvetrain: str,
        fuel_type: str,
        tech_level: int,
        redline_rpm: int,
        max_torque_nm: int,
        max_horsepower: int,
        max_safe_rpm: Optional[int] = None,
        current_year: Optional[int] = None
    ) -> list:
        """
        生成动力曲线（不同RPM下的扭矩和马力）
        
        重要：VE曲线基于MPS上限（max_safe_rpm）计算，然后根据用户设定的redline截断
        这样降低redline时曲线会被直接截断，而不是压缩
        
        Args:
            displacement_cc: 排量（cc）
            compression_ratio: 压缩比
            induction_type: 进气类型
            boost_pressure_bar: 增压压力
            valvetrain: 配气机构
            fuel_type: 燃料类型
            tech_level: 技术等级
            redline_rpm: 用户设定的红线转速（用于截断曲线）
            max_torque_nm: 最大扭矩（Nm）
            max_horsepower: 最大马力（HP）
            max_safe_rpm: 最大安全转速（MPS上限，用于VE曲线计算）
        
        Returns:
            动力曲线数据点列表，每个点包含 {rpm, torque, power}
            在redline_rpm之后，功率和扭矩降为0
        """
        curve = []
        displacement_liters = displacement_cc / 1000.0
        
        # 确保redline不超过max_safe_rpm
        if max_safe_rpm:
            redline_rpm = min(redline_rpm, max_safe_rpm)
            # 使用max_safe_rpm作为VE曲线的参考redline（物理上限）
            ve_reference_redline = max_safe_rpm
        else:
            # 如果没有提供max_safe_rpm，使用redline_rpm作为参考
            ve_reference_redline = redline_rpm
        
        # 计算热效率（如果提供了年份）
        thermal_efficiency = 1.0
        if current_year:
            thermal_efficiency = EngineeringCalculator.calculate_thermal_efficiency(
                current_year, compression_ratio, fuel_type
            )
        
        # 从1000 RPM到redline，每500 RPM一个点
        # 严格限制在redline_rpm（不包括redline_rpm + 1）
        max_rpm_for_curve = redline_rpm
        for rpm in range(1000, max_rpm_for_curve + 1, 500):
            # 如果超过redline，停止生成
            if rpm > redline_rpm:
                break
            
            # 使用VE曲线计算方法
            # 重要：VE曲线基于物理上限（ve_reference_redline）计算，而不是用户设定的redline
            # 这样当用户降低redline时，曲线会被直接截断，而不是重新计算
            ve_at_rpm = EngineeringCalculator.calculate_volumetric_efficiency(
                rpm, ve_reference_redline, valvetrain, induction_type, boost_pressure_bar
            )
            
            # 计算该RPM下的BMEP
            # 调整系数以匹配历史引擎性能：1946年2.0L引擎应产生~130 Nm
            bmep_base = 10.0 + (compression_ratio - 8.0) * 0.6
            
            # 增压系统影响（涡轮在低转时增压不足）
            boost_factor = 1.0
            if induction_type in ["TURBO", "TWINTURBO"]:
                if rpm < 2000:
                    boost_factor = 0.7  # 涡轮迟滞
                elif rpm < 3000:
                    boost_factor = 0.85
                else:
                    boost_factor = 1.0
            elif induction_type == "SUPERCHARGED":
                boost_factor = 1.0  # 机械增压全转速增压
            
            if induction_type == "NA":
                bmep_multiplier = 1.0
            elif induction_type == "TURBO":
                bmep_multiplier = 1.0 + boost_pressure_bar * 0.8 * boost_factor
            elif induction_type == "TWINTURBO":
                bmep_multiplier = 1.0 + boost_pressure_bar * 0.85 * boost_factor
            elif induction_type == "SUPERCHARGED":
                bmep_multiplier = 1.0 + boost_pressure_bar * 0.75 * boost_factor
            else:
                bmep_multiplier = 1.0
            
            bmep = bmep_base * bmep_multiplier
            
            # 燃料类型因子
            fuel_factor = EngineeringCalculator._get_fuel_property(
                fuel_type, "torque_factor", 1.0
            )
            
            # 技术等级
            tech_factor = 1.0 + (tech_level - 1) * 0.02
            
            # 计算该RPM下的扭矩：Torque = (BMEP × Displacement × 100 × VE × Tech_Factor × Fuel_Factor × ThermalEfficiency) / π
            torque_nm = (bmep * displacement_liters * 100.0 * ve_at_rpm * 
                        fuel_factor * tech_factor * thermal_efficiency) / math.pi
            
            # 计算功率：Power (HP) = (Torque (Nm) × RPM) / 7121
            # 使用正确的单位转换常数 7121
            power_hp = (torque_nm * rpm) / 7121.0
            
            # 限制在合理范围（不超过峰值）
            torque_nm = min(torque_nm, max_torque_nm * 1.05)
            power_hp = min(power_hp, max_horsepower * 1.05)
            
            # 不要在这里设置为0，让曲线自然截断
            # 只有在真正超过redline时才停止生成点
            
            curve.append({
                "rpm": rpm,
                "torque": round(torque_nm, 1),
                "power": round(power_hp, 1)
            })
        
        # 不添加redline处的0点，让曲线自然截断
        # 曲线应该在redline处保持最后一个有效值，而不是降到0
        
        return curve


__all__ = [
    "EngineeringCalculator",
    "EngineSpecs",
    "ChassisSpecs",
    "PerformanceResult"
]

