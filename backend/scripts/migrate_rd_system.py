"""
R&D系统迁移脚本
将现有的ResearchProject和EngineeringFamiliarity数据迁移到新的RDManager系统
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from backend.database import get_db
from backend.models.game_state import GameState
from backend.models.company import Company
from backend.logic.rd_manager import RDManager, DepartmentType, ProjectType, ProjectStatus
from backend.models.engineering import ResearchProject as OldResearchProject
from backend.models.engineering_familiarity import EngineeringFamiliarity

logger = logging.getLogger(__name__)


def migrate_research_projects(db: Session, game_id: int) -> Dict[str, Any]:
    """
    迁移ResearchProject数据到RDManager
    
    Args:
        db: 数据库会话
        game_id: 游戏ID
        
    Returns:
        迁移结果统计
    """
    results = {
        "companies_processed": 0,
        "projects_migrated": 0,
        "errors": []
    }
    
    try:
        # 获取所有公司
        companies = db.query(Company).filter(Company.game_id == game_id).all()
        
        for company in companies:
            try:
                # 获取该公司的所有ResearchProject
                old_projects = db.query(OldResearchProject).filter(
                    OldResearchProject.game_id == game_id,
                    OldResearchProject.company_id == company.id,
                    OldResearchProject.actual_completion_turn == None  # 只迁移未完成的
                ).all()
                
                if not old_projects:
                    continue
                
                # 创建或加载RDManager
                rd_manager = RDManager(
                    db=db,
                    company_id=company.id,
                    game_id=game_id
                )
                
                # 迁移每个项目
                for old_project in old_projects:
                    try:
                        # 确定项目类型（目前只有CHASSIS）
                        project_type = ProjectType.CHASSIS
                        
                        # 计算进度
                        if old_project.estimated_completion_turn and old_project.start_turn:
                            total_weeks = old_project.estimated_completion_turn - old_project.start_turn
                            remaining_weeks = old_project.remaining_weeks
                            progress = total_weeks - remaining_weeks if total_weeks > 0 else 0
                        else:
                            progress = 0
                            total_weeks = old_project.remaining_weeks
                        
                        # 创建新的ResearchProject
                        from backend.logic.rd_manager import ResearchProject
                        
                        new_project = ResearchProject(
                            type=project_type,
                            status=ProjectStatus.PAUSED if old_project.is_paused else ProjectStatus.ACTIVE,
                            payload={"chassis_id": old_project.chassis_id},
                            progress=progress,
                            target_weeks=total_weeks,
                            budget_allocated=old_project.total_cost,
                            company_id=company.id,
                            game_id=game_id,
                            start_turn=old_project.start_turn,
                        )
                        
                        # 添加到CHASSIS部门
                        dept = rd_manager.get_department(DepartmentType.CHASSIS)
                        if dept:
                            dept.active_projects.append(new_project)
                            results["projects_migrated"] += 1
                        
                    except Exception as e:
                        error_msg = f"迁移项目 {old_project.id} 失败: {e}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                
                # 保存RDManager状态
                rd_manager.save_state()
                results["companies_processed"] += 1
                
            except Exception as e:
                error_msg = f"迁移公司 {company.id} 的研发项目失败: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        db.commit()
        
    except Exception as e:
        logger.error(f"迁移ResearchProject失败: {e}", exc_info=True)
        db.rollback()
        results["errors"].append(f"迁移失败: {e}")
    
    return results


def migrate_engineering_familiarity(db: Session, game_id: int) -> Dict[str, Any]:
    """
    迁移EngineeringFamiliarity数据到RDManager部门熟悉度
    
    Args:
        db: 数据库会话
        game_id: 游戏ID
        
    Returns:
        迁移结果统计
    """
    results = {
        "companies_processed": 0,
        "familiarity_records_migrated": 0,
        "errors": []
    }
    
    try:
        # 获取所有公司
        companies = db.query(Company).filter(Company.game_id == game_id).all()
        
        for company in companies:
            try:
                # 获取该公司的所有EngineeringFamiliarity记录
                familiarity_records = db.query(EngineeringFamiliarity).filter(
                    EngineeringFamiliarity.game_id == game_id,
                    EngineeringFamiliarity.company_id == company.id
                ).all()
                
                if not familiarity_records:
                    continue
                
                # 创建或加载RDManager
                rd_manager = RDManager(
                    db=db,
                    company_id=company.id,
                    game_id=game_id
                )
                
                # 迁移每个熟悉度记录
                for fam_record in familiarity_records:
                    try:
                        # 根据category确定部门
                        if fam_record.category == "ENGINE":
                            dept_type = DepartmentType.POWERTRAIN
                        elif fam_record.category == "CHASSIS":
                            dept_type = DepartmentType.CHASSIS
                        else:
                            # 未知类别，跳过
                            continue
                        
                        # 获取部门
                        dept = rd_manager.get_department(dept_type)
                        if dept:
                            # 迁移熟悉度分数
                            dept.familiarity_score = float(fam_record.experience_points)
                            dept._update_familiarity_level()  # 重新计算等级和加成
                            results["familiarity_records_migrated"] += 1
                        
                    except Exception as e:
                        error_msg = f"迁移熟悉度记录 {fam_record.id} 失败: {e}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                
                # 保存RDManager状态
                rd_manager.save_state()
                results["companies_processed"] += 1
                
            except Exception as e:
                error_msg = f"迁移公司 {company.id} 的熟悉度失败: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        db.commit()
        
    except Exception as e:
        logger.error(f"迁移EngineeringFamiliarity失败: {e}", exc_info=True)
        db.rollback()
        results["errors"].append(f"迁移失败: {e}")
    
    return results


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    db = next(get_db())
    
    try:
        # 获取游戏
        game = db.query(GameState).first()
        if not game:
            print("错误: 未找到游戏状态")
            return
        
        game_id = game.id
        print(f"开始迁移游戏 {game_id} 的R&D系统...")
        
        # 1. 迁移ResearchProject
        print("\n=== 迁移ResearchProject ===")
        project_results = migrate_research_projects(db, game_id)
        print(f"处理公司数: {project_results['companies_processed']}")
        print(f"迁移项目数: {project_results['projects_migrated']}")
        if project_results['errors']:
            print(f"错误数: {len(project_results['errors'])}")
            for error in project_results['errors'][:5]:  # 只显示前5个错误
                print(f"  - {error}")
        
        # 2. 迁移EngineeringFamiliarity
        print("\n=== 迁移EngineeringFamiliarity ===")
        familiarity_results = migrate_engineering_familiarity(db, game_id)
        print(f"处理公司数: {familiarity_results['companies_processed']}")
        print(f"迁移记录数: {familiarity_results['familiarity_records_migrated']}")
        if familiarity_results['errors']:
            print(f"错误数: {len(familiarity_results['errors'])}")
            for error in familiarity_results['errors'][:5]:
                print(f"  - {error}")
        
        print("\n迁移完成！")
        
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()


