"""
工程熟悉度系统
处理公司对特定布局的设计经验积累和加成计算
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Tuple
import logging

from backend.models.engineering_familiarity import EngineeringFamiliarity
from backend.models.engineering import Engine, Chassis

logger = logging.getLogger(__name__)


class FamiliaritySystem:
    """
    工程熟悉度系统
    
    实现专长积累机制：
    - 从引擎/底盘设计提取布局类型
    - 跟踪经验值积累
    - 计算熟悉度加成效果
    """
    
    @staticmethod
    def get_layout_type(engine: Engine) -> str:
        """
        从引擎提取布局类型代码
        
        格式：{CONFIGURATION}{CYLINDERS}_{INDUCTION}
        例如：V8_TURBO, I4_NA, V6_SUPERCHARGED
        
        Args:
            engine: 引擎对象
            
        Returns:
            布局类型代码
        """
        config = engine.configuration
        cylinders = engine.cylinder_count
        induction = engine.induction_type
        
        # 简化induction类型名称
        induction_short = {
            "NA": "NA",
            "TURBO": "TURBO",
            "TWINTURBO": "TURBO",  # 双涡轮也归类为TURBO
            "SUPERCHARGED": "SC"
        }.get(induction, "NA")
        
        layout_type = f"{config}{cylinders}_{induction_short}"
        
        return layout_type
    
    @staticmethod
    def get_chassis_layout_type(chassis: Chassis) -> str:
        """
        从底盘提取布局类型代码
        
        格式：{LAYOUT}_{MATERIAL}
        例如：FR_ALUMINUM, FF_STEEL, AWD_CARBON
        
        Args:
            chassis: 底盘对象
            
        Returns:
            布局类型代码
        """
        layout = chassis.layout
        material = chassis.material
        
        layout_type = f"{layout}_{material}"
        
        return layout_type
    
    @staticmethod
    def get_or_create_familiarity(
        db: Session,
        company_id: int,
        layout_type: str,
        category: str,
        game_id: int
    ) -> EngineeringFamiliarity:
        """
        获取或创建熟悉度记录
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            layout_type: 布局类型代码
            category: 类别（ENGINE/CHASSIS）
            game_id: 游戏ID
            
        Returns:
            EngineeringFamiliarity 对象
        """
        familiarity = db.query(EngineeringFamiliarity).filter(
            EngineeringFamiliarity.company_id == company_id,
            EngineeringFamiliarity.layout_type == layout_type,
            EngineeringFamiliarity.category == category
        ).first()
        
        if not familiarity:
            familiarity = EngineeringFamiliarity(
                game_id=game_id,
                company_id=company_id,
                layout_type=layout_type,
                category=category,
                experience_points=0,
                familiarity_level=1
            )
            db.add(familiarity)
            db.flush()
        
        return familiarity
    
    @staticmethod
    def add_experience(
        db: Session,
        company_id: int,
        layout_type: str,
        category: str,
        experience: int,
        current_turn: int,
        game_id: int
    ) -> EngineeringFamiliarity:
        """
        增加经验值
        
        经验值计算规则：
        - 完成设计：+10经验点
        - 生产1000辆：+5经验点
        - 生产10000辆：+10经验点
        - 生产100000辆：+20经验点
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            layout_type: 布局类型代码
            category: 类别
            experience: 经验点数
            current_turn: 当前回合
            game_id: 游戏ID
            
        Returns:
            更新后的熟悉度对象
        """
        familiarity = FamiliaritySystem.get_or_create_familiarity(
            db, company_id, layout_type, category, game_id
        )
        
        familiarity.add_experience(experience, current_turn)
        familiarity.designs_completed += 1
        
        # 不在这里commit，让调用者控制事务
        db.flush()  # 刷新但不提交
        
        logger.debug(
            f"Added {experience} exp to {layout_type} ({category}) "
            f"for company {company_id}, "
            f"new level: {familiarity.familiarity_level}"
        )
        
        return familiarity
    
    @staticmethod
    def add_design_experience(
        db: Session,
        company_id: int,
        engine: Optional[Engine] = None,
        chassis: Optional[Chassis] = None,
        current_turn: int = 0,
        game_id: int = 0
    ) -> None:
        """
        在设计完成后增加经验值
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            engine: 引擎对象（可选）
            chassis: 底盘对象（可选）
            current_turn: 当前回合
            game_id: 游戏ID
        """
        if engine:
            layout_type = FamiliaritySystem.get_layout_type(engine)
            FamiliaritySystem.add_experience(
                db, company_id, layout_type, "ENGINE", 10, current_turn, game_id
            )
        
        if chassis:
            layout_type = FamiliaritySystem.get_chassis_layout_type(chassis)
            FamiliaritySystem.add_experience(
                db, company_id, layout_type, "CHASSIS", 10, current_turn, game_id
            )
    
    @staticmethod
    def add_production_experience(
        db: Session,
        company_id: int,
        layout_type: str,
        category: str,
        units_produced: int,
        current_turn: int,
        game_id: int
    ) -> None:
        """
        在生产后增加经验值
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            layout_type: 布局类型代码
            category: 类别
            units_produced: 生产数量
            current_turn: 当前回合
            game_id: 游戏ID
        """
        # 根据生产数量计算经验值
        experience = 0
        
        if units_produced >= 100000:
            experience = 20
        elif units_produced >= 10000:
            experience = 10
        elif units_produced >= 1000:
            experience = 5
        
        if experience > 0:
            familiarity = FamiliaritySystem.get_or_create_familiarity(
                db, company_id, layout_type, category, game_id
            )
            familiarity.total_units_produced += units_produced
            
            # 只在达到阈值时增加经验（避免重复计算）
            old_total = familiarity.total_units_produced - units_produced
            
            if old_total < 1000 and familiarity.total_units_produced >= 1000:
                FamiliaritySystem.add_experience(
                    db, company_id, layout_type, category, 5, current_turn, game_id
                )
            elif old_total < 10000 and familiarity.total_units_produced >= 10000:
                FamiliaritySystem.add_experience(
                    db, company_id, layout_type, category, 10, current_turn, game_id
                )
            elif old_total < 100000 and familiarity.total_units_produced >= 100000:
                FamiliaritySystem.add_experience(
                    db, company_id, layout_type, category, 20, current_turn, game_id
                )
            
            # 不在这里commit，让调用者控制事务
        db.flush()  # 刷新但不提交
    
    @staticmethod
    def get_familiarity_bonus(
        db: Session,
        company_id: int,
        layout_type: str,
        category: str
    ) -> Dict[str, float]:
        """
        获取熟悉度加成效果
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            layout_type: 布局类型代码
            category: 类别
            
        Returns:
            加成字典：{"r_d_cost_reduction": 0.1, "reliability_bonus": 0.05, ...}
        """
        familiarity = db.query(EngineeringFamiliarity).filter(
            EngineeringFamiliarity.company_id == company_id,
            EngineeringFamiliarity.layout_type == layout_type,
            EngineeringFamiliarity.category == category
        ).first()
        
        if not familiarity:
            return {
                "r_d_cost_reduction": 0.0,
                "reliability_bonus": 0.0,
                "development_time_reduction": 0.0
            }
        
        return familiarity.get_bonuses()
    
    @staticmethod
    def calculate_familiarity_level(experience_points: int) -> int:
        """
        计算熟悉度等级（1-10）
        
        Args:
            experience_points: 经验点数
            
        Returns:
            熟悉度等级 1-10
        """
        if experience_points < 10:
            return 1
        elif experience_points < 50:
            return 2
        elif experience_points < 100:
            return 3
        elif experience_points < 200:
            return 4
        elif experience_points < 400:
            return 5
        elif experience_points < 800:
            return 6
        elif experience_points < 1500:
            return 7
        elif experience_points < 3000:
            return 8
        elif experience_points < 6000:
            return 9
        else:
            return 10


__all__ = ["FamiliaritySystem"]

