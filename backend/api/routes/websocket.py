"""
WebSocket router for real-time game updates.

Implements the "Live Ticker" system where events stream to the frontend
as they happen during turn processing, creating an immersive FM-style experience.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """
    管理活跃的WebSocket连接。
    支持按game_id分组广播。
    """
    
    def __init__(self):
        # game_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, game_id: int):
        """接受新的WebSocket连接并加入对应的游戏房间"""
        await websocket.accept()
        
        async with self._lock:
            if game_id not in self.active_connections:
                self.active_connections[game_id] = set()
            self.active_connections[game_id].add(websocket)
        
        logger.info(f"WebSocket connected to game {game_id}. Total connections: {len(self.active_connections[game_id])}")
    
    async def disconnect(self, websocket: WebSocket, game_id: int):
        """断开WebSocket连接"""
        async with self._lock:
            if game_id in self.active_connections:
                self.active_connections[game_id].discard(websocket)
                if not self.active_connections[game_id]:
                    del self.active_connections[game_id]
        
        logger.info(f"WebSocket disconnected from game {game_id}")
    
    async def broadcast_to_game(self, game_id: int, message: dict):
        """
        向指定游戏的所有连接广播消息。
        
        Args:
            game_id: 游戏ID
            message: 要广播的消息（将被序列化为JSON）
        """
        if game_id not in self.active_connections:
            return
        
        message_json = json.dumps(message, ensure_ascii=False)
        
        # 复制集合以避免在迭代时修改
        connections = list(self.active_connections[game_id])
        
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.append(connection)
        
        # 清理失败的连接
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    self.active_connections[game_id].discard(conn)
    
    async def send_event_log(self, game_id: int, event_type: str, message: str, 
                           severity: str = "info", metadata: dict = None):
        """
        发送格式化的事件日志到前端。
        
        Args:
            game_id: 游戏ID
            event_type: 事件类型（如 "MARKET", "PRODUCTION", "FINANCE"）
            message: 事件消息文本
            severity: 严重程度（info, success, warning, error）
            metadata: 额外的元数据
        """
        payload = {
            "type": "event_log",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "message": message,
            "severity": severity,
            "metadata": metadata or {}
        }
        await self.broadcast_to_game(game_id, payload)
    
    async def send_turn_progress(self, game_id: int, current_phase: str, 
                                phase_index: int, total_phases: int,
                                progress_percent: float):
        """
        发送回合处理进度更新。
        
        Args:
            game_id: 游戏ID
            current_phase: 当前阶段名称
            phase_index: 当前阶段索引（从1开始）
            total_phases: 总阶段数
            progress_percent: 当前阶段进度百分比（0-100）
        """
        payload = {
            "type": "turn_progress",
            "timestamp": datetime.utcnow().isoformat(),
            "current_phase": current_phase,
            "phase_index": phase_index,
            "total_phases": total_phases,
            "progress_percent": progress_percent
        }
        await self.broadcast_to_game(game_id, payload)
    
    async def send_turn_complete(self, game_id: int, new_turn: int, 
                                new_year: int, new_month: int,
                                summary: dict):
        """
        发送回合完成通知。
        
        Args:
            game_id: 游戏ID
            new_turn: 新回合号
            new_year: 新年份
            new_month: 新月份
            summary: 回合摘要数据
        """
        payload = {
            "type": "turn_complete",
            "timestamp": datetime.utcnow().isoformat(),
            "turn_number": new_turn,
            "year": new_year,
            "month": new_month,
            "summary": summary
        }
        await self.broadcast_to_game(game_id, payload)
    
    async def send_error(self, game_id: int, error_message: str, error_code: str = None):
        """发送错误消息"""
        payload = {
            "type": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "message": error_message,
            "error_code": error_code
        }
        await self.broadcast_to_game(game_id, payload)


# 全局连接管理器实例
manager = ConnectionManager()


@router.websocket("/game")
async def websocket_game_simple_endpoint(websocket: WebSocket):
    """
    简化的WebSocket端点，不需要game_id参数
    自动连接到第一个游戏
    
    注意：此端点不依赖数据库会话，可以在游戏未加载时连接
    """
    # 默认 game_id，避免变量未定义错误
    game_id = 1
    
    # 注意：不要手动 accept，manager.connect() 会处理
    logger.info("WebSocket connecting (no game_id specified)")
    
    try:
        # 注册连接 (这里会自动 accept)
        await manager.connect(websocket, game_id)
        logger.info(f"Client auto-connected to game {game_id}")
        
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "payload": {
                "game_id": game_id,
                "message": "Connected to game updates"
            }
        })
        
        # 保持连接活跃
        while True:
            data = await websocket.receive_text()
            
            # 处理客户端命令
            try:
                command = json.loads(data)
                
                if command.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON: {data}")
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, game_id)
        logger.info(f"Client disconnected from game {game_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await manager.disconnect(websocket, game_id)
        except:
            pass  # 忽略断开连接时的错误


@router.websocket("/game/{game_id}")
async def websocket_game_endpoint(websocket: WebSocket, game_id: int):
    """
    游戏实时更新WebSocket端点。
    
    前端连接到此端点后，将接收：
    - 回合处理过程中的实时事件日志
    - 回合进度更新
    - 回合完成通知
    - 错误消息
    
    消息格式示例：
    {
        "type": "event_log",
        "timestamp": "2024-12-28T10:30:00.000Z",
        "event_type": "MARKET",
        "message": "北美地区销售了1,234辆车",
        "severity": "info",
        "metadata": {"region": "NAM", "units": 1234}
    }
    
    注意：此端点不依赖数据库会话，可以在游戏未加载时连接
    """
    await manager.connect(websocket, game_id)
    
    try:
        # 发送连接成功消息
        await manager.broadcast_to_game(game_id, {
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "game_id": game_id,
            "message": "已连接到游戏实时更新"
        })
        
        # 保持连接活跃，监听客户端消息
        while True:
            data = await websocket.receive_text()
            
            # 处理客户端命令（如心跳检测）
            try:
                command = json.loads(data)
                
                if command.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif command.get("type") == "subscribe":
                    # 未来可以实现更细粒度的订阅（如只订阅特定公司的事件）
                    pass
                
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from WebSocket: {data}")
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket, game_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await manager.disconnect(websocket, game_id)


def get_connection_manager() -> ConnectionManager:
    """
    获取全局ConnectionManager实例。
    
    用于在其他模块中获取manager进行广播。
    """
    return manager

