import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import type { EventLog, GameState } from '@/types';
import { apiPaths, apiUrl, getActiveGameId, setActiveGameId } from '@/services/apiClient';

interface GameContextValue {
  gameState: GameState | null;
  playerCompanyId: number | null;
  player_company_id: number | null;
  gameId: number | null;
  game_id: number | null;
  currentSave: GameState['currentSave'] | null;
  latestEvent: EventLog | null;
  eventHistory: EventLog[];
  isConnected: boolean;
  reconnect: () => void;
  refreshGameState: () => void;
}

interface GameProviderProps {
  children: ReactNode;
}

interface GameApiResponse {
  success?: boolean;
  game_id?: number;
  gameId?: number;
  player_company_id?: number;
  playerCompanyId?: number;
  current_save?: unknown;
  currentSave?: unknown;
  game?: {
    id?: number;
    year?: number;
    month?: number;
    week?: number;
    turn?: number;
  };
  player_company?: {
    id?: number;
    name?: string;
    cash?: number;
    prestige?: number;
    credit_rating?: string;
  };
  playerCompany?: GameState['playerCompany'];
}

interface InboundMessage {
  type?: string;
  payload?: unknown;
  id?: number;
  turn_number?: number;
  turn?: number;
  event_type?: string;
  message?: string;
  title?: string;
  description?: string;
  severity?: string;
  timestamp?: string;
  current_year?: number;
  current_month?: number;
  current_week?: number;
  game_id?: number;
  gameId?: number;
  player_company_id?: number;
  playerCompanyId?: number;
  currentSave?: GameState['currentSave'];
}

const GameContext = createContext<GameContextValue | undefined>(undefined);

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {};
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function optionalNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function normalizeCurrentSave(value: unknown, fallback?: GameState['currentSave']): GameState['currentSave'] | undefined {
  if (value === undefined || value === null) {
    return fallback;
  }

  const raw = asRecord(value);
  const savePath = raw.save_path ?? raw.savePath;
  const fileName = raw.file_name ?? raw.fileName;

  return {
    loaded: typeof raw.loaded === 'boolean' ? raw.loaded : fallback?.loaded ?? false,
    save_path: typeof savePath === 'string' ? savePath : fallback?.save_path ?? fallback?.savePath ?? null,
    savePath: typeof savePath === 'string' ? savePath : fallback?.savePath ?? fallback?.save_path ?? null,
    file_name: typeof fileName === 'string' ? fileName : fallback?.file_name ?? fallback?.fileName ?? null,
    fileName: typeof fileName === 'string' ? fileName : fallback?.fileName ?? fallback?.file_name ?? null,
  };
}

function normalizePlayerCompany(value: unknown, fallback?: GameState['playerCompany']): GameState['playerCompany'] | undefined {
  if (value === undefined || value === null) {
    return fallback;
  }

  const raw = asRecord(value);
  const id = optionalNumber(raw.id);
  if (id === undefined) {
    return fallback;
  }

  return {
    id,
    name: stringValue(raw.name, fallback?.name ?? 'Player Company'),
    cash: numberValue(raw.cash, fallback?.cash ?? 0),
    prestige: optionalNumber(raw.prestige) ?? fallback?.prestige,
    credit_rating: typeof raw.credit_rating === 'string' ? raw.credit_rating : fallback?.credit_rating,
  };
}

function normalizeGameState(value: unknown, fallback?: GameState | null): GameState | null {
  const raw = asRecord(value);
  const game = asRecord(raw.game);
  const base = fallback ?? undefined;
  const playerCompany = normalizePlayerCompany(raw.player_company ?? raw.playerCompany, base?.playerCompany);
  const gameId = optionalNumber(raw.game_id ?? raw.gameId ?? game.id) ?? base?.gameId ?? base?.game_id;
  const playerCompanyId =
    optionalNumber(raw.player_company_id ?? raw.playerCompanyId) ??
    playerCompany?.id ??
    base?.playerCompanyId ??
    base?.player_company_id;

  return {
    ...base,
    game_id: gameId,
    gameId,
    player_company_id: playerCompanyId,
    playerCompanyId,
    currentSave: normalizeCurrentSave(raw.current_save ?? raw.currentSave, base?.currentSave),
    current_year: numberValue(raw.current_year, numberValue(game.year, base?.current_year ?? 1946)),
    current_month: numberValue(raw.current_month, numberValue(game.month, base?.current_month ?? 1)),
    current_week: numberValue(raw.current_week, numberValue(game.week, base?.current_week ?? 1)),
    turn_number: numberValue(
      raw.turn_number,
      numberValue(raw.turn, numberValue(game.turn, base?.turn_number ?? 0))
    ),
    playerCompany,
  };
}

function normalizeSeverity(value: unknown): EventLog['severity'] {
  const severity = stringValue(value, 'info').toLowerCase();
  return severity === 'critical' || severity === 'warning' ? severity : 'info';
}

function eventFromPayload(payload: Record<string, unknown>, fallbackId: number): EventLog {
  return {
    id: numberValue(payload.id, fallbackId),
    turn_number: numberValue(payload.turn_number, numberValue(payload.turn, 0)),
    event_type: stringValue(payload.event_type, stringValue(payload.type, 'INFO')),
    title: stringValue(payload.message, stringValue(payload.title)),
    description: stringValue(payload.description, stringValue(payload.message)),
    severity: normalizeSeverity(payload.severity),
    created_at: stringValue(payload.timestamp, new Date().toISOString()),
    current_year: typeof payload.current_year === 'number' ? payload.current_year : undefined,
    current_month: typeof payload.current_month === 'number' ? payload.current_month : undefined,
    current_week: typeof payload.current_week === 'number' ? payload.current_week : undefined,
  };
}

export function GameProvider({ children }: GameProviderProps) {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [currentSaveState, setCurrentSaveState] = useState<GameState['currentSave'] | null>(null);
  const [latestEvent, setLatestEvent] = useState<EventLog | null>(null);
  const [eventHistory, setEventHistory] = useState<EventLog[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);

  const fetchRecentEvents = useCallback(async () => {
    try {
      const response = await fetch(apiUrl(apiPaths.currentGame('/events/recent'), { limit: 50 }), {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'omit',
      });

      if (!response.ok) {
        return;
      }

      const data = await response.json() as unknown[];
      if (!Array.isArray(data)) {
        return;
      }

      const events = data
        .slice()
        .reverse()
        .map((item, index) => eventFromPayload(asRecord(item), index + 1));

      setEventHistory(events);
      setLatestEvent(events.length > 0 ? events[events.length - 1] : null);
    } catch (error) {
      console.error('[GameProvider] Failed to fetch recent events:', error);
    }
  }, []);

  const fetchGameState = useCallback(async () => {
    try {
      const response = await fetch(apiUrl(apiPaths.currentGame('/state')), {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'omit',
      });

      if (!response.ok) {
        return;
      }

      const data = await response.json() as GameApiResponse;
      setCurrentSaveState(normalizeCurrentSave(data.current_save ?? data.currentSave) ?? null);

      if (!data.success || !data.game) {
        setActiveGameId(null);
        setGameState(null);
        return;
      }

      setGameState((prev) => {
        const next = normalizeGameState(data, prev);
        setActiveGameId(next?.gameId ?? next?.game_id);
        return next;
      });
    } catch (error) {
      console.error('[GameProvider] Failed to fetch game state:', error);
    }
  }, []);

  const connect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.close();
    }

    shouldReconnectRef.current = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const port = window.location.port ? `:${window.location.port}` : '';
    const gameId = getActiveGameId();
    const socketPath = apiPaths.websocket(gameId);
    const socket = new WebSocket(`${protocol}//${window.location.hostname}${port}${socketPath}`);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as InboundMessage;

        if (message.type === 'game_state') {
          setGameState((prev) => {
            const next = normalizeGameState(message.payload, prev);
            setActiveGameId(next?.gameId ?? next?.game_id);
            setCurrentSaveState(next?.currentSave ?? null);
            return next;
          });
          return;
        }

        if (message.type === 'event' || message.type === 'event_log') {
          const payload = asRecord(message.payload ?? message);
          const nextEvent = eventFromPayload(payload, 0);
          setLatestEvent(nextEvent);
          setEventHistory((prev) => [
            ...prev,
            eventFromPayload(payload, prev.length + 1),
          ].slice(-50));

          if (
            payload.current_year !== undefined ||
            payload.current_month !== undefined ||
            payload.current_week !== undefined
          ) {
            setGameState((prev) => {
              const base = prev ?? {
                current_year: 1946,
                current_month: 1,
                current_week: 1,
                turn_number: 0,
              };

              return {
                ...base,
                current_year: numberValue(payload.current_year, base.current_year),
                current_month: numberValue(payload.current_month, base.current_month),
                current_week: numberValue(payload.current_week, base.current_week),
                turn_number: numberValue(payload.turn_number, base.turn_number),
                playerCompany: base.playerCompany,
              };
            });
          }
          return;
        }

        if (message.type === 'turn_complete') {
          window.setTimeout(fetchGameState, 500);
          window.setTimeout(fetchRecentEvents, 500);
        }
      } catch (error) {
        console.error('[GameProvider] Failed to parse WebSocket message:', error);
      }
    };

    socket.onerror = () => {
      console.warn('[GameProvider] WebSocket connection unavailable; retrying in the background.');
    };

    socket.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
      if (shouldReconnectRef.current) {
        reconnectTimerRef.current = window.setTimeout(connect, 3000);
      }
    };
  }, [fetchGameState, fetchRecentEvents]);

  useEffect(() => {
    fetchGameState();
    fetchRecentEvents();
    connect();

    const handleGameLoaded = () => {
      window.setTimeout(fetchGameState, 1000);
      window.setTimeout(fetchRecentEvents, 1000);
    };

    window.addEventListener('gameLoaded', handleGameLoaded);

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (socketRef.current) {
        socketRef.current.onclose = null;
      }
      socketRef.current?.close();
      window.removeEventListener('gameLoaded', handleGameLoaded);
    };
  }, [connect, fetchGameState, fetchRecentEvents]);

  const reconnect = useCallback(() => {
    connect();
  }, [connect]);

  const refreshGameState = useCallback(() => {
    void fetchGameState();
    void fetchRecentEvents();
  }, [fetchGameState, fetchRecentEvents]);

  const playerCompanyId =
    gameState?.playerCompanyId ??
    gameState?.player_company_id ??
    gameState?.playerCompany?.id ??
    null;
  const gameId = gameState?.gameId ?? gameState?.game_id ?? null;
  const currentSave = gameState?.currentSave ?? currentSaveState ?? null;

  return (
    <GameContext.Provider
      value={{
        gameState,
        playerCompanyId,
        player_company_id: playerCompanyId,
        gameId,
        game_id: gameId,
        currentSave,
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

export function useGameContext() {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGameContext must be used within GameProvider');
  }
  return context;
}

export { useGameContext as useGame };
