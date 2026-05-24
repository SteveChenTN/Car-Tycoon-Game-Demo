import random

import pytest

from backend.core.economics.market_simulation import MarketSimulator
from backend.models.company import Company
from backend.models.engineering import Chassis, Engine, CarTrim
from backend.models.game_state import GameState
from backend.models.history import MarketDemandHistory, SalesHistory
from backend.models.inventory import DealershipInventory
from backend.models.market import ConsumerBucket, DistributionNetwork
from backend.models.region import Region


pytestmark = [pytest.mark.integration, pytest.mark.db]


def _create_region(db, game_id: int) -> Region:
    region = Region(
        game_id=game_id,
        code=f"TST{game_id}",
        name="Test Region",
        population=1_000_000,
        gdp_per_capita=30_000.0,
        gdp_growth_rate=0.02,
        purchasing_power_index=1.0,
        inflation_rate=0.03,
        unemployment_rate=0.05,
        car_ownership_rate=500.0,
        avg_vehicle_age=7.0,
        annual_sales_potential=50_000,
        infrastructure_quality=0.8,
        road_quality=0.8,
        fuel_price=1.0,
        electricity_price=0.1,
        import_tariff_rate=0.0,
        emission_standard="NONE",
        safety_standard="BASIC",
        corporate_tax_rate=0.25,
        ev_subsidy_rate=0.0,
        steel_availability=1.0,
        aluminum_availability=1.0,
        rare_earth_availability=1.0,
        labor_cost_index=1.0,
        skilled_labor_availability=1.0,
    )
    db.add(region)
    db.flush()
    return region


def _create_trim(db, game_id: int, company_id: int) -> CarTrim:
    engine = Engine(
        game_id=game_id,
        company_id=company_id,
        name="Market Test I4",
        code=f"MT-I4-{game_id}",
        bore_mm=82.0,
        stroke_mm=86.0,
        cylinder_count=4,
        configuration="INLINE",
        compression_ratio=10.0,
        induction_type="NA",
        boost_pressure_bar=0.0,
        material="CAST_IRON",
        valvetrain="SOHC",
        fuel_type="GASOLINE",
        tech_level=1,
        displacement_cc=1815,
        max_horsepower=100,
        max_torque_nm=150,
        redline_rpm=5500,
        weight_kg=150.0,
        length_mm=600.0,
        width_mm=500.0,
        height_mm=550.0,
        thermal_load=0.5,
        specific_output=55.0,
        reliability_base_score=70.0,
        fuel_efficiency_rating=0.7,
        bsfc_g_kwh=260.0,
        manufacturing_cost=1200.0,
    )
    db.add(engine)
    db.flush()

    chassis = Chassis(
        game_id=game_id,
        company_id=company_id,
        name="Market Test Platform",
        code=f"MT-CH-{game_id}",
        wheelbase_mm=2600,
        track_front_mm=1500,
        track_rear_mm=1500,
        layout="FF",
        engine_bay_length_mm=800.0,
        engine_bay_width_mm=700.0,
        engine_bay_height_mm=650.0,
        max_cooling_capacity_kw=120.0,
        material="STEEL",
        rigidity_rating=55.0,
        weight_kg=300.0,
        crash_test_rating=60.0,
        tech_level=1,
        manufacturing_cost=1800.0,
    )
    db.add(chassis)
    db.flush()

    trim = CarTrim(
        game_id=game_id,
        company_id=company_id,
        name="Market Test Trim",
        model_name="Market Test Model",
        trim_code=f"MT-TRIM-{game_id}",
        engine_id=engine.id,
        chassis_id=chassis.id,
        body_style="SEDAN",
        seating_capacity=5,
        cargo_volume_liters=400,
        body_weight_kg=250.0,
        drag_coefficient=0.35,
        frontal_area_sqm=2.3,
        total_weight_kg=700.0,
        power_to_weight_ratio=0.14,
        zero_to_hundred_kph_sec=12.0,
        top_speed_kph=160.0,
        quarter_mile_sec=18.0,
        braking_100_0_meters=45.0,
        lateral_g_force=0.75,
        fuel_economy_l_100km=7.5,
        final_reliability_score=70.0,
        segment="COMPACT",
        manufacturing_cost=5_000.0,
        msrp=9_000.0,
        is_in_production=True,
        production_start_turn=0,
    )
    db.add(trim)
    db.flush()
    return trim


def test_market_sales_mutate_inventory_finance_and_history(isolated_db_session):
    db = isolated_db_session
    game = db.query(GameState).first()
    company = db.query(Company).filter(Company.id == 1).one()
    company.cash = 1_000_000.0

    region = _create_region(db, game.id)
    trim = _create_trim(db, game.id, company.id)

    db.add(DistributionNetwork(
        game_id=game.id,
        company_id=company.id,
        region_id=region.id,
        type="OWNED",
        coverage_level=1.0,
        quality_score=85.0,
        monthly_capacity=40,
        setup_cost=0.0,
        monthly_upkeep=0.0,
        established_turn=0,
        is_active=True,
    ))

    inventory = DealershipInventory(
        game_id=game.id,
        region_id=region.id,
        car_trim_id=trim.id,
        company_id=company.id,
        quantity_new=15,
        quantity_in_transit=0,
        current_msrp=trim.msrp,
        current_discount_percent=0.0,
        effective_price=trim.msrp,
        last_restocked_turn=0,
        is_stocked=True,
    )
    db.add(inventory)

    db.add(ConsumerBucket(
        game_id=game.id,
        region_id=region.id,
        bucket_code=f"TEST-FAMILY-{game.id}",
        name="Test Family Buyers",
        segment="FAMILY",
        population_count=4_800,
        avg_income=60_000.0,
        avg_age=40.0,
        purchase_frequency_years=1.0,
        price_sensitivity=0.1,
        min_acceptable_utility=0.0,
    ))
    db.commit()

    random.seed(1)
    result = MarketSimulator(db).calculate_monthly_sales(
        region_id=region.id,
        current_turn=game.turn_number,
        game_id=game.id,
    )

    db.refresh(inventory)
    db.refresh(company)

    assert result.total_sales == 10
    assert inventory.quantity_new == 5
    assert inventory.units_sold_last_turn == 10
    assert company.monthly_units_sold == 10
    assert company.monthly_revenue == pytest.approx(90_000.0)
    assert company.monthly_cost_manufacturing == pytest.approx(50_000.0)
    assert company.monthly_profit == pytest.approx(40_000.0)
    assert company.cash == pytest.approx(1_040_000.0)

    sales = db.query(SalesHistory).filter(
        SalesHistory.game_id == game.id,
        SalesHistory.turn_number == game.turn_number + 1,
        SalesHistory.region_id == region.id,
        SalesHistory.trim_id == trim.id,
    ).one()
    assert sales.units_sold == 10
    assert sales.revenue_total == pytest.approx(90_000.0)
    assert sales.gross_profit_total == pytest.approx(40_000.0)
    assert sales.market_share_percent == pytest.approx(100.0)

    demand = db.query(MarketDemandHistory).filter(
        MarketDemandHistory.game_id == game.id,
        MarketDemandHistory.turn_number == game.turn_number + 1,
        MarketDemandHistory.region_id == region.id,
    ).one()
    assert demand.total_demand >= result.total_sales
    assert demand.new_car_sales == result.total_sales
    assert demand.used_car_sales == 0
    assert demand.lost_demand == result.unmet_demand
    assert demand.lost_reasons
