"""
工程核心数据模型：引擎、底盘、车辆配置
遵循硬核模拟原则：基于物理约束，而非随机数
"""
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, 
    ForeignKey, Text, CheckConstraint, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, validates
from typing import Optional, Dict, Any
import json
import math
from enum import Enum

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class ChassisSourceType(str, Enum):
    """底盘来源类型枚举"""
    MODULAR_PLATFORM = "MODULAR_PLATFORM"  # 模块化平台 - 高R&D成本，高可重用性
    BESPOKE = "BESPOKE"  # 定制底盘 - 低R&D成本，锁定单一车型
    CLONED = "CLONED"  # 克隆底盘 - 逆向工程，快速但法律风险


class RustProtectionLevel(str, Enum):
    """防锈保护级别枚举"""
    NONE = "NONE"  # 无特殊防锈处理
    PARTIAL_GALVANIZED = "PARTIAL_GALVANIZED"  # 部分镀锌（1960s+）
    FULL_DIP = "FULL_DIP"  # 全浸镀锌（1975+）


class FuelTankLocation(str, Enum):
    """油箱位置枚举"""
    REAR_AXLE_BEHIND = "REAR_AXLE_BEHIND"  # 后轴后方（传统位置，碰撞风险）
    UNDER_SEAT = "UNDER_SEAT"  # 座椅下方（紧凑型车）
    MID_CENTRAL = "MID_CENTRAL"  # 中央位置（最安全，但占用空间）


class WidthClass(str, Enum):
    """宽度级别枚举"""
    K_CAR = "K_CAR"  # K-Car（日本轻自动车标准，窄）
    STANDARD = "STANDARD"  # 标准宽度
    WIDEBODY = "WIDEBODY"  # 宽体（运动型/豪华型）


class Engine(Base, TimestampMixin, BaseModel):
    """
    引擎模型 - 完整的物理参数驱动设计
    
    核心哲学：
    - 性能由物理参数派生（排量、压缩比、进气方式）
    - 尺寸由配置和缸数决定（V型 vs 直列）
    - 可靠性受热负载和应力影响
    """
    __tablename__ = "engines"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=True, 
                       comment="NULL表示通用/第三方供应商引擎（暂不使用外键，等companies表创建后再添加）")
    
    name = Column(String(100), nullable=False, comment="引擎名称，如 'EcoBoost 2.0T'")
    code = Column(String(50), nullable=False, unique=True, comment="唯一引擎代码")
    
    # ========== 核心物理参数（输入） ==========
    bore_mm = Column(Float, nullable=False, comment="缸径（毫米）- 决定排量和功率潜力")
    stroke_mm = Column(Float, nullable=False, comment="行程（毫米）- 决定扭矩特性")
    cylinder_count = Column(Integer, nullable=False, comment="缸数：4/6/8/12等")
    
    configuration = Column(
        String(20), nullable=False,
        comment="配置类型：INLINE（直列）/ V（V型）/ BOXER（水平对置）/ VR（VR型）"
    )
    
    compression_ratio = Column(Float, nullable=False, default=10.0, 
                              comment="压缩比 - 影响效率和功率，范围通常8-14")
    
    induction_type = Column(
        String(20), nullable=False, default="NA",
        comment="进气方式：NA（自然吸气）/ TURBO（涡轮）/ SUPERCHARGED（机械增压）/ TWINTURBO"
    )
    
    boost_pressure_bar = Column(Float, nullable=True, default=0.0,
                                comment="增压压力（bar）- 仅增压引擎，0表示NA")
    
    material = Column(
        String(20), nullable=False, default="CAST_IRON",
        comment="缸体材料：CAST_IRON（铸铁）/ ALUMINUM（铝）/ MAGNESIUM（镁）"
    )
    
    valvetrain = Column(
        String(20), nullable=False, default="OHC",
        comment="配气机构：OHV/ SOHC/ DOHC/ VARIABLE（可变气门）"
    )
    
    fuel_type = Column(
        String(20), nullable=False, default="GASOLINE",
        comment="燃料类型：GASOLINE/ DIESEL/ E85/ LPG"
    )
    
    # ========== 技术等级（影响性能和可靠性） ==========
    tech_level = Column(Integer, nullable=False, default=1,
                       comment="技术等级1-10，影响材料质量、公差、热管理")
    
    # ========== 派生物理属性（计算得出，不由用户直接设置） ==========
    displacement_cc = Column(Integer, nullable=False, comment="排量（cc）- 由 bore × stroke × cylinders 计算")
    
    max_horsepower = Column(Integer, nullable=False, comment="最大马力（HP）- 物理公式派生")
    max_torque_nm = Column(Integer, nullable=False, comment="最大扭矩（牛·米）- 物理公式派生")
    redline_rpm = Column(Integer, nullable=False, comment="红线转速 - 由行程和材料限制")
    
    weight_kg = Column(Float, nullable=False, comment="引擎重量（kg）- 由排量、材料、配置计算")
    
    # ========== 尺寸约束（毫米） ==========
    length_mm = Column(Float, nullable=False, comment="引擎长度 - 影响底盘匹配")
    width_mm = Column(Float, nullable=False, comment="引擎宽度")
    height_mm = Column(Float, nullable=False, comment="引擎高度")
    
    # ========== 可靠性与热管理 ==========
    thermal_load = Column(Float, nullable=False, comment="热负载系数 - 高增压/高压缩比增加热量")
    specific_output = Column(Float, nullable=False, comment="升功率（HP/L）- 过高会降低可靠性")
    reliability_base_score = Column(Float, nullable=False, comment="基础可靠性分数 0-100")
    
    # ========== 燃油经济性 ==========
    fuel_efficiency_rating = Column(Float, nullable=False, 
                                    comment="燃效评级 - 基于热效率和BSFC")
    bsfc_g_kwh = Column(Float, nullable=False, 
                       comment="制动燃油消耗率 Brake Specific Fuel Consumption")
    
    # ========== 成本 ==========
    development_cost = Column(Float, nullable=False, default=0.0, 
                             comment="研发成本（百万游戏币）")
    manufacturing_cost = Column(Float, nullable=False, comment="单位制造成本")
    
    # ========== 状态与可用性 ==========
    # 注意：is_available 和 development_turn 已移至 RDManager 管理
    is_proprietary = Column(Boolean, nullable=False, default=False, 
                           comment="是否为专有技术")
    
    # ========== 3D可视化数据（为未来3D前端准备） ==========
    visual_specs = Column(
        JSON, nullable=True,
        comment="可视化规格（JSON）- 存储3D模型/纹理信息"
    )
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("bore_mm > 0 AND bore_mm <= 150", name="check_bore_range"),
        CheckConstraint("stroke_mm > 0 AND stroke_mm <= 200", name="check_stroke_range"),
        CheckConstraint("cylinder_count IN (2, 3, 4, 5, 6, 8, 10, 12, 16)", name="check_cylinder_count"),
        CheckConstraint("compression_ratio >= 6.0 AND compression_ratio <= 16.0", name="check_compression"),
        CheckConstraint("tech_level >= 1 AND tech_level <= 10", name="check_tech_level"),
        CheckConstraint("reliability_base_score >= 0 AND reliability_base_score <= 100", name="check_reliability"),
        Index("idx_engine_company", "company_id"),
        Index("idx_engine_game", "game_id"),
        # 注意：idx_engine_available 索引已移除（is_available字段已删除）
    )
    
    # ========== 关系 ==========
    # trims 反向关系将由 CarTrim 定义
    
    def to_dict(self) -> Dict[str, Any]:
        """扩展基类方法，包含技术细节"""
        base_dict = super().to_dict()
        base_dict.update({
            "bore_stroke_ratio": round(self.bore_mm / self.stroke_mm, 2) if self.stroke_mm > 0 else 0,
            "power_to_weight": round(self.max_horsepower / self.weight_kg, 2) if self.weight_kg > 0 else 0,
            "configuration_display": f"{self.configuration}{self.cylinder_count}",
            "displacement_liters": round(self.displacement_cc / 1000.0, 2),
        })
        return base_dict
    
    @validates("configuration")
    def validate_configuration(self, key: str, value: str) -> str:
        """验证配置类型"""
        allowed = ["INLINE", "V", "BOXER", "VR", "W"]
        if value.upper() not in allowed:
            raise ValueError(f"配置必须是以下之一: {allowed}")
        return value.upper()
    
    @validates("induction_type")
    def validate_induction(self, key: str, value: str) -> str:
        """验证进气类型"""
        allowed = ["NA", "TURBO", "SUPERCHARGED", "TWINTURBO"]
        if value.upper() not in allowed:
            raise ValueError(f"进气类型必须是以下之一: {allowed}")
        return value.upper()
    
    def finalize_design(self, payload: Dict[str, Any]) -> None:
        """
        完成设计（由RDManager调用）
        
        Args:
            payload: 设计完成时的额外数据
        """
        # 标记为可用（如果RDManager需要）
        # 注意：is_available字段已移除，由RDManager管理状态
        # 这里可以添加其他完成设计的逻辑，如应用熟悉度加成等
        pass
    
    def __repr__(self) -> str:
        return (f"<Engine(code='{self.code}', "
                f"config={self.configuration}{self.cylinder_count}, "
                f"displacement={self.displacement_cc}cc, "
                f"power={self.max_horsepower}hp, "
                f"induction={self.induction_type})>")


class Chassis(Base, TimestampMixin, BaseModel):
    """
    底盘平台模型 - 定义物理约束和安装空间
    
    核心约束：
    - 引擎舱尺寸限制（长宽高）
    - 冷却容量限制（高热负载引擎需要更大散热器）
    - 重量分配影响操控
    """
    __tablename__ = "chassis"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=True, 
                       comment="公司ID（暂不使用外键，等companies表创建后再添加）")
    
    name = Column(String(100), nullable=False, comment="平台名称，如 'C-Platform'")
    code = Column(String(50), nullable=False, unique=True)
    
    # ========== 尺寸与布局 ==========
    wheelbase_mm = Column(Integer, nullable=False, comment="轴距（毫米）")
    track_front_mm = Column(Integer, nullable=False, comment="前轮距")
    track_rear_mm = Column(Integer, nullable=False, comment="后轮距")
    
    layout = Column(
        String(10), nullable=False,
        comment="驱动布局：FF（前置前驱）/ FR（前置后驱）/ MR（中置后驱）/ RR（后置后驱）/ AWD（四驱）"
    )
    
    # ========== 引擎舱约束（关键！） ==========
    engine_bay_length_mm = Column(Float, nullable=False, 
                                  comment="引擎舱最大长度 - 决定能装多长的引擎")
    engine_bay_width_mm = Column(Float, nullable=False,
                                comment="引擎舱最大宽度 - V型引擎更宽")
    engine_bay_height_mm = Column(Float, nullable=False,
                                 comment="引擎舱最大高度 - 涡轮增压会增加高度需求")
    
    max_cooling_capacity_kw = Column(Float, nullable=False,
                                    comment="最大冷却容量（千瓦）- 限制可装引擎的热负载")
    
    # ========== 结构与材料 ==========
    material = Column(
        String(20), nullable=False, default="STEEL",
        comment="底盘材料：STEEL（钢）/ ALUMINUM（铝）/ CARBON（碳纤维）"
    )
    
    rigidity_rating = Column(Float, nullable=False, default=50.0,
                            comment="刚性评分 0-100 - 影响操控和安全")
    
    weight_kg = Column(Float, nullable=False, comment="底盘重量（kg）- 不含引擎")
    
    # ========== 安全与结构 ==========
    crash_test_rating = Column(Float, nullable=False, default=50.0,
                              comment="碰撞测试基础评分 0-100")
    
    # ========== 技术等级 ==========
    tech_level = Column(Integer, nullable=False, default=1)
    
    # ========== 底盘来源类型（R&D路径）==========
    source_type = Column(
        SQLEnum(ChassisSourceType, native_enum=False),
        nullable=False,
        default=ChassisSourceType.MODULAR_PLATFORM,
        comment="底盘来源类型：MODULAR_PLATFORM（模块化平台）/ BESPOKE（定制）/ CLONED（克隆）"
    )
    
    # ========== 逆向工程相关字段（仅CLONED类型）==========
    original_competitor_id = Column(
        Integer, nullable=True,
        comment="原始竞争对手车辆ID（仅克隆底盘）- 记录被逆向工程的CarTrim ID"
    )
    legal_risk_factor = Column(
        Float, nullable=False, default=0.0,
        comment="法律风险系数 0.0-1.0 - 在竞争对手所在区域销售时的风险"
    )
    quality_cap = Column(
        Float, nullable=True,
        comment="品质上限（仅克隆底盘）- 可改进但始终低于原版，范围0.0-1.0"
    )
    
    # ========== 平台共享（Platform Sharing）==========
    is_platform = Column(
        Boolean, nullable=False, default=True,
        comment="是否作为共享平台 - 平台可被多个车型使用以降低成本"
    )
    
    platform_family = Column(
        String(50), nullable=True,
        comment="平台家族代码 - 如 'MQB', 'TNGA'，同家族平台可共享部分设计"
    )
    
    derived_from_chassis_id = Column(
        Integer, nullable=True,
        comment="衍生自哪个平台ID - 衍生平台继承部分设计，降低研发成本"
    )
    
    models_using_count = Column(
        Integer, nullable=False, default=0,
        comment="使用此平台的车型数量 - 影响规模经济效益"
    )
    
    platform_generation = Column(
        Integer, nullable=False, default=1,
        comment="平台代数 - 第几代平台，新代数需要更多研发投入"
    )
    
    # ========== 灵活性参数（Platform Flexibility）==========
    min_wheelbase_mm = Column(
        Integer, nullable=True,
        comment="最小轴距（毫米）- 平台支持的最小轴距（已废弃，使用base_wheelbase和bandwidth_wheelbase）"
    )
    
    max_wheelbase_mm = Column(
        Integer, nullable=True,
        comment="最大轴距（毫米）- 平台支持的最大轴距（已废弃，使用base_wheelbase和bandwidth_wheelbase）"
    )
    
    # ========== 平台带宽参数（Platform Bandwidth）==========
    base_wheelbase_mm = Column(
        Integer, nullable=True,
        comment="基础轴距（毫米）- 平台的标准轴距，使用此值无额外成本"
    )
    
    bandwidth_wheelbase_mm = Column(
        Integer, nullable=True,
        comment="轴距带宽（毫米）- 允许的轴距调整范围（±值），超出需要适配成本"
    )
    
    base_track_width_mm = Column(
        Integer, nullable=True,
        comment="基础轮距（毫米）- 平台的标准轮距（前后轮距的平均值）"
    )
    
    bandwidth_track_mm = Column(
        Integer, nullable=True,
        comment="轮距带宽（毫米）- 允许的轮距调整范围（±值），超出需要适配成本"
    )
    
    supported_body_styles = Column(
        Text, nullable=False, default='["SEDAN"]',
        comment="支持的车身类型列表（JSON）- 如 ['SEDAN', 'SUV', 'WAGON']"
    )
    
    # ========== 规模经济效益 ==========
    base_tooling_cost = Column(
        Float, nullable=False, default=50.0,
        comment="基础模具成本（百万游戏币）- 首次使用平台的固定成本"
    )
    
    tooling_amortized = Column(
        Float, nullable=False, default=0.0,
        comment="已摊销的模具成本 - 随生产数量增加而增加"
    )
    
    economies_of_scale_factor = Column(
        Float, nullable=False, default=1.0,
        comment="规模经济系数 - 使用车型越多，单位成本越低（0.6-1.0）"
    )
    
    # ========== 成本 ==========
    development_cost = Column(Float, nullable=False, default=0.0)
    manufacturing_cost = Column(Float, nullable=False, comment="单位制造成本")
    
    # ========== 状态 ==========
    # 注意：is_available 和 development_turn 已移至 RDManager 管理
    
    # ========== 3D可视化数据（为未来3D前端准备） ==========
    visual_specs = Column(
        JSON, nullable=True,
        comment="可视化规格（JSON）- 存储车身造型参数"
    )
    
    # ========== 物理结构组 (Group A: Rigidity/Corrosion/NVH) ==========
    torsional_rigidity_target = Column(
        Integer, nullable=True, default=50,
        comment="扭转刚性目标 1-100 - 影响操控精度和NVH"
    )
    
    rust_protection_level = Column(
        SQLEnum(RustProtectionLevel, native_enum=False),
        nullable=False, default=RustProtectionLevel.NONE,
        comment="防锈保护级别：NONE / PARTIAL_GALVANIZED / FULL_DIP"
    )
    
    nvh_insulation_mass = Column(
        Float, nullable=True, default=0.0,
        comment="NVH隔音质量（kg）- 增加的隔音材料重量，影响舒适性"
    )
    
    # ========== 包装与安全组 (Group B & C: Packaging/Safety) ==========
    engine_bay_volume = Column(
        Integer, nullable=True,
        comment="引擎舱容积（升）- 从engine_bay_*_mm计算得出"
    )
    
    transmission_tunnel_fitted = Column(
        Boolean, nullable=False, default=False,
        comment="是否安装传动轴通道 - 启用RWD/AWD布局"
    )
    
    crumple_zone_length = Column(
        Float, nullable=True, default=0.0,
        comment="溃缩区长度（米）- 前后溃缩区总长度，影响安全但占用空间"
    )
    
    fuel_tank_location = Column(
        SQLEnum(FuelTankLocation, native_enum=False),
        nullable=False, default=FuelTankLocation.REAR_AXLE_BEHIND,
        comment="油箱位置：REAR_AXLE_BEHIND / UNDER_SEAT / MID_CENTRAL"
    )
    
    # ========== 制造与供应链组 (Group D & E: Manufacturing/Supply Chain) ==========
    manufacturing_complexity_score = Column(
        Float, nullable=True, default=0.5,
        comment="制造复杂度评分 0.0-1.0 - 影响工厂缺陷率"
    )
    
    parts_bin_sharing_ratio = Column(
        Float, nullable=True, default=0.5,
        comment="零件库共享比例 0.0-1.0 - 高值表示使用通用供应商零件"
    )
    
    # ========== 认证组 (Group F: Homologation/Regulations) ==========
    designed_bumper_height = Column(
        Float, nullable=True,
        comment="设计保险杠高度（米）- 关键用于70年代美国法规"
    )
    
    overall_width_class = Column(
        SQLEnum(WidthClass, native_enum=False),
        nullable=False, default=WidthClass.STANDARD,
        comment="宽度级别：K_CAR / STANDARD / WIDEBODY"
    )
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("wheelbase_mm > 1500 AND wheelbase_mm < 5000", name="check_wheelbase"),
        CheckConstraint("rigidity_rating >= 0 AND rigidity_rating <= 100", name="check_rigidity"),
        CheckConstraint("crash_test_rating >= 0 AND crash_test_rating <= 100", name="check_crash"),
        CheckConstraint("tech_level >= 1 AND tech_level <= 10", name="check_chassis_tech"),
        CheckConstraint("torsional_rigidity_target IS NULL OR (torsional_rigidity_target >= 1 AND torsional_rigidity_target <= 100)", name="check_torsional_rigidity"),
        CheckConstraint("manufacturing_complexity_score IS NULL OR (manufacturing_complexity_score >= 0.0 AND manufacturing_complexity_score <= 1.0)", name="check_manufacturing_complexity"),
        CheckConstraint("parts_bin_sharing_ratio IS NULL OR (parts_bin_sharing_ratio >= 0.0 AND parts_bin_sharing_ratio <= 1.0)", name="check_parts_bin_sharing"),
        CheckConstraint("nvh_insulation_mass IS NULL OR nvh_insulation_mass >= 0.0", name="check_nvh_mass"),
        CheckConstraint("crumple_zone_length IS NULL OR crumple_zone_length >= 0.0", name="check_crumple_zone"),
        Index("idx_chassis_company", "company_id"),
        Index("idx_chassis_game", "game_id"),
        # 注意：idx_chassis_available 索引已移除（is_available字段已删除）
    )
    
    @validates("layout")
    def validate_layout(self, key: str, value: str) -> str:
        """验证驱动布局"""
        allowed = ["FF", "FR", "MR", "RR", "AWD"]
        if value.upper() not in allowed:
            raise ValueError(f"布局必须是以下之一: {allowed}")
        return value.upper()
    
    @validates("material")
    def validate_material(self, key: str, value: str) -> str:
        """验证材料"""
        allowed = ["STEEL", "ALUMINUM", "CARBON"]
        if value.upper() not in allowed:
            raise ValueError(f"材料必须是以下之一: {allowed}")
        return value.upper()
    
    @validates("rust_protection_level")
    def validate_rust_protection(self, key: str, value: str) -> RustProtectionLevel:
        """验证防锈保护级别"""
        if isinstance(value, str):
            try:
                return RustProtectionLevel(value.upper())
            except ValueError:
                raise ValueError(f"防锈保护级别必须是以下之一: {[e.value for e in RustProtectionLevel]}")
        return value
    
    @validates("fuel_tank_location")
    def validate_fuel_tank_location(self, key: str, value: str) -> FuelTankLocation:
        """验证油箱位置"""
        if isinstance(value, str):
            try:
                return FuelTankLocation(value.upper())
            except ValueError:
                raise ValueError(f"油箱位置必须是以下之一: {[e.value for e in FuelTankLocation]}")
        return value
    
    @validates("overall_width_class")
    def validate_width_class(self, key: str, value: str) -> WidthClass:
        """验证宽度级别"""
        if isinstance(value, str):
            try:
                return WidthClass(value.upper())
            except ValueError:
                raise ValueError(f"宽度级别必须是以下之一: {[e.value for e in WidthClass]}")
        return value
    
    def get_supported_body_styles(self) -> list[str]:
        """获取支持的车身类型列表"""
        try:
            return json.loads(self.supported_body_styles)
        except:
            return ["SEDAN"]
    
    def set_supported_body_styles(self, styles: list[str]) -> None:
        """设置支持的车身类型列表"""
        self.supported_body_styles = json.dumps(styles)
    
    def add_body_style_support(self, style: str) -> bool:
        """
        添加车身类型支持
        
        Returns:
            是否成功添加（如果已存在则返回False）
        """
        styles = self.get_supported_body_styles()
        if style.upper() not in styles:
            styles.append(style.upper())
            self.set_supported_body_styles(styles)
            return True
        return False
    
    def supports_body_style(self, style: str) -> bool:
        """检查是否支持指定车身类型"""
        return style.upper() in self.get_supported_body_styles()
    
    def supports_wheelbase(self, wheelbase: int) -> bool:
        """
        检查是否支持指定轴距
        
        Args:
            wheelbase: 轴距（毫米）
            
        Returns:
            是否在支持范围内
        """
        if self.min_wheelbase_mm is None or self.max_wheelbase_mm is None:
            # 固定轴距平台
            return abs(wheelbase - self.wheelbase_mm) < 100  # 允许±100mm误差
        
        return self.min_wheelbase_mm <= wheelbase <= self.max_wheelbase_mm
    
    def calculate_economies_of_scale(self, total_models: int) -> float:
        """
        计算规模经济效益
        
        Args:
            total_models: 使用此平台的总车型数
            
        Returns:
            成本系数（越小越好，0.6-1.0）
        """
        import math
        
        # 单车型：1.0（无优惠）
        # 2-3车型：0.9
        # 4-6车型：0.8
        # 7+车型：0.7-0.6
        
        if total_models <= 1:
            return 1.0
        
        # 对数函数：成本随车型数增加而递减
        factor = 1.0 - (0.4 * math.log(total_models) / math.log(10))
        
        return max(0.6, min(1.0, factor))
    
    def update_platform_usage(self, model_count: int) -> None:
        """
        更新平台使用情况并重新计算规模经济
        
        Args:
            model_count: 当前使用此平台的车型数
        """
        self.models_using_count = model_count
        self.economies_of_scale_factor = self.calculate_economies_of_scale(model_count)
    
    def get_effective_manufacturing_cost(self) -> float:
        """
        获取有效制造成本（考虑规模经济）
        
        Returns:
            有效单位成本
        """
        return self.manufacturing_cost * self.economies_of_scale_factor
    
    def get_manufacturing_efficiency(self) -> float:
        """
        获取制造效率系数
        
        根据底盘来源类型返回不同的效率：
        - 模块化平台: 100% (1.0) - 标准效率
        - 定制底盘: 80% (0.8) - 低效率（工具不通用）
        - 克隆底盘: 120% (1.2) - 高效率（跳过工具开发）
        
        Returns:
            制造效率系数
        """
        if self.source_type == ChassisSourceType.MODULAR_PLATFORM:
            return 1.0  # 100%
        elif self.source_type == ChassisSourceType.BESPOKE:
            return 0.8  # 80%
        elif self.source_type == ChassisSourceType.CLONED:
            return 1.2  # 120% (跳过工具开发)
        return 1.0
    
    def get_reliability_penalty(self) -> float:
        """
        获取可靠性惩罚（仅克隆底盘）
        
        Returns:
            可靠性惩罚值（负数表示降低，如-15.0表示-15%）
        """
        if self.source_type == ChassisSourceType.CLONED:
            return -15.0  # -15%
        return 0.0
    
    def get_reusability(self) -> str:
        """
        获取可重用性描述
        
        Returns:
            可重用性级别：HIGH / NONE / LOW
        """
        if self.source_type == ChassisSourceType.MODULAR_PLATFORM:
            return "HIGH"
        elif self.source_type == ChassisSourceType.BESPOKE:
            return "NONE"  # 锁定单一车型
        elif self.source_type == ChassisSourceType.CLONED:
            return "LOW"  # 可重用但有限制
        return "NONE"
    
    def finalize_design(self, payload: Dict[str, Any]) -> None:
        """
        完成设计（由RDManager调用）
        
        Args:
            payload: 设计完成时的额外数据
        """
        # 标记为可用（如果RDManager需要）
        # 注意：is_available字段已移除，由RDManager管理状态
        # 这里可以添加其他完成设计的逻辑，如应用熟悉度加成等
        pass
    
    def __repr__(self) -> str:
        platform_info = f", platform={self.platform_family}" if self.platform_family else ""
        return (f"<Chassis(code='{self.code}', "
                f"layout={self.layout}, "
                f"wheelbase={self.wheelbase_mm}mm{platform_info}, "
                f"models_using={self.models_using_count}, "
                f"cost_factor={self.economies_of_scale_factor:.2f})>")


class CarTrim(Base, TimestampMixin, BaseModel):
    """
    车辆配置（Trim）- 引擎+底盘+车身的最终组装
    
    这是玩家最终设计和销售的产品
    所有性能参数从组件计算得出
    """
    __tablename__ = "car_trims"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False, 
                       comment="公司ID（暂不使用外键，等companies表创建后再添加）")
    
    name = Column(String(100), nullable=False, comment="配置名称，如 'Mustang GT Premium'")
    model_name = Column(String(100), nullable=False, comment="车型名称，如 'Mustang'")
    trim_code = Column(String(50), nullable=False, unique=True)
    
    # ========== 组件引用（核心！） ==========
    engine_id = Column(Integer, ForeignKey("engines.id", ondelete="RESTRICT"), nullable=False,
                      comment="使用的引擎ID")
    chassis_id = Column(Integer, ForeignKey("chassis.id", ondelete="RESTRICT"), nullable=False,
                       comment="使用的底盘ID")
    
    # ========== 车身参数 ==========
    body_style = Column(
        String(20), nullable=False,
        comment="车身类型：SEDAN/ COUPE/ SUV/ WAGON/ HATCHBACK/ CONVERTIBLE/ TRUCK"
    )
    
    seating_capacity = Column(Integer, nullable=False, default=5)
    cargo_volume_liters = Column(Integer, nullable=False, default=400)
    
    body_weight_kg = Column(Float, nullable=False, comment="车身重量（不含底盘和引擎）")
    drag_coefficient = Column(Float, nullable=False, default=0.35, 
                             comment="风阻系数 - 影响高速性能和油耗")
    frontal_area_sqm = Column(Float, nullable=False, default=2.5, 
                             comment="正面投影面积（平方米）")
    
    # ========== 派生性能参数（只读，由计算得出） ==========
    total_weight_kg = Column(Float, nullable=False, comment="总重 = 引擎 + 底盘 + 车身 + 流体")
    
    power_to_weight_ratio = Column(Float, nullable=False, 
                                   comment="推重比（HP/kg）- 关键性能指标")
    
    zero_to_hundred_kph_sec = Column(Float, nullable=False, 
                                     comment="0-100km/h 加速时间（秒）- 物理公式计算")
    
    top_speed_kph = Column(Float, nullable=False, comment="最高速度（km/h）")
    
    quarter_mile_sec = Column(Float, nullable=False, comment="1/4英里加速时间")
    
    braking_100_0_meters = Column(Float, nullable=False, 
                                  comment="100-0km/h 刹车距离（米）- 受重量和制动系统影响")
    
    lateral_g_force = Column(Float, nullable=False, 
                            comment="横向G值 - 弯道极限，受底盘刚性和轮胎影响")
    
    fuel_economy_l_100km = Column(Float, nullable=False, 
                                  comment="综合油耗（升/100公里）")
    
    # ========== 可靠性（考虑所有因素） ==========
    final_reliability_score = Column(Float, nullable=False,
                                     comment="最终可靠性 0-100 - 综合引擎、底盘、匹配度")
    
    # ========== 市场与定价 ==========
    segment = Column(
        String(20), nullable=False,
        comment="细分市场：SUBCOMPACT/ COMPACT/ MIDSIZE/ FULLSIZE/ LUXURY/ SPORTS/ SUPER"
    )
    
    manufacturing_cost = Column(Float, nullable=False, comment="制造成本 = 引擎 + 底盘 + 车身 + 组装")
    msrp = Column(Float, nullable=False, comment="建议零售价")
    
    # ========== 兼容性检查结果（缓存） ==========
    compatibility_status = Column(
        String(20), nullable=False, default="COMPATIBLE",
        comment="兼容性状态：COMPATIBLE/ INCOMPATIBLE/ WARNING"
    )
    compatibility_notes = Column(Text, nullable=True, 
                                comment="兼容性检查详细信息（JSON）")
    
    # ========== 生产与状态 ==========
    is_in_production = Column(Boolean, nullable=False, default=False)
    production_start_turn = Column(Integer, nullable=True)
    production_end_turn = Column(Integer, nullable=True)
    
    # ========== 平台关联（可选）==========
    platform_id = Column(
        Integer, nullable=True,
        comment="关联平台ID（Chassis ID）- NULL表示独立开发"
    )
    
    # ========== 3D可视化数据 ==========
    visual_specs = Column(
        JSON, nullable=True,
        comment="可视化规格（JSON）- mesh, paint, wheels等"
    )
    
    # ========== 关系 ==========
    engine = relationship("Engine", foreign_keys=[engine_id])
    chassis = relationship("Chassis", foreign_keys=[chassis_id])
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("total_weight_kg > 0", name="check_positive_weight"),
        CheckConstraint("zero_to_hundred_kph_sec > 0", name="check_positive_accel"),
        CheckConstraint("fuel_economy_l_100km > 0", name="check_positive_fuel"),
        CheckConstraint("final_reliability_score >= 0 AND final_reliability_score <= 100", 
                       name="check_trim_reliability"),
        CheckConstraint("drag_coefficient > 0 AND drag_coefficient < 2.0", name="check_drag"),
        Index("idx_trim_company", "company_id"),
        Index("idx_trim_engine", "engine_id"),
        Index("idx_trim_chassis", "chassis_id"),
        Index("idx_trim_production", "is_in_production"),
    )
    
    @validates("body_style")
    def validate_body_style(self, key: str, value: str) -> str:
        """验证车身类型"""
        allowed = ["SEDAN", "COUPE", "SUV", "WAGON", "HATCHBACK", "CONVERTIBLE", "TRUCK", "VAN"]
        if value.upper() not in allowed:
            raise ValueError(f"车身类型必须是以下之一: {allowed}")
        return value.upper()
    
    @validates("segment")
    def validate_segment(self, key: str, value: str) -> str:
        """验证细分市场"""
        allowed = ["SUBCOMPACT", "COMPACT", "MIDSIZE", "FULLSIZE", "LUXURY", "SPORTS", "SUPER"]
        if value.upper() not in allowed:
            raise ValueError(f"细分市场必须是以下之一: {allowed}")
        return value.upper()
    
    def __repr__(self) -> str:
        return (f"<CarTrim(code='{self.trim_code}', "
                f"model='{self.model_name}', "
                f"power={self.power_to_weight_ratio:.2f}hp/kg, "
                f"0-100={self.zero_to_hundred_kph_sec:.2f}s)>")


# 注意：ResearchProject 模型已移至 backend/logic/rd_manager.py
# 此模型现在由 RDManager 统一管理


# 导出所有模型
__all__ = ["Engine", "Chassis", "CarTrim", "ChassisSourceType"]

