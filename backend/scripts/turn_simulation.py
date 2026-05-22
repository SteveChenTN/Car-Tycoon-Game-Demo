"""
回合模拟脚本
模拟2个AI公司和1个玩家公司在3个不同国家进行12个月的销售

观察点：
1. 有没有哪个公司因为没有销售网络而销量为0？
2. 销量是否随每个月的"季节性波动"或"经济指数"变化？
3. AI是否在某个时刻发布了新营销活动？
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Any, Optional
import time
from datetime import datetime
from collections import defaultdict

from backend.database import SessionLocal, init_db
from backend.models import (
    GameState, Region, CarTrim, Engine, Chassis,
    DistributionNetwork, MarketingCampaign, ConsumerBucket, BrandPerception
)
from backend.core.economics.market_simulation import MarketSimulator, MarketResolutionResult
from backend.core.ai.ai_strategy import (
    AI_CEO, CEOPersonality, AIDecisionExecutor, create_random_personality
)
from backend.utils.logger import setup_logging, get_logger
from backend.config import GameConstants, MarketConstants
from backend.models.market import DistributionType, MarketingFocus, ConsumerSegment

logger = get_logger(__name__)


# ========== 数据初始化 ==========

def create_test_game(db) -> GameState:
    """创建测试游戏状态"""
    game = GameState(
        save_name="Turn Simulation Test",
        current_year=1950,
        current_month=1,
        current_week=1,
        turn_number=0,
        difficulty="normal",
        simulation_speed="monthly"
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    logger.info(f"创建游戏状态: ID={game.id}, 名称={game.save_name}")
    return game


def create_test_regions(db, game_id: int) -> List[Region]:
    """创建3个测试地区"""
    regions_data = [
        {
            "code": "NAM",
            "name": "North America",
            "population": 200_000_000,
            "gdp_per_capita": 15000.0,
            "gdp_growth_rate": 0.035,
            "purchasing_power_index": 1.2,
            "inflation_rate": 0.03,
            "unemployment_rate": 0.04,
            "car_ownership_rate": 350.0,
            "avg_vehicle_age": 10.0,
            "annual_sales_potential": 7_000_000,
            "infrastructure_quality": 0.85,
            "road_quality": 0.80,
            "fuel_price": 0.30,
            "electricity_price": 0.12,
            "import_tariff_rate": 0.025,
            "emission_standard": "NONE",
            "safety_standard": "BASIC",
            "corporate_tax_rate": 0.35,
            "ev_subsidy_rate": 0.0,
            "steel_availability": 0.9,
            "aluminum_availability": 0.8,
            "rare_earth_availability": 0.5,
            "labor_cost_index": 1.3,
            "skilled_labor_availability": 0.8,
            "pref_size_small": 0.20,
            "pref_size_medium": 0.35,
            "pref_size_large": 0.45,
            "pref_body_sedan": 0.35,
            "pref_body_suv": 0.35,
            "pref_body_hatchback": 0.10,
            "pref_body_coupe": 0.15,
            "pref_body_wagon": 0.05,
            "pref_fuel_efficiency_weight": 0.3,
            "pref_power_weight": 0.7,
        },
        {
            "code": "EUR",
            "name": "Europe",
            "population": 350_000_000,
            "gdp_per_capita": 8000.0,
            "gdp_growth_rate": 0.03,
            "purchasing_power_index": 1.0,
            "inflation_rate": 0.025,
            "unemployment_rate": 0.06,
            "car_ownership_rate": 250.0,
            "avg_vehicle_age": 12.0,
            "annual_sales_potential": 7_300_000,
            "infrastructure_quality": 0.75,
            "road_quality": 0.85,
            "fuel_price": 0.50,
            "electricity_price": 0.15,
            "import_tariff_rate": 0.10,
            "emission_standard": "NONE",
            "safety_standard": "MODERATE",
            "corporate_tax_rate": 0.40,
            "ev_subsidy_rate": 0.0,
            "steel_availability": 0.85,
            "aluminum_availability": 0.7,
            "rare_earth_availability": 0.4,
            "labor_cost_index": 1.1,
            "skilled_labor_availability": 0.85,
            "pref_size_small": 0.45,
            "pref_size_medium": 0.40,
            "pref_size_large": 0.15,
            "pref_body_sedan": 0.30,
            "pref_body_suv": 0.20,
            "pref_body_hatchback": 0.35,
            "pref_body_coupe": 0.05,
            "pref_body_wagon": 0.10,
            "pref_fuel_efficiency_weight": 0.7,
            "pref_power_weight": 0.3,
        },
        {
            "code": "ASI",
            "name": "Asia-Pacific",
            "population": 800_000_000,
            "gdp_per_capita": 2000.0,
            "gdp_growth_rate": 0.06,
            "purchasing_power_index": 0.6,
            "inflation_rate": 0.04,
            "unemployment_rate": 0.05,
            "car_ownership_rate": 50.0,
            "avg_vehicle_age": 15.0,
            "annual_sales_potential": 2_700_000,
            "infrastructure_quality": 0.45,
            "road_quality": 0.50,
            "fuel_price": 0.35,
            "electricity_price": 0.08,
            "import_tariff_rate": 0.30,
            "emission_standard": "NONE",
            "safety_standard": "BASIC",
            "corporate_tax_rate": 0.25,
            "ev_subsidy_rate": 0.0,
            "steel_availability": 0.95,
            "aluminum_availability": 0.6,
            "rare_earth_availability": 0.9,
            "labor_cost_index": 0.5,
            "skilled_labor_availability": 0.6,
            "pref_size_small": 0.60,
            "pref_size_medium": 0.30,
            "pref_size_large": 0.10,
            "pref_body_sedan": 0.50,
            "pref_body_suv": 0.15,
            "pref_body_hatchback": 0.30,
            "pref_body_coupe": 0.02,
            "pref_body_wagon": 0.03,
            "pref_fuel_efficiency_weight": 0.8,
            "pref_power_weight": 0.2,
        },
    ]
    
    regions = []
    for data in regions_data:
        region = Region(game_id=game_id, **data)
        db.add(region)
        regions.append(region)
    
    db.commit()
    for region in regions:
        db.refresh(region)
        logger.info(f"创建地区: {region.code} - {region.name} (ID={region.id})")
    
    return regions


def create_test_companies(db, game_id: int) -> Dict[str, int]:
    """
    创建3个测试公司
    返回: {"player": company_id, "ai1": company_id, "ai2": company_id}
    
    注意：由于Company模型尚未实现，我们使用company_id作为整数标识
    """
    # 公司ID映射（简化版，实际应该从数据库创建Company记录）
    companies = {
        "player": 1,   # 玩家公司
        "ai1": 2,      # AI公司1
        "ai2": 3       # AI公司2
    }
    
    logger.info(f"创建公司: 玩家={companies['player']}, AI1={companies['ai1']}, AI2={companies['ai2']}")
    return companies


def create_test_engines(db, game_id: int, company_ids: Dict[str, int]) -> Dict[int, Engine]:
    """为每个公司创建测试引擎"""
    engines = {}
    
    # 玩家公司：中等性能引擎
    player_engine = Engine(
        game_id=game_id,
        company_id=company_ids["player"],
        name="Player V6",
        code=f"PLAYER_V6_{game_id}_{company_ids['player']}",
        bore_mm=88.0,
        stroke_mm=82.0,
        cylinder_count=6,
        configuration="V",
        compression_ratio=10.5,
        induction_type="NA",
        boost_pressure_bar=0.0,
        material="CAST_IRON",
        valvetrain="OHV",
        fuel_type="GASOLINE",
        tech_level=3,
        displacement_cc=2998,
        max_horsepower=180,
        max_torque_nm=280,
        redline_rpm=5500,
        weight_kg=180.0,
        length_mm=650.0,
        width_mm=750.0,
        height_mm=650.0,
        thermal_load=0.6,
        specific_output=60.0,
        reliability_base_score=75.0,
        fuel_efficiency_rating=6.5,
        bsfc_g_kwh=280.0,
        manufacturing_cost=1500.0,  # 单位制造成本
        is_available=True
    )
    db.add(player_engine)
    engines[company_ids["player"]] = player_engine
    
    # AI公司1：高性能引擎
    ai1_engine = Engine(
        game_id=game_id,
        company_id=company_ids["ai1"],
        name="AI1 Turbo I4",
        code=f"AI1_TURBO_I4_{game_id}_{company_ids['ai1']}",
        bore_mm=86.0,
        stroke_mm=86.0,
        cylinder_count=4,
        configuration="INLINE",
        compression_ratio=9.0,
        induction_type="TURBO",
        boost_pressure_bar=0.8,
        material="ALUMINUM",
        valvetrain="DOHC",
        fuel_type="GASOLINE",
        tech_level=4,
        displacement_cc=1998,
        max_horsepower=220,
        max_torque_nm=350,
        redline_rpm=6500,
        weight_kg=145.0,
        length_mm=500.0,
        width_mm=600.0,
        height_mm=600.0,
        thermal_load=0.75,
        specific_output=110.0,
        reliability_base_score=70.0,
        fuel_efficiency_rating=7.0,
        bsfc_g_kwh=260.0,
        manufacturing_cost=1800.0,  # 单位制造成本
        is_available=True
    )
    db.add(ai1_engine)
    engines[company_ids["ai1"]] = ai1_engine
    
    # AI公司2：经济型引擎
    ai2_engine = Engine(
        game_id=game_id,
        company_id=company_ids["ai2"],
        name="AI2 Economy I4",
        code=f"AI2_ECO_I4_{game_id}_{company_ids['ai2']}",
        bore_mm=80.0,
        stroke_mm=90.0,
        cylinder_count=4,
        configuration="INLINE",
        compression_ratio=9.5,
        induction_type="NA",
        boost_pressure_bar=0.0,
        material="CAST_IRON",
        valvetrain="OHV",
        fuel_type="GASOLINE",
        tech_level=2,
        displacement_cc=1800,
        max_horsepower=95,
        max_torque_nm=150,
        redline_rpm=5000,
        weight_kg=120.0,
        length_mm=450.0,
        width_mm=550.0,
        height_mm=550.0,
        thermal_load=0.5,
        specific_output=52.8,
        reliability_base_score=80.0,
        fuel_efficiency_rating=8.5,
        bsfc_g_kwh=250.0,
        manufacturing_cost=1200.0,  # 单位制造成本
        is_available=True
    )
    db.add(ai2_engine)
    engines[company_ids["ai2"]] = ai2_engine
    
    db.commit()
    for company_id, engine in engines.items():
        db.refresh(engine)
        logger.info(f"创建引擎: {engine.name} (ID={engine.id}, 公司={company_id})")
    
    return engines


def create_test_chassis(db, game_id: int, company_ids: Dict[str, int]) -> Dict[int, Chassis]:
    """为每个公司创建测试底盘"""
    chassis_dict = {}
    
    # 玩家公司：中型车底盘
    player_chassis = Chassis(
        game_id=game_id,
        company_id=company_ids["player"],
        name="Player Midsize Platform",
        code=f"PLAYER_MIDSIZE_{game_id}_{company_ids['player']}",
        wheelbase_mm=2700,
        track_front_mm=1500,
        track_rear_mm=1500,
        layout="FR",  # 前置后驱
        engine_bay_length_mm=700.0,
        engine_bay_width_mm=800.0,
        engine_bay_height_mm=700.0,
        max_cooling_capacity_kw=150.0,
        material="STEEL",
        rigidity_rating=70.0,
        weight_kg=1200.0,
        crash_test_rating=60.0,
        tech_level=3,
        manufacturing_cost=3000.0,  # 单位制造成本
        is_available=True
    )
    db.add(player_chassis)
    chassis_dict[company_ids["player"]] = player_chassis
    
    # AI公司1：紧凑型运动底盘
    ai1_chassis = Chassis(
        game_id=game_id,
        company_id=company_ids["ai1"],
        name="AI1 Compact Sport",
        code=f"AI1_COMPACT_SPORT_{game_id}_{company_ids['ai1']}",
        wheelbase_mm=2600,
        track_front_mm=1480,
        track_rear_mm=1480,
        layout="FF",  # 前置前驱
        engine_bay_length_mm=600.0,
        engine_bay_width_mm=700.0,
        engine_bay_height_mm=650.0,
        max_cooling_capacity_kw=180.0,
        material="ALUMINUM",
        rigidity_rating=75.0,
        weight_kg=1000.0,
        crash_test_rating=55.0,
        tech_level=4,
        manufacturing_cost=3500.0,  # 单位制造成本
        is_available=True
    )
    db.add(ai1_chassis)
    chassis_dict[company_ids["ai1"]] = ai1_chassis
    
    # AI公司2：小型经济底盘
    ai2_chassis = Chassis(
        game_id=game_id,
        company_id=company_ids["ai2"],
        name="AI2 Subcompact Economy",
        code=f"AI2_SUBCOMPACT_ECO_{game_id}_{company_ids['ai2']}",
        wheelbase_mm=2400,
        track_front_mm=1400,
        track_rear_mm=1400,
        layout="FF",  # 前置前驱
        engine_bay_length_mm=500.0,
        engine_bay_width_mm=600.0,
        engine_bay_height_mm=600.0,
        max_cooling_capacity_kw=100.0,
        material="STEEL",
        rigidity_rating=60.0,
        weight_kg=800.0,
        crash_test_rating=50.0,
        tech_level=2,
        manufacturing_cost=2500.0,  # 单位制造成本
        is_available=True
    )
    db.add(ai2_chassis)
    chassis_dict[company_ids["ai2"]] = ai2_chassis
    
    db.commit()
    for company_id, chassis in chassis_dict.items():
        db.refresh(chassis)
        logger.info(f"创建底盘: {chassis.name} (ID={chassis.id}, 公司={company_id})")
    
    return chassis_dict


def create_test_car_trims(
    db, 
    game_id: int, 
    engines: Dict[int, Engine],
    chassis_dict: Dict[int, Chassis],
    company_ids: Dict[str, int]
) -> Dict[int, CarTrim]:
    """为每个公司创建测试车型"""
    trims = {}
    
    for company_id, engine in engines.items():
        chassis = chassis_dict[company_id]
        
        # 计算派生属性
        total_weight = engine.weight_kg + chassis.weight_kg + 200.0  # 引擎+底盘+车身
        power_to_weight = engine.max_horsepower / total_weight
        fuel_economy = 100.0 / (engine.fuel_efficiency_rating * 1.5)  # 简化计算
        
        # 简化的性能计算
        zero_to_hundred = max(5.0, 15.0 - power_to_weight * 2.0)
        top_speed = min(200.0, 80.0 + power_to_weight * 30.0)
        
        trim = CarTrim(
            game_id=game_id,
            company_id=company_id,
            name=f"{chassis.name} Trim",
            model_name=f"{chassis.name}",
            trim_code=f"{chassis.code}_TRIM_{game_id}",
            engine_id=engine.id,
            chassis_id=chassis.id,
            body_style="SEDAN" if "SEDAN" in chassis.name.upper() else "HATCHBACK",
            segment="MIDSIZE" if company_id == company_ids.get("player", 0) else ("COMPACT" if company_id == company_ids.get("ai1", 0) else "SUBCOMPACT"),
            seating_capacity=5,
            cargo_volume_liters=400,
            body_weight_kg=200.0,
            drag_coefficient=0.35,
            frontal_area_sqm=2.5,
            total_weight_kg=total_weight,
            power_to_weight_ratio=power_to_weight,
            zero_to_hundred_kph_sec=zero_to_hundred,
            top_speed_kph=top_speed,
            quarter_mile_sec=zero_to_hundred * 4.0,
            braking_100_0_meters=45.0,
            lateral_g_force=0.8,
            fuel_economy_l_100km=fuel_economy,
            final_reliability_score=engine.reliability_base_score,
            manufacturing_cost=engine.manufacturing_cost + chassis.manufacturing_cost + 500.0,
            msrp=15000.0 + (company_id - 1) * 5000.0,  # 不同价格
            is_in_production=True,
            production_start_turn=0
        )
        db.add(trim)
        trims[company_id] = trim
    
    db.commit()
    for company_id, trim in trims.items():
        db.refresh(trim)
        logger.info(f"创建车型: {trim.name} (ID={trim.id}, 公司={company_id}, 价格={trim.msrp:,.0f})")
    
    return trims


def create_distribution_networks(
    db,
    game_id: int,
    company_ids: Dict[str, int],
    regions: List[Region],
    create_networks: Dict[str, List[str]]
) -> Dict[int, List[DistributionNetwork]]:
    """
    创建分销网络
    
    Args:
        create_networks: {"player": ["NAM", "EUR"], "ai1": ["NAM"], "ai2": []}
                        表示哪些公司在哪些地区有分销网络
                        ai2为空列表，用于测试观察点1（无分销网络导致销量为0）
    """
    networks_by_company = defaultdict(list)
    
    for company_name, region_codes in create_networks.items():
        company_id = company_ids[company_name]
        
        for region_code in region_codes:
            region = next(r for r in regions if r.code == region_code)
            
            network = DistributionNetwork(
                game_id=game_id,
                company_id=company_id,
                region_id=region.id,
                type=DistributionType.FRANCHISE.value,
                coverage_level=0.7,  # 70%覆盖度
                quality_score=70.0,
                monthly_capacity=5000,
                setup_cost=100000.0,
                monthly_upkeep=50000.0,
                profit_split_dealer=0.3,
                is_active=True,
                established_turn=0
            )
            db.add(network)
            networks_by_company[company_id].append(network)
            logger.info(f"创建分销网络: {company_name} -> {region_code}")
    
    db.commit()
    for company_id, networks in networks_by_company.items():
        for network in networks:
            db.refresh(network)
    
    return dict(networks_by_company)


def create_consumer_buckets(db, game_id: int, regions: List[Region]):
    """为每个地区创建消费者细分"""
    for region in regions:
        # 创建几个基础细分
        segments = [
            ("FAMILY", 0.3, 8000.0, 0.4),
            ("PRACTICAL", 0.25, 6000.0, 0.5),
            ("YOUTH", 0.2, 5000.0, 0.6),
            ("SPORTS", 0.15, 12000.0, 0.3),
            ("LUXURY", 0.1, 20000.0, 0.2),
        ]
        
        segment_index = 0
        for segment_name, pop_ratio, avg_income, price_sensitivity in segments:
            population = int(region.population * pop_ratio / 1000)  # 简化：每千人中的潜在买家
            
            # 生成唯一的bucket_code和name（包含索引确保唯一性）
            bucket_code = f"{region.code}_{segment_name}_{game_id}_{segment_index}"
            bucket_name = f"{region.name} {segment_name} Segment"
            
            # 根据细分类型设置平均年龄
            age_map = {
                "YOUTH": 25.0,
                "FAMILY": 35.0,
                "PRACTICAL": 40.0,
                "SPORTS": 30.0,
                "LUXURY": 45.0
            }
            avg_age = age_map.get(segment_name, 35.0)
            
            bucket = ConsumerBucket(
                game_id=game_id,
                region_id=region.id,
                bucket_code=bucket_code,
                name=bucket_name,
                segment=segment_name,
                population_count=population,
                avg_income=avg_income,
                avg_age=avg_age,
                price_sensitivity=price_sensitivity,
                purchase_frequency_years=8.0,
                brand_loyalty=0.5,
                early_adopter_score=0.3,
                weight_price=0.3,
                weight_performance=0.15,
                weight_comfort=0.15,
                weight_reliability=0.15,
                weight_safety=0.10,
                weight_efficiency=0.10,
                weight_practicality=0.05,
                weight_prestige=0.0,
                preferred_body_styles='["SEDAN", "HATCHBACK"]',
                preferred_size="MEDIUM",
                current_demand=0,
                satisfied_demand=0,
                min_acceptable_utility=0.3
            )
            db.add(bucket)
            segment_index += 1
        
        logger.info(f"为地区 {region.code} 创建了 {len(segments)} 个消费者细分")
    
    db.commit()


def create_brand_perceptions(db, game_id: int, company_ids: Dict[str, int], regions: List[Region]):
    """创建初始品牌认知"""
    for region in regions:
        for company_name, company_id in company_ids.items():
            perception = BrandPerception(
                game_id=game_id,
                company_id=company_id,
                region_id=region.id,
                overall_awareness=0.5,  # 初始50%认知度
                fanbase_count=10000,
                sportiness_score=50.0,
                luxury_score=50.0,
                reliability_score=50.0,
                eco_friendly_score=50.0,
                value_for_money_score=50.0,
                innovation_score=50.0
            )
            db.add(perception)
    
    db.commit()
    logger.info("创建初始品牌认知数据")


# ========== 模拟主循环 ==========

def run_turn_simulation(
    db,
    game: GameState,
    company_ids: Dict[str, int],
    regions: List[Region],
    ai_personalities: Dict[int, CEOPersonality]
) -> Dict[str, Any]:
    """
    运行12个月的回合模拟
    
    Returns:
        包含所有观察点数据的字典
    """
    simulator = MarketSimulator(db)
    ai_executor = AIDecisionExecutor(db)
    
    # 记录数据
    monthly_results = []
    campaign_events = []
    
    logger.info("\n" + "="*80)
    logger.info("开始12个月回合模拟")
    logger.info("="*80)
    
    for month in range(1, 13):
        current_turn = game.turn_number
        
        logger.info(f"\n--- 第 {month} 月 (回合 {current_turn}) ---")
        logger.info(f"日期: {game.current_year}-{game.current_month:02d}")
        
        # 阶段1: AI决策
        ai_decisions_by_company = {}
        for company_name, company_id in company_ids.items():
            if company_name.startswith("ai"):
                personality = ai_personalities[company_id]
                ai_ceo = AI_CEO(db, company_id, personality)
                decisions = ai_ceo.make_turn_decisions(game.id, current_turn)
                
                # 执行决策
                for decision in decisions:
                    success = ai_executor.execute_decision(
                        decision, company_id, game.id, current_turn
                    )
                    if success and decision.decision_type == "MARKETING":
                        campaign_events.append({
                            "month": month,
                            "company_id": company_id,
                            "company_name": company_name,
                            "action": decision.action,
                            "reasoning": decision.reasoning,
                            "parameters": decision.parameters
                        })
                        logger.info(f"  ✓ {company_name} 启动营销活动: {decision.reasoning}")
                
                ai_decisions_by_company[company_id] = decisions
        
        # 阶段2: 市场模拟（每个地区）
        month_sales = defaultdict(lambda: defaultdict(int))  # {company_id: {region_id: sales}}
        month_demands = {}  # {region_id: demand}
        
        for region in regions:
            result = simulator.calculate_monthly_sales(
                region_id=region.id,
                current_turn=current_turn,
                game_id=game.id
            )
            
            month_demands[region.id] = result.total_demand
            
            for company_id, sales in result.sales_by_company.items():
                month_sales[company_id][region.id] = sales
            
            logger.info(
                f"  地区 {region.code}: 需求={result.total_demand:,}, "
                f"新车销量={result.total_sales:,}, "
                f"二手车={result.used_car_sales:,}"
            )
        
        # 阶段3: 记录月度结果
        month_result = {
            "month": month,
            "year": game.current_year,
            "turn": current_turn,
            "sales_by_company": {
                company_id: sum(sales.values())
                for company_id, sales in month_sales.items()
            },
            "sales_by_company_region": {
                company_id: dict(sales)
                for company_id, sales in month_sales.items()
            },
            "demand_by_region": month_demands,
            "economic_indicators": {
                region.id: {
                    "gdp_growth": region.gdp_growth_rate,
                    "unemployment": region.unemployment_rate,
                    "demand_modifier": region.calculate_demand_modifier()
                }
                for region in regions
            }
        }
        monthly_results.append(month_result)
        
        # 阶段4: 推进时间
        game.advance_turn()
        db.commit()
    
    return {
        "monthly_results": monthly_results,
        "campaign_events": campaign_events
    }


# ========== 结果分析与输出 ==========

def analyze_results(results: Dict[str, Any], company_ids: Dict[str, int]) -> None:
    """分析并输出观察点"""
    monthly_results = results["monthly_results"]
    campaign_events = results["campaign_events"]
    
    logger.info("\n" + "="*80)
    logger.info("观察点分析")
    logger.info("="*80)
    
    # 观察点1: 有没有公司因为没有销售网络而销量为0？
    logger.info("\n【观察点1】销售网络对销量的影响")
    logger.info("-" * 80)
    
    zero_sales_companies = []
    for month_data in monthly_results:
        for company_name, company_id in company_ids.items():
            sales = month_data["sales_by_company"].get(company_id, 0)
            if sales == 0:
                zero_sales_companies.append({
                    "month": month_data["month"],
                    "company": company_name,
                    "company_id": company_id
                })
    
    if zero_sales_companies:
        logger.info("发现销量为0的公司:")
        for entry in zero_sales_companies:
            logger.info(f"  第{entry['month']}月: {entry['company']} (ID={entry['company_id']})")
        logger.info("  → 结论: 这些公司可能没有建立分销网络，导致无法销售")
    else:
        logger.info("  所有公司在所有月份都有销量")
    
    # 观察点2: 销量是否随季节性波动或经济指数变化？
    logger.info("\n【观察点2】销量波动与经济指数关系")
    logger.info("-" * 80)
    
    # 计算每个公司的月度销量趋势
    for company_name, company_id in company_ids.items():
        sales_trend = [
            month_data["sales_by_company"].get(company_id, 0)
            for month_data in monthly_results
        ]
        total_sales = sum(sales_trend)
        avg_sales = total_sales / len(sales_trend) if sales_trend else 0
        
        logger.info(f"\n{company_name} (ID={company_id}):")
        logger.info(f"  总销量: {total_sales:,}")
        logger.info(f"  平均月销量: {avg_sales:,.0f}")
        logger.info(f"  月度销量: {[f'{s:,}' for s in sales_trend]}")
        
        # 检查波动性
        if sales_trend:
            min_sales = min(sales_trend)
            max_sales = max(sales_trend)
            variance = max_sales - min_sales
            logger.info(f"  波动范围: {min_sales:,} - {max_sales:,} (差异: {variance:,})")
        
        # 检查与经济指数的相关性
        logger.info("  经济指数变化:")
        for month_data in monthly_results[:3]:  # 显示前3个月
            for region_id, indicators in month_data["economic_indicators"].items():
                logger.info(
                    f"    第{month_data['month']}月: "
                    f"GDP增长={indicators['gdp_growth']:.1%}, "
                    f"失业率={indicators['unemployment']:.1%}, "
                    f"需求修正={indicators['demand_modifier']:.2f}"
                )
    
    # 观察点3: AI是否发布了新营销活动？
    logger.info("\n【观察点3】AI营销活动发布")
    logger.info("-" * 80)
    
    if campaign_events:
        logger.info(f"共发现 {len(campaign_events)} 个营销活动:")
        for event in campaign_events:
            logger.info(
                f"  第{event['month']}月: {event['company_name']} (ID={event['company_id']}) "
                f"启动营销活动"
            )
            logger.info(f"    理由: {event['reasoning']}")
            logger.info(f"    参数: {event['parameters']}")
    else:
        logger.info("  在12个月模拟期间，AI公司未发布任何营销活动")
        logger.info("  → 可能原因: AI决策条件未满足（市场份额未下降、品牌健康度正常等）")
    
    # 汇总表格
    logger.info("\n" + "="*80)
    logger.info("月度销量汇总表")
    logger.info("="*80)
    logger.info(f"{'月份':<6} {'玩家':<12} {'AI1':<12} {'AI2':<12} {'总需求':<12}")
    logger.info("-" * 80)
    
    for month_data in monthly_results:
        month = month_data["month"]
        player_sales = month_data["sales_by_company"].get(company_ids["player"], 0)
        ai1_sales = month_data["sales_by_company"].get(company_ids["ai1"], 0)
        ai2_sales = month_data["sales_by_company"].get(company_ids["ai2"], 0)
        total_demand = sum(month_data["demand_by_region"].values())
        
        logger.info(
            f"{month:<6} {player_sales:<12,} {ai1_sales:<12,} {ai2_sales:<12,} {total_demand:<12,}"
        )


# ========== 主函数 ==========

def main():
    """主函数"""
    setup_logging()
    logger.info("="*80)
    logger.info("回合模拟脚本启动")
    logger.info("="*80)
    
    # 确保data目录存在
    from backend.config import settings
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"数据库路径: {settings.DATABASE_URL}")
    logger.info(f"数据目录: {settings.DATA_DIR}")
    
    db = SessionLocal()
    
    try:
        # 初始化数据库
        init_db()
        
        # 1. 创建游戏状态
        game = create_test_game(db)
        
        # 2. 创建3个地区
        regions = create_test_regions(db, game.id)
        
        # 3. 创建3个公司
        company_ids = create_test_companies(db, game.id)
        
        # 4. 创建引擎、底盘、车型
        engines = create_test_engines(db, game.id, company_ids)
        chassis_dict = create_test_chassis(db, game.id, company_ids)
        trims = create_test_car_trims(db, game.id, engines, chassis_dict, company_ids)
        
        # 5. 创建分销网络（注意：ai2没有分销网络，用于测试观察点1）
        distribution_setup = {
            "player": ["NAM", "EUR", "ASI"],  # 玩家在所有地区都有网络
            "ai1": ["NAM", "EUR"],            # AI1在2个地区有网络
            "ai2": []                         # AI2没有分销网络（测试用）
        }
        networks = create_distribution_networks(
            db, game.id, company_ids, regions, distribution_setup
        )
        
        # 6. 创建消费者细分
        create_consumer_buckets(db, game.id, regions)
        
        # 7. 创建品牌认知
        create_brand_perceptions(db, game.id, company_ids, regions)
        
        # 8. 创建AI人格
        ai_personalities = {
            company_ids["ai1"]: CEOPersonality(
                aggression=70,
                innovation=60,
                risk_tolerance=65,
                loyalty=50
            ),
            company_ids["ai2"]: CEOPersonality(
                aggression=40,
                innovation=50,
                risk_tolerance=30,
                loyalty=70
            )
        }
        
        logger.info("\nAI公司人格设置:")
        for company_name, company_id in company_ids.items():
            if company_name.startswith("ai"):
                p = ai_personalities[company_id]
                logger.info(
                    f"  {company_name} (ID={company_id}): "
                    f"侵略性={p.aggression}, 创新性={p.innovation}, "
                    f"风险承受={p.risk_tolerance}, 忠诚度={p.loyalty}"
                )
        
        # 9. 运行12个月模拟
        results = run_turn_simulation(
            db, game, company_ids, regions, ai_personalities
        )
        
        # 10. 分析结果
        analyze_results(results, company_ids)
        
        logger.info("\n" + "="*80)
        logger.info("模拟完成！")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"模拟过程中发生错误: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

