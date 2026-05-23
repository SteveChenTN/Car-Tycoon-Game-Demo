import pytest

from backend.core.engineering.physics import EngineeringCalculator


pytestmark = pytest.mark.unit


def test_data_loading(game_data_loader):
    assert game_data_loader.list_all_materials()
    assert game_data_loader.list_all_fuels()
    assert game_data_loader.list_all_tech_nodes()
    assert game_data_loader.list_all_events()


def test_material_access(game_data_loader):
    materials = game_data_loader.list_all_materials()

    assert len(materials) >= 1
    assert game_data_loader.get_material("STEEL") is not None
    assert all(material.id for material in materials)
    assert all(material.density_kg_m3 > 0 for material in materials)
    assert all(material.cost_per_m2 >= 0 for material in materials)


def test_fuel_properties(game_data_loader):
    fuels = game_data_loader.list_all_fuels()

    assert len(fuels) >= 1
    assert any(fuel["id"] == "GASOLINE" for fuel in fuels)
    assert all(fuel["energy_density_mj_kg"] > 0 for fuel in fuels)


def test_tech_tree_dependencies(game_data_loader):
    tech_nodes = game_data_loader.list_all_tech_nodes()
    missing_dependencies = [
        (node.id, requirement)
        for node in tech_nodes
        for requirement in node.unlock_requirements
        if game_data_loader.get_tech_node(requirement) is None
    ]

    assert tech_nodes
    assert missing_dependencies == []


def test_events(game_data_loader):
    events = game_data_loader.list_all_events()

    assert len(events) >= 1
    assert all(event.id for event in events)
    assert all(event.event_type for event in events)


def test_mod_loading(game_data_loader):
    loaded_mod_materials = [
        material_id
        for material_id in ("TITANIUM", "GRAPHENE")
        if game_data_loader.get_material(material_id) is not None
    ]

    assert loaded_mod_materials


def test_engineering_integration(game_data_loader):
    EngineeringCalculator.set_data_loader(game_data_loader)

    displacement = EngineeringCalculator.calculate_displacement(
        bore_mm=86.0,
        stroke_mm=86.0,
        cylinder_count=4,
    )

    assert displacement == pytest.approx(1998.11, rel=0.01)
