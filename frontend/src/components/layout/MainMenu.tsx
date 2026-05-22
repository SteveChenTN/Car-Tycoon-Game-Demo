import { useState, useEffect } from 'react';
import { Play, FolderOpen, Settings, X } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { createNewGame, listSaves, loadGame, type SaveInfo } from '@/services/gameApi';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { cn } from '@/lib/utils';

// ============================================================
// Types
// ============================================================

interface MainMenuProps {
  onGameStart: () => void;
}

type MenuScreen = 'main' | 'load' | 'settings';

// ============================================================
// Main Menu Component
// ============================================================

export function MainMenu({ onGameStart }: MainMenuProps) {
  const { t, language, setLanguage } = useLanguage();
  const [currentScreen, setCurrentScreen] = useState<MenuScreen>('main');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // === Handlers ===

  const handleNewGame = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await createNewGame({
        company_name: 'Player Company',
        starting_year: 1946,
        difficulty: 'normal',
      });

      if (result.success) {
        onGameStart();
      } else {
        setError(result.error || 'Failed to create new game');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    setCurrentScreen('main');
    setError(null);
  };

  // === Screen Renderers ===

  const renderMainScreen = () => (
    <div className="flex flex-col items-center gap-6 w-full max-w-md">
      {/* Title */}
      <div className="text-center mb-8">
        <h1 className="text-6xl font-bold text-cyan-400 tracking-wider mb-2">
          {t('menu.title')}
        </h1>
        <p className="text-slate-400 text-sm uppercase tracking-widest">
          {t('menu.subtitle')}
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="w-full bg-rose-900/20 border border-rose-500/50 text-rose-300 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Menu Buttons */}
      <button
        onClick={handleNewGame}
        disabled={isLoading}
        className={cn(
          'w-full flex items-center justify-center gap-3 px-8 py-4',
          'bg-cyan-600 hover:bg-cyan-500 text-white font-semibold',
          'rounded border border-cyan-400/50 shadow-lg shadow-cyan-500/20',
          'transition-all duration-200 transform hover:scale-105',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none'
        )}
      >
        <Play className="w-5 h-5" />
        <span className="text-lg uppercase tracking-wide">
          {isLoading ? t('common.loading') : t('menu.newGame')}
        </span>
      </button>

      <button
        onClick={() => setCurrentScreen('load')}
        className={cn(
          'w-full flex items-center justify-center gap-3 px-8 py-4',
          'bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold',
          'rounded border border-slate-600 shadow-lg',
          'transition-all duration-200 transform hover:scale-105'
        )}
      >
        <FolderOpen className="w-5 h-5" />
        <span className="text-lg uppercase tracking-wide">{t('menu.loadGame')}</span>
      </button>

      <button
        onClick={() => setCurrentScreen('settings')}
        className={cn(
          'w-full flex items-center justify-center gap-3 px-8 py-4',
          'bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold',
          'rounded border border-slate-600 shadow-lg',
          'transition-all duration-200 transform hover:scale-105'
        )}
      >
        <Settings className="w-5 h-5" />
        <span className="text-lg uppercase tracking-wide">{t('menu.settings')}</span>
      </button>
    </div>
  );

  const renderLoadScreen = () => <LoadGameScreen onBack={handleBack} onLoad={onGameStart} />;

  const renderSettingsScreen = () => (
    <div className="flex flex-col items-center gap-6 w-full max-w-md">
      {/* Title */}
      <h2 className="text-3xl font-bold text-cyan-400 tracking-wider mb-4">
        {t('settings.title')}
      </h2>

      {/* Language Selector */}
      <div className="w-full bg-slate-900/50 border border-slate-700 rounded p-6">
        <label className="block text-slate-300 font-semibold mb-3">
          {t('settings.language')}
        </label>
        <div className="flex gap-3">
          <button
            onClick={() => setLanguage('en')}
            className={cn(
              'flex-1 px-4 py-3 rounded border font-semibold transition-all',
              language === 'en'
                ? 'bg-cyan-600 border-cyan-400 text-white'
                : 'bg-slate-800 border-slate-600 text-slate-400 hover:bg-slate-700'
            )}
          >
            English
          </button>
          <button
            onClick={() => setLanguage('zh')}
            className={cn(
              'flex-1 px-4 py-3 rounded border font-semibold transition-all',
              language === 'zh'
                ? 'bg-cyan-600 border-cyan-400 text-white'
                : 'bg-slate-800 border-slate-600 text-slate-400 hover:bg-slate-700'
            )}
          >
            中文
          </button>
        </div>
      </div>

      {/* Back Button */}
      <button
        onClick={handleBack}
        className={cn(
          'w-full flex items-center justify-center gap-2 px-6 py-3',
          'bg-slate-800 hover:bg-slate-700 text-slate-300',
          'rounded border border-slate-600 transition-all'
        )}
      >
        <X className="w-4 h-4" />
        <span className="uppercase tracking-wide">{t('menu.back')}</span>
      </button>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
      {/* Animated Background Grid */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-black to-slate-950">
        <div className="absolute inset-0 retro-grid opacity-20 animate-pulse" />
      </div>

      {/* Content */}
      <div className="relative z-10 w-full max-w-2xl px-8">
        {currentScreen === 'main' && renderMainScreen()}
        {currentScreen === 'load' && renderLoadScreen()}
        {currentScreen === 'settings' && renderSettingsScreen()}
      </div>
    </div>
  );
}

// ============================================================
// Load Game Sub-Component
// ============================================================

interface LoadGameScreenProps {
  onBack: () => void;
  onLoad: () => void;
}

function LoadGameScreen({ onBack, onLoad }: LoadGameScreenProps) {
  const { t } = useLanguage();
  const [saves, setSaves] = useState<SaveInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load saves on mount
  useEffect(() => {
    const fetchSaves = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const saveList = await listSaves();
        setSaves(saveList || []);
      } catch (err) {
        console.error('[LoadGameScreen] Failed to load saves:', err);
        setError(err instanceof Error ? err.message : 'Failed to load saves');
        setSaves([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSaves();
  }, []);

  const handleLoadSave = async (save: SaveInfo) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await loadGame(save.file_path);
      if (result.success) {
        onLoad();
      } else {
        setError(result.error || 'Failed to load save');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ErrorBoundary>
      <div className="flex flex-col items-center gap-6 w-full max-w-2xl">
        {/* Title */}
        <h2 className="text-3xl font-bold text-cyan-400 tracking-wider mb-4">
          {t('load.title')}
        </h2>

        {/* Error Display */}
        {error && (
          <div className="w-full bg-rose-900/20 border border-rose-500/50 text-rose-300 px-4 py-3 rounded">
            {error}
            <button
              onClick={() => {
                setError(null);
                setIsLoading(true);
                listSaves()
                  .then((saveList) => {
                    setSaves(saveList || []);
                    setIsLoading(false);
                  })
                  .catch((err) => {
                    setError(err instanceof Error ? err.message : 'Failed to load saves');
                    setIsLoading(false);
                  });
              }}
              className="ml-4 text-rose-300 hover:text-rose-200 underline"
            >
              重试
            </button>
          </div>
        )}

      {/* Saves List */}
      <div className="w-full bg-slate-900/50 border border-slate-700 rounded overflow-hidden max-h-96 overflow-y-auto">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">{t('common.loading')}</div>
        ) : saves.length === 0 ? (
          <div className="p-8 text-center text-slate-400">{t('load.empty')}</div>
        ) : (
          <div className="divide-y divide-slate-700">
            {saves.map((save, index) => (
              <button
                key={index}
                onClick={() => handleLoadSave(save)}
                className={cn(
                  'w-full px-6 py-4 text-left transition-colors',
                  'hover:bg-slate-800/50 focus:bg-slate-800'
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-cyan-400 font-semibold text-lg">
                      {save.save_name || save.file_name || '未命名存档'}
                    </p>
                    {(save.metadata || save.game_year) && (
                      <p className="text-slate-400 text-sm font-mono">
                        {save.metadata 
                          ? `${save.metadata.current_year}/${save.metadata.current_month} - Turn ${save.metadata.turn_number}`
                          : save.game_year 
                            ? `${save.game_year} - Turn ${save.turn_number || 0}`
                            : ''}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-slate-400 text-xs">
                      {save.saved_at || save.modified_time 
                        ? new Date(save.saved_at || save.modified_time || '').toLocaleString()
                        : '未知时间'}
                    </p>
                    <p className="text-slate-500 text-xs">
                      {(save.file_size_mb ?? save.size_mb ?? 0).toFixed(2)} MB
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Back Button */}
      <button
        onClick={onBack}
        className={cn(
          'w-full flex items-center justify-center gap-2 px-6 py-3',
          'bg-slate-800 hover:bg-slate-700 text-slate-300',
          'rounded border border-slate-600 transition-all'
        )}
      >
        <X className="w-4 h-4" />
        <span className="uppercase tracking-wide">{t('menu.back')}</span>
      </button>
      </div>
    </ErrorBoundary>
  );
}

