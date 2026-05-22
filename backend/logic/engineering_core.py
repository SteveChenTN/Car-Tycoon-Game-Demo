"""
工程核心物理引擎 - 硬核模拟的数学核心
Engineering Core Physics Engine - The Mathematical Heart of Hardcore Simulation

设计原则：
1. 纯逻辑模块 - 无游戏状态依赖
2. 基于真实物理公式 - 无随机数
3. 材料科学 + 结构工程 + 制造经济学
4. 数据驱动 - 所有常量可配置

核心功能：
- 材料科学：材料类型、等级、物理属性
- 结构物理：应力、应变、安全系数
- 工业复杂度：指数成本缩放
- 技术成熟度：时间-效率曲线
"""
import math
from enum import Enum
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ========== 数据结构定义 ==========

class MaterialType(str, Enum):
    """材料类型枚举"""
    CAST_IRON = "CAST_IRON"
    STEEL = "STEEL"
    ALUMINIUM = "ALUMINIUM"
    TITANIUM = "TITANIUM"
    CARBON_FIBER = "CARBON_FIBER"


@dataclass
class MaterialGrade:
    """
    材料等级 - 定义材料的物理和经济学属性
    
    属性：
    - id: 唯一标识符（如 "STEEL_LOW_CARBON", "STEEL_CHROMOLY"）
    - base_cost_multiplier: 基础成本倍数（相对于基准材料）
    - yield_strength_mpa: 屈服强度（MPa）- 永久变形的临界点
    - density: 密度（kg/m³）
    - thermal_conductivity: 热导率（W/m·K）- 影响冷却性能
    """
    id: str
    base_cost_multiplier: float
    yield_strength_mpa: float
    density: float  # kg/m³
    thermal_conductivity: float  # W/m·K


@dataclass
class ManufacturingProcess:
    """
    制造工艺 - 定义制造方法对成本和性能的影响
    
    属性：
    - id: 唯一标识符（如 "CASTING_SAND", "FORGING", "CNC"）
    - cost_setup: 设置成本（一次性投资）
    - cost_per_unit_mod: 单位成本修正（相对于基准）
    - strength_mod: 强度修正（锻造=1.4x，铸造=1.0x）
    - waste_ratio: 废料率（CNC=0.4，锻造=0.1）
    """
    id: str
    cost_setup: float
    cost_per_unit_mod: float
    strength_mod: float
    waste_ratio: float


# ========== 材料等级数据库 ==========

# 钢材等级
MATERIAL_GRADES: Dict[str, MaterialGrade] = {
    # 铸铁
    "CAST_IRON_STANDARD": MaterialGrade(
        id="CAST_IRON_STANDARD",
        base_cost_multiplier=1.0,
        yield_strength_mpa=250.0,  # 典型铸铁屈服强度
        density=7200.0,
        thermal_conductivity=50.0
    ),
    
    # 钢材等级
    "STEEL_LOW_CARBON": MaterialGrade(
        id="STEEL_LOW_CARBON",
        base_cost_multiplier=1.2,
        yield_strength_mpa=350.0,
        density=7850.0,
        thermal_conductivity=50.0
    ),
    "STEEL_MEDIUM_CARBON": MaterialGrade(
        id="STEEL_MEDIUM_CARBON",
        base_cost_multiplier=1.5,
        yield_strength_mpa=450.0,
        density=7850.0,
        thermal_conductivity=50.0
    ),
    "STEEL_CHROMOLY": MaterialGrade(
        id="STEEL_CHROMOLY",
        base_cost_multiplier=2.5,
        yield_strength_mpa=650.0,  # 铬钼钢，高强度
        density=7850.0,
        thermal_conductivity=50.0
    ),
    "STEEL_STAINLESS": MaterialGrade(
        id="STEEL_STAINLESS",
        base_cost_multiplier=3.0,
        yield_strength_mpa=500.0,
        density=8000.0,
        thermal_conductivity=15.0  # 不锈钢热导率较低
    ),
    
    # 铝合金
    "ALUMINIUM_CAST": MaterialGrade(
        id="ALUMINIUM_CAST",
        base_cost_multiplier=1.5,
        yield_strength_mpa=200.0,
        density=2700.0,
        thermal_conductivity=200.0  # 铝的热导率很高
    ),
    "ALUMINIUM_FORGED": MaterialGrade(
        id="ALUMINIUM_FORGED",
        base_cost_multiplier=2.0,
        yield_strength_mpa=300.0,
        density=2700.0,
        thermal_conductivity=200.0
    ),
    "ALUMINIUM_7075": MaterialGrade(
        id="ALUMINIUM_7075",
        base_cost_multiplier=3.5,
        yield_strength_mpa=500.0,  # 7075航空铝，高强度
        density=2700.0,
        thermal_conductivity=200.0
    ),
    
    # 钛合金
    "TITANIUM_GRADE5": MaterialGrade(
        id="TITANIUM_GRADE5",
        base_cost_multiplier=10.0,
        yield_strength_mpa=900.0,
        density=4500.0,
        thermal_conductivity=22.0
    ),
    
    # 碳纤维
    "CARBON_FIBER_STANDARD": MaterialGrade(
        id="CARBON_FIBER_STANDARD",
        base_cost_multiplier=15.0,
        yield_strength_mpa=600.0,  # 各向异性，这里是平均值
        density=1600.0,
        thermal_conductivity=5.0  # 碳纤维热导率低
    ),
}


# ========== 制造工艺数据库 ==========

MANUFACTURING_PROCESSES: Dict[str, ManufacturingProcess] = {
    # 铸造工艺
    "CASTING_SAND": ManufacturingProcess(
        id="CASTING_SAND",
        cost_setup=1000.0,  # 砂型铸造，设置成本低
        cost_per_unit_mod=1.0,
        strength_mod=1.0,
        waste_ratio=0.15  # 15%废料
    ),
    "CASTING_DIE": ManufacturingProcess(
        id="CASTING_DIE",
        cost_setup=50000.0,  # 压铸，模具成本高
        cost_per_unit_mod=0.7,  # 大批量时单位成本低
        strength_mod=1.1,
        waste_ratio=0.10
    ),
    
    # 锻造工艺
    "FORGING": ManufacturingProcess(
        id="FORGING",
        cost_setup=20000.0,
        cost_per_unit_mod=1.5,  # 单位成本较高
        strength_mod=1.4,  # 锻造强度提升40%
        waste_ratio=0.10
    ),
    "FORGING_CLOSED_DIE": ManufacturingProcess(
        id="FORGING_CLOSED_DIE",
        cost_setup=80000.0,  # 闭式模锻，模具成本极高
        cost_per_unit_mod=1.2,
        strength_mod=1.5,  # 强度提升50%
        waste_ratio=0.08
    ),
    
    # 冲压工艺
    "STAMPING": ManufacturingProcess(
        id="STAMPING",
        cost_setup=100000.0,  # 冲压模具成本高
        cost_per_unit_mod=0.5,  # 大批量时非常便宜
        strength_mod=1.0,
        waste_ratio=0.20  # 冲压废料较多
    ),
    
    # 机加工
    "CNC": ManufacturingProcess(
        id="CNC",
        cost_setup=5000.0,  # 设置成本中等
        cost_per_unit_mod=3.0,  # 单位成本高（人工+时间）
        strength_mod=1.0,
        waste_ratio=0.40  # CNC废料率很高
    ),
    "CNC_PRECISION": ManufacturingProcess(
        id="CNC_PRECISION",
        cost_setup=10000.0,
        cost_per_unit_mod=5.0,  # 精密加工更贵
        strength_mod=1.0,
        waste_ratio=0.50  # 精密加工废料更多
    ),
}


# ========== 工程核心计算类 ==========

class EngineeringCore:
    """
    工程核心物理引擎
    
    所有方法都是静态的，无状态。
    接受参数，返回物理/经济计算结果。
    """
    
    @staticmethod
    def calculate_component_stats(
        volume_m3: float,
        material_grade_id: str,
        process_id: str,
        design_complexity: float,
        load_requirements_n: float
    ) -> Dict[str, float]:
        """
        计算组件统计数据（重量、强度、可靠性）
        
        这是"终极零件计算器"，基于真实物理公式：
        1. 质量 = 体积 × 密度
        2. 强度 = 材料屈服强度 × 工艺强度修正
        3. 安全系数 = 强度 / 载荷要求
        4. 可靠性 = Sigmoid函数映射安全系数
        
        Args:
            volume_m3: 组件体积（立方米）
            material_grade_id: 材料等级ID
            process_id: 制造工艺ID
            design_complexity: 设计复杂度（1.0-10.0）
            load_requirements_n: 载荷要求（牛顿）- 最大扭矩/重量
            
        Returns:
            包含以下键的字典：
            - mass_kg: 质量（kg）
            - yield_strength_mpa: 屈服强度（MPa）
            - safety_factor: 安全系数
            - reliability_percent: 可靠性百分比（0-100）
        """
        # 获取材料等级
        material_grade = MATERIAL_GRADES.get(material_grade_id)
        if not material_grade:
            logger.warning(f"未知材料等级: {material_grade_id}，使用默认值")
            material_grade = MATERIAL_GRADES["STEEL_LOW_CARBON"]
        
        # 获取制造工艺
        process = MANUFACTURING_PROCESSES.get(process_id)
        if not process:
            logger.warning(f"未知制造工艺: {process_id}，使用默认值")
            process = MANUFACTURING_PROCESSES["CASTING_SAND"]
        
        # 1. 质量计算：Mass = Volume × Density
        mass_kg = volume_m3 * material_grade.density
        
        # 2. 强度计算：Strength = Material.YieldStrength × Process.StrengthMod
        # 设计复杂度影响：更复杂的设计可能引入应力集中
        complexity_strength_factor = 1.0 - (design_complexity - 1.0) * 0.02  # 每增加1复杂度，强度降低2%
        complexity_strength_factor = max(0.7, complexity_strength_factor)  # 最低70%
        
        effective_yield_strength_mpa = (
            material_grade.yield_strength_mpa * 
            process.strength_mod * 
            complexity_strength_factor
        )
        
        # 3. 安全系数计算：SF = Strength / Load_Requirements
        # 将载荷要求转换为应力（简化：假设均匀分布）
        # 应力 = 载荷 / 横截面积，这里用体积估算横截面积
        # 简化假设：横截面积 ≈ (体积)^(2/3)
        if volume_m3 > 0:
            estimated_area_m2 = (volume_m3 ** (2.0/3.0))
            stress_mpa = (load_requirements_n / estimated_area_m2) / 1_000_000.0  # 转换为MPa
        else:
            stress_mpa = 0.0
        
        if stress_mpa > 0:
            safety_factor = effective_yield_strength_mpa / stress_mpa
        else:
            safety_factor = 999.0  # 无载荷要求，安全系数极高
        
        # 4. 可靠性计算：使用Sigmoid函数映射安全系数到可靠性百分比
        # 如果SF < 1.0，可靠性 = 0%
        # 如果SF > 2.0，可靠性 = 99.9%
        # 使用Sigmoid: reliability = 100 / (1 + exp(-k*(SF - threshold)))
        if safety_factor < 1.0:
            reliability_percent = 0.0
        elif safety_factor > 2.0:
            reliability_percent = 99.9
        else:
            # 在1.0-2.0之间使用Sigmoid插值
            # 参数：k=5.0, threshold=1.5（中点）
            k = 5.0
            threshold = 1.5
            sigmoid_value = 1.0 / (1.0 + math.exp(-k * (safety_factor - threshold)))
            reliability_percent = sigmoid_value * 99.9
        
        return {
            "mass_kg": round(mass_kg, 2),
            "yield_strength_mpa": round(effective_yield_strength_mpa, 1),
            "safety_factor": round(safety_factor, 3),
            "reliability_percent": round(reliability_percent, 2)
        }
    
    @staticmethod
    def calculate_manufacturing_cost(
        base_material_cost: float,
        part_count: int,
        integration_complexity: float,
        process_id: str,
        volume_m3: float
    ) -> float:
        """
        计算制造成本（考虑复杂度指数缩放）
        
        公式：
        - 装配惩罚 = (零件数 × 0.5) × (集成复杂度 ^ 1.5)
        - 总成本 = 材料成本 + 工艺成本 + 装配惩罚
        
        原理：复杂度翻倍，成本应超过翻倍（墨菲定律）
        
        Args:
            base_material_cost: 基础材料成本
            part_count: 零件数量
            integration_complexity: 集成复杂度（1.0-10.0）
            process_id: 制造工艺ID
            volume_m3: 体积（用于计算废料成本）
            
        Returns:
            总制造成本
        """
        # 获取制造工艺
        process = MANUFACTURING_PROCESSES.get(process_id)
        if not process:
            process = MANUFACTURING_PROCESSES["CASTING_SAND"]
        
        # 1. 材料成本（考虑废料率）
        material_cost_with_waste = base_material_cost / (1.0 - process.waste_ratio)
        
        # 2. 工艺成本（设置成本摊销 + 单位成本）
        # 简化：假设设置成本摊销到1000个单位
        setup_cost_per_unit = process.cost_setup / 1000.0
        process_cost = volume_m3 * 1000.0 * process.cost_per_unit_mod * setup_cost_per_unit
        
        # 3. 装配惩罚（指数复杂度）
        # 复杂度翻倍，成本应超过翻倍
        assembly_penalty = (part_count * 0.5) * (integration_complexity ** 1.5)
        
        total_cost = material_cost_with_waste + process_cost + assembly_penalty
        
        return round(total_cost, 2)
    
    @staticmethod
    def get_maturity_modifier(
        tech_intro_year: int,
        current_year: int
    ) -> Dict[str, float]:
        """
        获取技术成熟度修正系数（时间-效率曲线）
        
        技术成熟度三个阶段：
        - Phase 1 (0-2年): 原型阶段 - 成本×3.0，故障率×2.0
        - Phase 2 (2-10年): 成熟阶段 - 线性下降到正常
        - Phase 3 (10+年): 商品化阶段 - 成本×0.8，质量稳定
        
        Args:
            tech_intro_year: 技术引入年份
            current_year: 当前年份
            
        Returns:
            包含以下键的字典：
            - cost_mod: 成本修正系数
            - quality_mod: 质量修正系数（影响可靠性）
        """
        years_active = current_year - tech_intro_year
        
        if years_active < 0:
            years_active = 0
        
        if years_active <= 2:
            # Phase 1: 原型阶段
            # 成本×3.0，故障率×2.0（质量修正 = 0.5）
            cost_mod = 3.0
            quality_mod = 0.5  # 故障率×2.0 = 质量×0.5
            
        elif years_active <= 10:
            # Phase 2: 成熟阶段 - 线性插值
            # 从 (2年, cost=3.0, quality=0.5) 到 (10年, cost=1.0, quality=1.0)
            phase2_ratio = (years_active - 2) / (10 - 2)
            cost_mod = 3.0 - (3.0 - 1.0) * phase2_ratio
            quality_mod = 0.5 + (1.0 - 0.5) * phase2_ratio
            
        else:
            # Phase 3: 商品化阶段
            cost_mod = 0.8
            quality_mod = 1.0
        
        return {
            "cost_mod": round(cost_mod, 3),
            "quality_mod": round(quality_mod, 3)
        }
    
    @staticmethod
    def evaluate_chassis_design(
        geometry: Dict[str, float],
        material_grade_id: str,
        process_id: str,
        current_year: int,
        tech_intro_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        评估底盘设计
        
        输入几何参数、材料、工艺、年份，返回重量、成本、最大载荷、可靠性评分。
        
        Args:
            geometry: 几何参数字典，包含：
                - volume_m3: 体积（立方米）
                - surface_area_m2: 表面积（平方米，可选）
                - load_requirements_n: 载荷要求（牛顿）
            material_grade_id: 材料等级ID
            process_id: 制造工艺ID
            current_year: 当前年份
            tech_intro_year: 技术引入年份（可选，用于成熟度修正）
            
        Returns:
            包含以下键的字典：
            - weight_kg: 重量（kg）
            - cost: 成本
            - max_load_n: 最大载荷（N）
            - reliability_score: 可靠性评分（0-100）
        """
        volume_m3 = geometry.get("volume_m3", 0.0)
        load_requirements_n = geometry.get("load_requirements_n", 10000.0)  # 默认10kN
        design_complexity = geometry.get("design_complexity", 5.0)
        
        # 计算组件统计
        component_stats = EngineeringCore.calculate_component_stats(
            volume_m3=volume_m3,
            material_grade_id=material_grade_id,
            process_id=process_id,
            design_complexity=design_complexity,
            load_requirements_n=load_requirements_n
        )
        
        # 获取材料等级（用于成本计算）
        material_grade = MATERIAL_GRADES.get(material_grade_id)
        if not material_grade:
            material_grade = MATERIAL_GRADES["STEEL_LOW_CARBON"]
        
        # 基础材料成本（简化：基于体积和密度）
        base_material_cost = volume_m3 * material_grade.density * 2.0  # $2/kg基准
        
        # 应用材料成本倍数
        base_material_cost *= material_grade.base_cost_multiplier
        
        # 计算制造成本
        part_count = int(geometry.get("part_count", 50))  # 默认50个零件
        integration_complexity = geometry.get("integration_complexity", 5.0)
        
        cost = EngineeringCore.calculate_manufacturing_cost(
            base_material_cost=base_material_cost,
            part_count=part_count,
            integration_complexity=integration_complexity,
            process_id=process_id,
            volume_m3=volume_m3
        )
        
        # 应用技术成熟度修正
        if tech_intro_year:
            maturity = EngineeringCore.get_maturity_modifier(tech_intro_year, current_year)
            cost *= maturity["cost_mod"]
            component_stats["reliability_percent"] *= maturity["quality_mod"]
        
        # 最大载荷 = 屈服强度 × 横截面积
        # 简化：使用体积估算横截面积
        if volume_m3 > 0:
            estimated_area_m2 = (volume_m3 ** (2.0/3.0))
            max_load_n = component_stats["yield_strength_mpa"] * 1_000_000.0 * estimated_area_m2
        else:
            max_load_n = 0.0
        
        return {
            "weight_kg": component_stats["mass_kg"],
            "cost": round(cost, 2),
            "max_load_n": round(max_load_n, 0),
            "reliability_score": round(component_stats["reliability_percent"], 2)
        }
    
    @staticmethod
    def evaluate_engine_block(
        displacement_cc: int,
        layout: str,
        material_grade_id: str,
        process_id: str,
        current_year: int,
        stroke_mm: float,
        tech_intro_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        评估引擎缸体设计
        
        输入排量、布局、材料、工艺、年份，返回缸体重量、最大RPM限制、热容量。
        
        重要：max_rpm_limit 基于材料应力限制 vs 活塞速度（物理计算）
        
        Args:
            displacement_cc: 排量（立方厘米）
            layout: 引擎布局（"INLINE", "V", "BOXER"等）
            material_grade_id: 材料等级ID
            process_id: 制造工艺ID
            current_year: 当前年份
            stroke_mm: 行程（毫米）- 用于计算MPS限制
            tech_intro_year: 技术引入年份（可选）
            
        Returns:
            包含以下键的字典：
            - block_weight_kg: 缸体重量（kg）
            - max_rpm_limit: 最大RPM限制（基于MPS）
            - thermal_capacity_kw: 热容量（kW）
        """
        # 估算缸体体积（简化：基于排量）
        # 缸体体积 ≈ 排量 × 2.0（包括缸壁、水道等）
        displacement_m3 = displacement_cc / 1_000_000.0
        block_volume_m3 = displacement_m3 * 2.0
        
        # 计算组件统计（载荷要求：基于排量估算）
        # 简化：假设每升排量产生1000N的载荷
        load_requirements_n = (displacement_cc / 1000.0) * 1000.0
        
        component_stats = EngineeringCore.calculate_component_stats(
            volume_m3=block_volume_m3,
            material_grade_id=material_grade_id,
            process_id=process_id,
            design_complexity=6.0,  # 引擎缸体复杂度较高
            load_requirements_n=load_requirements_n
        )
        
        # 获取材料等级
        material_grade = MATERIAL_GRADES.get(material_grade_id)
        if not material_grade:
            material_grade = MATERIAL_GRADES["CAST_IRON_STANDARD"]
        
        # 计算最大RPM限制（基于Mean Piston Speed）
        # MPS公式：MPS (m/s) = (Stroke × RPM × 2) / 60,000
        # 反推：RPM = (MPS × 60,000) / (Stroke × 2)
        # 材料限制：不同材料有不同的最大MPS
        # 简化：基于屈服强度估算最大MPS
        # 高强度材料可以承受更高的MPS
        max_mps_ms = 15.0 + (material_grade.yield_strength_mpa / 100.0)  # 基础15 m/s + 强度加成
        max_mps_ms = min(max_mps_ms, 30.0)  # 上限30 m/s
        
        stroke_m = stroke_mm / 1000.0
        if stroke_m > 0:
            max_rpm_limit = int((max_mps_ms * 60000.0) / (stroke_mm * 2.0))
        else:
            max_rpm_limit = 6000  # 默认值
        
        # 布局影响（某些布局平衡性更好，可以转得更快）
        layout_factor = {
            "INLINE": 1.0,
            "V": 1.05,
            "BOXER": 1.10,  # 水平对置最平衡
            "VR": 1.02,
            "W": 1.08,
        }.get(layout, 1.0)
        
        max_rpm_limit = int(max_rpm_limit * layout_factor)
        max_rpm_limit = max(3000, min(max_rpm_limit, 12000))  # 限制在合理范围
        
        # 热容量计算（基于材料热导率和体积）
        # 简化：热容量 = 热导率 × 体积 × 系数
        thermal_capacity_kw = (
            material_grade.thermal_conductivity * 
            block_volume_m3 * 
            100.0  # 经验系数
        )
        
        # 应用技术成熟度修正
        if tech_intro_year:
            maturity = EngineeringCore.get_maturity_modifier(tech_intro_year, current_year)
            # 成熟技术可以优化重量和热容量
            component_stats["mass_kg"] *= (1.0 / maturity["cost_mod"])  # 成本降低 = 优化设计 = 减重
        
        return {
            "block_weight_kg": round(component_stats["mass_kg"], 2),
            "max_rpm_limit": max_rpm_limit,
            "thermal_capacity_kw": round(thermal_capacity_kw, 2)
        }


# ========== 导出 ==========

__all__ = [
    "MaterialType",
    "MaterialGrade",
    "ManufacturingProcess",
    "EngineeringCore",
    "MATERIAL_GRADES",
    "MANUFACTURING_PROCESSES"
]


