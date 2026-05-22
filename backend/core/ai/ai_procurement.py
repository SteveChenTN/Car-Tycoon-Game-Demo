"""
AI采购代理 - 自动化采购策略执行

核心功能：
- 为AI公司（或玩家委托）自动执行原材料采购
- 实现多种采购策略（准时制、囤积型、平衡型）
- 价格趋势分析和决策
- 防止采购决策过于"完美"（增加真实性）

设计哲学：
- AI不应该有"完美预知"能力
- 策略有优缺点，囤积型可能被套牢
- 准时制在供应短缺时会遭受损失
"""
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import random

from backend.models.production import (
    Factory, MaterialMarket, Inventory,
    MaterialType, ProcurementPolicy
)
from backend.core.production.production_manager import ProductionManager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AIProcurementDelegate:
    """
    AI采购代理 - 执行自动化采购策略
    
    用途：
    1. AI公司使用此类自动管理原材料采购
    2. 玩家可以选择"委托AI"来简化微观管理
    3. 不同AI公司有不同的采购风格（个性化）
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.production_manager = ProductionManager(db)
    
    # ========== 策略执行 ==========
    
    def run_procurement_policy(
        self,
        factory: Factory,
        policy_type: str,
        planned_production: Dict[str, int],
        game_turn: int
    ) -> Tuple[bool, str, List[Dict]]:
        """
        为工厂执行采购策略
        
        Args:
            factory: 工厂对象
            policy_type: 策略类型（JUST_IN_TIME/HOARDER/BALANCED）
            planned_production: 计划生产量 {"ENGINE_123": 500, ...}
            game_turn: 当前游戏回合
        
        Returns:
            (成功/失败, 消息, 采购详情列表)
        """
        try:
            policy = ProcurementPolicy[policy_type.upper()]
        except KeyError:
            return False, f"未知的采购策略: {policy_type}", []
        
        if policy == ProcurementPolicy.JUST_IN_TIME:
            return self._execute_just_in_time(factory, planned_production, game_turn)
        elif policy == ProcurementPolicy.HOARDER:
            return self._execute_hoarder(factory, planned_production, game_turn)
        elif policy == ProcurementPolicy.BALANCED:
            return self._execute_balanced(factory, planned_production, game_turn)
        else:
            return False, "策略未实现", []
    
    # ========== 准时制策略（Just-In-Time） ==========
    
    def _execute_just_in_time(
        self,
        factory: Factory,
        planned_production: Dict[str, int],
        game_turn: int
    ) -> Tuple[bool, str, List[Dict]]:
        """
        准时制采购策略
        
        特点：
        - 只采购本周期需要的原材料（零库存）
        - 优点：资金占用少
        - 缺点：价格波动风险高，供应短缺时停产
        
        简化：假设1个回合 = 1周，计算1周的材料需求
        """
        logger.info(f"执行准时制采购策略 - 工厂: {factory.name}")
        
        # 1. 计算材料需求
        total_material_needs = self._calculate_total_material_needs(
            planned_production, factory
        )
        
        if not total_material_needs:
            return True, "无需采购（无生产计划或计算失败）", []
        
        # 2. 获取当前库存
        inventory = self._get_or_create_inventory(factory)
        
        # 3. 准时制：只采购缺口部分（不囤积）
        purchases = []
        for material_type, needed_qty in total_material_needs.items():
            current_stock = inventory.get_material_quantity(material_type)
            
            # JIT：库存不足才买，且只买刚好够的量
            shortage = needed_qty - current_stock
            if shortage > 0:
                # 增加5%安全边际（避免计算误差导致缺料）
                purchase_qty = shortage * 1.05
                
                success, msg, details = self.production_manager.purchase_materials(
                    factory, material_type, purchase_qty, factory.region_id
                )
                
                if success:
                    purchases.append(details)
                else:
                    logger.warning(f"准时制采购失败: {msg}")
        
        summary = f"准时制采购完成，共采购 {len(purchases)} 种材料"
        return True, summary, purchases
    
    # ========== 囤积型策略（Hoarder） ==========
    
    def _execute_hoarder(
        self,
        factory: Factory,
        planned_production: Dict[str, int],
        game_turn: int
    ) -> Tuple[bool, str, List[Dict]]:
        """
        囤积型采购策略
        
        特点：
        - 当价格低于历史均值10%时大量采购
        - 维持高库存水平（4-8周用量）
        - 优点：抵御价格上涨和供应短缺
        - 缺点：资金占用大，价格下跌时被套牢
        """
        logger.info(f"执行囤积型采购策略 - 工厂: {factory.name}")
        
        # 1. 计算月度材料需求（假设4周 = 1月）
        total_material_needs = self._calculate_total_material_needs(
            planned_production, factory
        )
        
        if not total_material_needs:
            return True, "无需采购", []
        
        # 2. 获取库存
        inventory = self._get_or_create_inventory(factory)
        
        # 3. 囤积策略：检查价格并决定采购量
        purchases = []
        for material_type, weekly_need in total_material_needs.items():
            current_stock = inventory.get_material_quantity(material_type)
            
            # 获取材料市场信息
            material_market = self._get_material_market(
                factory.game_id, factory.region_id, material_type
            )
            
            if not material_market:
                logger.warning(f"找不到 {material_type} 市场数据，跳过")
                continue
            
            # 计算目标库存（4-8周用量，取决于价格）
            if material_market.is_below_average(threshold=0.90):
                # 价格便宜：囤积8周用量
                target_stock = weekly_need * 8
                logger.info(f"{material_type} 价格低于均值10%，准备囤积")
            elif material_market.is_below_average(threshold=0.95):
                # 价格略低：囤积6周用量
                target_stock = weekly_need * 6
            else:
                # 价格正常或偏高：维持4周最低库存
                target_stock = weekly_need * 4
            
            # 采购至目标库存
            shortage = target_stock - current_stock
            if shortage > 0:
                # 囤积型：一次性采购到目标水平
                success, msg, details = self.production_manager.purchase_materials(
                    factory, material_type, shortage, factory.region_id
                )
                
                if success:
                    purchases.append(details)
                    logger.info(
                        f"囤积采购: {material_type} {shortage:.2f}kg, "
                        f"价格: ${material_market.current_price_per_kg:.2f}/kg"
                    )
                else:
                    logger.warning(f"囤积采购失败: {msg}")
        
        summary = f"囤积型采购完成，共采购 {len(purchases)} 种材料"
        return True, summary, purchases
    
    # ========== 平衡型策略（Balanced） ==========
    
    def _execute_balanced(
        self,
        factory: Factory,
        planned_production: Dict[str, int],
        game_turn: int
    ) -> Tuple[bool, str, List[Dict]]:
        """
        平衡型采购策略
        
        特点：
        - 维持2周安全库存
        - 价格低时适度增加库存（不过度囤积）
        - 供应紧张时优先采购
        - 平衡资金占用和风险
        """
        logger.info(f"执行平衡型采购策略 - 工厂: {factory.name}")
        
        # 1. 计算材料需求
        total_material_needs = self._calculate_total_material_needs(
            planned_production, factory
        )
        
        if not total_material_needs:
            return True, "无需采购", []
        
        # 2. 获取库存
        inventory = self._get_or_create_inventory(factory)
        
        # 3. 平衡策略：维持2周库存，价格低时增至3周
        purchases = []
        for material_type, weekly_need in total_material_needs.items():
            current_stock = inventory.get_material_quantity(material_type)
            
            # 获取市场信息
            material_market = self._get_material_market(
                factory.game_id, factory.region_id, material_type
            )
            
            if not material_market:
                continue
            
            # 基础目标：2周库存
            base_target = weekly_need * 2
            
            # 价格低于均值5%：增至3周
            if material_market.is_below_average(threshold=0.95):
                target_stock = weekly_need * 3
            # 供应紧张（supply_level < 0.8）：增至2.5周
            elif material_market.supply_level < 0.8:
                target_stock = weekly_need * 2.5
            else:
                target_stock = base_target
            
            # 采购至目标库存
            shortage = target_stock - current_stock
            if shortage > 0:
                success, msg, details = self.production_manager.purchase_materials(
                    factory, material_type, shortage, factory.region_id
                )
                
                if success:
                    purchases.append(details)
        
        summary = f"平衡型采购完成，共采购 {len(purchases)} 种材料"
        return True, summary, purchases
    
    # ========== 辅助方法 ==========
    
    def _calculate_total_material_needs(
        self,
        planned_production: Dict[str, int],
        factory: Factory
    ) -> Dict[str, float]:
        """
        计算总材料需求
        
        Args:
            planned_production: {"ENGINE_123": 500, "CHASSIS_456": 300}
            factory: 工厂对象
        
        Returns:
            {"STEEL": 50000.0, "ALUMINUM": 10000.0, ...}
        """
        total_needs: Dict[str, float] = {}
        
        # 简化：这里假设planned_production的key格式为 "TYPE_ID"
        # 实际使用时需要解析并查询具体的Engine/Chassis对象
        
        # 占位实现：返回基础材料需求（实际应该从数据库查询组件详情）
        # TODO: 完善此方法，根据planned_production查询实际组件并计算材料
        
        # 临时简化：假设每件产品需要标准材料
        if not planned_production:
            return {}
        
        total_qty = sum(planned_production.values())
        
        # 临时假设的材料需求（每件产品）
        standard_material_per_unit = {
            "STEEL": 100.0,
            "ALUMINUM": 30.0,
            "PLASTIC": 15.0,
            "ELECTRONICS": 2.0,
            "RUBBER": 5.0
        }
        
        for material, unit_need in standard_material_per_unit.items():
            total_needs[material] = unit_need * total_qty
        
        return total_needs
    
    def _get_or_create_inventory(self, factory: Factory) -> Inventory:
        """获取或创建工厂库存记录"""
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
        
        return inventory
    
    def _get_material_market(
        self,
        game_id: int,
        region_id: int,
        material_type: str
    ) -> Optional[MaterialMarket]:
        """获取材料市场数据（优先地区市场，其次全球市场）"""
        # 优先查询地区市场
        market = self.db.query(MaterialMarket).filter(
            MaterialMarket.game_id == game_id,
            MaterialMarket.region_id == region_id,
            MaterialMarket.material_type == material_type.upper()
        ).first()
        
        if market:
            return market
        
        # 全球市场
        market = self.db.query(MaterialMarket).filter(
            MaterialMarket.game_id == game_id,
            MaterialMarket.region_id.is_(None),
            MaterialMarket.material_type == material_type.upper()
        ).first()
        
        return market
    
    # ========== 策略推荐 ==========
    
    @staticmethod
    def recommend_policy_for_company(
        company_personality: str,
        cash_position: float,
        market_volatility: float
    ) -> ProcurementPolicy:
        """
        为AI公司推荐采购策略（基于公司个性）
        
        Args:
            company_personality: 公司性格（AGGRESSIVE/CONSERVATIVE/OPPORTUNISTIC）
            cash_position: 现金状况（高/低）
            market_volatility: 市场波动率
        
        Returns:
            推荐的采购策略
        """
        personality = company_personality.upper()
        
        # 激进型公司：现金充足时囤积，否则准时制
        if personality == "AGGRESSIVE":
            return ProcurementPolicy.HOARDER if cash_position > 1000000 else ProcurementPolicy.JUST_IN_TIME
        
        # 保守型公司：总是平衡
        elif personality == "CONSERVATIVE":
            return ProcurementPolicy.BALANCED
        
        # 机会主义：根据市场波动决策
        elif personality == "OPPORTUNISTIC":
            if market_volatility > 0.2:
                return ProcurementPolicy.HOARDER  # 高波动时囤积
            else:
                return ProcurementPolicy.JUST_IN_TIME
        
        # 默认：平衡型
        else:
            return ProcurementPolicy.BALANCED
    
    # ========== 批量执行（回合结算时调用） ==========
    
    def execute_all_ai_procurement(
        self,
        game_id: int,
        current_turn: int,
        ai_company_policies: Dict[int, str]
    ) -> Dict[int, List[Dict]]:
        """
        为所有AI公司执行采购（回合结算时批量调用）
        
        Args:
            game_id: 游戏ID
            current_turn: 当前回合
            ai_company_policies: {company_id: policy_type, ...}
        
        Returns:
            {company_id: [采购详情], ...}
        """
        results = {}
        
        # 获取所有AI公司的工厂
        for company_id, policy in ai_company_policies.items():
            company_factories = self.db.query(Factory).filter(
                Factory.game_id == game_id,
                Factory.company_id == company_id,
                Factory.is_operational == True
            ).all()
            
            company_purchases = []
            for factory in company_factories:
                # 简化：假设每个工厂都有标准生产计划
                # TODO: 从公司的生产计划表中读取实际计划
                planned_production = self._generate_mock_production_plan(factory)
                
                success, msg, purchases = self.run_procurement_policy(
                    factory, policy, planned_production, current_turn
                )
                
                if success:
                    company_purchases.extend(purchases)
            
            results[company_id] = company_purchases
        
        logger.info(
            f"回合 {current_turn}: 为 {len(ai_company_policies)} 家AI公司执行了采购策略"
        )
        
        return results
    
    def _generate_mock_production_plan(self, factory: Factory) -> Dict[str, int]:
        """
        生成模拟生产计划（临时实现）
        
        TODO: 实际应该从公司的生产计划系统中读取
        """
        # 简化：假设工厂利用80%产能
        planned_qty = int(factory.capacity_units_per_month * 0.8)
        
        if planned_qty > 0:
            return {"MOCK_PRODUCT_1": planned_qty}
        else:
            return {}


__all__ = ["AIProcurementDelegate"]


