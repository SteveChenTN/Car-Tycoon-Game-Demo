"""
存档系统管理器
负责序列化和反序列化游戏完整状态
"""
from sqlalchemy.orm import Session
from sqlalchemy import inspect, select
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime
from pathlib import Path

from backend.database import Base, SessionLocal
from backend.models import *
from backend.config import settings

logger = logging.getLogger(__name__)


class SaveLoadManager:
    """
    游戏存档管理器
    
    设计原则:
    1. 只序列化动态数据（游戏状态、公司、车辆等），不序列化静态配置（法规模板、难度配置等）
    2. 支持完整导出和增量保存
    3. 验证数据完整性
    """
    
    # 需要导出的动态表（按依赖顺序）
    DYNAMIC_TABLES = [
        "game_state",
        "regions",
        "companies",
        "engines",
        "chassis",
        "car_trims",
        "factories",
        "material_markets",
        "inventories",
        "component_listings",
        "b2b_transactions",
        "distribution_networks",
        "marketing_campaigns",
        "brand_perceptions",
        "consumer_buckets",
        "intelligence_reports",
        "loans",
        "tax_records",
        "vehicle_compliance",
        "recall_events",
        "prototype_projects",
        "testing_facilities",
        "game_events"
    ]
    
    # 静态配置表（不导出到存档，但需要在数据库中）
    STATIC_TABLES = [
        "regulations",
        "event_templates",
        "prestige_levels",
        "scenarios",
        "difficulty_modifiers"
    ]
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化存档管理器
        
        Args:
            db: 数据库会话（可选，未提供则创建新会话）
        """
        self.db = db
        self._owns_session = False
        if not self.db:
            self.db = SessionLocal()
            self._owns_session = True
    
    def __del__(self):
        """析构时关闭会话"""
        if self._owns_session and self.db:
            self.db.close()
    
    def save_game(
        self,
        game_id: int,
        save_path: str,
        save_name: str = "AutoSave",
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        保存游戏到文件
        
        Args:
            game_id: 游戏状态ID
            save_path: 保存路径
            save_name: 存档名称
            include_metadata: 是否包含元数据
        
        Returns:
            保存结果字典 {"success": bool, "file_path": str, "size_mb": float}
        """
        try:
            logger.info(f"开始保存游戏 game_id={game_id} to {save_path}")
            
            # 验证游戏存在
            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
            if not game_state:
                raise ValueError(f"Game ID {game_id} not found")
            
            # 构建保存数据
            save_data: Dict[str, Any] = {
                "version": settings.VERSION,
                "save_name": save_name,
                "game_id": game_id,
                "saved_at": datetime.utcnow().isoformat(),
                "data": {}
            }
            
            # 添加元数据
            if include_metadata:
                save_data["metadata"] = {
                    "current_year": game_state.current_year,
                    "current_month": game_state.current_month,
                    "current_week": game_state.current_week,
                    "turn_number": game_state.turn_number,
                    "difficulty": game_state.difficulty
                }
            
            # 导出每个表的数据
            for table_name in self.DYNAMIC_TABLES:
                try:
                    table_data = self._export_table(table_name, game_id)
                    save_data["data"][table_name] = table_data
                    logger.debug(f"已导出 {table_name}: {len(table_data)} 条记录")
                except Exception as e:
                    logger.error(f"导出表 {table_name} 失败: {e}")
                    raise
            
            # 写入文件
            save_file = Path(save_path)
            save_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            # 计算文件大小
            file_size_mb = save_file.stat().st_size / (1024 * 1024)
            
            logger.info(f"游戏保存成功: {save_file} ({file_size_mb:.2f} MB)")
            
            return {
                "success": True,
                "file_path": str(save_file),
                "size_mb": round(file_size_mb, 2),
                "record_count": sum(len(v) for v in save_data["data"].values())
            }
            
        except Exception as e:
            logger.error(f"保存游戏失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_game(
        self,
        save_path: str,
        clear_existing: bool = True
    ) -> Dict[str, Any]:
        """
        从文件加载游戏
        
        Args:
            save_path: 存档文件路径
            clear_existing: 是否清空现有数据（危险操作！）
        
        Returns:
            加载结果字典
        """
        try:
            logger.info(f"开始加载游戏 from {save_path}")
            
            # 读取文件
            save_file = Path(save_path)
            if not save_file.exists():
                raise FileNotFoundError(f"Save file not found: {save_path}")
            
            with open(save_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # 验证版本兼容性
            save_version = save_data.get("version", "unknown")
            logger.info(f"存档版本: {save_version}, 当前版本: {settings.VERSION}")
            
            # 可选：清空现有数据（仅在明确请求时）
            if clear_existing:
                logger.warning("清空现有游戏数据...")
                self._clear_dynamic_data()
            
            # 导入数据
            imported_counts = {}
            for table_name in self.DYNAMIC_TABLES:
                if table_name in save_data["data"]:
                    records = save_data["data"][table_name]
                    count = self._import_table(table_name, records)
                    imported_counts[table_name] = count
                    logger.debug(f"已导入 {table_name}: {count} 条记录")
            
            self.db.commit()
            
            logger.info(f"游戏加载成功: {sum(imported_counts.values())} 条记录")
            
            return {
                "success": True,
                "save_name": save_data.get("save_name"),
                "game_id": save_data.get("game_id"),
                "metadata": save_data.get("metadata"),
                "imported_counts": imported_counts,
                "total_records": sum(imported_counts.values())
            }
            
        except Exception as e:
            logger.error(f"加载游戏失败: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _export_table(self, table_name: str, game_id: int) -> List[Dict[str, Any]]:
        """
        导出单个表的数据
        
        Args:
            table_name: 表名
            game_id: 游戏ID
        
        Returns:
            记录列表
        """
        # 获取模型类
        model_class = self._get_model_class(table_name)
        if not model_class:
            return []
        
        # 查询数据（过滤game_id）
        query = self.db.query(model_class)
        if hasattr(model_class, 'game_id'):
            query = query.filter(model_class.game_id == game_id)
        
        records = query.all()
        
        # 序列化为字典
        return [self._serialize_record(record) for record in records]
    
    def _import_table(self, table_name: str, records: List[Dict[str, Any]]) -> int:
        """
        导入单个表的数据
        
        Args:
            table_name: 表名
            records: 记录列表
        
        Returns:
            导入记录数
        """
        model_class = self._get_model_class(table_name)
        if not model_class or not records:
            return 0
        
        for record_data in records:
            # 创建模型实例
            record = model_class(**record_data)
            self.db.add(record)
        
        return len(records)
    
    def _serialize_record(self, record: Any) -> Dict[str, Any]:
        """
        序列化ORM记录为字典
        
        Args:
            record: ORM模型实例
        
        Returns:
            字典表示
        """
        result = {}
        mapper = inspect(record.__class__)
        
        for column in mapper.columns:
            value = getattr(record, column.key)
            
            # 处理特殊类型
            if isinstance(value, datetime):
                result[column.key] = value.isoformat()
            elif isinstance(value, enum.Enum):
                result[column.key] = value.value
            else:
                result[column.key] = value
        
        return result
    
    def _get_model_class(self, table_name: str) -> Optional[type]:
        """
        根据表名获取模型类
        
        Args:
            table_name: 表名
        
        Returns:
            模型类或None
        """
        # 映射表名到模型类
        table_to_model = {
            "game_state": GameState,
            "regions": Region,
            "companies": Company,
            "engines": Engine,
            "chassis": Chassis,
            "car_trims": CarTrim,
            "factories": Factory,
            "material_markets": MaterialMarket,
            "inventories": Inventory,
            "component_listings": ComponentListing,
            "b2b_transactions": B2BTransaction,
            "distribution_networks": DistributionNetwork,
            "marketing_campaigns": MarketingCampaign,
            "brand_perceptions": BrandPerception,
            "consumer_buckets": ConsumerBucket,
            "intelligence_reports": IntelligenceReport,
            "loans": Loan,
            "tax_records": TaxRecord,
            "vehicle_compliance": VehicleCompliance,
            "recall_events": RecallEvent,
            "prototype_projects": PrototypeProject,
            "testing_facilities": TestingFacility,
            "game_events": GameEvent,
            "regulations": Regulation,
            "event_templates": EventTemplate,
            "prestige_levels": PrestigeLevel,
            "scenarios": Scenario,
            "difficulty_modifiers": DifficultyModifier
        }
        
        return table_to_model.get(table_name)
    
    def _clear_dynamic_data(self) -> None:
        """
        清空所有动态数据（保留静态配置）
        警告：这是危险操作！
        """
        # 反向删除（因为外键依赖）
        for table_name in reversed(self.DYNAMIC_TABLES):
            model_class = self._get_model_class(table_name)
            if model_class:
                self.db.query(model_class).delete()
        
        self.db.commit()
        logger.info("动态数据已清空")
    
    def get_save_info(self, save_path: str) -> Dict[str, Any]:
        """
        获取存档信息（不加载完整数据）
        
        Args:
            save_path: 存档路径
        
        Returns:
            存档信息字典
        """
        try:
            save_file = Path(save_path)
            if not save_file.exists():
                return {"success": False, "error": "File not found"}
            
            with open(save_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            return {
                "success": True,
                "save_name": save_data.get("save_name"),
                "version": save_data.get("version"),
                "saved_at": save_data.get("saved_at"),
                "metadata": save_data.get("metadata"),
                "file_size_mb": round(save_file.stat().st_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_saves(self, saves_directory: str = None) -> List[Dict[str, Any]]:
        """
        列出所有存档文件
        
        Args:
            saves_directory: 存档目录（默认为data/saves）
        
        Returns:
            存档信息列表
        """
        if saves_directory is None:
            saves_directory = settings.DATA_DIR / "saves"
        
        saves_dir = Path(saves_directory)
        if not saves_dir.exists():
            return []
        
        save_files = list(saves_dir.glob("*.json"))
        save_infos = []
        
        for save_file in save_files:
            info = self.get_save_info(str(save_file))
            if info.get("success"):
                info["file_path"] = str(save_file)
                save_infos.append(info)
        
        # 按保存时间排序
        save_infos.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        
        return save_infos


__all__ = ["SaveLoadManager"]


