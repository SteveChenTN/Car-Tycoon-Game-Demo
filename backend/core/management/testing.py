"""
原型测试系统业务逻辑
管理车辆原型测试流程
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging
import random

from backend.models.company import Company
from backend.models.testing import PrototypeProject, TestingPhase, TestingStatus, TestingFacility
from backend.models.engineering import CarTrim
from backend.models.legal import RecallEvent
from backend.models.game_state import GameState

logger = logging.getLogger(__name__)


class TestingLogic:
    """原型测试系统核心逻辑"""
    
    # 测试阶段持续时间（回合）
    PHASE_DURATIONS = {
        TestingPhase.PROTOTYPE_BUILD: 8,
        TestingPhase.LAB_TESTING: 12,
        TestingPhase.TRACK_TESTING: 16,
        TestingPhase.DURABILITY_TESTING: 20,
        TestingPhase.CRASH_TESTING: 8,
        TestingPhase.EMISSIONS_TESTING: 6
    }
    
    # 问题发现概率（基于测试强度）
    ISSUE_DISCOVERY_BASE_RATES = {
        "CRITICAL": 0.05,  # 5% 基础概率发现致命问题
        "MAJOR": 0.15,     # 15%
        "MINOR": 0.30      # 30%
    }
    
    def __init__(self, db: Session):
        """
        初始化测试逻辑
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def start_prototype_project(
        self,
        company_id: int,
        car_trim_id: int,
        budget: float,
        testing_intensity: float = 1.0,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        启动原型测试项目
        
        Args:
            company_id: 公司ID
            car_trim_id: 车型ID
            budget: 预算（百万游戏币）
            testing_intensity: 测试强度 0.5-2.0
            project_name: 项目名称（可选）
        
        Returns:
            项目创建结果
        """
        try:
            # 验证公司
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return {"success": False, "error": "Company not found"}
            
            # 验证车型
            car_trim = self.db.query(CarTrim).filter(CarTrim.id == car_trim_id).first()
            if not car_trim:
                return {"success": False, "error": "Car trim not found"}
            
            # 检查预算
            if company.cash < budget:
                return {
                    "success": False,
                    "error": f"Insufficient cash. Need {budget}M, have {company.cash}M"
                }
            
            # 获取游戏状态
            game_state = self.db.query(GameState).filter(
                GameState.id == company.game_id
            ).first()
            
            # 计算完成时间（基于测试强度）
            total_duration = sum(self.PHASE_DURATIONS.values())
            adjusted_duration = int(total_duration / testing_intensity)
            
            # 生成项目名称
            if not project_name:
                project_name = f"Project {car_trim.model_name} Proto"
            
            # 创建原型项目
            project = PrototypeProject(
                game_id=company.game_id,
                company_id=company_id,
                project_name=project_name,
                car_trim_id=car_trim_id,
                current_phase=TestingPhase.PROTOTYPE_BUILD,
                status=TestingStatus.IN_PROGRESS,
                progress_percent=0.0,
                start_turn=game_state.turn_number,
                estimated_completion_turn=game_state.turn_number + adjusted_duration,
                budget_allocated=budget,
                testing_intensity=testing_intensity
            )
            
            # 扣除初始预算
            company.cash -= budget
            
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(
                f"公司 {company.name} 启动原型项目: {project_name}, "
                f"预算 {budget}M, 强度 {testing_intensity}x"
            )
            
            return {
                "success": True,
                "project_id": project.id,
                "estimated_completion_turn": project.estimated_completion_turn,
                "estimated_cost": budget
            }
            
        except Exception as e:
            logger.error(f"启动原型项目失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def advance_testing_projects(self, current_turn: int) -> Dict[str, Any]:
        """
        推进所有进行中的测试项目
        
        Args:
            current_turn: 当前回合
        
        Returns:
            推进结果统计
        """
        try:
            # 查询所有进行中的项目
            active_projects = self.db.query(PrototypeProject).filter(
                PrototypeProject.status == TestingStatus.IN_PROGRESS
            ).all()
            
            results = {
                "projects_advanced": 0,
                "projects_completed": 0,
                "issues_found": 0,
                "phase_transitions": []
            }
            
            for project in active_projects:
                # 推进进度
                turns_elapsed = current_turn - project.start_turn
                total_turns = project.estimated_completion_turn - project.start_turn
                progress = (turns_elapsed / total_turns) * 100 if total_turns > 0 else 100
                project.progress_percent = min(100.0, progress)
                
                # 每回合消耗预算
                turn_cost = project.budget_allocated / total_turns if total_turns > 0 else 0
                project.budget_spent = min(project.budget_allocated, project.budget_spent + turn_cost)
                
                # 检查是否进入下一阶段
                phase_changed = self._check_phase_transition(project, current_turn)
                if phase_changed:
                    results["phase_transitions"].append({
                        "project_id": project.id,
                        "new_phase": project.current_phase.value
                    })
                
                # 测试阶段可能发现问题
                if project.current_phase != TestingPhase.PROTOTYPE_BUILD:
                    issues_found = self._discover_issues(project)
                    results["issues_found"] += issues_found
                
                # 检查是否完成
                if progress >= 100:
                    self._complete_testing(project)
                    results["projects_completed"] += 1
                
                results["projects_advanced"] += 1
            
            self.db.commit()
            
            return results
            
        except Exception as e:
            logger.error(f"推进测试项目失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _check_phase_transition(self, project: PrototypeProject, current_turn: int) -> bool:
        """
        检查并执行阶段转换
        
        Args:
            project: 原型项目
            current_turn: 当前回合
        
        Returns:
            是否发生了阶段转换
        """
        phase_order = [
            TestingPhase.PROTOTYPE_BUILD,
            TestingPhase.LAB_TESTING,
            TestingPhase.TRACK_TESTING,
            TestingPhase.DURABILITY_TESTING,
            TestingPhase.CRASH_TESTING,
            TestingPhase.EMISSIONS_TESTING,
            TestingPhase.COMPLETED
        ]
        
        current_phase_idx = phase_order.index(project.current_phase)
        
        # 计算当前阶段应完成的进度百分比
        total_duration = sum(self.PHASE_DURATIONS.values())
        phases_completed_duration = sum(
            self.PHASE_DURATIONS.get(phase, 0)
            for phase in phase_order[:current_phase_idx + 1]
        )
        phase_threshold = (phases_completed_duration / total_duration) * 100
        
        # 如果进度超过阈值，进入下一阶段
        if project.progress_percent >= phase_threshold and current_phase_idx < len(phase_order) - 1:
            project.current_phase = phase_order[current_phase_idx + 1]
            logger.info(
                f"原型项目 {project.project_name} 进入新阶段: {project.current_phase.value}"
            )
            return True
        
        return False
    
    def _discover_issues(self, project: PrototypeProject) -> int:
        """
        在测试中发现问题
        
        Args:
            project: 原型项目
        
        Returns:
            发现的问题数量
        """
        issues_found = 0
        
        # 测试强度影响发现率
        intensity_multiplier = project.testing_intensity
        
        # 对每个严重级别进行随机检查
        for severity, base_rate in self.ISSUE_DISCOVERY_BASE_RATES.items():
            adjusted_rate = base_rate * intensity_multiplier
            
            if random.random() < adjusted_rate:
                project.add_issue(severity)
                issues_found += 1
                logger.debug(
                    f"项目 {project.project_name} 发现 {severity} 问题"
                )
        
        return issues_found
    
    def _complete_testing(self, project: PrototypeProject) -> None:
        """
        完成测试项目
        
        Args:
            project: 原型项目
        """
        project.status = TestingStatus.COMPLETED
        project.current_phase = TestingPhase.COMPLETED
        project.progress_percent = 100.0
        
        game_state = self.db.query(GameState).filter(
            GameState.id == project.game_id
        ).first()
        project.actual_completion_turn = game_state.turn_number
        
        # 计算可靠性提升
        quality_score = project.calculate_completion_quality()
        reliability_boost = (quality_score - 50) / 10  # -5 到 +5 的范围
        project.reliability_improvement = reliability_boost
        
        # 计算召回风险（测试不充分会增加风险）
        if project.testing_intensity < 0.8:
            project.recall_risk_score = 0.7  # 高风险
        elif project.testing_intensity < 1.0:
            project.recall_risk_score = 0.4  # 中风险
        else:
            project.recall_risk_score = max(0.1, 0.5 - (quality_score / 200))
        
        # 应用到车型
        car_trim = self.db.query(CarTrim).filter(
            CarTrim.id == project.car_trim_id
        ).first()
        
        if car_trim:
            # 更新车型可靠性
            car_trim.final_reliability_score = min(
                100.0,
                car_trim.final_reliability_score + reliability_boost
            )
        
        logger.info(
            f"原型项目 {project.project_name} 完成! "
            f"质量分数: {quality_score:.1f}, 可靠性提升: {reliability_boost:+.1f}, "
            f"召回风险: {project.recall_risk_score:.2f}"
        )
    
    def skip_testing(
        self,
        car_trim_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """
        跳过测试直接量产（高风险）
        
        Args:
            car_trim_id: 车型ID
            company_id: 公司ID
        
        Returns:
            结果字典（包含风险警告）
        """
        try:
            car_trim = self.db.query(CarTrim).filter(CarTrim.id == car_trim_id).first()
            company = self.db.query(Company).filter(Company.id == company_id).first()
            
            if not car_trim or not company:
                return {"success": False, "error": "Invalid car or company"}
            
            # 创建一个"跳过"的项目记录（用于追踪）
            game_state = self.db.query(GameState).filter(
                GameState.id == company.game_id
            ).first()
            
            project = PrototypeProject(
                game_id=company.game_id,
                company_id=company_id,
                project_name=f"{car_trim.model_name} - TESTING SKIPPED",
                car_trim_id=car_trim_id,
                current_phase=TestingPhase.COMPLETED,
                status=TestingStatus.COMPLETED,
                progress_percent=100.0,
                start_turn=game_state.turn_number,
                estimated_completion_turn=game_state.turn_number,
                actual_completion_turn=game_state.turn_number,
                budget_allocated=0.0,
                budget_spent=0.0,
                testing_intensity=0.0,
                recall_risk_score=0.95,  # 极高风险！
                reliability_improvement=-15.0  # 可靠性惩罚
            )
            
            # 降低车型可靠性
            car_trim.final_reliability_score = max(
                0, car_trim.final_reliability_score - 15
            )
            
            self.db.add(project)
            self.db.commit()
            
            logger.warning(
                f"公司 {company.name} 跳过车型 {car_trim.model_name} 的测试! "
                f"召回风险极高: 95%"
            )
            
            return {
                "success": True,
                "warning": "测试已跳过 - 召回风险极高(95%)，可靠性下降-15",
                "recall_risk": 0.95,
                "reliability_penalty": -15.0
            }
            
        except Exception as e:
            logger.error(f"跳过测试失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def get_testing_facilities_bonus(self, company_id: int) -> Dict[str, float]:
        """
        获取公司测试设施提供的加成
        
        Args:
            company_id: 公司ID
        
        Returns:
            加成字典
        """
        facilities = self.db.query(TestingFacility).filter(
            TestingFacility.company_id == company_id,
            TestingFacility.is_operational == True
        ).all()
        
        total_efficiency_bonus = 0.0
        total_accuracy_bonus = 0.0
        
        for facility in facilities:
            total_efficiency_bonus += facility.testing_efficiency_bonus
            total_accuracy_bonus += facility.accuracy_bonus
        
        return {
            "efficiency_bonus": total_efficiency_bonus,
            "accuracy_bonus": total_accuracy_bonus,
            "facility_count": len(facilities)
        }


__all__ = ["TestingLogic"]


