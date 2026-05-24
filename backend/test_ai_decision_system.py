import pytest

from backend.core.ai import ai_strategy
from backend.core.ai.ai_strategy import (
    AI_CEO,
    CEOPersonality,
    get_or_create_company_personality,
)
from backend.core.management.game_loop import GameLoopManager
from backend.models.company import Company
from backend.models.engineering import CarTrim, Chassis, ChassisSourceType, Engine
from backend.models.game_manager import EventLog
from backend.models.history import FinancialHistory
from backend.models.market import BrandPerception, MarketingCampaign
from backend.models.production import Factory
from backend.models.region import Region
from backend.models.technology import CompanyTechnology, TechNode


def _create_region(db, game_id: int, code: str, potential: int) -> Region:
    region = Region(
        game_id=game_id,
        code=code,
        name=f"{code} Region",
        population=50_000_000,
        gdp_per_capita=30_000.0,
        gdp_growth_rate=0.03,
        purchasing_power_index=1.0,
        inflation_rate=0.03,
        unemployment_rate=0.05,
        car_ownership_rate=500.0,
        avg_vehicle_age=8.0,
        annual_sales_potential=potential,
        infrastructure_quality=0.8,
        road_quality=0.8,
        fuel_price=1.0,
        electricity_price=0.2,
        import_tariff_rate=0.0,
        emission_standard="NONE",
        safety_standard="BASIC",
        corporate_tax_rate=0.21,
        ev_subsidy_rate=0.0,
        steel_availability=0.8,
        aluminum_availability=0.8,
        rare_earth_availability=0.5,
        labor_cost_index=1.0,
        skilled_labor_availability=0.8,
    )
    db.add(region)
    db.flush()
    return region


def _create_ai_company(db, game_id: int) -> Company:
    company = Company(
        game_id=game_id,
        name="Vector Auto",
        short_code="VEC",
        is_player=False,
        is_ai=True,
        founded_year=1946,
        founded_turn=0,
        headquarters_region="NAM",
        cash=100_000_000.0,
        tech_level=5,
        ai_strategy="TECH_GIANT",
    )
    company.set_ai_personality({
        "aggression": 90,
        "innovation": 85,
        "risk_tolerance": 90,
        "loyalty": 50,
    })
    db.add(company)
    db.flush()
    return company


def _create_active_trim(db, game_id: int, company_id: int) -> CarTrim:
    engine = Engine(
        game_id=game_id,
        company_id=company_id,
        name="Vector I4",
        code="VEC-I4",
        bore_mm=86.0,
        stroke_mm=86.0,
        cylinder_count=4,
        configuration="INLINE",
        compression_ratio=10.0,
        induction_type="NA",
        boost_pressure_bar=0.0,
        material="ALUMINUM",
        valvetrain="DOHC",
        fuel_type="GASOLINE",
        tech_level=5,
        displacement_cc=1998,
        max_horsepower=150,
        max_torque_nm=200,
        redline_rpm=6500,
        weight_kg=150.0,
        length_mm=500.0,
        width_mm=500.0,
        height_mm=500.0,
        thermal_load=0.5,
        specific_output=75.0,
        reliability_base_score=75.0,
        fuel_efficiency_rating=0.7,
        bsfc_g_kwh=260.0,
        development_cost=0.0,
        manufacturing_cost=2_500.0,
        is_proprietary=True,
    )
    db.add(engine)
    db.flush()

    chassis = Chassis(
        game_id=game_id,
        company_id=company_id,
        name="Vector Platform",
        code="VEC-C",
        wheelbase_mm=2600,
        track_front_mm=1500,
        track_rear_mm=1500,
        layout="FF",
        engine_bay_length_mm=700.0,
        engine_bay_width_mm=700.0,
        engine_bay_height_mm=650.0,
        max_cooling_capacity_kw=160.0,
        material="STEEL",
        rigidity_rating=60.0,
        weight_kg=800.0,
        crash_test_rating=60.0,
        tech_level=5,
        source_type=ChassisSourceType.MODULAR_PLATFORM,
        supported_body_styles='["SEDAN"]',
        base_tooling_cost=50.0,
        tooling_amortized=0.0,
        economies_of_scale_factor=1.0,
        development_cost=0.0,
        manufacturing_cost=8_000.0,
    )
    db.add(chassis)
    db.flush()

    trim = CarTrim(
        game_id=game_id,
        company_id=company_id,
        name="Vector Sedan LX",
        model_name="Vector Sedan",
        trim_code="VEC-LX",
        engine_id=engine.id,
        chassis_id=chassis.id,
        body_style="SEDAN",
        seating_capacity=5,
        cargo_volume_liters=450,
        body_weight_kg=450.0,
        drag_coefficient=0.31,
        frontal_area_sqm=2.3,
        total_weight_kg=1_400.0,
        power_to_weight_ratio=0.11,
        zero_to_hundred_kph_sec=9.5,
        top_speed_kph=190.0,
        quarter_mile_sec=17.0,
        braking_100_0_meters=42.0,
        lateral_g_force=0.82,
        fuel_economy_l_100km=7.5,
        final_reliability_score=78.0,
        segment="MIDSIZE",
        manufacturing_cost=12_000.0,
        msrp=30_000.0,
        compatibility_status="COMPATIBLE",
        is_in_production=True,
        production_start_turn=0,
    )
    db.add(trim)
    db.flush()
    return trim


def _seed_ai_context(db, game_id: int, company: Company, region: Region) -> None:
    db.add(Factory(
        game_id=game_id,
        company_id=company.id,
        name="Vector NAM Plant",
        factory_type="ASSEMBLY",
        level=1,
        capacity_units_per_month=20_000,
        current_utilization_rate=0.96,
        region_id=region.id,
        efficiency_score=80.0,
        labor_cost_per_unit=150.0,
        overhead_cost_per_month=250_000.0,
        tech_level=5,
        is_operational=True,
        construction_completed_turn=0,
    ))

    db.add(BrandPerception(
        game_id=game_id,
        company_id=company.id,
        region_id=region.id,
        reliability_score=60.0,
        sportiness_score=60.0,
        luxury_score=45.0,
        eco_friendly_score=50.0,
        innovation_score=55.0,
        value_for_money_score=50.0,
        overall_awareness=0.4,
        fanbase_count=5_000,
    ))

    db.add_all([
        FinancialHistory(
            game_id=game_id,
            company_id=company.id,
            turn_number=2,
            year=1946,
            month=1,
            revenue_vehicles=10_000_000.0,
            cost_manufacturing=5_000_000.0,
            cost_admin=1_000_000.0,
            net_income=2_000_000.0,
            cash_end=company.cash,
            units_sold=900,
            market_share_global=0.10,
        ),
        FinancialHistory(
            game_id=game_id,
            company_id=company.id,
            turn_number=3,
            year=1946,
            month=1,
            revenue_vehicles=8_000_000.0,
            cost_manufacturing=5_000_000.0,
            cost_admin=1_000_000.0,
            net_income=1_000_000.0,
            cash_end=company.cash,
            units_sold=600,
            market_share_global=0.04,
        ),
    ])

    db.add(TechNode(
        game_id=game_id,
        tech_code="AI_TURBO_V1",
        name="AI Turbocharging",
        category="ENGINE",
        description="Forced induction research",
        prerequisite_techs="[]",
        min_year=1940,
        min_tech_level=1,
        base_research_cost=1_000_000.0,
        base_research_time=4,
        difficulty_rating=1.0,
        unlocks_parts="[]",
        unlocks_features="[]",
        stat_modifiers="{}",
    ))
    db.commit()


@pytest.mark.db
def test_missing_ai_personality_is_derived_and_persisted(isolated_db_session):
    db = isolated_db_session
    game_id = db.query(Company).filter(Company.is_player == True).first().game_id
    company = Company(
        game_id=game_id,
        name="Legacy AI",
        short_code="LEG",
        is_player=False,
        is_ai=True,
        founded_year=1946,
        founded_turn=0,
        headquarters_region="NAM",
        ai_strategy="TECH_GIANT",
    )
    db.add(company)
    db.commit()

    personality = get_or_create_company_personality(company)

    assert personality.innovation == 90
    assert company.get_ai_personality()["innovation"] == 90


@pytest.mark.db
def test_ai_decisions_use_real_metrics_without_random(monkeypatch, isolated_db_session):
    db = isolated_db_session
    game_id = db.query(Company).filter(Company.is_player == True).first().game_id
    region = _create_region(db, game_id, "NAM", 1_000_000)
    company = _create_ai_company(db, game_id)
    _seed_ai_context(db, game_id, company, region)

    def fail_random(*_args, **_kwargs):
        raise AssertionError("AI turn assessment should not call random")

    monkeypatch.setattr(ai_strategy.random, "uniform", fail_random)
    monkeypatch.setattr(ai_strategy.random, "random", fail_random)
    monkeypatch.setattr(ai_strategy.random, "randint", fail_random)

    decisions = AI_CEO(
        db,
        company.id,
        CEOPersonality(aggression=90, innovation=85, risk_tolerance=90, loyalty=50, foresight=70),
    ).make_turn_decisions(game_id, current_turn=3)

    assert {decision.decision_type for decision in decisions} >= {"MARKETING", "EXPANSION", "RD", "PRICING"}


@pytest.mark.db
def test_ai_phase_executes_actions_and_logs_events(isolated_db_session):
    db = isolated_db_session
    game_id = db.query(Company).filter(Company.is_player == True).first().game_id
    region_nam = _create_region(db, game_id, "NAM", 1_000_000)
    _create_region(db, game_id, "EUR", 2_000_000)
    company = _create_ai_company(db, game_id)
    trim = _create_active_trim(db, game_id, company.id)
    _seed_ai_context(db, game_id, company, region_nam)

    initial_factory_count = db.query(Factory).filter(Factory.company_id == company.id).count()
    initial_msrp = trim.msrp

    result = GameLoopManager(db)._phase_ai_decisions(game_id, current_turn=3)

    db.refresh(trim)
    db.refresh(company)

    assert result["ai_companies"] == 1
    assert db.query(MarketingCampaign).filter(MarketingCampaign.company_id == company.id).count() == 1
    assert trim.msrp < initial_msrp
    assert db.query(CompanyTechnology).filter(
        CompanyTechnology.company_id == company.id,
        CompanyTechnology.status == "RESEARCHING",
    ).count() == 1
    assert db.query(Factory).filter(Factory.company_id == company.id).count() > initial_factory_count
    assert db.query(EventLog).filter(
        EventLog.game_id == game_id,
        EventLog.event_type == "AI_ACTION",
        EventLog.related_company_id == company.id,
    ).count() >= 4
