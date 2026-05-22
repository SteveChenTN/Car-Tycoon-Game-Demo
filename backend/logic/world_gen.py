"""
程序化世界生成器
根据难度、随机种子和玩家设置生成独特的游戏世界
"""
import random
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from backend.models import (
    GameState, GameConfig, Region, Company, 
    EventLog, TechNode, Regulation
)
from backend.config import GameConstants, EconomicConstants, MarketConstants

logger = logging.getLogger(__name__)


class WorldGenerator:
    """
    世界生成器
    
    职责：
    1. 生成地理区域（带随机化修正）
    2. 生成AI竞争对手（从原型池随机选择）
    3. 生成市场趋势（随机化消费者偏好）
    4. 初始化玩家公司
    """
    
    # 信用评级映射（数字到评级字符串）
    CREDIT_RATING_MAP = {
        (90, 100): "AAA",
        (80, 89): "AA",
        (70, 79): "A",
        (60, 69): "BBB",
        (50, 59): "BB",
        (40, 49): "B",
        (30, 39): "CCC",
        (20, 29): "CC",
        (10, 19): "C",
        (0, 9): "D"
    }
    
    @classmethod
    def _credit_rating_from_score(cls, score: float) -> str:
        """
        将数字信用评分转换为评级字符串
        
        Args:
            score: 信用评分 (0-100)
            
        Returns:
            评级字符串 (AAA, AA, A, BBB, BB, B, CCC, CC, C, D)
        """
        score = int(score)
        for (min_score, max_score), rating in cls.CREDIT_RATING_MAP.items():
            if min_score <= score <= max_score:
                return rating
        return "D"  # 默认最低评级
    
    # =============================================================================
    # AI 公司原型库（20个）
    # =============================================================================
    
    AI_ARCHETYPES = [
        {
            "name": "TechnoMotors",
            "strategy": "TECH_GIANT",
            "description": "高科技先驱，擅长研发",
            "cash_multiplier": 1.5,
            "tech_level_bonus": 15,
            "rd_focus": 0.9,
            "marketing_focus": 0.5,
            "production_focus": 0.6
        },
        {
            "name": "ValueAuto",
            "strategy": "COST_CUTTER",
            "description": "成本杀手，薄利多销",
            "cash_multiplier": 1.2,
            "tech_level_bonus": 0,
            "rd_focus": 0.3,
            "marketing_focus": 0.7,
            "production_focus": 0.9
        },
        {
            "name": "LuxeDrive",
            "strategy": "LUXURY_BRAND",
            "description": "奢华品牌，高端市场",
            "cash_multiplier": 2.0,
            "tech_level_bonus": 10,
            "rd_focus": 0.7,
            "marketing_focus": 0.9,
            "production_focus": 0.4
        },
        {
            "name": "SpeedDemon Motors",
            "strategy": "PERFORMANCE",
            "description": "性能狂魔，运动路线",
            "cash_multiplier": 1.3,
            "tech_level_bonus": 8,
            "rd_focus": 0.8,
            "marketing_focus": 0.6,
            "production_focus": 0.5
        },
        {
            "name": "EcoWheels",
            "strategy": "EFFICIENCY",
            "description": "环保先锋，节能专家",
            "cash_multiplier": 1.1,
            "tech_level_bonus": 12,
            "rd_focus": 0.8,
            "marketing_focus": 0.6,
            "production_focus": 0.5
        },
        {
            "name": "MassMarket Inc",
            "strategy": "VOLUME",
            "description": "大众市场，规模优先",
            "cash_multiplier": 1.8,
            "tech_level_bonus": 0,
            "rd_focus": 0.4,
            "marketing_focus": 0.8,
            "production_focus": 0.9
        },
        {
            "name": "Heritage Motors",
            "strategy": "TRADITIONAL",
            "description": "老牌车企，稳健经营",
            "cash_multiplier": 1.6,
            "tech_level_bonus": 5,
            "rd_focus": 0.5,
            "marketing_focus": 0.7,
            "production_focus": 0.7
        },
        {
            "name": "AgileAuto",
            "strategy": "AGILE",
            "description": "灵活应变，快速迭代",
            "cash_multiplier": 1.0,
            "tech_level_bonus": 10,
            "rd_focus": 0.7,
            "marketing_focus": 0.6,
            "production_focus": 0.6
        },
        {
            "name": "SafetyFirst",
            "strategy": "SAFETY_FOCUS",
            "description": "安全至上，可靠性高",
            "cash_multiplier": 1.4,
            "tech_level_bonus": 8,
            "rd_focus": 0.7,
            "marketing_focus": 0.6,
            "production_focus": 0.7
        },
        {
            "name": "DesignHouse",
            "strategy": "DESIGN_FOCUS",
            "description": "设计驱动，美学优先",
            "cash_multiplier": 1.3,
            "tech_level_bonus": 5,
            "rd_focus": 0.6,
            "marketing_focus": 0.9,
            "production_focus": 0.5
        },
        {
            "name": "GlobalGiant",
            "strategy": "MULTINATIONAL",
            "description": "跨国巨头，全球布局",
            "cash_multiplier": 2.5,
            "tech_level_bonus": 10,
            "rd_focus": 0.6,
            "marketing_focus": 0.8,
            "production_focus": 0.8
        },
        {
            "name": "NicheSpecialist",
            "strategy": "NICHE",
            "description": "细分专家，小而美",
            "cash_multiplier": 0.8,
            "tech_level_bonus": 15,
            "rd_focus": 0.9,
            "marketing_focus": 0.4,
            "production_focus": 0.3
        },
        {
            "name": "ElectricFuture",
            "strategy": "EV_PIONEER",
            "description": "电动先锋，未来导向",
            "cash_multiplier": 1.2,
            "tech_level_bonus": 20,
            "rd_focus": 0.95,
            "marketing_focus": 0.7,
            "production_focus": 0.5
        },
        {
            "name": "TruckKing",
            "strategy": "COMMERCIAL",
            "description": "商用之王，货车专家",
            "cash_multiplier": 1.5,
            "tech_level_bonus": 3,
            "rd_focus": 0.4,
            "marketing_focus": 0.6,
            "production_focus": 0.9
        },
        {
            "name": "SportsCar Co",
            "strategy": "EXOTIC",
            "description": "超跑制造，限量精品",
            "cash_multiplier": 1.0,
            "tech_level_bonus": 12,
            "rd_focus": 0.8,
            "marketing_focus": 0.5,
            "production_focus": 0.3
        },
        {
            "name": "PeoplesCar",
            "strategy": "AFFORDABLE",
            "description": "人民之车，实惠为先",
            "cash_multiplier": 1.3,
            "tech_level_bonus": -5,
            "rd_focus": 0.3,
            "marketing_focus": 0.8,
            "production_focus": 0.9
        },
        {
            "name": "OffRoad Masters",
            "strategy": "OFF_ROAD",
            "description": "越野专家，SUV之王",
            "cash_multiplier": 1.4,
            "tech_level_bonus": 5,
            "rd_focus": 0.6,
            "marketing_focus": 0.7,
            "production_focus": 0.7
        },
        {
            "name": "FamilyFirst",
            "strategy": "FAMILY",
            "description": "家庭友好，实用主义",
            "cash_multiplier": 1.5,
            "tech_level_bonus": 3,
            "rd_focus": 0.5,
            "marketing_focus": 0.7,
            "production_focus": 0.8
        },
        {
            "name": "InnovateMotors",
            "strategy": "INNOVATOR",
            "description": "创新驱动，概念先行",
            "cash_multiplier": 1.1,
            "tech_level_bonus": 18,
            "rd_focus": 0.95,
            "marketing_focus": 0.6,
            "production_focus": 0.4
        },
        {
            "name": "ReliableWheels",
            "strategy": "RELIABILITY",
            "description": "可靠耐用，口碑至上",
            "cash_multiplier": 1.6,
            "tech_level_bonus": 7,
            "rd_focus": 0.6,
            "marketing_focus": 0.7,
            "production_focus": 0.8
        },
    ]
    
    def __init__(
        self,
        db: Session,
        difficulty: str = "normal",
        random_seed: Optional[int] = None,
        starting_year: int = 1946,
        save_name: Optional[str] = None
    ):
        """
        初始化世界生成器
        
        Args:
            db: 数据库会话
            difficulty: 难度 (easy/normal/hard/brutal)
            random_seed: 随机种子（None=使用当前时间）
            starting_year: 起始年份
            save_name: 存档名称
        """
        self.db = db
        self.difficulty = difficulty
        self.starting_year = starting_year
        self.save_name = save_name or f"Game_{starting_year}"
        
        # 设置随机种子（确保可重现）
        if random_seed is None:
            random_seed = int(datetime.now().timestamp())
        
        self.random_seed = random_seed
        random.seed(random_seed)
        
        logger.info(f"世界生成器初始化: difficulty={difficulty}, seed={random_seed}")
    
    def generate(
        self,
        player_company_name: str = "Player Motors",
        player_starting_capital: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        执行完整的世界生成流程
        
        Args:
            player_company_name: 玩家公司名称
            player_starting_capital: 玩家起始资金（None=根据难度自动）
            
        Returns:
            生成结果
        """
        try:
            logger.info("=" * 80)
            logger.info(f"开始生成游戏世界 (种子: {self.random_seed})")
            logger.info("=" * 80)
            
            # 1. 创建游戏状态
            game_state = self._create_game_state()
            self.db.add(game_state)
            self.db.commit()
            self.db.refresh(game_state)
            
            logger.info(f"✓ 游戏状态创建完成 (game_id={game_state.id})")
            
            # 2. 创建游戏配置
            game_config = self._create_game_config(game_state.id)
            self.db.add(game_config)
            
            # 3. 生成地理区域
            regions = self._generate_regions(game_state.id)
            self.db.add_all(regions)
            logger.info(f"✓ 生成 {len(regions)} 个地理区域")
            
            # 4. 创建玩家公司
            player = self._create_player_company(
                game_state.id,
                player_company_name,
                player_starting_capital
            )
            self.db.add(player)
            logger.info(f"✓ 玩家公司创建: {player.name}")
            
            # 5. 生成AI竞争对手
            ai_companies = self._generate_ai_companies(game_state.id)
            self.db.add_all(ai_companies)
            logger.info(f"✓ 生成 {len(ai_companies)} 个AI竞争对手")
            
            # 6. 生成初始技术树
            tech_nodes = self._generate_tech_tree(game_state.id)
            self.db.add_all(tech_nodes)
            logger.info(f"✓ 生成 {len(tech_nodes)} 个技术节点")
            
            # 7. 创建初始事件日志
            welcome_log = EventLog(
                game_id=game_state.id,
                turn_number=1,
                event_type="GAME_START",
                severity="INFO",
                message=f"欢迎来到 {player_company_name}！起始年份: {self.starting_year}",
                extra_data={
                    "difficulty": self.difficulty,
                    "seed": self.random_seed,
                    "player_capital": player.cash
                }
            )
            self.db.add(welcome_log)
            
            # 提交所有更改
            self.db.commit()
            
            logger.info("=" * 80)
            logger.info("✓ 世界生成完成！")
            logger.info("=" * 80)
            
            return {
                "success": True,
                "game_id": game_state.id,
                "seed": self.random_seed,
                "difficulty": self.difficulty,
                "starting_year": self.starting_year,
                "player_company": player.name,
                "regions_count": len(regions),
                "ai_companies_count": len(ai_companies),
                "tech_nodes_count": len(tech_nodes)
            }
            
        except Exception as e:
            logger.error(f"世界生成失败: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_game_state(self) -> GameState:
        """创建游戏状态"""
        return GameState(
            save_name=self.save_name,
            current_year=self.starting_year,
            current_month=GameConstants.STARTING_MONTH,
            current_week=GameConstants.STARTING_WEEK,
            turn_number=1,
            difficulty=self.difficulty,
            random_seed=self.random_seed
        )
    
    def _create_game_config(self, game_id: int) -> GameConfig:
        """创建游戏配置"""
        return GameConfig(
            game_id=game_id,
            mode="campaign",
            start_year=self.starting_year,
            end_year=self.starting_year + 50,  # 50年战役
            difficulty=self.difficulty
        )
    
    def _generate_regions(self, game_id: int) -> List[Region]:
        """
        生成地理区域
        应用随机化修正（±10% GDP等）
        """
        regions = []
        
        # 基础区域配置（来自设计文档）
        base_regions_config = [
            {
                "code": "NAM",
                "name": "North America",
                "population": 200_000_000,
                "gdp_per_capita": 15000.0,
                "car_ownership_rate": 350.0,
                "pref_size_large": 0.45,
                "fuel_price": 0.30,
            },
            {
                "code": "EUR",
                "name": "Europe",
                "population": 350_000_000,
                "gdp_per_capita": 8000.0,
                "car_ownership_rate": 250.0,
                "pref_size_small": 0.50,
                "fuel_price": 0.50,
            },
            {
                "code": "ASI",
                "name": "Asia-Pacific",
                "population": 800_000_000,
                "gdp_per_capita": 2000.0,
                "car_ownership_rate": 50.0,
                "pref_size_small": 0.60,
                "fuel_price": 0.40,
            },
            {
                "code": "LAM",
                "name": "Latin America",
                "population": 150_000_000,
                "gdp_per_capita": 3000.0,
                "car_ownership_rate": 120.0,
                "pref_size_medium": 0.55,
                "fuel_price": 0.35,
            },
            {
                "code": "MEA",
                "name": "Middle East & Africa",
                "population": 200_000_000,
                "gdp_per_capita": 2500.0,
                "car_ownership_rate": 80.0,
                "pref_size_medium": 0.50,
                "fuel_price": 0.20,
            },
        ]
        
        for config in base_regions_config:
            # 应用随机化修正（±10%）
            gdp_modifier = random.uniform(0.9, 1.1)
            demand_modifier = random.uniform(0.9, 1.1)
            
            region = Region(
                game_id=game_id,
                code=config["code"],
                name=config["name"],
                population=int(config["population"] * random.uniform(0.95, 1.05)),
                gdp_per_capita=config["gdp_per_capita"] * gdp_modifier,
                gdp_growth_rate=random.uniform(0.02, 0.05),
                purchasing_power_index=random.uniform(0.8, 1.2),
                inflation_rate=random.uniform(0.02, 0.04),
                unemployment_rate=random.uniform(0.03, 0.08),
                
                car_ownership_rate=config["car_ownership_rate"] * demand_modifier,
                avg_vehicle_age=random.uniform(8.0, 15.0),
                annual_sales_potential=int(
                    config["population"] * config["car_ownership_rate"] / 1000 * 0.08
                ),
                
                infrastructure_quality=random.uniform(0.6, 0.9),
                road_quality=random.uniform(0.6, 0.9),
                fuel_price=config["fuel_price"] * random.uniform(0.9, 1.1),
                electricity_price=random.uniform(0.08, 0.15),
                
                import_tariff_rate=random.uniform(0.0, 0.10),
                emission_standard="NONE",
                safety_standard="BASIC",
                corporate_tax_rate=random.uniform(0.20, 0.40),
                ev_subsidy_rate=0.0,
                
                steel_availability=random.uniform(0.7, 1.0),
                aluminum_availability=random.uniform(0.6, 1.0),
                rare_earth_availability=random.uniform(0.3, 0.8),
                labor_cost_index=random.uniform(0.8, 1.5),
                skilled_labor_availability=random.uniform(0.6, 0.9),
                
                # 偏好随机化（±15%）
                pref_size_small=max(0.1, config.get("pref_size_small", 0.3) * random.uniform(0.85, 1.15)),
                pref_size_medium=max(0.1, config.get("pref_size_medium", 0.4) * random.uniform(0.85, 1.15)),
                pref_size_large=max(0.1, config.get("pref_size_large", 0.3) * random.uniform(0.85, 1.15)),
                
                pref_body_sedan=0.35,
                pref_body_suv=0.30,
                pref_body_hatchback=0.20,
                pref_body_coupe=0.10,
                pref_body_wagon=0.05,
                
                pref_fuel_efficiency_weight=random.uniform(0.3, 0.7),
                pref_power_weight=random.uniform(0.3, 0.7),
            )
            
            regions.append(region)
        
        return regions
    
    def _create_player_company(
        self,
        game_id: int,
        name: str,
        starting_capital: Optional[float]
    ) -> Company:
        """创建玩家公司"""
        
        # 根据难度确定起始资金
        if starting_capital is None:
            capital_map = {
                "easy": 50_000_000.0,
                "normal": 30_000_000.0,
                "hard": 15_000_000.0,
                "brutal": 10_000_000.0
            }
            starting_capital = capital_map.get(self.difficulty, 30_000_000.0)
        
        # 生成公司简称代码（取前3个字符大写）
        short_code = name[:3].upper().replace(" ", "") if len(name) >= 3 else name.upper()[:3]
        
        return Company(
            game_id=game_id,
            name=name,
            short_code=short_code,  # 添加必需字段
            is_player=True,
            is_ai=False,  # 玩家不是AI
            is_bankrupt=False,
            founded_year=self.starting_year,
            founded_turn=1,  # 添加必需字段
            cash=starting_capital,
            credit_rating=self._credit_rating_from_score(70.0),  # 转换为 "A"
            prestige_score=0.0,
            tech_level=5,  # 修复：tech_level 必须是 1-10 的整数
            headquarters_region="NAM"
        )
    
    def _generate_ai_companies(self, game_id: int) -> List[Company]:
        """
        生成AI竞争对手
        根据难度从原型池中随机选择
        """
        
        # 根据难度确定AI数量
        ai_count_map = {
            "easy": 3,
            "normal": 5,
            "hard": 7,
            "brutal": 10
        }
        ai_count = ai_count_map.get(self.difficulty, 5)
        
        # 随机选择原型（不重复）
        selected_archetypes = random.sample(self.AI_ARCHETYPES, ai_count)
        
        ai_companies = []
        base_capital = 20_000_000.0
        
        for archetype in selected_archetypes:
            credit_score = random.uniform(60.0, 80.0)
            founded_year = random.randint(self.starting_year - 20, self.starting_year)
            short_code = archetype["name"][:3].upper().replace(" ", "") if len(archetype["name"]) >= 3 else archetype["name"].upper()[:3]
            
            # 计算 tech_level（必须在 1-10 范围内）
            # tech_level_bonus 范围通常是 -5 到 20，我们将其映射到 1-10
            base_tech_level = 5  # 基础技术等级（中等水平）
            # 将 tech_level_bonus（-5 到 20）映射到等级调整（-2 到 +3）
            tech_bonus_adjustment = max(-2, min(3, int(archetype.get("tech_level_bonus", 0) / 5)))
            tech_level = max(1, min(10, base_tech_level + tech_bonus_adjustment + random.randint(-1, 1)))
            
            company = Company(
                game_id=game_id,
                name=archetype["name"],
                short_code=short_code,  # 添加必需字段
                is_player=False,
                is_ai=True,  # AI公司
                is_bankrupt=False,
                founded_year=founded_year,
                founded_turn=1,  # 添加必需字段（简化：都设为1）
                cash=base_capital * archetype["cash_multiplier"] * random.uniform(0.8, 1.2),
                credit_rating=self._credit_rating_from_score(credit_score),
                prestige_score=random.uniform(0.0, 50.0),
                tech_level=tech_level,  # 修复：使用计算后的 1-10 整数
                headquarters_region=random.choice(["NAM", "EUR", "ASI", "LAM", "MEA"]),
                ai_strategy=archetype["strategy"]
            )
            ai_companies.append(company)
        
        return ai_companies
    
    def _generate_tech_tree(self, game_id: int) -> List[TechNode]:
        """
        生成初始技术树
        简化版：创建几个基础节点
        """
        tech_nodes = []
        
        base_techs = [
            {
                "code": "PLATFORM_BASIC",
                "name": "基础平台技术",
                "category": "PLATFORM",
                "description": "车身基础结构",
                "cost": 1_000_000.0,
                "research_weeks": 52,
                "unlocked": True
            },
            {
                "code": "ENGINE_INLINE4",
                "name": "直列四缸引擎",
                "category": "ENGINE",
                "description": "基础动力单元",
                "cost": 500_000.0,
                "research_weeks": 26,
                "unlocked": True
            },
            {
                "code": "ENGINE_V6",
                "name": "V6引擎",
                "category": "ENGINE",
                "description": "中等动力单元",
                "cost": 2_000_000.0,
                "research_weeks": 52,
                "unlocked": False
            },
            {
                "code": "SAFETY_BASIC",
                "name": "基础安全技术",
                "category": "SAFETY",
                "description": "安全带、刹车",
                "cost": 300_000.0,
                "research_weeks": 20,
                "unlocked": True
            },
        ]
        
        for tech in base_techs:
            node = TechNode(
                game_id=game_id,
                tech_code=tech["code"],
                name=tech["name"],
                category=tech["category"],
                description=tech["description"],
                base_research_cost=tech["cost"],  # 修复：使用 base_research_cost
                base_research_time=tech["research_weeks"],  # 修复：使用 base_research_time
                min_year=self.starting_year,
                min_tech_level=1,  # 添加必需字段
                difficulty_rating=1.0,  # 添加默认难度
                prerequisite_techs="[]",  # 添加默认前置技术
                unlocks_parts="[]",  # 添加默认解锁零件
                unlocks_features="[]",  # 添加默认解锁特性
                stat_modifiers="{}"  # 添加默认属性修正
            )
            tech_nodes.append(node)
        
        return tech_nodes


__all__ = ["WorldGenerator"]

