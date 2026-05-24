"""
生产管理器 - 处理零部件生产和整车装配

核心功能：
1. produce_component: 在零部件工厂生产引擎/变速箱等
2. assemble_car: 在装配厂组装完整车辆
3. auto_logistics: 计算跨地区运输成本

设计原则：
- 严格检查工厂类型匹配
- 原材料/零部件库存检查
- 工厂等级影响效率和成本
- 跨地区物流自动化（简化为成本计算）
"""
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
import math

from backend.models.production import (
    Factory, Inventory, MaterialMarket,
    FactoryType, MaterialType, ProductionLine
)
from backend.models.company import Company
from backend.models.engineering import Engine, Chassis, CarTrim
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ProductionManager:
    """生产管理器 - 协调工厂生产和库存管理"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== 原材料需求计算 ==========
    
    def calculate_engine_material_requirements(self, engine: Engine) -> Dict[str, float]:
        """
        计算生产一台引擎所需的原材料（公斤）
        
        基于物理参数计算：
        - 钢材：主要用于铸铁缸体和曲轴
        - 铝材：铝合金缸体和部件
        - 塑料：进气管、盖板等
        - 电子元件：ECU、传感器等（按件计，这里转换为等效重量）
        """
        materials = {}
        
        # 基础材料需求与引擎重量成正比
        engine_weight = engine.weight_kg
        
        # 根据材料类型分配
        if engine.material == "CAST_IRON":
            materials["STEEL"] = engine_weight * 0.70  # 铸铁缸体主要是钢
            materials["ALUMINUM"] = engine_weight * 0.15  # 铝合金气缸盖和部件
        elif engine.material == "ALUMINUM":
            materials["STEEL"] = engine_weight * 0.25  # 钢制曲轴和部件
            materials["ALUMINUM"] = engine_weight * 0.60  # 全铝缸体
        elif engine.material == "MAGNESIUM":
            materials["STEEL"] = engine_weight * 0.20
            materials["ALUMINUM"] = engine_weight * 0.50
            # 镁合金在游戏中简化为铝的升级版，不单独建模
        else:
            materials["STEEL"] = engine_weight * 0.50
            materials["ALUMINUM"] = engine_weight * 0.30
        
        # 塑料和橡胶（管路、密封件）
        materials["PLASTIC"] = engine_weight * 0.08
        materials["RUBBER"] = engine_weight * 0.05
        
        # 电子元件（涡轮增压引擎需要更多传感器）
        base_electronics = 2.0  # 基础2kg等效电子元件
        if engine.induction_type in ["TURBO", "TWINTURBO"]:
            base_electronics += 1.5  # 涡轮控制系统
        if engine.valvetrain == "VARIABLE":
            base_electronics += 1.0  # 可变气门正时
        materials["ELECTRONICS"] = base_electronics
        
        return materials
    
    def calculate_chassis_material_requirements(self, chassis: Chassis) -> Dict[str, float]:
        """
        计算生产一套底盘所需的原材料（公斤）
        """
        materials = {}
        
        chassis_weight = chassis.weight_kg
        
        # 根据底盘材料分配
        if chassis.material == "STEEL":
            materials["STEEL"] = chassis_weight * 0.85
            materials["ALUMINUM"] = chassis_weight * 0.05  # 少量铝合金部件
        elif chassis.material == "ALUMINUM":
            materials["STEEL"] = chassis_weight * 0.30  # 钢制加强部件
            materials["ALUMINUM"] = chassis_weight * 0.60
        elif chassis.material == "CARBON":
            # 碳纤维在游戏中简化为高级铝合金+复合材料
            materials["STEEL"] = chassis_weight * 0.15
            materials["ALUMINUM"] = chassis_weight * 0.50
            materials["PLASTIC"] = chassis_weight * 0.25  # 复合材料简化
        else:
            materials["STEEL"] = chassis_weight * 0.75
            materials["ALUMINUM"] = chassis_weight * 0.10
        
        # 橡胶（悬挂衬套、减震器）
        materials["RUBBER"] = chassis_weight * 0.05
        
        # 塑料（内饰固定件）
        materials.setdefault("PLASTIC", 0)
        materials["PLASTIC"] += chassis_weight * 0.03
        
        return materials
    
    def calculate_car_body_material_requirements(self, car_trim: CarTrim) -> Dict[str, float]:
        """
        计算车身所需材料（不含引擎和底盘）
        """
        materials = {}
        
        body_weight = car_trim.body_weight_kg
        
        # 车身主要是钢板或铝板
        materials["STEEL"] = body_weight * 0.60
        materials["ALUMINUM"] = body_weight * 0.10
        
        # 塑料（保险杠、内饰、仪表板）
        materials["PLASTIC"] = body_weight * 0.15
        
        # 玻璃
        materials["GLASS"] = body_weight * 0.08
        
        # 橡胶（密封条、轮胎）
        materials["RUBBER"] = body_weight * 0.05
        
        # 电子元件（灯光、仪表、娱乐系统）
        materials["ELECTRONICS"] = 5.0  # 基础电子设备
        
        return materials
    
    # ========== 零部件生产 ==========
    
    # ========== Weekly production loop ==========

    def process_weekly_production(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """Settle all running production lines for the current game week."""
        from backend.models.game_state import GameState

        game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
        current_week = game_state.current_week if game_state else 1

        lines = self.db.query(ProductionLine).filter(
            ProductionLine.game_id == game_id,
            ProductionLine.status == "RUNNING"
        ).all()
        lines.sort(key=lambda line: (
            0 if line.factory and line.factory.factory_type == FactoryType.COMPONENT.value else 1,
            line.id
        ))

        results: Dict[str, Any] = {
            "status": "ok",
            "week": current_week,
            "lines_processed": 0,
            "factories_processed": 0,
            "components_produced": 0,
            "cars_assembled": 0,
            "materials_used": {},
            "events": [],
            "lines": []
        }
        factory_stats: Dict[int, Dict[str, Any]] = {}

        for line in lines:
            factory = line.factory
            if not factory or not factory.is_operational or not line.current_design_id:
                continue

            company = self.db.query(Company).filter(Company.id == factory.company_id).first()
            car_trim = line.car_trim or self.db.query(CarTrim).filter(
                CarTrim.id == line.current_design_id
            ).first()
            if not car_trim:
                continue

            planned_qty = self._calculate_line_weekly_quantity(
                line, factory, company, car_trim, current_week
            )
            self._add_factory_capacity(factory_stats, factory, planned_qty)

            if factory.factory_type == FactoryType.COMPONENT.value:
                line_result = self._process_component_line(
                    line, factory, company, car_trim, planned_qty, current_turn
                )
                results["components_produced"] += line_result.get("quantity", 0) * 2
            elif factory.factory_type == FactoryType.ASSEMBLY.value:
                line_result = self._process_assembly_line(
                    line, factory, company, car_trim, planned_qty, current_turn
                )
                results["cars_assembled"] += line_result.get("quantity", 0)
            else:
                continue

            self._add_factory_output(factory_stats, factory, line_result.get("quantity", 0))
            results["lines_processed"] += 1
            results["lines"].append(line_result)
            results["events"].extend(line_result.get("events", []))
            self._merge_into(results["materials_used"], line_result.get("materials_used", {}))

        for stats in factory_stats.values():
            factory = stats["factory"]
            capacity = stats["capacity"]
            produced = stats["produced"]
            factory.current_utilization_rate = min(1.0, produced / capacity) if capacity > 0 else 0.0

        results["factories_processed"] = len(factory_stats)
        self.db.commit()
        return results

    def _process_component_line(
        self,
        line: ProductionLine,
        factory: Factory,
        company: Optional[Company],
        car_trim: CarTrim,
        planned_qty: int,
        current_turn: int
    ) -> Dict[str, Any]:
        inventory = self._get_or_create_inventory(factory)
        engine_materials = self.calculate_engine_material_requirements(car_trim.engine)
        chassis_materials = self.calculate_chassis_material_requirements(car_trim.chassis)
        per_unit_materials = self._sum_materials(engine_materials, chassis_materials)
        actual_qty, shortages = self._material_limited_quantity(
            inventory, per_unit_materials, planned_qty
        )

        events: List[Dict[str, Any]] = []
        if shortages:
            events.append(self._production_shortage_event(
                factory, line, car_trim, planned_qty, actual_qty, shortages
            ))

        if actual_qty <= 0:
            return {
                "line_id": line.id,
                "factory_id": factory.id,
                "type": "component",
                "car_trim_id": car_trim.id,
                "planned_quantity": planned_qty,
                "quantity": 0,
                "materials_used": {},
                "events": events
            }

        materials_used = {
            material: amount * actual_qty
            for material, amount in per_unit_materials.items()
        }
        for material, amount in materials_used.items():
            inventory.deduct_material(material, amount)

        inventory.add_component("engine", car_trim.engine_id, actual_qty)
        inventory.add_component("chassis", car_trim.chassis_id, actual_qty)

        labor_cost = factory.labor_cost_per_unit * actual_qty
        chassis_unit_cost = (
            car_trim.chassis.get_effective_manufacturing_cost()
            if hasattr(car_trim.chassis, "get_effective_manufacturing_cost")
            else car_trim.chassis.manufacturing_cost
        )
        unit_cost = float(car_trim.engine.manufacturing_cost or 0.0) + float(chassis_unit_cost or 0.0)
        efficiency_factor = max(0.5, 1.0 - (factory.level - 1) * 0.02)
        total_cost = (unit_cost * actual_qty + labor_cost) * efficiency_factor
        if company:
            company.record_cost("labor", labor_cost)
            company.record_cost("manufacturing", max(0.0, total_cost - labor_cost))

        self._record_component_familiarity(factory, car_trim, actual_qty, current_turn)

        return {
            "line_id": line.id,
            "factory_id": factory.id,
            "type": "component",
            "car_trim_id": car_trim.id,
            "planned_quantity": planned_qty,
            "quantity": actual_qty,
            "components_added": {
                f"engine_{car_trim.engine_id}": actual_qty,
                f"chassis_{car_trim.chassis_id}": actual_qty
            },
            "materials_used": materials_used,
            "total_cost": round(total_cost, 2),
            "events": events
        }

    def _process_assembly_line(
        self,
        line: ProductionLine,
        factory: Factory,
        company: Optional[Company],
        car_trim: CarTrim,
        planned_qty: int,
        current_turn: int
    ) -> Dict[str, Any]:
        inventory = self._get_or_create_inventory(factory)
        body_materials = self.calculate_car_body_material_requirements(car_trim)
        material_qty, material_shortages = self._material_limited_quantity(
            inventory, body_materials, planned_qty
        )
        engine_available = self._company_component_available(
            factory.company_id, factory.game_id, "engine", car_trim.engine_id
        )
        chassis_available = self._company_component_available(
            factory.company_id, factory.game_id, "chassis", car_trim.chassis_id
        )

        actual_qty = min(planned_qty, material_qty, engine_available, chassis_available)
        shortages = list(material_shortages)
        if engine_available < planned_qty:
            shortages.append({
                "kind": "component",
                "item": f"engine_{car_trim.engine_id}",
                "needed": planned_qty,
                "available": engine_available
            })
        if chassis_available < planned_qty:
            shortages.append({
                "kind": "component",
                "item": f"chassis_{car_trim.chassis_id}",
                "needed": planned_qty,
                "available": chassis_available
            })

        events: List[Dict[str, Any]] = []
        if shortages:
            events.append(self._production_shortage_event(
                factory, line, car_trim, planned_qty, actual_qty, shortages
            ))

        if actual_qty <= 0:
            return {
                "line_id": line.id,
                "factory_id": factory.id,
                "type": "assembly",
                "car_trim_id": car_trim.id,
                "planned_quantity": planned_qty,
                "quantity": 0,
                "materials_used": {},
                "events": events
            }

        materials_used = {
            material: amount * actual_qty
            for material, amount in body_materials.items()
        }
        for material, amount in materials_used.items():
            inventory.deduct_material(material, amount)

        logistics_cost = 0.0
        logistics_cost += self._deduct_company_component(
            factory.company_id, factory.game_id, factory, "engine", car_trim.engine_id, actual_qty
        )
        logistics_cost += self._deduct_company_component(
            factory.company_id, factory.game_id, factory, "chassis", car_trim.chassis_id, actual_qty
        )
        inventory.add_car(car_trim.id, actual_qty)

        labor_cost = factory.labor_cost_per_unit * actual_qty
        efficiency_factor = max(0.5, 1.0 - (factory.level - 1) * 0.02)
        total_cost = (car_trim.manufacturing_cost * actual_qty + labor_cost) * efficiency_factor + logistics_cost
        if company:
            company.record_cost("labor", labor_cost)
            company.record_cost("manufacturing", max(0.0, total_cost - labor_cost))
            company.monthly_units_produced += actual_qty

        car_trim.is_in_production = True
        if car_trim.production_start_turn is None:
            car_trim.production_start_turn = current_turn

        quality = self._record_assembly_quality(factory, car_trim, actual_qty, current_turn)

        return {
            "line_id": line.id,
            "factory_id": factory.id,
            "type": "assembly",
            "car_trim_id": car_trim.id,
            "planned_quantity": planned_qty,
            "quantity": actual_qty,
            "components_used": {
                f"engine_{car_trim.engine_id}": actual_qty,
                f"chassis_{car_trim.chassis_id}": actual_qty
            },
            "materials_used": materials_used,
            "total_cost": round(total_cost, 2),
            "logistics_cost": round(logistics_cost, 2),
            "events": events,
            **quality
        }

    def _calculate_line_weekly_quantity(
        self,
        line: ProductionLine,
        factory: Factory,
        company: Optional[Company],
        car_trim: CarTrim,
        current_week: int
    ) -> int:
        base_qty = self._split_monthly_quantity(line.monthly_capacity, current_week)
        if base_qty <= 0 or not factory.is_operational:
            return 0

        factory_efficiency = max(0.0, float(factory.efficiency_score or 0.0) / 100.0)
        company_efficiency = max(0.0, float(company.production_efficiency if company else 1.0))
        familiarity_efficiency = 1.0 + self._get_familiarity_efficiency_bonus(factory, car_trim)
        adjusted = base_qty * factory_efficiency * company_efficiency * familiarity_efficiency
        if adjusted <= 0:
            return 0
        return max(1, int(math.floor(adjusted)))

    @staticmethod
    def _split_monthly_quantity(monthly_quantity: int, current_week: int) -> int:
        monthly_quantity = max(0, int(monthly_quantity or 0))
        current_week = min(4, max(1, int(current_week or 1)))
        base = monthly_quantity // 4
        remainder = monthly_quantity % 4
        return base + (1 if current_week <= remainder else 0)

    def _get_or_create_inventory(self, factory: Factory) -> Inventory:
        inventory = self.db.query(Inventory).filter(Inventory.factory_id == factory.id).first()
        if inventory:
            return inventory

        inventory = Inventory(
            game_id=factory.game_id,
            factory_id=factory.id,
            raw_materials={},
            finished_components={},
            completed_cars={},
            total_inventory_value=0.0
        )
        self.db.add(inventory)
        self.db.flush()
        return inventory

    @staticmethod
    def _sum_materials(*material_sets: Dict[str, float]) -> Dict[str, float]:
        total: Dict[str, float] = {}
        for materials in material_sets:
            for material, amount in materials.items():
                total[material] = total.get(material, 0.0) + float(amount or 0.0)
        return total

    @staticmethod
    def _merge_into(target: Dict[str, float], source: Dict[str, float]) -> None:
        for key, amount in source.items():
            target[key] = target.get(key, 0.0) + float(amount or 0.0)

    def _material_limited_quantity(
        self,
        inventory: Inventory,
        per_unit_materials: Dict[str, float],
        target_qty: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        target_qty = max(0, int(target_qty or 0))
        actual_qty = target_qty
        shortages: List[Dict[str, Any]] = []

        for material, unit_amount in per_unit_materials.items():
            unit_amount = float(unit_amount or 0.0)
            if unit_amount <= 0:
                continue
            needed = unit_amount * target_qty
            available = inventory.get_material_quantity(material)
            if available + 1e-9 < needed:
                possible_qty = int(available // unit_amount)
                actual_qty = min(actual_qty, possible_qty)
                shortages.append({
                    "kind": "material",
                    "item": material,
                    "needed": round(needed, 4),
                    "available": round(available, 4)
                })

        return max(0, actual_qty), shortages

    def _company_component_available(
        self,
        company_id: int,
        game_id: int,
        component_type: str,
        component_id: int
    ) -> int:
        factories = self.db.query(Factory).filter(
            Factory.game_id == game_id,
            Factory.company_id == company_id
        ).all()
        if not factories:
            return 0
        factory_ids = [factory.id for factory in factories]
        inventories = self.db.query(Inventory).filter(Inventory.factory_id.in_(factory_ids)).all()
        return sum(
            inventory.get_component_quantity(component_id, component_type)
            for inventory in inventories
        )

    def _deduct_company_component(
        self,
        company_id: int,
        game_id: int,
        destination_factory: Factory,
        component_type: str,
        component_id: int,
        quantity: int
    ) -> float:
        factories = self.db.query(Factory).filter(
            Factory.game_id == game_id,
            Factory.company_id == company_id
        ).all()
        factories_by_id = {factory.id: factory for factory in factories}
        factory_ids = list(factories_by_id.keys())
        if not factory_ids:
            raise ValueError("No company factories available for component deduction")

        inventories = self.db.query(Inventory).filter(Inventory.factory_id.in_(factory_ids)).all()
        inventories.sort(key=lambda inventory: (
            0 if factories_by_id[inventory.factory_id].region_id == destination_factory.region_id else 1,
            0 if inventory.factory_id == destination_factory.id else 1,
            inventory.factory_id
        ))

        remaining = quantity
        logistics_cost = 0.0
        for inventory in inventories:
            if remaining <= 0:
                break
            available = inventory.get_component_quantity(component_id, component_type)
            if available <= 0:
                continue
            taken = min(remaining, available)
            if not inventory.deduct_component(component_type, component_id, taken):
                continue
            source_factory = factories_by_id[inventory.factory_id]
            if source_factory.id != destination_factory.id:
                logistics_cost += self.auto_logistics(source_factory, destination_factory, taken)
            remaining -= taken

        if remaining > 0:
            raise ValueError(f"Insufficient {component_type}_{component_id} inventory")
        return logistics_cost

    def _get_familiarity_efficiency_bonus(self, factory: Factory, car_trim: CarTrim) -> float:
        from backend.core.production.factory_familiarity import FactoryFamiliaritySystem
        from backend.models.factory_familiarity import FactoryProcessFamiliarity

        checks: List[Tuple[str, str]] = []
        if factory.factory_type == FactoryType.COMPONENT.value:
            checks.append((
                FactoryFamiliaritySystem.get_process_type(car_trim.engine),
                "ENGINE_MANUFACTURING"
            ))
            checks.append((
                FactoryFamiliaritySystem.get_chassis_process_type(car_trim.chassis),
                "CHASSIS_MANUFACTURING"
            ))
        elif factory.factory_type == FactoryType.ASSEMBLY.value:
            checks.append(("ASSEMBLY_GENERAL", "ASSEMBLY"))

        bonus = 0.0
        for process_type, category in checks:
            familiarity = self.db.query(FactoryProcessFamiliarity).filter(
                FactoryProcessFamiliarity.factory_id == factory.id,
                FactoryProcessFamiliarity.process_type == process_type,
                FactoryProcessFamiliarity.category == category
            ).first()
            if familiarity:
                bonus += float(familiarity.production_efficiency_bonus or 0.0)

        return min(0.10, bonus)

    def _record_component_familiarity(
        self,
        factory: Factory,
        car_trim: CarTrim,
        quantity: int,
        current_turn: int
    ) -> None:
        from backend.core.production.factory_familiarity import FactoryFamiliaritySystem

        engine_materials = self.calculate_engine_material_requirements(car_trim.engine)
        engine_process = FactoryFamiliaritySystem.get_process_type(car_trim.engine)
        FactoryFamiliaritySystem.add_process_experience(
            self.db, factory.id, engine_process, "ENGINE_MANUFACTURING",
            quantity, current_turn, factory.game_id
        )
        for material_type, application in FactoryFamiliaritySystem.get_material_types(car_trim.engine):
            kg_processed = engine_materials.get(material_type, 0.0) * quantity
            if kg_processed > 0:
                FactoryFamiliaritySystem.add_material_experience(
                    self.db, factory.id, material_type, application,
                    kg_processed, current_turn, factory.game_id
                )

        chassis_materials = self.calculate_chassis_material_requirements(car_trim.chassis)
        chassis_process = FactoryFamiliaritySystem.get_chassis_process_type(car_trim.chassis)
        FactoryFamiliaritySystem.add_process_experience(
            self.db, factory.id, chassis_process, "CHASSIS_MANUFACTURING",
            quantity, current_turn, factory.game_id
        )
        for material_type, application in FactoryFamiliaritySystem.get_chassis_material_types(car_trim.chassis):
            kg_processed = chassis_materials.get(material_type, 0.0) * quantity
            if kg_processed > 0:
                FactoryFamiliaritySystem.add_material_experience(
                    self.db, factory.id, material_type, application,
                    kg_processed, current_turn, factory.game_id
                )

    def _record_assembly_quality(
        self,
        factory: Factory,
        car_trim: CarTrim,
        quantity: int,
        current_turn: int
    ) -> Dict[str, Any]:
        from backend.core.production.reliability_growth import ReliabilityGrowthSystem
        from backend.core.production.factory_familiarity import FactoryFamiliaritySystem

        production_history = ReliabilityGrowthSystem.get_or_create_production_history(
            self.db, car_trim.company_id, car_trim.id, factory.id, factory.game_id
        )
        factory_reliability_bonus = FactoryFamiliaritySystem.get_factory_reliability_bonus(
            self.db, factory.id, car_trim.engine
        )
        defect_rate = max(0.001, 0.02 * (1.0 - factory_reliability_bonus * 2.0))
        ReliabilityGrowthSystem.update_reliability_from_production(
            production_history, quantity, current_turn, defect_rate
        )
        ReliabilityGrowthSystem.apply_reliability_growth_to_car_trim(
            self.db, car_trim, production_history
        )
        FactoryFamiliaritySystem.add_process_experience(
            self.db, factory.id, "ASSEMBLY_GENERAL", "ASSEMBLY",
            quantity, current_turn, factory.game_id
        )
        return {
            "reliability_multiplier": production_history.current_reliability_multiplier,
            "quality_stage": production_history.quality_ramp_up_stage
        }

    @staticmethod
    def _add_factory_capacity(
        factory_stats: Dict[int, Dict[str, Any]],
        factory: Factory,
        capacity: int
    ) -> None:
        stats = factory_stats.setdefault(
            factory.id,
            {"factory": factory, "capacity": 0, "produced": 0}
        )
        stats["capacity"] += max(0, int(capacity or 0))

    @staticmethod
    def _add_factory_output(
        factory_stats: Dict[int, Dict[str, Any]],
        factory: Factory,
        quantity: int
    ) -> None:
        stats = factory_stats.setdefault(
            factory.id,
            {"factory": factory, "capacity": 0, "produced": 0}
        )
        stats["produced"] += max(0, int(quantity or 0))

    @staticmethod
    def _production_shortage_event(
        factory: Factory,
        line: ProductionLine,
        car_trim: CarTrim,
        planned_qty: int,
        actual_qty: int,
        shortages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        status = "停产" if actual_qty <= 0 else "降产"
        return {
            "event_type": "PRODUCTION",
            "severity": "WARNING",
            "related_company_id": factory.company_id,
            "message": (
                f"{factory.name} / {line.name or ('Line ' + str(line.id))} "
                f"因库存不足{status}: 计划 {planned_qty}, 实产 {actual_qty}"
            ),
            "extra_data": {
                "factory_id": factory.id,
                "line_id": line.id,
                "car_trim_id": car_trim.id,
                "planned_quantity": planned_qty,
                "actual_quantity": actual_qty,
                "shortages": shortages
            }
        }

    def produce_component(
        self,
        factory: Factory,
        component_type: str,
        component_id: int,
        quantity: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        在零部件工厂生产组件（引擎、底盘等）
        
        Args:
            factory: 工厂对象
            component_type: 组件类型 ("engine", "chassis")
            component_id: 组件ID
            quantity: 生产数量
        
        Returns:
            (成功/失败, 消息, 生产详情)
        """
        # 1. 检查工厂类型
        if factory.factory_type != FactoryType.COMPONENT.value:
            return False, f"工厂 {factory.name} 不是零部件工厂，无法生产组件", {}
        
        if not factory.is_operational:
            return False, f"工厂 {factory.name} 未运营", {}
        
        # 2. 获取组件信息
        if component_type == "engine":
            component = self.db.query(Engine).filter(Engine.id == component_id).first()
            if not component:
                return False, f"引擎ID {component_id} 不存在", {}
            material_requirements = self.calculate_engine_material_requirements(component)
            unit_cost = component.manufacturing_cost
        elif component_type == "chassis":
            component = self.db.query(Chassis).filter(Chassis.id == component_id).first()
            if not component:
                return False, f"底盘ID {component_id} 不存在", {}
            material_requirements = self.calculate_chassis_material_requirements(component)
            unit_cost = component.manufacturing_cost
        else:
            return False, f"不支持的组件类型: {component_type}", {}
        
        # 3. 检查技术等级
        component_tech_level = getattr(component, 'tech_level', 1)
        if factory.tech_level < component_tech_level:
            return False, f"工厂技术等级 {factory.tech_level} 不足，无法生产技术等级 {component_tech_level} 的组件", {}
        
        # 4. 检查产能
        effective_capacity = factory.get_effective_capacity()
        if quantity > effective_capacity:
            return False, f"工厂月产能 {effective_capacity} 不足以生产 {quantity} 件", {}
        
        # 5. 获取或创建库存记录
        inventory = self.db.query(Inventory).filter(
            Inventory.factory_id == factory.id
        ).first()
        
        if not inventory:
            inventory = Inventory(
                game_id=factory.game_id,
                factory_id=factory.id,
                raw_materials={},
                finished_components={},
                completed_cars={},
                total_inventory_value=0.0
            )
            self.db.add(inventory)
            self.db.flush()
        
        # 6. 检查并扣减原材料
        total_materials_needed = {}
        for material, unit_amount in material_requirements.items():
            total_materials_needed[material] = unit_amount * quantity
        
        materials_shortage = []
        for material, needed_amount in total_materials_needed.items():
            available = inventory.get_material_quantity(material)
            if available < needed_amount:
                materials_shortage.append(
                    f"{material}: 需要 {needed_amount:.2f}kg, 库存 {available:.2f}kg"
                )
        
        if materials_shortage:
            return False, f"原材料不足: {', '.join(materials_shortage)}", {}

        # 7. 计算并检查现金成本（制造转换成本 + 劳动力）
        labor_cost = factory.labor_cost_per_unit * quantity
        efficiency_factor = 1.0 - (factory.level - 1) * 0.02
        total_cost = (unit_cost * quantity + labor_cost) * efficiency_factor

        company = self.db.query(Company).filter(Company.id == component.company_id).first()
        if company and company.cash < total_cost:
            return False, (
                f"资金不足: 需要 ${total_cost:,.0f}, "
                f"当前现金 ${company.cash:,.0f}"
            ), {}
        
        # 8. 扣减原材料
        for material, amount in total_materials_needed.items():
            inventory.deduct_material(material, amount)
        
        # 9. 增加零部件库存
        inventory.add_component(component_type, component_id, quantity)
        
        # 10. 记录财务成本
        if company:
            company.record_cost("labor", labor_cost)
            company.record_cost("manufacturing", max(0.0, total_cost - labor_cost))
        
        # 11. 更新工厂利用率
        factory.current_utilization_rate = min(1.0, quantity / effective_capacity)
        
        # 12. 添加工厂工艺和材料熟悉度经验
        from backend.core.production.factory_familiarity import FactoryFamiliaritySystem
        from backend.models.game_state import GameState
        
        game_state = self.db.query(GameState).filter(GameState.id == factory.game_id).first()
        current_turn = game_state.turn_number if game_state else 0
        
        if component_type == "engine":
            # 添加工艺经验
            process_type = FactoryFamiliaritySystem.get_process_type(component)
            FactoryFamiliaritySystem.add_process_experience(
                self.db, factory.id, process_type, "ENGINE_MANUFACTURING",
                quantity, current_turn, factory.game_id
            )
            
            # 添加材料经验
            material_types = FactoryFamiliaritySystem.get_material_types(component)
            for material_type, application in material_types:
                kg_processed = material_requirements.get(material_type, 0.0) * quantity
                if kg_processed > 0:
                    FactoryFamiliaritySystem.add_material_experience(
                        self.db, factory.id, material_type, application,
                        kg_processed, current_turn, factory.game_id
                    )
        elif component_type == "chassis":
            # 添加工艺经验
            process_type = FactoryFamiliaritySystem.get_chassis_process_type(component)
            FactoryFamiliaritySystem.add_process_experience(
                self.db, factory.id, process_type, "CHASSIS_MANUFACTURING",
                quantity, current_turn, factory.game_id
            )
            
            # 添加材料经验
            material_types = FactoryFamiliaritySystem.get_chassis_material_types(component)
            for material_type, application in material_types:
                kg_processed = material_requirements.get(material_type, 0.0) * quantity
                if kg_processed > 0:
                    FactoryFamiliaritySystem.add_material_experience(
                        self.db, factory.id, material_type, application,
                        kg_processed, current_turn, factory.game_id
                    )
        
        # 13. 提交更改
        self.db.commit()
        
        logger.info(
            f"工厂 {factory.name} 生产了 {quantity} 件 {component_type} (ID: {component_id}), "
            f"总成本: ${total_cost:,.2f}"
        )
        
        return True, "生产成功", {
            "component_type": component_type,
            "component_id": component_id,
            "quantity": quantity,
            "materials_used": total_materials_needed,
            "total_cost": round(total_cost, 2),
            "factory_utilization": round(factory.current_utilization_rate * 100, 1)
        }
    
    # ========== 整车装配 ==========
    
    def assemble_car(
        self,
        assembly_factory: Factory,
        car_trim_id: int,
        quantity: int,
        source_component_factory_id: Optional[int] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        在装配厂组装完整车辆
        
        Args:
            assembly_factory: 装配厂对象
            car_trim_id: 车型配置ID
            quantity: 装配数量
            source_component_factory_id: 零部件来源工厂ID（如为None则从本厂库存取）
        
        Returns:
            (成功/失败, 消息, 装配详情)
        
        注意：
        - 简化设计：暂不支持从B2B市场采购零部件（Step 3会添加）
        - 跨工厂物流：如果source_component_factory_id指定，会计算运输成本
        """
        # 1. 检查工厂类型
        if assembly_factory.factory_type != FactoryType.ASSEMBLY.value:
            return False, f"工厂 {assembly_factory.name} 不是装配厂，无法装配车辆", {}
        
        if not assembly_factory.is_operational:
            return False, f"工厂 {assembly_factory.name} 未运营", {}
        
        # 2. 获取车型配置
        car_trim = self.db.query(CarTrim).filter(CarTrim.id == car_trim_id).first()
        if not car_trim:
            return False, f"车型配置ID {car_trim_id} 不存在", {}
        
        # 3. 检查产能
        effective_capacity = assembly_factory.get_effective_capacity()
        if quantity > effective_capacity:
            return False, f"装配厂月产能 {effective_capacity} 不足以装配 {quantity} 辆", {}
        
        # 4. 获取装配厂库存
        assembly_inventory = self.db.query(Inventory).filter(
            Inventory.factory_id == assembly_factory.id
        ).first()
        
        if not assembly_inventory:
            assembly_inventory = Inventory(
                game_id=assembly_factory.game_id,
                factory_id=assembly_factory.id,
                raw_materials={},
                finished_components={},
                completed_cars={},
                total_inventory_value=0.0
            )
            self.db.add(assembly_inventory)
            self.db.flush()
        
        # 5. 确定零部件来源
        logistics_cost = 0.0
        if source_component_factory_id and source_component_factory_id != assembly_factory.id:
            # 跨工厂运输
            source_factory = self.db.query(Factory).filter(
                Factory.id == source_component_factory_id
            ).first()
            
            if not source_factory:
                return False, f"零部件来源工厂ID {source_component_factory_id} 不存在", {}
            
            source_inventory = self.db.query(Inventory).filter(
                Inventory.factory_id == source_factory.id
            ).first()
            
            if not source_inventory:
                return False, f"零部件来源工厂无库存记录", {}
            
            # 计算物流成本
            logistics_cost = self.auto_logistics(
                source_factory, assembly_factory, quantity
            )
            
            component_inventory = source_inventory
        else:
            # 使用本厂库存（假设是集成工厂或已转运）
            component_inventory = assembly_inventory
        
        # 6. 检查零部件库存
        engine_available = component_inventory.get_component_quantity(car_trim.engine_id, "engine")
        chassis_available = component_inventory.get_component_quantity(car_trim.chassis_id, "chassis")
        # 简化：暂不考虑变速箱等其他零部件，只检查引擎
        
        if engine_available < quantity:
            return False, (
                f"引擎库存不足: 需要 {quantity} 台, "
                f"库存 {engine_available} 台 (引擎ID: {car_trim.engine_id})"
            ), {}
        
        # 7. 检查车身材料（装配厂需要车身材料）
        if chassis_available < quantity:
            return False, (
                f"搴曠洏搴撳瓨涓嶈冻: 闇€瑕?{quantity} 濂? "
                f"搴撳瓨 {chassis_available} 濂?(搴曠洏ID: {car_trim.chassis_id})"
            ), {}

        body_materials_needed = self.calculate_car_body_material_requirements(car_trim)
        total_body_materials = {}
        for material, unit_amount in body_materials_needed.items():
            total_body_materials[material] = unit_amount * quantity
        
        materials_shortage = []
        for material, needed_amount in total_body_materials.items():
            available = assembly_inventory.get_material_quantity(material)
            if available < needed_amount:
                materials_shortage.append(
                    f"{material}: 需要 {needed_amount:.2f}kg, 库存 {available:.2f}kg"
                )
        
        if materials_shortage:
            return False, f"车身材料不足: {', '.join(materials_shortage)}", {}
        
        # 8. 计算并检查现金成本
        labor_cost = assembly_factory.labor_cost_per_unit * quantity
        efficiency_factor = 1.0 - (assembly_factory.level - 1) * 0.02
        total_cost = (car_trim.manufacturing_cost * quantity + labor_cost) * efficiency_factor + logistics_cost

        company = self.db.query(Company).filter(Company.id == car_trim.company_id).first()
        if company and company.cash < total_cost:
            return False, (
                f"资金不足: 需要 ${total_cost:,.0f}, "
                f"当前现金 ${company.cash:,.0f}"
            ), {}

        # 9. 扣减零部件和材料
        engine_success = component_inventory.deduct_component("engine", car_trim.engine_id, quantity)
        chassis_success = component_inventory.deduct_component("chassis", car_trim.chassis_id, quantity)
        if not engine_success or not chassis_success:
            return False, "扣减引擎库存失败（并发冲突？）", {}
        
        for material, amount in total_body_materials.items():
            assembly_inventory.deduct_material(material, amount)
        
        # 10. 增加成品车库存
        assembly_inventory.add_car(car_trim_id, quantity)
        
        # 11. 记录财务成本
        if company:
            company.record_cost("labor", labor_cost)
            company.record_cost("manufacturing", max(0.0, total_cost - labor_cost))
            company.monthly_units_produced += quantity
        
        # 12. 更新工厂利用率
        assembly_factory.current_utilization_rate = min(1.0, quantity / effective_capacity)
        
        # 13. 更新生产历史和可靠性增长
        from backend.core.production.reliability_growth import ReliabilityGrowthSystem
        from backend.core.production.factory_familiarity import FactoryFamiliaritySystem
        from backend.models.game_state import GameState
        
        game_state = self.db.query(GameState).filter(GameState.id == assembly_factory.game_id).first()
        current_turn = game_state.turn_number if game_state else 0
        
        # 获取或创建生产历史
        production_history = ReliabilityGrowthSystem.get_or_create_production_history(
            self.db, car_trim.company_id, car_trim_id, assembly_factory.id, assembly_factory.game_id
        )
        
        # 更新生产历史（计算缺陷率，考虑工厂熟悉度）
        defect_rate = 0.02  # 基础缺陷率
        # 应用工厂熟悉度加成（降低缺陷率）
        factory_reliability_bonus = FactoryFamiliaritySystem.get_factory_reliability_bonus(
            self.db, assembly_factory.id, car_trim.engine
        )
        defect_rate = max(0.001, defect_rate * (1.0 - factory_reliability_bonus * 2.0))  # 熟悉度降低缺陷率
        
        ReliabilityGrowthSystem.update_reliability_from_production(
            production_history, quantity, current_turn, defect_rate
        )
        
        # 应用可靠性增长到车型
        ReliabilityGrowthSystem.apply_reliability_growth_to_car_trim(
            self.db, car_trim, production_history
        )
        
        # 添加装配工艺经验
        FactoryFamiliaritySystem.add_process_experience(
            self.db, assembly_factory.id, "ASSEMBLY_GENERAL", "ASSEMBLY",
            quantity, current_turn, assembly_factory.game_id
        )
        
        # 13. 提交更改
        self.db.commit()
        
        logger.info(
            f"装配厂 {assembly_factory.name} 装配了 {quantity} 辆 {car_trim.name} "
            f"(Trim ID: {car_trim_id}), 总成本: ${total_cost:,.2f}, "
            f"可靠性倍数: {production_history.current_reliability_multiplier:.3f}"
        )
        
        return True, "装配成功", {
            "car_trim_id": car_trim_id,
            "car_name": car_trim.name,
            "quantity": quantity,
            "components_used": {
                f"engine_{car_trim.engine_id}": quantity,
                f"chassis_{car_trim.chassis_id}": quantity
            },
            "body_materials_used": total_body_materials,
            "total_cost": round(total_cost, 2),
            "logistics_cost": round(logistics_cost, 2),
            "factory_utilization": round(assembly_factory.current_utilization_rate * 100, 1),
            "reliability_multiplier": production_history.current_reliability_multiplier,
            "quality_stage": production_history.quality_ramp_up_stage
        }
    
    # ========== 物流计算 ==========
    
    def auto_logistics(
        self,
        source_factory: Factory,
        destination_factory: Factory,
        quantity: int
    ) -> float:
        """
        自动物流成本计算（简化）
        
        MVP简化：
        - 假设同地区运输成本低
        - 跨地区运输成本与距离和数量成正比
        - 不需要手动规划路线
        
        Args:
            source_factory: 发货工厂
            destination_factory: 收货工厂
            quantity: 运输数量
        
        Returns:
            物流成本（游戏币）
        """
        # 1. 检查是否同地区
        if source_factory.region_id == destination_factory.region_id:
            # 同地区：低成本，假设每件 $10
            cost_per_unit = 10.0
            logger.debug(
                f"同地区物流: {source_factory.name} -> {destination_factory.name}, "
                f"数量: {quantity}, 成本: ${cost_per_unit * quantity:,.2f}"
            )
            return cost_per_unit * quantity
        
        # 2. 跨地区：成本更高
        # 简化：假设跨地区固定成本 + 每件成本
        base_cost = 5000.0  # 跨地区固定物流费用
        cost_per_unit = 50.0  # 每件物流成本
        
        total_cost = base_cost + cost_per_unit * quantity
        
        logger.debug(
            f"跨地区物流: {source_factory.name} (Region {source_factory.region_id}) -> "
            f"{destination_factory.name} (Region {destination_factory.region_id}), "
            f"数量: {quantity}, 成本: ${total_cost:,.2f}"
        )
        
        return total_cost
    
    # ========== 采购原材料 ==========
    
    def purchase_materials(
        self,
        factory: Factory,
        material_type: str,
        quantity_kg: float,
        region_id: Optional[int] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        为工厂采购原材料
        
        Args:
            factory: 工厂对象
            material_type: 材料类型（STEEL, ALUMINUM等）
            quantity_kg: 采购数量（公斤）
            region_id: 采购地区（如为None则使用工厂所在地区）
        
        Returns:
            (成功/失败, 消息, 采购详情)
        """
        # 1. 确定采购地区
        purchase_region_id = region_id if region_id else factory.region_id
        
        # 2. 获取材料市场价格
        material_market = self.db.query(MaterialMarket).filter(
            MaterialMarket.game_id == factory.game_id,
            MaterialMarket.region_id == purchase_region_id,
            MaterialMarket.material_type == material_type.upper()
        ).first()
        
        if not material_market:
            # 尝试全球市场价格
            material_market = self.db.query(MaterialMarket).filter(
                MaterialMarket.game_id == factory.game_id,
                MaterialMarket.region_id.is_(None),
                MaterialMarket.material_type == material_type.upper()
            ).first()
        
        if not material_market:
            return False, f"找不到 {material_type} 的市场价格数据", {}
        
        # 3. 计算成本
        unit_price = material_market.current_price_per_kg
        total_cost = unit_price * quantity_kg

        company = self.db.query(Company).filter(Company.id == factory.company_id).first()
        if company and company.cash < total_cost:
            return False, (
                f"资金不足: 需要 ${total_cost:,.0f}, "
                f"当前现金 ${company.cash:,.0f}"
            ), {}
        
        # 4. 获取或创建库存
        inventory = self.db.query(Inventory).filter(
            Inventory.factory_id == factory.id
        ).first()
        
        if not inventory:
            inventory = Inventory(
                game_id=factory.game_id,
                factory_id=factory.id,
                raw_materials={},
                finished_components={},
                completed_cars={},
                total_inventory_value=0.0
            )
            self.db.add(inventory)
            self.db.flush()
        
        # 5. 增加库存
        inventory.add_material(material_type.upper(), quantity_kg)
        
        # 6. 更新库存价值
        inventory.total_inventory_value += total_cost

        if company:
            company.record_cost("materials", total_cost)
        
        # 7. 提交
        self.db.commit()
        
        logger.info(
            f"工厂 {factory.name} 采购了 {quantity_kg:.2f}kg {material_type}, "
            f"单价: ${unit_price:.2f}/kg, 总成本: ${total_cost:,.2f}"
        )
        
        return True, "采购成功", {
            "material_type": material_type.upper(),
            "quantity_kg": quantity_kg,
            "unit_price": round(unit_price, 2),
            "total_cost": round(total_cost, 2),
            "new_inventory": inventory.get_material_quantity(material_type.upper())
        }


__all__ = ["ProductionManager"]
