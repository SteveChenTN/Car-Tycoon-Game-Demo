"""
FastAPI 应用入口
"""
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.config import settings
from backend.database import Base  # 只导入 Base 类
from backend.models import GameState, Region
from backend.utils.logger import setup_logging, get_logger
from backend.core.save_manager import GameSessionManager, SaveManager

# 初始化日志
setup_logging()
logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Hardcore Automobile Company Simulation",
    debug=settings.DEBUG
)

# CORS配置（允许前端访问）
# 注意：必须在所有路由注册之前添加，确保所有响应都包含CORS头
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ============================================================================
# 生命周期事件
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 80)
    logger.info(f"🚗 {settings.APP_NAME} v{settings.VERSION} - Starting Up")
    logger.info("=" * 80)
    
    # 1. 初始化游戏数据加载器（必须首先执行）
    try:
        from backend.core.loader import initialize_game_data
        from backend.core.engineering.physics import EngineeringCalculator
        
        logger.info("📦 正在加载游戏数据...")
        data_loader = initialize_game_data("assets/data")
        
        # 将数据加载器注入到工程计算器
        EngineeringCalculator.set_data_loader(data_loader)
        
        logger.info("✓ 游戏数据加载完成（数据驱动架构已激活）")
        
    except Exception as e:
        logger.critical(f"❌ 游戏数据加载失败: {e}")
        logger.critical("服务器无法启动。请检查 assets/data/ 目录下的JSON文件。")
        raise RuntimeError(f"Game data loading failed: {e}") from e
    
    # 2. 初始化存档系统（确保模板数据库存在）
    try:
        save_mgr = SaveManager()
        save_mgr.ensure_template_exists()
        logger.info("✓ 存档系统初始化完成")
        logger.info(f"  - 存档目录: {save_mgr.saves_dir}")
        logger.info(f"  - 模板数据库: {save_mgr.template_db_path}")
    except Exception as e:
        logger.error(f"存档系统初始化失败: {e}")
        raise
    
    # 3. 检查是否有现有存档
    saves = save_mgr.list_saves()
    if saves:
        logger.info(f"✓ 发现 {len(saves)} 个现有存档")
        logger.info("  提示：使用 POST /api/v1/game/load 加载存档")
    else:
        logger.info("  未发现现有存档")
        logger.info("  提示：使用 POST /api/v1/game/new 创建新游戏")
    
    logger.info("")
    logger.info("⚠️  重要提示：多存档系统已启用")
    logger.info("  - 服务器启动时不会自动加载游戏")
    logger.info("  - 必须先调用 /api/v1/game/new 或 /api/v1/game/load")
    logger.info("  - 未加载游戏时访问游戏端点会返回 403 Forbidden")
    logger.info("")
    
    logger.info(f"✓ API Server ready at http://localhost:8000")
    logger.info(f"✓ API Docs available at http://localhost:8000/docs")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("=" * 80)
    logger.info("🛑 Shutting down AutoMogul API Server")
    
    # 断开数据库连接
    if GameSessionManager.is_game_loaded():
        logger.info("正在断开游戏存档连接...")
        GameSessionManager.disconnect()
    
    logger.info("=" * 80)


# ============================================================================
# 全局异常处理器（确保错误响应也包含CORS头）
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，确保所有错误响应都包含CORS头"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "INTERNAL_SERVER_ERROR",
            "detail": str(exc) if settings.DEBUG else "Internal server error"
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证错误处理器"""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "VALIDATION_ERROR",
            "detail": exc.errors()
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# ============================================================================
# 导入路由
# ============================================================================

from backend.api.routes import game, engineering, company, debug, history, websocket, factory, market, staff, diplomacy, reports

# 注册路由
app.include_router(game.router)
app.include_router(engineering.router)
app.include_router(company.router)
app.include_router(debug.router)
app.include_router(history.router)
app.include_router(websocket.router)  # WebSocket实时通信
app.include_router(factory.router)
app.include_router(market.router)
app.include_router(reports.router)  # 报告API
app.include_router(staff.router)
app.include_router(diplomacy.router)

logger.info("✓ API Routes registered (including WebSocket)")


# ============================================================================
# API 路由
# ============================================================================

@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """根路径：API信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "api_base": "/api/v1",
        "routes": {
            "game": "/api/v1/game",
            "engineering": "/api/v1/engineering",
            "company": "/api/v1/company",
            "debug": "/api/v1/debug",
            "websocket": "/ws/game/{game_id}"
        },
        "message": "Welcome to AutoMogul - Hardcore Automobile Company Simulation"
    }


@app.get("/health", tags=["Root"])
async def health_check() -> Dict[str, str]:
    """健康检查"""
    return {"status": "healthy"}


# 这些路由已移至 backend/api/routes/ 模块
# 请访问 /docs 查看完整API文档


# ============================================================================
# 主函数（用于调试）
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting development server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

