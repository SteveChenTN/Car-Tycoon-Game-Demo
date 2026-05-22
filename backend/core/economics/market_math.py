"""
高级市场数学模块 - Multinomial Logit 选择模型
基于效用的概率购买决策模型
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import math
import logging

logger = logging.getLogger(__name__)


class MultinomialLogitModel:
    """
    Multinomial Logit 离散选择模型
    
    用于模拟消费者在多个车辆选项中的购买决策
    
    核心公式:
        P_i = exp(V_i) / Σ_j exp(V_j)
    
    其中效用函数:
        V_i = β_price × ln(Price_i) + β_perf × Performance_i + 
              β_brand × BrandScore_i + ... + ε
    
    参数:
        - β 系数由消费者细分决定（价格敏感度、性能偏好等）
        - ε 是随机误差项（Type I Extreme Value分布）
    """
    
    def __init__(
        self,
        price_sensitivity: float = -1.0,
        use_numpy: bool = True
    ):
        """
        初始化Logit模型
        
        Args:
            price_sensitivity: 价格敏感度系数（通常为负）
            use_numpy: 是否使用NumPy加速（大规模计算时推荐）
        """
        self.price_sensitivity = price_sensitivity
        self.use_numpy = use_numpy
    
    def calculate_utility(
        self,
        price: float,
        attributes: Dict[str, float],
        weights: Dict[str, float],
        brand_modifier: float = 1.0,
        constant: float = 0.0
    ) -> float:
        """
        计算单个选项的效用值
        
        Args:
            price: 价格
            attributes: 属性字典 {"performance": 80, "comfort": 70, ...}
            weights: 权重字典（β系数）{"performance": 0.15, "comfort": 0.2, ...}
            brand_modifier: 品牌加成系数 0.5-1.5
            constant: 常数项（alternative-specific constant）
        
        Returns:
            效用值 V
        """
        utility = constant
        
        # 价格项（对数形式，负系数）
        if price > 0:
            utility += self.price_sensitivity * math.log(price)
        
        # 属性项（线性）
        for attr_name, attr_value in attributes.items():
            weight = weights.get(attr_name, 0.0)
            # 属性值归一化到0-1
            normalized_value = attr_value / 100.0 if attr_value > 1.0 else attr_value
            utility += weight * normalized_value
        
        # 品牌加成（乘性）
        utility *= brand_modifier
        
        return utility
    
    def calculate_choice_probabilities(
        self,
        utilities: List[float],
        temperature: float = 1.0
    ) -> List[float]:
        """
        根据效用值计算选择概率
        
        Args:
            utilities: 效用值列表
            temperature: 温度参数（控制随机性）
                - 1.0 = 标准Logit
                - >1.0 = 更随机（更平均分布）
                - <1.0 = 更确定性（更偏向高效用选项）
        
        Returns:
            概率列表（和为1.0）
        """
        if not utilities:
            return []
        
        if self.use_numpy:
            return self._calculate_probs_numpy(utilities, temperature)
        else:
            return self._calculate_probs_python(utilities, temperature)
    
    def _calculate_probs_numpy(
        self,
        utilities: List[float],
        temperature: float
    ) -> List[float]:
        """
        NumPy加速版本
        """
        utilities_array = np.array(utilities) / temperature
        
        # 数值稳定性：减去最大值
        max_utility = np.max(utilities_array)
        exp_utilities = np.exp(utilities_array - max_utility)
        
        # 计算概率
        sum_exp = np.sum(exp_utilities)
        if sum_exp == 0:
            # 退化情况：均匀分布
            return [1.0 / len(utilities)] * len(utilities)
        
        probabilities = exp_utilities / sum_exp
        
        return probabilities.tolist()
    
    def _calculate_probs_python(
        self,
        utilities: List[float],
        temperature: float
    ) -> List[float]:
        """
        纯Python版本（无NumPy依赖）
        """
        scaled_utilities = [u / temperature for u in utilities]
        
        # 数值稳定性
        max_utility = max(scaled_utilities)
        exp_utilities = [math.exp(u - max_utility) for u in scaled_utilities]
        
        sum_exp = sum(exp_utilities)
        if sum_exp == 0:
            return [1.0 / len(utilities)] * len(utilities)
        
        probabilities = [exp_u / sum_exp for exp_u in exp_utilities]
        
        return probabilities
    
    def simulate_choices(
        self,
        utilities: List[float],
        n_consumers: int,
        temperature: float = 1.0,
        random_seed: Optional[int] = None
    ) -> List[int]:
        """
        模拟N个消费者的选择
        
        Args:
            utilities: 效用值列表
            n_consumers: 消费者数量
            temperature: 温度参数
            random_seed: 随机种子（可复现）
        
        Returns:
            选择结果列表（索引）
        """
        if random_seed is not None:
            if self.use_numpy:
                np.random.seed(random_seed)
            else:
                import random
                random.seed(random_seed)
        
        probabilities = self.calculate_choice_probabilities(utilities, temperature)
        
        if self.use_numpy:
            choices = np.random.choice(
                len(utilities),
                size=n_consumers,
                p=probabilities
            )
            return choices.tolist()
        else:
            import random
            choices = random.choices(
                range(len(utilities)),
                weights=probabilities,
                k=n_consumers
            )
            return choices
    
    def batch_calculate_market_shares(
        self,
        options: List[Dict[str, Any]],
        consumer_segments: List[Dict[str, Any]],
        temperature: float = 1.0
    ) -> Dict[int, Dict[str, float]]:
        """
        批量计算多个消费者细分的市场份额
        
        Args:
            options: 车辆选项列表
                [{
                    "id": 1,
                    "price": 25000,
                    "attributes": {"performance": 75, "comfort": 80, ...},
                    "brand_modifier": 1.1
                }, ...]
            
            consumer_segments: 消费者细分列表
                [{
                    "id": 1,
                    "name": "Young Professionals",
                    "population": 50000,
                    "weights": {"performance": 0.2, "comfort": 0.15, ...}
                }, ...]
            
            temperature: 温度参数
        
        Returns:
            {
                segment_id: {
                    option_id: probability
                }
            }
        """
        results = {}
        
        for segment in consumer_segments:
            segment_id = segment["id"]
            weights = segment["weights"]
            
            # 计算该细分对所有选项的效用
            utilities = []
            option_ids = []
            
            for option in options:
                utility = self.calculate_utility(
                    price=option["price"],
                    attributes=option["attributes"],
                    weights=weights,
                    brand_modifier=option.get("brand_modifier", 1.0),
                    constant=option.get("constant", 0.0)
                )
                utilities.append(utility)
                option_ids.append(option["id"])
            
            # 计算概率
            probabilities = self.calculate_choice_probabilities(utilities, temperature)
            
            # 构建结果字典
            segment_shares = {}
            for opt_id, prob in zip(option_ids, probabilities):
                segment_shares[opt_id] = prob
            
            results[segment_id] = segment_shares
        
        return results
    
    def calculate_elasticity(
        self,
        utilities: List[float],
        option_index: int,
        attribute_name: str,
        attribute_value: float,
        weight: float,
        delta: float = 0.01
    ) -> float:
        """
        计算价格/属性弹性
        
        Args:
            utilities: 当前效用值列表
            option_index: 目标选项索引
            attribute_name: 属性名称（用于日志）
            attribute_value: 当前属性值
            weight: 该属性的权重系数
            delta: 变化量（百分比）
        
        Returns:
            弹性系数（无量纲）
        """
        # 基准概率
        base_probs = self.calculate_choice_probabilities(utilities)
        base_prob = base_probs[option_index]
        
        # 改变属性后的效用
        new_utilities = utilities.copy()
        delta_utility = weight * (attribute_value * delta / 100.0)
        new_utilities[option_index] += delta_utility
        
        # 新概率
        new_probs = self.calculate_choice_probabilities(new_utilities)
        new_prob = new_probs[option_index]
        
        # 弹性 = (ΔP/P) / (ΔX/X)
        if base_prob == 0 or attribute_value == 0:
            return 0.0
        
        elasticity = ((new_prob - base_prob) / base_prob) / delta
        
        return elasticity


class UsedCarUtilityCalculator:
    """
    二手车效用计算器
    
    为二手车应用折旧惩罚，使其与新车竞争
    """
    
    @staticmethod
    def calculate_age_penalty(age_years: int) -> float:
        """
        计算车龄惩罚系数
        
        Args:
            age_years: 车龄（年）
        
        Returns:
            惩罚系数（0-1）
        """
        # 对数衰减模型
        # 1年：~92%
        # 3年：~80%
        # 5年：~70%
        # 10年：~50%
        base_penalty = 1.0 - (age_years * 0.08)
        return max(0.3, min(1.0, base_penalty))
    
    @staticmethod
    def calculate_condition_penalty(condition_score: float) -> float:
        """
        计算车况惩罚系数
        
        Args:
            condition_score: 车况评分（0-100）
        
        Returns:
            惩罚系数（0-1）
        """
        return condition_score / 100.0
    
    @staticmethod
    def calculate_depreciated_utility(
        base_utility: float,
        age_years: int,
        condition_score: float,
        price_advantage: float = 0.0
    ) -> float:
        """
        计算二手车折旧后效用
        
        Args:
            base_utility: 新车基准效用
            age_years: 车龄
            condition_score: 车况评分
            price_advantage: 价格优势（新车价格 - 二手价格）/ 新车价格
        
        Returns:
            折旧后效用
        """
        age_penalty = UsedCarUtilityCalculator.calculate_age_penalty(age_years)
        condition_penalty = UsedCarUtilityCalculator.calculate_condition_penalty(condition_score)
        
        # 综合惩罚
        total_penalty = age_penalty * condition_penalty
        
        # 折旧后效用 = 基准效用 × 惩罚 + 价格优势加成
        depreciated_utility = (base_utility * total_penalty) + (price_advantage * 0.5)
        
        return depreciated_utility


# 导出
__all__ = [
    "MultinomialLogit",
    "MultinomialLogitModel",
    "UsedCarUtilityCalculator"
]

