"""
程序化车辆物理计算 - 连续参数代替预设车身
Procedural Vehicle Physics - Continuous parameters instead of preset bodies

核心哲学：
- 车身由几何参数定义（轴距、悬挂、尺寸），而非选择预设模板
- 所有性能和成本从物理公式派生
- 材料选择直接影响重量和成本
- 数据驱动：材料属性从 GameDataLoader 加载
"""
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
import math
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
class BodyDimensions:
    """车身几何参数（连续值）"""
    wheelbase_mm: float              # 轴距
    track_width_mm: float            # 轮距
    front_overhang_mm: float         # 前悬
    rear_overhang_mm: float          # 后悬
    bonnet_height_mm: float          # 引擎盖高度（影响引擎舱容积）
    roof_height_mm: float            # 车顶高度
    width_mm: float                  # 车身宽度
    
    @property
    def total_length_mm(self) -> float:
        """总长 = 前悬 + 轴距 + 后悬"""
        return self.front_overhang_mm + self.wheelbase_mm + self.rear_overhang_mm
    
    @property
    def frontal_area_sqm(self) -> float:
        """正面投影面积（m²）"""
        return (self.width_mm / 1000.0) * (self.roof_height_mm / 1000.0)


@dataclass
class MaterialProperties:
    """材料物理特性"""
    name: str
    density_kg_m3: float         # 密度（kg/m³）
    cost_per_m2: float           # 成本（$/m²）
    strength_multiplier: float   # 强度系数（影响需要的厚度）
    tech_level_required: int     # 所需技术等级


@dataclass
class MaterialProperties:
    """材料物理特性"""
    name: str
    density_kg_m3: float
    cost_per_m2: float
    strength_multiplier: float
    tech_level_required: int


def _load_materials_from_data_loader() -> Dict[str, MaterialProperties]:
    """从数据加载器加载材料数据"""
    try:
        from backend.core.loader import get_game_data_loader
        loader = get_game_data_loader()
        
        materials = {}
        for mat_data in loader.list_all_materials():
            materials[mat_data.id] = MaterialProperties(
                name=mat_data.name,
                density_kg_m3=mat_data.density_kg_m3,
                cost_per_m2=mat_data.cost_per_m2,
                strength_multiplier=mat_data.strength_multiplier,
                tech_level_required=mat_data.tech_level_required
            )
        
        logger.info(f"从数据加载器加载了 {len(materials)} 种车身材料")
        return materials
        
    except Exception as e:
        logger.warning(f"无法从数据加载器加载材料，使用默认值: {e}")
        # 向后兼容：如果数据加载器未初始化，使用默认值
        return {
            "STEEL": MaterialProperties(
                name="Steel",
                density_kg_m3=7850,
                cost_per_m2=25.0,
                strength_multiplier=1.0,
                tech_level_required=1
            ),
            "ALUMINUM": MaterialProperties(
                name="Aluminum",
                density_kg_m3=2700,
                cost_per_m2=75.0,
                strength_multiplier=0.85,
                tech_level_required=4
            ),
            "CARBON": MaterialProperties(
                name="Carbon Fiber",
                density_kg_m3=1600,
                cost_per_m2=450.0,
                strength_multiplier=1.5,
                tech_level_required=8
            ),
            "HSS": MaterialProperties(
                name="High Strength Steel",
                density_kg_m3=7850,
                cost_per_m2=40.0,
                strength_multiplier=1.3,
                tech_level_required=6
            )
        }


# 材料数据库（懒加载）
_MATERIALS_CACHE: Dict[str, MaterialProperties] = None


def get_materials() -> Dict[str, MaterialProperties]:
    """获取材料数据（单例模式）"""
    global _MATERIALS_CACHE
    if _MATERIALS_CACHE is None:
        _MATERIALS_CACHE = _load_materials_from_data_loader()
    return _MATERIALS_CACHE


# 导出MATERIALS作为函数调用，向后兼容
@property
def MATERIALS() -> Dict[str, MaterialProperties]:
    return get_materials()


# 为了向后兼容，提供MATERIALS作为模块级变量（首次访问时加载）
class _MaterialsProxy:
    def __getitem__(self, key):
        return get_materials()[key]
    
    def get(self, key, default=None):
        return get_materials().get(key, default)
    
    def keys(self):
        return get_materials().keys()
    
    def values(self):
        return get_materials().values()
    
    def items(self):
        return get_materials().items()


MATERIALS = _MaterialsProxy()


class ChassisCalculator:
    """
    车身物理计算器
    
    基于真实物理公式计算：
    - 白车身（BIW）重量和成本
    - 空间约束（引擎舱、座舱）
    - 空气动力学参数
    """
    
    # 工程常数
    AVERAGE_PANEL_THICKNESS_MM = 0.8      # 平均板材厚度（毫米）
    STRUCTURAL_REINFORCEMENT_FACTOR = 1.3  # 结构加强系数（支柱、横梁等增重）
    FLUIDS_AND_SYSTEMS_KG = 80.0          # 流体和系统重量（机油、冷却液、电气等）
    
    @staticmethod
    def calculate_surface_area(dims: BodyDimensions) -> float:
        """
        计算车身表面积（简化矩形模型）
        
        实际车身是复杂曲面，这里用近似公式：
        S ≈ 2 * (L×W + L×H + W×H) * curvature_factor
        
        Args:
            dims: 车身尺寸参数
            
        Returns:
            表面积（m²）
        """
        L = dims.total_length_mm / 1000.0  # 转换为米
        W = dims.width_mm / 1000.0
        H = dims.roof_height_mm / 1000.0
        
        # 基础表面积（矩形盒子）
        base_area = 2 * (L*W + L*H + W*H)
        
        # 曲率系数（实际车身比矩形盒子表面积大10-15%）
        curvature_factor = 1.12
        
        return base_area * curvature_factor
    
    @staticmethod
    def calculate_biw_weight(
        dims: BodyDimensions,
        material: str,
        tech_level: int,
        material_grade_id: Optional[str] = None,
        process_id: Optional[str] = None,
        current_year: Optional[int] = None
    ) -> float:
        """
        计算白车身重量（Body-In-White）
        
        现在使用 EngineeringCore 物理引擎进行硬核模拟计算。
        如果提供了 material_grade_id 和 process_id，将使用新的物理引擎。
        否则，使用向后兼容的旧方法。
        
        Formula:
            Weight = Surface Area × Thickness × Density × Structural Factor
            
        考虑因素：
        - 材料密度
        - 板材厚度（受材料强度影响）
        - 结构加强件（支柱、横梁、防撞梁）
        - 技术等级（更高技术 = 更优化结构）
        - 制造工艺（锻造 vs 铸造）
        
        Args:
            dims: 车身尺寸
            material: 材料类型（"STEEL", "ALUMINUM", "CARBON"）
            tech_level: 技术等级 1-10
            material_grade_id: 材料等级ID（可选，如 "STEEL_LOW_CARBON"）
            process_id: 制造工艺ID（可选，如 "STAMPING", "FORGING"）
            current_year: 当前年份（可选，用于技术成熟度修正）
            
        Returns:
            白车身重量（kg）
        """
        # 如果提供了新参数且 EngineeringCore 可用，使用新的物理引擎
        if (ENGINEERING_CORE_AVAILABLE and 
            material_grade_id and 
            process_id and 
            current_year is not None):
            
            try:
                # 计算体积（基于表面积和厚度）
                surface_area_m2 = ChassisCalculator.calculate_surface_area(dims)
                mat = MATERIALS.get(material, MATERIALS["STEEL"])
                base_thickness_m = ChassisCalculator.AVERAGE_PANEL_THICKNESS_MM / 1000.0
                effective_thickness_m = base_thickness_m / mat.strength_multiplier
                volume_m3 = surface_area_m2 * effective_thickness_m * ChassisCalculator.STRUCTURAL_REINFORCEMENT_FACTOR
                
                # 估算载荷要求（基于车身尺寸）
                # 简化：假设每平方米表面积需要承受10kN载荷
                load_requirements_n = surface_area_m2 * 10000.0
                
                # 使用 EngineeringCore 评估底盘设计
                geometry = {
                    "volume_m3": volume_m3,
                    "load_requirements_n": load_requirements_n,
                    "design_complexity": 5.0 + (tech_level - 1) * 0.5,  # 技术等级影响复杂度
                    "part_count": 100,  # 估算零件数
                    "integration_complexity": 5.0
                }
                
                result = EngineeringCore.evaluate_chassis_design(
                    geometry=geometry,
                    material_grade_id=material_grade_id,
                    process_id=process_id,
                    current_year=current_year,
                    tech_intro_year=current_year - tech_level * 2  # 简化：假设技术引入年份
                )
                
                return result["weight_kg"]
                
            except Exception as e:
                logger.warning(f"使用 EngineeringCore 计算失败，回退到旧方法: {e}")
                # 继续使用旧方法
        
        # 向后兼容：使用旧的计算方法
        mat = MATERIALS.get(material, MATERIALS["STEEL"])
        
        # 1. 计算表面积
        surface_area_m2 = ChassisCalculator.calculate_surface_area(dims)
        
        # 2. 有效厚度（考虑材料强度）
        base_thickness_m = ChassisCalculator.AVERAGE_PANEL_THICKNESS_MM / 1000.0
        effective_thickness_m = base_thickness_m / mat.strength_multiplier
        
        # 3. 板材重量
        panel_volume_m3 = surface_area_m2 * effective_thickness_m
        panel_weight_kg = panel_volume_m3 * mat.density_kg_m3
        
        # 4. 结构加强件（支柱、横梁、防撞梁等）
        structural_weight_kg = panel_weight_kg * (ChassisCalculator.STRUCTURAL_REINFORCEMENT_FACTOR - 1.0)
        
        # 5. 技术优化（更高技术等级 = 更优化的结构设计）
        # Tech 1: 无优化（1.0）
        # Tech 5: 10%优化（0.9）
        # Tech 10: 20%优化（0.8）
        tech_optimization_factor = 1.0 - (tech_level - 1) * 0.022
        
        total_biw_weight = (panel_weight_kg + structural_weight_kg) * tech_optimization_factor
        
        return total_biw_weight
    
    @staticmethod
    def calculate_structure_type_modifiers(
        structure_type: str,
        current_year: int = 1946
    ) -> Dict[str, float]:
        """
        计算结构类型对底盘性能的影响系数
        
        Args:
            structure_type: 结构类型 ("LADDER" 或 "MONOCOQUE")
            current_year: 当前年份（用于技术解锁检查）
            
        Returns:
            包含 weight_factor, stiffness_factor, cost_factor, durability_factor 的字典
        """
        if structure_type == "LADDER":
            # 非承载式 (Ladder Frame)
            return {
                "weight_factor": 1.20,      # +20% 重量
                "stiffness_factor": 0.85,   # -15% 刚性
                "cost_factor": 0.90,        # -10% 成本
                "durability_factor": 1.30,  # +30% 耐久性
            }
        elif structure_type == "MONOCOQUE":
            # 承载式 (Monocoque)
            # 早期年份成本更高（技术不成熟）
            early_year_penalty = 1.0
            if current_year < 1960:
                early_year_penalty = 1.3  # 1960年前成本+30%
            elif current_year < 1970:
                early_year_penalty = 1.15  # 1970年前成本+15%
            
            return {
                "weight_factor": 0.85,      # -15% 重量
                "stiffness_factor": 1.25,   # +25% 刚性
                "cost_factor": 1.20 * early_year_penalty,  # +20% 成本（早期更高）
                "durability_factor": 0.95,  # -5% 耐久性（更易损坏）
            }
        else:
            # 默认值（Ladder）
            return {
                "weight_factor": 1.0,
                "stiffness_factor": 1.0,
                "cost_factor": 1.0,
                "durability_factor": 1.0,
            }
    
    @staticmethod
    def calculate_biw_cost(
        dims: BodyDimensions,
        material: str,
        tech_level: int,
        material_grade_id: Optional[str] = None,
        process_id: Optional[str] = None,
        current_year: Optional[int] = None
    ) -> float:
        """
        计算白车身制造成本
        
        现在使用 EngineeringCore 物理引擎进行硬核模拟计算。
        如果提供了 material_grade_id 和 process_id，将使用新的物理引擎。
        否则，使用向后兼容的旧方法。
        
        Formula:
            Cost = Material Cost + Tooling Cost + Assembly Cost + Complexity Penalty
            
        Args:
            dims: 车身尺寸
            material: 材料类型
            tech_level: 技术等级
            material_grade_id: 材料等级ID（可选）
            process_id: 制造工艺ID（可选）
            current_year: 当前年份（可选）
            
        Returns:
            制造成本（游戏币）
        """
        # 如果提供了新参数且 EngineeringCore 可用，使用新的物理引擎
        if (ENGINEERING_CORE_AVAILABLE and 
            material_grade_id and 
            process_id and 
            current_year is not None):
            
            try:
                # 计算体积
                surface_area_m2 = ChassisCalculator.calculate_surface_area(dims)
                mat = MATERIALS.get(material, MATERIALS["STEEL"])
                base_thickness_m = ChassisCalculator.AVERAGE_PANEL_THICKNESS_MM / 1000.0
                effective_thickness_m = base_thickness_m / mat.strength_multiplier
                volume_m3 = surface_area_m2 * effective_thickness_m * ChassisCalculator.STRUCTURAL_REINFORCEMENT_FACTOR
                
                # 估算载荷要求
                load_requirements_n = surface_area_m2 * 10000.0
                
                # 使用 EngineeringCore 评估底盘设计
                geometry = {
                    "volume_m3": volume_m3,
                    "load_requirements_n": load_requirements_n,
                    "design_complexity": 5.0 + (tech_level - 1) * 0.5,
                    "part_count": 100,
                    "integration_complexity": 5.0 + (tech_level - 1) * 0.3
                }
                
                result = EngineeringCore.evaluate_chassis_design(
                    geometry=geometry,
                    material_grade_id=material_grade_id,
                    process_id=process_id,
                    current_year=current_year,
                    tech_intro_year=current_year - tech_level * 2
                )
                
                return result["cost"]
                
            except Exception as e:
                logger.warning(f"使用 EngineeringCore 计算成本失败，回退到旧方法: {e}")
                # 继续使用旧方法
        
        # 向后兼容：使用旧的计算方法
        mat = MATERIALS.get(material, MATERIALS["STEEL"])
        
        # 1. 材料成本
        surface_area_m2 = ChassisCalculator.calculate_surface_area(dims)
        material_cost = surface_area_m2 * mat.cost_per_m2
        
        # 2. 冲压和焊接成本（固定成本）
        base_tooling_cost = 5000.0  # 基础模具成本
        welding_cost_per_m2 = 30.0  # 焊接成本
        stamping_cost = base_tooling_cost + (surface_area_m2 * welding_cost_per_m2)
        
        # 3. 组装人工成本（与车身大小相关）
        assembly_hours = 20 + (surface_area_m2 * 2.0)  # 基础20小时 + 尺寸影响
        labor_rate_per_hour = 50.0
        assembly_cost = assembly_hours * labor_rate_per_hour
        
        # 4. 技术复杂度系数（更高技术 = 更贵的工艺）
        tech_complexity_multiplier = 1.0 + (tech_level - 1) * 0.05
        
        total_cost = (material_cost + stamping_cost + assembly_cost) * tech_complexity_multiplier
        
        return total_cost
    
    @staticmethod
    def calculate_engine_bay_volume(
        dims: BodyDimensions,
        layout: str = "FF"
    ) -> float:
        """
        计算引擎舱可用容积（Critical Constraint!）
        
        前置引擎 (FF/FR): 引擎舱在前悬部分
        中置引擎 (MR): 引擎在座舱后方
        后置引擎 (RR): 引擎在后悬部分
        
        Args:
            dims: 车身尺寸
            layout: 驱动布局（"FF", "FR", "MR", "RR"）
            
        Returns:
            引擎舱容积（升）
        """
        if layout in ["FF", "FR"]:
            # 前置引擎：引擎舱长度 ≈ 前悬长度 + 10%轴距
            bay_length_mm = dims.front_overhang_mm + (dims.wheelbase_mm * 0.1)
            bay_width_mm = dims.width_mm * 0.85  # 留出轮拱空间
            bay_height_mm = dims.bonnet_height_mm * 0.8  # 留出引擎盖间隙
            
        elif layout == "MR":
            # 中置引擎：引擎在座椅后方
            bay_length_mm = dims.wheelbase_mm * 0.25
            bay_width_mm = dims.width_mm * 0.7
            bay_height_mm = dims.roof_height_mm * 0.6
            
        elif layout == "RR":
            # 后置引擎：引擎舱在后悬
            bay_length_mm = dims.rear_overhang_mm + (dims.wheelbase_mm * 0.05)
            bay_width_mm = dims.width_mm * 0.8
            bay_height_mm = dims.roof_height_mm * 0.5
            
        else:
            raise ValueError(f"Unknown layout: {layout}")
        
        # 转换为升
        volume_mm3 = bay_length_mm * bay_width_mm * bay_height_mm
        volume_liters = volume_mm3 / 1_000_000
        
        return volume_liters
    
    @staticmethod
    def calculate_cabin_volume(dims: BodyDimensions) -> float:
        """
        计算座舱容积（影响舒适度）
        
        Formula:
            Cabin Volume ≈ Wheelbase × Width × (Roof Height - Floor Height)
            
        Args:
            dims: 车身尺寸
            
        Returns:
            座舱容积（升）
        """
        cabin_length_mm = dims.wheelbase_mm * 0.7  # 轴距的70%用于乘客空间
        cabin_width_mm = dims.width_mm * 0.9      # 减去门板厚度
        cabin_height_mm = dims.roof_height_mm * 0.6  # 减去地板和车顶厚度
        
        volume_mm3 = cabin_length_mm * cabin_width_mm * cabin_height_mm
        volume_liters = volume_mm3 / 1_000_000
        
        return volume_liters
    
    @staticmethod
    def calculate_drag_coefficient(
        dims: BodyDimensions,
        body_style: str,
        tech_level: int
    ) -> float:
        """
        计算风阻系数（Cd）
        
        基于：
        - 车身造型（轿车 vs SUV）
        - 长宽比
        - 技术等级（更高技术 = 更好的空气动力学设计）
        
        Args:
            dims: 车身尺寸
            body_style: 车身类型
            tech_level: 技术等级
            
        Returns:
            风阻系数（无量纲）
        """
        # 基础Cd值（根据车身类型）- 尝试从数据加载器获取
        try:
            from backend.core.loader import get_game_data_loader
            loader = get_game_data_loader()
            base_cd_data = loader._data_loader.physics_constants.get("drag_coefficients_base", {}) if loader._data_loader else {}
            base_cd = base_cd_data.get(body_style, None)
        except:
            base_cd = None
        
        # 如果数据加载器没有数据，使用默认值
        if base_cd is None:
            base_cd = {
                "SEDAN": 0.35,
                "COUPE": 0.32,
                "HATCHBACK": 0.36,
                "WAGON": 0.38,
                "SUV": 0.42,
                "TRUCK": 0.48,
                "CONVERTIBLE": 0.38,
                "VAN": 0.40
            }.get(body_style, 0.40)
        
        # 长宽比影响（更流线型 = 更低Cd）
        length_width_ratio = dims.total_length_mm / dims.width_mm
        if length_width_ratio < 2.5:
            ratio_penalty = 0.03  # 太短太宽
        elif length_width_ratio > 3.5:
            ratio_penalty = 0.02  # 太长
        else:
            ratio_penalty = 0.0   # 理想比例
        
        # 高度影响（更低 = 更好）
        height_penalty = (dims.roof_height_mm - 1300) / 1000 * 0.02
        height_penalty = max(0.0, height_penalty)  # 不给奖励，只有惩罚
        
        # 技术优化（更高技术 = 更好的空气动力学调教）
        # Tech 1: 无优化
        # Tech 5: -0.02
        # Tech 10: -0.05
        tech_improvement = (tech_level - 1) * 0.006
        
        final_cd = base_cd + ratio_penalty + height_penalty - tech_improvement
        
        # 合理范围检查
        return max(0.25, min(0.60, final_cd))
    
    @staticmethod
    def calculate_body_stats(
        dims: BodyDimensions,
        material: str,
        body_style: str,
        layout: str,
        tech_level: int
    ) -> Dict[str, Any]:
        """
        综合计算车身所有统计数据
        
        这是主入口函数，供 EngineeringService 调用
        
        Args:
            dims: 车身几何参数
            material: 材料类型
            body_style: 车身类型
            layout: 驱动布局
            tech_level: 技术等级
            
        Returns:
            包含所有车身统计数据的字典
        """
        # 验证材料技术要求
        mat = MATERIALS.get(material)
        if not mat:
            raise ValueError(f"Unknown material: {material}")
        
        if tech_level < mat.tech_level_required:
            raise ValueError(
                f"{material} requires tech level {mat.tech_level_required}, "
                f"but current level is {tech_level}"
            )
        
        # 计算所有统计数据
        stats = {
            # 重量
            "biw_weight_kg": ChassisCalculator.calculate_biw_weight(dims, material, tech_level),
            
            # 成本
            "biw_cost": ChassisCalculator.calculate_biw_cost(dims, material, tech_level),
            
            # 空间约束
            "engine_bay_volume_liters": ChassisCalculator.calculate_engine_bay_volume(dims, layout),
            "cabin_volume_liters": ChassisCalculator.calculate_cabin_volume(dims),
            
            # 空气动力学
            "drag_coefficient": ChassisCalculator.calculate_drag_coefficient(dims, body_style, tech_level),
            "frontal_area_sqm": dims.frontal_area_sqm,
            
            # 尺寸信息
            "total_length_mm": dims.total_length_mm,
            "wheelbase_mm": dims.wheelbase_mm,
            "width_mm": dims.width_mm,
            "height_mm": dims.roof_height_mm,
            
            # 材料信息
            "material": material,
            "material_density": mat.density_kg_m3,
            "surface_area_m2": ChassisCalculator.calculate_surface_area(dims),
        }
        
        return stats
    
    @staticmethod
    def validate_engine_fit(
        engine_dimensions: Dict[str, float],
        body_stats: Dict[str, Any],
        layout: str
    ) -> Tuple[bool, str]:
        """
        验证引擎是否能装入引擎舱
        
        这是关键约束检查！
        
        Args:
            engine_dimensions: 引擎尺寸 {"length_mm", "width_mm", "height_mm"}
            body_stats: 车身统计数据（来自 calculate_body_stats）
            layout: 驱动布局
            
        Returns:
            (是否兼容, 消息)
        """
        # 从体积反推近似尺寸约束
        # Volume = L × W × H
        # 假设引擎舱是长方体，取各边约束
        bay_volume_liters = body_stats["engine_bay_volume_liters"]
        bay_volume_mm3 = bay_volume_liters * 1_000_000
        
        # 粗略估算引擎舱尺寸（立方根）
        # 实际应从 BodyDimensions 计算，这里简化
        avg_dimension = bay_volume_mm3 ** (1/3)
        
        # 引擎舱尺寸估算（根据布局调整比例）
        if layout in ["FF", "FR"]:
            bay_length = avg_dimension * 1.5
            bay_width = avg_dimension * 0.9
            bay_height = avg_dimension * 0.8
        elif layout == "MR":
            bay_length = avg_dimension * 1.0
            bay_width = avg_dimension * 0.9
            bay_height = avg_dimension * 1.0
        else:  # RR
            bay_length = avg_dimension * 1.3
            bay_width = avg_dimension * 0.85
            bay_height = avg_dimension * 0.7
        
        # 检查各维度（留5%安装间隙）
        clearance = 1.05
        
        if engine_dimensions["length_mm"] * clearance > bay_length:
            return False, f"Engine too long ({engine_dimensions['length_mm']:.0f}mm > {bay_length:.0f}mm)"
        
        if engine_dimensions["width_mm"] * clearance > bay_width:
            return False, f"Engine too wide ({engine_dimensions['width_mm']:.0f}mm > {bay_width:.0f}mm)"
        
        if engine_dimensions["height_mm"] * clearance > bay_height:
            return False, f"Engine too tall ({engine_dimensions['height_mm']:.0f}mm > {bay_height:.0f}mm)"
        
        # 检查是否过于紧凑（维护困难）
        length_usage = engine_dimensions["length_mm"] / bay_length
        width_usage = engine_dimensions["width_mm"] / bay_width
        height_usage = engine_dimensions["height_mm"] / bay_height
        
        if any(usage > 0.95 for usage in [length_usage, width_usage, height_usage]):
            return True, "WARNING: Very tight fit, difficult maintenance access"
        
        return True, "Compatible"
    
    @staticmethod
    def calculate_manufacturing_complexity(
        torsional_rigidity_target: int = 50,
        rust_protection_level: str = "NONE",
        nvh_insulation_mass: float = 0.0,
        crumple_zone_length: float = 0.0,
        transmission_tunnel_fitted: bool = False,
        parts_bin_sharing_ratio: float = 0.5,
        material: str = "STEEL",
        tech_level: int = 5
    ) -> float:
        """
        计算制造复杂度评分 (0.0-1.0)
        
        复杂度越高，工厂缺陷率越高，需要更熟练的工人
        
        Args:
            torsional_rigidity_target: 扭转刚性目标 (1-100)
            rust_protection_level: 防锈保护级别
            nvh_insulation_mass: NVH隔音质量 (kg)
            crumple_zone_length: 溃缩区长度 (m)
            transmission_tunnel_fitted: 是否安装传动轴通道
            parts_bin_sharing_ratio: 零件库共享比例 (0.0-1.0)
            material: 材料类型
            tech_level: 技术等级
            
        Returns:
            制造复杂度评分 (0.0-1.0)，越高越复杂
        """
        complexity = 0.0
        
        # 1. 扭转刚性影响 (高刚性 = 更复杂的焊接和加固)
        rigidity_factor = (torsional_rigidity_target - 1) / 99.0  # 归一化到0-1
        complexity += rigidity_factor * 0.15
        
        # 2. 防锈保护影响
        rust_complexity = {
            "NONE": 0.0,
            "PARTIAL_GALVANIZED": 0.10,
            "FULL_DIP": 0.20,
        }.get(rust_protection_level, 0.0)
        complexity += rust_complexity
        
        # 3. NVH隔音影响 (更多隔音材料 = 更复杂的安装)
        nvh_factor = min(nvh_insulation_mass / 50.0, 1.0)  # 50kg为上限
        complexity += nvh_factor * 0.10
        
        # 4. 溃缩区影响 (更长的溃缩区 = 更复杂的结构设计)
        crumple_factor = min(crumple_zone_length / 1.0, 1.0)  # 1.0m为上限
        complexity += crumple_factor * 0.15
        
        # 5. 传动轴通道影响
        if transmission_tunnel_fitted:
            complexity += 0.10
        
        # 6. 零件库共享影响 (高共享 = 低复杂度，因为使用标准件)
        complexity += (1.0 - parts_bin_sharing_ratio) * 0.15
        
        # 7. 材料影响
        material_complexity = {
            "STEEL": 0.0,
            "ALUMINUM": 0.10,
            "CARBON": 0.25,
        }.get(material, 0.0)
        complexity += material_complexity
        
        # 8. 技术等级影响 (高技术 = 更复杂的工艺)
        tech_factor = (tech_level - 1) / 9.0  # 归一化到0-1
        complexity += tech_factor * 0.10
        
        # 限制在0.0-1.0范围
        return max(0.0, min(1.0, complexity))
    
    @staticmethod
    def calculate_enhanced_weight(
        base_weight_kg: float,
        nvh_insulation_mass: float = 0.0,
        crumple_zone_length: float = 0.0,
        rust_protection_level: str = "NONE",
        torsional_rigidity_target: int = 50
    ) -> float:
        """
        计算增强后的底盘重量（考虑新参数）
        
        Args:
            base_weight_kg: 基础重量（来自calculate_biw_weight）
            nvh_insulation_mass: NVH隔音质量 (kg)
            crumple_zone_length: 溃缩区长度 (m)
            rust_protection_level: 防锈保护级别
            torsional_rigidity_target: 扭转刚性目标
            
        Returns:
            总重量 (kg)
        """
        total_weight = base_weight_kg
        
        # 1. NVH隔音质量直接增加
        total_weight += nvh_insulation_mass
        
        # 2. 溃缩区增加重量（每米约+15kg结构加强）
        crumple_weight = crumple_zone_length * 15.0
        total_weight += crumple_weight
        
        # 3. 防锈保护增加重量（镀锌层）
        rust_weight = {
            "NONE": 0.0,
            "PARTIAL_GALVANIZED": 5.0,
            "FULL_DIP": 12.0,
        }.get(rust_protection_level, 0.0)
        total_weight += rust_weight
        
        # 4. 高扭转刚性需要更多加强件
        if torsional_rigidity_target > 70:
            rigidity_weight = (torsional_rigidity_target - 70) / 30.0 * 20.0  # 最多+20kg
            total_weight += rigidity_weight
        
        return total_weight
    
    @staticmethod
    def calculate_enhanced_cost(
        base_cost: float,
        rust_protection_level: str = "NONE",
        nvh_insulation_mass: float = 0.0,
        crumple_zone_length: float = 0.0,
        parts_bin_sharing_ratio: float = 0.5,
        manufacturing_complexity_score: float = 0.5
    ) -> float:
        """
        计算增强后的底盘成本（考虑新参数）
        
        Args:
            base_cost: 基础成本（来自calculate_biw_cost）
            rust_protection_level: 防锈保护级别
            nvh_insulation_mass: NVH隔音质量 (kg)
            crumple_zone_length: 溃缩区长度 (m)
            parts_bin_sharing_ratio: 零件库共享比例
            manufacturing_complexity_score: 制造复杂度评分
            
        Returns:
            总成本（游戏币）
        """
        total_cost = base_cost
        
        # 1. 防锈保护成本
        rust_cost = {
            "NONE": 0.0,
            "PARTIAL_GALVANIZED": 500.0,
            "FULL_DIP": 1500.0,
        }.get(rust_protection_level, 0.0)
        total_cost += rust_cost
        
        # 2. NVH隔音材料成本（每kg约$50）
        nvh_cost = nvh_insulation_mass * 50.0
        total_cost += nvh_cost
        
        # 3. 溃缩区结构成本（每米约$800）
        crumple_cost = crumple_zone_length * 800.0
        total_cost += crumple_cost
        
        # 4. 零件库共享影响（高共享 = 低R&D成本，但可能增加采购成本）
        # 定制零件：高R&D成本，低采购成本
        # 供应商零件：低R&D成本，高采购成本
        rnd_savings = (1.0 - parts_bin_sharing_ratio) * 2000.0  # 最多节省$2000
        procurement_cost = parts_bin_sharing_ratio * 500.0  # 最多增加$500采购成本
        total_cost = total_cost - rnd_savings + procurement_cost
        
        # 5. 制造复杂度影响（高复杂度 = 更高人工成本）
        complexity_multiplier = 1.0 + manufacturing_complexity_score * 0.3
        total_cost *= complexity_multiplier
        
        return max(0.0, total_cost)
    
    @staticmethod
    def calculate_engine_bay_volume_from_dimensions(
        engine_bay_length_mm: float,
        engine_bay_width_mm: float,
        engine_bay_height_mm: float
    ) -> int:
        """
        从尺寸计算引擎舱容积（升）
        
        Args:
            engine_bay_length_mm: 引擎舱长度 (mm)
            engine_bay_width_mm: 引擎舱宽度 (mm)
            engine_bay_height_mm: 引擎舱高度 (mm)
            
        Returns:
            引擎舱容积（升，整数）
        """
        volume_mm3 = engine_bay_length_mm * engine_bay_width_mm * engine_bay_height_mm
        volume_liters = volume_mm3 / 1_000_000
        return int(volume_liters)
    
    @staticmethod
    def calculate_platform_adaptation_cost(
        base_manufacturing_cost: float,
        actual_wheelbase_mm: int,
        base_wheelbase_mm: int,
        bandwidth_wheelbase_mm: int,
        actual_track_mm: int,
        base_track_mm: int,
        bandwidth_track_mm: int,
        is_bespoke: bool = False
    ) -> Tuple[float, float]:
        """
        计算平台适配成本
        
        如果车辆使用的轴距/轮距在平台带宽范围内，使用基础成本。
        如果超出带宽，需要支付适配成本（更高的单位成本 + 工程惩罚）。
        
        Bespoke底盘（非平台）严格固定，无带宽。
        
        Args:
            base_manufacturing_cost: 基础制造成本
            actual_wheelbase_mm: 实际使用的轴距
            base_wheelbase_mm: 平台基础轴距
            bandwidth_wheelbase_mm: 轴距带宽（±值）
            actual_track_mm: 实际使用的轮距（前后平均）
            base_track_mm: 平台基础轮距
            bandwidth_track_mm: 轮距带宽（±值）
            is_bespoke: 是否为定制底盘（无带宽）
            
        Returns:
            (单位成本, 工程惩罚系数)
            - 单位成本：可能高于基础成本
            - 工程惩罚系数：1.0 = 无惩罚，>1.0 = 有惩罚（影响研发时间）
        """
        if is_bespoke:
            # 定制底盘：严格固定，无带宽
            return base_manufacturing_cost, 1.0
        
        # 计算轴距偏差
        wheelbase_deviation = abs(actual_wheelbase_mm - base_wheelbase_mm)
        wheelbase_bandwidth_usage = wheelbase_deviation / bandwidth_wheelbase_mm if bandwidth_wheelbase_mm > 0 else 0.0
        
        # 计算轮距偏差
        track_deviation = abs(actual_track_mm - base_track_mm)
        track_bandwidth_usage = track_deviation / bandwidth_track_mm if bandwidth_track_mm > 0 else 0.0
        
        # 如果完全在带宽内，无额外成本
        if wheelbase_bandwidth_usage <= 1.0 and track_bandwidth_usage <= 1.0:
            return base_manufacturing_cost, 1.0
        
        # 超出带宽：计算适配成本
        # 使用最大偏差百分比
        max_deviation = max(wheelbase_bandwidth_usage, track_bandwidth_usage)
        
        # 适配成本：每超出10%带宽，增加5%单位成本
        # 例如：超出20% = +10%成本，超出100% = +50%成本
        cost_multiplier = 1.0 + (max_deviation - 1.0) * 0.5
        adapted_cost = base_manufacturing_cost * cost_multiplier
        
        # 工程惩罚：超出带宽需要额外工程时间
        # 每超出10%带宽，增加2%研发时间
        engineering_penalty = 1.0 + (max_deviation - 1.0) * 0.2
        
        return adapted_cost, engineering_penalty


# 导出
__all__ = ["ChassisCalculator", "BodyDimensions", "MaterialProperties", "MATERIALS"]

