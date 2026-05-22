"""
Inventory models: Factory vs Dealership split.

Implements two-tier inventory system:
1. FactoryInventory: Cars sitting at factory gate (not yet shipped)
2. DealershipInventory: Cars at dealerships, ready for sale

Logistics: Moving cars Factory → Dealership takes time and costs money.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class FactoryInventory(Base):
    """
    Factory-level inventory - finished cars waiting at the factory.
    
    These cars have been produced but not yet shipped to dealerships.
    Holding inventory here costs money (storage, depreciation risk).
    """
    __tablename__ = "factory_inventory"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    factory_id = Column(Integer, ForeignKey("factories.id"), nullable=False)
    car_trim_id = Column(Integer, ForeignKey("car_trims.id"), nullable=False)
    
    # Quantity
    quantity = Column(Integer, nullable=False, default=0)
    
    # Age tracking (for holding cost calculation)
    produced_turn = Column(Integer, nullable=False)
    avg_age_turns = Column(Float, default=0.0)  # Average age of units in inventory
    
    # Costs
    unit_production_cost = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)  # quantity * unit_cost
    
    # Holding costs
    storage_cost_per_turn = Column(Float, default=5.0)  # $ per unit per turn
    accumulated_holding_cost = Column(Float, default=0.0)
    
    # Relationships
    factory = relationship("Factory", foreign_keys=[factory_id])
    car_trim = relationship("CarTrim", foreign_keys=[car_trim_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_factory_inv_factory", "factory_id"),
        Index("idx_factory_inv_trim", "car_trim_id"),
        Index("idx_factory_inv_game", "game_id"),
    )
    
    def update_value(self):
        """Recalculate total value based on quantity and unit cost."""
        self.total_value = self.quantity * self.unit_production_cost
    
    def add_units(self, quantity: int, turn: int):
        """
        Add newly produced units.
        
        Args:
            quantity: Number of units to add
            turn: Current turn number
        """
        # Update average age weighted by quantity
        if self.quantity > 0:
            total_age = self.avg_age_turns * self.quantity
            new_total_age = total_age  # Existing units age
            self.avg_age_turns = new_total_age / (self.quantity + quantity)
        else:
            self.avg_age_turns = 0.0
        
        self.quantity += quantity
        self.update_value()
    
    def remove_units(self, quantity: int) -> bool:
        """
        Remove units (for shipping to dealerships).
        
        Returns:
            True if successful, False if insufficient inventory
        """
        if quantity > self.quantity:
            return False
        
        self.quantity -= quantity
        self.update_value()
        return True
    
    def accrue_holding_costs(self, turns: int = 1):
        """Accrue holding costs for inventory aging."""
        holding_cost = self.quantity * self.storage_cost_per_turn * turns
        self.accumulated_holding_cost += holding_cost
        self.avg_age_turns += turns
    
    def __repr__(self):
        return f"<FactoryInventory(factory_id={self.factory_id}, trim_id={self.car_trim_id}, qty={self.quantity})>"


class DealershipInventory(Base):
    """
    Dealership-level inventory - cars available for sale in a region.
    
    These cars have been shipped from factory and are ready for customers.
    Dealerships handle pricing (MSRP + discounts), financing, trade-ins.
    """
    __tablename__ = "dealership_inventory"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    car_trim_id = Column(Integer, ForeignKey("car_trims.id"), nullable=False)
    company_id = Column(Integer, nullable=False)  # Owner company (TODO: FK when companies ready)
    
    # Quantity
    quantity_new = Column(Integer, nullable=False, default=0)
    quantity_in_transit = Column(Integer, default=0)  # Shipped but not arrived
    
    # Arrival tracking
    expected_arrival_turn = Column(Integer)  # When in-transit units arrive
    
    # Pricing
    current_msrp = Column(Float, nullable=False)
    current_discount_percent = Column(Float, default=0.0)  # 0-100
    effective_price = Column(Float, nullable=False)  # MSRP * (1 - discount)
    
    # Inventory age (for incentive calculation)
    avg_days_in_inventory = Column(Float, default=0.0)
    oldest_unit_age_turns = Column(Integer, default=0)
    
    # Sales metrics (for demand forecasting)
    units_sold_last_turn = Column(Integer, default=0)
    units_sold_last_month = Column(Integer, default=0)
    
    # Holding costs
    dealership_holding_cost_per_unit = Column(Float, default=50.0)  # $ per unit per turn
    total_holding_cost = Column(Float, default=0.0)
    
    # Status
    last_restocked_turn = Column(Integer)
    is_stocked = Column(Boolean, default=True)  # False if out of stock
    
    # Relationships
    region = relationship("Region", foreign_keys=[region_id])
    car_trim = relationship("CarTrim", foreign_keys=[car_trim_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_dealer_inv_region", "region_id"),
        Index("idx_dealer_inv_trim", "car_trim_id"),
        Index("idx_dealer_inv_company", "company_id"),
        Index("idx_dealer_inv_stocked", "is_stocked"),
        Index("idx_dealer_inv_composite", "region_id", "car_trim_id"),
    )
    
    def update_effective_price(self):
        """Recalculate effective price after discount changes."""
        self.effective_price = self.current_msrp * (1.0 - self.current_discount_percent / 100.0)
    
    def add_units_in_transit(self, quantity: int, arrival_turn: int):
        """
        Add units that have been shipped but not arrived.
        
        Args:
            quantity: Number of units shipped
            arrival_turn: Turn when they will arrive
        """
        self.quantity_in_transit += quantity
        self.expected_arrival_turn = arrival_turn
    
    def receive_shipment(self, quantity: int, current_turn: int):
        """
        Receive a shipment from factory.
        
        Args:
            quantity: Number of units arriving
            current_turn: Current turn number
        """
        # Move from in-transit to new
        shipment_size = min(quantity, self.quantity_in_transit)
        self.quantity_in_transit -= shipment_size
        self.quantity_new += shipment_size
        
        self.last_restocked_turn = current_turn
        self.is_stocked = True
    
    def sell_units(self, quantity: int) -> bool:
        """
        Sell units to customers.
        
        Returns:
            True if successful, False if insufficient inventory
        """
        if quantity > self.quantity_new:
            return False
        
        self.quantity_new -= quantity
        self.units_sold_last_turn += quantity
        
        if self.quantity_new == 0:
            self.is_stocked = False
        
        return True
    
    def apply_discount(self, discount_percent: float):
        """
        Apply a discount to stimulate sales.
        
        Args:
            discount_percent: Discount percentage (0-100)
        """
        self.current_discount_percent = max(0.0, min(100.0, discount_percent))
        self.update_effective_price()
    
    def accrue_holding_costs(self, turns: int = 1):
        """Accrue holding costs for unsold inventory."""
        cost = self.quantity_new * self.dealership_holding_cost_per_unit * turns
        self.total_holding_cost += cost
        self.avg_days_in_inventory += turns
        self.oldest_unit_age_turns += turns
    
    def calculate_incentive_recommendation(self) -> float:
        """
        Calculate recommended discount based on inventory age.
        
        Returns:
            Recommended discount percentage (0-30)
        """
        # Old inventory → increase discount
        if self.oldest_unit_age_turns > 12:  # > 1 year
            return 25.0
        elif self.oldest_unit_age_turns > 6:  # > 6 months
            return 15.0
        elif self.oldest_unit_age_turns > 3:  # > 3 months
            return 5.0
        else:
            return 0.0
    
    def __repr__(self):
        return f"<DealershipInventory(region_id={self.region_id}, trim_id={self.car_trim_id}, qty={self.quantity_new}, in_transit={self.quantity_in_transit})>"


class ShipmentLog(Base):
    """
    Track shipments from factories to dealerships.
    
    Implements logistics simulation:
    - Transit time based on distance
    - Cost based on quantity and distance
    - Tracking of in-flight inventory
    """
    __tablename__ = "shipment_logs"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # Route
    factory_id = Column(Integer, ForeignKey("factories.id"), nullable=False)
    destination_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    
    # Cargo
    car_trim_id = Column(Integer, ForeignKey("car_trims.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Timeline
    shipped_turn = Column(Integer, nullable=False)
    estimated_arrival_turn = Column(Integer, nullable=False)
    actual_arrival_turn = Column(Integer)
    
    # Costs
    shipping_cost_total = Column(Float, nullable=False)
    shipping_cost_per_unit = Column(Float, nullable=False)
    
    # Status
    status = Column(String(20), default="IN_TRANSIT")  # IN_TRANSIT, DELIVERED, CANCELLED
    
    # Incidents (optional)
    delay_turns = Column(Integer, default=0)
    damage_quantity = Column(Integer, default=0)
    incident_description = Column(String(200))
    
    # Relationships
    factory = relationship("Factory", foreign_keys=[factory_id])
    region = relationship("Region", foreign_keys=[destination_region_id])
    car_trim = relationship("CarTrim", foreign_keys=[car_trim_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_shipment_factory", "factory_id"),
        Index("idx_shipment_region", "destination_region_id"),
        Index("idx_shipment_status", "status"),
        Index("idx_shipment_arrival", "estimated_arrival_turn"),
    )
    
    def mark_delivered(self, current_turn: int, damage: int = 0):
        """
        Mark shipment as delivered.
        
        Args:
            current_turn: Current turn number
            damage: Number of units damaged in transit
        """
        self.status = "DELIVERED"
        self.actual_arrival_turn = current_turn
        self.damage_quantity = damage
        
        if current_turn > self.estimated_arrival_turn:
            self.delay_turns = current_turn - self.estimated_arrival_turn
    
    def __repr__(self):
        return f"<ShipmentLog(id={self.id}, factory→region={self.factory_id}→{self.destination_region_id}, qty={self.quantity}, status={self.status})>"


# Export
__all__ = [
    "FactoryInventory",
    "DealershipInventory",
    "ShipmentLog"
]


