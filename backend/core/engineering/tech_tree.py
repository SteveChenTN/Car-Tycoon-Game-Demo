"""
技术树系统逻辑
处理技术解锁、研发进度、突破检查等
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Tuple, Optional
import logging
import math
import random

from backend.models.technology import TechNode, CompanyTechnology
from backend.models.company import Company
from backend.models.game_state import GameState

logger = logging.getLogger(__name__)


class TechTreeSystem:
    """
    技术树系统
    
    负责管理技术依赖关系、研发进度、突破概率等
    """
    
    @staticmethod
    def initialize_company_tech_tree(
        db: Session,
        company_id: int,
        game_id: int
    ) -> int:
        """
        为公司初始化技术树
        创建所有技术节点的CompanyTechnology记录
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            game_id: 游戏ID
            
        Returns:
            初始化的技术数量
        """
        # 获取游戏中的所有技术节点
        tech_nodes = db.query(TechNode).filter(TechNode.game_id == game_id).all()
        
        # 获取公司当前年份和技术等级
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        initialized_count = 0
        
        for tech_node in tech_nodes:
            # 检查是否已存在记录
            existing = db.query(CompanyTechnology).filter(
                CompanyTechnology.company_id == company_id,
                CompanyTechnology.tech_node_id == tech_node.id
            ).first()
            
            if existing:
                continue
            
            # 确定初始状态
            initial_status = "LOCKED"
            
            # 检查是否满足前置条件（无前置条件的为起始技术）
            prerequisites = tech_node.get_prerequisites()
            if not prerequisites:
                initial_status = "AVAILABLE"
            
            # 创建记录
            company_tech = CompanyTechnology(
                company_id=company_id,
                tech_node_id=tech_node.id,
                status=initial_status,
                research_efficiency=company.rd_efficiency
            )
            
            db.add(company_tech)
            initialized_count += 1
        
        db.commit()
        logger.info(f"Initialized {initialized_count} technologies for company {company_id}")
        
        return initialized_count
    
    @staticmethod
    def check_tech_available(
        db: Session,
        company_id: int,
        tech_node_id: int
    ) -> Tuple[bool, str]:
        """
        检查技术是否可供研发
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            tech_node_id: 技术节点ID
            
        Returns:
            (是否可用, 原因说明)
        """
        tech_node = db.query(TechNode).filter(TechNode.id == tech_node_id).first()
        if not tech_node:
            return False, "技术不存在"
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return False, "公司不存在"
        
        company_tech = db.query(CompanyTechnology).filter(
            CompanyTechnology.company_id == company_id,
            CompanyTechnology.tech_node_id == tech_node_id
        ).first()
        
        if not company_tech:
            return False, "公司未初始化此技术"
        
        # 检查是否已完成
        if company_tech.status == "COMPLETED":
            return False, "技术已解锁"
        
        # 检查是否正在研发
        if company_tech.status == "RESEARCHING":
            return True, "正在研发中"
        
        # 检查技术等级要求
        if company.tech_level < tech_node.min_tech_level:
            return False, f"需要技术等级 {tech_node.min_tech_level}（当前 {company.tech_level}）"
        
        # 检查前置技术
        prerequisites = tech_node.get_prerequisites()
        if prerequisites:
            for prereq_code in prerequisites:
                prereq_node = db.query(TechNode).filter(
                    TechNode.game_id == tech_node.game_id,
                    TechNode.tech_code == prereq_code
                ).first()
                
                if not prereq_node:
                    return False, f"前置技术 {prereq_code} 不存在"
                
                prereq_company_tech = db.query(CompanyTechnology).filter(
                    CompanyTechnology.company_id == company_id,
                    CompanyTechnology.tech_node_id == prereq_node.id
                ).first()
                
                if not prereq_company_tech or prereq_company_tech.status != "COMPLETED":
                    return False, f"需要先解锁技术：{prereq_node.name}"
        
        # 检查年份门控（历史约束）
        year_check_result = TechTreeSystem.check_year_gating(db, tech_node)
        if not year_check_result[0]:
            return False, year_check_result[1]
        
        return True, "可以开始研发"
    
    @staticmethod
    def start_research(
        db: Session,
        company_id: int,
        tech_node_id: int,
        monthly_investment: float,
        current_turn: int,
        assigned_engineers: int = 0
    ) -> Tuple[bool, str]:
        """
        开始研发技术
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            tech_node_id: 技术节点ID
            monthly_investment: 每月投资（百万游戏币）
            current_turn: 当前回合
            assigned_engineers: 分配的工程师数量
            
        Returns:
            (是否成功, 消息)
        """
        # 检查是否可以研发
        can_research, reason = TechTreeSystem.check_tech_available(db, company_id, tech_node_id)
        
        if not can_research and "正在研发中" not in reason:
            return False, reason
        
        tech_node = db.query(TechNode).filter(TechNode.id == tech_node_id).first()
        company = db.query(Company).filter(Company.id == company_id).first()
        company_tech = db.query(CompanyTechnology).filter(
            CompanyTechnology.company_id == company_id,
            CompanyTechnology.tech_node_id == tech_node_id
        ).first()
        
        # 检查资金
        if company.cash < monthly_investment:
            return False, f"资金不足（需要 {monthly_investment:.2f}M，当前 {company.cash:.2f}M）"
        
        # 更新状态
        if company_tech.status == "AVAILABLE":
            company_tech.status = "RESEARCHING"
            company_tech.research_started_turn = current_turn
            logger.info(f"Company {company_id} started researching {tech_node.name}")
        
        # 更新投资
        company_tech.monthly_investment = monthly_investment
        company_tech.assigned_engineers = assigned_engineers
        company_tech.research_efficiency = company.rd_efficiency
        
        # 计算预计完成回合
        optimal_investment = tech_node.base_research_cost / tech_node.base_research_time
        if monthly_investment > 0:
            estimated_months = tech_node.base_research_cost / monthly_investment
            estimated_months /= company.rd_efficiency  # 效率加成
            company_tech.estimated_completion_turn = current_turn + int(estimated_months)
        
        db.commit()
        
        return True, f"开始研发 {tech_node.name}，预计投入 {monthly_investment:.2f}M/月"
    
    @staticmethod
    def process_research_turn(
        db: Session,
        company_id: int,
        current_turn: int
    ) -> List[Dict]:
        """
        处理公司所有正在研发的技术（每回合调用）
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            current_turn: 当前回合
            
        Returns:
            事件列表：[{"tech_name": "xxx", "event": "progress/breakthrough/completed"}]
        """
        events = []
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return events
        
        # 获取所有正在研发的技术
        researching_techs = db.query(CompanyTechnology).filter(
            CompanyTechnology.company_id == company_id,
            CompanyTechnology.status == "RESEARCHING"
        ).all()
        
        for company_tech in researching_techs:
            tech_node = db.query(TechNode).filter(TechNode.id == company_tech.tech_node_id).first()
            
            if not tech_node:
                continue
            
            # 扣除资金
            if company.cash < company_tech.monthly_investment:
                # 资金不足，暂停研发
                company_tech.monthly_investment = 0
                events.append({
                    "tech_name": tech_node.name,
                    "event": "suspended",
                    "reason": "资金不足"
                })
                logger.warning(f"Research on {tech_node.name} suspended due to insufficient funds")
                continue
            
            company.cash -= company_tech.monthly_investment
            company_tech.total_invested += company_tech.monthly_investment
            
            # 计算研发进度
            progress_delta = TechTreeSystem._calculate_research_progress(
                tech_node=tech_node,
                company_tech=company_tech,
                company=company
            )
            
            company_tech.research_progress = min(1.0, company_tech.research_progress + progress_delta)
            
            # 检查是否完成
            if company_tech.research_progress >= 1.0:
                # 研发完成
                company_tech.status = "COMPLETED"
                company_tech.research_completed_turn = current_turn
                company_tech.completion_quality = TechTreeSystem._calculate_completion_quality(
                    company_tech, company
                )
                
                # 应用技术效果
                TechTreeSystem._apply_tech_effects(db, company, tech_node)
                
                # 解锁后续技术
                TechTreeSystem._unlock_dependent_techs(db, company_id, tech_node)
                
                events.append({
                    "tech_name": tech_node.name,
                    "event": "completed",
                    "quality": company_tech.completion_quality
                })
                
                logger.info(f"Company {company_id} completed research on {tech_node.name}")
            else:
                # 尝试突破（概率事件）
                breakthrough_occurred = TechTreeSystem._check_breakthrough(
                    tech_node, company_tech, company
                )
                
                if breakthrough_occurred:
                    events.append({
                        "tech_name": tech_node.name,
                        "event": "breakthrough",
                        "progress": company_tech.research_progress
                    })
                    logger.info(f"Research breakthrough on {tech_node.name}!")
            
            company_tech.last_breakthrough_check_turn = current_turn
        
        db.commit()
        
        return events
    
    @staticmethod
    def _calculate_research_progress(
        tech_node: TechNode,
        company_tech: CompanyTechnology,
        company: Company
    ) -> float:
        """
        计算单回合研发进度增量
        
        Returns:
            进度增量 0-1
        """
        # 基础进度 = 投资 / 总成本
        base_progress = company_tech.monthly_investment / tech_node.base_research_cost
        
        # 效率修正
        efficiency_factor = company_tech.research_efficiency
        
        # 难度修正
        difficulty_factor = 1.0 / tech_node.difficulty_rating
        
        # 工程师数量加成（边际递减）
        engineer_bonus = 1.0
        if company_tech.assigned_engineers > 0:
            engineer_bonus = 1.0 + math.log(1 + company_tech.assigned_engineers / 10) * 0.2
        
        progress = base_progress * efficiency_factor * difficulty_factor * engineer_bonus
        
        return progress
    
    @staticmethod
    def _check_breakthrough(
        tech_node: TechNode,
        company_tech: CompanyTechnology,
        company: Company
    ) -> bool:
        """
        检查是否发生研发突破（加速进度）
        
        Returns:
            是否发生突破
        """
        company_tech.breakthrough_attempts += 1
        
        # 基础突破概率（每月）
        base_probability = 0.05  # 5%
        
        # 投资强度影响
        optimal_investment = tech_node.base_research_cost / tech_node.base_research_time
        if optimal_investment > 0:
            investment_ratio = company_tech.monthly_investment / optimal_investment
            # 最优投资时概率最高，过低或过高都降低
            if investment_ratio < 0.5:
                investment_factor = investment_ratio * 2  # 0-1
            elif investment_ratio < 1.5:
                investment_factor = 1.0  # 最优区间
            else:
                investment_factor = 1.0 / (investment_ratio - 0.5)  # 递减
        else:
            investment_factor = 0.5
        
        # 难度影响（越难越不容易突破）
        difficulty_factor = 1.0 / math.sqrt(tech_node.difficulty_rating)
        
        # 工程师影响
        engineer_factor = 1.0 + (company_tech.assigned_engineers / 50.0)
        
        # 随机因素
        random_factor = random.uniform(0.5, 1.5)
        
        breakthrough_prob = (base_probability * investment_factor * 
                           difficulty_factor * engineer_factor * random_factor)
        
        if random.random() < breakthrough_prob:
            # 突破！增加进度
            bonus_progress = random.uniform(0.05, 0.15)
            company_tech.research_progress = min(1.0, company_tech.research_progress + bonus_progress)
            return True
        
        return False
    
    @staticmethod
    def _calculate_completion_quality(
        company_tech: CompanyTechnology,
        company: Company
    ) -> float:
        """
        计算完成质量（影响技术效果）
        
        Returns:
            质量评分 0-1
        """
        base_quality = 0.7
        
        # 效率加成
        efficiency_bonus = (company.rd_efficiency - 1.0) * 0.2
        
        # 工程师数量加成
        engineer_bonus = min(company_tech.assigned_engineers / 100.0, 0.2)
        
        # 随机因素
        random_factor = random.uniform(-0.1, 0.1)
        
        quality = base_quality + efficiency_bonus + engineer_bonus + random_factor
        
        return max(0.3, min(1.0, quality))
    
    @staticmethod
    def _apply_tech_effects(
        db: Session,
        company: Company,
        tech_node: TechNode
    ) -> None:
        """
        应用技术解锁的效果到公司
        
        Args:
            db: 数据库会话
            company: 公司对象
            tech_node: 技术节点
        """
        modifiers = tech_node.get_stat_modifiers()
        
        # 应用属性修正
        if "rd_efficiency" in modifiers:
            company.rd_efficiency *= modifiers["rd_efficiency"]
            logger.info(f"Company {company.id} R&D efficiency: {company.rd_efficiency:.2f}")
        
        if "production_efficiency" in modifiers:
            company.production_efficiency *= modifiers["production_efficiency"]
            logger.info(f"Company {company.id} production efficiency: {company.production_efficiency:.2f}")
        
        if "tech_level_bonus" in modifiers:
            company.tech_level += int(modifiers["tech_level_bonus"])
            company.tech_level = min(10, company.tech_level)
            logger.info(f"Company {company.id} tech level: {company.tech_level}")
        
        db.commit()
    
    @staticmethod
    def _unlock_dependent_techs(
        db: Session,
        company_id: int,
        completed_tech: TechNode
    ) -> None:
        """
        解锁依赖于此技术的后续技术
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            completed_tech: 刚完成的技术节点
        """
        # 查找所有将此技术作为前置条件的技术
        all_techs = db.query(TechNode).filter(
            TechNode.game_id == completed_tech.game_id
        ).all()
        
        for tech_node in all_techs:
            prerequisites = tech_node.get_prerequisites()
            
            if completed_tech.tech_code not in prerequisites:
                continue
            
            # 检查所有前置条件是否都已满足
            all_prereqs_met = True
            for prereq_code in prerequisites:
                prereq_node = db.query(TechNode).filter(
                    TechNode.game_id == tech_node.game_id,
                    TechNode.tech_code == prereq_code
                ).first()
                
                if not prereq_node:
                    all_prereqs_met = False
                    break
                
                prereq_company_tech = db.query(CompanyTechnology).filter(
                    CompanyTechnology.company_id == company_id,
                    CompanyTechnology.tech_node_id == prereq_node.id
                ).first()
                
                if not prereq_company_tech or prereq_company_tech.status != "COMPLETED":
                    all_prereqs_met = False
                    break
            
            if all_prereqs_met:
                # 解锁此技术
                company_tech = db.query(CompanyTechnology).filter(
                    CompanyTechnology.company_id == company_id,
                    CompanyTechnology.tech_node_id == tech_node.id
                ).first()
                
                if company_tech and company_tech.status == "LOCKED":
                    company_tech.status = "AVAILABLE"
                    logger.info(f"Unlocked technology {tech_node.name} for company {company_id}")
        
        db.commit()
    
    @staticmethod
    def get_available_techs(
        db: Session,
        company_id: int
    ) -> List[Dict]:
        """
        获取公司可研发的技术列表
        
        Returns:
            技术信息列表
        """
        company_techs = db.query(CompanyTechnology).filter(
            CompanyTechnology.company_id == company_id,
            CompanyTechnology.status.in_(["AVAILABLE", "RESEARCHING"])
        ).all()
        
        result = []
        for ct in company_techs:
            tech_node = db.query(TechNode).filter(TechNode.id == ct.tech_node_id).first()
            if tech_node:
                result.append({
                    "tech_id": tech_node.id,
                    "tech_code": tech_node.tech_code,
                    "name": tech_node.name,
                    "category": tech_node.category,
                    "status": ct.status,
                    "progress": ct.research_progress,
                    "cost": tech_node.base_research_cost,
                    "time": tech_node.base_research_time,
                    "difficulty": tech_node.difficulty_rating,
                    "monthly_investment": ct.monthly_investment,
                    "total_invested": ct.total_invested
                })
        
        return result
    
    @staticmethod
    def check_year_gating(
        db: Session,
        tech_node: TechNode
    ) -> Tuple[bool, str]:
        """
        检查技术年份门控（历史约束）
        
        防止在历史时间点之前解锁技术，例如不能在1946年研发1980年的技术
        
        Args:
            db: 数据库会话
            tech_node: 技术节点
            
        Returns:
            (是否通过检查, 原因说明)
        """
        # 获取游戏状态
        game_state = db.query(GameState).filter(
            GameState.id == tech_node.game_id
        ).first()
        
        if not game_state:
            return False, "游戏状态不存在"
        
        # 检查当前年份是否达到技术的最早解锁年份
        if game_state.current_year < tech_node.min_year:
            return False, (
                f"技术 {tech_node.name} 最早在 {tech_node.min_year} 年可用"
                f"（当前 {game_state.current_year} 年）"
            )
        
        return True, "年份检查通过"


__all__ = ["TechTreeSystem"]

