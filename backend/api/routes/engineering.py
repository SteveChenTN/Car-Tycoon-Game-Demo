"""
工程设计API路由
处理发动机、底盘、车辆设计等
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.core.dependencies import get_db_optional
from backend.models import GameState, Company, Engine, Chassis, CarTrim, CompanyTechnology, TechNode
from backend.services.engineering_service import EngineeringService
from backend.core.engineering.physics import EngineeringCalculator
from backend.core.economics.espionage import ReverseEngineeringService
from backend.logic.engineering_core import EngineeringCore, MATERIAL_GRADES, MANUFACTURING_PROCESSES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/engineering", tags=["Engineering"])


# ============================================================================
# Request Models
# ============================================================================

class EngineSimulationRequest(BaseModel):
    """发动机模拟请求（不保存）"""
    company_id: int
    bore_mm: float = Field(gt=50, lt=150)
    stroke_mm: float = Field(gt=50, lt=150)
    cylinder_count: int = Field(ge=2, le=16)
    configuration: str  # INLINE/V/BOXER/VR/W
    compression_ratio: float = Field(gt=6, lt=15)
    induction_type: str  # NA/TURBO/SUPERCHARGED/TWINTURBO
    boost_pressure_bar: float = Field(default=0, ge=0, le=3)
    material: str  # CAST_IRON/ALUMINUM/MAGNESIUM
    valvetrain: str  # OHV/SOHC/DOHC/VARIABLE
    fuel_type: str  # GASOLINE/DIESEL/E85/LPG
    tech_level: int = Field(ge=1, le=10)
    manufacturing_tolerance: float = Field(default=0.5, ge=0.0, le=1.0, 
                                          description="制造公差 (0.0=低成本快速, 1.0=高精度耗时)")
    redline_rpm: Optional[int] = Field(default=None, ge=2000, le=12000,
                                      description="用户设定的红线转速（可选，如果不提供则使用MPS计算的上限）")

    class Config:
        from_attributes = True


class EngineDesignRequest(BaseModel):
    """发动机设计请求（保存到数据库）"""
    company_id: int
    name: str
    code: str
    bore_mm: float = Field(gt=50, lt=150)
    stroke_mm: float = Field(gt=50, lt=150)
    cylinder_count: int = Field(ge=2, le=16)
    configuration: str  # INLINE/V/BOXER/VR/W
    compression_ratio: float = Field(gt=6, lt=15)
    induction_type: str  # NA/TURBO/SUPERCHARGED/TWINTURBO
    boost_pressure_bar: float = Field(default=0, ge=0, le=3)
    material: str  # CAST_IRON/ALUMINUM/MAGNESIUM
    valvetrain: str  # OHV/SOHC/DOHC/VARIABLE
    fuel_type: str  # GASOLINE/DIESEL/E85/LPG
    tech_level: int = Field(ge=1, le=10)
    manufacturing_tolerance: float = Field(default=0.5, ge=0.0, le=1.0,
                                          description="制造公差 (0.0=低成本快速, 1.0=高精度耗时)")

    class Config:
        from_attributes = True


class ChassisDesignRequest(BaseModel):
    """底盘设计请求"""
    company_id: int
    name: str
    code: str
    wheelbase_mm: int = Field(gt=1500, lt=4000)
    track_front_mm: int = Field(gt=1000, lt=2000)
    track_rear_mm: int = Field(gt=1000, lt=2000)
    layout: str  # FF/FR/MR/RR/AWD
    engine_bay_length_mm: float
    engine_bay_width_mm: float
    engine_bay_height_mm: float
    max_cooling_capacity_kw: float
    material: str  # STEEL/ALUMINUM/CARBON
    tech_level: int = Field(ge=1, le=10)
    
    # 底盘来源类型（R&D路径）
    source_type: str = "MODULAR_PLATFORM"  # MODULAR_PLATFORM / BESPOKE / CLONED
    
    # 逆向工程相关（仅CLONED类型）
    original_competitor_id: Optional[int] = None
    legal_risk_factor: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_cap: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    # 平台相关
    is_platform: bool = False
    platform_family: Optional[str] = None
    supported_body_styles: Optional[List[str]] = None
    min_wheelbase_mm: Optional[int] = None
    max_wheelbase_mm: Optional[int] = None
    
    # 平台带宽参数
    base_wheelbase_mm: Optional[int] = None
    bandwidth_wheelbase_mm: Optional[int] = None
    base_track_width_mm: Optional[int] = None
    bandwidth_track_mm: Optional[int] = None
    
    # ========== 物理结构组 (Group A) ==========
    torsional_rigidity_target: Optional[int] = Field(default=50, ge=1, le=100)
    rust_protection_level: Optional[str] = Field(default="NONE")  # NONE / PARTIAL_GALVANIZED / FULL_DIP
    nvh_insulation_mass: Optional[float] = Field(default=0.0, ge=0.0)
    
    # ========== 包装与安全组 (Group B & C) ==========
    engine_bay_volume: Optional[int] = None  # 将从engine_bay_*_mm计算
    transmission_tunnel_fitted: bool = Field(default=False)
    crumple_zone_length: Optional[float] = Field(default=0.0, ge=0.0)
    fuel_tank_location: Optional[str] = Field(default="REAR_AXLE_BEHIND")  # REAR_AXLE_BEHIND / UNDER_SEAT / MID_CENTRAL
    
    # ========== 制造与供应链组 (Group D & E) ==========
    manufacturing_complexity_score: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    parts_bin_sharing_ratio: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    
    # ========== 认证组 (Group F) ==========
    designed_bumper_height: Optional[float] = Field(default=None, ge=0.0)
    overall_width_class: Optional[str] = Field(default="STANDARD")  # K_CAR / STANDARD / WIDEBODY
    
    # ========== 研发成本（前端计算，可选，向后兼容）==========
    program_cost: Optional[float] = Field(default=None, ge=0.0, description="研发项目总成本（游戏币）")
    rd_weeks: Optional[int] = Field(default=None, ge=1, description="研发周期（周）")

    class Config:
        from_attributes = True


class CarTrimDesignRequest(BaseModel):
    """车辆设计请求"""
    company_id: int
    name: str
    model_name: str
    trim_code: str
    engine_id: int
    chassis_id: int
    body_style: str  # SEDAN/COUPE/SUV/etc
    body_weight_kg: float = Field(gt=200, lt=3000)
    drag_coefficient: float = Field(gt=0.2, lt=0.6)
    frontal_area_sqm: float = Field(gt=1.5, lt=5.0)
    seating_capacity: int = Field(ge=2, le=9)
    cargo_volume_liters: int = Field(ge=50, le=3000)
    segment: str  # SUBCOMPACT/COMPACT/MIDSIZE/FULLSIZE/LUXURY
    msrp: float = Field(gt=5000)

    class Config:
        from_attributes = True


# ============================================================================
# 发动机设计端点
# ============================================================================

@router.post("/engine/design", response_model=Dict[str, Any])
async def design_engine(
    request: EngineDesignRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    设计新发动机
    
    Args:
        request: 发动机设计参数
    
    Returns:
        设计结果，包括计算出的性能参数
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        # 验证公司存在
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 检查引擎代码是否已存在
        existing_engine = db.query(Engine).filter(
            Engine.code == request.code,
            Engine.game_id == game.id
        ).first()
        
        if existing_engine:
            raise HTTPException(
                status_code=400,
                detail=f"引擎代码 '{request.code}' 已存在。请使用不同的代码。"
            )
        
        # 验证技术等级（检查年份限制）
        max_allowed_tech_level = EngineeringCalculator.get_max_tech_level_for_year(game.current_year)
        effective_tech_level = min(request.tech_level, max_allowed_tech_level)
        if request.tech_level > max_allowed_tech_level:
            raise HTTPException(
                status_code=400,
                detail=f"技术等级 {request.tech_level} 超过 {game.current_year} 年的限制（最大 {max_allowed_tech_level}）"
            )
        
        # 验证压缩比限制
        max_cr = EngineeringCalculator.get_fuel_octane_limit(game.current_year, request.fuel_type)
        if request.compression_ratio > max_cr:
            raise HTTPException(
                status_code=400,
                detail=f"压缩比 {request.compression_ratio:.1f}:1 超过 {game.current_year} 年燃料限制（最大 ~{max_cr:.1f}:1）"
            )
        
        # 验证组件可用性
        # 验证材料
        is_valid, error_msg = EngineeringCalculator.validate_component_availability(
            'material', request.material, game.current_year, effective_tech_level
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 验证配气机构
        is_valid, error_msg = EngineeringCalculator.validate_component_availability(
            'valvetrain', request.valvetrain, game.current_year, effective_tech_level
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 验证进气方式
        is_valid, error_msg = EngineeringCalculator.validate_component_availability(
            'induction', request.induction_type, game.current_year, effective_tech_level
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 验证燃料（暂时不强制验证，因为燃料没有tech_level_required字段）
        # is_valid, error_msg = EngineeringCalculator.validate_component_availability(
        #     'fuel', request.fuel_type, game.current_year, effective_tech_level
        # )
        # if not is_valid:
        #     raise HTTPException(status_code=400, detail=error_msg)
        
        # 创建发动机
        engine = EngineeringService.create_engine_with_calculations(
            db=db,
            game_id=game.id,
            company_id=request.company_id,
            name=request.name,
            code=request.code,
            bore_mm=request.bore_mm,
            stroke_mm=request.stroke_mm,
            cylinder_count=request.cylinder_count,
            configuration=request.configuration,
            compression_ratio=request.compression_ratio,
            induction_type=request.induction_type,
            boost_pressure_bar=request.boost_pressure_bar,
            material=request.material,
            valvetrain=request.valvetrain,
            fuel_type=request.fuel_type,
            tech_level=request.tech_level,
            manufacturing_tolerance=getattr(request, 'manufacturing_tolerance', 0.5)
        )
        
        db.commit()
        db.refresh(engine)
        
        return {
            "success": True,
            "engine": {
                "id": engine.id,
                "name": engine.name,
                "code": engine.code,
                "displacement_cc": engine.displacement_cc,
                "horsepower": engine.max_horsepower,
                "torque_nm": engine.max_torque_nm,
                "weight_kg": engine.weight_kg,
                "dimensions": {
                    "length_mm": engine.length_mm,
                    "width_mm": engine.width_mm,
                    "height_mm": engine.height_mm
                },
                "reliability_score": engine.reliability_base_score,
                "thermal_load": engine.thermal_load,
                "manufacturing_cost": engine.manufacturing_cost
            },
            "warnings": []  # TODO: 添加警告逻辑
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"发动机设计失败: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engine/{engine_id}", response_model=Dict[str, Any])
async def get_engine(
    engine_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取发动机详情
    
    Args:
        engine_id: 发动机ID
    
    Returns:
        发动机完整信息
    """
    try:
        engine = db.query(Engine).filter(Engine.id == engine_id).first()
        if not engine:
            raise HTTPException(status_code=404, detail="发动机不存在")
        
        company = db.query(Company).filter(Company.id == engine.company_id).first()
        
        return {
            "success": True,
            "engine": {
                "id": engine.id,
                "name": engine.name,
                "code": engine.code,
                "company": company.name if company else "未知",
                "company_id": engine.company_id,
                "specifications": {
                    "displacement_cc": engine.displacement_cc,
                    "configuration": engine.configuration,
                    "cylinder_count": engine.cylinder_count,
                    "bore_mm": engine.bore_mm,
                    "stroke_mm": engine.stroke_mm,
                    "compression_ratio": engine.compression_ratio,
                    "induction": engine.induction_type,
                    "boost_bar": engine.boost_pressure_bar,
                    "material": engine.material,
                    "valvetrain": engine.valvetrain,
                    "fuel_type": engine.fuel_type
                },
                "performance": {
                    "max_horsepower": engine.max_horsepower,
                    "max_torque_nm": engine.max_torque_nm,
                    "redline_rpm": engine.redline_rpm,
                    "specific_output": engine.specific_output,
                    "bsfc_g_kwh": engine.bsfc_g_kwh
                },
                "physical": {
                    "weight_kg": engine.weight_kg,
                    "length_mm": engine.length_mm,
                    "width_mm": engine.width_mm,
                    "height_mm": engine.height_mm
                },
                "quality": {
                    "thermal_load": engine.thermal_load,
                    "reliability_score": engine.reliability_base_score,
                    "fuel_efficiency_rating": engine.fuel_efficiency_rating
                },
                "economics": {
                    "manufacturing_cost": engine.manufacturing_cost,
                    "development_cost": engine.development_cost,
                    "is_proprietary": engine.is_proprietary,
                    "is_available": engine.is_available
                },
                "tech_level": engine.tech_level
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取发动机失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engine/simulate", response_model=Dict[str, Any])
async def simulate_engine(
    request: EngineSimulationRequest,
    db: Optional[Session] = Depends(get_db_optional)
) -> Dict[str, Any]:
    """
    模拟引擎设计（不保存到数据库）
    
    用于实时预览引擎性能，返回扭矩/马力曲线和统计信息
    
    Args:
        request: 引擎设计参数
    
    Returns:
        模拟结果，包括动力曲线、统计信息
    """
    try:
        # 尝试获取游戏状态，如果没有则使用默认值
        current_year = 1946  # 默认年份
        game = None
        if db:
            game = db.query(GameState).first()
            if game:
                current_year = game.current_year
        
        # 计算基础参数
        displacement_cc = EngineeringCalculator.calculate_displacement(
            request.bore_mm, request.stroke_mm, request.cylinder_count
        )
        
        # 计算MPS限制的最大安全转速（作为上限）
        max_safe_rpm, calculated_redline_rpm = EngineeringCalculator.calculate_redline_rpm(
            request.stroke_mm, request.material, request.configuration, 
            request.tech_level, request.valvetrain, current_year
        )
        
        # 如果用户提供了redline_rpm，使用它（但不能超过MPS上限）
        if request.redline_rpm is not None:
            # 用户设定的redline不能超过MPS计算的上限
            redline_rpm = min(request.redline_rpm, max_safe_rpm)
        else:
            # 使用MPS计算的上限
            redline_rpm = calculated_redline_rpm
        
        max_torque_nm = EngineeringCalculator.calculate_torque(
            displacement_cc, request.compression_ratio, request.induction_type,
            request.boost_pressure_bar, request.fuel_type, request.tech_level, 
            current_year=current_year,
            valvetrain=request.valvetrain,
            redline_rpm=redline_rpm,
            max_safe_rpm=max_safe_rpm  # 传递MPS上限用于VE曲线计算
        )
        
        max_horsepower, thermal_efficiency = EngineeringCalculator.calculate_horsepower(
            displacement_cc, request.compression_ratio, request.induction_type,
            request.boost_pressure_bar, request.valvetrain, request.fuel_type,
            request.tech_level, redline_rpm, current_year,
            max_safe_rpm=max_safe_rpm  # 传递MPS上限用于VE曲线计算
        )
        
        # 生成动力曲线（传递current_year以应用热效率）
        power_curve = EngineeringCalculator.generate_power_curve(
            displacement_cc, request.compression_ratio, request.induction_type,
            request.boost_pressure_bar, request.valvetrain, request.fuel_type,
            request.tech_level, redline_rpm, max_torque_nm, max_horsepower, max_safe_rpm, current_year
        )
        
        # 计算其他统计信息
        dimensions = EngineeringCalculator.calculate_engine_dimensions(
            request.bore_mm, request.stroke_mm, request.cylinder_count,
            request.configuration, request.induction_type
        )
        
        weight_kg = EngineeringCalculator.calculate_engine_weight(
            displacement_cc, request.configuration, request.material,
            request.induction_type, request.tech_level
        )
        
        specific_output = max_horsepower / (displacement_cc / 1000.0)
        thermal_load = EngineeringCalculator.calculate_thermal_load(
            max_horsepower, displacement_cc, request.induction_type,
            request.boost_pressure_bar, request.compression_ratio
        )
        
        reliability_score = EngineeringCalculator.calculate_reliability_score(
            specific_output, thermal_load, request.tech_level, request.material,
            compression_ratio=request.compression_ratio,
            current_year=current_year,
            fuel_type=request.fuel_type
        )
        
        manufacturing_cost = EngineeringCalculator.calculate_manufacturing_cost(
            displacement_cc, request.cylinder_count, request.configuration,
            request.material, request.induction_type, request.valvetrain, request.tech_level
        )
        
        # 验证和警告
        warnings = []
        
        # 技术等级限制警告
        max_allowed_tech_level = EngineeringCalculator.get_max_tech_level_for_year(current_year)
        effective_tech_level = min(request.tech_level, max_allowed_tech_level)
        if request.tech_level > max_allowed_tech_level:
            warnings.append(
                f"警告：技术等级 {request.tech_level} 超过 {current_year} 年的限制（最大 {max_allowed_tech_level}）！"
                f"引擎将使用有效技术等级 {max_allowed_tech_level} 进行计算。"
            )
        
        # 组件可用性警告
        is_valid, error_msg = EngineeringCalculator.validate_component_availability(
            'material', request.material, current_year, effective_tech_level
        )
        if not is_valid:
            warnings.append(f"警告：{error_msg}")
        
        is_valid, error_msg = EngineeringCalculator.validate_component_availability(
            'valvetrain', request.valvetrain, current_year, effective_tech_level
        )
        if not is_valid:
            warnings.append(f"警告：{error_msg}")
        
        is_valid, error_msg = EngineeringCalculator.validate_component_availability(
            'induction', request.induction_type, current_year, effective_tech_level
        )
        if not is_valid:
            warnings.append(f"警告：{error_msg}")
        
        # 压缩比限制警告（使用新的函数）
        max_cr = EngineeringCalculator.get_fuel_octane_limit(current_year, request.fuel_type)
        if request.compression_ratio > max_cr:
            warnings.append(
                f"压缩比 {request.compression_ratio:.1f}:1 超过 {current_year}年燃料限制（最大 ~{max_cr:.1f}:1）！"
                f"可能导致爆震，大幅降低可靠性和效率。"
            )
        
        if thermal_load > 70:
            warnings.append(f"热负载过高 ({thermal_load:.1f})，可能影响可靠性。")
        if reliability_score < 40:
            warnings.append(f"可靠性评分过低 ({reliability_score:.1f})，建议调整参数。")
        
        return {
            "success": True,
            "torque_curve": [{"rpm": p["rpm"], "torque": p["torque"]} for p in power_curve],
            "hp_curve": [{"rpm": p["rpm"], "hp": p["power"]} for p in power_curve],
            "stats": {
                "displacement_cc": displacement_cc,
                "max_horsepower": max_horsepower,
                "max_torque_nm": max_torque_nm,
                "redline_rpm": redline_rpm,
                "max_safe_rpm": max_safe_rpm,
                "thermal_efficiency": thermal_efficiency,
                "weight_kg": weight_kg,
                "length_mm": dimensions[0],
                "width_mm": dimensions[1],
                "height_mm": dimensions[2],
                "reliability": reliability_score,
                "thermal_load": thermal_load,
                "cost": manufacturing_cost
            },
            "warnings": warnings
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"引擎模拟失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components/unlocked", response_model=Dict[str, Any])
async def get_unlocked_components(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取公司已解锁的引擎组件
    
    根据技术树解锁状态，返回可用的：
    - 燃料系统（Fuel Systems）
    - 材料（Materials）
    - 配气机构（Valvetrain）
    - 进气方式（Induction Types）
    - 配置（Configurations）
    
    Args:
        company_id: 公司ID
    
    Returns:
        解锁的组件列表
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 获取公司已完成的技术（使用关系加载技术节点）
        completed_techs = db.query(CompanyTechnology).filter(
            CompanyTechnology.company_id == company_id,
            CompanyTechnology.status == "COMPLETE"
        ).all()
        
        # 获取技术节点详情（通过关系）
        tech_nodes = [ct.tech_node for ct in completed_techs if ct.tech_node]
        
        # 基础可用组件（所有公司默认可用）
        unlocked = {
            "fuel_systems": ["GASOLINE"],  # 基础燃料
            "materials": ["CAST_IRON"],  # 基础材料
            "valvetrains": ["OHV"],  # 基础配气机构
            "induction_types": ["NA"],  # 基础进气方式
            "configurations": ["INLINE"],  # 基础配置
        }
        
        # 从技术树解锁的组件
        for tech_node in tech_nodes:
            unlocks_parts = tech_node.get_unlocks_parts()
            unlocks_features = tech_node.get_unlocks_features()
            
            # 解析解锁的组件
            for part in unlocks_parts:
                if part.startswith("FUEL_"):
                    fuel_type = part.replace("FUEL_", "")
                    if fuel_type not in unlocked["fuel_systems"]:
                        unlocked["fuel_systems"].append(fuel_type)
                elif part.startswith("MATERIAL_"):
                    material = part.replace("MATERIAL_", "")
                    if material not in unlocked["materials"]:
                        unlocked["materials"].append(material)
                elif part.startswith("VALVETRAIN_"):
                    valvetrain = part.replace("VALVETRAIN_", "")
                    if valvetrain not in unlocked["valvetrains"]:
                        unlocked["valvetrains"].append(valvetrain)
                elif part.startswith("INDUCTION_"):
                    induction = part.replace("INDUCTION_", "")
                    if induction not in unlocked["induction_types"]:
                        unlocked["induction_types"].append(induction)
                elif part.startswith("CONFIG_"):
                    config = part.replace("CONFIG_", "")
                    if config not in unlocked["configurations"]:
                        unlocked["configurations"].append(config)
            
            # 从特性解锁（备用方法）
            for feature in unlocks_features:
                if feature in ["EFI", "CARBURETOR"]:
                    # 这些是燃料系统特性，但不直接解锁新燃料类型
                    pass
                elif feature in ["TURBO", "SUPERCHARGER", "TWINTURBO"]:
                    if feature not in unlocked["induction_types"]:
                        unlocked["induction_types"].append(feature)
        
        # 根据当前年份添加历史可用组件
        current_year = game.current_year
        if current_year >= 1950:
            unlocked["materials"].append("ALUMINUM")
        if current_year >= 1960:
            unlocked["valvetrains"].append("SOHC")
        if current_year >= 1970:
            unlocked["valvetrains"].append("DOHC")
        if current_year >= 1980:
            unlocked["induction_types"].append("TURBO")
        if current_year >= 1990:
            unlocked["valvetrains"].append("VARIABLE")
        if current_year >= 2000:
            unlocked["materials"].append("MAGNESIUM")
            unlocked["induction_types"].append("TWINTURBO")
        
        # 去重并排序
        for key in unlocked:
            unlocked[key] = sorted(list(set(unlocked[key])))
        
        # 记录解锁的组件（调试用）
        logger.info(f"解锁的组件（去重后）: {unlocked}")
        
        # 查询组件熟悉度信息
        from backend.models.engineering_familiarity import EngineeringFamiliarity
        
        # 为每个组件添加熟悉度信息
        # 确保所有类别都被初始化，即使为空列表
        components_with_familiarity = {
            "fuel_systems": [],
            "materials": [],
            "valvetrains": [],
            "induction_types": [],
            "configurations": []
        }
        
        # 映射组件类型到布局类型前缀（用于查询熟悉度）
        component_to_layout_prefix = {
            "materials": "MATERIAL_",
            "valvetrains": "VALVETRAIN_",
            "fuel_systems": "FUEL_",
            "induction_types": "INDUCTION_",
            "configurations": "CONFIG_"
        }
        
        # 遍历所有解锁的组件，添加到 components_with_familiarity
        for category, component_list in unlocked.items():
            if category not in components_with_familiarity:
                logger.warning(f"未知的组件类别: {category}，跳过")
                continue
            
            if not component_list:
                logger.warning(f"类别 {category} 的组件列表为空，跳过")
                continue
            
            logger.info(f"处理类别 {category}: {len(component_list)} 个组件 - {component_list}")
            
            for component_value in component_list:
                if not component_value:
                    logger.warning(f"跳过空的组件值")
                    continue
                # 查询所有使用该组件的布局的熟悉度
                # 简化：查询所有ENGINE类别的熟悉度，然后根据布局类型匹配
                all_familiarities = db.query(EngineeringFamiliarity).filter(
                    EngineeringFamiliarity.company_id == company_id,
                    EngineeringFamiliarity.category == "ENGINE"
                ).all()
                
                # 查找包含该组件的布局
                matching_familiarities = []
                for fam in all_familiarities:
                    # 检查布局类型是否包含该组件
                    # 例如：V8_TURBO 包含 TURBO (induction_type)
                    if component_value in fam.layout_type:
                        matching_familiarities.append(fam)
                
                # 计算平均熟悉度（如果有匹配的）
                if matching_familiarities:
                    avg_level = sum(f.familiarity_level for f in matching_familiarities) / len(matching_familiarities)
                    avg_cost_reduction = sum(f.r_d_cost_reduction for f in matching_familiarities) / len(matching_familiarities)
                    avg_reliability_bonus = sum(f.reliability_bonus for f in matching_familiarities) / len(matching_familiarities)
                else:
                    # 默认值：无熟悉度
                    avg_level = 1
                    avg_cost_reduction = 0.0
                    avg_reliability_bonus = 0.0
                
                components_with_familiarity[category].append({
                    "value": component_value,
                    "familiarity_level": int(round(avg_level)),
                    "cost_modifier": round(-avg_cost_reduction, 4),  # 成本降低 = 负数修正
                    "reliability_modifier": round(avg_reliability_bonus, 4)
                })
        
        # 记录返回的数据结构（调试用）
        logger.info(f"返回解锁组件数据: 类别数量={len(components_with_familiarity)}, 当前年份={current_year}")
        for category, items in components_with_familiarity.items():
            logger.info(f"  {category}: {len(items)} 个组件")
            if items:
                logger.info(f"    组件列表: {[item.get('value', 'N/A') for item in items]}")
            else:
                logger.warning(f"    警告: {category} 类别为空！")
        
        return {
            "success": True,
            "components": components_with_familiarity,
            "current_year": current_year
        }
        
    except Exception as e:
        logger.error(f"获取解锁组件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 底盘时间门控端点
# ============================================================================

@router.get("/chassis/available-tabs", response_model=Dict[str, Any])
async def get_available_chassis_tabs(
    year: int = Query(..., description="游戏年份"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取指定年份可见的底盘设计标签页
    
    Args:
        year: 游戏年份
        
    Returns:
        可见标签页列表
    """
    try:
        from backend.logic.tech_gates import get_visible_chassis_tabs
        
        visible_tabs = get_visible_chassis_tabs(year)
        
        return {
            "success": True,
            "year": year,
            "visible_tabs": visible_tabs
        }
    except Exception as e:
        logger.error(f"获取可见标签页失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chassis/field-gating", response_model=Dict[str, Any])
async def get_chassis_field_gating(
    year: int = Query(..., description="游戏年份"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取所有底盘字段的门控信息
    
    Args:
        year: 游戏年份
        
    Returns:
        字段门控信息字典
    """
    try:
        from backend.logic.tech_gates import get_field_gating_info, get_rust_protection_options, get_fuel_tank_location_options
        
        gating_info = get_field_gating_info(year)
        rust_options = get_rust_protection_options(year)
        fuel_tank_options = get_fuel_tank_location_options(year)
        
        return {
            "success": True,
            "year": year,
            "field_gating": gating_info,
            "rust_protection_options": rust_options,
            "fuel_tank_location_options": fuel_tank_options
        }
    except Exception as e:
        logger.error(f"获取字段门控信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chassis/feedback", response_model=Dict[str, Any])
async def generate_chassis_feedback(
    chassis_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    生成测试车手反馈
    
    注意：此端点不需要游戏已加载，因为反馈生成是纯计算函数
    
    Args:
        chassis_data: 底盘参数字典
        
    Returns:
        包含评分和文本反馈的字典
    """
    try:
        from backend.core.engineering.chassis_feedback import generate_feedback_summary
        
        feedback = generate_feedback_summary(chassis_data)
        
        return {
            "success": True,
            "feedback": feedback
        }
    except Exception as e:
        logger.error(f"生成反馈失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 底盘设计端点
# ============================================================================

@router.post("/chassis/design", response_model=Dict[str, Any])
async def design_chassis(
    request: ChassisDesignRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    设计新底盘/平台
    
    Args:
        request: 底盘设计参数
    
    Returns:
        设计结果
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 检查底盘代码是否已存在
        existing_chassis = db.query(Chassis).filter(
            Chassis.code == request.code,
            Chassis.game_id == game.id
        ).first()
        
        if existing_chassis:
            raise HTTPException(
                status_code=400,
                detail=f"底盘代码 '{request.code}' 已存在。请使用不同的代码。"
            )
        
        # 根据source_type计算开发成本和周期
        from backend.models.engineering import ChassisSourceType
        
        source_type_enum = ChassisSourceType(request.source_type.upper())
        
        # 计算开发成本和周期（基于source_type）
        if source_type_enum == ChassisSourceType.MODULAR_PLATFORM:
            # 模块化平台：高R&D成本，长周期
            base_development_cost = 5_000_000.0
            development_weeks = 50
            is_platform = True
        elif source_type_enum == ChassisSourceType.BESPOKE:
            # 定制底盘：低R&D成本，短周期
            base_development_cost = 500_000.0
            development_weeks = 12
            is_platform = False
        elif source_type_enum == ChassisSourceType.CLONED:
            # 克隆底盘：几乎无R&D成本（逆向工程），但需要验证
            base_development_cost = 200_000.0
            development_weeks = 2  # 快速
            is_platform = False
        else:
            base_development_cost = 1_000_000.0
            development_weeks = 20
            is_platform = request.is_platform
        
        # 根据技术等级和材料调整成本
        tech_cost_multiplier = 1.0 + (request.tech_level - 1) * 0.1
        material_cost_multiplier = {
            "STEEL": 1.0,
            "ALUMINUM": 1.3,
            "CARBON": 2.0,
        }.get(request.material.upper(), 1.0)
        
        # 使用前端提供的成本数据（如果提供），否则使用后端计算的值（向后兼容）
        if request.program_cost is not None and request.rd_weeks is not None:
            from backend.logic.rd_manager import normalize_project_cost
            program_cost = normalize_project_cost(request.program_cost)
            rd_weeks = request.rd_weeks
        else:
            # 向后兼容：使用后端计算的值
            program_cost = base_development_cost * tech_cost_multiplier * material_cost_multiplier
            rd_weeks = development_weeks
        
        final_development_cost = program_cost
        
        # ========== 资金验证 ==========
        # 重新查询公司以确保获取最新数据（避免缓存问题）
        db.refresh(company)
        
        if company.cash < program_cost:
            raise HTTPException(
                status_code=402,
                detail=f"资金不足。需要 ${program_cost:,.0f}，当前资金 ${company.cash:,.0f}"
            )
        
        # 创建底盘（初始状态为开发中）
        chassis = EngineeringService.create_chassis(
            db=db,
            game_id=game.id,
            company_id=request.company_id,
            name=request.name,
            code=request.code,
            wheelbase_mm=request.wheelbase_mm,
            track_front_mm=request.track_front_mm,
            track_rear_mm=request.track_rear_mm,
            layout=request.layout,
            engine_bay_length_mm=request.engine_bay_length_mm,
            engine_bay_width_mm=request.engine_bay_width_mm,
            engine_bay_height_mm=request.engine_bay_height_mm,
            max_cooling_capacity_kw=request.max_cooling_capacity_kw,
            material=request.material,
            tech_level=request.tech_level,
            development_cost=final_development_cost,
            is_platform=is_platform,
            platform_family=request.platform_family,
            supported_body_styles=request.supported_body_styles,
            min_wheelbase_mm=request.min_wheelbase_mm,
            max_wheelbase_mm=request.max_wheelbase_mm,
            base_wheelbase_mm=request.base_wheelbase_mm,
            bandwidth_wheelbase_mm=request.bandwidth_wheelbase_mm,
            base_track_width_mm=request.base_track_width_mm,
            bandwidth_track_mm=request.bandwidth_track_mm,
            source_type=source_type_enum,
            original_competitor_id=request.original_competitor_id,
            legal_risk_factor=request.legal_risk_factor,
            quality_cap=request.quality_cap,
            # 新字段
            torsional_rigidity_target=request.torsional_rigidity_target,
            rust_protection_level=request.rust_protection_level,
            nvh_insulation_mass=request.nvh_insulation_mass,
            engine_bay_volume=request.engine_bay_volume,
            transmission_tunnel_fitted=request.transmission_tunnel_fitted,
            crumple_zone_length=request.crumple_zone_length,
            fuel_tank_location=request.fuel_tank_location,
            manufacturing_complexity_score=request.manufacturing_complexity_score,
            parts_bin_sharing_ratio=request.parts_bin_sharing_ratio,
            designed_bumper_height=request.designed_bumper_height,
            overall_width_class=request.overall_width_class
        )
        
        # 确保chassis.id可用
        db.flush()
        
        # 使用RDManager启动研发项目
        from backend.logic.rd_manager import RDManager, ProjectType
        
        rd_manager = RDManager(
            db=db,
            company_id=company.id,
            game_id=game.id
        )
        
        # 启动底盘研发项目
        success, message, research_project = rd_manager.start_project(
            project_type=ProjectType.CHASSIS,
            payload={"chassis_id": chassis.id},
            base_weeks=rd_weeks,
            base_cost=program_cost,
            current_turn=game.turn_number
        )
        
        if not success:
            db.rollback()
            raise HTTPException(status_code=400, detail=message)
        
        # 保存RDManager状态
        rd_manager.save_state()
        
        # 提交所有更改
        db.commit()
        
        # 刷新对象
        db.refresh(company)
        db.refresh(chassis)
        
        logger.info(
            f"✓ 底盘项目创建完成。最终资金余额: ${company.cash:,.0f} "
            f"(已扣除 ${program_cost:,.0f})"
        )
        
        # 生成测试车手反馈
        from backend.core.engineering.chassis_feedback import generate_feedback_summary
        
        chassis_data = {
            "torsional_rigidity_target": chassis.torsional_rigidity_target or 50,
            "rigidity_rating": chassis.rigidity_rating,
            "nvh_insulation_mass": chassis.nvh_insulation_mass or 0.0,
            "material": chassis.material,
            "crash_test_rating": chassis.crash_test_rating,
            "crumple_zone_length": chassis.crumple_zone_length or 0.0,
            "fuel_tank_location": chassis.fuel_tank_location.value if chassis.fuel_tank_location else "REAR_AXLE_BEHIND",
            "manufacturing_complexity_score": chassis.manufacturing_complexity_score or 0.5,
            "parts_bin_sharing_ratio": chassis.parts_bin_sharing_ratio or 0.5,
        }
        
        feedback = generate_feedback_summary(chassis_data)
        
        return {
            "success": True,
            "chassis": {
                "id": chassis.id,
                "name": chassis.name,
                "code": chassis.code,
                "wheelbase_mm": chassis.wheelbase_mm,
                "layout": chassis.layout,
                "material": chassis.material,
                "weight_kg": chassis.weight_kg,
                "rigidity_rating": chassis.rigidity_rating,
                "crash_test_rating": chassis.crash_test_rating,
                "manufacturing_cost": chassis.manufacturing_cost,
                "is_platform": chassis.is_platform,
                "platform_family": chassis.platform_family,
                "source_type": chassis.source_type.value if chassis.source_type else "MODULAR_PLATFORM",
                "development_cost": chassis.development_cost,
                "development_weeks": rd_weeks,
                "reusability": chassis.get_reusability(),
                "manufacturing_efficiency": chassis.get_manufacturing_efficiency(),
                # 新字段
                "torsional_rigidity_target": chassis.torsional_rigidity_target,
                "rust_protection_level": chassis.rust_protection_level.value if chassis.rust_protection_level else "NONE",
                "nvh_insulation_mass": chassis.nvh_insulation_mass,
                "engine_bay_volume": chassis.engine_bay_volume,
                "transmission_tunnel_fitted": chassis.transmission_tunnel_fitted,
                "crumple_zone_length": chassis.crumple_zone_length,
                "fuel_tank_location": chassis.fuel_tank_location.value if chassis.fuel_tank_location else "REAR_AXLE_BEHIND",
                "manufacturing_complexity_score": chassis.manufacturing_complexity_score,
                "parts_bin_sharing_ratio": chassis.parts_bin_sharing_ratio,
                "designed_bumper_height": chassis.designed_bumper_height,
                "overall_width_class": chassis.overall_width_class.value if chassis.overall_width_class else "STANDARD",
            },
            "research_project": {
                "id": research_project.id,
                "type": research_project.type.value,
                "status": research_project.status.value,
                "progress": research_project.progress,
                "target_weeks": research_project.target_weeks,
                "budget_allocated": research_project.budget_allocated,
                "start_turn": research_project.start_turn,
            },
            "company_funds_remaining": company.cash,
            "feedback": feedback
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"底盘设计失败: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 车辆设计端点
# ============================================================================

@router.post("/car/design", response_model=Dict[str, Any])
async def design_car(
    request: CarTrimDesignRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    设计新车辆
    
    组合发动机和底盘，进行兼容性检查，计算性能参数
    
    Args:
        request: 车辆设计参数
    
    Returns:
        设计结果，包括性能计算和兼容性检查
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 检查车辆代码（trim_code）是否已存在
        existing_car = db.query(CarTrim).filter(
            CarTrim.trim_code == request.trim_code,
            CarTrim.game_id == game.id
        ).first()
        
        if existing_car:
            raise HTTPException(
                status_code=400,
                detail=f"车辆代码 '{request.trim_code}' 已存在。请使用不同的代码。"
            )
        
        # 验证发动机和底盘存在
        engine = db.query(Engine).filter(Engine.id == request.engine_id).first()
        chassis = db.query(Chassis).filter(Chassis.id == request.chassis_id).first()
        
        if not engine:
            raise HTTPException(status_code=404, detail="发动机不存在")
        if not chassis:
            raise HTTPException(status_code=404, detail="底盘不存在")
        
        # 检查兼容性
        is_compatible, message, details = EngineeringService.check_compatibility(
            db=db,
            engine_id=request.engine_id,
            chassis_id=request.chassis_id
        )
        
        if not is_compatible:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INCOMPATIBLE",
                    "message": message,
                    "details": details
                }
            )
        
        # 创建车辆
        car_trim, creation_message = EngineeringService.create_car_trim(
            db=db,
            game_id=game.id,
            company_id=request.company_id,
            name=request.name,
            model_name=request.model_name,
            trim_code=request.trim_code,
            engine_id=request.engine_id,
            chassis_id=request.chassis_id,
            body_style=request.body_style,
            body_weight_kg=request.body_weight_kg,
            drag_coefficient=request.drag_coefficient,
            frontal_area_sqm=request.frontal_area_sqm,
            seating_capacity=request.seating_capacity,
            cargo_volume_liters=request.cargo_volume_liters,
            segment=request.segment,
            msrp=request.msrp
        )
        
        db.commit()
        db.refresh(car_trim)
        
        return {
            "success": True,
            "car": {
                "id": car_trim.id,
                "name": car_trim.name,
                "model_name": car_trim.model_name,
                "trim_code": car_trim.trim_code,
                "body_style": car_trim.body_style,
                "segment": car_trim.segment,
                "performance": {
                    "zero_to_hundred_kph_sec": car_trim.zero_to_hundred_kph_sec,
                    "top_speed_kph": car_trim.top_speed_kph,
                    "quarter_mile_sec": car_trim.quarter_mile_sec,
                    "fuel_economy_l_100km": car_trim.fuel_economy_l_100km,
                    "power_to_weight_ratio": car_trim.power_to_weight_ratio
                },
                "weight": {
                    "total_kg": car_trim.total_weight_kg,
                    "engine_kg": engine.weight_kg,
                    "chassis_kg": chassis.weight_kg,
                    "body_kg": car_trim.body_weight_kg
                },
                "reliability_score": car_trim.final_reliability_score,
                "manufacturing_cost": car_trim.manufacturing_cost,
                "msrp": car_trim.msrp,
                "compatibility": {
                    "status": car_trim.compatibility_status,
                    "notes": car_trim.compatibility_notes
                }
            },
            "message": creation_message,
            "warnings": details.get("warnings", []) if details else []
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"车辆设计失败: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compatibility/check", response_model=Dict[str, Any])
async def check_compatibility(
    engine_id: int,
    chassis_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    检查发动机和底盘的兼容性
    
    Args:
        engine_id: 发动机ID
        chassis_id: 底盘ID
    
    Returns:
        兼容性检查结果
    """
    try:
        is_compatible, message, details = EngineeringService.check_compatibility(
            db=db,
            engine_id=engine_id,
            chassis_id=chassis_id
        )
        
        return {
            "compatible": is_compatible,
            "message": message,
            "details": details
        }
        
    except Exception as e:
        logger.error(f"兼容性检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 列表端点
# ============================================================================

@router.get("/engines", response_model=List[Dict[str, Any]])
async def list_engines(
    company_id: Optional[int] = None,
    available_only: bool = False,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    列出发动机
    
    Args:
        company_id: 筛选特定公司
        available_only: 仅显示可用的
    
    Returns:
        发动机列表
    """
    try:
        query = db.query(Engine)
        
        if company_id:
            query = query.filter(Engine.company_id == company_id)
        
        if available_only:
            query = query.filter(Engine.is_available == True)
        
        engines = query.all()
        
        return [
            {
                "id": e.id,
                "name": e.name,
                "code": e.code,
                "displacement_cc": e.displacement_cc,
                "horsepower": e.max_horsepower,
                "torque_nm": e.max_torque_nm,
                "configuration": e.configuration,
                "cylinder_count": e.cylinder_count,
                "reliability_score": e.reliability_base_score,
                "cost": e.manufacturing_cost
            }
            for e in engines
        ]
        
    except Exception as e:
        logger.error(f"列出发动机失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chassis", response_model=List[Dict[str, Any]])
async def list_chassis(
    company_id: Optional[int] = None,
    available_only: bool = True,  # 默认只返回可用的底盘（开发中的平台不可用）
    source_type: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    列出底盘
    
    Args:
        company_id: 筛选特定公司
        available_only: 仅显示可用的（默认True，过滤掉开发中的平台）
        source_type: 筛选底盘来源类型（MODULAR_PLATFORM/BESPOKE/CLONED）
    
    Returns:
        底盘列表
    """
    try:
        from backend.models.engineering import ChassisSourceType
        
        query = db.query(Chassis)
        
        if company_id:
            query = query.filter(Chassis.company_id == company_id)
        
        # 默认只返回可用的底盘（开发中的平台不可用）
        if available_only:
            query = query.filter(Chassis.is_available == True)
        
        if source_type:
            try:
                source_type_enum = ChassisSourceType(source_type.upper())
                query = query.filter(Chassis.source_type == source_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的source_type: {source_type}。必须是: MODULAR_PLATFORM, BESPOKE, CLONED"
                )
        
        chassis_list = query.all()
        
        return [
            {
                "id": c.id,
                "name": c.name,
                "code": c.code,
                "wheelbase_mm": c.wheelbase_mm,
                "layout": c.layout,
                "material": c.material,
                "is_platform": c.is_platform,
                "platform_family": c.platform_family,
                "cost": c.manufacturing_cost,
                "source_type": c.source_type.value if c.source_type else "MODULAR_PLATFORM",
                "is_available": c.is_available,
                "development_turn": c.development_turn,
                "reusability": c.get_reusability(),
                "legal_risk_factor": c.legal_risk_factor if c.source_type == ChassisSourceType.CLONED else None,
                "quality_cap": c.quality_cap if c.source_type == ChassisSourceType.CLONED else None,
                "original_competitor_id": c.original_competitor_id if c.source_type == ChassisSourceType.CLONED else None,
                "manufacturing_efficiency": c.get_manufacturing_efficiency(),
                "reliability_penalty": c.get_reliability_penalty()
            }
            for c in chassis_list
        ]
        
    except Exception as e:
        logger.error(f"列出底盘失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 研发项目查询端点
# ============================================================================

@router.get("/research-projects", response_model=List[Dict[str, Any]])
async def list_research_projects(
    company_id: Optional[int] = Query(None, description="公司ID筛选"),
    game_id: Optional[int] = Query(None, description="游戏ID"),
    db: Session = Depends(get_db_optional)
) -> List[Dict[str, Any]]:
    """
    列出研发项目（使用RDManager）
    
    Args:
        company_id: 筛选特定公司（可选）
        game_id: 游戏ID（可选，如果不提供则从当前游戏获取）
        db: 数据库会话
        
    Returns:
        研发项目列表
    """
    try:
        if db is None:
            return []
        
        # 获取游戏ID
        if not game_id:
            game = db.query(GameState).first()
            if not game:
                return []
            game_id = game.id
        
        from backend.logic.rd_manager import RDManager
        from backend.models.company import Company
        
        result = []
        
        # 获取所有公司或指定公司
        if company_id:
            companies = [db.query(Company).filter(Company.id == company_id).first()]
        else:
            companies = db.query(Company).filter(Company.game_id == game_id).all()
        
        for company in companies:
            if not company:
                continue
            
            # 加载RDManager
            rd_manager = RDManager(
                db=db,
                company_id=company.id,
                game_id=game_id
            )
            
            # 获取所有活跃项目
            projects = rd_manager.get_active_projects()
            
            for project in projects:
                # 根据项目类型获取相关信息
                project_info = {
                    "id": project.id,
                    "type": project.type.value,
                    "status": project.status.value,
                    "company_id": project.company_id,
                    "company_name": company.name,
                    "progress": project.progress,
                    "target_weeks": project.target_weeks,
                    "progress_percent": round((project.progress / project.target_weeks * 100) if project.target_weeks > 0 else 0, 1),
                    "budget_allocated": project.budget_allocated,
                    "start_turn": project.start_turn,
                    "completion_turn": project.completion_turn,
                    "is_completed": project.status.value == "COMPLETED",
                }
                
                # 根据项目类型添加特定信息
                if project.type.value == "CHASSIS":
                    chassis_id = project.payload.get("chassis_id")
                    if chassis_id:
                        chassis = db.query(Chassis).filter(Chassis.id == chassis_id).first()
                        if chassis:
                            project_info["chassis_id"] = chassis_id
                            project_info["chassis_name"] = chassis.name
                            project_info["chassis_code"] = chassis.code
                
                result.append(project_info)
        
        # 按start_turn降序排序
        result.sort(key=lambda x: x.get("start_turn", 0), reverse=True)
        
        return result
        
    except Exception as e:
        logger.error(f"列出研发项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research-projects/{project_id}", response_model=Dict[str, Any])
async def get_research_project(
    project_id: str,  # 改为字符串（UUID）
    db: Session = Depends(get_db_optional)
) -> Dict[str, Any]:
    """
    获取单个研发项目详情（使用RDManager）
    
    Args:
        project_id: 研发项目ID（UUID字符串）
        db: 数据库会话
        
    Returns:
        研发项目详情
    """
    try:
        if db is None:
            raise HTTPException(status_code=404, detail="游戏未加载")
        
        from backend.logic.rd_manager import RDManager
        from backend.models.company import Company
        
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        # 在所有公司中查找项目
        companies = db.query(Company).filter(Company.game_id == game.id).all()
        
        for company in companies:
            rd_manager = RDManager(
                db=db,
                company_id=company.id,
                game_id=game.id
            )
            
            # 在所有部门中查找项目
            for dept_type, dept in rd_manager.departments.items():
                for project in dept.active_projects:
                    if project.id == project_id:
                        # 找到项目，构建返回信息
                        project_info = {
                            "id": project.id,
                            "type": project.type.value,
                            "status": project.status.value,
                            "company_id": project.company_id,
                            "company_name": company.name,
                            "progress": project.progress,
                            "target_weeks": project.target_weeks,
                            "progress_percent": round((project.progress / project.target_weeks * 100) if project.target_weeks > 0 else 0, 1),
                            "budget_allocated": project.budget_allocated,
                            "start_turn": project.start_turn,
                            "completion_turn": project.completion_turn,
                            "is_completed": project.status.value == "COMPLETED",
                            "department": dept_type.value,
                        }
                        
                        # 根据项目类型添加特定信息
                        if project.type.value == "CHASSIS":
                            chassis_id = project.payload.get("chassis_id")
                            if chassis_id:
                                chassis = db.query(Chassis).filter(Chassis.id == chassis_id).first()
                                if chassis:
                                    project_info["chassis_id"] = chassis_id
                                    project_info["chassis_name"] = chassis.name
                                    project_info["chassis_code"] = chassis.code
                        
                        return project_info
        
        raise HTTPException(status_code=404, detail="研发项目不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取研发项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
        completed_weeks = total_weeks - project.remaining_weeks
        progress_percent = (completed_weeks / total_weeks * 100) if total_weeks > 0 else 0
        weeks_elapsed = current_turn - project.start_turn
        
        return {
            "id": project.id,
            "chassis": {
                "id": chassis.id,
                "name": chassis.name,
                "code": chassis.code,
                "is_available": chassis.is_available
            },
            "company": {
                "id": project.company_id,
                "name": company.name if company else f"公司{project.company_id}"
            },
            "progress": {
                "remaining_weeks": project.remaining_weeks,
                "total_weeks": total_weeks,
                "completed_weeks": completed_weeks,
                "progress_percent": round(progress_percent, 1),
                "weeks_elapsed": weeks_elapsed
            },
            "cost": {
                "total_cost": project.total_cost,
                "cost_per_week": project.total_cost / total_weeks if total_weeks > 0 else 0
            },
            "status": {
                "is_paused": project.is_paused,
                "is_completed": project.actual_completion_turn is not None
            },
            "timeline": {
                "start_turn": project.start_turn,
                "estimated_completion_turn": project.estimated_completion_turn,
                "actual_completion_turn": project.actual_completion_turn,
                "current_turn": current_turn
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取研发项目详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cars", response_model=List[Dict[str, Any]])
async def list_cars(
    company_id: Optional[int] = None,
    in_production: bool = False,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    列出车辆
    
    Args:
        company_id: 筛选特定公司
        in_production: 仅显示在产车型
    
    Returns:
        车辆列表
    """
    try:
        query = db.query(CarTrim)
        
        if company_id:
            query = query.filter(CarTrim.company_id == company_id)
        
        if in_production:
            query = query.filter(CarTrim.is_in_production == True)
        
        cars = query.all()
        
        return [
            {
                "id": car.id,
                "model_name": car.model_name,
                "name": car.name,
                "trim_code": car.trim_code,
                "body_style": car.body_style,
                "segment": car.segment,
                "horsepower": car.engine.max_horsepower if car.engine else 0,
                "zero_to_hundred": car.zero_to_hundred_kph_sec,
                "reliability": car.final_reliability_score,
                "msrp": car.msrp,
                "in_production": car.is_in_production
            }
            for car in cars
        ]
        
    except Exception as e:
        logger.error(f"列出车辆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/designs/available", response_model=Dict[str, Any])
async def get_available_designs(
    company_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取可用的车辆设计列表（用于生产分配）
    
    Args:
        company_id: 公司ID
    
    Returns:
        可用设计列表
    """
    try:
        # 获取该公司的所有车辆设计
        # 注意：CarTrim 没有 is_available 字段，只有 is_in_production
        # 这里返回所有设计，不管是否在生产中
        cars = db.query(CarTrim).filter(
            CarTrim.company_id == company_id
        ).all()
        
        designs = [
            {
                "id": car.id,
                "name": car.name,
                "model_name": car.model_name,
                "trim_code": car.trim_code,
                "body_style": car.body_style,
                "segment": car.segment,
                "msrp": car.msrp,
                "manufacturing_cost": car.manufacturing_cost or 0,
                "in_production": car.is_in_production
            }
            for car in cars
        ]
        
        return {
            "success": True,
            "designs": designs
        }
        
    except Exception as e:
        logger.error(f"获取可用设计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 逆向工程端点
# ============================================================================

class ReverseEngineeringRequest(BaseModel):
    """逆向工程请求"""
    company_id: int
    target_car_id: int  # 竞争对手的CarTrim ID
    investment_multiplier: float = Field(default=1.0, ge=0.5, le=3.0,
                                         description="投资倍数，影响精度和风险")

    class Config:
        from_attributes = True


@router.post("/reverse-engineer", response_model=Dict[str, Any])
async def reverse_engineer_car(
    request: ReverseEngineeringRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    逆向工程竞争对手车辆
    
    功能：
    - 生成情报报告
    - 创建克隆底盘（source_type=CLONED）
    - 解锁相关技术节点
    
    Args:
        request: 逆向工程请求参数
    
    Returns:
        逆向工程结果，包括生成的克隆底盘ID和技术解锁列表
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        # 验证目标车辆存在且不是自己的
        target_car = db.query(CarTrim).filter(
            CarTrim.id == request.target_car_id,
            CarTrim.game_id == game.id
        ).first()
        
        if not target_car:
            raise HTTPException(status_code=404, detail="目标车辆不存在")
        
        if target_car.company_id == request.company_id:
            raise HTTPException(
                status_code=400,
                detail="不能逆向工程自己的车辆"
            )
        
        # 执行逆向工程
        reverse_service = ReverseEngineeringService(db)
        result = reverse_service.reverse_engineer_car(
            company_id=request.company_id,
            target_car_id=request.target_car_id,
            game_id=game.id,
            current_turn=game.current_turn,
            investment_multiplier=request.investment_multiplier
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.message
            )
        
        # 获取克隆底盘信息（如果创建成功）
        cloned_chassis_info = None
        if result.cloned_chassis_id:
            cloned_chassis = db.query(Chassis).filter(
                Chassis.id == result.cloned_chassis_id
            ).first()
            if cloned_chassis:
                cloned_chassis_info = {
                    "id": cloned_chassis.id,
                    "name": cloned_chassis.name,
                    "code": cloned_chassis.code,
                    "source_type": cloned_chassis.source_type.value,
                    "quality_cap": cloned_chassis.quality_cap,
                    "legal_risk_factor": cloned_chassis.legal_risk_factor,
                    "manufacturing_efficiency": cloned_chassis.get_manufacturing_efficiency(),
                    "reliability_penalty": cloned_chassis.get_reliability_penalty()
                }
        
        return {
            "success": True,
            "intelligence_report_id": result.intelligence_report_id,
            "cloned_chassis": cloned_chassis_info,
            "unlocked_tech_ids": result.unlocked_tech_ids,
            "cost": result.cost,
            "time_turns": result.time_turns,
            "revealed_data": result.revealed_data,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"逆向工程失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 研发项目启动API（统一处理三种路径）
# ============================================================================

class ResearchProjectRequest(BaseModel):
    """研发项目启动请求"""
    company_id: int
    project_type: str  # "MODULAR_PLATFORM", "BESPOKE_CHASSIS", "REVERSE_ENGINEER"
    
    # 模块化平台参数
    platform_name: Optional[str] = None
    platform_code: Optional[str] = None
    supported_body_styles: Optional[List[str]] = None
    min_wheelbase_mm: Optional[int] = None
    max_wheelbase_mm: Optional[int] = None
    
    # 定制底盘参数
    chassis_name: Optional[str] = None
    chassis_code: Optional[str] = None
    wheelbase_mm: Optional[int] = None
    layout: Optional[str] = None
    
    # 逆向工程参数
    target_car_id: Optional[int] = None
    investment_multiplier: Optional[float] = None
    
    # 通用参数
    material: str = "STEEL"
    tech_level: int = 5

    class Config:
        from_attributes = True


@router.post("/research/start-project", response_model=Dict[str, Any])
async def start_research_project(
    request: ResearchProjectRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    启动研发项目（统一处理三种路径）
    
    支持三种项目类型：
    1. MODULAR_PLATFORM - 模块化平台开发
    2. BESPOKE_CHASSIS - 定制底盘开发
    3. REVERSE_ENGINEER - 逆向工程
    
    Args:
        request: 研发项目请求参数
    
    Returns:
        项目创建结果
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="公司不存在")
        
        project_type = request.project_type.upper()
        
        if project_type == "MODULAR_PLATFORM":
            # 路径A：模块化平台开发
            if not request.platform_name or not request.platform_code:
                raise HTTPException(
                    status_code=400,
                    detail="模块化平台需要提供platform_name和platform_code"
                )
            
            # 调用底盘设计API（通过内部调用）
            chassis_request = ChassisDesignRequest(
                company_id=request.company_id,
                name=request.platform_name,
                code=request.platform_code,
                wheelbase_mm=request.min_wheelbase_mm or 2500,
                track_front_mm=1500,
                track_rear_mm=1500,
                layout="FF",
                engine_bay_length_mm=600.0,
                engine_bay_width_mm=500.0,
                engine_bay_height_mm=600.0,
                max_cooling_capacity_kw=150.0,
                material=request.material,
                tech_level=request.tech_level,
                source_type="MODULAR_PLATFORM",
                is_platform=True,
                supported_body_styles=request.supported_body_styles or ["SEDAN"],
                min_wheelbase_mm=request.min_wheelbase_mm,
                max_wheelbase_mm=request.max_wheelbase_mm
            )
            
            result = await design_chassis(chassis_request, db)
            return {
                "success": True,
                "project_type": "MODULAR_PLATFORM",
                "chassis": result["chassis"],
                "message": "模块化平台开发项目已启动"
            }
            
        elif project_type == "BESPOKE_CHASSIS":
            # 路径B：定制底盘开发
            if not request.chassis_name or not request.chassis_code:
                raise HTTPException(
                    status_code=400,
                    detail="定制底盘需要提供chassis_name和chassis_code"
                )
            
            chassis_request = ChassisDesignRequest(
                company_id=request.company_id,
                name=request.chassis_name,
                code=request.chassis_code,
                wheelbase_mm=request.wheelbase_mm or 2500,
                track_front_mm=1500,
                track_rear_mm=1500,
                layout=request.layout or "FF",
                engine_bay_length_mm=600.0,
                engine_bay_width_mm=500.0,
                engine_bay_height_mm=600.0,
                max_cooling_capacity_kw=150.0,
                material=request.material,
                tech_level=request.tech_level,
                source_type="BESPOKE",
                is_platform=False
            )
            
            result = await design_chassis(chassis_request, db)
            return {
                "success": True,
                "project_type": "BESPOKE_CHASSIS",
                "chassis": result["chassis"],
                "message": "定制底盘开发项目已启动，可直接用于车辆设计"
            }
            
        elif project_type == "REVERSE_ENGINEER":
            # 路径C：逆向工程
            if not request.target_car_id:
                raise HTTPException(
                    status_code=400,
                    detail="逆向工程需要提供target_car_id"
                )
            
            reverse_request = ReverseEngineeringRequest(
                company_id=request.company_id,
                target_car_id=request.target_car_id,
                investment_multiplier=request.investment_multiplier or 1.0
            )
            
            result = await reverse_engineer_car(reverse_request, db)
            return {
                "success": True,
                "project_type": "REVERSE_ENGINEER",
                **result,
                "message": "逆向工程项目已完成，已生成克隆底盘"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"无效的项目类型: {project_type}。必须是: MODULAR_PLATFORM, BESPOKE_CHASSIS, REVERSE_ENGINEER"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动研发项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EngineeringCore API Endpoints (Physics Engine)
# ============================================================================

class ChassisCalcRequest(BaseModel):
    """底盘计算请求"""
    wheelbase_mm: float = Field(gt=0, description="轴距（毫米）")
    track_front_mm: float = Field(gt=0, description="前轮距（毫米）")
    track_rear_mm: float = Field(gt=0, description="后轮距（毫米）")
    structure_type: str = Field(description="结构类型：LADDER 或 MONOCOQUE")
    material_id: str = Field(description="材料ID，如 STEEL_LOW_CARBON, ALUMINIUM_CAST")
    process_id: str = Field(description="制造工艺ID，如 STAMPING, FORGING, CASTING_SAND")
    design_year: int = Field(ge=1946, le=2100, description="设计年份")
    tech_level: int = Field(default=1, ge=1, le=10, description="技术等级")
    torsional_rigidity_target: int = Field(default=50, ge=1, le=100, description="扭转刚性目标")
    layout: str = Field(default="FF", description="驱动布局：FF, FR, MR, RR, AWD")
    
    class Config:
        from_attributes = True


class EngineCalcRequest(BaseModel):
    """引擎计算请求"""
    displacement_cc: int = Field(gt=0, description="排量（立方厘米）")
    configuration: str = Field(description="引擎配置：INLINE, V, BOXER, VR, W")
    material_grade_id: str = Field(description="材料等级ID，如 CAST_IRON_STANDARD, ALUMINIUM_FORGED")
    process_id: str = Field(description="制造工艺ID，如 CASTING_DIE, FORGING")
    design_year: int = Field(ge=1946, le=2100, description="设计年份")
    stroke_mm: float = Field(gt=0, description="行程（毫米）")
    tech_level: int = Field(default=1, ge=1, le=10, description="技术等级")
    
    class Config:
        from_attributes = True


@router.post("/calculate-chassis", response_model=Dict[str, Any])
async def calculate_chassis(
    request: ChassisCalcRequest,
    db: Optional[Session] = Depends(get_db_optional)
) -> Dict[str, Any]:
    """
    计算底盘设计统计数据
    
    使用 EngineeringCore 物理引擎进行硬核模拟计算。
    返回重量、成本、最大载荷、可靠性评分。
    """
    try:
        # 计算体积（基于轴距和轮距）
        avg_track_mm = (request.track_front_mm + request.track_rear_mm) / 2.0
        # 简化：假设底盘体积 = 轴距 × 轮距 × 高度（估算）
        # 高度估算：基于结构类型
        estimated_height_mm = 500.0 if request.structure_type == "LADDER" else 400.0
        volume_m3 = (request.wheelbase_mm / 1000.0) * (avg_track_mm / 1000.0) * (estimated_height_mm / 1000.0) * 0.5
        
        # 估算载荷要求（基于扭转刚性目标）
        # 更高的扭转刚性 = 更高的载荷要求
        base_load_n = 10000.0
        load_requirements_n = base_load_n * (1.0 + request.torsional_rigidity_target / 100.0)
        
        # 设计复杂度（基于结构类型和布局）
        design_complexity = 5.0
        if request.structure_type == "MONOCOQUE":
            design_complexity += 2.0
        if request.layout in ["MR", "RR", "AWD"]:
            design_complexity += 1.5
        
        # 估算零件数和集成复杂度
        part_count = 100 if request.structure_type == "LADDER" else 150
        integration_complexity = 5.0 + (request.tech_level - 1) * 0.3
        
        # 使用 EngineeringCore 评估底盘设计
        geometry = {
            "volume_m3": volume_m3,
            "load_requirements_n": load_requirements_n,
            "design_complexity": design_complexity,
            "part_count": part_count,
            "integration_complexity": integration_complexity
        }
        
        result = EngineeringCore.evaluate_chassis_design(
            geometry=geometry,
            material_grade_id=request.material_id,
            process_id=request.process_id,
            current_year=request.design_year,
            tech_intro_year=request.design_year - request.tech_level * 2
        )
        
        return {
            "success": True,
            "weight_kg": result["weight_kg"],
            "cost": result["cost"],
            "max_load_n": result["max_load_n"],
            "reliability_score": result["reliability_score"],
            "safety_factor": result.get("safety_factor", 0.0)
        }
        
    except KeyError as e:
        logger.error(f"无效的材料等级或工艺ID: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"无效的材料等级或工艺ID: {str(e)}"
        )
    except Exception as e:
        logger.error(f"底盘计算失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"底盘计算失败: {str(e)}"
        )


@router.post("/calculate-engine", response_model=Dict[str, Any])
async def calculate_engine(
    request: EngineCalcRequest,
    db: Optional[Session] = Depends(get_db_optional)
) -> Dict[str, Any]:
    """
    计算引擎缸体设计统计数据
    
    使用 EngineeringCore 物理引擎进行硬核模拟计算。
    返回缸体重量、最大RPM限制、热容量。
    """
    try:
        result = EngineeringCore.evaluate_engine_block(
            displacement_cc=request.displacement_cc,
            layout=request.configuration,
            material_grade_id=request.material_grade_id,
            process_id=request.process_id,
            current_year=request.design_year,
            stroke_mm=request.stroke_mm,
            tech_intro_year=request.design_year - request.tech_level * 2
        )
        
        return {
            "success": True,
            "block_weight_kg": result["block_weight_kg"],
            "max_rpm_limit": result["max_rpm_limit"],
            "thermal_capacity_kw": result["thermal_capacity_kw"]
        }
        
    except KeyError as e:
        logger.error(f"无效的材料等级或工艺ID: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"无效的材料等级或工艺ID: {str(e)}"
        )
    except Exception as e:
        logger.error(f"引擎计算失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"引擎计算失败: {str(e)}"
        )


@router.get("/material-grades", response_model=Dict[str, Any])
async def get_material_grades() -> Dict[str, Any]:
    """
    获取所有可用的材料等级
    """
    grades = {}
    for grade_id, grade in MATERIAL_GRADES.items():
        grades[grade_id] = {
            "id": grade.id,
            "base_cost_multiplier": grade.base_cost_multiplier,
            "yield_strength_mpa": grade.yield_strength_mpa,
            "density": grade.density,
            "thermal_conductivity": grade.thermal_conductivity
        }
    
    return {
        "success": True,
        "material_grades": grades
    }


@router.get("/manufacturing-processes", response_model=Dict[str, Any])
async def get_manufacturing_processes() -> Dict[str, Any]:
    """
    获取所有可用的制造工艺
    """
    processes = {}
    for process_id, process in MANUFACTURING_PROCESSES.items():
        processes[process_id] = {
            "id": process.id,
            "cost_setup": process.cost_setup,
            "cost_per_unit_mod": process.cost_per_unit_mod,
            "strength_mod": process.strength_mod,
            "waste_ratio": process.waste_ratio
        }
    
    return {
        "success": True,
        "manufacturing_processes": processes
    }


__all__ = ["router"]
