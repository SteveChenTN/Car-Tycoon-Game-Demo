"""
测试车手反馈生成器 - 基于公式生成主观反馈
Test Driver Feedback Generator - Formula-based subjective feedback

核心哲学：
- 基于底盘参数计算各项评分
- 根据评分组合生成自然语言反馈
- 模拟真实测试车手的主观感受
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def calculate_rigidity_score(
    torsional_rigidity_target: int = 50,
    rigidity_rating: float = 50.0
) -> float:
    """
    计算刚性评分 (0.0-1.0)
    
    Args:
        torsional_rigidity_target: 扭转刚性目标 (1-100)
        rigidity_rating: 基础刚性评分 (0-100)
        
    Returns:
        刚性评分 (0.0-1.0)
    """
    # 综合扭转刚性和基础刚性
    target_normalized = (torsional_rigidity_target - 1) / 99.0
    rating_normalized = rigidity_rating / 100.0
    
    # 加权平均
    score = (target_normalized * 0.6 + rating_normalized * 0.4)
    return max(0.0, min(1.0, score))


def calculate_nvh_score(
    nvh_insulation_mass: float = 0.0,
    material: str = "STEEL"
) -> float:
    """
    计算NVH/舒适性评分 (0.0-1.0)
    
    Args:
        nvh_insulation_mass: NVH隔音质量 (kg)
        material: 材料类型
        
    Returns:
        NVH评分 (0.0-1.0)
    """
    # 隔音质量影响（每kg约+0.02分，上限50kg）
    insulation_score = min(nvh_insulation_mass / 50.0, 1.0) * 0.6
    
    # 材料影响（铝和碳纤维通常NVH更好）
    material_score = {
        "STEEL": 0.3,
        "ALUMINUM": 0.5,
        "CARBON": 0.4,
    }.get(material, 0.3)
    
    total_score = insulation_score + material_score
    return max(0.0, min(1.0, total_score))


def calculate_safety_score(
    crash_test_rating: float = 50.0,
    crumple_zone_length: float = 0.0,
    fuel_tank_location: str = "REAR_AXLE_BEHIND"
) -> float:
    """
    计算安全评分 (0.0-1.0)
    
    Args:
        crash_test_rating: 碰撞测试评分 (0-100)
        crumple_zone_length: 溃缩区长度 (m)
        fuel_tank_location: 油箱位置
        
    Returns:
        安全评分 (0.0-1.0)
    """
    # 基础碰撞测试评分
    crash_score = crash_test_rating / 100.0 * 0.5
    
    # 溃缩区影响（每米约+0.1分，上限1.0m）
    crumple_score = min(crumple_zone_length / 1.0, 1.0) * 0.3
    
    # 油箱位置影响
    tank_location_score = {
        "REAR_AXLE_BEHIND": 0.1,  # 传统位置，碰撞风险
        "UNDER_SEAT": 0.15,       # 稍好
        "MID_CENTRAL": 0.2,       # 最安全
    }.get(fuel_tank_location, 0.1)
    
    total_score = crash_score + crumple_score + tank_location_score
    return max(0.0, min(1.0, total_score))


def calculate_manufacturing_ease_score(
    manufacturing_complexity_score: float = 0.5,
    parts_bin_sharing_ratio: float = 0.5
) -> float:
    """
    计算制造便利性评分 (0.0-1.0)
    
    注意：这是"制造便利性"，所以复杂度越高，评分越低
    
    Args:
        manufacturing_complexity_score: 制造复杂度 (0.0-1.0)
        parts_bin_sharing_ratio: 零件库共享比例 (0.0-1.0)
        
    Returns:
        制造便利性评分 (0.0-1.0)，越高越容易制造
    """
    # 复杂度越低，便利性越高
    complexity_ease = 1.0 - manufacturing_complexity_score
    
    # 零件库共享越高，便利性越高（使用标准件）
    parts_ease = parts_bin_sharing_ratio
    
    # 加权平均
    total_score = complexity_ease * 0.6 + parts_ease * 0.4
    return max(0.0, min(1.0, total_score))


def calculate_character_score(
    parts_bin_sharing_ratio: float = 0.5,
    material: str = "STEEL"
) -> float:
    """
    计算"特色"评分 (0.0-1.0)
    
    高零件库共享 = 低特色（通用感）
    定制零件 = 高特色（独特感）
    
    Args:
        parts_bin_sharing_ratio: 零件库共享比例
        material: 材料类型
        
    Returns:
        特色评分 (0.0-1.0)，越高越有特色
    """
    # 零件库共享越低，特色越高
    parts_character = 1.0 - parts_bin_sharing_ratio
    
    # 材料影响（碳纤维更有特色）
    material_character = {
        "STEEL": 0.3,
        "ALUMINUM": 0.5,
        "CARBON": 0.8,
    }.get(material, 0.3)
    
    total_score = parts_character * 0.7 + material_character * 0.3
    return max(0.0, min(1.0, total_score))


def generate_test_driver_feedback(chassis_data: Dict[str, Any]) -> str:
    """
    基于底盘参数生成测试车手主观反馈
    
    Args:
        chassis_data: 底盘参数字典，包含所有相关字段
        
    Returns:
        测试车手反馈文本（中文）
    """
    # 提取参数（带默认值）
    torsional_rigidity_target = chassis_data.get("torsional_rigidity_target", 50)
    rigidity_rating = chassis_data.get("rigidity_rating", 50.0)
    nvh_insulation_mass = chassis_data.get("nvh_insulation_mass", 0.0)
    material = chassis_data.get("material", "STEEL")
    crash_test_rating = chassis_data.get("crash_test_rating", 50.0)
    crumple_zone_length = chassis_data.get("crumple_zone_length", 0.0)
    fuel_tank_location = chassis_data.get("fuel_tank_location", "REAR_AXLE_BEHIND")
    manufacturing_complexity_score = chassis_data.get("manufacturing_complexity_score", 0.5)
    parts_bin_sharing_ratio = chassis_data.get("parts_bin_sharing_ratio", 0.5)
    
    # 计算各项评分
    rigidity_score = calculate_rigidity_score(torsional_rigidity_target, rigidity_rating)
    nvh_score = calculate_nvh_score(nvh_insulation_mass, material)
    safety_score = calculate_safety_score(crash_test_rating, crumple_zone_length, fuel_tank_location)
    manufacturing_ease_score = calculate_manufacturing_ease_score(manufacturing_complexity_score, parts_bin_sharing_ratio)
    character_score = calculate_character_score(parts_bin_sharing_ratio, material)
    
    # 生成反馈片段
    feedback_parts = []
    
    # 1. 刚性反馈
    if rigidity_score < 0.3:
        feedback_parts.append("底盘在弯道中明显扭曲，感觉不稳定。")
    elif rigidity_score < 0.5:
        feedback_parts.append("过弯时能感觉到一些底盘变形，但仍在可接受范围内。")
    elif rigidity_score < 0.7:
        feedback_parts.append("底盘刚性良好，过弯时感觉扎实。")
    else:
        feedback_parts.append("底盘非常坚固，在极限驾驶时依然稳定可靠。")
    
    # 2. NVH反馈
    if nvh_score < 0.3:
        feedback_parts.append("路噪和发动机噪音明显，舒适性一般。")
    elif nvh_score < 0.5:
        feedback_parts.append("噪音控制尚可，但仍有改进空间。")
    elif nvh_score < 0.7:
        feedback_parts.append("车内相对安静，隔音效果不错。")
    else:
        feedback_parts.append("车内非常安静，隔音效果出色，适合长途驾驶。")
    
    # 3. 安全反馈
    if safety_score < 0.4:
        feedback_parts.append("安全配置较为基础，建议加强。")
    elif safety_score < 0.6:
        feedback_parts.append("安全性能达到基本要求。")
    elif safety_score < 0.8:
        feedback_parts.append("安全性能良好，溃缩区设计合理。")
    else:
        feedback_parts.append("安全性能优秀，溃缩区和油箱位置设计得当。")
    
    # 4. 特色/操控反馈
    if character_score < 0.3:
        feedback_parts.append("操控感通用且松散，缺乏特色。")
    elif character_score < 0.5:
        feedback_parts.append("操控感中规中矩，没有明显亮点。")
    elif character_score < 0.7:
        feedback_parts.append("操控感有特色，反馈清晰。")
    else:
        feedback_parts.append("操控感独特且精准，驾驶乐趣很高。")
    
    # 5. 制造质量反馈（基于制造复杂度）
    if manufacturing_complexity_score > 0.8:
        feedback_parts.append("制造工艺复杂，需要仔细检查装配质量。")
    elif manufacturing_complexity_score < 0.3:
        feedback_parts.append("制造工艺简单，装配质量稳定。")
    
    # 组合反馈
    if not feedback_parts:
        return "测试车手：'整体表现中规中矩，没有明显问题。'"
    
    feedback_text = "测试车手：'" + " ".join(feedback_parts) + "'"
    return feedback_text


def generate_feedback_summary(chassis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成完整的反馈摘要（包含评分和文本）
    
    Args:
        chassis_data: 底盘参数字典
        
    Returns:
        包含各项评分和文本反馈的字典
    """
    # 提取参数
    torsional_rigidity_target = chassis_data.get("torsional_rigidity_target", 50)
    rigidity_rating = chassis_data.get("rigidity_rating", 50.0)
    nvh_insulation_mass = chassis_data.get("nvh_insulation_mass", 0.0)
    material = chassis_data.get("material", "STEEL")
    crash_test_rating = chassis_data.get("crash_test_rating", 50.0)
    crumple_zone_length = chassis_data.get("crumple_zone_length", 0.0)
    fuel_tank_location = chassis_data.get("fuel_tank_location", "REAR_AXLE_BEHIND")
    manufacturing_complexity_score = chassis_data.get("manufacturing_complexity_score", 0.5)
    parts_bin_sharing_ratio = chassis_data.get("parts_bin_sharing_ratio", 0.5)
    
    # 计算所有评分
    scores = {
        "rigidity": calculate_rigidity_score(torsional_rigidity_target, rigidity_rating),
        "nvh": calculate_nvh_score(nvh_insulation_mass, material),
        "safety": calculate_safety_score(crash_test_rating, crumple_zone_length, fuel_tank_location),
        "manufacturing_ease": calculate_manufacturing_ease_score(manufacturing_complexity_score, parts_bin_sharing_ratio),
        "character": calculate_character_score(parts_bin_sharing_ratio, material),
    }
    
    # 生成文本反馈
    feedback_text = generate_test_driver_feedback(chassis_data)
    
    return {
        "scores": scores,
        "feedback_text": feedback_text,
    }


# 导出
__all__ = [
    "calculate_rigidity_score",
    "calculate_nvh_score",
    "calculate_safety_score",
    "calculate_manufacturing_ease_score",
    "calculate_character_score",
    "generate_test_driver_feedback",
    "generate_feedback_summary",
]


