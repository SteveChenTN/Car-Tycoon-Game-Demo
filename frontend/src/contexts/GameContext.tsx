import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { GameState, EventLog } from '@/types';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// ============================================================
// Context Types
// ============================================================

interface GameContextValue {
  gameState: GameState | null;
  latestEvent: EventLog | null;
  eventHistory: EventLog[];
  isConnected: boolean;
  reconnect: () => void;
  refreshGameState: () => void;
}

const GameContext = createContext<GameContextValue | undefined>(undefined);

// ============================================================
// Provider Component
// ============================================================

interface GameProviderProps {
  children: ReactNode;
}

export function GameProvider({ children }: GameProviderProps) {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [latestEvent, setLatestEvent] = useState<EventLog | null>(null);
  const [eventHistory, setEventHistory] = useState<EventLog[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/game`;
    
    console.log('[GameProvider] Connecting to WebSocket:', wsUrl);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('[GameProvider] WebSocket connected');
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('[GameProvider] Message received:', message.type, message);

        switch (message.type) {
          case 'connected':
            console.log('[GameProvider] WebSocket connected:', message.payload);
            // 连接成功，可以触发一次状态刷新
            break;
          case 'game_state':
            console.log('[GameProvider] Updating game state:', message.payload);
            setGameState(message.payload);
            break;
          case 'event':
          case 'event_log':
            console.log('[GameProvider] Event received:', message.payload);
            // 处理事件日志格式
            const eventData = message.payload || message;
            setLatestEvent({
              id: eventData.id || 0,
              turn_number: eventData.turn_number || eventData.turn || 0,
              event_type: eventData.event_type || eventData.type || 'INFO',
              title: eventData.message || eventData.title || '',
              description: eventData.description || eventData.message || '',
              severity: (eventData.severity || 'info').toLowerCase() as 'info' | 'warning' | 'critical',
              created_at: eventData.timestamp || new Date().toISOString(),
              current_year: eventData.current_year,
              current_month: eventData.current_month,
              current_week: eventData.current_week,
            });
            setEventHistory((prev) => {
              const newHistory = [...prev, {
                id: eventData.id || prev.length + 1,
                turn_number: eventData.turn_number || eventData.turn || 0,
                event_type: eventData.event_type || eventData.type || 'INFO',
                title: eventData.message || eventData.title || '',
                description: eventData.description || eventData.message || '',
                severity: (eventData.severity || 'info').toLowerCase() as 'info' | 'warning' | 'critical',
                created_at: eventData.timestamp || new Date().toISOString(),
                current_year: eventData.current_year,
                current_month: eventData.current_month,
                current_week: eventData.current_week,
              }];
              // Keep only last 50 events for performance
              return newHistory.slice(-50);
            });
            
            // 关键修复：从event中更新游戏时间
            if (eventData) {
              // 检查event是否包含时间信息
              if (eventData.current_year !== undefined || 
                  eventData.current_month !== undefined || 
                  eventData.current_week !== undefined) {
                console.log('[GameProvider] Updating game time from event:', {
                  year: eventData.current_year,
                  month: eventData.current_month,
                  week: eventData.current_week,
                });
                
                setGameState((prevState) => {
                  if (!prevState) {
                    console.warn('[GameProvider] No previous game state, creating new one');
                    return {
                      current_year: eventData.current_year ?? 1946,
                      current_month: eventData.current_month ?? 1,
                      current_week: eventData.current_week ?? 1,
                      turn_number: eventData.turn_number ?? 0,
                    };
                  }
                  
                  const updatedState = {
                    ...prevState,
                    current_year: eventData.current_year ?? prevState.current_year,
                    current_month: eventData.current_month ?? prevState.current_month,
                    current_week: eventData.current_week ?? prevState.current_week,
                    turn_number: eventData.turn_number ?? prevState.turn_number,
                  };
                  
                  console.log('[GameProvider] Game state updated:', updatedState);
                  return updatedState;
                });
              }
            }
            break;
          case 'notification':
            console.log('[GameProvider] Notification:', message.payload);
            break;
          case 'turn_complete':
            console.log('[GameProvider] Turn complete:', message);
            // 回合完成，刷新游戏状态
            setTimeout(() => {
              fetchGameState();
            }, 500);
            break;
          case 'pong':
            // 心跳响应，无需处理
            break;
          default:
            console.warn('[GameProvider] Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('[GameProvider] Failed to parse message:', error);
      }
    };

    socket.onerror = (error) => {
      console.error('[GameProvider] WebSocket error:', error);
    };

    socket.onclose = () => {
      console.log('[GameProvider] WebSocket disconnected');
      setIsConnected(false);
      
      // Auto-reconnect after 3 seconds
      setTimeout(() => {
        console.log('[GameProvider] Attempting to reconnect...');
        connect();
      }, 3000);
    };

    setWs(socket);
  };

  // 从 API 获取初始游戏状态
  const fetchGameState = async () => {
    try {
      console.log('[GameProvider] Fetching game state from API...');
      const response = await fetch(`${API_BASE_URL}/game/state`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        // 添加credentials以支持CORS
        credentials: 'omit',
      });
      
      if (!response.ok) {
        // 尝试解析错误响应
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
        
        if (response.status === 500 || response.status === 404) {
          // 游戏未加载或不存在，这是正常的
          console.log('[GameProvider] Game not loaded yet:', errorMessage);
          return;
        }
        
        console.warn('[GameProvider] Failed to fetch game state:', errorMessage);
        return;
      }
      
      const data = await response.json();
      
      console.log('[GameProvider] Raw API response:', JSON.stringify(data, null, 2));
      
      if (data.success && data.game) {
        const newState: GameState = {
          current_year: data.game.year,
          current_month: data.game.month,
          current_week: data.game.week,
          turn_number: data.game.turn,
          playerCompany: data.player_company ? {
            id: data.player_company.id,
            name: data.player_company.name,
            cash: data.player_company.cash,
            prestige: data.player_company.prestige,
            credit_rating: data.player_company.credit_rating,
          } : undefined,
        };
        
        // 使用函数式更新，确保获取最新的状态
        setGameState((prevState) => {
          const hasChanged = !prevState || 
            prevState.current_year !== newState.current_year ||
            prevState.current_month !== newState.current_month ||
            prevState.current_week !== newState.current_week ||
            prevState.turn_number !== newState.turn_number ||
            prevState.playerCompany?.cash !== newState.playerCompany?.cash;
          
          console.log('[GameProvider] State update:', {
            previous: prevState ? {
              date: `${prevState.current_year}-${prevState.current_month}-W${prevState.current_week}`,
              turn: prevState.turn_number,
              cash: prevState.playerCompany?.cash
            } : 'null',
            new: {
              date: `${newState.current_year}-${newState.current_month}-W${newState.current_week}`,
              turn: newState.turn_number,
              cash: newState.playerCompany?.cash
            },
            hasChanged
          });
          
          return newState;
        });
      } else {
        console.warn('[GameProvider] No game state available:', data);
      }
    } catch (error) {
      console.error('[GameProvider] Failed to fetch game state:', error);
      // 不抛出错误，允许继续运行（可能游戏还未加载）
    }
  };

  useEffect(() => {
    // 先获取初始状态
    fetchGameState();
    
    // 然后连接 WebSocket
    connect();

    // 监听游戏加载事件
    const handleGameLoaded = () => {
      console.log('[GameProvider] Game loaded event received, refreshing state...');
      setTimeout(() => {
        fetchGameState();
      }, 1000); // 等待1秒让后端完成加载
    };

    window.addEventListener('gameLoaded', handleGameLoaded);

    return () => {
      if (ws) {
        ws.close();
      }
      window.removeEventListener('gameLoaded', handleGameLoaded);
    };
  }, []);

  const reconnect = () => {
    if (ws) {
      ws.close();
    }
    connect();
  };

  // 导出刷新函数，供外部调用（例如游戏加载后）
  const refreshGameState = () => {
    fetchGameState();
  };

  return (
    <GameContext.Provider
      value={{
        gameState,
        latestEvent,
        eventHistory,
        isConnected,
        reconnect,
        refreshGameState,
      }}
    >
      {children}
    </GameContext.Provider>
  );
}

// ============================================================
// Hook
// ============================================================

export function useGameContext() {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGameContext must be used within GameProvider');
  }
  return context;
}

// 别名导出，保持向后兼容
export { useGameContext as useGame };

