"""
可靠性增长系统
处理基于生产数量的可靠性增长和质量爬坡
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from backend.models.production_history import ProductionHistory
from backend.models.engineering import CarTrim

logger = logging.getLogger(__name__)


class ReliabilityGrowthSystem:
    """
    可靠性增长系统
    
    实现学习曲线效应：
    - 早期生产：可靠性较低（0.95倍）
    - 稳定生产：可靠性正常（1.0倍）
    - 优化生产：可靠性提升（1.05倍）
    - 成熟生产：可靠性最高（1.10倍）
    """
    
    @staticmethod
    def get_or_create_production_history(
        db: Session,
        company_id: int,
        car_trim_id: int,
        factory_id: int,
        game_id: int
    ) -> ProductionHistory:
        """
        获取或创建生产历史记录
        
        Args:
            db: 数据库会话
            company_id: 公司ID
            car_trim_id: 车型ID
            factory_id: 工厂ID
            game_id: 游戏ID
            
        Returns:
            ProductionHistory 对象
        """
        history = db.query(ProductionHistory).filter(
            ProductionHistory.company_id == company_id,
            ProductionHistory.car_trim_id == car_trim_id,
            ProductionHistory.factory_id == factory_id
        ).first()
        
        if not history:
            history = ProductionHistory(
                game_id=game_id,
                company_id=company_id,
                car_trim_id=car_trim_id,
                factory_id=factory_id,
                total_units_produced=0,
                current_reliability_multiplier=0.95,  # 初始为早期阶段
                quality_ramp_up_stage="EARLY"
            )
            db.add(history)
            db.flush()
        
        return history
    
    @staticmethod
    def update_reliability_from_production(
        history: ProductionHistory,
        units_produced_this_turn: int,
        current_turn: int,
        defect_rate: float = 0.02
    ) -> float:
        """
        根据生产数量更新可靠性倍数
        
        Args:
            history: 生产历史记录
            units_produced_this_turn: 本回合生产数量
            current_turn: 当前回合
            defect_rate: 本回合缺陷率
            
        Returns:
            更新后的可靠性倍数
        """
        # 更新生产统计
        history.update_production(units_produced_this_turn, current_turn, defect_rate)
        
        # 重新计算可靠性倍数
        history.update_reliability_from_production()
        
        logger.debug(
            f"Production history updated: {history.total_units_produced} units, "
            f"stage={history.quality_ramp_up_stage}, "
            f"multiplier={history.current_reliability_multiplier:.3f}"
        )
        
        return history.current_reliability_multiplier
    
    @staticmethod
    def calculate_quality_ramp_up(units_produced: int) -> str:
        """
        计算质量爬坡阶段
        
        Args:
            units_produced: 累计生产数量
            
        Returns:
            质量阶段：EARLY/MID/MATURE/OPTIMIZED
        """
        if units_produced < 1000:
            return "EARLY"
        elif units_produced < 5000:
            return "MID"
        elif units_produced < 20000:
            return "MATURE"
        else:
            return "OPTIMIZED"
    
    @staticmethod
    def get_effective_reliability(
        base_reliability: float,
        history: Optional[ProductionHistory]
    ) -> float:
        """
        获取有效可靠性（基础 × 经验倍数）
        
        Args:
            base_reliability: 基础可靠性分数（0-100）
            history: 生产历史记录（可选）
            
        Returns:
            有效可靠性分数（0-100）
        """
        if history is None:
            # 没有生产历史，使用基础可靠性（假设是早期阶段）
            multiplier = 0.95
        else:
            multiplier = history.current_reliability_multiplier
        
        effective_reliability = base_reliability * multiplier
        
        # 限制在0-100范围内
        effective_reliability = max(0.0, min(100.0, effective_reliability))
        
        return round(effective_reliability, 2)
    
    @staticmethod
    def apply_reliability_growth_to_car_trim(
        db: Session,
        car_trim: CarTrim,
        history: Optional[ProductionHistory]
    ) -> None:
        """
        将可靠性增长应用到车型的最终可靠性分数
        
        Args:
            db: 数据库会话
            car_trim: 车型对象
            history: 生产历史记录（可选）
        """
        if history is None:
            # 没有生产历史，使用基础可靠性
            effective_reliability = car_trim.final_reliability_score
        else:
            # 获取基础可靠性（从当前分数反推，或使用原始值）
            # 注意：这里假设final_reliability_score是基础值
            # 如果需要，可以添加base_reliability_score字段
            base_reliability = car_trim.final_reliability_score
            
            # 应用增长倍数
            effective_reliability = ReliabilityGrowthSystem.get_effective_reliability(
                base_reliability, history
            )
            
            # 更新车型的最终可靠性
            car_trim.final_reliability_score = effective_reliability
            
            logger.debug(
                f"Applied reliability growth to {car_trim.name}: "
                f"{base_reliability:.1f} -> {effective_reliability:.1f} "
                f"(multiplier={history.current_reliability_multiplier:.3f})"
            )
    
    @staticmethod
    def get_reliability_growth_info(
        history: Optional[ProductionHistory]
    ) -> Dict[str, Any]:
        """
        获取可靠性增长信息（用于前端显示）
        
        Args:
            history: 生产历史记录（可选）
            
        Returns:
            信息字典
        """
        if history is None:
            return {
                "stage": "EARLY",
                "multiplier": 0.95,
                "units_produced": 0,
                "next_stage_units": 1000,
                "description": "尚未开始生产"
            }
        
        units = history.total_units_produced
        stage = history.quality_ramp_up_stage
        
        # 计算下一阶段需要的数量
        if stage == "EARLY":
            next_stage_units = 1000
            description = "早期生产阶段：可靠性较低，存在学习曲线"
        elif stage == "MID":
            next_stage_units = 5000
            description = "稳定生产阶段：可靠性正常"
        elif stage == "MATURE":
            next_stage_units = 20000
            description = "优化生产阶段：可靠性提升"
        else:  # OPTIMIZED
            next_stage_units = None
            description = "成熟生产阶段：可靠性最高"
        
        return {
            "stage": stage,
            "multiplier": history.current_reliability_multiplier,
            "units_produced": units,
            "next_stage_units": next_stage_units,
            "description": description,
            "defect_rate": history.average_defect_rate
        }


__all__ = ["ReliabilityGrowthSystem"]


