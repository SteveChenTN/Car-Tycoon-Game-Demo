"""
数据驱动架构测试脚本
验证数据加载器和数据驱动功能是否正常工作
"""
import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.core.loader import initialize_game_data, get_game_data_loader
from backend.core.engineering.physics import EngineeringCalculator


def test_data_loading():
    """测试数据加载"""
    print("=" * 60)
    print("测试 1: 数据加载器初始化")
    print("=" * 60)
    
    try:
        loader = initialize_game_data("../assets/data")
        print("✓ 数据加载器初始化成功")
        return loader
    except Exception as e:
        print(f"✗ 数据加载失败: {e}")
        return None


def test_material_access(loader):
    """测试材料数据访问"""
    print("\n" + "=" * 60)
    print("测试 2: 材料数据访问")
    print("=" * 60)
    
    try:
        materials = loader.list_all_materials()
        print(f"✓ 加载了 {len(materials)} 种车身材料:")
        
        for mat in materials:
            print(f"  - {mat.name} ({mat.id}): {mat.density_kg_m3} kg/m³, ${mat.cost_per_m2}/m², 技术等级 {mat.tech_level_required}")
        
        # 测试单个材料访问
        steel = loader.get_material("STEEL")
        if steel:
            print(f"\n✓ 单个材料访问成功: {steel.name}")
        
        return True
    except Exception as e:
        print(f"✗ 材料数据访问失败: {e}")
        return False


def test_fuel_properties(loader):
    """测试燃料属性"""
    print("\n" + "=" * 60)
    print("测试 3: 燃料属性")
    print("=" * 60)
    
    try:
        fuels = loader.list_all_fuels()
        print(f"✓ 加载了 {len(fuels)} 种燃料:")
        
        for fuel in fuels:
            print(f"  - {fuel['name']} ({fuel['id']}): {fuel['energy_density_mj_kg']} MJ/kg")
        
        return True
    except Exception as e:
        print(f"✗ 燃料属性访问失败: {e}")
        return False


def test_tech_tree(loader):
    """测试技术树"""
    print("\n" + "=" * 60)
    print("测试 4: 技术树")
    print("=" * 60)
    
    try:
        tech_nodes = loader.list_all_tech_nodes()
        print(f"✓ 加载了 {len(tech_nodes)} 个技术节点:")
        
        # 按类别分组
        categories = {}
        for node in tech_nodes:
            cat = node.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(node)
        
        for cat, nodes in categories.items():
            print(f"\n  [{cat}] - {len(nodes)} 个节点:")
            for node in nodes[:3]:  # 只显示前3个
                print(f"    - {node.name} (成本: ${node.cost:,})")
        
        # 验证依赖关系
        print("\n✓ 验证技术树依赖关系...")
        errors = 0
        for node in tech_nodes:
            for req in node.unlock_requirements:
                if not loader.get_tech_node(req):
                    print(f"  ✗ 错误: {node.id} 依赖不存在的技术 {req}")
                    errors += 1
        
        if errors == 0:
            print("  ✓ 所有依赖关系有效")
        
        return errors == 0
    except Exception as e:
        print(f"✗ 技术树访问失败: {e}")
        return False


def test_events(loader):
    """测试事件系统"""
    print("\n" + "=" * 60)
    print("测试 5: 事件系统")
    print("=" * 60)
    
    try:
        events = loader.list_all_events()
        print(f"✓ 加载了 {len(events)} 个事件模板:")
        
        # 按类型分组
        event_types = {}
        for event in events:
            et = event.event_type
            if et not in event_types:
                event_types[et] = []
            event_types[et].append(event)
        
        for etype, evts in event_types.items():
            print(f"  - {etype}: {len(evts)} 个事件")
        
        # 显示历史事件
        print("\n  历史事件:")
        historical = [e for e in events if e.min_year or e.max_year]
        for event in historical[:3]:
            year_range = f"{event.min_year or '?'}-{event.max_year or '?'}"
            print(f"    - {event.title} ({year_range})")
        
        return True
    except Exception as e:
        print(f"✗ 事件系统访问失败: {e}")
        return False


def test_mod_loading(loader):
    """测试模组加载"""
    print("\n" + "=" * 60)
    print("测试 6: 模组系统")
    print("=" * 60)
    
    try:
        # 检查模组材料
        titanium = loader.get_material("TITANIUM")
        graphene = loader.get_material("GRAPHENE")
        
        if titanium or graphene:
            print("✓ 检测到模组材料:")
            if titanium:
                print(f"  - {titanium.name}: {titanium.density_kg_m3} kg/m³")
            if graphene:
                print(f"  - {graphene.name}: {graphene.density_kg_m3} kg/m³")
        else:
            print("⚠ 未检测到模组材料（这是正常的，如果没有启用模组）")
        
        return True
    except Exception as e:
        print(f"✗ 模组系统测试失败: {e}")
        return False


def test_engineering_integration():
    """测试工程计算器集成"""
    print("\n" + "=" * 60)
    print("测试 7: 工程计算器集成")
    print("=" * 60)
    
    try:
        loader = get_game_data_loader()
        EngineeringCalculator.set_data_loader(loader)
        
        print("✓ 工程计算器数据加载器已设置")
        
        # 测试计算（使用数据驱动的值）
        displacement = EngineeringCalculator.calculate_displacement(
            bore_mm=86.0,
            stroke_mm=86.0,
            cylinder_count=4
        )
        print(f"✓ 测试计算: 4缸 86x86mm 引擎排量 = {displacement} cc")
        
        return True
    except Exception as e:
        print(f"✗ 工程计算器集成失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "数据驱动架构 - 完整测试套件" + " " * 16 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n")
    
    results = []
    
    # 1. 数据加载
    loader = test_data_loading()
    if not loader:
        print("\n❌ 数据加载失败，终止测试")
        return False
    results.append(True)
    
    # 2-6. 数据访问测试
    results.append(test_material_access(loader))
    results.append(test_fuel_properties(loader))
    results.append(test_tech_tree(loader))
    results.append(test_events(loader))
    results.append(test_mod_loading(loader))
    
    # 7. 工程计算器集成
    results.append(test_engineering_integration())
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("\n✓ 所有测试通过！数据驱动架构工作正常。")
        return True
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


