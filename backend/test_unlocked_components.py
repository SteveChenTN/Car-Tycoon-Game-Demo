"""
测试解锁组件API
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.database import get_db
from backend.api.routes.engineering import get_unlocked_components
import json

def test_unlocked_components():
    """测试获取解锁组件"""
    db = next(get_db())
    try:
        result = get_unlocked_components(company_id=1, db=db)
        print("=" * 80)
        print("解锁组件API测试结果:")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("=" * 80)
        
        # 检查每个类别是否有组件
        components = result.get("components", {})
        for category, items in components.items():
            print(f"{category}: {len(items)} 个组件")
            if items:
                print(f"  组件列表: {[item.get('value', 'N/A') for item in items]}")
            else:
                print(f"  警告: {category} 类别为空！")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_unlocked_components()

