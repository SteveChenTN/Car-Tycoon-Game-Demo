"""
自然语言指令解析器
将玩家的自然语言输入转换为结构化的游戏指令
"""
from typing import Dict, Any, Tuple, Optional, List
import re
import logging

logger = logging.getLogger(__name__)


class DirectiveParser:
    """
    指令解析器
    
    将自然语言指令解析为结构化参数
    使用关键词匹配和模式识别（简化版NLP）
    """
    
    # 关键词字典
    KEYWORDS = {
        "design": {
            "triggers": ["开发", "设计", "造", "制造", "打造", "build", "design", "create", "develop"],
            "category": "DESIGN"
        },
        "production": {
            "triggers": ["生产", "产能", "提升产量", "增加产量", "扩大", "production", "capacity", "increase"],
            "category": "PRODUCTION"
        },
        "marketing": {
            "triggers": ["营销", "推广", "宣传", "市场", "marketing", "promote", "advertise"],
            "category": "MARKETING"
        },
        "rd": {
            "triggers": ["研发", "研究", "技术", "科研", "R&D", "research", "technology"],
            "category": "RD"
        },
        "hr": {
            "triggers": ["招聘", "雇佣", "解雇", "人事", "hire", "fire", "recruit"],
            "category": "HR"
        },
        "finance": {
            "triggers": ["融资", "贷款", "成本", "预算", "finance", "loan", "cost", "budget"],
            "category": "FINANCE"
        }
    }
    
    BODY_STYLES = {
        "轿车": "SEDAN", "sedan": "SEDAN",
        "跑车": "COUPE", "coupe": "COUPE", "sports car": "COUPE",
        "SUV": "SUV", "越野": "SUV",
        "旅行车": "WAGON", "wagon": "WAGON",
        "掀背": "HATCHBACK", "hatchback": "HATCHBACK",
        "敞篷": "CONVERTIBLE", "convertible": "CONVERTIBLE",
        "卡车": "TRUCK", "truck": "TRUCK", "皮卡": "TRUCK"
    }
    
    SEGMENTS = {
        "微型": "SUBCOMPACT", "subcompact": "SUBCOMPACT", "小型": "SUBCOMPACT",
        "紧凑": "COMPACT", "compact": "COMPACT", "紧凑型": "COMPACT",
        "中型": "MIDSIZE", "midsize": "MIDSIZE", "中级": "MIDSIZE",
        "大型": "FULLSIZE", "fullsize": "FULLSIZE", "全尺寸": "FULLSIZE",
        "豪华": "LUXURY", "luxury": "LUXURY",
        "运动": "SPORTS", "sports": "SPORTS", "性能": "SPORTS",
        "超跑": "SUPER", "supercar": "SUPER"
    }
    
    PRIORITIES = {
        "安全": "SAFETY", "safety": "SAFETY",
        "性能": "PERFORMANCE", "performance": "PERFORMANCE", "动力": "PERFORMANCE",
        "舒适": "COMFORT", "comfort": "COMFORT",
        "经济": "EFFICIENCY", "efficiency": "EFFICIENCY", "燃油经济": "EFFICIENCY", "省油": "EFFICIENCY",
        "可靠": "RELIABILITY", "reliability": "RELIABILITY", "质量": "RELIABILITY",
        "成本": "COST", "cost": "COST", "便宜": "COST", "低价": "COST"
    }
    
    @staticmethod
    def parse(text: str) -> Tuple[Dict[str, Any], float]:
        """
        解析自然语言指令
        
        Args:
            text: 原始文本
            
        Returns:
            (解析后的参数字典, 置信度0-1)
        """
        text_lower = text.lower()
        
        # 识别类别
        category = DirectiveParser._identify_category(text_lower)
        
        # 根据类别进行具体解析
        if category == "DESIGN":
            return DirectiveParser._parse_design_directive(text, text_lower)
        elif category == "PRODUCTION":
            return DirectiveParser._parse_production_directive(text, text_lower)
        elif category == "MARKETING":
            return DirectiveParser._parse_marketing_directive(text, text_lower)
        elif category == "RD":
            return DirectiveParser._parse_rd_directive(text, text_lower)
        elif category == "HR":
            return DirectiveParser._parse_hr_directive(text, text_lower)
        elif category == "FINANCE":
            return DirectiveParser._parse_finance_directive(text, text_lower)
        else:
            return {"category": "UNKNOWN", "original_text": text}, 0.0
    
    @staticmethod
    def _identify_category(text_lower: str) -> Optional[str]:
        """识别指令类别"""
        for category_info in DirectiveParser.KEYWORDS.values():
            for trigger in category_info["triggers"]:
                if trigger in text_lower:
                    return category_info["category"]
        return None
    
    @staticmethod
    def _parse_design_directive(text: str, text_lower: str) -> Tuple[Dict[str, Any], float]:
        """
        解析设计类指令
        
        Example: "开发一款紧凑型SUV，优先考虑安全性和燃油经济性，价格在20-30万"
        """
        params = {
            "category": "DESIGN",
            "action": "DESIGN_VEHICLE",
            "original_text": text
        }
        
        confidence = 0.6  # 基础置信度
        
        # 识别车身类型
        for keyword, body_style in DirectiveParser.BODY_STYLES.items():
            if keyword in text_lower:
                params["body_style"] = body_style
                confidence += 0.1
                break
        
        # 识别细分市场
        for keyword, segment in DirectiveParser.SEGMENTS.items():
            if keyword in text_lower:
                params["segment"] = segment
                confidence += 0.1
                break
        
        # 识别优先级
        priorities = []
        for keyword, priority in DirectiveParser.PRIORITIES.items():
            if keyword in text_lower:
                priorities.append(priority)
                confidence += 0.05
        
        if priorities:
            params["priorities"] = priorities
        
        # 识别价格范围（简单正则）
        price_pattern = r'(\d+)[-到~](\d+)[万千百]*'
        price_match = re.search(price_pattern, text)
        if price_match:
            min_price = float(price_match.group(1))
            max_price = float(price_match.group(2))
            
            # 判断单位（万/千）
            if "万" in text:
                min_price *= 10000
                max_price *= 10000
            elif "千" in text or "k" in text_lower:
                min_price *= 1000
                max_price *= 1000
            
            params["price_range"] = {
                "min": min_price,
                "max": max_price
            }
            confidence += 0.1
        
        # 识别目标市场
        regions = {
            "亚洲": "ASI", "asia": "ASI",
            "欧洲": "EUR", "europe": "EUR",
            "北美": "NAM", "north america": "NAM",
            "拉美": "LAM", "latin america": "LAM",
            "中东": "MEA", "middle east": "MEA"
        }
        
        for keyword, region_code in regions.items():
            if keyword in text_lower:
                params["target_region"] = region_code
                confidence += 0.05
                break
        
        return params, min(1.0, confidence)
    
    @staticmethod
    def _parse_production_directive(text: str, text_lower: str) -> Tuple[Dict[str, Any], float]:
        """
        解析生产类指令
        
        Example: "将Fusion的产能提升到每月10000辆"
        """
        params = {
            "category": "PRODUCTION",
            "action": "ADJUST_PRODUCTION",
            "original_text": text
        }
        
        confidence = 0.5
        
        # 识别车型名称（简化：提取大写单词或中文车型名）
        model_pattern = r'([A-Z][a-z]+|[\u4e00-\u9fa5]{2,5})'
        model_matches = re.findall(model_pattern, text)
        if model_matches:
            params["model_name"] = model_matches[0]
            confidence += 0.1
        
        # 识别产能目标
        capacity_patterns = [
            r'(\d+(?:,\d{3})*)\s*辆',
            r'(\d+(?:,\d{3})*)\s*units',
            r'产能.*?(\d+(?:,\d{3})*)'
        ]
        
        for pattern in capacity_patterns:
            match = re.search(pattern, text_lower)
            if match:
                capacity = int(match.group(1).replace(',', ''))
                params["target_capacity"] = capacity
                confidence += 0.2
                break
        
        # 识别时间范围
        if "每月" in text or "monthly" in text_lower:
            params["time_unit"] = "MONTHLY"
            confidence += 0.05
        elif "每年" in text or "yearly" in text_lower:
            params["time_unit"] = "YEARLY"
            confidence += 0.05
        
        # 识别动作（提升/降低）
        if any(word in text_lower for word in ["提升", "增加", "扩大", "increase", "expand"]):
            params["direction"] = "INCREASE"
            confidence += 0.05
        elif any(word in text_lower for word in ["降低", "减少", "缩小", "decrease", "reduce"]):
            params["direction"] = "DECREASE"
            confidence += 0.05
        
        return params, min(1.0, confidence)
    
    @staticmethod
    def _parse_marketing_directive(text: str, text_lower: str) -> Tuple[Dict[str, Any], float]:
        """解析营销类指令"""
        params = {
            "category": "MARKETING",
            "action": "MARKETING_CAMPAIGN",
            "original_text": text
        }
        
        confidence = 0.5
        
        # 识别营销重点
        focus_map = {
            "品牌": "BRAND", "brand": "BRAND",
            "销量": "SALES", "sales": "SALES",
            "新品": "LAUNCH", "launch": "LAUNCH",
            "形象": "IMAGE", "image": "IMAGE"
        }
        
        for keyword, focus in focus_map.items():
            if keyword in text_lower:
                params["focus"] = focus
                confidence += 0.15
                break
        
        # 识别预算
        budget_pattern = r'(\d+(?:\.\d+)?)\s*[万千百]*'
        if "预算" in text or "budget" in text_lower:
            match = re.search(budget_pattern, text)
            if match:
                budget = float(match.group(1))
                if "万" in text:
                    budget *= 10
                params["budget"] = budget
                confidence += 0.2
        
        return params, min(1.0, confidence)
    
    @staticmethod
    def _parse_rd_directive(text: str, text_lower: str) -> Tuple[Dict[str, Any], float]:
        """解析研发类指令"""
        params = {
            "category": "RD",
            "action": "RESEARCH_TECH",
            "original_text": text
        }
        
        confidence = 0.5
        
        # 识别技术类型
        tech_keywords = {
            "涡轮": "TURBO", "turbo": "TURBO",
            "混动": "HYBRID", "hybrid": "HYBRID",
            "电动": "ELECTRIC", "electric": "ELECTRIC", "EV": "ELECTRIC",
            "自动驾驶": "AUTONOMOUS", "autonomous": "AUTONOMOUS",
            "轻量化": "LIGHTWEIGHT", "lightweight": "LIGHTWEIGHT"
        }
        
        for keyword, tech_type in tech_keywords.items():
            if keyword in text_lower:
                params["tech_type"] = tech_type
                confidence += 0.2
                break
        
        # 识别投资金额
        investment_pattern = r'投入.*?(\d+(?:\.\d+)?)\s*[万千百]*'
        match = re.search(investment_pattern, text)
        if match:
            investment = float(match.group(1))
            if "万" in text:
                investment *= 10
            params["monthly_investment"] = investment
            confidence += 0.15
        
        # 识别时间限制
        time_pattern = r'(\d+)\s*[年月]'
        match = re.search(time_pattern, text)
        if match:
            time_value = int(match.group(1))
            if "年" in text or "year" in text_lower:
                params["deadline_months"] = time_value * 12
            else:
                params["deadline_months"] = time_value
            confidence += 0.1
        
        return params, min(1.0, confidence)
    
    @staticmethod
    def _parse_hr_directive(text: str, text_lower: str) -> Tuple[Dict[str, Any], float]:
        """解析人事类指令"""
        params = {
            "category": "HR",
            "original_text": text
        }
        
        confidence = 0.5
        
        # 识别动作
        if any(word in text_lower for word in ["招聘", "雇佣", "hire", "recruit"]):
            params["action"] = "HIRE"
            confidence += 0.2
        elif any(word in text_lower for word in ["解雇", "fire"]):
            params["action"] = "FIRE"
            confidence += 0.2
        
        # 识别职位
        positions = {
            "CTO": "CTO", "技术总监": "CTO", "首席技术官": "CTO",
            "CFO": "CFO", "财务总监": "CFO", "首席财务官": "CFO",
            "CMO": "CMO", "营销总监": "CMO", "首席营销官": "CMO",
            "COO": "COO", "运营总监": "COO", "首席运营官": "COO",
            "工程师": "ENGINEER", "engineer": "ENGINEER"
        }
        
        for keyword, position in positions.items():
            if keyword in text_lower or keyword in text:
                params["position"] = position
                confidence += 0.15
                break
        
        return params, min(1.0, confidence)
    
    @staticmethod
    def _parse_finance_directive(text: str, text_lower: str) -> Tuple[Dict[str, Any], float]:
        """解析财务类指令"""
        params = {
            "category": "FINANCE",
            "original_text": text
        }
        
        confidence = 0.5
        
        # 识别动作
        if any(word in text_lower for word in ["贷款", "融资", "loan", "borrow"]):
            params["action"] = "REQUEST_LOAN"
            confidence += 0.2
            
            # 识别金额
            amount_pattern = r'(\d+(?:\.\d+)?)\s*[万千百]*'
            match = re.search(amount_pattern, text)
            if match:
                amount = float(match.group(1))
                if "万" in text:
                    amount *= 10
                elif "亿" in text:
                    amount *= 1000
                params["amount"] = amount
                confidence += 0.2
        
        elif any(word in text_lower for word in ["成本", "削减", "降低", "reduce", "cut"]):
            params["action"] = "REDUCE_COST"
            confidence += 0.2
            
            # 识别目标百分比
            percent_pattern = r'(\d+(?:\.\d+)?)\s*%'
            match = re.search(percent_pattern, text)
            if match:
                params["target_reduction"] = float(match.group(1)) / 100
                confidence += 0.15
        
        return params, min(1.0, confidence)
    
    @staticmethod
    def validate_parsed_directive(params: Dict[str, Any]) -> List[str]:
        """
        验证解析后的指令是否有足够信息执行
        
        Returns:
            缺失信息列表（空列表表示可以执行）
        """
        missing = []
        
        category = params.get("category")
        
        if category == "DESIGN":
            if "body_style" not in params:
                missing.append("车身类型")
            if "segment" not in params:
                missing.append("细分市场")
        
        elif category == "PRODUCTION":
            if "model_name" not in params:
                missing.append("车型名称")
            if "target_capacity" not in params:
                missing.append("目标产能")
        
        elif category == "RD":
            if "tech_type" not in params:
                missing.append("技术类型")
        
        elif category == "HR":
            if "action" not in params:
                missing.append("操作类型（招聘/解雇）")
            if "position" not in params:
                missing.append("职位")
        
        return missing


__all__ = ["DirectiveParser"]


