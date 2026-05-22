"""
研发项目处理系统
处理底盘平台的研发进度和完成逻辑
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import logging

from backend.models.engineering import ResearchProject, Chassis
from backend.models.company import Company
from backend.models.game_state import GameState

logger = logging.getLogger(__name__)


class ResearchProjectManager:
    """研发项目管理器"""
    
    @staticmethod
    def process_research_projects(
        db: Session,
        game_id: int,
        current_turn: int
    ) -> Dict[str, Any]:
        """
        处理所有进行中的研发项目（每回合调用）
        
        Args:
            db: 数据库会话
            game_id: 游戏ID
            current_turn: 当前回合
            
        Returns:
            处理结果统计
        """
        results = {
            "projects_processed": 0,
            "projects_completed": 0,
            "chassis_unlocked": []
        }
        
        try:
            # 查询所有未暂停且未完成的研发项目
            active_projects = db.query(ResearchProject).filter(
                ResearchProject.game_id == game_id,
                ResearchProject.is_paused == False,
                ResearchProject.actual_completion_turn == None
            ).all()
            
            for project in active_projects:
                results["projects_processed"] += 1
                
                # 每回合减少1周
                if project.remaining_weeks > 0:
                    project.remaining_weeks -= 1
                
                # 检查是否完成
                if project.remaining_weeks <= 0 or current_turn >= project.estimated_completion_turn:
                    # 项目完成
                    project.remaining_weeks = 0
                    project.actual_completion_turn = current_turn
                    
                    # 解锁底盘
                    chassis = db.query(Chassis).filter(Chassis.id == project.chassis_id).first()
                    if chassis:
                        chassis.is_available = True
                        chassis.development_turn = None  # 开发完成，清除开发回合
                        
                        # 获取公司信息用于日志
                        company = db.query(Company).filter(Company.id == project.company_id).first()
                        company_name = company.name if company else f"公司{project.company_id}"
                        
                        results["chassis_unlocked"].append({
                            "chassis_id": chassis.id,
                            "chassis_name": chassis.name,
                            "chassis_code": chassis.code,
                            "company_id": project.company_id,
                            "company_name": company_name
                        })
                        
                        logger.info(
                            f"✓ 研发项目完成: {chassis.name} ({chassis.code}) - "
                            f"公司: {company_name}, 总成本: {project.total_cost:.2f}M"
                        )
                    
                    results["projects_completed"] += 1
            
            # 不在这里commit，让调用者（game_loop）统一管理事务
            # db.commit() 会在game_loop的最后统一执行
            
            return results
            
        except Exception as e:
            logger.error(f"处理研发项目失败: {e}", exc_info=True)
            # 不在这里rollback，让调用者处理
            return results

