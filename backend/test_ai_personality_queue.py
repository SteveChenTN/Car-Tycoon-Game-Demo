import json

import pytest

from backend.core.ai.ai_strategy import (
    AI_CEO,
    AIDecision,
    AIDecisionQueueManager,
    CEOPersonality,
    CompanySituation,
    calculate_decision_delay,
)
from backend.models import (
    AIDecisionQueue,
    Company,
    GameState,
    MarketingCampaign,
    Region,
    TechNode,
)


def make_region(db, game_id: int, code: str = "NAM") -> Region:
    region = Region(
        game_id=game_id,
        code=code,
        name=f"Region {code}",
        population=100_000_000,
        gdp_per_capita=20_000,
        gdp_growth_rate=0.04,
        purchasing_power_index=1.0,
        inflation_rate=0.03,
        unemployment_rate=0.05,
        car_ownership_rate=300.0,
        avg_vehicle_age=10.0,
        annual_sales_potential=1_000_000,
        infrastructure_quality=0.8,
        road_quality=0.8,
        fuel_price=0.4,
        electricity_price=0.1,
        import_tariff_rate=0.02,
        emission_standard="NONE",
        safety_standard="BASIC",
        corporate_tax_rate=0.25,
        ev_subsidy_rate=0.05,
        steel_availability=0.9,
        aluminum_availability=0.8,
        rare_earth_availability=0.7,
        labor_cost_index=1.0,
        skilled_labor_availability=0.8,
    )
    db.add(region)
    db.flush()
    return region


def make_ai_company(
    db,
    game_id: int,
    name: str,
    strategy: str = "NICHE",
    cash: float = 50_000_000,
    total_assets: float = 50_000_000,
    total_employees: int = 500,
) -> Company:
    company = Company(
        game_id=game_id,
        name=name,
        short_code=name[:3].upper(),
        is_player=False,
        is_ai=True,
        founded_year=1990,
        founded_turn=0,
        headquarters_region="NAM",
        cash=cash,
        total_assets=total_assets,
        total_employees=total_employees,
        ai_strategy=strategy,
    )
    db.add(company)
    db.flush()
    return company


def make_tech(
    db,
    game_id: int,
    code: str,
    min_year: int,
    base_time: int = 8,
    difficulty: float = 1.0,
    prereqs=None,
    features=None,
) -> TechNode:
    tech = TechNode(
        game_id=game_id,
        tech_code=code,
        name=code.replace("_", " ").title(),
        category="ENGINE",
        description=code,
        prerequisite_techs=json.dumps(prereqs or []),
        min_year=min_year,
        min_tech_level=1,
        base_research_cost=10.0,
        base_research_time=base_time,
        difficulty_rating=difficulty,
        unlocks_parts="[]",
        unlocks_features=json.dumps(features or []),
        stat_modifiers="{}",
    )
    db.add(tech)
    db.flush()
    return tech


def test_ai_personality_defaults_include_foresight(isolated_db_session):
    company = isolated_db_session.query(Company).first()
    company.ai_personality_traits = '{"aggression": 66}'

    traits = company.get_ai_personality()

    assert traits["aggression"] == 66
    assert traits["foresight"] == 50

    with pytest.raises(ValueError):
        CEOPersonality(
            aggression=50,
            innovation=50,
            risk_tolerance=50,
            loyalty=50,
            foresight=101,
        )


def test_decision_delay_ranges_follow_company_size():
    decision = AIDecision(
        decision_type="EXPANSION",
        action="ENTER_REGION",
        parameters={"region_id": 1},
        reasoning="test",
        priority=5,
    )
    small = Company(
        id=10,
        game_id=1,
        name="Small",
        short_code="SML",
        is_player=False,
        is_ai=True,
        founded_year=1990,
        founded_turn=0,
        headquarters_region="NAM",
        cash=10_000_000,
        total_assets=12_000_000,
        total_employees=200,
        ai_strategy="NICHE",
    )
    giant = Company(
        id=11,
        game_id=1,
        name="Giant",
        short_code="GNT",
        is_player=False,
        is_ai=True,
        founded_year=1990,
        founded_turn=0,
        headquarters_region="NAM",
        cash=50_000_000,
        total_assets=70_000_000,
        total_employees=5_000,
        ai_strategy="MULTINATIONAL",
    )

    assert 1 <= calculate_decision_delay(small, decision, current_turn=12) <= 2
    assert 8 <= calculate_decision_delay(giant, decision, current_turn=12) <= 16


def test_queued_decision_executes_only_when_due(isolated_db_session):
    db = isolated_db_session
    game = db.query(GameState).first()
    region = make_region(db, game.id)
    company = make_ai_company(db, game.id, "Queue AI", strategy="NICHE")

    decision = AIDecision(
        decision_type="MARKETING",
        action="LAUNCH_CAMPAIGN",
        parameters={
            "region_id": region.id,
            "target_bucket": "PRACTICAL",
            "focus": "BRAND_AWARENESS",
            "budget": 100_000,
            "duration_turns": 3,
        },
        reasoning="test campaign",
        priority=7,
    )
    manager = AIDecisionQueueManager(db)
    queued = manager.enqueue_decisions(company, [decision], current_turn=10)
    due_turn = queued[0].due_turn

    early = manager.process_due_decisions(game.id, due_turn - 1)

    assert early["executed_count"] == 0
    assert db.query(MarketingCampaign).count() == 0

    due = manager.process_due_decisions(game.id, due_turn)

    assert due["executed_count"] == 1
    assert db.query(MarketingCampaign).count() == 1
    assert db.query(AIDecisionQueue).first().status == "EXECUTED"


def test_foresight_changes_new_energy_timing(isolated_db_session):
    db = isolated_db_session
    game = db.query(GameState).first()
    game.current_year = 1994

    style = make_tech(db, game.id, "TECH_STYLE_REFRESH", min_year=1990, base_time=5)
    direct = make_tech(db, game.id, "TECH_DIRECT_INJECTION", min_year=1990, base_time=20)
    make_tech(
        db,
        game.id,
        "TECH_HYBRID_POWERTRAIN",
        min_year=2000,
        base_time=24,
        difficulty=3.0,
        prereqs=[direct.tech_code],
        features=["HYBRID_ELECTRIC_VEHICLE"],
    )
    high_company = make_ai_company(db, game.id, "High Foresight")
    low_company = make_ai_company(db, game.id, "Low Foresight")

    situation = CompanySituation(
        company_id=high_company.id,
        cash_balance=100_000_000,
        monthly_burn_rate=1_000_000,
        cash_runway_months=100,
        market_share_trend=0.0,
        profit_margin=0.1,
        brand_health=60,
        production_utilization=0.7,
        competitor_threats=[],
        market_opportunities=[],
    )

    high_decision = AI_CEO(
        db,
        high_company.id,
        CEOPersonality(50, 90, 50, 50, 90),
    )._make_rd_decisions(situation, game.id)[0]
    low_decision = AI_CEO(
        db,
        low_company.id,
        CEOPersonality(50, 90, 50, 50, 10),
    )._make_rd_decisions(situation, game.id)[0]

    assert high_decision.parameters["tech_code"] == "TECH_DIRECT_INJECTION"
    assert low_decision.parameters["tech_code"] == style.tech_code
