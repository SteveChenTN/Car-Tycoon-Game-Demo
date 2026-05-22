"""
工厂重新配置（Retooling）系统
处理生产线切换车型时的时间成本和资金成本计算
"""
from sqlalchemy.orm import Session
from typing import Tuple, Optional
import logging
import math

from backend.models.production import ProductionLine
from backend.models.engineering import CarTrim

logger = logging.getLogger(__name__)


class RetoolingCalculator:
    """
    工厂重新配置计算器
    
    计算生产线切换车型时需要的：
    - 重新配置时间（回合数）
    - 重新配置成本（百万游戏币）
    """
    
    @staticmethod
    def calculate_retooling_time(
        previous_design: Optional[CarTrim],
        new_design: CarTrim,
        factory_level: int
    ) -> int:
        """
        计算重新配置时间（回合数）
        
        影响因素：
        - 设计复杂度差异（车身类型、引擎类型、底盘类型）
        - 工厂等级（高等级工厂配置更快）
        - 是否首次配置（首次配置需要更多时间）
        
        Args:
            previous_design: 之前生产的车型（None表示首次配置）
            new_design: 新车型设计
            factory_level: 工厂等级 1-10
            
        Returns:
            重新配置时间（回合数，最小1回合）
        """
        # 基础时间（月数）
        if previous_design is None:
            # 首次配置：基础2个月
            base_months = 2.0
        else:
            # 切换配置：基础1个月
            base_months = 1.0
            
            # 计算设计差异复杂度
            complexity_diff = RetoolingCalculator._calculate_design_complexity_diff(
                previous_design, new_design
            )
            # 差异越大，时间越长（0-2个月额外时间）
            base_months += complexity_diff * 2.0
        
        # 工厂等级影响（高等级工厂配置更快）
        # 等级1：100%时间，等级10：60%时间
        level_factor = 1.0 - (factory_level - 1) * 0.044  # 每级减少4.4%
        level_factor = max(0.6, min(1.0, level_factor))
        
        # 计算最终时间（转换为回合数，假设1回合=1周，4周=1月）
        total_weeks = base_months * 4.0 * level_factor
        total_turns = max(1, int(math.ceil(total_weeks)))
        
        logger.debug(
            f"Retooling time: {total_turns} turns "
            f"(base={base_months:.1f}mo, level_factor={level_factor:.2f})"
        )
        
        return total_turns
    
    @staticmethod
    def calculate_retooling_cost(
        previous_design: Optional[CarTrim],
        new_design: CarTrim,
        factory_level: int
    ) -> float:
        """
        计算重新配置成本（百万游戏币）
        
        影响因素：
        - 设计复杂度差异
        - 工厂等级（高等级工厂成本更高但效率更高）
        - 模具和工具成本
        
        Args:
            previous_design: 之前生产的车型（None表示首次配置）
            new_design: 新车型设计
            factory_level: 工厂等级 1-10
            
        Returns:
            重新配置成本（百万游戏币）
        """
        # 基础成本
        if previous_design is None:
            # 首次配置：基础50万（模具、工具）
            base_cost = 0.5
        else:
            # 切换配置：基础20万
            base_cost = 0.2
            
            # 设计差异影响成本
            complexity_diff = RetoolingCalculator._calculate_design_complexity_diff(
                previous_design, new_design
            )
            # 差异越大，成本越高（0-30万额外成本）
            base_cost += complexity_diff * 0.3
        
        # 工厂等级影响（高等级工厂需要更精密的工具，成本更高）
        # 但高等级工厂效率更高，所以时间成本更低
        level_cost_factor = 1.0 + (factory_level - 1) * 0.1  # 每级+10%成本
        
        # 车型复杂度影响（基于制造成本）
        # 复杂车型需要更多工具
        design_complexity_factor = 1.0 + (new_design.manufacturing_cost / 10000.0) * 0.1
        design_complexity_factor = min(2.0, design_complexity_factor)  # 最多2倍
        
        total_cost = base_cost * level_cost_factor * design_complexity_factor
        
        logger.debug(
            f"Retooling cost: {total_cost:.2f}M "
            f"(base={base_cost:.2f}M, level_factor={level_cost_factor:.2f}, "
            f"design_factor={design_complexity_factor:.2f})"
        )
        
        return round(total_cost, 2)
    
    @staticmethod
    def _calculate_design_complexity_diff(
        previous_design: CarTrim,
        new_design: CarTrim
    ) -> float:
        """
        计算两个设计之间的复杂度差异（0-1）
        
        比较维度：
        - 车身类型
        - 引擎类型（排量、配置、进气方式）
        - 底盘类型
        
        Returns:
            复杂度差异 0-1（0=完全相同，1=完全不同）
        """
        diff_score = 0.0
        total_weight = 0.0
        
        # 车身类型差异（权重30%）
        if previous_design.body_style != new_design.body_style:
            diff_score += 0.3
        total_weight += 0.3
        
        # 引擎差异（权重50%）
        engine_diff = 0.0
        
        # 引擎ID不同
        if previous_design.engine_id != new_design.engine_id:
            engine_diff += 0.3
        
        # 这里可以进一步比较引擎属性，但需要查询Engine表
        # 简化：如果引擎ID不同，认为有差异
        if engine_diff > 0:
            diff_score += engine_diff * 0.5
        
        total_weight += 0.5
        
        # 底盘差异（权重20%）
        if previous_design.chassis_id != new_design.chassis_id:
            diff_score += 0.2
        total_weight += 0.2
        
        # 归一化到0-1
        if total_weight > 0:
            normalized_diff = diff_score / total_weight
        else:
            normalized_diff = 0.0
        
        return min(1.0, normalized_diff)
    
    @staticmethod
    def check_retooling_complete(
        line: ProductionLine,
        current_turn: int
    ) -> bool:
        """
        检查重新配置是否完成
        
        Args:
            line: 生产线对象
            current_turn: 当前回合数
            
        Returns:
            是否完成重新配置
        """
        if line.status != "RETOOLING":
            return False
        
        if line.retooling_until_turn is None:
            # 没有设置完成回合，认为未完成
            return False
        
        return current_turn >= line.retooling_until_turn
    
    @staticmethod
    def start_retooling(
        db: Session,
        line: ProductionLine,
        new_design: CarTrim,
        current_turn: int
    ) -> Tuple[bool, str, dict]:
        """
        开始重新配置生产线
        
        Args:
            db: 数据库会话
            line: 生产线对象
            new_design: 新车型设计
            current_turn: 当前回合数
            
        Returns:
            (是否成功, 消息, 详情字典)
        """
        # 获取之前的设计
        previous_design = None
        if line.current_design_id:
            previous_design = db.query(CarTrim).filter(
                CarTrim.id == line.current_design_id
            ).first()
        
        # 获取工厂等级
        factory = line.factory
        factory_level = factory.level if factory else 1
        
        # 计算时间和成本
        retooling_turns = RetoolingCalculator.calculate_retooling_time(
            previous_design, new_design, factory_level
        )
        retooling_cost = RetoolingCalculator.calculate_retooling_cost(
            previous_design, new_design, factory_level
        )
        
        # 更新生产线状态
        line.status = "RETOOLING"
        line.retooling_until_turn = current_turn + retooling_turns
        line.retooling_start_turn = current_turn
        line.retooling_cost = retooling_cost
        
        # 保存之前的设计ID（用于后续分析）
        if previous_design:
            line.previous_design_id = previous_design.id
        
        # 注意：current_design_id 在retooling完成后再更新
        # 这里先不更新，等retooling完成后再设置
        
        db.commit()
        
        logger.info(
            f"Production line {line.id} started retooling to {new_design.name}: "
            f"{retooling_turns} turns, {retooling_cost:.2f}M cost"
        )
        
        return True, "开始重新配置", {
            "retooling_turns": retooling_turns,
            "retooling_cost": retooling_cost,
            "completion_turn": line.retooling_until_turn
        }


__all__ = ["RetoolingCalculator"]

