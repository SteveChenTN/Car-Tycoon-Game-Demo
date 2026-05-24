import pytest

from backend.core.management.game_loop import GameLoopManager
from backend.core.production.production_manager import ProductionManager
from backend.core.production.retooling import RetoolingCalculator
from backend.models.company import Company
from backend.models.engineering import Chassis, Engine, CarTrim
from backend.models.game_manager import EventLog
from backend.models.production import Factory, FactoryType, Inventory, ProductionLine
from backend.models.region import Region
from backend.models.supply import (
    CompanySupplierRelation,
    ContractStatus,
    PartSupplier,
    SupplierContract,
)


pytestmark = [pytest.mark.integration, pytest.mark.db]


def _create_region(db, game_id: int) -> Region:
    region = Region(
        game_id=game_id,
        code="NAM",
        name="North America",
        population=100_000_000,
        gdp_per_capita=30_000.0,
        gdp_growth_rate=0.02,
        purchasing_power_index=1.0,
        inflation_rate=0.03,
        unemployment_rate=0.05,
        car_ownership_rate=500.0,
        avg_vehicle_age=7.0,
        annual_sales_potential=1_000_000,
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


def _create_design(db, game_id: int, company_id: int) -> CarTrim:
    engine = Engine(
        game_id=game_id,
        company_id=company_id,
        name="Test I4",
        code=f"T-I4-{game_id}",
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
        name="Test Platform",
        code=f"T-CH-{game_id}",
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
        name="Test Trim",
        model_name="Test Model",
        trim_code=f"T-TRIM-{game_id}",
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
        manufacturing_cost=5000.0,
        msrp=9000.0,
    )
    db.add(trim)
    db.commit()
    return trim


def _create_factory(
    db,
    game_id: int,
    company_id: int,
    region_id: int,
    factory_type: str,
    name: str,
) -> Factory:
    factory = Factory(
        game_id=game_id,
        company_id=company_id,
        name=name,
        factory_type=factory_type,
        level=1,
        capacity_units_per_month=40,
        current_utilization_rate=0.0,
        region_id=region_id,
        efficiency_score=100.0,
        labor_cost_per_unit=10.0,
        overhead_cost_per_month=1000.0,
        tech_level=1,
        is_operational=True,
    )
    db.add(factory)
    db.flush()
    return factory


def _seed_materials(inventory: Inventory, materials: dict[str, float], quantity: int) -> None:
    for material, per_unit in materials.items():
        inventory.add_material(material, per_unit * quantity)


def _create_world(db):
    game = db.query(__import__("backend.models.game_state", fromlist=["GameState"]).GameState).first()
    company = db.query(Company).filter(Company.id == 1).first()
    company.cash = 1_000_000_000.0
    company.production_efficiency = 1.0

    region = _create_region(db, game.id)
    trim = _create_design(db, game.id, company.id)
    component_factory = _create_factory(
        db, game.id, company.id, region.id, FactoryType.COMPONENT.value, "Component Plant"
    )
    assembly_factory = _create_factory(
        db, game.id, company.id, region.id, FactoryType.ASSEMBLY.value, "Assembly Plant"
    )

    component_inventory = Inventory(
        game_id=game.id,
        factory_id=component_factory.id,
        raw_materials={},
        finished_components={},
        completed_cars={},
        total_inventory_value=0.0,
    )
    assembly_inventory = Inventory(
        game_id=game.id,
        factory_id=assembly_factory.id,
        raw_materials={},
        finished_components={},
        completed_cars={},
        total_inventory_value=0.0,
    )
    db.add_all([component_inventory, assembly_inventory])
    db.flush()

    manager = ProductionManager(db)
    component_materials = manager._sum_materials(
        manager.calculate_engine_material_requirements(trim.engine),
        manager.calculate_chassis_material_requirements(trim.chassis),
    )
    body_materials = manager.calculate_car_body_material_requirements(trim)
    _seed_materials(component_inventory, component_materials, 20)
    _seed_materials(assembly_inventory, body_materials, 20)

    component_line = ProductionLine(
        game_id=game.id,
        factory_id=component_factory.id,
        name="Components",
        status="RUNNING",
        current_design_id=trim.id,
        monthly_capacity=40,
    )
    assembly_line = ProductionLine(
        game_id=game.id,
        factory_id=assembly_factory.id,
        name="Assembly",
        status="RUNNING",
        current_design_id=trim.id,
        monthly_capacity=40,
    )
    db.add_all([component_line, assembly_line])
    db.commit()

    return {
        "game": game,
        "company": company,
        "region": region,
        "trim": trim,
        "component_factory": component_factory,
        "assembly_factory": assembly_factory,
        "component_inventory": component_inventory,
        "assembly_inventory": assembly_inventory,
        "component_line": component_line,
        "assembly_line": assembly_line,
    }


def test_weekly_production_builds_components_and_cars(isolated_db_session):
    db = isolated_db_session
    world = _create_world(db)

    result = ProductionManager(db).process_weekly_production(world["game"].id, 0)
    db.refresh(world["assembly_inventory"])
    db.refresh(world["company"])

    assert result["cars_assembled"] == 10
    assert result["components_produced"] == 20
    assert world["assembly_inventory"].get_car_quantity(world["trim"].id) == 10
    assert world["company"].monthly_units_produced == 10


def test_shortage_reduces_or_stops_line_and_logs_event(isolated_db_session):
    db = isolated_db_session
    world = _create_world(db)
    world["component_inventory"].raw_materials = {}
    db.commit()

    result = GameLoopManager(db)._phase_production(world["game"].id, 0)
    db.flush()

    assert result["cars_assembled"] == 0
    assert result["events"]
    assert db.query(EventLog).filter(EventLog.event_type == "PRODUCTION").count() >= 1


def test_supplier_contract_delivery_adds_material_inventory(isolated_db_session):
    db = isolated_db_session
    world = _create_world(db)
    world["component_inventory"].raw_materials = {}

    supplier = PartSupplier(
        game_id=world["game"].id,
        name="Steel Supplier",
        short_name="STEELCO",
        founded_year=1950,
        headquarters_region_id=world["region"].id,
        specialty="STEEL",
        quality_level=70.0,
        reliability_rating=90.0,
        capacity_monthly=1000,
    )
    db.add(supplier)
    db.flush()
    relation = CompanySupplierRelation(
        company_id=world["company"].id,
        supplier_id=supplier.id,
        trust_level=0.5,
    )
    db.add(relation)
    db.flush()
    contract = SupplierContract(
        game_id=world["game"].id,
        relation_id=relation.id,
        supplier_id=supplier.id,
        company_id=world["company"].id,
        contract_type="FIXED_PRICE",
        material_type="STEEL",
        fixed_price_per_unit=2.0,
        monthly_volume_commitment=40,
        max_monthly_volume=40,
        start_turn=0,
        end_turn=8,
        status=ContractStatus.ACTIVE.value,
    )
    db.add(contract)
    db.commit()

    result = GameLoopManager(db)._phase_contract_execution(world["game"].id, 0)
    db.refresh(world["component_inventory"])

    assert result["contracts_executed"] == 1
    assert result["total_materials_delivered"] == 10
    assert world["component_inventory"].get_material_quantity("STEEL") == 10


def test_retooling_keeps_target_design_for_completion(isolated_db_session):
    db = isolated_db_session
    world = _create_world(db)
    line = world["assembly_line"]
    line.status = "IDLE"
    line.current_design_id = None
    db.commit()

    success, _, details = RetoolingCalculator.start_retooling(db, line, world["trim"], 0)
    assert success
    assert line.current_design_id == world["trim"].id

    completed = GameLoopManager(db)._check_retooling_completion(
        world["game"].id, details["completion_turn"]
    )
    db.refresh(line)

    assert completed == 1
    assert line.status == "RUNNING"
    assert line.current_design_id == world["trim"].id
