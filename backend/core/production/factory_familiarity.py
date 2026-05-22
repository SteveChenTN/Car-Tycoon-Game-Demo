"""
工厂工艺和材料熟悉度系统
处理工厂对特定制造工艺和材料的经验积累
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple
import logging

from backend.models.factory_familiarity import (
    FactoryProcessFamiliarity, 
    FactoryMaterialFamiliarity
)
from backend.models.engineering import Engine, Chassis

logger = logging.getLogger(__name__)


class FactoryFamiliaritySystem:
    """
    工厂熟悉度系统
    
    实现制造层面的专长积累：
    - 工艺熟悉度：基于生产件数
    - 材料熟悉度：基于加工重量（kg）
    """
    
    @staticmethod
    def get_process_type(component: Engine) -> str:
        """
        从引擎提取工艺类型
        
        格式：{MATERIAL}_ENGINE_{CONFIGURATION}{CYLINDERS}
        例如：CAST_IRON_ENGINE_V8, ALUMINUM_ENGINE_I4
        
        Args:
            component: 引擎对象
            
        Returns:
            工艺类型代码
        """
        material = component.material
        config = component.configuration
        cylinders = component.cylinder_count
        
        process_type = f"{material}_ENGINE_{config}{cylinders}"
        
        return process_type
    
    @staticmethod
    def get_chassis_process_type(chassis: Chassis) -> str:
        """
        从底盘提取工艺类型
        
        格式：{MATERIAL}_CHASSIS_{LAYOUT}
        例如：ALUMINUM_CHASSIS_FR, STEEL_CHASSIS_FF
        
        Args:
            chassis: 底盘对象
            
        Returns:
            工艺类型代码
        """
        material = chassis.material
        layout = chassis.layout
        
        process_type = f"{material}_CHASSIS_{layout}"
        
        return process_type
    
    @staticmethod
    def get_material_types(component: Engine) -> List[Tuple[str, str]]:
        """
        从引擎提取材料类型和应用场景对列表
        
        Args:
            component: 引擎对象
            
        Returns:
            [(material_type, application), ...] 列表
        """
        materials = []
        
        # 引擎材料
        materials.append((component.material, "ENGINE_BLOCK"))
        
        # 如果有增压，可能需要特殊材料处理
        if component.induction_type in ["TURBO", "TWINTURBO"]:
            materials.append(("STEEL", "TURBO_COMPONENTS"))
        
        return materials
    
    @staticmethod
    def get_chassis_material_types(chassis: Chassis) -> List[Tuple[str, str]]:
        """
        从底盘提取材料类型和应用场景对列表
        
        Args:
            chassis: 底盘对象
            
        Returns:
            [(material_type, application), ...] 列表
        """
        return [(chassis.material, "CHASSIS")]
    
    @staticmethod
    def get_or_create_process_familiarity(
        db: Session,
        factory_id: int,
        process_type: str,
        category: str,
        game_id: int
    ) -> FactoryProcessFamiliarity:
        """
        获取或创建工艺熟悉度记录
        
        Args:
            db: 数据库会话
            factory_id: 工厂ID
            process_type: 工艺类型代码
            category: 类别
            game_id: 游戏ID
            
        Returns:
            FactoryProcessFamiliarity 对象
        """
        familiarity = db.query(FactoryProcessFamiliarity).filter(
            FactoryProcessFamiliarity.factory_id == factory_id,
            FactoryProcessFamiliarity.process_type == process_type,
            FactoryProcessFamiliarity.category == category
        ).first()
        
        if not familiarity:
            familiarity = FactoryProcessFamiliarity(
                game_id=game_id,
                factory_id=factory_id,
                process_type=process_type,
                category=category,
                experience_points=0,
                familiarity_level=1
            )
            db.add(familiarity)
            db.flush()
        
        return familiarity
    
    @staticmethod
    def get_or_create_material_familiarity(
        db: Session,
        factory_id: int,
        material_type: str,
        application: str,
        game_id: int
    ) -> FactoryMaterialFamiliarity:
        """
        获取或创建材料熟悉度记录
        
        Args:
            db: 数据库会话
            factory_id: 工厂ID
            material_type: 材料类型
            application: 应用场景
            game_id: 游戏ID
            
        Returns:
            FactoryMaterialFamiliarity 对象
        """
        familiarity = db.query(FactoryMaterialFamiliarity).filter(
            FactoryMaterialFamiliarity.factory_id == factory_id,
            FactoryMaterialFamiliarity.material_type == material_type,
            FactoryMaterialFamiliarity.application == application
        ).first()
        
        if not familiarity:
            familiarity = FactoryMaterialFamiliarity(
                game_id=game_id,
                factory_id=factory_id,
                material_type=material_type,
                application=application,
                experience_points=0,
                familiarity_level=1
            )
            db.add(familiarity)
            db.flush()
        
        return familiarity
    
    @staticmethod
    def add_process_experience(
        db: Session,
        factory_id: int,
        process_type: str,
        category: str,
        units_produced: int,
        current_turn: int,
        game_id: int
    ) -> FactoryProcessFamiliarity:
        """
        增加工艺经验
        
        经验值计算：
        - 生产1件：+1经验点
        - 生产100件：+10经验点（批量加成）
        - 生产1000件：+50经验点（规模加成）
        - 生产10000件：+100经验点（专家级）
        
        Args:
            db: 数据库会话
            factory_id: 工厂ID
            process_type: 工艺类型
            category: 类别
            units_produced: 生产数量
            current_turn: 当前回合
            game_id: 游戏ID
            
        Returns:
            更新后的熟悉度对象
        """
        familiarity = FactoryFamiliaritySystem.get_or_create_process_familiarity(
            db, factory_id, process_type, category, game_id
        )
        
        # 计算经验值（基于生产数量）
        experience = 0
        
        # 基础经验：每件+1点
        experience += units_produced
        
        # 批量加成：每100件额外+9点（总共+10点）
        if units_produced >= 100:
            batches = units_produced // 100
            experience += batches * 9
        
        # 规模加成：每1000件额外+40点（总共+50点）
        if units_produced >= 1000:
            thousands = units_produced // 1000
            experience += thousands * 40
        
        # 专家级加成：每10000件额外+50点（总共+100点）
        if units_produced >= 10000:
            ten_thousands = units_produced // 10000
            experience += ten_thousands * 50
        
        # 更新经验
        old_total = familiarity.total_units_produced
        familiarity.total_units_produced += units_produced
        
        # 只在达到阈值时增加经验（避免重复计算）
        if old_total < 100 and familiarity.total_units_produced >= 100:
            familiarity.add_experience(10, current_turn)
        elif old_total < 1000 and familiarity.total_units_produced >= 1000:
            familiarity.add_experience(50, current_turn)
        elif old_total < 10000 and familiarity.total_units_produced >= 10000:
            familiarity.add_experience(100, current_turn)
        else:
            # 小批量生产，直接增加经验
            if experience > 0:
                familiarity.add_experience(experience, current_turn)
        
        db.commit()
        
        logger.debug(
            f"Added process experience to factory {factory_id}: "
            f"{process_type} ({category}), "
            f"{units_produced} units, "
            f"new level: {familiarity.familiarity_level}"
        )
        
        return familiarity
    
    @staticmethod
    def add_material_experience(
        db: Session,
        factory_id: int,
        material_type: str,
        application: str,
        kg_processed: float,
        current_turn: int,
        game_id: int
    ) -> FactoryMaterialFamiliarity:
        """
        增加材料经验
        
        经验值计算：
        - 加工100kg：+1经验点
        - 加工1000kg：+10经验点
        - 加工10000kg：+50经验点
        - 加工100000kg：+100经验点
        
        Args:
            db: 数据库会话
            factory_id: 工厂ID
            material_type: 材料类型
            application: 应用场景
            kg_processed: 加工重量（公斤）
            current_turn: 当前回合
            game_id: 游戏ID
            
        Returns:
            更新后的熟悉度对象
        """
        familiarity = FactoryFamiliaritySystem.get_or_create_material_familiarity(
            db, factory_id, material_type, application, game_id
        )
        
        # 计算经验值（基于加工重量）
        experience = 0
        
        # 基础经验：每100kg +1点
        experience += int(kg_processed / 100.0)
        
        # 批量加成：每1000kg额外+9点
        if kg_processed >= 1000:
            thousands = int(kg_processed / 1000.0)
            experience += thousands * 9
        
        # 规模加成：每10000kg额外+40点
        if kg_processed >= 10000:
            ten_thousands = int(kg_processed / 10000.0)
            experience += ten_thousands * 40
        
        # 专家级加成：每100000kg额外+50点
        if kg_processed >= 100000:
            hundred_thousands = int(kg_processed / 100000.0)
            experience += hundred_thousands * 50
        
        # 更新经验
        old_total = familiarity.total_kg_processed
        familiarity.total_kg_processed += kg_processed
        
        # 只在达到阈值时增加经验（避免重复计算）
        if old_total < 1000 and familiarity.total_kg_processed >= 1000:
            familiarity.add_experience(10, current_turn)
        elif old_total < 10000 and familiarity.total_kg_processed >= 10000:
            familiarity.add_experience(50, current_turn)
        elif old_total < 100000 and familiarity.total_kg_processed >= 100000:
            familiarity.add_experience(100, current_turn)
        else:
            # 小批量加工，直接增加经验
            if experience > 0:
                familiarity.add_experience(experience, current_turn)
        
        db.commit()
        
        logger.debug(
            f"Added material experience to factory {factory_id}: "
            f"{material_type} ({application}), "
            f"{kg_processed:.0f}kg, "
            f"new level: {familiarity.familiarity_level}"
        )
        
        return familiarity
    
    @staticmethod
    def get_factory_reliability_bonus(
        db: Session,
        factory_id: int,
        component: Engine
    ) -> float:
        """
        获取工厂可靠性总加成（工艺+材料）
        
        Args:
            db: 数据库会话
            factory_id: 工厂ID
            component: 组件对象（Engine或Chassis）
            
        Returns:
            总可靠性加成（百分比，如0.03表示+3%）
        """
        total_bonus = 0.0
        
        # 获取工艺熟悉度加成
        if isinstance(component, Engine):
            process_type = FactoryFamiliaritySystem.get_process_type(component)
            process_fam = db.query(FactoryProcessFamiliarity).filter(
                FactoryProcessFamiliarity.factory_id == factory_id,
                FactoryProcessFamiliarity.process_type == process_type,
                FactoryProcessFamiliarity.category == "ENGINE_MANUFACTURING"
            ).first()
            
            if process_fam:
                total_bonus += process_fam.reliability_bonus
            
            # 获取材料熟悉度加成
            material_types = FactoryFamiliaritySystem.get_material_types(component)
            for material_type, application in material_types:
                material_fam = db.query(FactoryMaterialFamiliarity).filter(
                    FactoryMaterialFamiliarity.factory_id == factory_id,
                    FactoryMaterialFamiliarity.material_type == material_type,
                    FactoryMaterialFamiliarity.application == application
                ).first()
                
                if material_fam:
                    total_bonus += material_fam.reliability_bonus
        
        return round(total_bonus, 4)
    
    @staticmethod
    def calculate_process_familiarity_level(experience_points: int) -> int:
        """
        计算工艺熟悉度等级（1-10）
        
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
    
    @staticmethod
    def calculate_material_familiarity_level(experience_points: int) -> int:
        """
        计算材料熟悉度等级（1-10）
        
        Args:
            experience_points: 经验点数
            
        Returns:
            熟悉度等级 1-10
        """
        # 使用相同的等级计算逻辑
        return FactoryFamiliaritySystem.calculate_process_familiarity_level(experience_points)


__all__ = ["FactoryFamiliaritySystem"]


