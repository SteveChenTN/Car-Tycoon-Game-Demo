"""
市场模拟核心算法
实现月度销售计算、需求匹配和市场解析
"""
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
from collections import defaultdict
import math
import random
import time

from backend.models.market import (
    ConsumerBucket, DistributionNetwork, BrandPerception,
    MarketingCampaign, DistributionType, MarketingFocus
)
from backend.models.engineering import CarTrim
from backend.models.company import Company
from backend.models.region import Region
from backend.models.game_state import GameState
from backend.models.history import SalesHistory, MarketDemandHistory, UsedCarInventory
from backend.models.inventory import DealershipInventory
from backend.config import MarketConstants, EconomicConstants
from backend.utils.logger import get_logger
from backend.core.economics.market_math import MultinomialLogitModel as MultinomialLogit

logger = get_logger(__name__)


# ========== 数据结构 ==========

@dataclass
class VehicleOption:
    """可选车辆（新车或二手车）"""
    car_trim_id: Optional[int]  # None表示二手车聚合
    company_id: int
    segment: str
    price: float
    
    # 性能属性（归一化到0-1）
    performance_score: float
    comfort_score: float
    reliability_score: float
    safety_score: float
    efficiency_score: float
    practicality_score: float
    prestige_score: float
    
    # 可用性
    is_used: bool
    distribution_coverage: float  # 分销覆盖度
    available_units: int
    dealer_inventory_id: Optional[int] = None
    manufacturing_cost: float = 0.0
    discount_percent: float = 0.0
    revenue_retention: float = 1.0


@dataclass
class MarketResolutionResult:
    """市场解析结果"""
    region_id: int
    total_demand: int
    total_sales: int
    sales_by_company: Dict[int, int]
    sales_by_trim: Dict[int, int]
    unmet_demand: int
    used_car_sales: int
    execution_time_ms: float
    sales_details_by_trim: Dict[int, Dict[str, Any]]
    total_revenue: float
    total_manufacturing_cost: float
    total_gross_profit: float
    lost_demand_by_reason: Dict[str, int]


# ========== 核心市场模拟类 ==========

class MarketSimulator:
    """
    市场模拟器
    负责计算每个地区的月度销售
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== 主入口 ==========
    
    def calculate_monthly_sales(
        self,
        region_id: int,
        current_turn: int,
        game_id: int
    ) -> MarketResolutionResult:
        """
        计算月度销售（核心算法）
        
        Args:
            region_id: 地区ID
            current_turn: 当前回合
            game_id: 游戏ID
        
        Returns:
            市场解析结果
        """
        start_time = time.time()
        
        logger.info(f"开始计算地区 {region_id} 的月度销售（回合 {current_turn}）")
        
        # 阶段1：获取市场上下文
        game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            raise ValueError(f"游戏 {game_id} 不存在")

        period_factor = self._get_period_factor(game_state)
        region = self._get_region(region_id)
        consumer_buckets = self._get_consumer_buckets(region_id, game_id)
        self._receive_arrived_shipments(region_id, game_id, current_turn)
        available_vehicles = self._get_available_vehicles(
            region_id=region_id,
            game_id=game_id,
            period_factor=period_factor
        )
        empty_market_reason = self._determine_empty_market_reason(region_id, game_id)
        
        logger.debug(f"  消费者细分数: {len(consumer_buckets)}")
        logger.debug(f"  可选车型数: {len(available_vehicles)}")
        
        # 阶段2：计算每个细分的需求
        total_demand = self._calculate_demand(
            consumer_buckets, region, current_turn, period_factor
        )
        
        # 阶段3：运行购买模拟
        sales_result = self._simulate_purchases(
            consumer_buckets=consumer_buckets,
            vehicles=available_vehicles,
            region=region,
            game_id=game_id,
            current_turn=current_turn,
            empty_market_reason=empty_market_reason
        )
        
        # 阶段4：生成结果
        execution_time_ms = (time.time() - start_time) * 1000
        
        result = MarketResolutionResult(
            region_id=region_id,
            total_demand=total_demand,
            total_sales=sales_result["total_new_sales"],
            sales_by_company=sales_result["sales_by_company"],
            sales_by_trim=sales_result["sales_by_trim"],
            unmet_demand=max(
                0,
                total_demand - sales_result["total_new_sales"] - sales_result["used_car_sales"]
            ),
            used_car_sales=sales_result["used_car_sales"],
            execution_time_ms=execution_time_ms,
            sales_details_by_trim=sales_result["sales_details_by_trim"],
            total_revenue=sales_result["total_revenue"],
            total_manufacturing_cost=sales_result["total_manufacturing_cost"],
            total_gross_profit=sales_result["total_gross_profit"],
            lost_demand_by_reason=sales_result["lost_demand_by_reason"]
        )

        self._persist_market_outcome(
            game_id=game_id,
            game_state=game_state,
            region=region,
            result=result
        )
        
        logger.info(
            f"✓ 地区 {region_id} 市场解析完成 | "
            f"需求: {total_demand:,} | 新车销量: {result.total_sales:,} | "
            f"二手车: {result.used_car_sales:,} | 耗时: {execution_time_ms:.2f}ms"
        )
        
        return result
    
    # ========== 阶段1：获取数据 ==========

    def _get_period_factor(self, game_state: GameState) -> float:
        """将月度需求/容量缩放到当前回合粒度。"""
        if game_state.simulation_speed == "weekly":
            return 1.0 / 4.0
        return 1.0

    def _receive_arrived_shipments(
        self,
        region_id: int,
        game_id: int,
        current_turn: int
    ) -> None:
        """把已到达的经销商在途库存转为可售新车。"""
        arrivals = self.db.query(DealershipInventory).filter(
            DealershipInventory.game_id == game_id,
            DealershipInventory.region_id == region_id,
            DealershipInventory.quantity_in_transit > 0,
            DealershipInventory.expected_arrival_turn.isnot(None),
            DealershipInventory.expected_arrival_turn <= current_turn
        ).all()

        for inventory in arrivals:
            inventory.receive_shipment(inventory.quantity_in_transit, current_turn)

        if arrivals:
            self.db.flush()

    def _determine_empty_market_reason(self, region_id: int, game_id: int) -> str:
        """区分没有分销网络和有渠道但没有可售库存。"""
        has_distribution = self.db.query(DistributionNetwork).filter(
            DistributionNetwork.game_id == game_id,
            DistributionNetwork.region_id == region_id,
            DistributionNetwork.is_active == True,
            DistributionNetwork.coverage_level > 0
        ).first()
        return "NO_NEW_STOCK" if has_distribution else "NO_DISTRIBUTION"

    def _get_region(self, region_id: int) -> Region:
        """获取地区信息"""
        region = self.db.query(Region).filter(Region.id == region_id).first()
        if not region:
            raise ValueError(f"地区 {region_id} 不存在")
        return region
    
    def _get_consumer_buckets(self, region_id: int, game_id: int) -> List[ConsumerBucket]:
        """获取该地区的所有消费者细分"""
        return self.db.query(ConsumerBucket).filter(
            ConsumerBucket.region_id == region_id,
            ConsumerBucket.game_id == game_id
        ).all()
    
    def _get_available_vehicles(
        self,
        region_id: int,
        game_id: int,
        period_factor: float
    ) -> List[VehicleOption]:
        """
        获取该地区可购买的所有车辆
        包含分销覆盖度、经销商库存和周期容量过滤
        """
        vehicles = []
        
        # 查询所有在售的车型配置
        trims = self.db.query(CarTrim).filter(
            CarTrim.game_id == game_id,
            CarTrim.is_in_production == True
        ).all()
        
        for trim in trims:
            # 检查分销网络
            distribution = self.db.query(DistributionNetwork).filter(
                DistributionNetwork.game_id == game_id,
                DistributionNetwork.company_id == trim.company_id,
                DistributionNetwork.region_id == region_id,
                DistributionNetwork.is_active == True
            ).first()
            
            if not distribution or distribution.coverage_level == 0.0:
                # 该公司在此地区无分销，车辆不可见
                continue

            dealer_inventory = self.db.query(DealershipInventory).filter(
                DealershipInventory.game_id == game_id,
                DealershipInventory.region_id == region_id,
                DealershipInventory.car_trim_id == trim.id,
                DealershipInventory.company_id == trim.company_id
            ).first()

            if not dealer_inventory or dealer_inventory.quantity_new <= 0:
                continue

            period_capacity = int(distribution.monthly_capacity * period_factor)
            if distribution.monthly_capacity > 0 and period_capacity == 0:
                period_capacity = 1

            available_units = min(dealer_inventory.quantity_new, period_capacity)
            if available_units <= 0:
                continue
            
            # 创建车辆选项
            vehicle = self._convert_trim_to_option(
                trim=trim,
                distribution=distribution,
                dealer_inventory=dealer_inventory,
                available_units=available_units
            )
            vehicles.append(vehicle)
        
        return vehicles
    
    def _convert_trim_to_option(
        self,
        trim: CarTrim,
        distribution: DistributionNetwork,
        dealer_inventory: DealershipInventory,
        available_units: int
    ) -> VehicleOption:
        """
        将CarTrim转换为VehicleOption
        归一化所有属性到0-1范围
        """
        # 性能评分（基于功率重量比）
        performance_score = min(trim.power_to_weight_ratio / 0.2, 1.0)  # 0.2 hp/kg = 1.0
        
        # 舒适性评分（基于车身类型和细分市场）
        comfort_map = {
            "LUXURY": 0.9, "FULLSIZE": 0.8, "MIDSIZE": 0.7,
            "COMPACT": 0.6, "SUBCOMPACT": 0.5, "SPORTS": 0.4, "SUPER": 0.3
        }
        comfort_score = comfort_map.get(trim.segment, 0.6)
        
        # 可靠性评分（直接使用）
        reliability_score = trim.final_reliability_score / 100.0
        
        # 安全评分（基于底盘碰撞测试）
        # 需要加载底盘数据
        safety_score = 0.7  # 默认值，后续可以从chassis.crash_test_rating获取
        
        # 效率评分（燃油经济性，越低越好）
        efficiency_score = max(0.0, 1.0 - (trim.fuel_economy_l_100km / 20.0))  # 20L/100km = 0分
        
        # 实用性评分（基于座位数和载货量）
        practicality_score = min((trim.seating_capacity * 100 + trim.cargo_volume_liters) / 1000.0, 1.0)
        
        # 声望评分（基于细分市场）
        prestige_map = {
            "SUPER": 1.0, "LUXURY": 0.9, "SPORTS": 0.8,
            "FULLSIZE": 0.6, "MIDSIZE": 0.5, "COMPACT": 0.3, "SUBCOMPACT": 0.2
        }
        prestige_score = prestige_map.get(trim.segment, 0.5)
        
        return VehicleOption(
            car_trim_id=trim.id,
            company_id=trim.company_id,
            segment=trim.segment,
            price=float(dealer_inventory.effective_price or dealer_inventory.current_msrp or trim.msrp or 0.0),
            performance_score=performance_score,
            comfort_score=comfort_score,
            reliability_score=reliability_score,
            safety_score=safety_score,
            efficiency_score=efficiency_score,
            practicality_score=practicality_score,
            prestige_score=prestige_score,
            is_used=False,
            distribution_coverage=distribution.coverage_level,
            available_units=available_units,
            dealer_inventory_id=dealer_inventory.id,
            manufacturing_cost=float(trim.manufacturing_cost or 0.0),
            discount_percent=dealer_inventory.current_discount_percent or 0.0,
            revenue_retention=distribution.get_effective_margin()
        )
    
    # ========== 阶段2：需求计算 ==========
    
    def _calculate_demand(
        self,
        buckets: List[ConsumerBucket],
        region: Region,
        current_turn: int,
        period_factor: float
    ) -> int:
        """
        计算总需求量
        基于人口、购买频率和经济修正
        """
        total_demand = 0
        
        # 经济修正系数
        economic_modifier = self._calculate_economic_modifier(region)
        
        for bucket in buckets:
            # 基础购买意向：人口 * 年度购买频率 / 12（月度）
            annual_purchases = bucket.population_count / bucket.purchase_frequency_years
            monthly_base_demand = annual_purchases / 12.0
            
            # 应用经济修正和随机波动
            demand = monthly_base_demand * period_factor * economic_modifier * random.uniform(0.9, 1.1)
            bucket.current_demand = int(demand)
            bucket.satisfied_demand = 0  # 重置
            
            total_demand += bucket.current_demand
        
        self.db.flush()
        
        return total_demand
    
    def _calculate_economic_modifier(self, region: Region) -> float:
        """
        计算经济修正系数
        基于GDP增长率、失业率等
        
        Returns:
            修正系数（0.5 - 1.5）
        """
        modifier = 1.0
        
        # GDP增长影响
        modifier += (region.gdp_growth_rate - 0.03) * 2.0
        
        # 失业率影响
        modifier += region.unemployment_rate * EconomicConstants.UNEMPLOYMENT_DEMAND_IMPACT
        
        # 限制范围
        return max(0.5, min(1.5, modifier))
    
    # ========== 阶段3：购买模拟 ==========
    
    def _simulate_purchases(
        self,
        consumer_buckets: List[ConsumerBucket],
        vehicles: List[VehicleOption],
        region: Region,
        game_id: int,
        current_turn: int,
        empty_market_reason: str
    ) -> Dict:
        """
        运行购买模拟（使用Multinomial Logit模型）
        每个消费者细分评估所有车辆并做出购买决策
        """
        sales_by_company = {}
        sales_by_trim = {}
        sales_details_by_trim: Dict[int, Dict[str, Any]] = {}
        total_new_sales = 0
        used_candidate_demand = 0
        lost_demand_by_reason = defaultdict(int)

        def route_unmet(quantity: int, reason: str) -> None:
            nonlocal used_candidate_demand
            if quantity <= 0:
                return

            used_attempts = int(quantity * 0.3)
            used_candidate_demand += used_attempts
            lost_now = quantity - used_attempts
            if lost_now > 0:
                lost_demand_by_reason[reason] += lost_now
        
        # 随机打乱顺序以避免系统性偏差
        random.shuffle(consumer_buckets)
        
        for bucket in consumer_buckets:
            if bucket.current_demand == 0:
                continue
            
            # 获取品牌认知数据
            brand_perceptions = self._get_brand_perceptions(region.id, game_id)
            
            # 获取营销活动数据
            active_campaigns = self._get_active_campaigns(
                region.id, game_id, bucket.segment, current_turn
            )
            
            # 使用Multinomial Logit模型批量处理需求
            # 为了性能，按批次处理（每批100个买家）
            batch_size = 100
            remaining_demand = bucket.current_demand
            
            while remaining_demand > 0:
                current_batch = min(batch_size, remaining_demand)
                
                # 准备Logit模型的选项
                options = []
                for vehicle in vehicles:
                    if vehicle.available_units <= 0:
                        continue  # 库存耗尽
                    
                    # 计算效用分数
                    utility = self._calculate_utility(
                        vehicle=vehicle,
                        bucket=bucket,
                        brand_perception=brand_perceptions.get(vehicle.company_id),
                        marketing_campaigns=active_campaigns.get(vehicle.company_id, []),
                        region=region
                    )
                    
                    # 应用分销覆盖度
                    utility *= vehicle.distribution_coverage
                    
                    # 创建Logit选项
                    options.append({
                        'id': vehicle.car_trim_id or -1,
                        'vehicle': vehicle,
                        'attributes': {
                            'price': vehicle.price,
                            'performance': vehicle.performance_score * 100,
                            'brand': brand_perceptions.get(vehicle.company_id).overall_awareness * 100 if brand_perceptions.get(vehicle.company_id) else 50,
                            'utility': utility
                        }
                    })
                
                # 添加"不购买"选项
                options.append({
                    'id': 0,
                    'vehicle': None,
                    'attributes': {
                        'price': 0,
                        'performance': 0,
                        'brand': 0,
                        'utility': bucket.min_acceptable_utility * 0.5  # 不购买的效用
                    }
                })
                
                if len(options) <= 1:
                    # 没有可选车辆，所有人都不购买
                    route_unmet(current_batch, empty_market_reason)
                    remaining_demand -= current_batch
                    continue
                
                # 计算选择概率
                utility_scores = []
                for option in options:
                    attributes = option["attributes"]
                    utility_scores.append(
                        -0.00002 * attributes["price"]
                        + 0.01 * attributes["performance"]
                        + 0.02 * attributes["brand"]
                        + 3.0 * attributes["utility"]
                    )
                logit_model = MultinomialLogit(use_numpy=False)
                probabilities = logit_model.calculate_choice_probabilities(utility_scores)
                
                # 根据概率分配购买
                allocated_count = 0
                for i, option in enumerate(options):
                    purchase_count = int(probabilities[i] * current_batch)
                    allocated_count += purchase_count
                    
                    if purchase_count == 0:
                        continue
                    
                    if option['vehicle'] is None:
                        route_unmet(purchase_count, "LOW_UTILITY_OR_PRICE")
                    else:
                        vehicle = option['vehicle']
                        # 考虑库存限制
                        actual_sales = min(purchase_count, vehicle.available_units)

                        if actual_sales > 0 and vehicle.dealer_inventory_id is not None:
                            dealer_inventory = self.db.query(DealershipInventory).filter(
                                DealershipInventory.id == vehicle.dealer_inventory_id
                            ).first()

                            if dealer_inventory and dealer_inventory.sell_units(actual_sales):
                                vehicle.available_units -= actual_sales
                                total_new_sales += actual_sales
                                bucket.satisfied_demand += actual_sales

                                customer_revenue = vehicle.price * actual_sales
                                company_revenue = customer_revenue * vehicle.revenue_retention
                                manufacturing_cost = vehicle.manufacturing_cost * actual_sales
                                gross_profit = company_revenue - manufacturing_cost

                                sales_by_company[vehicle.company_id] = (
                                    sales_by_company.get(vehicle.company_id, 0) + actual_sales
                                )

                                if vehicle.car_trim_id:
                                    sales_by_trim[vehicle.car_trim_id] = (
                                        sales_by_trim.get(vehicle.car_trim_id, 0) + actual_sales
                                    )

                                    detail = sales_details_by_trim.setdefault(
                                        vehicle.car_trim_id,
                                        {
                                            "trim_id": vehicle.car_trim_id,
                                            "company_id": vehicle.company_id,
                                            "units_sold": 0,
                                            "customer_revenue": 0.0,
                                            "revenue_total": 0.0,
                                            "manufacturing_cost_total": 0.0,
                                            "gross_profit_total": 0.0,
                                            "discount_weighted_total": 0.0,
                                        }
                                    )
                                    detail["units_sold"] += actual_sales
                                    detail["customer_revenue"] += customer_revenue
                                    detail["revenue_total"] += company_revenue
                                    detail["manufacturing_cost_total"] += manufacturing_cost
                                    detail["gross_profit_total"] += gross_profit
                                    detail["discount_weighted_total"] += (
                                        (vehicle.discount_percent / 100.0) * actual_sales
                                    )
                            else:
                                actual_sales = 0

                        stock_shortfall = purchase_count - actual_sales
                        if stock_shortfall > 0:
                            route_unmet(stock_shortfall, "NO_NEW_STOCK")

                rounding_lost = current_batch - allocated_count
                if rounding_lost > 0:
                    route_unmet(rounding_lost, "ROUNDING_LOST")
                
                remaining_demand -= current_batch

        used_car_sales = self._simulate_used_car_sales(
            game_id=game_id,
            region_id=region.id,
            demand=used_candidate_demand
        )
        used_stockout = used_candidate_demand - used_car_sales
        if used_stockout > 0:
            lost_demand_by_reason["USED_STOCKOUT"] += used_stockout

        self.db.flush()
        
        return {
            "total_new_sales": total_new_sales,
            "used_car_sales": used_car_sales,
            "sales_by_company": sales_by_company,
            "sales_by_trim": sales_by_trim,
            "sales_details_by_trim": sales_details_by_trim,
            "total_revenue": sum(d["revenue_total"] for d in sales_details_by_trim.values()),
            "total_manufacturing_cost": sum(
                d["manufacturing_cost_total"] for d in sales_details_by_trim.values()
            ),
            "total_gross_profit": sum(
                d["gross_profit_total"] for d in sales_details_by_trim.values()
            ),
            "lost_demand_by_reason": dict(lost_demand_by_reason),
        }

    def _simulate_used_car_sales(self, game_id: int, region_id: int, demand: int) -> int:
        """用现有二手车库存承接未满足的新车需求。"""
        if demand <= 0:
            return 0

        used_cars = self.db.query(UsedCarInventory).filter(
            UsedCarInventory.game_id == game_id,
            UsedCarInventory.region_id == region_id,
            UsedCarInventory.quantity > 0
        ).order_by(
            UsedCarInventory.condition_score.desc(),
            UsedCarInventory.avg_asking_price.asc()
        ).all()

        total_sold = 0

        for used_car in used_cars:
            if total_sold >= demand:
                break

            max_sellable = min(used_car.quantity, demand - total_sold)
            avg_market_price = 25000.0
            price_factor = min(1.0, avg_market_price / max(used_car.avg_asking_price, 1.0))
            condition_factor = used_car.condition_score / 100.0
            actual_sold = int(max_sellable * price_factor * condition_factor)
            actual_sold = max(0, min(actual_sold, used_car.quantity))

            if actual_sold <= 0:
                continue

            used_car.quantity -= actual_sold
            total_sold += actual_sold

        return total_sold

    def _persist_market_outcome(
        self,
        game_id: int,
        game_state: GameState,
        region: Region,
        result: MarketResolutionResult
    ) -> None:
        """写入销售历史、需求历史，并更新公司本回合财务指标。"""
        report_turn = game_state.turn_number + 1

        for detail in result.sales_details_by_trim.values():
            units_sold = detail["units_sold"]
            if units_sold <= 0:
                continue

            revenue_total = detail["revenue_total"]
            gross_profit_total = detail["gross_profit_total"]
            manufacturing_cost_total = detail["manufacturing_cost_total"]
            avg_transaction_price = detail["customer_revenue"] / units_sold
            avg_discount_percent = detail["discount_weighted_total"] / units_sold
            market_share_percent = (
                units_sold / result.total_sales * 100.0
                if result.total_sales > 0 else 0.0
            )
            gross_margin_percent = (
                gross_profit_total / revenue_total * 100.0
                if revenue_total > 0 else 0.0
            )

            self.db.add(SalesHistory(
                game_id=game_id,
                turn_number=report_turn,
                year=game_state.current_year,
                month=game_state.current_month,
                region_id=region.id,
                trim_id=detail["trim_id"],
                company_id=detail["company_id"],
                units_sold=units_sold,
                revenue_total=revenue_total,
                avg_transaction_price=avg_transaction_price,
                avg_discount_percent=avg_discount_percent,
                market_share_percent=market_share_percent,
                gross_profit_total=gross_profit_total,
                gross_margin_percent=gross_margin_percent,
            ))

            company = self.db.query(Company).filter(
                Company.id == detail["company_id"]
            ).first()
            if not company:
                continue

            company.record_revenue(revenue_total, units_sold=units_sold)
            company.record_cost("manufacturing", manufacturing_cost_total)

        lost_demand = sum(result.lost_demand_by_reason.values())
        demand_record = self.db.query(MarketDemandHistory).filter(
            MarketDemandHistory.game_id == game_id,
            MarketDemandHistory.turn_number == report_turn,
            MarketDemandHistory.region_id == region.id
        ).first()

        if demand_record:
            demand_record.year = game_state.current_year
            demand_record.month = game_state.current_month
            demand_record.total_demand = result.total_demand
            demand_record.new_car_sales = result.total_sales
            demand_record.used_car_sales = result.used_car_sales
            demand_record.lost_demand = lost_demand
            demand_record.lost_reasons = result.lost_demand_by_reason
        else:
            self.db.add(MarketDemandHistory(
                game_id=game_id,
                turn_number=report_turn,
                year=game_state.current_year,
                month=game_state.current_month,
                region_id=region.id,
                total_demand=result.total_demand,
                new_car_sales=result.total_sales,
                used_car_sales=result.used_car_sales,
                lost_demand=lost_demand,
                lost_reasons=result.lost_demand_by_reason,
            ))

        self.db.flush()
    
    def _get_brand_perceptions(
        self,
        region_id: int,
        game_id: int
    ) -> Dict[int, BrandPerception]:
        """获取所有公司的品牌认知（以company_id为键）"""
        perceptions = self.db.query(BrandPerception).filter(
            BrandPerception.region_id == region_id,
            BrandPerception.game_id == game_id
        ).all()
        
        return {p.company_id: p for p in perceptions}
    
    def _get_active_campaigns(
        self,
        region_id: int,
        game_id: int,
        target_segment: str,
        current_turn: int
    ) -> Dict[int, List[MarketingCampaign]]:
        """获取当前活跃的营销活动"""
        campaigns = self.db.query(MarketingCampaign).filter(
            MarketingCampaign.region_id == region_id,
            MarketingCampaign.game_id == game_id,
            MarketingCampaign.is_active == True,
            MarketingCampaign.target_bucket == target_segment,
            MarketingCampaign.start_turn <= current_turn,
            MarketingCampaign.end_turn >= current_turn
        ).all()
        
        # 按公司分组
        by_company = {}
        for campaign in campaigns:
            if campaign.company_id not in by_company:
                by_company[campaign.company_id] = []
            by_company[campaign.company_id].append(campaign)
        
        return by_company
    
    def _calculate_utility(
        self,
        vehicle: VehicleOption,
        bucket: ConsumerBucket,
        brand_perception: Optional[BrandPerception],
        marketing_campaigns: List[MarketingCampaign],
        region: Region
    ) -> float:
        """
        计算效用分数（核心算法）
        
        U(vehicle, buyer) = Σ(weight_i × score_i) × brand_modifier × price_modifier × marketing_boost
        
        Returns:
            效用分数（0-1+）
        """
        # 1. 基础效用（属性加权和）
        base_utility = (
            bucket.weight_performance * vehicle.performance_score +
            bucket.weight_comfort * vehicle.comfort_score +
            bucket.weight_reliability * vehicle.reliability_score +
            bucket.weight_safety * vehicle.safety_score +
            bucket.weight_efficiency * vehicle.efficiency_score +
            bucket.weight_practicality * vehicle.practicality_score +
            bucket.weight_prestige * vehicle.prestige_score
        )
        
        # 2. 价格修正（价格效用）
        price_utility = self._calculate_price_utility(
            price=vehicle.price,
            buyer_income=bucket.avg_income,
            price_sensitivity=bucket.price_sensitivity
        )
        
        # 加权价格
        total_utility = base_utility * (1 - bucket.weight_price) + price_utility * bucket.weight_price
        
        # 3. 品牌修正
        if brand_perception:
            brand_modifier = self._calculate_brand_modifier(
                brand=brand_perception,
                bucket=bucket
            )
            total_utility *= brand_modifier
        
        # 4. 营销推动
        if marketing_campaigns:
            marketing_boost = self._calculate_marketing_boost(
                campaigns=marketing_campaigns,
                region=region
            )
            total_utility *= (1.0 + marketing_boost)
        
        return max(0.0, min(2.0, total_utility))  # 限制在0-2范围
    
    def _calculate_price_utility(
        self,
        price: float,
        buyer_income: float,
        price_sensitivity: float
    ) -> float:
        """
        计算价格效用
        价格越低（相对收入），效用越高
        
        Returns:
            价格效用分数（0-1）
        """
        # 价格收入比
        price_to_income = price / (buyer_income * 3.0)  # 假设3年收入
        
        # 基础价格效用（反比关系）
        if price_to_income <= 0.5:
            utility = 1.0
        elif price_to_income <= 1.0:
            utility = 1.0 - (price_to_income - 0.5) * 0.5
        else:
            utility = 0.5 * (1.0 / price_to_income)
        
        # 应用价格敏感度
        # 高敏感度：价格影响更大
        utility = utility ** (1.0 + price_sensitivity)
        
        return max(0.0, min(1.0, utility))
    
    def _calculate_brand_modifier(
        self,
        brand: BrandPerception,
        bucket: ConsumerBucket
    ) -> float:
        """
        计算品牌修正系数
        基于品牌认知和细分偏好的匹配度
        
        Returns:
            品牌修正系数（0.5 - 1.5）
        """
        # 基础修正：品牌知名度
        modifier = 0.8 + brand.overall_awareness * 0.4  # 0.8 - 1.2
        
        # 粉丝基数影响（忠诚客户加成）
        if bucket.brand_loyalty > 0.5:
            fanbase_bonus = min(brand.fanbase_count / bucket.population_count, 0.2)
            modifier += fanbase_bonus
        
        # 品牌属性与细分需求匹配
        # 例如：SPORTS细分更看重sportiness_score
        # 这里简化处理，可以后续扩展
        
        return max(0.5, min(1.5, modifier))
    
    def _calculate_marketing_boost(
        self,
        campaigns: List[MarketingCampaign],
        region: Region
    ) -> float:
        """
        计算营销推动效果
        
        Returns:
            营销提升系数（0 - 0.5，表示0-50%提升）
        """
        if not campaigns:
            return 0.0
        
        total_boost = 0.0
        
        for campaign in campaigns:
            # 基础效果：基于预算
            base_effect = min(campaign.budget / 1000000.0, 0.3)  # 最高30%
            
            # 经济周期修正（衰退期营销效果下降）
            economic_modifier = self._calculate_economic_modifier(region)
            adjusted_effect = base_effect * economic_modifier
            
            # 根据焦点类型调整
            if campaign.focus == MarketingFocus.SALES_PUSH.value:
                adjusted_effect *= 1.5  # 促销活动效果更直接
            elif campaign.focus == MarketingFocus.BRAND_AWARENESS.value:
                adjusted_effect *= 0.8  # 品牌建设长期效果，短期较弱
            
            total_boost += adjusted_effect
        
        return min(total_boost, 0.5)  # 最高50%提升


# ========== 便捷函数 ==========

def run_market_simulation_for_region(
    db: Session,
    region_id: int,
    current_turn: int,
    game_id: int
) -> MarketResolutionResult:
    """
    便捷函数：运行单个地区的市场模拟
    """
    simulator = MarketSimulator(db)
    return simulator.calculate_monthly_sales(region_id, current_turn, game_id)


def run_market_simulation_for_all_regions(
    db: Session,
    game_id: int,
    current_turn: int
) -> List[MarketResolutionResult]:
    """
    便捷函数：运行所有地区的市场模拟
    """
    results = []
    
    regions = db.query(Region).filter(Region.game_id == game_id).all()
    
    for region in regions:
        result = run_market_simulation_for_region(
            db=db,
            region_id=region.id,
            current_turn=current_turn,
            game_id=game_id
        )
        results.append(result)
    
    return results


__all__ = [
    "MarketSimulator",
    "MarketResolutionResult",
    "VehicleOption",
    "run_market_simulation_for_region",
    "run_market_simulation_for_all_regions"
]
