"""
Async Game Loop Manager - WebSocket实时广播版本

这是game_loop.py的async包装器，增加了WebSocket实时事件广播功能。
创建"Live Ticker"体验，让前端实时看到回合处理过程。
"""
import asyncio
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from backend.core.management.game_loop import GameLoopManager
from backend.api.routes.websocket import get_connection_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncGameLoopManager:
    """
    异步游戏循环管理器
    
    包装同步的GameLoopManager，添加WebSocket实时广播功能。
    每个阶段执行时都会通过WebSocket向前端推送进度和事件。
    """
    
    def __init__(self, db: Session):
        """
        初始化异步游戏循环管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.sync_manager = GameLoopManager(db)
        self.ws_manager = get_connection_manager()
        
        # 阶段定义
        self.phases = [
            {"id": 1, "name": "世界更新", "key": "world_update"},
            {"id": 2, "name": "AI公司决策", "key": "ai_decisions"},
            {"id": 3, "name": "生产解算", "key": "production"},
            {"id": 4, "name": "市场解算", "key": "market"},
            {"id": 5, "name": "财务结算", "key": "financial"},
            {"id": 6, "name": "供应商合约", "key": "contracts"},
            {"id": 7, "name": "测试项目", "key": "testing"},
            {"id": 8, "name": "二手车市场", "key": "used_cars"},
            {"id": 9, "name": "事件触发", "key": "events"},
            {"id": 10, "name": "历史记录", "key": "snapshot"},
            {"id": 11, "name": "回合清理", "key": "cleanup"}
        ]
        
        self.total_phases = len(self.phases)
    
    async def advance_turn_async(self, game_id: int) -> Dict[str, Any]:
        """
        异步推进游戏回合，实时广播进度
        
        Args:
            game_id: 游戏ID
        
        Returns:
            回合执行结果摘要
        """
        start_time = datetime.utcnow()
        
        try:
            # 发送回合开始通知
            await self.ws_manager.send_event_log(
                game_id=game_id,
                event_type="TURN_START",
                message="🎮 开始处理新回合...",
                severity="info"
            )
            
            # 执行各个阶段（使用run_in_executor在线程池中运行同步代码）
            loop = asyncio.get_event_loop()
            
            # 阶段1: 世界更新
            await self._execute_phase_with_broadcast(
                game_id=game_id,
                phase_index=0,
                executor_func=lambda: self._run_phase_world_update(game_id)
            )
            
            # 阶段2: AI决策
            await self._execute_phase_with_broadcast(
                game_id=game_id,
                phase_index=1,
                executor_func=lambda: self._run_phase_ai_decisions(game_id)
            )
            
            # 阶段3: 生产
            await self._execute_phase_with_broadcast(
                game_id=game_id,
                phase_index=2,
                executor_func=lambda: self._run_phase_production(game_id)
            )
            
            # 阶段4: 市场
            await self._execute_phase_with_broadcast(
                game_id=game_id,
                phase_index=3,
                executor_func=lambda: self._run_phase_market(game_id)
            )
            
            # 阶段5: 财务
            await self._execute_phase_with_broadcast(
                game_id=game_id,
                phase_index=4,
                executor_func=lambda: self._run_phase_financial(game_id)
            )
            
            # 阶段6-11: 其他阶段（简化处理）
            for phase_idx in range(5, self.total_phases):
                phase = self.phases[phase_idx]
                await self.ws_manager.send_turn_progress(
                    game_id=game_id,
                    current_phase=phase["name"],
                    phase_index=phase["id"],
                    total_phases=self.total_phases,
                    progress_percent=0
                )
                
                # 短暂延迟以展示进度
                await asyncio.sleep(0.1)
                
                await self.ws_manager.send_turn_progress(
                    game_id=game_id,
                    current_phase=phase["name"],
                    phase_index=phase["id"],
                    total_phases=self.total_phases,
                    progress_percent=100
                )
            
            # 使用同步管理器完成实际的回合推进
            logger.info("执行完整回合推进（同步）...")
            result = await loop.run_in_executor(
                None,
                self.sync_manager.advance_turn,
                game_id
            )
            
            if not result.get("success"):
                await self.ws_manager.send_error(
                    game_id=game_id,
                    error_message=f"回合处理失败: {result.get('error')}",
                    error_code="TURN_FAILED"
                )
                return result
            
            # 计算执行时间
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            # 发送回合完成通知
            await self.ws_manager.send_turn_complete(
                game_id=game_id,
                new_turn=result.get("new_turn", 0),
                new_year=result.get("new_year", 1950),
                new_month=result.get("new_month", 1),
                summary={
                    "execution_time": elapsed,
                    "event_count": result.get("event_count", 0),
                    "phases_completed": self.total_phases
                }
            )
            
            logger.info(f"✓ 回合 {result.get('new_turn')} 完成 (耗时: {elapsed:.2f}秒)")
            
            return result
            
        except Exception as e:
            logger.error(f"异步回合推进失败: {e}", exc_info=True)
            
            await self.ws_manager.send_error(
                game_id=game_id,
                error_message=f"回合处理异常: {str(e)}",
                error_code="TURN_EXCEPTION"
            )
            
            return {"success": False, "error": str(e)}
    
    async def _execute_phase_with_broadcast(
        self,
        game_id: int,
        phase_index: int,
        executor_func
    ):
        """
        执行单个阶段并广播进度
        
        Args:
            game_id: 游戏ID
            phase_index: 阶段索引（0-based）
            executor_func: 执行函数（同步）
        """
        phase = self.phases[phase_index]
        
        # 阶段开始
        await self.ws_manager.send_turn_progress(
            game_id=game_id,
            current_phase=phase["name"],
            phase_index=phase["id"],
            total_phases=self.total_phases,
            progress_percent=0
        )
        
        # 在线程池中执行同步代码
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, executor_func)
        
        # 广播阶段结果事件
        await self._broadcast_phase_events(game_id, phase["key"], result)
        
        # 阶段完成
        await self.ws_manager.send_turn_progress(
            game_id=game_id,
            current_phase=phase["name"],
            phase_index=phase["id"],
            total_phases=self.total_phases,
            progress_percent=100
        )
        
        # 短暂延迟以展示进度
        await asyncio.sleep(0.05)
    
    async def _broadcast_phase_events(
        self,
        game_id: int,
        phase_key: str,
        result: Dict[str, Any]
    ):
        """
        广播阶段执行结果的关键事件
        
        Args:
            game_id: 游戏ID
            phase_key: 阶段键名
            result: 阶段执行结果
        """
        if not result or "error" in result:
            return
        
        # 根据不同阶段广播不同类型的事件
        if phase_key == "world_update":
            regions_updated = result.get("regions_updated", 0)
            await self.ws_manager.send_event_log(
                game_id=game_id,
                event_type="WORLD",
                message=f"🌍 更新了 {regions_updated} 个地区的经济指标",
                severity="info"
            )
        
        elif phase_key == "ai_decisions":
            ai_count = result.get("ai_companies", 0)
            await self.ws_manager.send_event_log(
                game_id=game_id,
                event_type="AI",
                message=f"🤖 {ai_count} 家AI公司完成决策",
                severity="info"
            )
        
        elif phase_key == "production":
            total_produced = result.get("total_units_produced", 0)
            if total_produced > 0:
                await self.ws_manager.send_event_log(
                    game_id=game_id,
                    event_type="PRODUCTION",
                    message=f"🏭 本回合生产了 {total_produced:,} 辆车",
                    severity="success"
                )
        
        elif phase_key == "market":
            total_sales = result.get("total_sales", 0)
            if total_sales > 0:
                await self.ws_manager.send_event_log(
                    game_id=game_id,
                    event_type="MARKET",
                    message=f"💰 市场销售了 {total_sales:,} 辆车",
                    severity="success"
                )
        
        elif phase_key == "financial":
            companies_processed = result.get("companies_processed", 0)
            await self.ws_manager.send_event_log(
                game_id=game_id,
                event_type="FINANCE",
                message=f"💵 完成 {companies_processed} 家公司的财务结算",
                severity="info"
            )
    
    # ========== 同步执行器方法（在线程池中调用） ==========
    
    def _run_phase_world_update(self, game_id: int) -> Dict[str, Any]:
        """执行世界更新阶段（同步）"""
        from backend.models.game_state import GameState
        game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            return {"error": "Game not found"}
        
        return self.sync_manager._phase_world_update(game_id, game_state.turn_number)
    
    def _run_phase_ai_decisions(self, game_id: int) -> Dict[str, Any]:
        """执行AI决策阶段（同步）"""
        from backend.models.game_state import GameState
        game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            return {"error": "Game not found"}
        
        return self.sync_manager._phase_ai_decisions(game_id, game_state.turn_number)
    
    def _run_phase_production(self, game_id: int) -> Dict[str, Any]:
        """执行生产阶段（同步）"""
        from backend.models.game_state import GameState
        game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            return {"error": "Game not found"}
        
        return self.sync_manager._phase_production(game_id, game_state.turn_number)
    
    def _run_phase_market(self, game_id: int) -> Dict[str, Any]:
        """执行市场阶段（同步）"""
        from backend.models.game_state import GameState
        game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            return {"error": "Game not found"}
        
        return self.sync_manager._phase_market(game_id, game_state.turn_number)
    
    def _run_phase_financial(self, game_id: int) -> Dict[str, Any]:
        """执行财务阶段（同步）"""
        from backend.models.game_state import GameState
        game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
        if not game_state:
            return {"error": "Game not found"}
        
        return self.sync_manager._phase_financial(game_id, game_state.turn_number)


# 导出
__all__ = ["AsyncGameLoopManager"]


