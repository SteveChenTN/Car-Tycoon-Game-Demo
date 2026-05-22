"""
财务系统模型
管理贷款、债券、税务等金融工具
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index, Enum
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any
import enum
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class LoanType(enum.Enum):
    """贷款类型"""
    BANK_SHORT_TERM = "BANK_SHORT_TERM"      # 银行短期贷款（1-2年）
    BANK_LONG_TERM = "BANK_LONG_TERM"        # 银行长期贷款（5-10年）
    CORPORATE_BOND = "CORPORATE_BOND"        # 企业债券
    GOVERNMENT_SUBSIDY = "GOVERNMENT_SUBSIDY"  # 政府补贴贷款（低息）
    PRIVATE_EQUITY = "PRIVATE_EQUITY"        # 私募股权


class LoanStatus(enum.Enum):
    """贷款状态"""
    PENDING = "PENDING"        # 待批准
    ACTIVE = "ACTIVE"          # 生效中
    DEFAULTED = "DEFAULTED"    # 违约
    PAID_OFF = "PAID_OFF"      # 已还清


class Loan(Base, TimestampMixin, BaseModel):
    """
    贷款记录模型
    记录公司的所有融资行为
    """
    __tablename__ = "loans"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 贷款基础信息 ====================
    loan_type = Column(
        Enum(LoanType), nullable=False,
        comment="贷款类型"
    )
    
    status = Column(
        Enum(LoanStatus), nullable=False, default=LoanStatus.PENDING,
        comment="贷款状态"
    )
    
    principal_amount = Column(
        Float, nullable=False,
        comment="本金金额（百万游戏币）"
    )
    
    remaining_principal = Column(
        Float, nullable=False,
        comment="剩余本金"
    )
    
    interest_rate = Column(
        Float, nullable=False,
        comment="年利率（如0.05表示5%）- 基于信用评级动态计算"
    )
    
    # ==================== 时间与期限 ====================
    issued_turn = Column(
        Integer, nullable=False,
        comment="发放回合"
    )
    
    maturity_turn = Column(
        Integer, nullable=False,
        comment="到期回合"
    )
    
    payment_frequency_turns = Column(
        Integer, nullable=False, default=12,
        comment="还款频率（每N回合还款一次，默认12=每季度）"
    )
    
    next_payment_turn = Column(
        Integer, nullable=False,
        comment="下次还款回合"
    )
    
    # ==================== 还款统计 ====================
    total_interest_paid = Column(
        Float, nullable=False, default=0.0,
        comment="累计已付利息"
    )
    
    total_principal_paid = Column(
        Float, nullable=False, default=0.0,
        comment="累计已还本金"
    )
    
    missed_payments = Column(
        Integer, nullable=False, default=0,
        comment="错过还款次数（触发违约）"
    )
    
    # ==================== 债券特有字段 ====================
    bond_face_value = Column(
        Float, nullable=True,
        comment="债券面值（仅债券类型）"
    )
    
    bond_coupon_rate = Column(
        Float, nullable=True,
        comment="票面利率（仅债券类型）"
    )
    
    bondholders_count = Column(
        Integer, nullable=True,
        comment="债券持有人数（仅债券类型）"
    )
    
    # ==================== 贷款条件 ====================
    collateral_description = Column(
        Text, nullable=True,
        comment="抵押品描述（如工厂、专利）"
    )
    
    covenant_rules = Column(
        Text, nullable=True,
        comment="贷款契约条款（JSON格式）- 如最低现金要求、负债率上限"
    )
    
    early_repayment_penalty = Column(
        Float, nullable=False, default=0.0,
        comment="提前还款罚金率（如0.02表示需付2%罚金）"
    )
    
    # ==================== 关系 ====================
    # company = relationship("Company", back_populates="loans")
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("principal_amount > 0", name="check_loan_principal"),
        CheckConstraint("remaining_principal >= 0", name="check_remaining_principal"),
        CheckConstraint("interest_rate >= 0 AND interest_rate <= 1.0", name="check_interest_rate"),
        CheckConstraint("maturity_turn > issued_turn", name="check_loan_maturity"),
        CheckConstraint("payment_frequency_turns > 0", name="check_payment_freq"),
        CheckConstraint("missed_payments >= 0", name="check_missed_payments"),
        CheckConstraint("early_repayment_penalty >= 0 AND early_repayment_penalty <= 0.5", name="check_penalty"),
        Index("idx_loan_company", "company_id"),
        Index("idx_loan_status", "status"),
        Index("idx_loan_next_payment", "next_payment_turn"),
    )
    
    def calculate_current_payment_amount(self) -> float:
        """
        计算当前应付金额（本金+利息）
        使用等额本息还款法
        """
        if self.remaining_principal <= 0:
            return 0.0
        
        # 计算剩余还款次数
        remaining_turns = self.maturity_turn - self.next_payment_turn
        remaining_payments = max(1, remaining_turns // self.payment_frequency_turns)
        
        # 每期利率
        period_rate = self.interest_rate * (self.payment_frequency_turns / 48)  # 假设48回合=1年
        
        if period_rate == 0:
            # 无息贷款
            return self.remaining_principal / remaining_payments
        
        # 等额本息公式: PMT = P * [r(1+r)^n] / [(1+r)^n - 1]
        numerator = self.remaining_principal * period_rate * ((1 + period_rate) ** remaining_payments)
        denominator = ((1 + period_rate) ** remaining_payments) - 1
        
        if denominator == 0:
            return self.remaining_principal
        
        return numerator / denominator
    
    def make_payment(self, payment_amount: float, current_turn: int) -> Dict[str, float]:
        """
        执行还款
        
        Args:
            payment_amount: 还款金额
            current_turn: 当前回合
        
        Returns:
            还款明细字典 {"principal": ..., "interest": ...}
        """
        if self.status != LoanStatus.ACTIVE:
            return {"principal": 0.0, "interest": 0.0}
        
        # 计算利息部分
        period_rate = self.interest_rate * (self.payment_frequency_turns / 48)
        interest_portion = self.remaining_principal * period_rate
        principal_portion = max(0, payment_amount - interest_portion)
        
        # 更新记录
        self.total_interest_paid += interest_portion
        self.total_principal_paid += principal_portion
        self.remaining_principal -= principal_portion
        
        # 更新下次还款时间
        self.next_payment_turn = current_turn + self.payment_frequency_turns
        
        # 检查是否已还清
        if self.remaining_principal <= 0.01:  # 容差
            self.remaining_principal = 0.0
            self.status = LoanStatus.PAID_OFF
        
        return {
            "principal": principal_portion,
            "interest": interest_portion
        }
    
    def mark_default(self) -> None:
        """标记为违约"""
        self.status = LoanStatus.DEFAULTED
        self.missed_payments += 1
    
    def get_covenant_rules(self) -> Dict[str, Any]:
        """获取贷款契约条款"""
        if not self.covenant_rules:
            return {}
        try:
            return json.loads(self.covenant_rules)
        except:
            return {}
    
    def set_covenant_rules(self, rules: Dict[str, Any]) -> None:
        """设置贷款契约条款"""
        self.covenant_rules = json.dumps(rules)
    
    def __repr__(self) -> str:
        return (f"<Loan(id={self.id}, company_id={self.company_id}, "
                f"type={self.loan_type.value}, principal={self.principal_amount:.1f}M, "
                f"remaining={self.remaining_principal:.1f}M, rate={self.interest_rate*100:.1f}%)>")


class TaxRecord(Base, TimestampMixin, BaseModel):
    """
    税务记录模型
    记录公司的税务支出历史
    """
    __tablename__ = "tax_records"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 税务信息 ====================
    tax_year = Column(Integer, nullable=False, comment="纳税年份")
    tax_quarter = Column(Integer, nullable=False, comment="纳税季度 1-4")
    
    region_code = Column(
        String(10), nullable=False,
        comment="税收区域代码"
    )
    
    # ==================== 税基与税额 ====================
    taxable_income = Column(
        Float, nullable=False,
        comment="应税收入（百万游戏币）"
    )
    
    corporate_tax_rate = Column(
        Float, nullable=False,
        comment="企业所得税率（当期适用）"
    )
    
    corporate_tax_paid = Column(
        Float, nullable=False,
        comment="已缴企业所得税"
    )
    
    # ==================== 其他税费 ====================
    payroll_tax_paid = Column(
        Float, nullable=False, default=0.0,
        comment="工资税"
    )
    
    property_tax_paid = Column(
        Float, nullable=False, default=0.0,
        comment="财产税（工厂、土地）"
    )
    
    import_duty_paid = Column(
        Float, nullable=False, default=0.0,
        comment="进口关税"
    )
    
    export_subsidy_received = Column(
        Float, nullable=False, default=0.0,
        comment="出口补贴（负税）"
    )
    
    rd_tax_credit = Column(
        Float, nullable=False, default=0.0,
        comment="研发税收抵免"
    )
    
    # ==================== 总计 ====================
    total_tax_paid = Column(
        Float, nullable=False,
        comment="当期总税款"
    )
    
    # ==================== 审计与合规 ====================
    is_audited = Column(
        Boolean, nullable=False, default=False,
        comment="是否被审计"
    )
    
    audit_penalty = Column(
        Float, nullable=False, default=0.0,
        comment="审计罚款（若有）"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("tax_quarter >= 1 AND tax_quarter <= 4", name="check_tax_quarter"),
        CheckConstraint("corporate_tax_rate >= 0 AND corporate_tax_rate <= 1.0", name="check_tax_rate"),
        CheckConstraint("total_tax_paid >= 0", name="check_total_tax"),
        Index("idx_tax_company_year", "company_id", "tax_year"),
        Index("idx_tax_region", "region_code"),
    )
    
    def __repr__(self) -> str:
        return (f"<TaxRecord(company_id={self.company_id}, "
                f"year={self.tax_year}Q{self.tax_quarter}, "
                f"region={self.region_code}, total={self.total_tax_paid:.1f}M)>")


__all__ = ["Loan", "LoanType", "LoanStatus", "TaxRecord"]


