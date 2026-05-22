"""
工程服务层 - 处理引擎、底盘、车辆配置的业务逻辑

提供高级API用于：
- 创建和计算引擎参数
- 创建底盘
- 组装车辆配置
- 兼容性检查
"""
from typing import Tuple, Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging

from backend.models.engineering import Engine, Chassis, CarTrim, ChassisSourceType
from backend.core.engineering.physics import EngineeringCalculator
from backend.core.engineering.chassis_math import (
    ChassisCalculator, BodyDimensions, MATERIALS
)

logger = logging.getLogger(__name__)


class EngineeringService:
    """工程服务 - 核心业务逻辑"""
    
    @staticmethod
    def create_engine_with_calculations(
        db: Session,
        game_id: int,
        company_id: Optional[int],
        name: str,
        code: str,
        bore_mm: float,
        stroke_mm: float,
        cylinder_count: int,
        configuration: str,
        compression_ratio: float,
        induction_type: str,
        boost_pressure_bar: float = 0.0,
        material: str = "ALUMINUM",
        valvetrain: str = "DOHC",
        fuel_type: str = "GASOLINE",
        tech_level: int = 5,
        development_cost: float = 0.0,
        is_proprietary: bool = False,
        manufacturing_tolerance: float = 0.5
    ) -> Engine:
        """
        创建引擎并自动计算所有派生参数
        
        这是创建引擎的推荐方法，确保所有物理参数一致性
        
        Args:
            db: 数据库会话
            game_id: 游戏ID
            company_id: 公司ID（None表示通用引擎）
            name: 引擎名称
            code: 唯一代码
            bore_mm: 缸径
            stroke_mm: 行程
            cylinder_count: 缸数
            configuration: 配置（INLINE/V/BOXER等）
            compression_ratio: 压缩比
            induction_type: 进气类型（NA/TURBO等）
            boost_pressure_bar: 增压压力
            material: 材料
            valvetrain: 配气机构
            fuel_type: 燃料类型
            tech_level: 技术等级
            development_cost: 研发成本
            is_proprietary: 是否专有
            
        Returns:
            创建并保存的Engine对象
        """
        logger.info(f"创建引擎: {name} ({code})")
        
        # ===== 第一步：计算基础物理参数 =====
        displacement_cc = EngineeringCalculator.calculate_displacement(
            bore_mm, stroke_mm, cylinder_count
        )
        logger.debug(f"排量: {displacement_cc} cc")
        
        # 计算尺寸
        length_mm, width_mm, height_mm = EngineeringCalculator.calculate_engine_dimensions(
            bore_mm, stroke_mm, cylinder_count, configuration, induction_type
        )
        logger.debug(f"尺寸: {length_mm} × {width_mm} × {height_mm} mm")
        
        # 计算重量
        weight_kg = EngineeringCalculator.calculate_engine_weight(
            displacement_cc, configuration, material, induction_type, tech_level
        )
        logger.debug(f"重量: {weight_kg} kg")
        
        # 计算红线转速（需要年份以限制tech_level）
        from backend.models.game_state import GameState
        game_state = db.query(GameState).filter(GameState.id == game_id).first()
        current_year = game_state.current_year if game_state else 1946
        
        max_safe_rpm, redline_rpm = EngineeringCalculator.calculate_redline_rpm(
            stroke_mm, material, configuration, tech_level, valvetrain, current_year
        )
        logger.debug(f"最大安全转速: {max_safe_rpm} RPM, 红线转速: {redline_rpm} RPM")
        
        # ===== 第二步：计算性能参数 =====
        # current_year已在上面获取
        
        max_horsepower, thermal_efficiency = EngineeringCalculator.calculate_horsepower(
            displacement_cc, compression_ratio, induction_type, boost_pressure_bar,
            valvetrain, fuel_type, tech_level, redline_rpm, current_year,
            max_safe_rpm=max_safe_rpm  # 传递MPS上限用于VE曲线计算
        )
        logger.debug(f"最大马力: {max_horsepower} HP, 热效率: {thermal_efficiency:.2%}")
        
        max_torque_nm = EngineeringCalculator.calculate_torque(
            displacement_cc, compression_ratio, induction_type, 
            boost_pressure_bar, fuel_type, tech_level, 
            current_year=current_year,
            valvetrain=valvetrain,
            redline_rpm=redline_rpm,
            max_safe_rpm=max_safe_rpm  # 传递MPS上限用于VE曲线计算
        )
        logger.debug(f"最大扭矩: {max_torque_nm} Nm")
        
        # 应用制造公差影响
        tolerance_impact = EngineeringCalculator.calculate_manufacturing_impact(manufacturing_tolerance)
        logger.debug(f"制造公差影响: {tolerance_impact}")
        
        # 应用性能加成
        max_horsepower = int(max_horsepower * (1.0 + tolerance_impact["performance_bonus"]))
        max_torque_nm = int(max_torque_nm * (1.0 + tolerance_impact["performance_bonus"]))
        
        # ===== 第三步：计算可靠性和效率 =====
        specific_output = max_horsepower / (displacement_cc / 1000.0)
        
        thermal_load = EngineeringCalculator.calculate_thermal_load(
            max_horsepower, displacement_cc, induction_type, 
            boost_pressure_bar, compression_ratio
        )
        logger.debug(f"热负载: {thermal_load}")
        
        reliability_base_score = EngineeringCalculator.calculate_reliability_score(
            specific_output, thermal_load, tech_level, material,
            compression_ratio=compression_ratio,
            current_year=current_year,
            fuel_type=fuel_type
        )
        # 应用制造公差可靠性加成
        reliability_base_score = reliability_base_score * (1.0 + tolerance_impact["reliability_bonus"])
        reliability_base_score = max(0.0, min(100.0, reliability_base_score))
        logger.debug(f"基础可靠性: {reliability_base_score} (含公差影响)")
        
        fuel_efficiency_rating, bsfc_g_kwh = EngineeringCalculator.calculate_fuel_efficiency(
            displacement_cc, max_horsepower, compression_ratio, 
            induction_type, fuel_type, tech_level
        )
        logger.debug(f"燃效评级: {fuel_efficiency_rating}, BSFC: {bsfc_g_kwh} g/kWh")
        
        # ===== 第四步：计算成本 =====
        manufacturing_cost = EngineeringCalculator.calculate_manufacturing_cost(
            displacement_cc, cylinder_count, configuration, material,
            induction_type, valvetrain, tech_level
        )
        # 应用制造公差成本影响
        manufacturing_cost = manufacturing_cost * tolerance_impact["unit_cost_multiplier"]
        logger.debug(f"制造成本: {manufacturing_cost} (含公差影响: {tolerance_impact['unit_cost_multiplier']:.2f}x)")
        
        # ===== 第五步：创建数据库对象 =====
        engine = Engine(
            game_id=game_id,
            company_id=company_id,
            name=name,
            code=code,
            # 输入参数
            bore_mm=bore_mm,
            stroke_mm=stroke_mm,
            cylinder_count=cylinder_count,
            configuration=configuration.upper(),
            compression_ratio=compression_ratio,
            induction_type=induction_type.upper(),
            boost_pressure_bar=boost_pressure_bar,
            material=material.upper(),
            valvetrain=valvetrain.upper(),
            fuel_type=fuel_type.upper(),
            tech_level=tech_level,
            # 计算得出的参数
            displacement_cc=displacement_cc,
            max_horsepower=max_horsepower,
            max_torque_nm=max_torque_nm,
            redline_rpm=redline_rpm,
            weight_kg=weight_kg,
            length_mm=length_mm,
            width_mm=width_mm,
            height_mm=height_mm,
            thermal_load=thermal_load,
            specific_output=specific_output,
            reliability_base_score=reliability_base_score,
            fuel_efficiency_rating=fuel_efficiency_rating,
            bsfc_g_kwh=bsfc_g_kwh,
            development_cost=development_cost,
            manufacturing_cost=manufacturing_cost,
            is_proprietary=is_proprietary,
            is_available=True
        )
        
        db.add(engine)
        db.commit()
        db.refresh(engine)
        
        # ===== 第六步：添加设计经验（熟悉度系统） =====
        if company_id:
            from backend.core.engineering.familiarity import FamiliaritySystem
            from backend.models.game_state import GameState
            
            # 获取当前回合
            game_state = db.query(GameState).filter(GameState.id == game_id).first()
            current_turn = game_state.turn_number if game_state else 0
            
            # 添加引擎设计经验
            FamiliaritySystem.add_design_experience(
                db, company_id, engine=engine, current_turn=current_turn, game_id=game_id
            )
        
        logger.info(f"引擎创建成功: {engine.code} - {engine.max_horsepower}HP @ {engine.redline_rpm}RPM")
        
        return engine
    
    @staticmethod
    def create_chassis(
        db: Session,
        game_id: int,
        company_id: Optional[int],
        name: str,
        code: str,
        wheelbase_mm: int,
        track_front_mm: int,
        track_rear_mm: int,
        layout: str,
        engine_bay_length_mm: float,
        engine_bay_width_mm: float,
        engine_bay_height_mm: float,
        max_cooling_capacity_kw: float,
        material: str = "STEEL",
        rigidity_rating: float = 50.0,
        crash_test_rating: float = 50.0,
        tech_level: int = 5,
        development_cost: float = 0.0,
        is_platform: bool = False,
        platform_family: Optional[str] = None,
        supported_body_styles: Optional[List[str]] = None,
        min_wheelbase_mm: Optional[int] = None,
        max_wheelbase_mm: Optional[int] = None,
        base_wheelbase_mm: Optional[int] = None,
        bandwidth_wheelbase_mm: Optional[int] = None,
        base_track_width_mm: Optional[int] = None,
        bandwidth_track_mm: Optional[int] = None,
        source_type: ChassisSourceType = ChassisSourceType.MODULAR_PLATFORM,
        original_competitor_id: Optional[int] = None,
        legal_risk_factor: float = 0.0,
        quality_cap: Optional[float] = None,
        # 新字段
        torsional_rigidity_target: Optional[int] = None,
        rust_protection_level: Optional[str] = None,
        nvh_insulation_mass: Optional[float] = None,
        engine_bay_volume: Optional[int] = None,
        transmission_tunnel_fitted: bool = False,
        crumple_zone_length: Optional[float] = None,
        fuel_tank_location: Optional[str] = None,
        manufacturing_complexity_score: Optional[float] = None,
        parts_bin_sharing_ratio: Optional[float] = None,
        designed_bumper_height: Optional[float] = None,
        overall_width_class: Optional[str] = None
    ) -> Chassis:
        """
        创建底盘
        
        Args:
            db: 数据库会话
            game_id: 游戏ID
            company_id: 公司ID
            name: 底盘名称
            code: 唯一代码
            wheelbase_mm: 轴距
            track_front_mm: 前轮距
            track_rear_mm: 后轮距
            layout: 驱动布局
            engine_bay_*: 引擎舱尺寸约束
            max_cooling_capacity_kw: 最大冷却容量
            material: 材料
            rigidity_rating: 刚性评分
            crash_test_rating: 碰撞测试评分
            tech_level: 技术等级
            development_cost: 研发成本
            
        Returns:
            创建的Chassis对象
        """
        logger.info(f"创建底盘: {name} ({code})")
        
        # 计算引擎舱容积（如果未提供）
        if engine_bay_volume is None:
            from backend.core.engineering.chassis_math import ChassisCalculator
            engine_bay_volume = ChassisCalculator.calculate_engine_bay_volume_from_dimensions(
                engine_bay_length_mm, engine_bay_width_mm, engine_bay_height_mm
            )
        
        # 计算制造复杂度（如果未提供）
        if manufacturing_complexity_score is None:
            from backend.core.engineering.chassis_math import ChassisCalculator
            manufacturing_complexity_score = ChassisCalculator.calculate_manufacturing_complexity(
                torsional_rigidity_target=torsional_rigidity_target or 50,
                rust_protection_level=rust_protection_level or "NONE",
                nvh_insulation_mass=nvh_insulation_mass or 0.0,
                crumple_zone_length=crumple_zone_length or 0.0,
                transmission_tunnel_fitted=transmission_tunnel_fitted,
                parts_bin_sharing_ratio=parts_bin_sharing_ratio or 0.5,
                material=material,
                tech_level=tech_level
            )
        
        # 计算底盘重量（基于轴距和材料，考虑新参数）
        # 简化公式：重量 ≈ 轴距 × 材料系数
        base_weight = wheelbase_mm / 10.0  # 基础重量
        
        material_factor = {
            "STEEL": 1.0,
            "ALUMINUM": 0.7,
            "CARBON": 0.5,
        }.get(material.upper(), 1.0)
        
        weight_kg = base_weight * material_factor
        
        # 应用新参数对重量的影响
        from backend.core.engineering.chassis_math import ChassisCalculator
        weight_kg = ChassisCalculator.calculate_enhanced_weight(
            base_weight_kg=weight_kg,
            nvh_insulation_mass=nvh_insulation_mass or 0.0,
            crumple_zone_length=crumple_zone_length or 0.0,
            rust_protection_level=rust_protection_level or "NONE",
            torsional_rigidity_target=torsional_rigidity_target or 50
        )
        
        # 计算制造成本
        base_cost = wheelbase_mm * 0.5  # 基础成本
        material_cost_factor = {
            "STEEL": 1.0,
            "ALUMINUM": 2.0,
            "CARBON": 5.0,
        }.get(material.upper(), 1.0)
        
        manufacturing_cost = base_cost * material_cost_factor * (1.0 + tech_level * 0.1)
        
        # 应用新参数对成本的影响
        manufacturing_cost = ChassisCalculator.calculate_enhanced_cost(
            base_cost=manufacturing_cost,
            rust_protection_level=rust_protection_level or "NONE",
            nvh_insulation_mass=nvh_insulation_mass or 0.0,
            crumple_zone_length=crumple_zone_length or 0.0,
            parts_bin_sharing_ratio=parts_bin_sharing_ratio or 0.5,
            manufacturing_complexity_score=manufacturing_complexity_score
        )
        
        logger.debug(f"底盘重量: {weight_kg} kg, 成本: {manufacturing_cost}")
        
        # 根据source_type调整制造成本（应用制造效率惩罚）
        if source_type == ChassisSourceType.BESPOKE:
            # 定制底盘：单位成本+20%（效率80%）
            manufacturing_cost *= 1.2
        elif source_type == ChassisSourceType.CLONED:
            # 克隆底盘：跳过工具开发，成本降低（效率120%）
            manufacturing_cost *= 0.9
        
        # 导入Enum类型
        from backend.models.engineering import RustProtectionLevel, FuelTankLocation, WidthClass
        
        # 转换Enum值
        rust_level = RustProtectionLevel(rust_protection_level.upper()) if rust_protection_level else RustProtectionLevel.NONE
        fuel_location = FuelTankLocation(fuel_tank_location.upper()) if fuel_tank_location else FuelTankLocation.REAR_AXLE_BEHIND
        width_class = WidthClass(overall_width_class.upper()) if overall_width_class else WidthClass.STANDARD
        
        chassis = Chassis(
            game_id=game_id,
            company_id=company_id,
            name=name,
            code=code,
            wheelbase_mm=wheelbase_mm,
            track_front_mm=track_front_mm,
            track_rear_mm=track_rear_mm,
            layout=layout.upper(),
            engine_bay_length_mm=engine_bay_length_mm,
            engine_bay_width_mm=engine_bay_width_mm,
            engine_bay_height_mm=engine_bay_height_mm,
            max_cooling_capacity_kw=max_cooling_capacity_kw,
            material=material.upper(),
            rigidity_rating=rigidity_rating,
            weight_kg=weight_kg,
            crash_test_rating=crash_test_rating,
            tech_level=tech_level,
            development_cost=development_cost,
            manufacturing_cost=manufacturing_cost,
            is_available=True,
            source_type=source_type,
            original_competitor_id=original_competitor_id,
            legal_risk_factor=legal_risk_factor,
            quality_cap=quality_cap,
            is_platform=is_platform,
            platform_family=platform_family,
            min_wheelbase_mm=min_wheelbase_mm,
            max_wheelbase_mm=max_wheelbase_mm,
            base_wheelbase_mm=base_wheelbase_mm,
            bandwidth_wheelbase_mm=bandwidth_wheelbase_mm,
            base_track_width_mm=base_track_width_mm,
            bandwidth_track_mm=bandwidth_track_mm,
            # 新字段
            torsional_rigidity_target=torsional_rigidity_target,
            rust_protection_level=rust_level,
            nvh_insulation_mass=nvh_insulation_mass,
            engine_bay_volume=engine_bay_volume,
            transmission_tunnel_fitted=transmission_tunnel_fitted,
            crumple_zone_length=crumple_zone_length,
            fuel_tank_location=fuel_location,
            manufacturing_complexity_score=manufacturing_complexity_score,
            parts_bin_sharing_ratio=parts_bin_sharing_ratio,
            designed_bumper_height=designed_bumper_height,
            overall_width_class=width_class
        )
        
        # 设置支持的车身类型
        if supported_body_styles:
            chassis.set_supported_body_styles(supported_body_styles)
        
        db.add(chassis)
        # 不在这里commit，让调用者控制事务（确保资金扣除等操作在同一事务中）
        db.flush()  # 刷新以获取chassis.id，但不提交
        db.refresh(chassis)
        
        # ===== 添加设计经验（熟悉度系统） =====
        if company_id:
            from backend.core.engineering.familiarity import FamiliaritySystem
            from backend.models.game_state import GameState
            
            # 获取当前回合
            game_state = db.query(GameState).filter(GameState.id == game_id).first()
            current_turn = game_state.turn_number if game_state else 0
            
            # 添加底盘设计经验
            FamiliaritySystem.add_design_experience(
                db, company_id, chassis=chassis, current_turn=current_turn, game_id=game_id
            )
        
        logger.info(f"底盘创建成功: {chassis.code}")
        
        return chassis
    
    @staticmethod
    def check_compatibility(
        db: Session,
        engine_id: int,
        chassis_id: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检查引擎与底盘的兼容性
        
        这是核心功能：确保物理约束得到满足
        
        Args:
            db: 数据库会话
            engine_id: 引擎ID
            chassis_id: 底盘ID
            
        Returns:
            (is_compatible, message, details)
            - is_compatible: 是否兼容
            - message: 兼容性消息
            - details: 详细信息字典
        """
        # 获取引擎和底盘
        engine = db.query(Engine).filter(Engine.id == engine_id).first()
        chassis = db.query(Chassis).filter(Chassis.id == chassis_id).first()
        
        if not engine:
            return (False, f"引擎ID {engine_id} 不存在", {})
        
        if not chassis:
            return (False, f"底盘ID {chassis_id} 不存在", {})
        
        logger.info(f"检查兼容性: 引擎 {engine.code} vs 底盘 {chassis.code}")
        
        # 使用物理计算器检查
        is_compatible, reason = EngineeringCalculator.check_engine_chassis_compatibility(
            engine_length=engine.length_mm,
            engine_width=engine.width_mm,
            engine_height=engine.height_mm,
            thermal_load=engine.thermal_load,
            bay_length=chassis.engine_bay_length_mm,
            bay_width=chassis.engine_bay_width_mm,
            bay_height=chassis.engine_bay_height_mm,
            cooling_capacity=chassis.max_cooling_capacity_kw
        )
        
        # 构建详细信息
        details = {
            "engine": {
                "code": engine.code,
                "name": engine.name,
                "dimensions_mm": {
                    "length": engine.length_mm,
                    "width": engine.width_mm,
                    "height": engine.height_mm
                },
                "thermal_load": engine.thermal_load,
                "power": engine.max_horsepower,
                "weight_kg": engine.weight_kg
            },
            "chassis": {
                "code": chassis.code,
                "name": chassis.name,
                "engine_bay_mm": {
                    "length": chassis.engine_bay_length_mm,
                    "width": chassis.engine_bay_width_mm,
                    "height": chassis.engine_bay_height_mm
                },
                "cooling_capacity_kw": chassis.max_cooling_capacity_kw,
                "layout": chassis.layout
            },
            "clearances": {
                "length_mm": chassis.engine_bay_length_mm - engine.length_mm,
                "width_mm": chassis.engine_bay_width_mm - engine.width_mm,
                "height_mm": chassis.engine_bay_height_mm - engine.height_mm,
                "cooling_margin_kw": chassis.max_cooling_capacity_kw - engine.thermal_load * 2.0
            }
        }
        
        logger.info(f"兼容性检查结果: {is_compatible} - {reason}")
        
        return (is_compatible, reason, details)
    
    @staticmethod
    def create_car_trim(
        db: Session,
        game_id: int,
        company_id: int,
        name: str,
        model_name: str,
        trim_code: str,
        engine_id: int,
        chassis_id: int,
        body_style: str,
        body_weight_kg: float,
        drag_coefficient: float = 0.30,
        frontal_area_sqm: float = 2.5,
        seating_capacity: int = 5,
        cargo_volume_liters: int = 400,
        segment: str = "MIDSIZE",
        msrp: float = 30000.0,
        tire_grip: float = 1.0
    ) -> Tuple[Optional[CarTrim], str]:
        """
        创建车辆配置（组装引擎+底盘+车身）
        
        自动检查兼容性并计算所有性能参数
        
        Args:
            db: 数据库会话
            game_id: 游戏ID
            company_id: 公司ID
            name: 配置名称
            model_name: 车型名称
            trim_code: 配置代码
            engine_id: 引擎ID
            chassis_id: 底盘ID
            body_style: 车身类型
            body_weight_kg: 车身重量
            drag_coefficient: 风阻系数
            frontal_area_sqm: 正面投影面积
            seating_capacity: 座位数
            cargo_volume_liters: 后备箱容积
            segment: 细分市场
            msrp: 建议零售价
            tire_grip: 轮胎抓地力系数
            
        Returns:
            (CarTrim对象或None, 消息)
        """
        logger.info(f"创建车辆配置: {name} ({trim_code})")
        
        # ===== 第一步：兼容性检查 =====
        is_compatible, compat_message, compat_details = EngineeringService.check_compatibility(
            db, engine_id, chassis_id
        )
        
        if not is_compatible:
            logger.warning(f"兼容性检查失败: {compat_message}")
            return (None, f"兼容性检查失败: {compat_message}")
        
        # 获取引擎和底盘对象
        engine = db.query(Engine).filter(Engine.id == engine_id).first()
        chassis = db.query(Chassis).filter(Chassis.id == chassis_id).first()
        
        # ===== 第二步：计算总重量 =====
        # 总重 = 引擎 + 底盘 + 车身 + 流体（燃油、机油、冷却液等，估算100kg）
        fluids_weight = 100.0
        total_weight_kg = engine.weight_kg + chassis.weight_kg + body_weight_kg + fluids_weight
        
        logger.debug(f"总重量: {total_weight_kg} kg (引擎{engine.weight_kg} + 底盘{chassis.weight_kg} + 车身{body_weight_kg} + 流体{fluids_weight})")
        
        # ===== 第三步：计算性能 =====
        performance = EngineeringCalculator.calculate_vehicle_performance(
            total_weight_kg=total_weight_kg,
            horsepower=engine.max_horsepower,
            torque_nm=engine.max_torque_nm,
            drag_coefficient=drag_coefficient,
            frontal_area_sqm=frontal_area_sqm,
            drivetrain=chassis.layout,
            tire_grip=tire_grip
        )
        
        logger.debug(f"性能: 0-100={performance.zero_to_hundred_kph_sec}s, 极速={performance.top_speed_kph}km/h")
        
        # ===== 第四步：计算推重比 =====
        power_to_weight_ratio = engine.max_horsepower / total_weight_kg
        
        # ===== 第五步：计算最终可靠性 =====
        # 综合考虑引擎可靠性、底盘质量、匹配度、熟悉度加成
        base_reliability = engine.reliability_base_score
        chassis_quality_bonus = (chassis.rigidity_rating - 50.0) * 0.1  # 刚性影响
        
        # 如果冷却接近极限，降低可靠性
        cooling_margin = compat_details["clearances"]["cooling_margin_kw"]
        if cooling_margin < 10:
            cooling_penalty = (10 - cooling_margin) * 2.0
        else:
            cooling_penalty = 0
        
        # 应用设计熟悉度加成
        design_familiarity_bonus = 0.0
        if company_id:
            from backend.core.engineering.familiarity import FamiliaritySystem
            
            # 获取引擎布局熟悉度加成
            engine_layout = FamiliaritySystem.get_layout_type(engine)
            engine_bonuses = FamiliaritySystem.get_familiarity_bonus(
                db, company_id, engine_layout, "ENGINE"
            )
            design_familiarity_bonus += base_reliability * engine_bonuses["reliability_bonus"]
            
            # 获取底盘布局熟悉度加成
            chassis_layout = FamiliaritySystem.get_chassis_layout_type(chassis)
            chassis_bonuses = FamiliaritySystem.get_familiarity_bonus(
                db, company_id, chassis_layout, "CHASSIS"
            )
            design_familiarity_bonus += base_reliability * chassis_bonuses["reliability_bonus"]
        
        final_reliability = (
            base_reliability + 
            chassis_quality_bonus - 
            cooling_penalty + 
            design_familiarity_bonus
        )
        final_reliability = max(0.0, min(100.0, final_reliability))
        
        logger.debug(f"最终可靠性: {final_reliability} (引擎{base_reliability} + 底盘{chassis_quality_bonus} - 冷却{cooling_penalty})")
        
        # ===== 第六步：计算制造成本 =====
        manufacturing_cost = engine.manufacturing_cost + chassis.manufacturing_cost + body_weight_kg * 5.0
        
        logger.debug(f"制造成本: {manufacturing_cost}")
        
        # ===== 第七步：创建CarTrim对象 =====
        car_trim = CarTrim(
            game_id=game_id,
            company_id=company_id,
            name=name,
            model_name=model_name,
            trim_code=trim_code,
            engine_id=engine_id,
            chassis_id=chassis_id,
            body_style=body_style.upper(),
            seating_capacity=seating_capacity,
            cargo_volume_liters=cargo_volume_liters,
            body_weight_kg=body_weight_kg,
            drag_coefficient=drag_coefficient,
            frontal_area_sqm=frontal_area_sqm,
            total_weight_kg=total_weight_kg,
            power_to_weight_ratio=power_to_weight_ratio,
            zero_to_hundred_kph_sec=performance.zero_to_hundred_kph_sec,
            top_speed_kph=performance.top_speed_kph,
            quarter_mile_sec=performance.quarter_mile_sec,
            braking_100_0_meters=performance.braking_100_0_meters,
            lateral_g_force=performance.lateral_g_force,
            fuel_economy_l_100km=performance.fuel_economy_l_100km,
            final_reliability_score=final_reliability,
            segment=segment.upper(),
            manufacturing_cost=manufacturing_cost,
            msrp=msrp,
            compatibility_status="COMPATIBLE",
            compatibility_notes=compat_message,
            is_in_production=False
        )
        
        db.add(car_trim)
        db.commit()
        db.refresh(car_trim)
        
        logger.info(f"车辆配置创建成功: {car_trim.trim_code} - {car_trim.power_to_weight_ratio:.2f}hp/kg, 0-100={car_trim.zero_to_hundred_kph_sec}s")
        
        return (car_trim, f"创建成功: {compat_message}")
    
    # ==================== Procedural Vehicle Body Creation ====================
    
    @staticmethod
    def create_procedural_body_chassis(
        db: Session,
        game_id: int,
        company_id: Optional[int],
        name: str,
        code: str,
        # Geometric Parameters
        wheelbase_mm: float,
        track_width_mm: float,
        front_overhang_mm: float,
        rear_overhang_mm: float,
        bonnet_height_mm: float,
        roof_height_mm: float,
        width_mm: float,
        # Material & Tech
        panel_material: str,  # "STEEL", "ALUMINUM", "CARBON", "HSS"
        body_style: str,      # "SEDAN", "SUV", etc.
        layout: str,          # "FF", "FR", "MR", "RR", "AWD"
        tech_level: int = 5,
        # Optional
        development_cost: float = 0.0,
        rigidity_rating: float = 60.0,
        crash_test_rating: float = 50.0
    ) -> Tuple[Chassis, Dict[str, Any]]:
        """
        创建程序化车身底盘（基于连续几何参数）
        
        这是新的车身创建方法，取代预设模板：
        - 输入：连续的几何参数（轴距、悬挂、高度等）
        - 输出：自动计算的重量、成本、空间约束
        
        Args:
            db: 数据库会话
            game_id: 游戏ID
            company_id: 公司ID
            name: 底盘名称
            code: 唯一代码
            wheelbase_mm: 轴距（毫米）
            track_width_mm: 轮距（毫米）
            front_overhang_mm: 前悬（毫米）
            rear_overhang_mm: 后悬（毫米）
            bonnet_height_mm: 引擎盖高度（毫米）
            roof_height_mm: 车顶高度（毫米）
            width_mm: 车身宽度（毫米）
            panel_material: 车身板材材料
            body_style: 车身类型
            layout: 驱动布局
            tech_level: 技术等级
            development_cost: 研发成本
            rigidity_rating: 刚性评分
            crash_test_rating: 碰撞测试评分
            
        Returns:
            (Chassis对象, 车身统计数据字典)
        """
        logger.info(f"创建程序化车身底盘: {name} ({code})")
        
        # 1. 构建几何参数
        dims = BodyDimensions(
            wheelbase_mm=wheelbase_mm,
            track_width_mm=track_width_mm,
            front_overhang_mm=front_overhang_mm,
            rear_overhang_mm=rear_overhang_mm,
            bonnet_height_mm=bonnet_height_mm,
            roof_height_mm=roof_height_mm,
            width_mm=width_mm
        )
        
        logger.debug(f"总长: {dims.total_length_mm:.0f} mm, 正面面积: {dims.frontal_area_sqm:.2f} m²")
        
        # 2. 计算车身统计数据
        try:
            body_stats = ChassisCalculator.calculate_body_stats(
                dims=dims,
                material=panel_material,
                body_style=body_style,
                layout=layout,
                tech_level=tech_level
            )
        except ValueError as e:
            logger.error(f"车身计算失败: {e}")
            raise
        
        logger.debug(f"白车身重量: {body_stats['biw_weight_kg']:.1f} kg, 成本: ${body_stats['biw_cost']:,.0f}")
        logger.debug(f"引擎舱容积: {body_stats['engine_bay_volume_liters']:.1f} L")
        logger.debug(f"风阻系数: {body_stats['drag_coefficient']:.3f}")
        
        # 3. 推算引擎舱尺寸约束
        # 从体积反推近似尺寸
        bay_volume_liters = body_stats["engine_bay_volume_liters"]
        avg_dimension_mm = (bay_volume_liters * 1_000_000) ** (1/3)
        
        if layout in ["FF", "FR"]:
            bay_length = avg_dimension_mm * 1.5
            bay_width = avg_dimension_mm * 0.9
            bay_height = avg_dimension_mm * 0.8
        elif layout == "MR":
            bay_length = avg_dimension_mm * 1.0
            bay_width = avg_dimension_mm * 0.9
            bay_height = avg_dimension_mm * 1.0
        else:  # RR
            bay_length = avg_dimension_mm * 1.3
            bay_width = avg_dimension_mm * 0.85
            bay_height = avg_dimension_mm * 0.7
        
        # 4. 估算冷却容量（基于引擎舱大小和前面积）
        max_cooling_capacity_kw = (dims.frontal_area_sqm * 50.0) + (tech_level * 5.0)
        
        # 5. 创建 Chassis 对象
        chassis = Chassis(
            game_id=game_id,
            company_id=company_id,
            name=name,
            code=code,
            # 尺寸
            wheelbase_mm=int(wheelbase_mm),
            track_front_mm=int(track_width_mm),
            track_rear_mm=int(track_width_mm),
            layout=layout.upper(),
            # 引擎舱约束
            engine_bay_length_mm=bay_length,
            engine_bay_width_mm=bay_width,
            engine_bay_height_mm=bay_height,
            max_cooling_capacity_kw=max_cooling_capacity_kw,
            # 材料与结构
            material=panel_material.upper(),
            rigidity_rating=rigidity_rating,
            weight_kg=body_stats["biw_weight_kg"] + 100.0,  # BIW + 悬挂/传动重量
            crash_test_rating=crash_test_rating,
            # 技术
            tech_level=tech_level,
            # 成本
            development_cost=development_cost,
            manufacturing_cost=body_stats["biw_cost"],
            # 平台共享（初始为独立）
            is_platform=True,
            platform_family=None,
            derived_from_chassis_id=None,
            models_using_count=0,
            economies_of_scale_factor=1.0,
            # 可用性
            is_available=True
        )
        
        db.add(chassis)
        db.commit()
        db.refresh(chassis)
        
        logger.info(
            f"✓ 程序化底盘创建成功: {chassis.code} | "
            f"L={dims.total_length_mm:.0f}mm, "
            f"Weight={chassis.weight_kg:.0f}kg, "
            f"Cd={body_stats['drag_coefficient']:.3f}, "
            f"Cost=${chassis.manufacturing_cost:,.0f}"
        )
        
        return chassis, body_stats
    
    @staticmethod
    def validate_engine_fits_procedural_body(
        engine: Engine,
        chassis: Chassis
    ) -> Tuple[bool, str]:
        """
        验证引擎是否适配程序化车身
        
        检查：
        - 引擎尺寸 vs 引擎舱空间
        - 引擎热负载 vs 冷却容量
        
        Args:
            engine: Engine对象
            chassis: Chassis对象（程序化创建）
            
        Returns:
            (是否兼容, 消息)
        """
        # 1. 尺寸检查（5%安装间隙）
        clearance = 1.05
        
        if engine.length_mm * clearance > chassis.engine_bay_length_mm:
            return False, (
                f"引擎太长：{engine.length_mm:.0f}mm 超出引擎舱 {chassis.engine_bay_length_mm:.0f}mm"
            )
        
        if engine.width_mm * clearance > chassis.engine_bay_width_mm:
            return False, (
                f"引擎太宽：{engine.width_mm:.0f}mm 超出引擎舱 {chassis.engine_bay_width_mm:.0f}mm"
            )
        
        if engine.height_mm * clearance > chassis.engine_bay_height_mm:
            return False, (
                f"引擎太高：{engine.height_mm:.0f}mm 超出引擎舱 {chassis.engine_bay_height_mm:.0f}mm"
            )
        
        # 2. 冷却容量检查
        required_cooling_kw = engine.thermal_load * 2.0  # 热负载转为冷却需求
        cooling_usage = required_cooling_kw / chassis.max_cooling_capacity_kw
        
        if cooling_usage > 1.0:
            return False, (
                f"冷却不足：引擎需要 {required_cooling_kw:.0f}kW，但底盘仅提供 {chassis.max_cooling_capacity_kw:.0f}kW"
            )
        
        # 3. 警告级别检查
        length_usage = engine.length_mm / chassis.engine_bay_length_mm
        width_usage = engine.width_mm / chassis.engine_bay_width_mm
        height_usage = engine.height_mm / chassis.engine_bay_height_mm
        
        if any(usage > 0.95 for usage in [length_usage, width_usage, height_usage]):
            return True, "⚠️ 警告：非常紧凑的安装，维护困难"
        
        if cooling_usage > 0.9:
            return True, f"⚠️ 警告：冷却容量接近极限（{cooling_usage*100:.0f}%使用率）"
        
        return True, "✓ 完全兼容"


__all__ = ["EngineeringService"]

