import axios from 'axios';

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

type ScopedDomain =
  | 'engineering'
  | 'factory'
  | 'market'
  | 'reports'
  | 'history'
  | 'staff'
  | 'diplomacy'
  | 'companies'
  | 'debug';

const envApiBase = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL = typeof envApiBase === 'string' ? envApiBase.replace(/\/$/, '') : '';

let activeGameId: number | null = null;

export const api = axios.create({
  baseURL: API_BASE_URL || undefined,
});

function cleanSuffix(suffix = ''): string {
  if (!suffix) return '';
  return suffix.startsWith('/') ? suffix : `/${suffix}`;
}

function appendQuery(path: string, params?: QueryParams): string {
  if (!params) return path;

  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      query.set(key, String(value));
    }
  });

  const queryString = query.toString();
  return queryString ? `${path}?${queryString}` : path;
}

export function setActiveGameId(gameId: number | null | undefined): void {
  activeGameId = typeof gameId === 'number' && Number.isFinite(gameId) ? gameId : null;
}

export function getActiveGameId(): number | null {
  return activeGameId;
}

export function apiUrl(path: string, params?: QueryParams): string {
  return `${API_BASE_URL}${appendQuery(path, params)}`;
}

export const apiPaths = {
  games: {
    create: '/api/v1/games',
    load: '/api/v1/games/load',
    saves: '/api/v1/games/saves',
    scoped: (gameId: number, suffix = '') => `/api/v1/games/${gameId}${cleanSuffix(suffix)}`,
  },
  legacy: {
    game: (suffix = '') => `/api/v1/game${cleanSuffix(suffix)}`,
    v1: (domain: string, suffix = '') => `/api/v1/${domain}${cleanSuffix(suffix)}`,
    reports: (suffix = '') => `/api/reports${cleanSuffix(suffix)}`,
  },
  currentGame: (futureSuffix: string, legacySuffix = futureSuffix) => {
    const gameId = getActiveGameId();
    return gameId
      ? `/api/v1/games/${gameId}${cleanSuffix(futureSuffix)}`
      : `/api/v1/game${cleanSuffix(legacySuffix)}`;
  },
  scoped: (
    domain: ScopedDomain,
    suffix = '',
    legacyPath?: string
  ) => {
    const gameId = getActiveGameId();
    if (gameId) {
      return `/api/v1/games/${gameId}/${domain}${cleanSuffix(suffix)}`;
    }

    if (legacyPath) {
      return legacyPath;
    }

    if (domain === 'reports') {
      return `/api/reports${cleanSuffix(suffix)}`;
    }

    if (domain === 'companies') {
      return `/api/v1/company${cleanSuffix(suffix)}`;
    }

    return `/api/v1/${domain}${cleanSuffix(suffix)}`;
  },
  websocket: (gameId = getActiveGameId()) => {
    const suffix = gameId ? `/ws/game/${gameId}` : '/ws/game';
    return suffix;
  },
};
