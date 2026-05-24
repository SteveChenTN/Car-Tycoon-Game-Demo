/**
 * 游戏管理 API 服务
 * 处理存档、加载、新游戏等核心功能
 */

import type { GameState } from '@/types';
import { apiPaths, apiUrl, setActiveGameId } from './apiClient';

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 5000
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: init.signal ?? controller.signal,
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

// ============================================================
// Types
// ============================================================

export interface SaveInfo {
  success: boolean;
  save_name: string;
  version: string;
  saved_at: string;
  metadata?: {
    current_year: number;
    current_month: number;
    current_week: number;
    turn_number: number;
    difficulty: string;
  };
  file_path: string;
  file_size_mb: number;
}

interface BackendSaveInfo {
  save_name?: string;
  file_name?: string;
  version?: string;
  saved_at?: string;
  modified_time?: string;
  created_time?: string;
  metadata?: SaveInfo['metadata'];
  game_year?: number;
  current_year?: number;
  current_month?: number;
  current_week?: number;
  turn_number?: number;
  difficulty?: string;
  file_path?: string;
  file_size_mb?: number;
  size_mb?: number;
}

export interface SaveGameResponse {
  success: boolean;
  file_path?: string;
  size_mb?: number;
  record_count?: number;
  error?: string;
}

export interface LoadGameResponse {
  success: boolean;
  save_name?: string;
  game_id?: number;
  metadata?: {
    current_year: number;
    current_month: number;
    current_week: number;
    turn_number: number;
    difficulty: string;
  };
  imported_counts?: Record<string, number>;
  total_records?: number;
  error?: string;
}

export interface NewGameRequest {
  company_name: string;
  starting_year?: number;
  difficulty?: 'easy' | 'normal' | 'hard' | 'brutal';
  starting_capital?: number;
}

export interface NewGameResponse {
  success: boolean;
  game_id?: number;
  message?: string;
  error?: string;
}

// ============================================================
// Game Management API
// ============================================================

/**
 * 创建新游戏
 */
export async function createNewGame(request: NewGameRequest): Promise<NewGameResponse> {
  try {
    const response = await fetch(apiUrl(apiPaths.games.create), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    setActiveGameId(data.game_id ?? data.game?.id);
    return data;
  } catch (error) {
    console.error('Failed to create new game:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * 保存游戏
 */
export async function saveGame(saveName: string): Promise<SaveGameResponse> {
  try {
    const response = await fetch(apiUrl(apiPaths.legacy.game('/save')), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ save_name: saveName }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to save game:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * 加载游戏
 */
export async function loadGame(filePath: string): Promise<LoadGameResponse> {
  try {
    const response = await fetch(apiUrl(apiPaths.games.load), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ save_path: filePath }), // 修复：使用 save_path 而不是 file_path
    });

    if (!response.ok) {
      // 尝试获取更详细的错误信息
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        }
      } catch {
        // 如果无法解析错误响应，使用默认消息
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    setActiveGameId(data.game_id ?? data.game?.id);
    return data;
  } catch (error) {
    console.error('Failed to load game:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * 获取所有存档列表
 */
export async function listSaves(): Promise<SaveInfo[]> {
  try {
    const response = await fetchWithTimeout(apiUrl(apiPaths.games.saves));

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    const saves = (data.saves || []) as BackendSaveInfo[];
    
    // 转换后端数据格式以匹配前端期望
    return saves.map((save) => ({
      success: true,
      save_name: save.save_name || save.file_name || '未命名存档',
      version: save.version || '1.0',
      saved_at: save.saved_at || save.modified_time || save.created_time || new Date().toISOString(),
      metadata: save.metadata || ((save.game_year || save.current_year) ? {
        current_year: save.game_year || save.current_year || 1946,
        current_month: save.current_month || 1,
        current_week: save.current_week || 1,
        turn_number: save.turn_number || 0,
        difficulty: save.difficulty || 'normal'
      } : undefined),
      file_path: save.file_path || save.file_name || '',
      file_size_mb: save.file_size_mb ?? save.size_mb ?? 0
    }));
  } catch (error) {
    console.warn('Failed to list saves:', error);
    return [];
  }
}

/**
 * 删除存档
 */
export async function deleteSave(filePath: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(apiUrl(apiPaths.games.saves), {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ save_path: filePath }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to delete save:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * 获取游戏状态
 * 返回当前游戏的完整状态，包括日期、回合、玩家公司信息等
 */
export async function getGameState(): Promise<GameState | null> {
  try {
    const response = await fetch(apiUrl(apiPaths.currentGame('/state')));

    if (!response.ok) {
      if (response.status === 500) {
        // 游戏未加载，这是正常的
        console.log('[gameApi] Game not loaded yet');
        return null;
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (data.success && data.game) {
      const playerCompany = data.player_company
        ? {
            id: data.player_company.id,
            name: data.player_company.name,
            cash: data.player_company.cash,
            prestige: data.player_company.prestige,
            credit_rating: data.player_company.credit_rating,
          }
        : undefined;
      const gameId = data.game_id ?? data.game.id;
      const playerCompanyId = data.player_company_id ?? playerCompany?.id;
      setActiveGameId(gameId);

      return {
        game_id: gameId,
        gameId,
        player_company_id: playerCompanyId,
        playerCompanyId,
        currentSave: data.current_save
          ? {
              loaded: data.current_save.loaded,
              save_path: data.current_save.save_path,
              savePath: data.current_save.save_path,
              file_name: data.current_save.file_name,
              fileName: data.current_save.file_name,
            }
          : undefined,
        current_year: data.game.year,
        current_month: data.game.month,
        current_week: data.game.week,
        turn_number: data.game.turn,
        playerCompany,
      };
    }

    setActiveGameId(null);
    return null;
  } catch (error) {
    console.error('[gameApi] Failed to fetch game state:', error);
    return null;
  }
}

/**
 * 推进下一个回合（一周）
 * 
 * TODO: 验证后端数学计算已按周缩放：
 * - 运营成本：月成本应除以4得到周成本
 * - 生产输出：月产量应除以4得到周产量
 * - 现金流：确保周度计算不会导致经济崩溃
 */
export async function nextTurn(): Promise<{ success: boolean; new_date?: string; error?: string }> {
  try {
    const response = await fetch(apiUrl(apiPaths.currentGame('/next_turn')), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        }
      } catch {
        // 如果无法解析错误响应，使用默认消息
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    return {
      success: data.success || false,
      new_date: data.new_date,
      error: data.error,
    };
  } catch (error) {
    console.error('[gameApi] Failed to advance turn:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
