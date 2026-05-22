"""
市场模拟核心算法
实现月度销售计算、需求匹配和市场解析
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
import math
import random
import time

from backend.models.market import (
    ConsumerBucket, DistributionNetwork, BrandPerception,
    MarketingCampaign, DistributionType, MarketingFocus
)
from backend.models.engineering import CarTrim
from backend.models.region import Region
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
        region = self._get_region(region_id)
        consumer_buckets = self._get_consumer_buckets(region_id, game_id)
        available_vehicles = self._get_available_vehicles(region_id, game_id)
        
        logger.debug(f"  消费者细分数: {len(consumer_buckets)}")
        logger.debug(f"  可选车型数: {len(available_vehicles)}")
        
        # 阶段2：计算每个细分的需求
        total_demand = self._calculate_demand(consumer_buckets, region, current_turn)
        
        # 阶段3：运行购买模拟
        sales_result = self._simulate_purchases(
            consumer_buckets=consumer_buckets,
            vehicles=available_vehicles,
            region=region,
            game_id=game_id
        )
        
        # 阶段4：生成结果
        execution_time_ms = (time.time() - start_time) * 1000
        
        result = MarketResolutionResult(
            region_id=region_id,
            total_demand=total_demand,
            total_sales=sales_result["total_new_sales"],
            sales_by_company=sales_result["sales_by_company"],
            sales_by_trim=sales_result["sales_by_trim"],
            unmet_demand=total_demand - sales_result["total_new_sales"] - sales_result["used_car_sales"],
            used_car_sales=sales_result["used_car_sales"],
            execution_time_ms=execution_time_ms
        )
        
        logger.info(
            f"✓ 地区 {region_id} 市场解析完成 | "
            f"需求: {total_demand:,} | 新车销量: {result.total_sales:,} | "
            f"二手车: {result.used_car_sales:,} | 耗时: {execution_time_ms:.2f}ms"
        )
        
        return result
    
    # ========== 阶段1：获取数据 ==========
    
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
        game_id: int
    ) -> List[VehicleOption]:
        """
        获取该地区可购买的所有车辆
        包含分销覆盖度过滤
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
                DistributionNetwork.company_id == trim.company_id,
                DistributionNetwork.region_id == region_id,
                DistributionNetwork.is_active == True
            ).first()
            
            if not distribution or distribution.coverage_level == 0.0:
                # 该公司在此地区无分销，车辆不可见
                continue
            
            # 创建车辆选项
            vehicle = self._convert_trim_to_option(
                trim=trim,
                distribution=distribution
            )
            vehicles.append(vehicle)
        
        # TODO: 添加二手车选项（简化版）
        # 这里可以后续扩展，现在只模拟新车市场
        
        return vehicles
    
    def _convert_trim_to_option(
        self,
        trim: CarTrim,
        distribution: DistributionNetwork
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
            price=trim.msrp,
            performance_score=performance_score,
            comfort_score=comfort_score,
            reliability_score=reliability_score,
            safety_score=safety_score,
            efficiency_score=efficiency_score,
            practicality_score=practicality_score,
            prestige_score=prestige_score,
            is_used=False,
            distribution_coverage=distribution.coverage_level,
            available_units=distribution.monthly_capacity
        )
    
    # ========== 阶段2：需求计算 ==========
    
    def _calculate_demand(
        self,
        buckets: List[ConsumerBucket],
        region: Region,
        current_turn: int
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
            demand = monthly_base_demand * economic_modifier * random.uniform(0.9, 1.1)
            bucket.current_demand = int(demand)
            bucket.satisfied_demand = 0  # 重置
            
            total_demand += bucket.current_demand
        
        self.db.commit()
        
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
        game_id: int
    ) -> Dict:
        """
        运行购买模拟（使用Multinomial Logit模型）
        每个消费者细分评估所有车辆并做出购买决策
        """
        sales_by_company = {}
        sales_by_trim = {}
        total_new_sales = 0
        used_car_sales = 0
        
        # 随机打乱顺序以避免系统性偏差
        random.shuffle(consumer_buckets)
        
        for bucket in consumer_buckets:
            if bucket.current_demand == 0:
                continue
            
            # 获取品牌认知数据
            brand_perceptions = self._get_brand_perceptions(region.id, game_id)
            
            # 获取营销活动数据
            active_campaigns = self._get_active_campaigns(region.id, game_id, bucket.segment)
            
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
                    used_car_sales += int(current_batch * 0.3)
                    remaining_demand -= current_batch
                    continue
                
                # 初始化Logit模型
                # Beta参数：价格负系数，性能正系数，品牌正系数
                logit_model = MultinomialLogit(beta_params={
                    'price': -0.00002,  # 价格每增加$1，效用降低0.00002
                    'performance': 0.01,  # 性能每增加1分，效用增加0.01
                    'brand': 0.02,  # 品牌知名度每增加1分，效用增加0.02
                    'utility': 3.0  # 直接效用得分的权重
                })
                
                # 计算选择概率
                probabilities = logit_model.calculate_probabilities(options)
                
                # 根据概率分配购买
                for i, option in enumerate(options):
                    purchase_count = int(probabilities[i] * current_batch)
                    
                    if purchase_count == 0:
                        continue
                    
                    if option['vehicle'] is None:
                        # "不购买"选项：30%转向二手车
                        used_car_sales += int(purchase_count * 0.3)
                    else:
                        vehicle = option['vehicle']
                        # 考虑库存限制
                        actual_sales = min(purchase_count, vehicle.available_units)
                        
                        vehicle.available_units -= actual_sales
                        total_new_sales += actual_sales
                        bucket.satisfied_demand += actual_sales
                        
                        # 记录销量
                        sales_by_company[vehicle.company_id] = \
                            sales_by_company.get(vehicle.company_id, 0) + actual_sales
                        
                        if vehicle.car_trim_id:
                            sales_by_trim[vehicle.car_trim_id] = \
                                sales_by_trim.get(vehicle.car_trim_id, 0) + actual_sales
                
                remaining_demand -= current_batch
        
        # 提交数据库更新
        self.db.commit()
        
        return {
            "total_new_sales": total_new_sales,
            "used_car_sales": used_car_sales,
            "sales_by_company": sales_by_company,
            "sales_by_trim": sales_by_trim
        }
    
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
        target_segment: str
    ) -> Dict[int, List[MarketingCampaign]]:
        """获取当前活跃的营销活动"""
        campaigns = self.db.query(MarketingCampaign).filter(
            MarketingCampaign.region_id == region_id,
            MarketingCampaign.game_id == game_id,
            MarketingCampaign.is_active == True,
            MarketingCampaign.target_bucket == target_segment
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

