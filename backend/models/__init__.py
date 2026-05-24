"""
数据模型导出
"""
from backend.models.base import TimestampMixin, BaseModel
from backend.models.game_state import GameState
from backend.models.region import Region
from backend.models.engineering import Engine, Chassis, CarTrim
from backend.models.production import (
    Factory, MaterialMarket, Inventory, ProductionLine,
    FactoryType, MaterialType, ProcurementPolicy
)
from backend.models.b2b import ComponentListing, B2BTransaction
from backend.models.market import (
    DistributionNetwork, MarketingCampaign, BrandPerception,
    ConsumerBucket, IntelligenceReport,
    DistributionType, MarketingFocus, ConsumerSegment
)
from backend.models.company import Company
from backend.models.finance import Loan, LoanType, LoanStatus, TaxRecord
from backend.models.legal import (
    Regulation, RegulationType,
    VehicleCompliance, ComplianceStatus,
    RecallEvent
)
from backend.models.testing import (
    PrototypeProject, TestingPhase, TestingStatus,
    TestingFacility
)
from backend.models.events import (
    GameEvent, EventType, EventSeverity, EventStatus,
    EventTemplate
)
from backend.models.game_manager import EventLog, GameConfig
from backend.models.technology import TechNode, CompanyTechnology
from backend.models.ai_decision import AIDecisionQueue
from backend.models.staff import Staff
from backend.models.directive import Directive
from backend.models.diplomacy import CompetitorRelation, DiplomaticAction, Patent
from backend.models.history import (
    SalesHistory, FinancialHistory, MarketDemandHistory, UsedCarInventory
)
from backend.models.inventory import (
    FactoryInventory, DealershipInventory, ShipmentLog
)
from backend.models.supply import (
    SupplierContract, MaterialMarket as MaterialMarketSupply
)
from backend.models.production_history import ProductionHistory
from backend.models.engineering_familiarity import EngineeringFamiliarity
from backend.models.factory_familiarity import (
    FactoryProcessFamiliarity, FactoryMaterialFamiliarity
)

__all__ = [
    "TimestampMixin",
    "BaseModel",
    "GameState",
    "Region",
    "Engine",
    "Chassis",
    "CarTrim",
    "Factory",
    "MaterialMarket",
    "Inventory",
    "ProductionLine",
    "FactoryType",
    "MaterialType",
    "ProcurementPolicy",
    "ComponentListing",
    "B2BTransaction",
    "DistributionNetwork",
    "MarketingCampaign",
    "BrandPerception",
    "ConsumerBucket",
    "IntelligenceReport",
    "DistributionType",
    "MarketingFocus",
    "ConsumerSegment",
    "Company",
    "Loan",
    "LoanType",
    "LoanStatus",
    "TaxRecord",
    "Regulation",
    "RegulationType",
    "VehicleCompliance",
    "ComplianceStatus",
    "RecallEvent",
    "PrototypeProject",
    "TestingPhase",
    "TestingStatus",
    "TestingFacility",
    "GameEvent",
    "EventType",
    "EventSeverity",
    "EventStatus",
    "EventTemplate",
    "EventLog",
    "GameConfig",
    "TechNode",
    "CompanyTechnology",
    "AIDecisionQueue",
    "Staff",
    "Directive",
    "CompetitorRelation",
    "DiplomaticAction",
    "Patent",
    "SalesHistory",
    "FinancialHistory",
    "MarketDemandHistory",
    "UsedCarInventory",
    "FactoryInventory",
    "DealershipInventory",
    "ShipmentLog",
    "SupplierContract",
    "MaterialMarketSupply",
    "ProductionHistory",
    "EngineeringFamiliarity",
    "FactoryProcessFamiliarity",
    "FactoryMaterialFamiliarity"
]
