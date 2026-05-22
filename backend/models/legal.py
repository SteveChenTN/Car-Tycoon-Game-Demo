"""
法规与合规系统模型
管理排放标准、安全标准、车辆合规认证等
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index, Enum, Date
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any, List
import enum
import json
from datetime import date

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class RegulationType(enum.Enum):
    """法规类型"""
    EMISSION = "EMISSION"          # 排放标准
    SAFETY = "SAFETY"              # 安全标准
    FUEL_ECONOMY = "FUEL_ECONOMY"  # 燃油经济性
    NOISE = "NOISE"                # 噪音标准
    MANUFACTURING = "MANUFACTURING"  # 制造标准（劳工、环保）


class ComplianceStatus(enum.Enum):
    """合规状态"""
    COMPLIANT = "COMPLIANT"        # 合规
    NON_COMPLIANT = "NON_COMPLIANT"  # 不合规
    PENDING_REVIEW = "PENDING_REVIEW"  # 待审核
    EXEMPTED = "EXEMPTED"          # 豁免


class Regulation(Base, TimestampMixin, BaseModel):
    """
    法规标准模型
    定义历史上的各类汽车法规（排放、安全等）
    """
    __tablename__ = "regulations"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 法规基础信息 ====================
    regulation_name = Column(
        String(200), nullable=False,
        comment="法规名称（如'US Clean Air Act 1970'）"
    )
    
    short_code = Column(
        String(50), nullable=False,
        comment="法规简称（如'CAA_1970'）"
    )
    
    regulation_type = Column(
        Enum(RegulationType), nullable=False,
        comment="法规类型"
    )
    
    region_code = Column(
        String(10), nullable=False,
        comment="适用地区代码（NAM/EUR/ASI等，或'GLOBAL'）"
    )
    
    # ==================== 生效时间 ====================
    effective_year = Column(
        Integer, nullable=False,
        comment="生效年份"
    )
    
    effective_month = Column(
        Integer, nullable=False, default=1,
        comment="生效月份 1-12"
    )
    
    # ==================== 法规要求（JSON格式） ====================
    requirements = Column(
        Text, nullable=False,
        comment="法规要求详细内容（JSON格式）- 如{'max_co2_g_km': 120, 'crash_test_min': 70}"
    )
    
    # ==================== 处罚措施 ====================
    fine_per_violation = Column(
        Float, nullable=False, default=0.0,
        comment="每次违规罚款（百万游戏币）"
    )
    
    can_ban_sales = Column(
        Boolean, nullable=False, default=False,
        comment="是否可以禁止销售不合规车型"
    )
    
    grace_period_months = Column(
        Integer, nullable=False, default=0,
        comment="宽限期（月）- 允许厂商调整的时间"
    )
    
    # ==================== 描述与历史背景 ====================
    description = Column(
        Text, nullable=True,
        comment="法规描述与背景"
    )
    
    historical_context = Column(
        Text, nullable=True,
        comment="历史背景（如石油危机、环保运动）"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("effective_year >= 1900 AND effective_year <= 2100", name="check_effective_year"),
        CheckConstraint("effective_month >= 1 AND effective_month <= 12", name="check_effective_month"),
        CheckConstraint("fine_per_violation >= 0", name="check_fine"),
        CheckConstraint("grace_period_months >= 0", name="check_grace_period"),
        Index("idx_regulation_region_year", "region_code", "effective_year"),
        Index("idx_regulation_type", "regulation_type"),
    )
    
    def get_requirements(self) -> Dict[str, Any]:
        """获取法规要求详情"""
        try:
            return json.loads(self.requirements)
        except:
            return {}
    
    def set_requirements(self, reqs: Dict[str, Any]) -> None:
        """设置法规要求"""
        self.requirements = json.dumps(reqs)
    
    def is_active_in_turn(self, current_year: int, current_month: int) -> bool:
        """
        检查法规在指定回合是否生效
        
        Args:
            current_year: 当前游戏年份
            current_month: 当前游戏月份
        
        Returns:
            是否生效
        """
        if current_year < self.effective_year:
            return False
        if current_year == self.effective_year and current_month < self.effective_month:
            return False
        return True
    
    def __repr__(self) -> str:
        return (f"<Regulation(id={self.id}, name='{self.regulation_name}', "
                f"region={self.region_code}, year={self.effective_year})>")


class VehicleCompliance(Base, TimestampMixin, BaseModel):
    """
    车辆合规记录
    记录每个车型在各地区的合规状态
    """
    __tablename__ = "vehicle_compliance"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 车辆与地区 ====================
    car_trim_id = Column(
        Integer, nullable=False,
        comment="车型ID（关联CarTrim）"
    )
    
    region_code = Column(
        String(10), nullable=False,
        comment="地区代码"
    )
    
    regulation_id = Column(
        Integer, ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False,
        comment="相关法规ID"
    )
    
    # ==================== 合规状态 ====================
    status = Column(
        Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.PENDING_REVIEW,
        comment="合规状态"
    )
    
    # ==================== 测试结果（JSON格式） ====================
    test_results = Column(
        Text, nullable=True,
        comment="测试结果详情（JSON格式）- 如{'co2_g_km': 115, 'crash_test_score': 75}"
    )
    
    certification_cost = Column(
        Float, nullable=False, default=0.0,
        comment="认证成本（百万游戏币）"
    )
    
    # ==================== 审核信息 ====================
    reviewed_turn = Column(
        Integer, nullable=True,
        comment="审核回合"
    )
    
    expires_turn = Column(
        Integer, nullable=True,
        comment="认证过期回合（NULL表示永久有效）"
    )
    
    # ==================== 违规处罚 ====================
    is_banned = Column(
        Boolean, nullable=False, default=False,
        comment="是否被禁售"
    )
    
    ban_start_turn = Column(
        Integer, nullable=True,
        comment="禁售开始回合"
    )
    
    total_fines_paid = Column(
        Float, nullable=False, default=0.0,
        comment="累计罚款"
    )
    
    # ==================== 备注 ====================
    notes = Column(
        Text, nullable=True,
        comment="审核备注"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("certification_cost >= 0", name="check_cert_cost"),
        CheckConstraint("total_fines_paid >= 0", name="check_fines"),
        Index("idx_compliance_car_region", "car_trim_id", "region_code"),
        Index("idx_compliance_regulation", "regulation_id"),
        Index("idx_compliance_status", "status"),
        Index("idx_compliance_banned", "is_banned"),
    )
    
    def get_test_results(self) -> Dict[str, Any]:
        """获取测试结果"""
        if not self.test_results:
            return {}
        try:
            return json.loads(self.test_results)
        except:
            return {}
    
    def set_test_results(self, results: Dict[str, Any]) -> None:
        """设置测试结果"""
        self.test_results = json.dumps(results)
    
    def __repr__(self) -> str:
        return (f"<VehicleCompliance(car_id={self.car_trim_id}, "
                f"region={self.region_code}, status={self.status.value})>")


class RecallEvent(Base, TimestampMixin, BaseModel):
    """
    召回事件模型
    记录车辆质量问题导致的召回
    """
    __tablename__ = "recall_events"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 召回基础信息 ====================
    car_trim_id = Column(
        Integer, nullable=False,
        comment="被召回车型ID"
    )
    
    recall_reason = Column(
        String(200), nullable=False,
        comment="召回原因（如'引擎过热风险'）"
    )
    
    severity = Column(
        String(20), nullable=False,
        comment="严重程度: MINOR/MODERATE/MAJOR/CRITICAL"
    )
    
    # ==================== 影响范围 ====================
    affected_vehicles = Column(
        Integer, nullable=False,
        comment="受影响车辆数量"
    )
    
    affected_regions = Column(
        Text, nullable=False,
        comment="受影响地区（JSON数组）"
    )
    
    # ==================== 时间 ====================
    announced_turn = Column(
        Integer, nullable=False,
        comment="公告回合"
    )
    
    completion_turn = Column(
        Integer, nullable=True,
        comment="召回完成回合"
    )
    
    # ==================== 成本与赔偿 ====================
    total_cost = Column(
        Float, nullable=False,
        comment="总召回成本（百万游戏币）"
    )
    
    compensation_per_vehicle = Column(
        Float, nullable=False, default=0.0,
        comment="每辆车补偿金额"
    )
    
    # ==================== 声誉影响 ====================
    reputation_damage = Column(
        Float, nullable=False,
        comment="声誉损失（绝对值）"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("affected_vehicles > 0", name="check_affected_vehicles"),
        CheckConstraint("total_cost >= 0", name="check_recall_cost"),
        CheckConstraint("reputation_damage >= 0", name="check_reputation_damage"),
        Index("idx_recall_company", "company_id"),
        Index("idx_recall_car", "car_trim_id"),
        Index("idx_recall_turn", "announced_turn"),
    )
    
    @validates("severity")
    def validate_severity(self, key: str, value: str) -> str:
        """验证严重程度"""
        valid_severities = ["MINOR", "MODERATE", "MAJOR", "CRITICAL"]
        if value not in valid_severities:
            raise ValueError(f"Invalid severity: {value}. Must be one of {valid_severities}")
        return value
    
    def get_affected_regions(self) -> List[str]:
        """获取受影响地区列表"""
        try:
            return json.loads(self.affected_regions)
        except:
            return []
    
    def set_affected_regions(self, regions: List[str]) -> None:
        """设置受影响地区"""
        self.affected_regions = json.dumps(regions)
    
    def __repr__(self) -> str:
        return (f"<RecallEvent(id={self.id}, company_id={self.company_id}, "
                f"reason='{self.recall_reason}', vehicles={self.affected_vehicles})>")


__all__ = [
    "Regulation", "RegulationType",
    "VehicleCompliance", "ComplianceStatus",
    "RecallEvent"
]


