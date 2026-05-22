"""
数据驱动架构 - 游戏数据加载器
Game Data Loader - Support for Modding via External JSON Files

设计原则：
1. Fail Fast - 如果数据文件缺失或格式错误，拒绝启动
2. Validation - 验证所有数据完整性和类型
3. Modding Support - 自动加载基础数据 + 模组扩展
4. In-Memory Cache - 启动时加载一次，运行时从内存读取
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class MaterialData:
    """材料数据结构"""
    id: str
    name: str
    density_kg_m3: float
    cost_per_m2: float
    strength_multiplier: float
    tech_level_required: int


@dataclass
class ComponentData:
    """组件数据结构（涡轮、机械增压等）"""
    id: str
    name: str
    type: str  # "turbo", "supercharger", etc.
    cost: float
    weight_kg: float
    boost_multiplier: float
    tech_level_required: int


@dataclass
class TechNode:
    """技术树节点"""
    id: str
    name: str
    description: str
    cost: float
    research_time_turns: int
    unlock_requirements: List[str]  # 前置技术ID列表
    category: str
    effects: Dict[str, Any]


@dataclass
class GameEventTemplate:
    """游戏事件模板"""
    id: str
    event_type: str
    severity: str
    title: str
    description: str
    trigger_conditions: Dict[str, Any]
    trigger_probability: float
    effects: Dict[str, Any]
    min_year: Optional[int]
    max_year: Optional[int]


class GameDataLoader:
    """
    游戏数据加载器
    
    职责：
    1. 在服务器启动时从JSON加载所有游戏数据
    2. 验证数据完整性
    3. 提供数据访问接口
    4. 支持模组扩展
    """
    
    def __init__(self, data_directory: str = "assets/data"):
        """
        初始化数据加载器
        
        Args:
            data_directory: 数据文件目录路径
        """
        self.data_directory = Path(data_directory)
        
        # 数据存储（内存中）
        self.materials: Dict[str, MaterialData] = {}
        self.engine_materials: Dict[str, Dict[str, Any]] = {}
        self.fuel_properties: Dict[str, Dict[str, Any]] = {}
        self.components: Dict[str, ComponentData] = {}
        self.tech_tree: Dict[str, TechNode] = {}
        self.events: Dict[str, GameEventTemplate] = {}
        self.physics_constants: Dict[str, Any] = {}
        self.cost_multipliers: Dict[str, Dict[str, float]] = {}
        
        self._loaded = False
        
        logger.info(f"数据加载器初始化，数据目录: {self.data_directory.absolute()}")
    
    def load_all_data(self) -> None:
        """
        加载所有游戏数据
        
        如果任何关键文件缺失或格式错误，抛出异常（Fail Fast）
        """
        logger.info("=" * 60)
        logger.info("开始加载游戏数据...")
        logger.info("=" * 60)
        
        try:
            # 验证目录存在
            if not self.data_directory.exists():
                raise FileNotFoundError(
                    f"数据目录不存在: {self.data_directory.absolute()}\n"
                    f"请创建目录并放置JSON数据文件。"
                )
            
            # 加载各类数据（顺序很重要）
            self._load_physics_constants()
            self._load_component_stats()
            self._load_tech_tree()
            self._load_events()
            
            # 加载模组（如果存在）
            self._load_mods()
            
            # 验证数据完整性
            self._validate_all_data()
            
            self._loaded = True
            
            logger.info("=" * 60)
            logger.info("✓ 所有游戏数据加载成功！")
            logger.info(f"  - 材料: {len(self.materials)} 种")
            logger.info(f"  - 引擎材料: {len(self.engine_materials)} 种")
            logger.info(f"  - 燃料类型: {len(self.fuel_properties)} 种")
            logger.info(f"  - 组件: {len(self.components)} 种")
            logger.info(f"  - 技术节点: {len(self.tech_tree)} 个")
            logger.info(f"  - 事件模板: {len(self.events)} 个")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.critical(f"❌ 数据加载失败: {e}", exc_info=True)
            logger.critical("服务器无法启动，请检查数据文件。")
            raise RuntimeError(f"Game data loading failed: {e}") from e
    
    def _load_physics_constants(self) -> None:
        """加载物理常数"""
        file_path = self.data_directory / "physics_constants.json"
        
        if not file_path.exists():
            logger.warning(f"物理常数文件不存在: {file_path}，使用默认值")
            # 使用默认值
            self.physics_constants = {
                "GRAVITY": 9.81,
                "AIR_DENSITY": 1.225,
                "PI": 3.141592653589793
            }
            return
        
        logger.info(f"加载物理常数: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.physics_constants = data
        
        logger.debug(f"  ✓ 加载 {len(data)} 个物理常数")
    
    def _load_component_stats(self) -> None:
        """加载组件统计数据（材料、燃料、部件）"""
        file_path = self.data_directory / "component_stats.json"
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"关键文件缺失: {file_path}\n"
                f"请创建 component_stats.json 文件。"
            )
        
        logger.info(f"加载组件数据: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载车身材料（Chassis Materials）
        if "body_materials" in data:
            for mat in data["body_materials"]:
                self.materials[mat["id"]] = MaterialData(
                    id=mat["id"],
                    name=mat["name"],
                    density_kg_m3=mat["density_kg_m3"],
                    cost_per_m2=mat["cost_per_m2"],
                    strength_multiplier=mat["strength_multiplier"],
                    tech_level_required=mat["tech_level_required"]
                )
            logger.debug(f"  ✓ 车身材料: {len(self.materials)} 种")
        
        # 加载引擎材料（Engine Materials）
        if "engine_materials" in data:
            for mat in data["engine_materials"]:
                self.engine_materials[mat["id"]] = mat
            logger.debug(f"  ✓ 引擎材料: {len(self.engine_materials)} 种")
        
        # 加载燃料属性
        if "fuel_properties" in data:
            for fuel in data["fuel_properties"]:
                self.fuel_properties[fuel["id"]] = fuel
            logger.debug(f"  ✓ 燃料类型: {len(self.fuel_properties)} 种")
        
        # 加载组件（涡轮、机械增压等）
        if "components" in data:
            for comp in data["components"]:
                self.components[comp["id"]] = ComponentData(
                    id=comp["id"],
                    name=comp["name"],
                    type=comp["type"],
                    cost=comp["cost"],
                    weight_kg=comp["weight_kg"],
                    boost_multiplier=comp.get("boost_multiplier", 1.0),
                    tech_level_required=comp["tech_level_required"]
                )
            logger.debug(f"  ✓ 组件: {len(self.components)} 种")
        
        # 加载成本系数
        if "cost_multipliers" in data:
            self.cost_multipliers = data["cost_multipliers"]
            logger.debug(f"  ✓ 成本系数: {len(self.cost_multipliers)} 类")
    
    def _load_tech_tree(self) -> None:
        """加载技术树"""
        file_path = self.data_directory / "tech_tree.json"
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"关键文件缺失: {file_path}\n"
                f"请创建 tech_tree.json 文件。"
            )
        
        logger.info(f"加载技术树: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载技术节点
        if "nodes" in data:
            for node in data["nodes"]:
                self.tech_tree[node["id"]] = TechNode(
                    id=node["id"],
                    name=node["name"],
                    description=node["description"],
                    cost=node["cost"],
                    research_time_turns=node["research_time_turns"],
                    unlock_requirements=node.get("unlock_requirements", []),
                    category=node.get("category", "general"),
                    effects=node.get("effects", {})
                )
            logger.debug(f"  ✓ 技术节点: {len(self.tech_tree)} 个")
        
        logger.info(f"  ✓ 技术树加载完成")
    
    def _load_events(self) -> None:
        """加载事件模板"""
        file_path = self.data_directory / "events.json"
        
        if not file_path.exists():
            logger.warning(f"事件文件不存在: {file_path}，游戏将没有随机事件")
            return
        
        logger.info(f"加载事件模板: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载事件
        if "events" in data:
            for event in data["events"]:
                self.events[event["id"]] = GameEventTemplate(
                    id=event["id"],
                    event_type=event["event_type"],
                    severity=event["severity"],
                    title=event["title"],
                    description=event["description"],
                    trigger_conditions=event.get("trigger_conditions", {}),
                    trigger_probability=event.get("trigger_probability", 0.1),
                    effects=event.get("effects", {}),
                    min_year=event.get("min_year"),
                    max_year=event.get("max_year")
                )
            logger.debug(f"  ✓ 事件模板: {len(self.events)} 个")
    
    def _load_mods(self) -> None:
        """
        加载模组数据
        
        扫描 assets/data/mods/ 目录，自动加载所有模组
        模组可以添加新数据或覆盖基础数据
        """
        mods_dir = self.data_directory / "mods"
        
        if not mods_dir.exists():
            logger.debug("模组目录不存在，跳过模组加载")
            return
        
        logger.info(f"扫描模组目录: {mods_dir}")
        
        # 查找所有 mod_*.json 文件
        mod_files = sorted(mods_dir.glob("mod_*.json"))
        
        if not mod_files:
            logger.debug("未找到模组文件")
            return
        
        for mod_file in mod_files:
            try:
                logger.info(f"加载模组: {mod_file.name}")
                
                with open(mod_file, 'r', encoding='utf-8') as f:
                    mod_data = json.load(f)
                
                # 模组元数据
                mod_info = mod_data.get("mod_info", {})
                logger.info(f"  模组名称: {mod_info.get('name', 'Unknown')}")
                logger.info(f"  版本: {mod_info.get('version', 'Unknown')}")
                logger.info(f"  作者: {mod_info.get('author', 'Unknown')}")
                
                # 合并数据（模组可以添加或覆盖）
                if "body_materials" in mod_data:
                    for mat in mod_data["body_materials"]:
                        self.materials[mat["id"]] = MaterialData(
                            id=mat["id"],
                            name=mat["name"],
                            density_kg_m3=mat["density_kg_m3"],
                            cost_per_m2=mat["cost_per_m2"],
                            strength_multiplier=mat["strength_multiplier"],
                            tech_level_required=mat["tech_level_required"]
                        )
                    logger.debug(f"  ✓ 添加/覆盖 {len(mod_data['body_materials'])} 种材料")
                
                if "tech_nodes" in mod_data:
                    for node in mod_data["tech_nodes"]:
                        self.tech_tree[node["id"]] = TechNode(
                            id=node["id"],
                            name=node["name"],
                            description=node["description"],
                            cost=node["cost"],
                            research_time_turns=node["research_time_turns"],
                            unlock_requirements=node.get("unlock_requirements", []),
                            category=node.get("category", "mod"),
                            effects=node.get("effects", {})
                        )
                    logger.debug(f"  ✓ 添加/覆盖 {len(mod_data['tech_nodes'])} 个技术节点")
                
                if "events" in mod_data:
                    for event in mod_data["events"]:
                        self.events[event["id"]] = GameEventTemplate(
                            id=event["id"],
                            event_type=event["event_type"],
                            severity=event["severity"],
                            title=event["title"],
                            description=event["description"],
                            trigger_conditions=event.get("trigger_conditions", {}),
                            trigger_probability=event.get("trigger_probability", 0.1),
                            effects=event.get("effects", {}),
                            min_year=event.get("min_year"),
                            max_year=event.get("max_year")
                        )
                    logger.debug(f"  ✓ 添加/覆盖 {len(mod_data['events'])} 个事件")
                
                logger.info(f"  ✓ 模组 {mod_file.name} 加载成功")
                
            except Exception as e:
                logger.error(f"模组加载失败 {mod_file.name}: {e}", exc_info=True)
                # 模组加载失败不影响主程序启动
                continue
    
    def _validate_all_data(self) -> None:
        """验证数据完整性"""
        logger.info("验证数据完整性...")
        
        errors = []
        
        # 验证材料数据
        if not self.materials:
            errors.append("未加载任何车身材料")
        
        if not self.engine_materials:
            errors.append("未加载任何引擎材料")
        
        if not self.fuel_properties:
            errors.append("未加载任何燃料类型")
        
        # 验证技术树
        if not self.tech_tree:
            errors.append("技术树为空")
        
        # 验证技术树依赖关系
        for tech_id, tech in self.tech_tree.items():
            for req_id in tech.unlock_requirements:
                if req_id not in self.tech_tree:
                    errors.append(f"技术 '{tech_id}' 依赖不存在的技术: '{req_id}'")
        
        if errors:
            error_msg = "\n".join(f"  - {err}" for err in errors)
            raise ValueError(f"数据验证失败:\n{error_msg}")
        
        logger.info("  ✓ 数据验证通过")
    
    # ==================== 数据访问接口 ====================
    
    def get_material(self, material_id: str) -> Optional[MaterialData]:
        """获取车身材料数据"""
        return self.materials.get(material_id)
    
    def get_engine_material(self, material_id: str) -> Optional[Dict[str, Any]]:
        """获取引擎材料数据"""
        return self.engine_materials.get(material_id)
    
    def get_fuel_properties(self, fuel_id: str) -> Optional[Dict[str, Any]]:
        """获取燃料属性"""
        return self.fuel_properties.get(fuel_id)
    
    def get_component(self, component_id: str) -> Optional[ComponentData]:
        """获取组件数据"""
        return self.components.get(component_id)
    
    def get_tech_node(self, tech_id: str) -> Optional[TechNode]:
        """获取技术节点"""
        return self.tech_tree.get(tech_id)
    
    def get_event_template(self, event_id: str) -> Optional[GameEventTemplate]:
        """获取事件模板"""
        return self.events.get(event_id)
    
    def get_physics_constant(self, constant_name: str, default: Any = None) -> Any:
        """获取物理常数"""
        return self.physics_constants.get(constant_name, default)
    
    def get_cost_multiplier(self, category: str, item_id: str, default: float = 1.0) -> float:
        """获取成本系数"""
        if category in self.cost_multipliers:
            return self.cost_multipliers[category].get(item_id, default)
        return default
    
    def list_all_materials(self) -> List[MaterialData]:
        """列出所有车身材料"""
        return list(self.materials.values())
    
    def list_all_engine_materials(self) -> List[Dict[str, Any]]:
        """列出所有引擎材料"""
        return list(self.engine_materials.values())
    
    def list_all_fuels(self) -> List[Dict[str, Any]]:
        """列出所有燃料类型"""
        return list(self.fuel_properties.values())
    
    def list_all_tech_nodes(self) -> List[TechNode]:
        """列出所有技术节点"""
        return list(self.tech_tree.values())
    
    def list_all_events(self) -> List[GameEventTemplate]:
        """列出所有事件模板"""
        return list(self.events.values())
    
    def is_loaded(self) -> bool:
        """检查数据是否已加载"""
        return self._loaded


# 全局单例
_game_data_loader: Optional[GameDataLoader] = None


def get_game_data_loader() -> GameDataLoader:
    """
    获取全局数据加载器单例
    
    Returns:
        GameDataLoader实例
    
    Raises:
        RuntimeError: 如果数据未加载
    """
    global _game_data_loader
    
    if _game_data_loader is None:
        raise RuntimeError(
            "Game data not loaded. Call initialize_game_data() first."
        )
    
    return _game_data_loader


def initialize_game_data(data_directory: str = "assets/data") -> GameDataLoader:
    """
    初始化并加载游戏数据（服务器启动时调用一次）
    
    Args:
        data_directory: 数据文件目录
    
    Returns:
        GameDataLoader实例
    """
    global _game_data_loader
    
    if _game_data_loader is not None:
        logger.warning("Game data already initialized, skipping...")
        return _game_data_loader
    
    logger.info("初始化游戏数据加载器...")
    
    _game_data_loader = GameDataLoader(data_directory)
    _game_data_loader.load_all_data()
    
    return _game_data_loader


__all__ = [
    "GameDataLoader",
    "MaterialData",
    "ComponentData",
    "TechNode",
    "GameEventTemplate",
    "get_game_data_loader",
    "initialize_game_data"
]


