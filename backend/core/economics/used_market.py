"""
二手车市场逻辑模块
处理二手车生成、交易、折旧
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, List, Optional
import logging

from backend.models.history import UsedCarInventory
from backend.models.region import Region
from backend.models.engineering import CarTrim

logger = logging.getLogger(__name__)


class UsedCarMarket:
    """
    二手车市场管理器
    
    核心流程：
    1. 新车销售后进入"待二手"队列
    2. 每月部分新车进入二手市场（decay_rate）
    3. 二手车在市场上随时间折旧
    4. 二手车与新车通过Logit模型竞争
    """
    
    def __init__(self, db: Session):
        """
        初始化二手车市场
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def add_newly_sold_cars_to_pool(
        self,
        game_id: int,
        region_id: int,
        car_trim_id: int,
        quantity: int,
        original_price: float,
        decay_rate: float = 0.02
    ) -> Dict[str, Any]:
        """
        新车销售后，部分进入二手车池
        
        Args:
            game_id: 游戏ID
            region_id: 地区ID
            car_trim_id: 车型ID
            quantity: 新售出数量
            original_price: 原价
            decay_rate: 进入二手市场比率（默认2%/月）
        
        Returns:
            操作结果
        """
        try:
            # 计算进入二手市场的数量
            entering_used_market = int(quantity * decay_rate)
            
            if entering_used_market <= 0:
                return {
                    "success": True,
                    "message": "数量太小，未进入二手市场"
                }
            
            # 查找或创建年龄=0的二手车记录
            used_car = self.db.query(UsedCarInventory).filter(
                and_(
                    UsedCarInventory.game_id == game_id,
                    UsedCarInventory.region_id == region_id,
                    UsedCarInventory.car_trim_id == car_trim_id,
                    UsedCarInventory.age_years == 0
                )
            ).first()
            
            if used_car:
                # 更新现有记录
                used_car.quantity += entering_used_market
            else:
                # 创建新记录
                # 第一年折旧：20-25%
                depreciation_year_1 = 0.22
                base_price = original_price * (1 - depreciation_year_1)
                
                used_car = UsedCarInventory(
                    game_id=game_id,
                    region_id=region_id,
                    car_trim_id=car_trim_id,
                    age_years=0,
                    condition_score=95.0,  # 几乎新车
                    quantity=entering_used_market,
                    base_price=base_price,
                    avg_asking_price=base_price,
                    depreciation_rate=0.15  # 后续年度15%
                )
                
                self.db.add(used_car)
            
            self.db.commit()
            
            logger.info(
                f"新增二手车: 地区={region_id}, 车型={car_trim_id}, "
                f"数量={entering_used_market}"
            )
            
            return {
                "success": True,
                "quantity_added": entering_used_market,
                "base_price": used_car.base_price
            }
            
        except Exception as e:
            logger.error(f"添加二手车失败: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def age_used_car_inventory(
        self,
        game_id: int,
        max_age_years: int = 15
    ) -> Dict[str, Any]:
        """
        老化二手车库存
        
        每个月执行一次：
        1. 应用月度折旧
        2. 降低车况评分
        3. 移除过老车辆
        
        Args:
            game_id: 游戏ID
            max_age_years: 最大保留车龄
        
        Returns:
            操作结果
        """
        try:
            results = {
                "aged_records": 0,
                "removed_records": 0,
                "total_depreciation": 0.0
            }
            
            # 获取所有二手车记录
            used_cars = self.db.query(UsedCarInventory).filter(
                UsedCarInventory.game_id == game_id
            ).all()
            
            for used_car in used_cars:
                # 应用月度折旧
                old_price = used_car.base_price
                used_car.apply_monthly_depreciation()
                new_price = used_car.base_price
                
                depreciation_amount = old_price - new_price
                results["total_depreciation"] += depreciation_amount * used_car.quantity
                
                # 检查是否超龄
                if used_car.age_years >= max_age_years:
                    self.db.delete(used_car)
                    results["removed_records"] += 1
                else:
                    results["aged_records"] += 1
            
            self.db.commit()
            
            logger.info(
                f"二手车老化完成: 老化={results['aged_records']}条, "
                f"移除={results['removed_records']}条, "
                f"总折旧={results['total_depreciation']:,.0f}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"二手车老化失败: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def transfer_used_cars(
        self,
        game_id: int,
        source_region_id: int,
        dest_region_id: int,
        car_trim_id: int,
        quantity: int,
        transport_cost_per_unit: float = 500.0
    ) -> Dict[str, Any]:
        """
        转移二手车（地区间交易）
        
        **约束：** 只有当源地区allow_used_export=True 且 目标地区allow_used_import=True 时才允许
        
        Args:
            game_id: 游戏ID
            source_region_id: 源地区
            dest_region_id: 目标地区
            car_trim_id: 车型ID
            quantity: 转移数量
            transport_cost_per_unit: 单位运输成本
        
        Returns:
            操作结果
        """
        try:
            # 检查地区政策
            source_region = self.db.query(Region).filter(Region.id == source_region_id).first()
            dest_region = self.db.query(Region).filter(Region.id == dest_region_id).first()
            
            if not source_region or not dest_region:
                return {"success": False, "error": "地区不存在"}
            
            # 政策检查
            if not getattr(source_region, 'allow_used_export', True):
                return {
                    "success": False,
                    "error": f"{source_region.name} 禁止二手车出口"
                }
            
            if not getattr(dest_region, 'allow_used_import', True):
                return {
                    "success": False,
                    "error": f"{dest_region.name} 禁止二手车进口"
                }
            
            # 查找源库存（取最老的车）
            source_inventory = self.db.query(UsedCarInventory).filter(
                and_(
                    UsedCarInventory.game_id == game_id,
                    UsedCarInventory.region_id == source_region_id,
                    UsedCarInventory.car_trim_id == car_trim_id,
                    UsedCarInventory.quantity >= quantity
                )
            ).order_by(UsedCarInventory.age_years.desc()).first()
            
            if not source_inventory:
                return {
                    "success": False,
                    "error": "源库存不足"
                }
            
            # 扣减源库存
            source_inventory.quantity -= quantity
            
            # 增加目标库存（或创建）
            dest_inventory = self.db.query(UsedCarInventory).filter(
                and_(
                    UsedCarInventory.game_id == game_id,
                    UsedCarInventory.region_id == dest_region_id,
                    UsedCarInventory.car_trim_id == car_trim_id,
                    UsedCarInventory.age_years == source_inventory.age_years
                )
            ).first()
            
            if dest_inventory:
                dest_inventory.quantity += quantity
            else:
                # 创建新记录
                # 加上运输成本
                adjusted_price = source_inventory.base_price + transport_cost_per_unit
                
                dest_inventory = UsedCarInventory(
                    game_id=game_id,
                    region_id=dest_region_id,
                    car_trim_id=car_trim_id,
                    age_years=source_inventory.age_years,
                    condition_score=source_inventory.condition_score * 0.95,  # 运输损耗
                    quantity=quantity,
                    base_price=adjusted_price,
                    avg_asking_price=adjusted_price,
                    depreciation_rate=source_inventory.depreciation_rate
                )
                
                self.db.add(dest_inventory)
            
            # 清理空记录
            if source_inventory.quantity == 0:
                self.db.delete(source_inventory)
            
            self.db.commit()
            
            total_transport_cost = transport_cost_per_unit * quantity
            
            logger.info(
                f"二手车转移成功: {source_region.name} -> {dest_region.name}, "
                f"数量={quantity}, 运费={total_transport_cost:,.0f}"
            )
            
            return {
                "success": True,
                "quantity_transferred": quantity,
                "transport_cost_total": total_transport_cost,
                "source_region": source_region.name,
                "dest_region": dest_region.name
            }
            
        except Exception as e:
            logger.error(f"二手车转移失败: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def get_used_car_listings(
        self,
        game_id: int,
        region_id: Optional[int] = None,
        car_trim_id: Optional[int] = None,
        max_age_years: Optional[int] = None,
        min_condition: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        获取二手车列表（带筛选）
        
        Args:
            game_id: 游戏ID
            region_id: 地区筛选（可选）
            car_trim_id: 车型筛选（可选）
            max_age_years: 最大车龄筛选（可选）
            min_condition: 最低车况筛选（可选）
        
        Returns:
            二手车列表
        """
        try:
            query = self.db.query(UsedCarInventory).filter(
                UsedCarInventory.game_id == game_id
            )
            
            if region_id is not None:
                query = query.filter(UsedCarInventory.region_id == region_id)
            
            if car_trim_id is not None:
                query = query.filter(UsedCarInventory.car_trim_id == car_trim_id)
            
            if max_age_years is not None:
                query = query.filter(UsedCarInventory.age_years <= max_age_years)
            
            if min_condition is not None:
                query = query.filter(UsedCarInventory.condition_score >= min_condition)
            
            # 按价格排序
            query = query.order_by(UsedCarInventory.avg_asking_price.asc())
            
            used_cars = query.all()
            
            results = []
            for used_car in used_cars:
                results.append({
                    "id": used_car.id,
                    "region_id": used_car.region_id,
                    "car_trim_id": used_car.car_trim_id,
                    "age_years": used_car.age_years,
                    "condition_score": used_car.condition_score,
                    "quantity": used_car.quantity,
                    "base_price": used_car.base_price,
                    "avg_asking_price": used_car.avg_asking_price,
                    "utility_penalty": used_car.calculate_utility_penalty()
                })
            
            return results
            
        except Exception as e:
            logger.error(f"获取二手车列表失败: {e}")
            return []
    
    def simulate_used_car_sales(
        self,
        game_id: int,
        region_id: int,
        demand: int,
        price_sensitivity: float = 0.8
    ) -> Dict[str, Any]:
        """
        模拟二手车销售
        
        这是一个简化版本，真正的销售竞争在market_simulation.py中
        通过Logit模型与新车竞争
        
        Args:
            game_id: 游戏ID
            region_id: 地区ID
            demand: 潜在需求
            price_sensitivity: 价格敏感度
        
        Returns:
            销售结果
        """
        try:
            used_cars = self.db.query(UsedCarInventory).filter(
                and_(
                    UsedCarInventory.game_id == game_id,
                    UsedCarInventory.region_id == region_id,
                    UsedCarInventory.quantity > 0
                )
            ).order_by(
                # 优先卖车况好、价格低的
                UsedCarInventory.condition_score.desc(),
                UsedCarInventory.avg_asking_price.asc()
            ).all()
            
            total_sold = 0
            total_revenue = 0.0
            sales_by_trim = {}
            
            for used_car in used_cars:
                if total_sold >= demand:
                    break
                
                # 简单需求分配（后续会被Logit模型替代）
                max_sellable = min(used_car.quantity, demand - total_sold)
                
                # 价格吸引力（越便宜越容易卖）
                avg_market_price = 25000  # TODO: 从市场获取
                price_factor = min(1.0, avg_market_price / max(used_car.avg_asking_price, 1.0))
                
                # 车况影响
                condition_factor = used_car.condition_score / 100.0
                
                # 综合吸引力
                attractiveness = price_factor * condition_factor
                
                # 实际销量
                actual_sold = int(max_sellable * attractiveness * price_sensitivity)
                actual_sold = max(0, min(actual_sold, used_car.quantity))
                
                if actual_sold > 0:
                    # 扣减库存
                    used_car.quantity -= actual_sold
                    
                    # 记录销售
                    revenue = actual_sold * used_car.avg_asking_price
                    total_sold += actual_sold
                    total_revenue += revenue
                    
                    trim_id = used_car.car_trim_id
                    if trim_id not in sales_by_trim:
                        sales_by_trim[trim_id] = {"quantity": 0, "revenue": 0.0}
                    
                    sales_by_trim[trim_id]["quantity"] += actual_sold
                    sales_by_trim[trim_id]["revenue"] += revenue
            
            self.db.commit()
            
            return {
                "success": True,
                "total_sold": total_sold,
                "total_revenue": total_revenue,
                "sales_by_trim": sales_by_trim,
                "satisfaction_rate": total_sold / demand if demand > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"二手车销售模拟失败: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}


# 导出
__all__ = ["UsedCarMarket"]


