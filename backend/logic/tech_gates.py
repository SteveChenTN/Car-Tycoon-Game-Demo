"""
时间门控服务 - 基于游戏年份控制功能可见性
Tech Gating Service - Controls feature visibility based on game year

核心功能：
- 根据年份返回可见的标签页
- 字段级解锁检查
- 标签页内容过滤
"""
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


# 标签页定义
TAB_FUNDAMENTALS = "Fundamentals"
TAB_SAFETY_PACKAGING = "Safety & Packaging"
TAB_REFINEMENT_MANUFACTURING = "Refinement & Manufacturing"

# 所有标签页列表
ALL_TABS = [TAB_FUNDAMENTALS, TAB_SAFETY_PACKAGING, TAB_REFINEMENT_MANUFACTURING]

# 字段到标签页的映射
FIELD_TO_TAB_MAP = {
    # Fundamentals标签页字段
    "wheelbase_mm": TAB_FUNDAMENTALS,
    "track_front_mm": TAB_FUNDAMENTALS,
    "track_rear_mm": TAB_FUNDAMENTALS,
    "material": TAB_FUNDAMENTALS,
    "layout": TAB_FUNDAMENTALS,
    "parts_bin_sharing_ratio": TAB_FUNDAMENTALS,
    
    # Safety & Packaging标签页字段
    "crumple_zone_length": TAB_SAFETY_PACKAGING,
    "fuel_tank_location": TAB_SAFETY_PACKAGING,
    "transmission_tunnel_fitted": TAB_SAFETY_PACKAGING,
    "designed_bumper_height": TAB_SAFETY_PACKAGING,
    "overall_width_class": TAB_SAFETY_PACKAGING,
    
    # Refinement & Manufacturing标签页字段
    "torsional_rigidity_target": TAB_REFINEMENT_MANUFACTURING,
    "rust_protection_level": TAB_REFINEMENT_MANUFACTURING,
    "nvh_insulation_mass": TAB_REFINEMENT_MANUFACTURING,
    "manufacturing_complexity_score": TAB_REFINEMENT_MANUFACTURING,
}

# 字段解锁年份映射
FIELD_UNLOCK_YEAR = {
    # Fundamentals - 始终可用
    "wheelbase_mm": 1946,
    "track_front_mm": 1946,
    "track_rear_mm": 1946,
    "material": 1946,
    "layout": 1946,
    "parts_bin_sharing_ratio": 1946,
    
    # Safety & Packaging - 1960+解锁
    "crumple_zone_length": 1960,
    "fuel_tank_location": 1960,
    "transmission_tunnel_fitted": 1960,
    "designed_bumper_height": 1970,  # 美国5mph保险杠法规
    "overall_width_class": 1960,
    
    # Refinement & Manufacturing - 1975+解锁
    "torsional_rigidity_target": 1975,
    "rust_protection_level": 1960,  # 部分镀锌1960+，全浸镀锌1975+
    "nvh_insulation_mass": 1975,
    "manufacturing_complexity_score": 1975,
}

# 特殊值解锁年份（如Enum的特定值）
SPECIAL_VALUE_UNLOCK_YEAR = {
    "rust_protection_level": {
        "NONE": 1946,
        "PARTIAL_GALVANIZED": 1960,
        "FULL_DIP": 1975,
    },
    "fuel_tank_location": {
        "REAR_AXLE_BEHIND": 1946,
        "UNDER_SEAT": 1960,
        "MID_CENTRAL": 1975,
    },
}


def get_visible_chassis_tabs(year: int) -> List[str]:
    """
    根据年份返回可见的标签页列表
    
    Args:
        year: 游戏年份
        
    Returns:
        可见标签页列表
    """
    if year < 1960:
        return [TAB_FUNDAMENTALS]
    elif year < 1975:
        return [TAB_FUNDAMENTALS, TAB_SAFETY_PACKAGING]
    else:
        return [TAB_FUNDAMENTALS, TAB_SAFETY_PACKAGING, TAB_REFINEMENT_MANUFACTURING]


def is_field_unlocked(field_name: str, year: int, field_value: str = None) -> bool:
    """
    检查字段是否在指定年份解锁
    
    Args:
        field_name: 字段名称
        year: 游戏年份
        field_value: 字段值（用于检查特殊值解锁，如Enum的特定值）
        
    Returns:
        是否解锁
    """
    # 检查字段基础解锁年份
    unlock_year = FIELD_UNLOCK_YEAR.get(field_name, 1946)
    if year < unlock_year:
        return False
    
    # 检查特殊值解锁（如Enum的特定值）
    if field_value and field_name in SPECIAL_VALUE_UNLOCK_YEAR:
        value_unlock_year = SPECIAL_VALUE_UNLOCK_YEAR[field_name].get(field_value, unlock_year)
        return year >= value_unlock_year
    
    return True


def get_available_fields_for_tab(tab_name: str, year: int) -> List[str]:
    """
    获取指定标签页在指定年份可用的字段列表
    
    Args:
        tab_name: 标签页名称
        year: 游戏年份
        
    Returns:
        可用字段列表
    """
    available_fields = []
    
    for field_name, field_tab in FIELD_TO_TAB_MAP.items():
        if field_tab == tab_name and is_field_unlocked(field_name, year):
            available_fields.append(field_name)
    
    return available_fields


def get_field_gating_info(year: int) -> Dict[str, Dict[str, any]]:
    """
    获取所有字段的门控信息
    
    Args:
        year: 游戏年份
        
    Returns:
        字段门控信息字典，格式：
        {
            "field_name": {
                "unlocked": bool,
                "unlock_year": int,
                "tab": str,
                "special_values": {...}  # 如果适用
            }
        }
    """
    gating_info = {}
    
    for field_name, unlock_year in FIELD_UNLOCK_YEAR.items():
        tab = FIELD_TO_TAB_MAP.get(field_name, TAB_FUNDAMENTALS)
        unlocked = is_field_unlocked(field_name, year)
        
        info = {
            "unlocked": unlocked,
            "unlock_year": unlock_year,
            "tab": tab,
        }
        
        # 添加特殊值解锁信息（如果适用）
        if field_name in SPECIAL_VALUE_UNLOCK_YEAR:
            info["special_values"] = {}
            for value, value_unlock_year in SPECIAL_VALUE_UNLOCK_YEAR[field_name].items():
                info["special_values"][value] = {
                    "unlocked": year >= value_unlock_year,
                    "unlock_year": value_unlock_year,
                }
        
        gating_info[field_name] = info
    
    return gating_info


def get_rust_protection_options(year: int) -> List[str]:
    """
    获取指定年份可用的防锈保护选项
    
    Args:
        year: 游戏年份
        
    Returns:
        可用选项列表
    """
    options = []
    
    if year >= 1946:
        options.append("NONE")
    if year >= 1960:
        options.append("PARTIAL_GALVANIZED")
    if year >= 1975:
        options.append("FULL_DIP")
    
    return options


def get_fuel_tank_location_options(year: int) -> List[str]:
    """
    获取指定年份可用的油箱位置选项
    
    Args:
        year: 游戏年份
        
    Returns:
        可用选项列表
    """
    options = []
    
    if year >= 1946:
        options.append("REAR_AXLE_BEHIND")
    if year >= 1960:
        options.append("UNDER_SEAT")
    if year >= 1975:
        options.append("MID_CENTRAL")
    
    return options


