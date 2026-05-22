"""
Vehicle hierarchy models: VehiclePlatform -> VehicleModel -> CarTrim

Implements strict separation:
1. VehiclePlatform: Engineering base (high R&D cost, shared across models)
2. VehicleModel: Marketing nameplate (e.g., "Golf", links to platform)
3. CarTrim: Saleable unit (e.g., "Golf GTI", specific engine/features)

This allows realistic platform economics where multiple models share R&D costs.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from typing import Dict, Any, List
import json

from backend.database import Base
from backend.models.base import TimestampMixin


class VehiclePlatform(Base, TimestampMixin):
    """
    Vehicle platform - the engineering foundation.
    
    A platform defines:
    - Core chassis architecture
    - Powertrain mounting points
    - Wheelbase range
    - Supported body styles
    
    Example: Volkswagen MQB platform → supports Golf, Passat, Tiguan, etc.
    
    Economics: High upfront R&D cost, but amortized across many models.
    """
    __tablename__ = "vehicle_platforms"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False)  # TODO: Add FK when companies table ready
    
    # Identity
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    generation = Column(Integer, default=1)
    
    # Engineering specs (references Chassis)
    chassis_id = Column(Integer, ForeignKey("chassis.id"), nullable=False)
    
    # Flexibility
    min_wheelbase_mm = Column(Integer, nullable=False)
    max_wheelbase_mm = Column(Integer, nullable=False)
    supported_body_styles = Column(Text, nullable=False)  # JSON array
    supported_drivetrains = Column(Text, nullable=False)  # JSON: ["FF", "AWD"]
    
    # Engine compatibility
    min_engine_displacement_cc = Column(Integer, default=1000)
    max_engine_displacement_cc = Column(Integer, default=6000)
    max_engine_power_hp = Column(Integer, default=300)
    
    # Development
    development_start_turn = Column(Integer)
    development_complete_turn = Column(Integer)
    development_cost_total = Column(Float, nullable=False)
    
    # Economics
    per_model_tooling_cost = Column(Float, nullable=False)  # Cost to adapt platform for new model
    base_production_cost = Column(Float, nullable=False)  # Cost per unit
    
    # Usage tracking
    models_count = Column(Integer, default=0)
    total_units_produced = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_discontinued = Column(Boolean, default=False)
    
    # Visual specs for 3D rendering
    visual_specs = Column(Text, nullable=True)  # JSON
    
    # Relationships
    chassis = relationship("Chassis", foreign_keys=[chassis_id])
    models = relationship("VehicleModel", back_populates="platform")
    
    # Indexes
    __table_args__ = (
        Index("idx_platform_company", "company_id"),
        Index("idx_platform_chassis", "chassis_id"),
        Index("idx_platform_active", "is_active"),
    )
    
    def get_supported_body_styles(self) -> List[str]:
        """Parse JSON array of supported body styles."""
        try:
            return json.loads(self.supported_body_styles)
        except:
            return []
    
    def supports_body_style(self, style: str) -> bool:
        """Check if platform can accommodate this body style."""
        return style.upper() in self.get_supported_body_styles()
    
    def supports_engine(self, displacement_cc: int, power_hp: int) -> bool:
        """Check if engine fits platform constraints."""
        return (
            self.min_engine_displacement_cc <= displacement_cc <= self.max_engine_displacement_cc
            and power_hp <= self.max_engine_power_hp
        )
    
    def validate_chassis_source_type(self) -> Dict[str, Any]:
        """
        验证关联的底盘是否为模块化平台类型
        
        VehiclePlatform只能关联source_type=MODULAR_PLATFORM的底盘
        
        Returns:
            {"valid": bool, "error": str}
        """
        if not self.chassis:
            return {"valid": False, "error": "未关联底盘"}
        
        from backend.models.engineering import ChassisSourceType
        if self.chassis.source_type != ChassisSourceType.MODULAR_PLATFORM:
            return {
                "valid": False,
                "error": f"VehiclePlatform只能关联模块化平台底盘，当前底盘类型为: {self.chassis.source_type}"
            }
        
        return {"valid": True, "error": None}
    
    def calculate_amortized_cost_per_unit(self) -> float:
        """
        Calculate per-unit platform cost including amortization.
        
        More models = lower cost per unit due to amortization.
        """
        if self.total_units_produced == 0:
            return self.base_production_cost
        
        # Amortize development cost over units produced
        amortization = self.development_cost_total / max(1, self.total_units_produced)
        
        return self.base_production_cost + amortization
    
    def __repr__(self):
        return f"<VehiclePlatform(code='{self.code}', models={self.models_count}, units={self.total_units_produced})>"


class VehicleModel(Base, TimestampMixin):
    """
    Vehicle model - the marketing nameplate.
    
    A model is customer-facing:
    - Has a brand name (e.g., "Mustang", "Golf")
    - Tied to a specific platform
    - Can have multiple trims (GTI, R-Line, etc.)
    
    Example: Ford Mustang (S197 platform) → Mustang V6, Mustang GT, Mustang Shelby trims
    
    Economics: Lower R&D than platform, mainly styling and engineering.
    """
    __tablename__ = "vehicle_models"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False)  # TODO: Add FK
    
    # Platform link (REQUIRED)
    platform_id = Column(Integer, ForeignKey("vehicle_platforms.id"), nullable=False)
    
    # Identity
    name = Column(String(100), nullable=False)  # "Mustang", "Golf"
    model_code = Column(String(50), unique=True, nullable=False)
    generation = Column(Integer, default=1)
    
    # Classification
    body_style = Column(String(20), nullable=False)  # Must match platform support
    segment = Column(String(20), nullable=False)  # COMPACT, MIDSIZE, etc.
    market_position = Column(String(20), nullable=False)  # ECONOMY, MAINSTREAM, PREMIUM, LUXURY
    
    # Dimensions (within platform wheelbase range)
    length_mm = Column(Integer, nullable=False)
    width_mm = Column(Integer, nullable=False)
    height_mm = Column(Integer, nullable=False)
    wheelbase_mm = Column(Integer, nullable=False)
    
    # Development
    design_start_turn = Column(Integer)
    design_complete_turn = Column(Integer)
    production_start_turn = Column(Integer)
    production_end_turn = Column(Integer)
    
    design_cost = Column(Float, nullable=False)  # Styling, engineering
    tooling_cost = Column(Float, nullable=False)  # Model-specific tooling
    
    # Design targets (high-level goals)
    target_reliability = Column(Float)
    target_performance = Column(Float)
    target_efficiency = Column(Float)
    target_comfort = Column(Float)
    target_safety = Column(Float)
    target_price_point = Column(Float)
    
    # Calculated metrics (aggregated from trims)
    overall_quality_score = Column(Float)
    overall_reliability_score = Column(Float)
    total_units_sold = Column(Integer, default=0)
    
    # Design method tracking
    designed_via = Column(String(20), nullable=False)  # MANUAL, DIRECTIVE, AI
    design_directive_text = Column(Text)  # If designed via NL directive
    
    # Status
    is_active = Column(Boolean, default=False)
    is_discontinued = Column(Boolean, default=False)
    
    # Visual specs (model-specific styling)
    visual_specs = Column(Text)  # JSON with 3D rendering parameters
    
    # Relationships
    platform = relationship("VehiclePlatform", back_populates="models")
    trims = relationship("CarTrim", back_populates="model", foreign_keys="CarTrim.vehicle_model_id")
    
    # Indexes
    __table_args__ = (
        Index("idx_model_company", "company_id"),
        Index("idx_model_platform", "platform_id"),
        Index("idx_model_active", "is_active"),
        Index("idx_model_segment", "segment", "market_position"),
    )
    
    def validate_against_platform(self) -> Dict[str, Any]:
        """
        Validate that model configuration is compatible with platform.
        
        Returns:
            {"valid": bool, "errors": [...], "warnings": [...]}
        """
        errors = []
        warnings = []
        
        if not self.platform:
            errors.append("No platform assigned")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check body style support
        if not self.platform.supports_body_style(self.body_style):
            errors.append(f"Platform does not support {self.body_style}")
        
        # Check wheelbase range
        if not (self.platform.min_wheelbase_mm <= self.wheelbase_mm <= self.platform.max_wheelbase_mm):
            errors.append(f"Wheelbase {self.wheelbase_mm}mm outside platform range "
                        f"({self.platform.min_wheelbase_mm}-{self.platform.max_wheelbase_mm}mm)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_total_development_cost(self) -> float:
        """Calculate total cost including platform share."""
        platform_share = self.platform.per_model_tooling_cost if self.platform else 0.0
        return self.design_cost + self.tooling_cost + platform_share
    
    def __repr__(self):
        return f"<VehicleModel(name='{self.name}', platform='{self.platform.code if self.platform else 'None'}', trims={len(self.trims) if self.trims else 0})>"


# Update CarTrim to link to VehicleModel
# Note: This requires altering the existing CarTrim table to add vehicle_model_id FK
"""
ALTER TABLE car_trims ADD COLUMN vehicle_model_id INTEGER REFERENCES vehicle_models(id);
"""


class VehicleVisualSpecs:
    """
    Pydantic-style schema for vehicle visual specifications.
    
    This is stored as JSON in the visual_specs column of VehiclePlatform/VehicleModel/CarTrim.
    
    Purpose: Frontend 3D engine reads this to construct the car visually.
    """
    
    @staticmethod
    def create_default(body_style: str = "SEDAN") -> Dict[str, Any]:
        """Create default visual specs for a body style."""
        return {
            "body_style_mesh_id": f"mesh_{body_style.lower()}_generic",
            "paint_material_id": "paint_metallic_silver",
            "wheel_id": "wheel_alloy_17inch",
            "ride_height": 150.0,  # mm
            "accessory_ids": [],
            
            # Proportions (for procedural generation)
            "hood_length_ratio": 0.25,
            "cabin_length_ratio": 0.50,
            "trunk_length_ratio": 0.25,
            
            "greenhouse_height_ratio": 0.45,
            "beltline_height_ratio": 0.55,
            
            # Styling
            "grille_style": "horizontal_slats",
            "grille_size": 0.3,
            "headlight_style": "swept",
            "taillight_style": "horizontal",
            
            # Colors
            "exterior_color_hex": "#C0C0C0",
            "exterior_finish": "metallic",
            "trim_color": "chrome",
            "wheel_color": "silver",
            
            # Interior
            "interior_primary_color": "black",
            "interior_secondary_color": "gray",
            "interior_material": "cloth",
            
            # Wheels
            "wheel_diameter_inches": 17,
            "tire_width_mm": 215,
            "tire_aspect_ratio": 55
        }
    
    @staticmethod
    def validate(specs: Dict[str, Any]) -> bool:
        """Validate visual specs structure."""
        required_keys = [
            "body_style_mesh_id",
            "paint_material_id",
            "wheel_id"
        ]
        return all(key in specs for key in required_keys)


# Export
__all__ = [
    "VehiclePlatform",
    "VehicleModel",
    "VehicleVisualSpecs"
]

