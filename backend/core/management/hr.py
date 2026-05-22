"""
人力资源系统逻辑
处理高管招聘、解雇、士气、忠诚度管理等
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Tuple, Optional
import logging
import random

from backend.models.staff import Staff
from backend.models.company import Company

logger = logging.getLogger(__name__)


class HRSystem:
    """
    人力资源系统
    
    负责管理公司高管的招聘、解雇、绩效、士气等
    """
    
    # 职位市场价值基准（百万游戏币/年）
    POSITION_BASE_SALARY = {
        "CEO": 2.0,
        "CTO": 1.2,
        "CFO": 1.2,
        "CMO": 1.0,
        "COO": 1.0,
        "ENGINEER": 0.08,
        "DESIGNER": 0.08
    }
    
    @staticmethod
    def generate_staff(
        db: Session,
        game_id: int,
        position: str,
        nationality: str = "USA",
        skill_range: Tuple[float, float] = (40.0, 80.0)
    ) -> Staff:
        """
        生成一个新的员工/高管
        
        Args:
            db: 数据库会话
            game_id: 游戏ID
            position: 职位
            nationality: 国籍
            skill_range: 技能范围（最小值，最大值）
            
        Returns:
            新生成的Staff对象
        """
        # 生成随机名字（简化版，实际应该有名字库）
        first_names = ["John", "Mary", "David", "Sarah", "Michael", "Jennifer", "Robert", "Linda"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        # 生成技能
        skill_min, skill_max = skill_range
        skills = {
            "engineering": random.uniform(skill_min, skill_max),
            "finance": random.uniform(skill_min, skill_max),
            "marketing": random.uniform(skill_min, skill_max),
            "operations": random.uniform(skill_min, skill_max),
            "leadership": random.uniform(skill_min, skill_max)
        }
        
        # 根据职位加强主要技能
        if position == "CTO" or position == "ENGINEER":
            skills["engineering"] += 15
        elif position == "CFO":
            skills["finance"] += 15
        elif position == "CMO":
            skills["marketing"] += 15
        elif position == "COO":
            skills["operations"] += 15
        elif position == "CEO":
            skills["leadership"] += 20
        
        # 限制在0-100
        for key in skills:
            skills[key] = max(0.0, min(100.0, skills[key]))
        
        # 生成个性特征
        traits = {
            "aggression": random.uniform(30.0, 70.0),
            "innovation": random.uniform(30.0, 70.0),
            "risk_tolerance": random.uniform(30.0, 70.0),
            "loyalty": random.uniform(40.0, 80.0)
        }
        
        # 年龄和经验
        age = random.randint(35, 55)
        years_experience = age - 25
        
        # 计算市场价值
        base_salary = HRSystem.POSITION_BASE_SALARY.get(position, 0.1)
        primary_skill = max(skills.values())
        skill_multiplier = 0.5 + (primary_skill / 100.0) * 1.0
        experience_multiplier = 1.0 + (years_experience / 30.0) * 0.5
        
        market_value = base_salary * skill_multiplier * experience_multiplier
        
        # 创建员工
        staff = Staff(
            game_id=game_id,
            company_id=None,  # 初始在人才市场
            first_name=first_name,
            last_name=last_name,
            age=age,
            nationality=nationality,
            position=position,
            skill_engineering=skills["engineering"],
            skill_finance=skills["finance"],
            skill_marketing=skills["marketing"],
            skill_operations=skills["operations"],
            skill_leadership=skills["leadership"],
            trait_aggression=traits["aggression"],
            trait_innovation=traits["innovation"],
            trait_risk_tolerance=traits["risk_tolerance"],
            trait_loyalty=traits["loyalty"],
            current_morale=70.0,
            current_loyalty=traits["loyalty"],
            years_experience=years_experience,
            annual_salary=0.0,
            market_value=market_value,
            is_available=True
        )
        
        db.add(staff)
        db.commit()
        
        logger.info(f"Generated {position} {staff.full_name} with market value {market_value:.2f}M")
        
        return staff
    
    @staticmethod
    def hire_staff(
        db: Session,
        company_id: int,
        staff_id: int,
        offered_salary: float,
        current_turn: int
    ) -> Tuple[bool, str]:
        """
        雇佣员工
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            staff_id: 员工ID
            offered_salary: 提供的年薪（百万游戏币）
            current_turn: 当前回合
            
        Returns:
            (是否成功, 消息)
        """
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return False, "公司不存在"
        
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            return False, "员工不存在"
        
        if not staff.is_available:
            return False, f"{staff.full_name} 不在人才市场"
        
        if staff.company_id is not None:
            return False, f"{staff.full_name} 已被雇佣"
        
        # 检查公司是否有同职位的人（简化版，实际可能允许多个）
        existing_position = db.query(Staff).filter(
            Staff.company_id == company_id,
            Staff.position == staff.position
        ).first()
        
        if existing_position and staff.position in ["CEO", "CTO", "CFO", "CMO", "COO"]:
            return False, f"公司已有{staff.position}：{existing_position.full_name}"
        
        # 检查资金
        if company.cash < offered_salary / 12:  # 至少支付一个月
            return False, f"资金不足（需要 {offered_salary/12:.2f}M 作为首月工资）"
        
        # 检查薪资是否满足员工期望
        if offered_salary < staff.market_value * 0.8:
            return False, f"{staff.full_name} 拒绝了报价（期望至少 {staff.market_value*0.8:.2f}M）"
        
        # 接受概率（薪资越高，接受概率越高）
        salary_ratio = offered_salary / staff.market_value
        accept_probability = 0.5 + min(salary_ratio - 0.8, 0.5)  # 0.5-1.0
        
        if random.random() > accept_probability:
            return False, f"{staff.full_name} 拒绝了报价"
        
        # 雇佣成功
        staff.company_id = company_id
        staff.annual_salary = offered_salary
        staff.hire_turn = current_turn
        staff.is_available = False
        staff.current_morale = 80.0  # 新员工士气较高
        staff.current_loyalty = staff.trait_loyalty
        
        db.commit()
        
        logger.info(f"Company {company_id} hired {staff.full_name} as {staff.position} for {offered_salary:.2f}M/year")
        
        return True, f"成功雇佣 {staff.full_name}（{staff.position}），年薪 {offered_salary:.2f}M"
    
    @staticmethod
    def fire_staff(
        db: Session,
        company_id: int,
        staff_id: int,
        current_turn: int,
        severance_multiplier: float = 1.0
    ) -> Tuple[bool, str]:
        """
        解雇员工
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            staff_id: 员工ID
            current_turn: 当前回合
            severance_multiplier: 遣散费倍数（通常0.5-2.0）
            
        Returns:
            (是否成功, 消息)
        """
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return False, "公司不存在"
        
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            return False, "员工不存在"
        
        if staff.company_id != company_id:
            return False, f"{staff.full_name} 不属于该公司"
        
        # 计算遣散费
        severance = staff.annual_salary * severance_multiplier
        
        if company.cash < severance:
            return False, f"资金不足支付遣散费（需要 {severance:.2f}M）"
        
        # 支付遣散费
        company.cash -= severance
        
        # 解雇
        staff.company_id = None
        staff.fire_turn = current_turn
        staff.is_available = True
        staff.current_loyalty -= 30  # 被解雇降低忠诚度
        staff.current_loyalty = max(0.0, staff.current_loyalty)
        
        # 影响公司员工士气（全体员工）
        all_staff = db.query(Staff).filter(Staff.company_id == company_id).all()
        for s in all_staff:
            s.current_morale -= 5  # 解雇事件降低士气
            s.current_morale = max(0.0, s.current_morale)
        
        db.commit()
        
        logger.info(f"Company {company_id} fired {staff.full_name}, paid severance {severance:.2f}M")
        
        return True, f"解雇 {staff.full_name}，支付遣散费 {severance:.2f}M"
    
    @staticmethod
    def update_staff_morale_and_loyalty(
        db: Session,
        company_id: int,
        company_performance_score: float
    ) -> List[Dict]:
        """
        更新公司所有员工的士气和忠诚度（每回合调用）
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            company_performance_score: 公司业绩评分 0-100
            
        Returns:
            事件列表（如有员工准备离职等）
        """
        events = []
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return events
        
        all_staff = db.query(Staff).filter(Staff.company_id == company_id).all()
        
        for staff in all_staff:
            # 检查薪资满意度
            salary_satisfied = not staff.is_underpaid()
            
            # 更新士气
            old_morale = staff.current_morale
            staff.update_morale(company_performance_score, salary_satisfied)
            
            # 更新忠诚度（受士气和薪资影响）
            loyalty_change = 0.0
            
            if salary_satisfied:
                loyalty_change += 1.0
            else:
                loyalty_change -= 2.0
            
            if staff.current_morale > 70:
                loyalty_change += 1.0
            elif staff.current_morale < 30:
                loyalty_change -= 3.0
            
            staff.current_loyalty += loyalty_change
            staff.current_loyalty = max(0.0, min(100.0, staff.current_loyalty))
            
            # 更新疲劳度（简化：每回合增加，休假或低工作量降低）
            staff.fatigue_level += random.uniform(0.5, 2.0)
            staff.fatigue_level = max(0.0, min(100.0, staff.fatigue_level))
            
            # 更新市场价值
            staff.update_market_value()
            
            # 检查跳槽风险
            turnover_risk = staff.calculate_turnover_risk()
            
            if turnover_risk > 0.5:
                events.append({
                    "staff_id": staff.id,
                    "staff_name": staff.full_name,
                    "position": staff.position,
                    "event": "high_turnover_risk",
                    "risk": turnover_risk,
                    "reason": "低士气或低薪资"
                })
            
            # 检查是否实际离职（概率事件）
            if random.random() < turnover_risk / 12:  # 月度概率
                # 员工离职
                staff.company_id = None
                staff.is_available = True
                
                events.append({
                    "staff_id": staff.id,
                    "staff_name": staff.full_name,
                    "position": staff.position,
                    "event": "resigned",
                    "reason": "士气和忠诚度过低"
                })
                
                logger.warning(f"{staff.full_name} resigned from company {company_id}")
            
            # 检查退休
            if staff.age >= staff.retirement_age:
                if random.random() < 0.1:  # 10%每月退休概率
                    staff.is_retired = True
                    staff.company_id = None
                    staff.is_available = False
                    
                    events.append({
                        "staff_id": staff.id,
                        "staff_name": staff.full_name,
                        "position": staff.position,
                        "event": "retired",
                        "reason": f"年龄{staff.age}"
                    })
                    
                    logger.info(f"{staff.full_name} retired from company {company_id}")
        
        db.commit()
        
        return events
    
    @staticmethod
    def calculate_executive_bonus(
        db: Session,
        company_id: int
    ) -> float:
        """
        计算并发放高管奖金
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            
        Returns:
            总奖金金额（百万游戏币）
        """
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return 0.0
        
        # 基于公司利润的奖金池
        if company.quarterly_profit <= 0:
            return 0.0
        
        bonus_pool = company.quarterly_profit * 0.05  # 5%的利润作为奖金
        
        executives = db.query(Staff).filter(
            Staff.company_id == company_id,
            Staff.position.in_(["CEO", "CTO", "CFO", "CMO", "COO"])
        ).all()
        
        if not executives:
            return 0.0
        
        total_paid = 0.0
        
        for exec in executives:
            # 根据绩效和设定的奖金比例发放
            individual_bonus = exec.annual_salary * exec.bonus_percentage
            
            # 绩效调整
            effectiveness = exec.calculate_effectiveness()
            individual_bonus *= effectiveness
            
            # 不超过奖金池
            individual_bonus = min(individual_bonus, bonus_pool - total_paid)
            
            if individual_bonus > 0:
                # 发放奖金（增加士气和忠诚度）
                exec.current_morale = min(100.0, exec.current_morale + 5)
                exec.current_loyalty = min(100.0, exec.current_loyalty + 3)
                
                total_paid += individual_bonus
                
                logger.info(f"Paid bonus {individual_bonus:.2f}M to {exec.full_name}")
        
        company.cash -= total_paid
        db.commit()
        
        return total_paid
    
    @staticmethod
    def get_available_candidates(
        db: Session,
        game_id: int,
        position: Optional[str] = None
    ) -> List[Dict]:
        """
        获取人才市场上的候选人
        
        Args:
            db: 数据库会话
            game_id: 游戏ID
            position: 职位过滤（可选）
            
        Returns:
            候选人信息列表
        """
        query = db.query(Staff).filter(
            Staff.game_id == game_id,
            Staff.is_available == True,
            Staff.is_retired == False
        )
        
        if position:
            query = query.filter(Staff.position == position)
        
        candidates = query.all()
        
        result = []
        for staff in candidates:
            result.append({
                "id": staff.id,
                "name": staff.full_name,
                "position": staff.position,
                "age": staff.age,
                "primary_skill": staff.get_primary_skill(),
                "market_value": staff.market_value,
                "experience": staff.years_experience,
                "traits": {
                    "aggression": staff.trait_aggression,
                    "innovation": staff.trait_innovation,
                    "risk_tolerance": staff.trait_risk_tolerance,
                    "loyalty": staff.trait_loyalty
                }
            })
        
        return result
    
    @staticmethod
    def get_company_staff_overview(
        db: Session,
        company_id: int
    ) -> Dict:
        """
        获取公司人员概览
        
        Returns:
            人员信息字典
        """
        staff_list = db.query(Staff).filter(Staff.company_id == company_id).all()
        
        overview = {
            "total_count": len(staff_list),
            "total_salary": sum(s.annual_salary for s in staff_list),
            "average_morale": sum(s.current_morale for s in staff_list) / len(staff_list) if staff_list else 0,
            "average_loyalty": sum(s.current_loyalty for s in staff_list) / len(staff_list) if staff_list else 0,
            "high_risk_count": sum(1 for s in staff_list if s.calculate_turnover_risk() > 0.5),
            "positions": {}
        }
        
        for staff in staff_list:
            overview["positions"][staff.position] = {
                "name": staff.full_name,
                "skill": staff.get_primary_skill(),
                "effectiveness": staff.calculate_effectiveness(),
                "morale": staff.current_morale,
                "loyalty": staff.current_loyalty,
                "salary": staff.annual_salary,
                "turnover_risk": staff.calculate_turnover_risk()
            }
        
        return overview


__all__ = ["HRSystem"]


