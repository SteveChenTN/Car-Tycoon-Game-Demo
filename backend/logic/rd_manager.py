"""
统一R&D管理系统
集中管理所有研发项目（引擎、底盘、技术、车辆），基于部门系统
"""
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
import logging
import math

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MONEY_LEGACY_MILLION_THRESHOLD = 100_000.0
MONEY_MILLION = 1_000_000.0


def normalize_project_cost(amount: float) -> float:
    """Normalize legacy million-denominated R&D costs to absolute currency."""
    amount = float(amount or 0.0)
    if 0.0 < abs(amount) < MONEY_LEGACY_MILLION_THRESHOLD:
        return amount * MONEY_MILLION
    return amount


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


class ProjectType(str, Enum):
    """研发项目类型"""
    ENGINE = "ENGINE"  # 引擎研发
    CHASSIS = "CHASSIS"  # 底盘研发
    CAR = "CAR"  # 车辆研发
    TECH = "TECH"  # 技术研发


class ProjectStatus(str, Enum):
    """项目状态"""
    PENDING = "PENDING"  # 待启动
    ACTIVE = "ACTIVE"  # 进行中
    PAUSED = "PAUSED"  # 已暂停
    COMPLETED = "COMPLETED"  # 已完成


class DepartmentType(str, Enum):
    """部门类型"""
    POWERTRAIN = "POWERTRAIN"  # 动力总成（引擎）
    CHASSIS = "CHASSIS"  # 底盘
    VEHICLE = "VEHICLE"  # 车辆
    TECH = "TECH"  # 技术


class ResearchProject(BaseModel):
    """研发项目数据模型"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ProjectType
    status: ProjectStatus = ProjectStatus.PENDING
    payload: Dict[str, Any] = Field(default_factory=dict)  # 存储蓝图数据或技术ID
    progress: int = 0  # 当前周数
    target_weeks: int  # 总周数
    budget_allocated: float  # 已分配预算（百万游戏币）
    company_id: int
    game_id: int
    start_turn: Optional[int] = None
    completion_turn: Optional[int] = None
    
    class Config:
        use_enum_values = True


class Department(BaseModel):
    """部门定义"""
    type: DepartmentType
    slots_total: int = 2  # 初始槽位数
    active_projects: List[ResearchProject] = Field(default_factory=list)
    familiarity_score: float = 0.0  # 熟悉度分数（经验值）
    familiarity_level: int = 1  # 熟悉度等级（1-10，从分数计算）
    
    # 加成效果（从熟悉度等级计算）
    cost_reduction: float = 0.0  # 研发成本降低（0-15%）
    time_reduction: float = 0.0  # 研发时间缩短（0-15%）
    reliability_bonus: float = 0.0  # 可靠性加成（0-8%）
    
    class Config:
        use_enum_values = True
    
    def _update_familiarity_level(self) -> None:
        """
        根据熟悉度分数更新等级（1-10）
        经验值曲线从 EngineeringFamiliarity 迁移
        """
        if self.familiarity_score < 10:
            level = 1
        elif self.familiarity_score < 50:
            level = 2
        elif self.familiarity_score < 100:
            level = 3
        elif self.familiarity_score < 200:
            level = 4
        elif self.familiarity_score < 400:
            level = 5
        elif self.familiarity_score < 800:
            level = 6
        elif self.familiarity_score < 1500:
            level = 7
        elif self.familiarity_score < 3000:
            level = 8
        elif self.familiarity_score < 6000:
            level = 9
        else:
            level = 10
        
        self.familiarity_level = level
        self._update_bonuses()
    
    def _update_bonuses(self) -> None:
        """
        根据熟悉度等级更新效果加成
        从 EngineeringFamiliarity 迁移
        """
        level = self.familiarity_level
        
        # 熟悉度等级效果：
        # 等级1-3：无加成
        # 等级4-6：研发成本-5%，可靠性+2%
        # 等级7-8：研发成本-10%，可靠性+5%，研发时间-10%
        # 等级9-10：研发成本-15%，可靠性+8%，研发时间-15%
        
        if level <= 3:
            self.cost_reduction = 0.0
            self.reliability_bonus = 0.0
            self.time_reduction = 0.0
        elif level <= 6:
            self.cost_reduction = 0.05
            self.reliability_bonus = 0.02
            self.time_reduction = 0.0
        elif level <= 8:
            self.cost_reduction = 0.10
            self.reliability_bonus = 0.05
            self.time_reduction = 0.10
        else:  # 9-10
            self.cost_reduction = 0.15
            self.reliability_bonus = 0.08
            self.time_reduction = 0.15
    
    def add_familiarity(self, experience_points: float) -> None:
        """
        增加部门熟悉度
        
        Args:
            experience_points: 经验点数
        """
        self.familiarity_score += experience_points
        self._update_familiarity_level()
    
    def get_available_slots(self) -> int:
        """获取可用槽位数"""
        active_count = len([p for p in self.active_projects if p.status == ProjectStatus.ACTIVE])
        return max(0, self.slots_total - active_count)
    
    def can_start_project(self) -> bool:
        """检查是否可以启动新项目"""
        return self.get_available_slots() > 0


class RDManager:
    """
    统一R&D管理器
    
    管理所有研发项目，基于部门系统：
    - POWERTRAIN: 引擎研发
    - CHASSIS: 底盘研发
    - VEHICLE: 车辆研发
    - TECH: 技术研发
    """
    
    def __init__(self, db: Session, company_id: int, game_id: int, state: Optional[Dict[str, Any]] = None):
        """
        初始化R&D管理器
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            game_id: 游戏ID
            state: 从数据库加载的状态（可选，如果为None则从GameState加载）
        """
        self.db = db
        self.company_id = company_id
        self.game_id = game_id
        
        # 如果没有提供state，尝试从GameState加载
        if state is None:
            from backend.models.game_state import GameState
            game_state = db.query(GameState).filter(GameState.id == game_id).first()
            if game_state:
                state = game_state.get_rd_manager_state_for_company(company_id)
        
        # 初始化4个部门
        if state:
            self.departments = self._from_dict(state)
        else:
            self.departments = {
                DepartmentType.POWERTRAIN: Department(type=DepartmentType.POWERTRAIN),
                DepartmentType.CHASSIS: Department(type=DepartmentType.CHASSIS),
                DepartmentType.VEHICLE: Department(type=DepartmentType.VEHICLE),
                DepartmentType.TECH: Department(type=DepartmentType.TECH),
            }
    
    def save_state(self) -> None:
        """
        保存状态到GameState
        """
        from backend.models.game_state import GameState
        game_state = self.db.query(GameState).filter(GameState.id == self.game_id).first()
        if game_state:
            state_dict = self.to_dict()
            game_state.set_rd_manager_state_for_company(self.company_id, state_dict)
            self.db.commit()
    
    def start_project(
        self,
        project_type: ProjectType,
        payload: Dict[str, Any],
        base_weeks: int,
        base_cost: float,
        current_turn: int
    ) -> Tuple[bool, str, Optional[ResearchProject]]:
        """
        启动研发项目
        
        Args:
            project_type: 项目类型
            payload: 项目数据（蓝图或技术ID）
            base_weeks: 基础研发周数
            base_cost: 基础研发成本（百万游戏币）
            current_turn: 当前回合
            
        Returns:
            (是否成功, 消息, 项目对象)
        """
        # 映射项目类型到部门
        dept_mapping = {
            ProjectType.ENGINE: DepartmentType.POWERTRAIN,
            ProjectType.CHASSIS: DepartmentType.CHASSIS,
            ProjectType.CAR: DepartmentType.VEHICLE,
            ProjectType.TECH: DepartmentType.TECH,
        }
        
        dept_type = dept_mapping.get(project_type)
        if not dept_type:
            return False, f"未知的项目类型: {project_type}", None
        
        department = self.departments[dept_type]
        
        # 检查槽位
        if not department.can_start_project():
            return False, f"{_enum_value(dept_type)}部门槽位已满（{department.slots_total}/{department.slots_total}）", None
        
        # 获取公司
        from backend.models.company import Company
        company = self.db.query(Company).filter(Company.id == self.company_id).first()
        if not company:
            return False, "公司不存在", None
        
        # 应用熟悉度加成：成本和时间
        normalized_base_cost = normalize_project_cost(base_cost)
        effective_cost = normalized_base_cost * (1 - department.cost_reduction)
        effective_weeks = int(base_weeks * (1 - department.time_reduction))
        
        # 检查资金
        if company.cash < effective_cost:
            return False, f"资金不足（需要 ${effective_cost:,.0f}，当前 ${company.cash:,.0f}）", None
        
        # 扣除资金
        company.record_cost("rd", effective_cost)
        
        # 创建项目
        project = ResearchProject(
            type=project_type,
            status=ProjectStatus.ACTIVE,
            payload=payload,
            progress=0,
            target_weeks=effective_weeks,
            budget_allocated=effective_cost,
            company_id=self.company_id,
            game_id=self.game_id,
            start_turn=current_turn
        )
        
        # 添加到部门
        department.active_projects.append(project)
        
        logger.info(
            f"启动研发项目: {_enum_value(project_type)} - "
            f"公司 {self.company_id}, 部门 {_enum_value(dept_type)}, "
            f"周数 {effective_weeks} (基础 {base_weeks}), "
            f"成本 ${effective_cost:,.0f} (基础 ${normalized_base_cost:,.0f}), "
            f"熟悉度加成: 成本-{department.cost_reduction*100:.0f}%, 时间-{department.time_reduction*100:.0f}%"
        )
        
        return True, f"项目已启动，预计 {effective_weeks} 周完成", project
    
    def process_weekly_tick(self, current_turn: int) -> Dict[str, Any]:
        """
        处理每周tick，更新所有活跃项目进度
        
        Args:
            current_turn: 当前回合
            
        Returns:
            处理结果统计
        """
        results = {
            "projects_processed": 0,
            "projects_completed": 0,
            "completed_projects": []
        }
        
        # 遍历所有部门
        for dept_type, department in self.departments.items():
            # 处理部门中的活跃项目
            for project in department.active_projects:
                if project.status != ProjectStatus.ACTIVE:
                    continue
                
                results["projects_processed"] += 1
                
                # 增加进度
                project.progress += 1
                
                # 检查是否完成
                if project.progress >= project.target_weeks:
                    # 项目完成
                    project.status = ProjectStatus.COMPLETED
                    project.completion_turn = current_turn
                    
                    # 完成项目
                    completion_result = self._finalize_project(project)
                    
                    # 增加部门熟悉度（项目完成获得经验）
                    experience_gained = self._calculate_experience_gain(project)
                    department.add_familiarity(experience_gained)
                    
                    # 协调FactoryFamiliarity系统（混合策略）
                    self._notify_factory_familiarity(project, experience_gained, current_turn)
                    
                    results["projects_completed"] += 1
                    results["completed_projects"].append({
                        "project_id": project.id,
                        "type": _enum_value(project.type),
                        "department": _enum_value(dept_type),
                        "completion_result": completion_result
                    })
                    
                    logger.info(
                        f"研发项目完成: {_enum_value(project.type)} - "
                        f"公司 {self.company_id}, 部门 {_enum_value(dept_type)}, "
                        f"获得经验 {experience_gained:.1f}, "
                        f"部门熟悉度等级: {department.familiarity_level}"
                    )
        
        return results
    
    def _finalize_project(self, project: ResearchProject) -> Dict[str, Any]:
        """
        完成项目，分发到具体领域类
        
        Args:
            project: 完成的项目
            
        Returns:
            完成结果
        """
        try:
            if project.type == ProjectType.ENGINE:
                return self._finalize_engine(project)
            elif project.type == ProjectType.CHASSIS:
                return self._finalize_chassis(project)
            elif project.type == ProjectType.CAR:
                return self._finalize_vehicle(project)
            elif project.type == ProjectType.TECH:
                return self._finalize_tech(project)
            else:
                return {"success": False, "error": f"未知项目类型: {project.type}"}
        except Exception as e:
            logger.error(f"完成项目失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _finalize_engine(self, project: ResearchProject) -> Dict[str, Any]:
        """完成引擎研发"""
        from backend.models.engineering import Engine
        
        # 从payload获取引擎ID或数据
        engine_id = project.payload.get("engine_id")
        if engine_id:
            engine = self.db.query(Engine).filter(Engine.id == engine_id).first()
            if engine:
                # 调用引擎的finalize_design方法
                if hasattr(engine, 'finalize_design'):
                    engine.finalize_design(project.payload)
                
                self.db.commit()
                return {"success": True, "engine_id": engine.id, "engine_code": engine.code}
        
        return {"success": False, "error": "引擎ID不存在"}
    
    def _finalize_chassis(self, project: ResearchProject) -> Dict[str, Any]:
        """完成底盘研发"""
        from backend.models.engineering import Chassis
        
        chassis_id = project.payload.get("chassis_id")
        if chassis_id:
            chassis = self.db.query(Chassis).filter(Chassis.id == chassis_id).first()
            if chassis:
                if hasattr(chassis, 'finalize_design'):
                    chassis.finalize_design(project.payload)
                
                self.db.commit()
                return {"success": True, "chassis_id": chassis.id, "chassis_code": chassis.code}
        
        return {"success": False, "error": "底盘ID不存在"}
    
    def _finalize_vehicle(self, project: ResearchProject) -> Dict[str, Any]:
        """完成车辆研发"""
        # 车辆研发完成逻辑（待实现）
        return {"success": True, "message": "车辆研发完成"}
    
    def _finalize_tech(self, project: ResearchProject) -> Dict[str, Any]:
        """完成技术研发"""
        from backend.models.technology import CompanyTechnology
        
        tech_node_id = project.payload.get("tech_node_id")
        if tech_node_id:
            company_tech = self.db.query(CompanyTechnology).filter(
                CompanyTechnology.company_id == self.company_id,
                CompanyTechnology.tech_node_id == tech_node_id
            ).first()
            
            if company_tech:
                if hasattr(company_tech, 'finalize_design'):
                    company_tech.finalize_design(project.payload)
                else:
                    # 标记技术为已完成
                    company_tech.status = "COMPLETED"
                    company_tech.research_completed_turn = project.completion_turn
                
                self.db.commit()
                return {"success": True, "tech_node_id": tech_node_id}
        
        return {"success": False, "error": "技术节点不存在"}
    
    def _calculate_experience_gain(self, project: ResearchProject) -> float:
        """
        计算项目完成获得的经验值
        
        Args:
            project: 完成的项目
            
        Returns:
            经验点数
        """
        # 基础经验 = 项目周数 * 成本系数
        base_exp = project.target_weeks * 2.0
        cost_factor = min(project.budget_allocated / 100.0, 2.0)  # 成本越高经验越多，上限2倍
        
        return base_exp * cost_factor
    
    def _notify_factory_familiarity(self, project: ResearchProject, experience_gained: float, current_turn: int) -> None:
        """
        通知FactoryFamiliarity系统项目完成（混合策略）
        
        Args:
            project: 完成的项目
            experience_gained: 获得的经验值
            current_turn: 当前回合
        """
        try:
            # 仅对引擎和底盘项目通知FactoryFamiliarity
            if project.type not in [ProjectType.ENGINE, ProjectType.CHASSIS]:
                return
            
            from backend.models.factory_familiarity import FactoryProcessFamiliarity
            
            # 根据项目类型确定工艺类型
            if project.type == ProjectType.ENGINE:
                # 从payload获取引擎信息
                engine_id = project.payload.get("engine_id")
                if engine_id:
                    from backend.models.engineering import Engine
                    engine = self.db.query(Engine).filter(Engine.id == engine_id).first()
                    if engine:
                        # 构建工艺类型代码（例如：ALUMINUM_ENGINE_V8_TURBO）
                        process_type = f"{engine.material}_ENGINE_{engine.configuration}{engine.cylinder_count}"
                        if engine.induction_type != "NA":
                            process_type += f"_{engine.induction_type}"
                        
                        # 查找或创建FactoryProcessFamiliarity记录
                        # 注意：需要factory_id，这里简化处理，实际应该从项目关联的工厂获取
                        # 暂时跳过，因为需要工厂信息
                        pass
            
            elif project.type == ProjectType.CHASSIS:
                # 从payload获取底盘信息
                chassis_id = project.payload.get("chassis_id")
                if chassis_id:
                    from backend.models.engineering import Chassis
                    chassis = self.db.query(Chassis).filter(Chassis.id == chassis_id).first()
                    if chassis:
                        # 构建工艺类型代码（例如：ALUMINUM_CHASSIS_FR）
                        process_type = f"{chassis.material}_CHASSIS_{chassis.layout}"
                        
                        # 查找或创建FactoryProcessFamiliarity记录
                        # 注意：需要factory_id，这里简化处理
                        pass
            
        except Exception as e:
            # 如果FactoryFamiliarity系统不可用，不影响主流程
            logger.warning(f"通知FactoryFamiliarity失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        序列化为字典（用于保存到数据库）
        
        Returns:
            状态字典
        """
        return {
            "departments": {
                _enum_value(dept_type): {
                    "type": _enum_value(dept.type),
                    "slots_total": dept.slots_total,
                    "familiarity_score": dept.familiarity_score,
                    "familiarity_level": dept.familiarity_level,
                    "active_projects": [
                        {
                            "id": p.id,
                            "type": _enum_value(p.type),
                            "status": _enum_value(p.status),
                            "payload": p.payload,
                            "progress": p.progress,
                            "target_weeks": p.target_weeks,
                            "budget_allocated": p.budget_allocated,
                            "company_id": p.company_id,
                            "game_id": p.game_id,
                            "start_turn": p.start_turn,
                            "completion_turn": p.completion_turn,
                        }
                        for p in dept.active_projects
                    ]
                }
                for dept_type, dept in self.departments.items()
            }
        }
    
    def _from_dict(self, state: Dict[str, Any]) -> Dict[DepartmentType, Department]:
        """
        从字典恢复状态（从数据库加载）
        
        Args:
            state: 状态字典
            
        Returns:
            部门字典
        """
        departments = {}
        
        dept_data = state.get("departments", {})
        
        for dept_type_str, dept_dict in dept_data.items():
            try:
                dept_type = DepartmentType(dept_type_str)
                
                # 恢复项目列表
                projects = []
                for p_dict in dept_dict.get("active_projects", []):
                    project = ResearchProject(
                        id=p_dict["id"],
                        type=ProjectType(p_dict["type"]),
                        status=ProjectStatus(p_dict["status"]),
                        payload=p_dict["payload"],
                        progress=p_dict["progress"],
                        target_weeks=p_dict["target_weeks"],
                        budget_allocated=p_dict["budget_allocated"],
                        company_id=p_dict["company_id"],
                        game_id=p_dict["game_id"],
                        start_turn=p_dict.get("start_turn"),
                        completion_turn=p_dict.get("completion_turn"),
                    )
                    projects.append(project)
                
                # 创建部门
                department = Department(
                    type=dept_type,
                    slots_total=dept_dict.get("slots_total", 2),
                    active_projects=projects,
                    familiarity_score=dept_dict.get("familiarity_score", 0.0),
                    familiarity_level=dept_dict.get("familiarity_level", 1),
                )
                
                # 重新计算加成（确保一致性）
                department._update_bonuses()
                
                departments[dept_type] = department
                
            except (ValueError, KeyError) as e:
                logger.warning(f"恢复部门 {dept_type_str} 失败: {e}，使用默认值")
                departments[DepartmentType(dept_type_str)] = Department(type=DepartmentType(dept_type_str))
        
        # 确保所有4个部门都存在
        for dept_type in DepartmentType:
            if dept_type not in departments:
                departments[dept_type] = Department(type=dept_type)
        
        return departments
    
    def get_department(self, dept_type: DepartmentType) -> Optional[Department]:
        """获取指定部门"""
        return self.departments.get(dept_type)
    
    def get_active_projects(self, dept_type: Optional[DepartmentType] = None) -> List[ResearchProject]:
        """
        获取活跃项目列表
        
        Args:
            dept_type: 部门类型（None表示所有部门）
            
        Returns:
            项目列表
        """
        if dept_type:
            dept = self.departments.get(dept_type)
            return [p for p in dept.active_projects if p.status == ProjectStatus.ACTIVE] if dept else []
        else:
            all_projects = []
            for dept in self.departments.values():
                all_projects.extend([p for p in dept.active_projects if p.status == ProjectStatus.ACTIVE])
            return all_projects


__all__ = ["RDManager", "ResearchProject", "Department", "ProjectType", "ProjectStatus", "DepartmentType"]
