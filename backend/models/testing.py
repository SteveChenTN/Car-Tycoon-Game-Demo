"""
原型测试系统模型
管理车型原型开发、测试、可靠性验证
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, CheckConstraint, Index, Enum
from sqlalchemy.orm import relationship, validates
from typing import Dict, Any
import enum
import json

from backend.database import Base
from backend.models.base import TimestampMixin, BaseModel


class TestingPhase(enum.Enum):
    """测试阶段"""
    PROTOTYPE_BUILD = "PROTOTYPE_BUILD"    # 原型车制造
    LAB_TESTING = "LAB_TESTING"            # 实验室测试
    TRACK_TESTING = "TRACK_TESTING"        # 赛道测试
    DURABILITY_TESTING = "DURABILITY_TESTING"  # 耐久性测试
    CRASH_TESTING = "CRASH_TESTING"        # 碰撞测试
    EMISSIONS_TESTING = "EMISSIONS_TESTING"  # 排放测试
    COMPLETED = "COMPLETED"                # 测试完成


class TestingStatus(enum.Enum):
    """测试状态"""
    PLANNED = "PLANNED"        # 计划中
    IN_PROGRESS = "IN_PROGRESS"  # 进行中
    COMPLETED = "COMPLETED"    # 已完成
    FAILED = "FAILED"          # 测试失败
    CANCELLED = "CANCELLED"    # 已取消


class PrototypeProject(Base, TimestampMixin, BaseModel):
    """
    原型项目模型
    记录车型从概念到量产前的原型开发与测试过程
    """
    __tablename__ = "prototype_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 项目基础信息 ====================
    project_name = Column(
        String(100), nullable=False,
        comment="项目名称（如'Project Phoenix'）"
    )
    
    car_trim_id = Column(
        Integer, nullable=False,
        comment="目标车型ID（关联CarTrim）"
    )
    
    # ==================== 进度与状态 ====================
    current_phase = Column(
        Enum(TestingPhase), nullable=False, default=TestingPhase.PROTOTYPE_BUILD,
        comment="当前测试阶段"
    )
    
    status = Column(
        Enum(TestingStatus), nullable=False, default=TestingStatus.PLANNED,
        comment="项目状态"
    )
    
    progress_percent = Column(
        Float, nullable=False, default=0.0,
        comment="整体进度 0-100"
    )
    
    # ==================== 时间 ====================
    start_turn = Column(
        Integer, nullable=False,
        comment="开始回合"
    )
    
    estimated_completion_turn = Column(
        Integer, nullable=False,
        comment="预计完成回合"
    )
    
    actual_completion_turn = Column(
        Integer, nullable=True,
        comment="实际完成回合"
    )
    
    # ==================== 投资与成本 ====================
    budget_allocated = Column(
        Float, nullable=False,
        comment="分配预算（百万游戏币）"
    )
    
    budget_spent = Column(
        Float, nullable=False, default=0.0,
        comment="已花费预算"
    )
    
    # ==================== 测试强度（影响结果质量） ====================
    testing_intensity = Column(
        Float, nullable=False, default=1.0,
        comment="测试强度倍数 0.5-2.0（投入越多，发现问题越多，最终产品越可靠）"
    )
    
    # ==================== 测试结果统计 ====================
    issues_found_critical = Column(
        Integer, nullable=False, default=0,
        comment="发现的致命问题数"
    )
    
    issues_found_major = Column(
        Integer, nullable=False, default=0,
        comment="发现的重大问题数"
    )
    
    issues_found_minor = Column(
        Integer, nullable=False, default=0,
        comment="发现的次要问题数"
    )
    
    issues_resolved = Column(
        Integer, nullable=False, default=0,
        comment="已解决问题数"
    )
    
    # ==================== 性能验证结果 ====================
    validated_performance = Column(
        Text, nullable=True,
        comment="验证后的性能数据（JSON格式）- 真实的0-100加速、油耗等"
    )
    
    reliability_improvement = Column(
        Float, nullable=False, default=0.0,
        comment="可靠性提升值（相对于初始设计）"
    )
    
    # ==================== 测试报告 ====================
    test_summary = Column(
        Text, nullable=True,
        comment="测试总结报告（文本）"
    )
    
    recommendations = Column(
        Text, nullable=True,
        comment="工程师建议（JSON数组）- 如['增加冷却系统容量', '优化悬挂调校']"
    )
    
    # ==================== 风险评估 ====================
    recall_risk_score = Column(
        Float, nullable=False, default=0.5,
        comment="召回风险分数 0-1（跳过测试会很高）"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_progress"),
        CheckConstraint("budget_allocated > 0", name="check_budget"),
        CheckConstraint("budget_spent >= 0", name="check_spent"),
        CheckConstraint("testing_intensity >= 0.5 AND testing_intensity <= 2.0", name="check_intensity"),
        CheckConstraint("issues_found_critical >= 0", name="check_issues_critical"),
        CheckConstraint("issues_found_major >= 0", name="check_issues_major"),
        CheckConstraint("issues_found_minor >= 0", name="check_issues_minor"),
        CheckConstraint("issues_resolved >= 0", name="check_resolved"),
        CheckConstraint("reliability_improvement >= -50 AND reliability_improvement <= 50", name="check_reliability"),
        CheckConstraint("recall_risk_score >= 0 AND recall_risk_score <= 1", name="check_recall_risk"),
        Index("idx_prototype_company", "company_id"),
        Index("idx_prototype_car", "car_trim_id"),
        Index("idx_prototype_status", "status"),
        Index("idx_prototype_phase", "current_phase"),
    )
    
    def get_validated_performance(self) -> Dict[str, Any]:
        """获取验证后的性能数据"""
        if not self.validated_performance:
            return {}
        try:
            return json.loads(self.validated_performance)
        except:
            return {}
    
    def set_validated_performance(self, data: Dict[str, Any]) -> None:
        """设置验证后的性能数据"""
        self.validated_performance = json.dumps(data)
    
    def get_recommendations(self) -> list[str]:
        """获取工程师建议列表"""
        if not self.recommendations:
            return []
        try:
            return json.loads(self.recommendations)
        except:
            return []
    
    def set_recommendations(self, recs: list[str]) -> None:
        """设置工程师建议"""
        self.recommendations = json.dumps(recs)
    
    def add_issue(self, severity: str) -> None:
        """
        添加发现的问题
        
        Args:
            severity: 严重程度 'CRITICAL'/'MAJOR'/'MINOR'
        """
        if severity == "CRITICAL":
            self.issues_found_critical += 1
        elif severity == "MAJOR":
            self.issues_found_major += 1
        elif severity == "MINOR":
            self.issues_found_minor += 1
    
    def get_total_issues(self) -> int:
        """获取总问题数"""
        return self.issues_found_critical + self.issues_found_major + self.issues_found_minor
    
    def calculate_completion_quality(self) -> float:
        """
        计算完成质量分数 0-100
        基于问题解决率、测试强度等
        """
        total_issues = self.get_total_issues()
        if total_issues == 0:
            base_quality = 85.0  # 没发现问题不代表没问题，可能是测试不够
        else:
            resolution_rate = self.issues_resolved / total_issues
            base_quality = 50.0 + (resolution_rate * 40.0)
        
        # 测试强度加成
        intensity_bonus = (self.testing_intensity - 1.0) * 10
        
        # 致命问题扣分
        critical_penalty = self.issues_found_critical * 5
        
        final_quality = base_quality + intensity_bonus - critical_penalty
        return max(0.0, min(100.0, final_quality))
    
    def __repr__(self) -> str:
        return (f"<PrototypeProject(id={self.id}, name='{self.project_name}', "
                f"phase={self.current_phase.value}, progress={self.progress_percent:.1f}%)>")


class TestingFacility(Base, TimestampMixin, BaseModel):
    """
    测试设施模型
    特殊解锁的测试设施（如风洞、试车场）
    """
    __tablename__ = "testing_facilities"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game_state.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # ==================== 设施信息 ====================
    facility_type = Column(
        String(50), nullable=False,
        comment="设施类型: WIND_TUNNEL/PROVING_GROUND/CRASH_LAB/EMISSIONS_LAB"
    )
    
    facility_name = Column(
        String(100), nullable=False,
        comment="设施名称"
    )
    
    location_region = Column(
        String(10), nullable=False,
        comment="所在地区代码"
    )
    
    # ==================== 能力与等级 ====================
    capability_level = Column(
        Integer, nullable=False, default=1,
        comment="能力等级 1-5（影响测试精度和效率）"
    )
    
    testing_efficiency_bonus = Column(
        Float, nullable=False, default=0.1,
        comment="测试效率加成 0-1"
    )
    
    accuracy_bonus = Column(
        Float, nullable=False, default=0.05,
        comment="测试精度加成 0-0.5"
    )
    
    # ==================== 建设与成本 ====================
    construction_cost = Column(
        Float, nullable=False,
        comment="建设成本（百万游戏币）"
    )
    
    annual_operating_cost = Column(
        Float, nullable=False,
        comment="年运营成本（百万游戏币）"
    )
    
    built_turn = Column(
        Integer, nullable=False,
        comment="建成回合"
    )
    
    # ==================== 状态 ====================
    is_operational = Column(
        Boolean, nullable=False, default=True,
        comment="是否运营中"
    )
    
    # ==================== 约束 ====================
    __table_args__ = (
        CheckConstraint("capability_level >= 1 AND capability_level <= 5", name="check_capability"),
        CheckConstraint("testing_efficiency_bonus >= 0 AND testing_efficiency_bonus <= 1", name="check_efficiency"),
        CheckConstraint("accuracy_bonus >= 0 AND accuracy_bonus <= 0.5", name="check_accuracy"),
        CheckConstraint("construction_cost > 0", name="check_construction_cost"),
        CheckConstraint("annual_operating_cost >= 0", name="check_operating_cost"),
        Index("idx_facility_company", "company_id"),
        Index("idx_facility_type", "facility_type"),
        Index("idx_facility_operational", "is_operational"),
    )
    
    @validates("facility_type")
    def validate_facility_type(self, key: str, value: str) -> str:
        """验证设施类型"""
        valid_types = ["WIND_TUNNEL", "PROVING_GROUND", "CRASH_LAB", "EMISSIONS_LAB", "COLD_WEATHER_LAB"]
        if value not in valid_types:
            raise ValueError(f"Invalid facility type: {value}. Must be one of {valid_types}")
        return value
    
    def __repr__(self) -> str:
        return (f"<TestingFacility(id={self.id}, type={self.facility_type}, "
                f"level={self.capability_level}, operational={self.is_operational})>")


__all__ = [
    "PrototypeProject", "TestingPhase", "TestingStatus",
    "TestingFacility"
]


