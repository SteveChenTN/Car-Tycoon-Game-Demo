"""
游戏管理API路由
处理游戏循环、回合推进、游戏状态等
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.core.save_manager import get_db, GameSessionManager, SaveManager
from backend.core.dependencies import get_db_optional
from backend.models import GameState, GameConfig, EventLog, Company
from backend.core.management.game_loop import GameLoopManager
from backend.core.management.game_loop_async import AsyncGameLoopManager
from backend.logic.world_gen import WorldGenerator
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/game", tags=["Game"])


# ============================================================================
# Request/Response 模型
# ============================================================================

class GameStateResponse(BaseModel):
    """游戏状态响应"""
    success: bool
    game_id: int
    turn_number: int
    date: str
    year: int
    month: int
    week: int
    mode: str
    difficulty: str
    
    class Config:
        from_attributes = True


class TurnAdvanceResponse(BaseModel):
    """回合推进响应"""
    success: bool
    old_turn: int
    new_turn: int
    old_date: str
    new_date: str
    execution_time_sec: float
    event_logs: List[Dict[str, Any]]
    phase_summaries: Dict[str, Any]
    
    class Config:
        from_attributes = True


def _current_save_payload() -> Dict[str, Any]:
    current_save_path = GameSessionManager.get_current_save_path()
    return {
        "loaded": current_save_path is not None,
        "save_path": str(current_save_path) if current_save_path else None,
        "file_name": current_save_path.name if current_save_path else None,
    }


# ============================================================================
# 游戏状态端点
# ============================================================================

@router.get("/state", response_model=Dict[str, Any])
async def get_game_state(db: Session = Depends(get_db_optional)) -> Dict[str, Any]:
    """
    获取当前游戏完整状态
    
    Returns:
        完整的游戏状态，包括：
        - 游戏基本信息
        - 玩家公司信息
        - 当前日期/回合
        - 最近事件
    """
    try:
        # 检查游戏是否已加载
        if db is None:
            return {
                "success": False,
                "error": "NO_GAME_LOADED",
                "current_save": _current_save_payload(),
                "message": "请先创建或加载游戏存档",
                "action": "请使用 POST /api/v1/game/new 创建新游戏，或 POST /api/v1/game/load 加载存档"
            }
        
        # 获取游戏状态
        game = db.query(GameState).first()
        if not game:
            return {
                "success": False,
                "error": "NO_GAME_FOUND",
                "current_save": _current_save_payload(),
                "message": "请先初始化游戏世界 (运行 init_world.py)"
            }
        
        # 获取游戏配置
        config = db.query(GameConfig).filter(GameConfig.game_id == game.id).first()
        
        # 获取玩家公司
        player_company = db.query(Company).filter(
            Company.game_id == game.id,
            Company.is_player == True
        ).first()
        
        # 获取最近的事件日志（最近50条）
        recent_logs = db.query(EventLog).filter(
            EventLog.game_id == game.id
        ).order_by(EventLog.id.desc()).limit(50).all()
        
        return {
            "success": True,
            "game_id": game.id,
            "player_company_id": player_company.id if player_company else None,
            "game": {
                "id": game.id,
                "turn": game.turn_number,
                "date": game.get_date_string(),
                "year": game.current_year,
                "month": game.current_month,
                "week": game.current_week,
                "total_weeks_elapsed": game.get_total_weeks_elapsed()
            },
            "config": config.to_dict() if config else None,
            "player_company": {
                "id": player_company.id,
                "name": player_company.name,
                "cash": player_company.cash,
                "prestige": player_company.prestige_score,
                "credit_rating": player_company.credit_rating
            } if player_company else None,
            "current_save": _current_save_payload(),
            "recent_events": [log.to_dict() for log in recent_logs]
        }
        
    except Exception as e:
        logger.error(f"获取游戏状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=Dict[str, Any])
async def get_game_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    获取游戏状态摘要（轻量级）
    
    Returns:
        游戏状态摘要
    """
    try:
        loop_mgr = GameLoopManager(db)
        game = db.query(GameState).first()
        
        if not game:
            return {
                "success": False,
                "error": "NO_GAME_FOUND"
            }
        
        return loop_mgr.get_game_status(game.id)
        
    except Exception as e:
        logger.error(f"获取游戏状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 回合推进端点
# ============================================================================

@router.post("/next_turn", response_model=Dict[str, Any])
async def advance_next_turn(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    推进下一个游戏回合
    
    这是游戏的核心端点，执行完整的游戏循环：
    1. 世界更新
    2. AI决策
    3. 生产解算
    4. 市场解算
    5. 财务结算
    6. 测试推进
    7. 事件触发
    8. 清理
    
    Returns:
        回合推进结果，包括所有事件日志（FM风格ticker数据）
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        # 检查游戏是否结束
        config = db.query(GameConfig).filter(GameConfig.game_id == game.id).first()
        if config and config.end_year and game.current_year >= config.end_year:
            return {
                "success": False,
                "error": "GAME_ENDED",
                "message": f"游戏已结束（到达结束年份 {config.end_year}）"
            }
        
        # 执行游戏循环
        loop_mgr = GameLoopManager(db)
        result = loop_mgr.advance_turn(game.id)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "回合推进失败"))
        
        # 获取本回合生成的事件日志
        turn_logs = db.query(EventLog).filter(
            EventLog.game_id == game.id,
            EventLog.turn_number == result["new_turn"]
        ).all()
        
        return {
            "success": True,
            "old_turn": result["turn"],
            "new_turn": result["new_turn"],
            "old_date": f"{result['turn']}",  # 将被替换为实际日期
            "new_date": result["new_date"],
            "execution_time_sec": result["execution_time_sec"],
            "event_logs": [log.to_dict() for log in turn_logs],
            "phase_summaries": result["phases"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回合推进失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/next_turn_async", response_model=Dict[str, Any])
async def advance_next_turn_async(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    推进下一个游戏回合（异步版本，带WebSocket实时广播）
    
    这个版本会通过WebSocket实时推送回合处理进度和事件日志，
    创建"Live Ticker"体验。前端应先连接到 /ws/game/{game_id}
    
    执行流程：
    1. 世界更新 → 实时广播经济变化
    2. AI决策 → 实时广播AI行动
    3. 生产解算 → 实时广播生产数据
    4. 市场解算 → 实时广播销售数据
    5. 财务结算 → 实时广播财务结果
    6. 测试推进 → 实时广播测试进度
    7. 事件触发 → 实时广播游戏事件
    8. 清理 → 完成回合
    
    Returns:
        回合推进结果摘要（详细事件已通过WebSocket发送）
    """
    try:
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        # 检查游戏是否结束
        config = db.query(GameConfig).filter(GameConfig.game_id == game.id).first()
        if config and config.end_year and game.current_year >= config.end_year:
            return {
                "success": False,
                "error": "GAME_ENDED",
                "message": f"游戏已结束（到达结束年份 {config.end_year}）"
            }
        
        # 使用异步游戏循环管理器
        async_loop_mgr = AsyncGameLoopManager(db)
        result = await async_loop_mgr.advance_turn_async(game.id)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "回合推进失败"))
        
        # 返回摘要（详细日志已通过WebSocket发送）
        return {
            "success": True,
            "new_turn": result.get("new_turn"),
            "new_date": result.get("new_date"),
            "execution_time_sec": result.get("execution_time_sec", 0),
            "event_count": result.get("event_count", 0),
            "message": "回合处理完成，详细事件已通过WebSocket推送"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"异步回合推进失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advance_multiple")
async def advance_multiple_turns(
    turns: int,
    stop_on_event: bool = False,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    批量推进多个回合
    
    Args:
        turns: 要推进的回合数
        stop_on_event: 是否在重大事件发生时停止
    
    Returns:
        批量推进结果摘要
    """
    try:
        if turns < 1 or turns > 520:  # 最多10年
            raise HTTPException(status_code=400, detail="回合数必须在1-520之间")
        
        game = db.query(GameState).first()
        if not game:
            raise HTTPException(status_code=404, detail="游戏未初始化")
        
        loop_mgr = GameLoopManager(db)
        
        results = {
            "success": True,
            "turns_executed": 0,
            "stopped_early": False,
            "stop_reason": None,
            "final_turn": game.turn_number,
            "final_date": game.get_date_string(),
            "summaries": []
        }
        
        for i in range(turns):
            turn_result = loop_mgr.advance_turn(game.id)
            
            if not turn_result.get("success"):
                results["stopped_early"] = True
                results["stop_reason"] = f"回合推进失败: {turn_result.get('error')}"
                break
            
            results["turns_executed"] += 1
            results["summaries"].append({
                "turn": turn_result["new_turn"],
                "date": turn_result["new_date"]
            })
            
            # 检查是否有重大事件（如果启用停止）
            if stop_on_event:
                critical_events = db.query(EventLog).filter(
                    EventLog.game_id == game.id,
                    EventLog.turn_number == turn_result["new_turn"],
                    EventLog.severity.in_(["CRITICAL", "ERROR"])
                ).first()
                
                if critical_events:
                    results["stopped_early"] = True
                    results["stop_reason"] = "遇到重大事件"
                    break
        
        # 更新最终状态
        db.refresh(game)
        results["final_turn"] = game.turn_number
        results["final_date"] = game.get_date_string()
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量推进失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 事件日志端点
# ============================================================================

@router.get("/events", response_model=List[Dict[str, Any]])
async def get_event_logs(
    turn: int = None,
    event_type: str = None,
    severity: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取事件日志
    
    Args:
        turn: 筛选特定回合
        event_type: 筛选事件类型
        severity: 筛选严重程度
        limit: 返回数量限制
    
    Returns:
        事件日志列表
    """
    try:
        game = db.query(GameState).first()
        if not game:
            return []
        
        query = db.query(EventLog).filter(EventLog.game_id == game.id)
        
        if turn is not None:
            query = query.filter(EventLog.turn_number == turn)
        
        if event_type:
            query = query.filter(EventLog.event_type == event_type)
        
        if severity:
            query = query.filter(EventLog.severity == severity)
        
        logs = query.order_by(EventLog.id.desc()).limit(limit).all()
        
        return [log.to_dict() for log in logs]
        
    except Exception as e:
        logger.error(f"获取事件日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/recent", response_model=List[Dict[str, Any]])
async def get_recent_events(
    limit: int = 50,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取最近的事件日志（用于前端ticker）
    
    Args:
        limit: 返回数量
    
    Returns:
        最近的事件日志
    """
    try:
        game = db.query(GameState).first()
        if not game:
            return []
        
        logs = db.query(EventLog).filter(
            EventLog.game_id == game.id
        ).order_by(EventLog.id.desc()).limit(limit).all()
        
        return [log.to_dict() for log in logs]
        
    except Exception as e:
        logger.error(f"获取最近事件失败: {e}")
        return []


# ============================================================================
# 游戏管理端点 (Save/Load/New)
# ============================================================================

class NewGameRequest(BaseModel):
    """新游戏请求"""
    save_name: Optional[str] = None
    company_name: str = "Player Company"
    starting_year: int = 1946
    difficulty: str = "normal"
    starting_capital: Optional[float] = None
    random_seed: Optional[int] = None


@router.post("/new", response_model=Dict[str, Any])
async def create_new_game(request: NewGameRequest) -> Dict[str, Any]:
    """
    创建新游戏（多存档系统）
    
    流程：
    1. 创建新的存档文件（从template.db复制）
    2. 连接到新存档
    3. 运行世界生成器
    4. 返回结果
    
    Args:
        request: 新游戏配置
    
    Returns:
        新游戏创建结果
    """
    try:
        logger.info(f"创建新游戏: {request.company_name}")
        
        # 1. 初始化SaveManager
        save_mgr = SaveManager()
        
        # 2. 确保模板数据库存在
        if not save_mgr.ensure_template_exists():
            return {
                "success": False,
                "error": "TEMPLATE_CREATION_FAILED",
                "message": "无法创建模板数据库"
            }
        
        # 3. 创建新存档
        result = save_mgr.create_new_save(
            save_name=request.save_name or f"{request.company_name}_{request.starting_year}",
            use_template=True
        )
        
        if not result["success"]:
            return result
        
        save_path = result["save_path"]
        logger.info(f"新存档已创建: {save_path}")
        
        # 4. 连接到新存档
        from pathlib import Path
        if not GameSessionManager.connect_to_save(Path(save_path)):
            return {
                "success": False,
                "error": "CONNECTION_FAILED",
                "message": "无法连接到新存档"
            }
        
        # 5. 获取数据库会话并生成世界
        session_factory = GameSessionManager.get_current_session_factory()
        db = session_factory()
        
        try:
            # 6. 运行世界生成器
            world_gen = WorldGenerator(
                db=db,
                difficulty=request.difficulty,
                random_seed=request.random_seed,
                starting_year=request.starting_year,
                save_name=request.save_name or f"{request.company_name}_{request.starting_year}"
            )
            
            gen_result = world_gen.generate(
                player_company_name=request.company_name,
                player_starting_capital=request.starting_capital
            )
            
            if not gen_result["success"]:
                # 生成失败，删除存档
                db.close()
                GameSessionManager.disconnect()
                save_mgr.delete_save(save_path)
                return gen_result
            
            db.commit()
            db.close()
            
            logger.info(f"✓ 新游戏创建完成: {request.company_name}")
            
            return {
                "success": True,
                "message": "新游戏创建成功！",
                "save_path": save_path,
                "save_name": result["file_name"],
                **gen_result
            }
            
        except Exception as e:
            db.rollback()
            db.close()
            GameSessionManager.disconnect()
            # 清理失败的存档
            save_mgr.delete_save(save_path)
            raise
        
    except Exception as e:
        logger.error(f"创建新游戏失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))




# ============================================================================
# 游戏管理端点 (Save/Load/New) - 多存档系统
# ============================================================================

# 注意：旧的 save 端点已移除
# 在多存档系统中，存档文件通过文件系统自动管理（SQLite文件即存档）
# 所有更改会自动持久化到当前加载的 .db 文件
# 如需手动备份，可以直接复制 saves/ 目录下的 .db 文件


class LoadGameRequest(BaseModel):
    """加载游戏请求"""
    save_path: str


@router.post("/load", response_model=Dict[str, Any])
async def load_saved_game(request: LoadGameRequest) -> Dict[str, Any]:
    """
    加载存档（多存档系统）
    
    流程：
    1. 断开当前数据库连接（如果有）
    2. 连接到指定存档文件
    3. 验证数据完整性
    
    Args:
        request: 包含存档路径
    
    Returns:
        加载结果
    """
    try:
        from pathlib import Path
        
        save_path = Path(request.save_path)
        
        # 验证文件存在
        if not save_path.exists():
            return {
                "success": False,
                "error": "FILE_NOT_FOUND",
                "message": f"存档文件不存在: {save_path}"
            }
        
        # 验证文件在saves目录内（安全检查）
        save_mgr = SaveManager()
        if not save_path.is_relative_to(save_mgr.saves_dir):
            return {
                "success": False,
                "error": "INVALID_PATH",
                "message": "只能加载 saves 目录内的存档"
            }
        
        # 断开当前连接
        if GameSessionManager.is_game_loaded():
            logger.info("断开当前游戏连接")
            GameSessionManager.disconnect()
        
        # 连接到新存档
        if not GameSessionManager.connect_to_save(save_path):
            return {
                "success": False,
                "error": "CONNECTION_FAILED",
                "message": "无法连接到存档文件"
            }
        
        # 验证数据完整性
        session_factory = GameSessionManager.get_current_session_factory()
        if not session_factory:
            GameSessionManager.disconnect()
            return {
                "success": False,
                "error": "SESSION_FAILED",
                "message": "无法创建数据库会话"
            }
        
        db = None
        try:
            db = session_factory()
            
            # 检查数据库是否有表结构（验证是否是有效的存档文件）
            try:
                # 尝试查询表是否存在
                from sqlalchemy import inspect
                inspector = inspect(GameSessionManager.get_current_engine())
                tables = inspector.get_table_names()
                
                if not tables or 'game_state' not in tables:
                    db.close()
                    GameSessionManager.disconnect()
                    return {
                        "success": False,
                        "error": "INVALID_SAVE",
                        "message": "存档文件无效（缺少表结构）"
                    }
            except Exception as table_check_err:
                logger.warning(f"检查表结构时出错: {table_check_err}")
                # 继续尝试查询，如果查询失败再报错
            
            # 查询游戏状态
            game = db.query(GameState).first()
            if not game:
                db.close()
                GameSessionManager.disconnect()
                return {
                    "success": False,
                    "error": "INVALID_SAVE",
                    "message": "存档文件为空或损坏（未找到游戏状态）"
                }
            
            # 查询玩家公司
            player = db.query(Company).filter(Company.is_player == True).first()
            if not player:
                db.close()
                GameSessionManager.disconnect()
                return {
                    "success": False,
                    "error": "INVALID_SAVE",
                    "message": "存档文件为空或损坏（未找到玩家公司）"
                }
            
            logger.info(f"✓ 游戏加载成功: {player.name} (年份: {game.current_year}, 回合: {game.turn_number})")
            
            result = {
                "success": True,
                "message": "游戏加载成功",
                "save_path": str(save_path),
                "game": {
                    "id": game.id,
                    "year": game.current_year,
                    "turn": game.turn_number,
                    "difficulty": game.difficulty
                },
                "player": {
                    "name": player.name,
                    "cash": player.cash,
                    "prestige": player.prestige_score
                }
            }
            
            db.close()
            return result
            
        except Exception as e:
            if db:
                try:
                    db.close()
                except:
                    pass
            GameSessionManager.disconnect()
            logger.error(f"加载存档时发生错误: {e}", exc_info=True)
            return {
                "success": False,
                "error": "LOAD_ERROR",
                "message": f"加载存档失败: {str(e)}"
            }
        
    except Exception as e:
        logger.error(f"加载游戏失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/saves", response_model=Dict[str, Any])
async def list_saved_games() -> Dict[str, Any]:
    """
    获取所有存档列表
    
    注意：此端点不需要 get_db 依赖（无需加载游戏即可调用）
    
    Returns:
        存档列表
    """
    try:
        save_mgr = SaveManager()
        saves = save_mgr.list_saves()
        
        return {
            "success": True,
            "saves": saves,
            "current_save": str(GameSessionManager.get_current_save_path()) 
                           if GameSessionManager.is_game_loaded() else None
        }
        
    except Exception as e:
        logger.error(f"获取存档列表失败: {e}")
        return {
            "success": False,
            "saves": [],
            "error": str(e)
        }


class DeleteSaveRequest(BaseModel):
    """删除存档请求"""
    save_path: str


@router.delete("/save", response_model=Dict[str, Any])
async def delete_saved_game(request: DeleteSaveRequest) -> Dict[str, Any]:
    """
    删除存档
    
    注意：如果删除的是当前加载的存档，会自动断开连接
    
    Args:
        request: 包含存档路径
    
    Returns:
        删除结果
    """
    try:
        save_mgr = SaveManager()
        result = save_mgr.delete_save(request.save_path)
        
        if result["success"]:
            logger.info(f"存档已删除: {request.save_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"删除存档失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


__all__ = ["router"]
