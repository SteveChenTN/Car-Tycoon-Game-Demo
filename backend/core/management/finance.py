"""
财务系统业务逻辑
处理贷款申请、还款、税务计算等财务操作
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from backend.models.company import Company
from backend.models.finance import Loan, LoanType, LoanStatus, TaxRecord
from backend.models.game_state import GameState
from backend.models.region import Region

logger = logging.getLogger(__name__)


class FinanceLogic:
    """财务系统核心逻辑"""
    
    # 基准利率（将根据信用评级调整）
    BASE_INTEREST_RATES = {
        LoanType.BANK_SHORT_TERM: 0.05,      # 5%
        LoanType.BANK_LONG_TERM: 0.06,       # 6%
        LoanType.CORPORATE_BOND: 0.07,       # 7%
        LoanType.GOVERNMENT_SUBSIDY: 0.02,   # 2% (政府补贴)
        LoanType.PRIVATE_EQUITY: 0.15        # 15% (高风险高回报)
    }
    
    # 信用评级利率调整（百分点）
    CREDIT_RATING_ADJUSTMENTS = {
        "AAA": -0.015,  # -1.5%
        "AA": -0.010,   # -1.0%
        "A": -0.005,    # -0.5%
        "BBB": 0.000,   # 基准
        "BB": 0.010,    # +1.0%
        "B": 0.020,     # +2.0%
        "CCC": 0.035,   # +3.5%
        "CC": 0.050,    # +5.0%
        "C": 0.075,     # +7.5%
        "D": 0.100      # +10.0% (几乎不可能获批)
    }
    
    def __init__(self, db: Session):
        """
        初始化财务逻辑
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def apply_for_loan(
        self,
        company_id: int,
        loan_type: LoanType,
        principal_amount: float,
        duration_turns: int,
        payment_frequency_turns: int = 12
    ) -> Dict[str, Any]:
        """
        申请贷款
        
        Args:
            company_id: 公司ID
            loan_type: 贷款类型
            principal_amount: 本金金额（百万游戏币）
            duration_turns: 贷款期限（回合）
            payment_frequency_turns: 还款频率（每N回合还款一次）
        
        Returns:
            结果字典 {"success": bool, "loan_id": int, "interest_rate": float, ...}
        """
        try:
            # 获取公司信息
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return {"success": False, "error": "Company not found"}
            
            # 获取游戏状态
            game_state = self.db.query(GameState).filter(
                GameState.id == company.game_id
            ).first()
            if not game_state:
                return {"success": False, "error": "Game state not found"}
            
            # 更新公司信用评级
            company.update_credit_score()
            
            # 检查信用资格
            if company.credit_rating in ["D", "C"] and loan_type != LoanType.PRIVATE_EQUITY:
                return {
                    "success": False,
                    "error": f"Credit rating {company.credit_rating} too low for this loan type"
                }
            
            # 计算利率
            interest_rate = self._calculate_interest_rate(loan_type, company.credit_rating)
            
            # 检查债务比率（防止过度负债）
            projected_debt = company.total_debt + principal_amount
            projected_debt_ratio = projected_debt / max(company.total_assets, 1.0)
            
            if projected_debt_ratio > 0.9:  # 负债率超过90%
                return {
                    "success": False,
                    "error": f"Debt ratio too high ({projected_debt_ratio*100:.1f}%), loan denied"
                }
            
            # 创建贷款记录
            loan = Loan(
                game_id=company.game_id,
                company_id=company_id,
                loan_type=loan_type,
                status=LoanStatus.ACTIVE,
                principal_amount=principal_amount,
                remaining_principal=principal_amount,
                interest_rate=interest_rate,
                issued_turn=game_state.turn_number,
                maturity_turn=game_state.turn_number + duration_turns,
                payment_frequency_turns=payment_frequency_turns,
                next_payment_turn=game_state.turn_number + payment_frequency_turns
            )
            
            # 更新公司财务
            company.cash += principal_amount
            company.total_debt += principal_amount
            company.update_credit_score()  # 重新计算信用评级
            
            self.db.add(loan)
            self.db.commit()
            self.db.refresh(loan)
            
            logger.info(
                f"公司 {company.name} 获得 {loan_type.value} 贷款: "
                f"{principal_amount:.1f}M @ {interest_rate*100:.2f}%"
            )
            
            return {
                "success": True,
                "loan_id": loan.id,
                "principal": principal_amount,
                "interest_rate": interest_rate,
                "maturity_turn": loan.maturity_turn,
                "monthly_payment": loan.calculate_current_payment_amount()
            }
            
        except Exception as e:
            logger.error(f"申请贷款失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def process_loan_payments(self, current_turn: int) -> Dict[str, Any]:
        """
        处理所有到期的贷款还款
        
        Args:
            current_turn: 当前回合
        
        Returns:
            处理结果统计
        """
        try:
            # 查询所有需要还款的活跃贷款
            active_loans = self.db.query(Loan).filter(
                Loan.status == LoanStatus.ACTIVE,
                Loan.next_payment_turn <= current_turn
            ).all()
            
            results = {
                "total_loans": len(active_loans),
                "successful_payments": 0,
                "defaults": 0,
                "paid_off": 0,
                "total_paid": 0.0
            }
            
            for loan in active_loans:
                company = self.db.query(Company).filter(Company.id == loan.company_id).first()
                if not company:
                    continue
                
                payment_amount = loan.calculate_current_payment_amount()
                
                # 检查公司是否有足够现金
                if company.cash >= payment_amount:
                    # 执行还款
                    payment_details = loan.make_payment(payment_amount, current_turn)
                    company.cash -= payment_amount
                    company.total_debt = loan.remaining_principal
                    
                    results["successful_payments"] += 1
                    results["total_paid"] += payment_amount
                    
                    if loan.status == LoanStatus.PAID_OFF:
                        results["paid_off"] += 1
                        logger.info(f"公司 {company.name} 还清贷款 #{loan.id}")
                    
                else:
                    # 逾期未还
                    loan.mark_default()
                    results["defaults"] += 1
                    
                    # 信用评级惩罚
                    company.credit_score = max(0, company.credit_score - 10)
                    company.update_credit_score()
                    
                    logger.warning(
                        f"公司 {company.name} 贷款 #{loan.id} 违约! "
                        f"需付 {payment_amount:.1f}M, 现金仅 {company.cash:.1f}M"
                    )
            
            self.db.commit()
            
            logger.info(
                f"回合 {current_turn} 贷款还款处理完成: "
                f"{results['successful_payments']}/{results['total_loans']} 成功, "
                f"{results['defaults']} 违约"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"处理贷款还款失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def calculate_taxes(
        self,
        company_id: int,
        taxable_income: float,
        region_code: str,
        tax_year: int,
        tax_quarter: int
    ) -> Dict[str, Any]:
        """
        计算并记录税务
        
        Args:
            company_id: 公司ID
            taxable_income: 应税收入
            region_code: 税收区域
            tax_year: 纳税年份
            tax_quarter: 纳税季度
        
        Returns:
            税务计算结果
        """
        try:
            # 获取地区税率
            region = self.db.query(Region).filter(
                Region.code == region_code
            ).first()
            
            if not region:
                return {"success": False, "error": "Region not found"}
            
            corporate_tax_rate = region.corporate_tax_rate
            
            # 计算企业所得税
            corporate_tax = max(0, taxable_income * corporate_tax_rate)
            
            # TODO: 可以添加更复杂的税务计算
            # - 工资税（基于员工数量）
            # - 财产税（基于工厂资产）
            # - 研发税收抵免
            
            payroll_tax = 0.0  # 暂时简化
            property_tax = 0.0
            rd_tax_credit = 0.0
            
            total_tax = corporate_tax + payroll_tax + property_tax - rd_tax_credit
            
            # 创建税务记录
            tax_record = TaxRecord(
                game_id=self.db.query(Company).filter(
                    Company.id == company_id
                ).first().game_id,
                company_id=company_id,
                tax_year=tax_year,
                tax_quarter=tax_quarter,
                region_code=region_code,
                taxable_income=taxable_income,
                corporate_tax_rate=corporate_tax_rate,
                corporate_tax_paid=corporate_tax,
                payroll_tax_paid=payroll_tax,
                property_tax_paid=property_tax,
                rd_tax_credit=rd_tax_credit,
                total_tax_paid=total_tax
            )
            
            self.db.add(tax_record)
            
            # 扣除公司现金
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if company:
                company.cash -= total_tax
            
            self.db.commit()
            
            logger.info(
                f"公司 {company.name} {tax_year}Q{tax_quarter} 纳税: "
                f"{total_tax:.1f}M (税率 {corporate_tax_rate*100:.1f}%)"
            )
            
            return {
                "success": True,
                "total_tax": total_tax,
                "corporate_tax": corporate_tax,
                "effective_rate": corporate_tax_rate
            }
            
        except Exception as e:
            logger.error(f"计算税务失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _calculate_interest_rate(self, loan_type: LoanType, credit_rating: str) -> float:
        """
        计算贷款利率
        
        Args:
            loan_type: 贷款类型
            credit_rating: 信用评级
        
        Returns:
            年利率
        """
        base_rate = self.BASE_INTEREST_RATES.get(loan_type, 0.08)
        adjustment = self.CREDIT_RATING_ADJUSTMENTS.get(credit_rating, 0.0)
        
        final_rate = base_rate + adjustment
        
        # 确保利率在合理范围内
        return max(0.01, min(0.30, final_rate))
    
    def get_company_financial_summary(self, company_id: int) -> Dict[str, Any]:
        """
        获取公司财务摘要
        
        Args:
            company_id: 公司ID
        
        Returns:
            财务摘要字典
        """
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return {"success": False, "error": "Company not found"}
            
            # 统计贷款
            active_loans = self.db.query(Loan).filter(
                Loan.company_id == company_id,
                Loan.status == LoanStatus.ACTIVE
            ).all()
            
            total_loan_count = len(active_loans)
            total_interest_expense = sum(
                loan.remaining_principal * loan.interest_rate
                for loan in active_loans
            )
            
            # 计算下季度应付款项
            upcoming_payments = sum(
                loan.calculate_current_payment_amount()
                for loan in active_loans
            )
            
            return {
                "success": True,
                "cash": company.cash,
                "total_debt": company.total_debt,
                "debt_ratio": company.calculate_debt_ratio(),
                "credit_rating": company.credit_rating,
                "credit_score": company.credit_score,
                "active_loan_count": total_loan_count,
                "annual_interest_expense": total_interest_expense,
                "upcoming_payments": upcoming_payments,
                "bankruptcy_risk": company.bankruptcy_risk
            }
            
        except Exception as e:
            logger.error(f"获取财务摘要失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


__all__ = ["FinanceLogic"]


