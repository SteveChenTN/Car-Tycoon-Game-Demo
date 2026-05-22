"""
事件系统业务逻辑
管理事件触发、效果应用、新闻生成
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Callable
import logging
import random

from backend.models.events import GameEvent, EventType, EventSeverity, EventStatus, EventTemplate
from backend.models.company import Company
from backend.models.game_state import GameState
from backend.models.region import Region

logger = logging.getLogger(__name__)


class EventLogic:
    """事件系统核心逻辑"""
    
    def __init__(self, db: Session):
        """
        初始化事件逻辑
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self._event_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """注册默认事件处理器"""
        self._event_handlers["cash_change"] = self._handle_cash_change
        self._event_handlers["reputation_change"] = self._handle_reputation_change
        self._event_handlers["prestige_change"] = self._handle_prestige_change
        self._event_handlers["tech_level_change"] = self._handle_tech_level_change
        self._event_handlers["employee_morale_change"] = self._handle_morale_change
    
    def trigger_event(
        self,
        game_id: int,
        event_type: EventType,
        title: str,
        description: str,
        severity: EventSeverity = EventSeverity.INFO,
        effects: Optional[Dict[str, Any]] = None,
        affected_company_id: Optional[int] = None,
        affected_region_code: Optional[str] = None,
        requires_player_action: bool = False,
        player_choices: Optional[List[Dict[str, Any]]] = None,
        news_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        触发一个游戏事件
        
        Args:
            game_id: 游戏ID
            event_type: 事件类型
            title: 事件标题
            description: 事件描述
            severity: 严重程度
            effects: 事件效果（JSON格式）
            affected_company_id: 受影响公司ID（可选）
            affected_region_code: 受影响地区（可选）
            requires_player_action: 是否需要玩家响应
            player_choices: 玩家选项列表（可选）
            news_category: 新闻分类（可选）
        
        Returns:
            事件创建结果
        """
        try:
            # 获取游戏状态
            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
            if not game_state:
                return {"success": False, "error": "Game not found"}
            
            # 创建事件
            event = GameEvent(
                game_id=game_id,
                event_type=event_type,
                severity=severity,
                status=EventStatus.TRIGGERED,
                title=title,
                description=description,
                affected_company_id=affected_company_id,
                affected_region_code=affected_region_code,
                triggered_turn=game_state.turn_number,
                requires_player_action=requires_player_action,
                news_category=news_category,
                is_public=True
            )
            
            # 设置效果
            if effects:
                event.set_effects(effects)
            
            # 设置玩家选项
            if player_choices:
                event.set_player_choices(player_choices)
            
            self.db.add(event)
            
            # 如果不需要玩家响应，立即应用效果
            if not requires_player_action and effects:
                event.status = EventStatus.ACTIVE
                self._apply_event_effects(event)
                event.status = EventStatus.RESOLVED
            
            self.db.commit()
            self.db.refresh(event)
            
            logger.info(
                f"事件触发: [{event_type.value}] {title} "
                f"(severity={severity.value}, game={game_id}, turn={game_state.turn_number})"
            )
            
            return {
                "success": True,
                "event_id": event.id,
                "requires_action": requires_player_action
            }
            
        except Exception as e:
            logger.error(f"触发事件失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def process_player_choice(
        self,
        event_id: int,
        choice_id: str
    ) -> Dict[str, Any]:
        """
        处理玩家对事件的选择
        
        Args:
            event_id: 事件ID
            choice_id: 选择的选项ID
        
        Returns:
            处理结果
        """
        try:
            event = self.db.query(GameEvent).filter(GameEvent.id == event_id).first()
            if not event:
                return {"success": False, "error": "Event not found"}
            
            if not event.requires_player_action:
                return {"success": False, "error": "Event does not require player action"}
            
            # 查找选择的选项
            choices = event.get_player_choices()
            selected_choice = None
            
            for choice in choices:
                if choice.get("id") == choice_id:
                    selected_choice = choice
                    break
            
            if not selected_choice:
                return {"success": False, "error": f"Invalid choice: {choice_id}"}
            
            # 记录玩家选择
            event.player_choice_made = choice_id
            event.status = EventStatus.ACTIVE
            
            # 应用选项的效果
            choice_effects = selected_choice.get("effects", {})
            if choice_effects:
                event.set_effects(choice_effects)
                self._apply_event_effects(event)
            
            event.status = EventStatus.RESOLVED
            
            self.db.commit()
            
            logger.info(
                f"玩家对事件 {event.title} 选择了: {choice_id}"
            )
            
            return {
                "success": True,
                "choice": choice_id,
                "effects_applied": choice_effects
            }
            
        except Exception as e:
            logger.error(f"处理玩家选择失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def check_random_events(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        检查并触发随机事件（基于事件模板）
        
        Args:
            game_id: 游戏ID
            current_turn: 当前回合
        
        Returns:
            触发的事件列表
        """
        try:
            # 获取所有启用的事件模板
            templates = self.db.query(EventTemplate).filter(
                EventTemplate.is_enabled == True
            ).all()
            
            triggered_events = []
            
            for template in templates:
                # 检查触发条件
                if self._check_template_conditions(template, game_id, current_turn):
                    # 随机触发
                    if random.random() < template.trigger_probability:
                        # 触发事件
                        result = self._trigger_from_template(template, game_id, current_turn)
                        if result.get("success"):
                            triggered_events.append(result)
            
            return {
                "success": True,
                "events_triggered": len(triggered_events),
                "events": triggered_events
            }
            
        except Exception as e:
            logger.error(f"检查随机事件失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def generate_news(
        self,
        game_id: int,
        news_type: str,
        subject: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成新闻事件
        
        Args:
            game_id: 游戏ID
            news_type: 新闻类型（如PRODUCT_LAUNCH, COMPANY_BANKRUPTCY, TECH_BREAKTHROUGH）
            subject: 主题（如公司名、车型名）
            details: 详细信息
        
        Returns:
            新闻生成结果
        """
        # 预定义新闻模板
        news_templates = {
            "PRODUCT_LAUNCH": {
                "title": f"{subject} 发布新车型",
                "description": f"{subject} 在今日发布了全新车型。市场反响{details.get('reception', '热烈')}。"
            },
            "COMPANY_BANKRUPTCY": {
                "title": f"{subject} 宣布破产",
                "description": f"由于财务困难，{subject} 今日正式宣布破产。这标志着该品牌的终结。"
            },
            "TECH_BREAKTHROUGH": {
                "title": f"{subject} 取得技术突破",
                "description": f"{subject} 在{details.get('tech_area', '研发领域')}取得重大突破，行业震惊。"
            },
            "RECALL_EVENT": {
                "title": f"{subject} 召回{details.get('vehicle_count', '数千')}辆汽车",
                "description": f"由于{details.get('reason', '质量问题')},{subject}宣布召回旗下车型。"
            },
            "MARKET_DOMINANCE": {
                "title": f"{subject} 占据{details.get('region', '全球')}市场领先地位",
                "description": f"{subject}以{details.get('share', '20%')}的市场份额成为行业领导者。"
            }
        }
        
        template = news_templates.get(news_type)
        if not template:
            return {"success": False, "error": f"Unknown news type: {news_type}"}
        
        return self.trigger_event(
            game_id=game_id,
            event_type=EventType.NEWS,
            title=template["title"],
            description=template["description"],
            severity=EventSeverity.INFO,
            news_category="INDUSTRY"
        )
    
    def _apply_event_effects(self, event: GameEvent) -> None:
        """
        应用事件效果
        
        Args:
            event: 游戏事件
        """
        effects = event.get_effects()
        
        if not effects:
            return
        
        # 如果事件影响特定公司
        if event.affected_company_id:
            company = self.db.query(Company).filter(
                Company.id == event.affected_company_id
            ).first()
            
            if company:
                for effect_type, value in effects.items():
                    handler = self._event_handlers.get(effect_type)
                    if handler:
                        handler(company, value)
        
        # 如果事件影响特定地区
        if event.affected_region_code:
            region = self.db.query(Region).filter(
                Region.code == event.affected_region_code
            ).first()
            
            if region:
                # 应用地区效果
                if "gdp_change_percent" in effects:
                    region.gdp_per_capita *= (1 + effects["gdp_change_percent"])
                
                if "unemployment_change" in effects:
                    region.unemployment_rate = max(
                        0.01,
                        min(0.5, region.unemployment_rate + effects["unemployment_change"])
                    )
    
    # 效果处理器
    def _handle_cash_change(self, company: Company, value: float) -> None:
        """处理现金变化"""
        company.cash += value
        logger.debug(f"公司 {company.name} 现金变化: {value:+.1f}M")
    
    def _handle_reputation_change(self, company: Company, value: float) -> None:
        """处理声誉变化"""
        company.reputation_quality = max(0, min(100, company.reputation_quality + value))
        logger.debug(f"公司 {company.name} 声誉变化: {value:+.1f}")
    
    def _handle_prestige_change(self, company: Company, value: float) -> None:
        """处理声望变化"""
        company.prestige_score = max(0, company.prestige_score + value)
        logger.debug(f"公司 {company.name} 声望变化: {value:+.1f}")
    
    def _handle_tech_level_change(self, company: Company, value: int) -> None:
        """处理技术等级变化"""
        company.tech_level = max(1, min(10, company.tech_level + value))
        logger.debug(f"公司 {company.name} 技术等级变化: {value:+d}")
    
    def _handle_morale_change(self, company: Company, value: float) -> None:
        """处理员工士气变化"""
        company.employee_morale = max(0, min(1, company.employee_morale + value))
        logger.debug(f"公司 {company.name} 员工士气变化: {value:+.2f}")
    
    def _check_template_conditions(
        self,
        template: EventTemplate,
        game_id: int,
        current_turn: int
    ) -> bool:
        """
        检查事件模板的触发条件
        
        Args:
            template: 事件模板
            game_id: 游戏ID
            current_turn: 当前回合
        
        Returns:
            是否满足条件
        """
        conditions = template.get_trigger_conditions()
        
        # 检查回合数限制
        if "min_turn" in conditions and current_turn < conditions["min_turn"]:
            return False
        
        if "max_turn" in conditions and current_turn > conditions["max_turn"]:
            return False
        
        # TODO: 可以添加更多条件检查（如GDP、市场份额等）
        
        return True
    
    def _trigger_from_template(
        self,
        template: EventTemplate,
        game_id: int,
        current_turn: int
    ) -> Dict[str, Any]:
        """
        从模板触发事件
        
        Args:
            template: 事件模板
            game_id: 游戏ID
            current_turn: 当前回合
        
        Returns:
            触发结果
        """
        # 简单的变量替换（可以扩展）
        title = template.title_template
        description = template.description_template
        
        effects = template.get_effects_template()
        
        return self.trigger_event(
            game_id=game_id,
            event_type=template.event_type,
            title=title,
            description=description,
            severity=template.severity,
            effects=effects
        )
    
    def get_active_events(
        self,
        game_id: int,
        include_resolved: bool = False
    ) -> List[GameEvent]:
        """
        获取活跃事件列表
        
        Args:
            game_id: 游戏ID
            include_resolved: 是否包含已解决的事件
        
        Returns:
            事件列表
        """
        query = self.db.query(GameEvent).filter(GameEvent.game_id == game_id)
        
        if not include_resolved:
            query = query.filter(
                GameEvent.status.in_([EventStatus.TRIGGERED, EventStatus.ACTIVE])
            )
        
        return query.order_by(GameEvent.triggered_turn.desc()).all()


__all__ = ["EventLogic"]


