"""
间谍与逆向工程系统
实现"战争迷雾"机制，允许玩家/AI获取竞争对手情报
"""
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from datetime import datetime
import random
import json

from backend.models.market import IntelligenceReport
from backend.models.engineering import Engine, Chassis, CarTrim, ChassisSourceType
from backend.services.engineering_service import EngineeringService
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ========== 数据结构 ==========

@dataclass
class EspionageResult:
    """间谍行动结果"""
    success: bool
    intelligence_report_id: Optional[int]
    cost: float
    time_turns: int
    reliability: float  # 情报可靠性 0-1
    message: str


@dataclass
class ReverseEngineeringResult:
    """逆向工程结果"""
    success: bool
    intelligence_report_id: Optional[int]
    cloned_chassis_id: Optional[int]  # 生成的克隆底盘ID
    unlocked_tech_ids: list[int]  # 解锁的技术节点ID列表
    cost: float
    time_turns: int
    revealed_data: Dict
    message: str


# ========== 间谍系统 ==========

class EspionageService:
    """
    间谍服务
    负责获取竞争对手的隐藏信息
    """
    
    # 基础成本常量
    BASE_COST_FINANCIAL = 500000      # 财务情报 50万
    BASE_COST_TECH = 1000000          # 技术情报 100万
    BASE_COST_STRATEGY = 750000       # 战略情报 75万
    BASE_COST_CAR_SPECS = 300000      # 车辆规格 30万
    
    BASE_TIME_TURNS = 3  # 基础时间：3回合
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger("EspionageService")
    
    # ========== 财务情报 ==========
    
    def gather_financial_intelligence(
        self,
        company_id: int,
        target_company_id: int,
        game_id: int,
        current_turn: int,
        investment_multiplier: float = 1.0
    ) -> EspionageResult:
        """
        收集目标公司的财务情报
        
        Args:
            company_id: 发起方公司ID
            target_company_id: 目标公司ID
            game_id: 游戏ID
            current_turn: 当前回合
            investment_multiplier: 投资倍数（增加成功率和可靠性）
        
        Returns:
            间谍行动结果
        """
        self.logger.info(
            f"公司 {company_id} 尝试收集公司 {target_company_id} 的财务情报"
        )
        
        # 计算成本和时间
        cost = self.BASE_COST_FINANCIAL * investment_multiplier
        time_turns = max(1, int(self.BASE_TIME_TURNS / investment_multiplier))
        
        # 成功率（基础50%，投资可提升）
        success_rate = min(0.95, 0.50 + investment_multiplier * 0.15)
        success = random.random() < success_rate
        
        if not success:
            return EspionageResult(
                success=False,
                intelligence_report_id=None,
                cost=cost * 0.5,  # 失败退还一半
                time_turns=time_turns,
                reliability=0.0,
                message="情报收集失败，目标公司反间谍措施有效"
            )
        
        # 成功：生成情报快照
        # TODO: 实际应从Company模型获取
        financial_data = {
            "cash_balance": random.uniform(10000000, 100000000),  # 模拟数据
            "revenue_last_quarter": random.uniform(5000000, 50000000),
            "profit_margin": random.uniform(0.05, 0.20),
            "debt_level": random.uniform(0, 50000000),
            "credit_rating": random.choice(["AAA", "AA", "A", "BBB"]),
            "burn_rate_monthly": random.uniform(1000000, 10000000)
        }
        
        # 可靠性（投资越多越准确）
        reliability = min(0.95, 0.60 + investment_multiplier * 0.10)
        
        # 添加噪声（模拟不准确性）
        if reliability < 1.0:
            noise_factor = 1.0 - reliability
            for key in ["cash_balance", "revenue_last_quarter", "debt_level"]:
                if key in financial_data:
                    financial_data[key] *= random.uniform(
                        1.0 - noise_factor * 0.3,
                        1.0 + noise_factor * 0.3
                    )
        
        # 创建情报报告
        report = IntelligenceReport(
            game_id=game_id,
            company_id=company_id,
            target_company_id=target_company_id,
            report_type="FINANCIAL",
            data_snapshot=json.dumps(financial_data),
            reliability=reliability,
            acquired_turn=current_turn,
            cost=cost,
            expires_turn=current_turn + 12  # 12回合后过期
        )
        
        self.db.add(report)
        self.db.commit()
        
        self.logger.info(
            f"✓ 财务情报收集成功 | 可靠性: {reliability*100:.0f}% | "
            f"成本: {cost:,.0f}"
        )
        
        return EspionageResult(
            success=True,
            intelligence_report_id=report.id,
            cost=cost,
            time_turns=time_turns,
            reliability=reliability,
            message=f"成功获取目标公司财务情报（可靠性{reliability*100:.0f}%）"
        )
    
    # ========== 技术情报 ==========
    
    def gather_tech_intelligence(
        self,
        company_id: int,
        target_company_id: int,
        game_id: int,
        current_turn: int,
        investment_multiplier: float = 1.0
    ) -> EspionageResult:
        """
        收集目标公司的技术情报（研发项目、技术等级）
        
        Args:
            company_id: 发起方公司ID
            target_company_id: 目标公司ID
            game_id: 游戏ID
            current_turn: 当前回合
            investment_multiplier: 投资倍数
        
        Returns:
            间谍行动结果
        """
        self.logger.info(
            f"公司 {company_id} 尝试收集公司 {target_company_id} 的技术情报"
        )
        
        cost = self.BASE_COST_TECH * investment_multiplier
        time_turns = max(2, int(self.BASE_TIME_TURNS * 1.5 / investment_multiplier))
        
        # 技术情报更难获取
        success_rate = min(0.85, 0.40 + investment_multiplier * 0.12)
        success = random.random() < success_rate
        
        if not success:
            return EspionageResult(
                success=False,
                intelligence_report_id=None,
                cost=cost * 0.5,
                time_turns=time_turns,
                reliability=0.0,
                message="技术情报收集失败，目标公司保密措施严密"
            )
        
        # 成功：查询目标公司的引擎和底盘
        engines = self.db.query(Engine).filter(
            Engine.company_id == target_company_id,
            Engine.game_id == game_id,
            Engine.is_available == True
        ).all()
        
        chassis_list = self.db.query(Chassis).filter(
            Chassis.company_id == target_company_id,
            Chassis.game_id == game_id,
            Chassis.is_available == True
        ).all()
        
        tech_data = {
            "engine_count": len(engines),
            "chassis_count": len(chassis_list),
            "avg_engine_tech_level": sum(e.tech_level for e in engines) / len(engines) if engines else 0,
            "max_engine_power": max((e.max_horsepower for e in engines), default=0),
            "rd_projects_estimated": random.randint(1, 5)  # 模拟
        }
        
        reliability = min(0.90, 0.55 + investment_multiplier * 0.10)
        
        report = IntelligenceReport(
            game_id=game_id,
            company_id=company_id,
            target_company_id=target_company_id,
            report_type="TECH",
            data_snapshot=json.dumps(tech_data),
            reliability=reliability,
            acquired_turn=current_turn,
            cost=cost,
            expires_turn=current_turn + 8  # 8回合后过期
        )
        
        self.db.add(report)
        self.db.commit()
        
        self.logger.info(
            f"✓ 技术情报收集成功 | 可靠性: {reliability*100:.0f}% | "
            f"引擎数: {tech_data['engine_count']}"
        )
        
        return EspionageResult(
            success=True,
            intelligence_report_id=report.id,
            cost=cost,
            time_turns=time_turns,
            reliability=reliability,
            message=f"成功获取技术情报（{tech_data['engine_count']}个引擎，平均技术等级{tech_data['avg_engine_tech_level']:.1f}）"
        )
    
    # ========== 查询情报 ==========
    
    def get_intelligence_reports(
        self,
        company_id: int,
        target_company_id: Optional[int] = None,
        report_type: Optional[str] = None,
        current_turn: Optional[int] = None
    ) -> list[IntelligenceReport]:
        """
        获取已有的情报报告
        
        Args:
            company_id: 公司ID
            target_company_id: 可选，筛选目标公司
            report_type: 可选，筛选报告类型
            current_turn: 可选，用于过滤过期报告
        
        Returns:
            情报报告列表
        """
        query = self.db.query(IntelligenceReport).filter(
            IntelligenceReport.company_id == company_id
        )
        
        if target_company_id:
            query = query.filter(IntelligenceReport.target_company_id == target_company_id)
        
        if report_type:
            query = query.filter(IntelligenceReport.report_type == report_type)
        
        reports = query.all()
        
        # 过滤过期报告
        if current_turn:
            reports = [r for r in reports if not r.is_expired(current_turn)]
        
        return reports


# ========== 逆向工程系统 ==========

class ReverseEngineeringService:
    """
    逆向工程服务
    分析竞争对手的车辆以获取精确技术数据
    """
    
    BASE_COST_PER_CAR = 200000  # 基础成本 20万
    BASE_TIME_TURNS = 2
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger("ReverseEngineering")
    
    def reverse_engineer_car(
        self,
        company_id: int,
        target_car_id: int,
        game_id: int,
        current_turn: int,
        investment_multiplier: float = 1.0
    ) -> ReverseEngineeringResult:
        """
        逆向工程目标车辆
        
        Args:
            company_id: 发起方公司ID
            target_car_id: 目标CarTrim ID
            game_id: 游戏ID
            current_turn: 当前回合
            investment_multiplier: 投资倍数（影响细节水平）
        
        Returns:
            逆向工程结果
        """
        # 获取目标车辆
        target_car = self.db.query(CarTrim).filter(
            CarTrim.id == target_car_id,
            CarTrim.game_id == game_id
        ).first()
        
        if not target_car:
            return ReverseEngineeringResult(
                success=False,
                intelligence_report_id=None,
                cloned_chassis_id=None,
                unlocked_tech_ids=[],
                cost=0,
                time_turns=0,
                revealed_data={},
                message="目标车辆不存在"
            )
        
        self.logger.info(
            f"公司 {company_id} 开始逆向工程车辆 {target_car.name} (ID: {target_car_id})"
        )
        
        cost = self.BASE_COST_PER_CAR * investment_multiplier
        time_turns = max(1, int(self.BASE_TIME_TURNS / investment_multiplier))
        
        # 逆向工程总是成功，只是精度不同
        # 加载引擎数据
        engine = self.db.query(Engine).filter(
            Engine.id == target_car.engine_id
        ).first()
        
        # 加载底盘数据
        chassis = self.db.query(Chassis).filter(
            Chassis.id == target_car.chassis_id
        ).first()
        
        # 精度基于投资
        precision = min(0.98, 0.80 + investment_multiplier * 0.06)
        
        # 生成逆向工程数据
        revealed_data = {
            "car_trim_id": target_car.id,
            "car_name": target_car.name,
            "segment": target_car.segment,
            
            # 性能数据
            "horsepower": int(target_car.engine.max_horsepower * random.uniform(1.0 - (1 - precision) * 0.2, 1.0 + (1 - precision) * 0.2)),
            "torque_nm": int(target_car.engine.max_torque_nm * random.uniform(1.0 - (1 - precision) * 0.2, 1.0 + (1 - precision) * 0.2)),
            "displacement_cc": target_car.engine.displacement_cc,
            "induction_type": target_car.engine.induction_type,
            
            "zero_to_hundred": round(target_car.zero_to_hundred_kph_sec * random.uniform(0.95, 1.05), 2),
            "top_speed": int(target_car.top_speed_kph * random.uniform(0.95, 1.05)),
            
            # 可靠性
            "reliability_score": round(target_car.final_reliability_score * random.uniform(0.90, 1.00), 1),
            
            # 成本估算（不太准确）
            "estimated_manufacturing_cost": target_car.manufacturing_cost * random.uniform(0.80, 1.20),
            "msrp": target_car.msrp,
            
            # 技术等级
            "engine_tech_level": engine.tech_level if engine else 0,
            "chassis_tech_level": chassis.tech_level if chassis else 0,
            
            "precision": precision
        }
        
        # 创建情报报告
        report = IntelligenceReport(
            game_id=game_id,
            company_id=company_id,
            target_company_id=target_car.company_id,
            report_type="CAR_SPECS",
            data_snapshot=json.dumps(revealed_data),
            reliability=precision,
            acquired_turn=current_turn,
            cost=cost,
            expires_turn=None  # 车辆规格不过期
        )
        
        self.db.add(report)
        self.db.commit()
        
        # 创建克隆底盘
        cloned_chassis_id = None
        unlocked_tech_ids = []
        
        try:
            # 获取原底盘信息
            original_chassis = chassis
            
            if original_chassis:
                # 计算品质上限：初始为原版品质的85%，可改进但始终低于原版
                base_quality = (original_chassis.rigidity_rating + original_chassis.crash_test_rating) / 200.0
                quality_cap = base_quality * 0.85  # 初始上限85%
                
                # 计算法律风险：基于投资倍数（投资越多，风险越高，因为更容易被发现）
                legal_risk = min(0.8, 0.3 + (investment_multiplier - 1.0) * 0.1)
                
                # 生成克隆底盘代码
                cloned_code = f"CLONE_{target_car.trim_code}_{company_id}"
                
                # 创建克隆底盘
                # 创建克隆底盘（注意：create_chassis现在不自动commit）
                cloned_chassis = EngineeringService.create_chassis(
                    db=self.db,
                    game_id=game_id,
                    company_id=company_id,
                    name=f"{target_car.name} (克隆版)",
                    code=cloned_code,
                    wheelbase_mm=original_chassis.wheelbase_mm,
                    track_front_mm=original_chassis.track_front_mm,
                    track_rear_mm=original_chassis.track_rear_mm,
                    layout=original_chassis.layout,
                    engine_bay_length_mm=original_chassis.engine_bay_length_mm,
                    engine_bay_width_mm=original_chassis.engine_bay_width_mm,
                    engine_bay_height_mm=original_chassis.engine_bay_height_mm,
                    max_cooling_capacity_kw=original_chassis.max_cooling_capacity_kw,
                    material=original_chassis.material,
                    rigidity_rating=original_chassis.rigidity_rating * 0.85,  # 降低15%
                    crash_test_rating=original_chassis.crash_test_rating * 0.85,
                    tech_level=original_chassis.tech_level,
                    development_cost=cost,
                    source_type=ChassisSourceType.CLONED,
                    original_competitor_id=target_car.id,
                    legal_risk_factor=legal_risk,
                    quality_cap=quality_cap,
                    is_platform=False
                )
                
                cloned_chassis_id = cloned_chassis.id
                
                # 解锁相关技术（基于技术等级）
                # TODO: 实现技术解锁逻辑，这里先返回空列表
                # unlocked_tech_ids = self._unlock_technologies_from_reverse_engineering(
                #     engine_tech_level=engine.tech_level if engine else 0,
                #     chassis_tech_level=original_chassis.tech_level
                # )
                
                self.logger.info(
                    f"✓ 创建克隆底盘: {cloned_chassis.code} | "
                    f"品质上限: {quality_cap*100:.0f}% | 法律风险: {legal_risk*100:.0f}%"
                )
        except Exception as e:
            self.logger.error(f"创建克隆底盘失败: {e}", exc_info=True)
            # 即使创建底盘失败，情报报告仍然有效
        
        self.logger.info(
            f"✓ 逆向工程完成 | 车辆: {target_car.name} | "
            f"精度: {precision*100:.0f}% | 成本: {cost:,.0f} | "
            f"克隆底盘ID: {cloned_chassis_id}"
        )
        
        return ReverseEngineeringResult(
            success=True,
            intelligence_report_id=report.id,
            cloned_chassis_id=cloned_chassis_id,
            unlocked_tech_ids=unlocked_tech_ids,
            cost=cost,
            time_turns=time_turns,
            revealed_data=revealed_data,
            message=f"成功逆向工程 {target_car.name}（精度{precision*100:.0f}%）" + 
                   (f"，已生成克隆底盘" if cloned_chassis_id else "")
        )
    
    def get_car_intelligence(
        self,
        company_id: int,
        target_car_id: int,
        game_id: int
    ) -> Optional[Dict]:
        """
        获取已有的车辆情报
        
        Returns:
            情报数据或None
        """
        report = self.db.query(IntelligenceReport).filter(
            IntelligenceReport.company_id == company_id,
            IntelligenceReport.game_id == game_id,
            IntelligenceReport.report_type == "CAR_SPECS"
        ).first()
        
        if report:
            data = report.get_data()
            if data.get("car_trim_id") == target_car_id:
                return data
        
        return None


# ========== 便捷函数 ==========

def spy_on_competitor_finances(
    db: Session,
    company_id: int,
    target_company_id: int,
    game_id: int,
    current_turn: int,
    budget: float = 500000
) -> EspionageResult:
    """
    便捷函数：间谍竞争对手财务
    """
    service = EspionageService(db)
    investment_multiplier = budget / service.BASE_COST_FINANCIAL
    
    return service.gather_financial_intelligence(
        company_id=company_id,
        target_company_id=target_company_id,
        game_id=game_id,
        current_turn=current_turn,
        investment_multiplier=investment_multiplier
    )


def reverse_engineer_competitor_car(
    db: Session,
    company_id: int,
    target_car_id: int,
    game_id: int,
    current_turn: int,
    budget: float = 200000
) -> ReverseEngineeringResult:
    """
    便捷函数：逆向工程竞争对手车辆
    """
    service = ReverseEngineeringService(db)
    investment_multiplier = budget / service.BASE_COST_PER_CAR
    
    return service.reverse_engineer_car(
        company_id=company_id,
        target_car_id=target_car_id,
        game_id=game_id,
        current_turn=current_turn,
        investment_multiplier=investment_multiplier
    )


__all__ = [
    "EspionageService",
    "ReverseEngineeringService",
    "EspionageResult",
    "ReverseEngineeringResult",
    "spy_on_competitor_finances",
    "reverse_engineer_competitor_car"
]

