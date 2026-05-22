"""
Supply chain and supplier relationship models.

Implements:
- PartSupplier: External suppliers of components/materials
- CompanySupplierRelation: Trust, contracts, and pricing relationships
- SupplierContract: Formal supply agreements with terms
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from backend.database import Base


class ContractStatus(Enum):
    """供应商合约状态枚举"""
    ACTIVE = "ACTIVE"           # 生效中
    EXPIRED = "EXPIRED"         # 已过期
    CANCELLED = "CANCELLED"     # 已取消
    BREACHED = "BREACHED"       # 已违约
    COMPLETED = "COMPLETED"     # 已完成


class PartSupplier(Base):
    """
    External supplier of parts/materials.
    
    Suppliers specialize in certain categories (e.g., "Electronics", "Engines")
    and have quality/reliability ratings that affect:
    - Delivered part quality
    - On-time delivery probability
    - Price competitiveness
    """
    __tablename__ = "part_suppliers"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # Identity
    name = Column(String(100), nullable=False)
    short_name = Column(String(20))
    founded_year = Column(Integer)
    
    # Location
    headquarters_region_id = Column(Integer, ForeignKey("regions.id"))
    
    # Specialty
    specialty = Column(String(50), nullable=False)  # "ENGINES", "ELECTRONICS", "STEEL", etc.
    sub_specialties = Column(Text)  # JSON array: ["TURBOCHARGERS", "FUEL_INJECTION"]
    
    # Capabilities
    quality_level = Column(Float, nullable=False, default=50.0)  # 0-100
    reliability_rating = Column(Float, nullable=False, default=50.0)  # 0-100 (delivery reliability)
    capacity_monthly = Column(Integer, nullable=False, default=10000)  # Units or kg
    min_order_quantity = Column(Integer, default=100)
    
    # Pricing
    base_cost_modifier = Column(Float, default=1.0)  # Multiplier on standard costs
    volume_discount_rate = Column(Float, default=0.0)  # Discount per 1000 units
    
    # Logistics
    lead_time_weeks = Column(Integer, default=4)
    ships_globally = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    bankruptcy_risk = Column(Float, default=0.0)  # 0-1 probability
    
    # Relationships
    headquarters_region = relationship("Region", foreign_keys=[headquarters_region_id])
    company_relations = relationship("CompanySupplierRelation", back_populates="supplier")
    contracts = relationship("SupplierContract", back_populates="supplier")
    
    def __repr__(self):
        return f"<PartSupplier(id={self.id}, name='{self.name}', specialty='{self.specialty}')>"
    
    def calculate_effective_price(self, base_price: float, order_quantity: int, 
                                 trust_level: float = 0.5) -> float:
        """
        Calculate the effective price for an order.
        
        Args:
            base_price: Base market price
            order_quantity: Number of units ordered
            trust_level: Relationship trust level (0-1)
        
        Returns:
            Final price per unit
        """
        # Base modifier
        price = base_price * self.base_cost_modifier
        
        # Volume discount
        if order_quantity > 1000:
            thousands = order_quantity / 1000.0
            discount = min(0.3, thousands * self.volume_discount_rate)
            price *= (1.0 - discount)
        
        # Trust discount (long-term relationships get better prices)
        trust_discount = trust_level * 0.15  # Up to 15% off
        price *= (1.0 - trust_discount)
        
        return price
    
    def get_delivery_risk(self, reliability: float = None) -> float:
        """
        Calculate probability of late/failed delivery.
        
        Args:
            reliability: Override reliability (default: use self.reliability_rating)
        
        Returns:
            Risk probability (0-1)
        """
        rel = reliability if reliability is not None else self.reliability_rating
        
        # Higher reliability = lower risk
        # 100 reliability = 1% risk
        # 50 reliability = 15% risk
        # 0 reliability = 50% risk
        base_risk = 0.5 - (rel / 100.0) * 0.49
        
        # Add bankruptcy risk
        total_risk = base_risk + (self.bankruptcy_risk * 0.3)
        
        return min(0.95, total_risk)


class CompanySupplierRelation(Base):
    """
    Relationship between a company and a supplier.
    
    Key mechanic: The longer you work with a supplier, the higher the trust_level,
    which unlocks better prices, priority during shortages, and flexible terms.
    """
    __tablename__ = "company_supplier_relations"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("part_suppliers.id", ondelete="CASCADE"), nullable=False)
    
    # Relationship metrics
    trust_level = Column(Float, nullable=False, default=0.3)  # 0-1, starts low
    relationship_age_months = Column(Integer, default=0)
    total_transactions = Column(Integer, default=0)
    total_value_transacted = Column(Float, default=0.0)
    
    # Performance tracking
    on_time_deliveries = Column(Integer, default=0)
    late_deliveries = Column(Integer, default=0)
    quality_issues = Column(Integer, default=0)
    
    # Current terms
    negotiated_discount_rate = Column(Float, default=0.0)  # Permanent discount earned
    priority_status = Column(Boolean, default=False)  # Get priority during shortages
    
    # Active contracts count
    active_contracts_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    relationship_quality = Column(String(20), default="NEW")  # NEW, GOOD, EXCELLENT, STRAINED, BROKEN
    
    # Relationships
    company = relationship("Company", back_populates="supplier_relations")
    supplier = relationship("PartSupplier", back_populates="company_relations")
    contracts = relationship("SupplierContract", back_populates="relation")
    
    def __repr__(self):
        return f"<CompanySupplierRelation(company_id={self.company_id}, supplier_id={self.supplier_id}, trust={self.trust_level:.2f})>"
    
    def update_trust_after_delivery(self, on_time: bool, quality_ok: bool):
        """
        Update trust level after a delivery.
        
        Args:
            on_time: Was the delivery on time?
            quality_ok: Was the quality acceptable?
        """
        if on_time:
            self.on_time_deliveries += 1
            self.trust_level = min(1.0, self.trust_level + 0.02)
        else:
            self.late_deliveries += 1
            self.trust_level = max(0.0, self.trust_level - 0.05)
        
        if not quality_ok:
            self.quality_issues += 1
            self.trust_level = max(0.0, self.trust_level - 0.08)
        
        self.total_transactions += 1
        self._update_relationship_quality()
    
    def increase_trust_over_time(self, months: int = 1):
        """
        Gradually increase trust through sustained relationship.
        
        Call this each turn for active relationships.
        """
        if self.is_active and self.total_transactions > 0:
            self.relationship_age_months += months
            
            # Gradual trust growth (slower at high levels)
            growth = 0.01 * (1.0 - self.trust_level)
            self.trust_level = min(1.0, self.trust_level + growth)
            
            self._update_relationship_quality()
    
    def _update_relationship_quality(self):
        """Update the qualitative relationship status."""
        if self.trust_level < 0.2:
            self.relationship_quality = "BROKEN"
        elif self.trust_level < 0.4:
            self.relationship_quality = "STRAINED"
        elif self.trust_level < 0.6:
            self.relationship_quality = "NEW"
        elif self.trust_level < 0.8:
            self.relationship_quality = "GOOD"
        else:
            self.relationship_quality = "EXCELLENT"
    
    def calculate_negotiated_discount(self) -> float:
        """
        Calculate the permanent discount rate earned through the relationship.
        
        Returns:
            Discount rate (0-0.20 = 0-20%)
        """
        # Base discount from trust
        base_discount = self.trust_level * 0.10  # Up to 10%
        
        # Volume bonus
        if self.total_value_transacted > 10_000_000:
            volume_bonus = 0.05
        elif self.total_value_transacted > 1_000_000:
            volume_bonus = 0.03
        else:
            volume_bonus = 0.0
        
        # Reliability bonus
        if self.total_transactions > 10:
            success_rate = self.on_time_deliveries / self.total_transactions
            if success_rate > 0.95:
                reliability_bonus = 0.05
            else:
                reliability_bonus = 0.0
        else:
            reliability_bonus = 0.0
        
        total_discount = base_discount + volume_bonus + reliability_bonus
        
        self.negotiated_discount_rate = min(0.20, total_discount)
        return self.negotiated_discount_rate


class SupplierContract(Base):
    """
    Formal supply contract with specific terms.
    
    Companies can negotiate contracts for:
    - Fixed pricing (hedge against price volatility)
    - Volume commitments (lower prices for guaranteed volume)
    - Priority supply (during shortages)
    """
    __tablename__ = "supplier_contracts"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    relation_id = Column(Integer, ForeignKey("company_supplier_relations.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("part_suppliers.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    # Contract terms
    contract_type = Column(String(30), nullable=False)  # SPOT, FIXED_PRICE, VOLUME_COMMITMENT, PRIORITY
    
    # Material/part specification
    material_type = Column(String(50))  # "STEEL", "ALUMINUM", etc.
    part_category = Column(String(50))  # "ENGINES", "TRANSMISSIONS", etc.
    
    # Pricing
    fixed_price_per_unit = Column(Float)  # For fixed-price contracts
    volume_discount_rate = Column(Float, default=0.0)
    
    # Volume
    monthly_volume_commitment = Column(Integer)  # Min units per month
    max_monthly_volume = Column(Integer)  # Max units supplier will provide
    
    # Duration
    start_turn = Column(Integer, nullable=False)
    end_turn = Column(Integer, nullable=False)
    auto_renew = Column(Boolean, default=False)
    
    # Performance
    total_units_delivered = Column(Integer, default=0)
    total_value = Column(Float, default=0.0)
    breaches = Column(Integer, default=0)  # Times contract was violated
    
    # Status
    status = Column(String(20), default="ACTIVE")  # ACTIVE, EXPIRED, CANCELLED, BREACHED
    
    # Penalties
    early_termination_penalty = Column(Float, default=0.0)
    breach_penalty_per_unit = Column(Float, default=0.0)
    
    # Relationships
    relation = relationship("CompanySupplierRelation", back_populates="contracts")
    supplier = relationship("PartSupplier", back_populates="contracts")
    
    def __repr__(self):
        return f"<SupplierContract(id={self.id}, type='{self.contract_type}', status='{self.status}')>"
    
    def is_active(self, current_turn: int) -> bool:
        """Check if contract is currently active."""
        return (
            self.status == "ACTIVE" and
            self.start_turn <= current_turn <= self.end_turn
        )
    
    def record_delivery(self, units: int, price_per_unit: float):
        """Record a delivery under this contract."""
        self.total_units_delivered += units
        self.total_value += units * price_per_unit
    
    def check_breach(self, current_turn: int, actual_volume: int) -> bool:
        """
        Check if company breached volume commitment.
        
        Returns:
            True if breached
        """
        if self.contract_type == "VOLUME_COMMITMENT":
            months_active = current_turn - self.start_turn + 1
            expected_volume = self.monthly_volume_commitment * months_active
            
            if self.total_units_delivered < expected_volume * 0.8:  # 80% threshold
                self.breaches += 1
                return True
        
        return False
    
    def calculate_termination_cost(self, current_turn: int) -> float:
        """Calculate cost to terminate contract early."""
        remaining_turns = self.end_turn - current_turn
        
        if remaining_turns <= 0:
            return 0.0
        
        # Base penalty
        base_penalty = self.early_termination_penalty
        
        # Additional penalty based on unfulfilled commitment
        if self.contract_type == "VOLUME_COMMITMENT":
            remaining_commitment = remaining_turns * self.monthly_volume_commitment
            commitment_value = remaining_commitment * (self.fixed_price_per_unit or 100.0)
            commitment_penalty = commitment_value * 0.15  # 15% of remaining value
        else:
            commitment_penalty = 0.0
        
        return base_penalty + commitment_penalty
    
    def calculate_monthly_payment(self) -> float:
        """
        计算本月应付金额
        
        Returns:
            应付金额
        """
        if not self.monthly_volume_commitment or not self.fixed_price_per_unit:
            return 0.0
        
        base_payment = self.monthly_volume_commitment * self.fixed_price_per_unit
        
        # 应用折扣
        if self.volume_discount_rate:
            base_payment *= (1.0 - self.volume_discount_rate)
        
        return base_payment
    
    def execute_monthly_delivery(self, current_turn: int) -> dict:
        """
        执行月度交付
        
        Args:
            current_turn: 当前回合数
        
        Returns:
            交付结果字典
        """
        if not self.is_active(current_turn):
            return {
                "success": False,
                "error": "Contract is not active"
            }
        
        # 记录交付
        delivery_units = self.monthly_volume_commitment or 0
        price_per_unit = self.fixed_price_per_unit or 0.0
        
        self.record_delivery(delivery_units, price_per_unit)
        
        # 检查是否完成
        if current_turn >= self.end_turn:
            self.status = ContractStatus.COMPLETED.value
        
        return {
            "success": True,
            "units_delivered": delivery_units,
            "total_cost": delivery_units * price_per_unit,
            "status": self.status
        }
    
    def breach_contract(self, current_turn: int, reason: str = "", penalty_rate: float = 0.3) -> float:
        """
        违约合约
        
        Args:
            current_turn: 当前回合数
            reason: 违约原因
            penalty_rate: 罚金比例
        
        Returns:
            罚金金额
        """
        self.status = ContractStatus.BREACHED.value
        self.breaches += 1
        
        # 计算罚金
        remaining_value = (self.end_turn - current_turn) * self.calculate_monthly_payment()
        penalty = remaining_value * penalty_rate
        
        return penalty


class MaterialMarket(Base):
    """
    原材料市场价格跟踪表
    
    跟踪全球和地区性原材料价格波动
    """
    __tablename__ = "material_markets"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)  # NULL表示全球价格
    
    # 材料类型
    material_type = Column(String(50), nullable=False)  # STEEL, ALUMINUM, PLASTIC等
    
    # 价格信息
    current_price_per_kg = Column(Float, nullable=False)
    historical_avg_price = Column(Float, nullable=False)  # 滚动12月平均价
    price_volatility = Column(Float, nullable=False, default=0.1)  # 波动指数 0-1
    
    # 供应水平
    supply_level = Column(Float, nullable=False, default=1.0)  # 0-2, 1.0=正常
    
    # 更新时间
    last_update_turn = Column(Integer, nullable=False)
    
    # 关系
    region = relationship("Region", foreign_keys=[region_id])
    
    def __repr__(self):
        location = f"Region {self.region_id}" if self.region_id else "Global"
        return f"<MaterialMarket({location}, {self.material_type}, ${self.current_price_per_kg:.2f}/kg)>"


__all__ = [
    "ContractStatus",
    "PartSupplier",
    "CompanySupplierRelation",
    "SupplierContract",
    "MaterialMarket"
]
