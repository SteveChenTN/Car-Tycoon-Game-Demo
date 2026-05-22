# 数据驱动架构 - 模组支持

## 概述

本游戏采用**数据驱动架构**，所有游戏规则、材料属性、技术树、事件等数据都存储在外部JSON文件中，而非硬编码在代码里。

这意味着：
- ✅ **易于调整平衡性**：直接修改JSON即可，无需重新编译
- ✅ **支持模组扩展**：玩家可以创建自定义内容
- ✅ **Fail Fast原则**：数据文件错误时服务器拒绝启动，保证数据完整性

---

## 目录结构

```
assets/data/
├── component_stats.json      # 组件统计数据（材料、燃料、部件）
├── physics_constants.json    # 物理常数
├── tech_tree.json            # 技术树
├── events.json               # 游戏事件模板
└── mods/                     # 模组目录
    └── mod_*.json            # 模组文件
```

---

## 核心数据文件

### 1. `component_stats.json`

定义所有材料、燃料、组件的属性：

```json
{
  "body_materials": [
    {
      "id": "STEEL",
      "name": "Steel",
      "density_kg_m3": 7850,
      "cost_per_m2": 25.0,
      "strength_multiplier": 1.0,
      "tech_level_required": 1
    }
  ],
  "engine_materials": [...],
  "fuel_properties": [...],
  "components": [...]
}
```

**字段说明**：
- `id`: 唯一标识符（程序中引用）
- `density_kg_m3`: 材料密度，影响重量
- `cost_per_m2`: 单位成本
- `strength_multiplier`: 强度系数（影响需要的材料厚度）
- `tech_level_required`: 解锁所需技术等级

---

### 2. `physics_constants.json`

物理计算中使用的常数：

```json
{
  "fundamental_constants": {
    "PI": 3.141592653589793,
    "GRAVITY": 9.81,
    "AIR_DENSITY": 1.225
  },
  "engineering_constants": {
    "AVERAGE_PANEL_THICKNESS_MM": 0.8,
    "STRUCTURAL_REINFORCEMENT_FACTOR": 1.3
  }
}
```

修改这些值会影响所有物理计算。

---

### 3. `tech_tree.json`

技术树节点定义：

```json
{
  "nodes": [
    {
      "id": "turbocharging_tech",
      "name": "涡轮增压技术",
      "description": "研发涡轮增压系统",
      "cost": 25000,
      "research_time_turns": 6,
      "unlock_requirements": ["basic_engine_design"],
      "category": "engine",
      "effects": {
        "unlock_induction": ["TURBO"]
      }
    }
  ]
}
```

**字段说明**：
- `unlock_requirements`: 前置技术ID列表（必须先研究这些技术）
- `effects`: 解锁效果（可以是材料、配置、组件等）

---

### 4. `events.json`

随机事件和历史事件模板：

```json
{
  "events": [
    {
      "id": "oil_crisis_1973",
      "event_type": "ECONOMIC",
      "severity": "HIGH",
      "title": "石油危机",
      "description": "油价暴涨...",
      "trigger_conditions": {
        "min_turn": 1,
        "year_range": [1973, 1974]
      },
      "trigger_probability": 1.0,
      "effects": {
        "fuel_price_multiplier": 3.0
      }
    }
  ]
}
```

**字段说明**：
- `trigger_probability`: 触发概率（0-1）
- `min_year/max_year`: 限定事件年份（历史事件）
- `effects`: 事件效果（对公司或市场的影响）

---

## 模组系统

### 创建模组

1. 在 `assets/data/mods/` 目录下创建 `mod_your_mod_name.json`
2. 添加模组信息和数据：

```json
{
  "mod_info": {
    "name": "My Mod",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "Description of your mod"
  },
  
  "body_materials": [
    {
      "id": "TITANIUM",
      "name": "Titanium Alloy",
      "density_kg_m3": 4500,
      "cost_per_m2": 200.0,
      "strength_multiplier": 1.4,
      "tech_level_required": 9
    }
  ],
  
  "tech_nodes": [...],
  "events": [...]
}
```

3. 重启服务器，模组会自动加载

### 模组加载顺序

1. 基础数据（`component_stats.json`, `tech_tree.json` 等）
2. 模组文件（按文件名字母顺序）
3. 后加载的模组可以覆盖先前的数据（通过相同的 `id`）

### 示例模组

参考 `assets/data/mods/mod_super_materials.json`，它添加了：
- 钛合金材料
- 石墨烯材料
- 对应的技术节点
- 相关事件

---

## 数据验证

服务器启动时会验证：
- ✅ 所有必需文件是否存在
- ✅ JSON格式是否正确
- ✅ 技术树依赖关系是否有效
- ✅ 材料ID是否唯一

**如果验证失败，服务器将拒绝启动并输出错误信息。**

---

## 开发者指南

### 添加新的数据类型

1. 在 `backend/core/loader.py` 中添加数据结构：

```python
@dataclass
class NewDataType:
    id: str
    name: str
    # ... other fields
```

2. 在 `GameDataLoader` 中添加加载方法：

```python
def _load_new_data_type(self) -> None:
    # Load from JSON
    pass
```

3. 更新 `load_all_data()` 调用新方法

4. 在需要使用的地方调用 `get_game_data_loader()`

### 在计算器中使用数据

```python
from backend.core.loader import get_game_data_loader

loader = get_game_data_loader()
material = loader.get_material("STEEL")
print(f"密度: {material.density_kg_m3}")
```

---

## 常见问题

**Q: 修改JSON后需要重启服务器吗？**  
A: 是的，数据只在启动时加载一次。

**Q: 模组可以删除基础数据吗？**  
A: 不能。模组只能添加或覆盖数据。

**Q: 如何禁用某个模组？**  
A: 将模组文件移出 `mods/` 目录，或重命名为不以 `mod_` 开头的名字。

**Q: 模组之间冲突怎么办？**  
A: 后加载的模组会覆盖先前的数据（基于 `id`）。调整文件名以控制加载顺序。

---

## 贡献模组

欢迎分享你的模组！

1. 确保JSON格式正确
2. 添加清晰的 `description`
3. 测试平衡性
4. 提交到社区

---

**Happy Modding! 🚗💨**


