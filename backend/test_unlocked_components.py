import pytest

from backend.api.routes.engineering import get_unlocked_components


pytestmark = [pytest.mark.integration, pytest.mark.db]


@pytest.mark.asyncio
async def test_unlocked_components(isolated_db_session):
    result = await get_unlocked_components(company_id=1, db=isolated_db_session)

    assert result["success"] is True
    assert result["current_year"] == 1950

    components = result["components"]
    assert set(components) == {
        "fuel_systems",
        "materials",
        "valvetrains",
        "induction_types",
        "configurations",
    }

    assert _component_values(components["fuel_systems"]) >= {"GASOLINE"}
    assert _component_values(components["materials"]) >= {"CAST_IRON", "ALUMINUM"}
    assert _component_values(components["valvetrains"]) >= {"OHV"}
    assert _component_values(components["induction_types"]) >= {"NA"}
    assert _component_values(components["configurations"]) >= {"INLINE"}

    for category_items in components.values():
        for item in category_items:
            assert item["familiarity_level"] >= 1
            assert "cost_modifier" in item
            assert "reliability_modifier" in item


def _component_values(items):
    return {item["value"] for item in items}
