"""
世界初始化脚本
根据设计文档生成初始地区数据
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Any
import time

from backend.database import SessionLocal, init_db, Base, engine
from backend.models import GameState, Region
from backend.utils.logger import setup_logging, get_logger
from backend.config import GameConstants


logger = get_logger(__name__)


def create_initial_regions(game_id: int) -> List[Region]:
    """
    根据设计文档创建初始地区数据
    
    Args:
        game_id: 游戏ID
        
    Returns:
        创建的Region对象列表
    """
    
    # 基于设计文档 10.1 的初始配置
    regions_data = [
        {
            # 北美 - 高收入，偏好大型车和动力
            "code": "NAM",
            "name": "North America",
            "population": 200_000_000,
            "gdp_per_capita": 15000.0,
            "gdp_growth_rate": 0.035,
            "purchasing_power_index": 1.2,
            "inflation_rate": 0.03,
            "unemployment_rate": 0.04,
            
            "car_ownership_rate": 350.0,  # 每千人350辆
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
            
            # 偏好：大型车为主
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
            # 欧洲 - 中等收入，偏好小型车和燃效
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
            "fuel_price": 0.50,  # 高油价
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
            
            # 偏好：小型车为主
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
            # 亚太 - 低收入但高增长，偏好小型经济车
            "code": "ASI",
            "name": "Asia-Pacific",
            "population": 800_000_000,
            "gdp_per_capita": 2000.0,
            "gdp_growth_rate": 0.06,  # 高增长
            "purchasing_power_index": 0.6,
            "inflation_rate": 0.04,
            "unemployment_rate": 0.05,
            
            "car_ownership_rate": 50.0,  # 低保有量
            "avg_vehicle_age": 15.0,
            "annual_sales_potential": 2_700_000,
            
            "infrastructure_quality": 0.45,
            "road_quality": 0.50,
            "fuel_price": 0.35,
            "electricity_price": 0.08,
            
            "import_tariff_rate": 0.30,  # 高关税保护
            "emission_standard": "NONE",
            "safety_standard": "BASIC",
            "corporate_tax_rate": 0.25,
            "ev_subsidy_rate": 0.0,
            
            "steel_availability": 0.95,
            "aluminum_availability": 0.6,
            "rare_earth_availability": 0.9,  # 亚洲稀土丰富
            "labor_cost_index": 0.5,  # 低劳动力成本
            "skilled_labor_availability": 0.6,
            
            # 偏好：小型车占绝对主导
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
        {
            # 拉丁美洲 - 中低收入，市场增长中
            "code": "LAM",
            "name": "Latin America",
            "population": 250_000_000,
            "gdp_per_capita": 4500.0,
            "gdp_growth_rate": 0.04,
            "purchasing_power_index": 0.75,
            "inflation_rate": 0.06,  # 较高通胀
            "unemployment_rate": 0.08,
            
            "car_ownership_rate": 120.0,
            "avg_vehicle_age": 14.0,
            "annual_sales_potential": 2_100_000,
            
            "infrastructure_quality": 0.50,
            "road_quality": 0.45,
            "fuel_price": 0.40,
            "electricity_price": 0.10,
            
            "import_tariff_rate": 0.20,
            "emission_standard": "NONE",
            "safety_standard": "BASIC",
            "corporate_tax_rate": 0.30,
            "ev_subsidy_rate": 0.0,
            
            "steel_availability": 0.7,
            "aluminum_availability": 0.65,
            "rare_earth_availability": 0.3,
            "labor_cost_index": 0.7,
            "skilled_labor_availability": 0.65,
            
            "pref_size_small": 0.35,
            "pref_size_medium": 0.45,
            "pref_size_large": 0.20,
            
            "pref_body_sedan": 0.40,
            "pref_body_suv": 0.30,
            "pref_body_hatchback": 0.20,
            "pref_body_coupe": 0.05,
            "pref_body_wagon": 0.05,
            
            "pref_fuel_efficiency_weight": 0.6,
            "pref_power_weight": 0.4,
        },
        {
            # 中东非洲 - 低收入，新兴市场
            "code": "MEA",
            "name": "Middle East & Africa",
            "population": 400_000_000,
            "gdp_per_capita": 3000.0,
            "gdp_growth_rate": 0.045,
            "purchasing_power_index": 0.65,
            "inflation_rate": 0.05,
            "unemployment_rate": 0.10,
            
            "car_ownership_rate": 80.0,
            "avg_vehicle_age": 16.0,
            "annual_sales_potential": 2_000_000,
            
            "infrastructure_quality": 0.40,
            "road_quality": 0.40,
            "fuel_price": 0.25,  # 油价低（产油区）
            "electricity_price": 0.09,
            
            "import_tariff_rate": 0.15,
            "emission_standard": "NONE",
            "safety_standard": "BASIC",
            "corporate_tax_rate": 0.20,
            "ev_subsidy_rate": 0.0,
            
            "steel_availability": 0.6,
            "aluminum_availability": 0.5,
            "rare_earth_availability": 0.35,
            "labor_cost_index": 0.6,
            "skilled_labor_availability": 0.5,
            
            "pref_size_small": 0.30,
            "pref_size_medium": 0.40,
            "pref_size_large": 0.30,
            
            "pref_body_sedan": 0.35,
            "pref_body_suv": 0.40,  # SUV偏好较高（地形需求）
            "pref_body_hatchback": 0.15,
            "pref_body_coupe": 0.05,
            "pref_body_wagon": 0.05,
            
            "pref_fuel_efficiency_weight": 0.4,
            "pref_power_weight": 0.6,
        }
    ]
    
    regions = []
    for data in regions_data:
        region = Region(game_id=game_id, **data)
        regions.append(region)
        logger.info(
            f"Created region: {region.code} ({region.name}) - "
            f"Pop: {region.population:,}, GDP/capita: ${region.gdp_per_capita:,.0f}"
        )
    
    return regions


def initialize_world(save_name: str = "NewGame") -> Dict[str, Any]:
    """
    初始化游戏世界
    
    Args:
        save_name: 存档名称
        
    Returns:
        包含game_id等信息的字典
    """
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Starting World Initialization...")
    logger.info("=" * 80)
    
    db = SessionLocal()
    
    try:
        # 1. 创建游戏状态
        logger.info(f"Creating game state: {save_name}")
        game_state = GameState(
            save_name=save_name,
            current_year=GameConstants.STARTING_YEAR,
            current_month=GameConstants.STARTING_MONTH,
            current_week=GameConstants.STARTING_WEEK,
            turn_number=0,
            difficulty="normal",
            simulation_speed="weekly"
        )
        db.add(game_state)
        db.flush()  # 获取game_state.id
        
        game_id = game_state.id
        date_string = game_state.get_date_string()
        
        logger.info(f"✓ Game state created with ID: {game_id}")
        logger.info(f"  Starting date: {date_string}")
        
        # 2. 创建地区
        logger.info("\nCreating regions...")
        regions = create_initial_regions(game_id)
        db.add_all(regions)
        
        # 3. 提交到数据库
        db.commit()
        logger.info(f"\n✓ Successfully created {len(regions)} regions")
        
        # 4. 验证数据（在提交前收集数据）
        logger.info("\n" + "=" * 80)
        logger.info("World Summary:")
        logger.info("=" * 80)
        
        total_population = sum(r.population for r in regions)
        total_gdp = sum(r.get_total_gdp() for r in regions)
        total_market = sum(r.get_addressable_market_size() for r in regions)
        
        logger.info(f"Total World Population: {total_population:,}")
        logger.info(f"Total World GDP: ${total_gdp:,.0f}")
        logger.info(f"Total Addressable Market: {total_market:,} vehicles/year")
        
        logger.info("\nRegion Details:")
        for region in regions:
            logger.info(
                f"  [{region.code}] {region.name:20s} | "
                f"Pop: {region.population:>12,} | "
                f"GDP/cap: ${region.gdp_per_capita:>8,.0f} | "
                f"Growth: {region.gdp_growth_rate*100:>5.1f}% | "
                f"Market: {region.get_addressable_market_size():>9,}"
            )
        
        elapsed = (time.time() - start_time) * 1000
        logger.info("\n" + "=" * 80)
        logger.info(f"✓ World initialization completed in {elapsed:.2f}ms")
        logger.info("=" * 80)
        
        # 返回字典而不是对象，避免Session关闭后访问问题
        return {
            "game_id": game_id,
            "save_name": save_name,
            "date_string": date_string,
            "total_population": total_population,
            "total_gdp": total_gdp,
            "total_market": total_market,
            "region_count": len(regions)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize world: {e}", exc_info=True)
        raise
    finally:
        db.close()


def main():
    """主函数"""
    # 设置日志
    setup_logging()
    
    logger.info("Initializing database schema...")
    init_db()
    logger.info("✓ Database schema initialized\n")
    
    # 初始化世界
    result = initialize_world(save_name="Initial_1950")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Initialization Complete!")
    logger.info("=" * 80)
    logger.info(f"Game ID: {result['game_id']}")
    logger.info(f"Save Name: {result['save_name']}")
    logger.info(f"Start Date: {result['date_string']}")
    logger.info(f"Regions Created: {result['region_count']}")
    logger.info(f"Database: {project_root / 'data' / 'automogul.db'}")
    logger.info("\nYou can now start the FastAPI server:")
    logger.info("  cd backend")
    logger.info("  uvicorn main:app --reload")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

