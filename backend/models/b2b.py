"""
B2B市场数据模型 - 企业间零部件交易

核心功能：
- 玩家可以发布自己的引擎/底盘设计到市场供其他公司采购
- AI竞争对手也可以发布产品
- 支持最小订购量（MOQ）约束
- 价格发现机制（供需影响价格）
"""
from sqlalchemy import (
    Column, Integer, Float, String, Boolean,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class ComponentListing(Base, TimestampMixin, BaseModel):
    """
    B2B零部件挂牌 - 企业间组件交易市场
    
    设计说明：
    - 卖方可以是玩家或AI公司
    - 支持引擎、底盘等核心零部件
    - 最小订购量（MOQ）防止小额订单
    - 可设置是否独家供应（防止技术扩散）
    """
    __tablename__ = "b2b_component_listings"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # ========== 卖方信息 ==========
    seller_company_id = Column(Integer, nullable=False,
                              comment="卖方公司ID（暂不使用外键，等companies表创建后再添加）")
    
    # ========== 零部件信息 ==========
    component_type = Column(
        String(20), nullable=False,
        comment="组件类型：ENGINE（引擎）/ CHASSIS（底盘）/ TRANSMISSION（变速箱）"
    )
    
    component_id = Column(Integer, nullable=False,
                         comment="组件ID - 对应engines.id或chassis.id等")
    
    # ========== 定价 ==========
    unit_price = Column(Float, nullable=False,
                       comment="单价（游戏币/件）")
    
    min_order_quantity = Column(Integer, nullable=False, default=100,
                               comment="最小订购量（MOQ）- 批量生产才划算")
    
    # ========== 供应状态 ==========
    available_quantity = Column(Integer, nullable=True,
                               comment="可供应数量 - NULL表示无限量供应")
    
    is_active = Column(Boolean, nullable=False, default=True,
                      comment="是否启用 - False表示下架")
    
    # ========== 商业条款 ==========
    is_exclusive = Column(Boolean, nullable=False, default=False,
                         comment="是否独家供应 - True表示只对特定客户开放")
    
    exclusive_buyer_company_id = Column(Integer, nullable=True,
                                       comment="独家买方公司ID - 仅在is_exclusive=True时有效")
    
    lead_time_weeks = Column(Integer, nullable=False, default=4,
                            comment="交货周期（周）")
    
    # ========== 销售统计 ==========
    total_sold_quantity = Column(Integer, nullable=False, default=0,
                                comment="累计销售数量")
    
    last_sale_turn = Column(Integer, nullable=True,
                           comment="最后一次销售的回合数")
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="check_positive_price"),
        CheckConstraint("min_order_quantity > 0", name="check_positive_moq"),
        CheckConstraint("available_quantity IS NULL OR available_quantity >= 0", 
                       name="check_nonnegative_quantity"),
        CheckConstraint("lead_time_weeks >= 0", name="check_nonnegative_lead_time"),
        Index("idx_b2b_seller", "seller_company_id"),
        Index("idx_b2b_component", "component_type", "component_id"),
        Index("idx_b2b_active", "is_active"),
        Index("idx_b2b_exclusive", "is_exclusive", "exclusive_buyer_company_id"),
    )
    
    @validates("component_type")
    def validate_component_type(self, key: str, value: str) -> str:
        """验证组件类型"""
        allowed = ["ENGINE", "CHASSIS", "TRANSMISSION", "SUSPENSION"]
        if value.upper() not in allowed:
            raise ValueError(f"组件类型必须是以下之一: {allowed}")
        return value.upper()
    
    def can_purchase(self, buyer_company_id: int, quantity: int) -> tuple[bool, str]:
        """
        检查买方是否可以购买
        
        Args:
            buyer_company_id: 买方公司ID
            quantity: 购买数量
        
        Returns:
            (可以购买, 错误信息)
        """
        if not self.is_active:
            return False, "该产品已下架"
        
        if quantity < self.min_order_quantity:
            return False, f"订购数量必须 >= {self.min_order_quantity} 件（MOQ）"
        
        if self.available_quantity is not None:
            if quantity > self.available_quantity:
                return False, f"库存不足，仅剩 {self.available_quantity} 件"
        
        if self.is_exclusive:
            if self.exclusive_buyer_company_id != buyer_company_id:
                return False, "该产品为独家供应，您无权采购"
        
        # 防止自己买自己的产品（虽然理论上可以用于转移库存，但简化处理）
        if self.seller_company_id == buyer_company_id:
            return False, "不能采购自己发布的产品"
        
        return True, "可以购买"
    
    def record_sale(self, quantity: int, current_turn: int) -> None:
        """
        记录销售
        
        Args:
            quantity: 销售数量
            current_turn: 当前回合数
        """
        self.total_sold_quantity += quantity
        self.last_sale_turn = current_turn
        
        if self.available_quantity is not None:
            self.available_quantity -= quantity
            if self.available_quantity <= 0:
                self.is_active = False  # 自动下架
    
    def to_dict(self) -> Dict[str, Any]:
        """扩展基类方法"""
        base_dict = super().to_dict()
        base_dict.update({
            "availability_status": "无限量" if self.available_quantity is None else f"{self.available_quantity} 件",
            "exclusivity": "独家" if self.is_exclusive else "公开",
        })
        return base_dict
    
    def __repr__(self) -> str:
        return (f"<ComponentListing(type={self.component_type}, "
                f"component_id={self.component_id}, "
                f"seller={self.seller_company_id}, "
                f"price=${self.unit_price:,.0f}, "
                f"MOQ={self.min_order_quantity})>")


class B2BTransaction(Base, TimestampMixin, BaseModel):
    """
    B2B交易记录 - 企业间零部件交易历史
    
    用途：
    - 记录所有B2B采购历史
    - 用于生成财务报表和市场分析
    - AI可以分析交易历史优化采购策略
    """
    __tablename__ = "b2b_transactions"
    
    # ========== 基础信息 ==========
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    listing_id = Column(Integer, ForeignKey("b2b_component_listings.id", ondelete="SET NULL"), 
                       nullable=True,
                       comment="挂牌ID - 可能已被删除")
    
    # ========== 交易双方 ==========
    seller_company_id = Column(Integer, nullable=False)
    buyer_company_id = Column(Integer, nullable=False)
    
    # ========== 交易内容 ==========
    component_type = Column(String(20), nullable=False)
    component_id = Column(Integer, nullable=False)
    
    quantity = Column(Integer, nullable=False,
                     comment="交易数量")
    
    unit_price = Column(Float, nullable=False,
                       comment="成交单价")
    
    total_amount = Column(Float, nullable=False,
                         comment="总金额")
    
    # ========== 交货信息 ==========
    delivery_factory_id = Column(Integer, ForeignKey("factories.id", ondelete="SET NULL"),
                                nullable=True,
                                comment="交货工厂ID")
    
    transaction_turn = Column(Integer, nullable=False,
                            comment="交易发生的回合数")
    
    expected_delivery_turn = Column(Integer, nullable=False,
                                   comment="预计交货回合数")
    
    actual_delivery_turn = Column(Integer, nullable=True,
                                 comment="实际交货回合数 - NULL表示未交货")
    
    # ========== 状态 ==========
    status = Column(
        String(20), nullable=False, default="PENDING",
        comment="交易状态：PENDING（待交货）/ DELIVERED（已交货）/ CANCELLED（已取消）"
    )
    
    # ========== 约束 ==========
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_positive_quantity"),
        CheckConstraint("unit_price > 0", name="check_positive_unit_price"),
        CheckConstraint("total_amount > 0", name="check_positive_total"),
        Index("idx_transaction_buyer", "buyer_company_id"),
        Index("idx_transaction_seller", "seller_company_id"),
        Index("idx_transaction_turn", "transaction_turn"),
        Index("idx_transaction_status", "status"),
    )
    
    # ========== 关系 ==========
    listing = relationship("ComponentListing", foreign_keys=[listing_id])
    delivery_factory = relationship("Factory", foreign_keys=[delivery_factory_id])
    
    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        """验证交易状态"""
        allowed = ["PENDING", "DELIVERED", "CANCELLED"]
        if value.upper() not in allowed:
            raise ValueError(f"交易状态必须是以下之一: {allowed}")
        return value.upper()
    
    def __repr__(self) -> str:
        return (f"<B2BTransaction(buyer={self.buyer_company_id}, "
                f"seller={self.seller_company_id}, "
                f"type={self.component_type}, "
                f"qty={self.quantity}, "
                f"amount=${self.total_amount:,.0f}, "
                f"status={self.status})>")


# 导出模型
__all__ = ["ComponentListing", "B2BTransaction"]


