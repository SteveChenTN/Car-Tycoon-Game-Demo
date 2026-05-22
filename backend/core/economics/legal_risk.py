"""
法律风险检查系统
处理克隆底盘在竞争对手所在区域销售时的法律风险
"""
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
import random

from backend.models.engineering import Chassis, ChassisSourceType, CarTrim
from backend.models.company import Company
from backend.models.region import Region
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class LegalRiskService:
    """法律风险服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger("LegalRisk")
    
    def check_legal_risk_on_sale(
        self,
        cloned_chassis_id: int,
        selling_region_id: int,
        company_id: int
    ) -> Tuple[bool, float, Dict[str, any]]:
        """
        检查克隆底盘在指定区域销售时的法律风险
        
        Args:
            cloned_chassis_id: 克隆底盘ID
            selling_region_id: 销售区域ID
            company_id: 销售公司ID
        
        Returns:
            (是否触发风险, 风险概率, 风险详情)
        """
        chassis = self.db.query(Chassis).filter(
            Chassis.id == cloned_chassis_id,
            Chassis.source_type == ChassisSourceType.CLONED
        ).first()
        
        if not chassis:
            return False, 0.0, {}
        
        if not chassis.original_competitor_id:
            return False, 0.0, {}
        
        # 获取原始竞争对手车辆
        original_car = self.db.query(CarTrim).filter(
            CarTrim.id == chassis.original_competitor_id
        ).first()
        
        if not original_car:
            return False, 0.0, {}
        
        # 获取竞争对手公司
        competitor_company = self.db.query(Company).filter(
            Company.id == original_car.company_id
        ).first()
        
        if not competitor_company:
            return False, 0.0, {}
        
        # 检查竞争对手总部区域
        competitor_region_code = competitor_company.headquarters_region
        
        # 获取销售区域
        selling_region = self.db.query(Region).filter(
            Region.id == selling_region_id
        ).first()
        
        if not selling_region:
            return False, 0.0, {}
        
        # 计算区域匹配度
        region_match = 1.0 if selling_region.code == competitor_region_code else 0.5
        
        # 计算触发概率 = 法律风险系数 * 区域匹配度
        trigger_probability = chassis.legal_risk_factor * region_match
        
        # 随机检查是否触发
        triggered = random.random() < trigger_probability
        
        risk_details = {
            "cloned_chassis_id": cloned_chassis_id,
            "original_car_id": chassis.original_competitor_id,
            "original_car_name": original_car.name,
            "competitor_company_id": competitor_company.id,
            "competitor_company_name": competitor_company.name,
            "selling_region_id": selling_region_id,
            "selling_region_code": selling_region.code,
            "competitor_region_code": competitor_region_code,
            "region_match": region_match,
            "legal_risk_factor": chassis.legal_risk_factor,
            "trigger_probability": trigger_probability,
            "triggered": triggered
        }
        
        if triggered:
            self.logger.warning(
                f"法律风险触发！公司 {company_id} 在区域 {selling_region.code} "
                f"销售克隆底盘 {chassis.code}，竞争对手: {competitor_company.name}"
            )
        
        return triggered, trigger_probability, risk_details
    
    def calculate_penalty(
        self,
        risk_details: Dict[str, any],
        units_sold: int
    ) -> Dict[str, any]:
        """
        计算法律风险惩罚
        
        Args:
            risk_details: 风险详情
            units_sold: 已售出数量
        
        Returns:
            惩罚详情（罚款、声誉损失等）
        """
        base_fine = 1000000.0  # 基础罚款 $1M
        fine_per_unit = 5000.0  # 每单位罚款
        
        total_fine = base_fine + (fine_per_unit * units_sold)
        
        reputation_loss = min(20.0, risk_details["legal_risk_factor"] * 25.0)
        
        return {
            "fine_amount": total_fine,
            "reputation_loss": reputation_loss,
            "may_require_recall": risk_details["legal_risk_factor"] > 0.6,
            "units_affected": units_sold
        }


__all__ = ["LegalRiskService"]


