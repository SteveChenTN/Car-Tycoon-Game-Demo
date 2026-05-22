import { useState, useEffect } from 'react';
import { Play, Save, FolderOpen, Settings, Home, X } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { saveGame, listSaves, loadGame, type SaveInfo } from '@/services/gameApi';
import { cn } from '@/lib/utils';

// ============================================================
// Types
// ============================================================

interface PauseMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onMainMenu?: () => void;
}

type PauseScreen = 'main' | 'save' | 'load' | 'settings';

// ============================================================
// Pause Menu Component
// ============================================================

export function PauseMenu({ isOpen, onClose, onMainMenu }: PauseMenuProps) {
  const { t, language, setLanguage } = useLanguage();
  const [currentScreen, setCurrentScreen] = useState<PauseScreen>('main');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  // === Handlers ===

  const handleClose = () => {
    setCurrentScreen('main');
    setError(null);
    setSuccessMessage(null);
    onClose();
  };

  const handleBack = () => {
    setCurrentScreen('main');
    setError(null);
    setSuccessMessage(null);
  };

  const handleSaveGame = async (saveName: string) => {
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await saveGame(saveName);
      if (result.success) {
        setSuccessMessage(t('save.success'));
        setTimeout(() => {
          handleClose();
        }, 1500);
      } else {
        setError(result.error || t('save.error'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('save.error'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadGame = async (filePath: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await loadGame(filePath);
      if (result.success) {
        setSuccessMessage(t('load.success'));
        setTimeout(() => {
          handleClose();
        }, 1500);
      } else {
        setError(result.error || t('load.error'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('load.error'));
    } finally {
      setIsLoading(false);
    }
  };

  // === Screen Renderers ===

  const renderMainScreen = () => (
    <div className="flex flex-col gap-4 w-full">
      <button
        onClick={handleClose}
        className={cn(
          'w-full flex items-center justify-center gap-3 px-6 py-4',
          'bg-cyan-600 hover:bg-cyan-500 text-white font-semibold',
          'rounded border border-cyan-400/50 transition-all'
        )}
      >
        <Play className="w-5 h-5" />
        <span className="text-lg uppercase tracking-wide">{t('pause.resume')}</span>
      </button>

      <button
        onClick={() => setCurrentScreen('save')}
        className={cn(
          'w-full flex items-center justify-center gap-3 px-6 py-4',
          'bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold',
          'rounded border border-slate-600 transition-all'
        )}
      >
        <Save className="w-5 h-5" />
        <span className="text-lg uppercase tracking-wide">{t('pause.save')}</span>
      </button>

      <button
        onClick={() => setCurrentScreen('load')}
        className={cn(
          'w-full flex items-center justify-center gap-3 px-6 py-4',
          'bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold',
          'rounded border border-slate-600 transition-all'
        )}
      >
        <FolderOpen className="w-5 h-5" />
        <span className="text-lg uppercase tracking-wide">{t('pause.load')}</span>
      </button>

      <button
        onClick={() => setCurrentScreen('settings')}
        className={cn(
          'w-full flex items-center justify-center gap-3 px-6 py-4',
          'bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold',
          'rounded border border-slate-600 transition-all'
        )}
      >
        <Settings className="w-5 h-5" />
        <span className="text-lg uppercase tracking-wide">{t('pause.settings')}</span>
      </button>

      {onMainMenu && (
        <>
          <div className="border-t border-slate-700 my-2" />
          <button
            onClick={onMainMenu}
            className={cn(
              'w-full flex items-center justify-center gap-3 px-6 py-4',
              'bg-rose-900/30 hover:bg-rose-900/50 text-rose-300 font-semibold',
              'rounded border border-rose-700/50 transition-all'
            )}
          >
            <Home className="w-5 h-5" />
            <span className="text-lg uppercase tracking-wide">{t('pause.mainMenu')}</span>
          </button>
        </>
      )}
    </div>
  );

  const renderSaveScreen = () => <SaveGameScreen onSave={handleSaveGame} onBack={handleBack} isLoading={isLoading} />;
  const renderLoadScreen = () => <LoadGameScreen onLoad={handleLoadGame} onBack={handleBack} isLoading={isLoading} />;

  const renderSettingsScreen = () => (
    <div className="flex flex-col gap-6 w-full">
      {/* Language Selector */}
      <div className="bg-slate-900/50 border border-slate-700 rounded p-4">
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
        <span className="uppercase tracking-wide">{t('btn.back')}</span>
      </button>
    </div>
  );

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Menu Panel */}
      <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
        <div className="pointer-events-auto w-full max-w-md mx-4">
          <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-slate-800 border-b border-slate-700">
              <h2 className="text-2xl font-bold text-cyan-400 tracking-wider">
                {t('pause.title')}
              </h2>
              <button
                onClick={handleClose}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6">
              {/* Error Display */}
              {error && (
                <div className="mb-4 bg-rose-900/20 border border-rose-500/50 text-rose-300 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              {/* Success Display */}
              {successMessage && (
                <div className="mb-4 bg-emerald-900/20 border border-emerald-500/50 text-emerald-300 px-4 py-3 rounded">
                  {successMessage}
                </div>
              )}

              {/* Screen Content */}
              {currentScreen === 'main' && renderMainScreen()}
              {currentScreen === 'save' && renderSaveScreen()}
              {currentScreen === 'load' && renderLoadScreen()}
              {currentScreen === 'settings' && renderSettingsScreen()}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ============================================================
// Save Game Sub-Component
// ============================================================

interface SaveGameScreenProps {
  onSave: (saveName: string) => void;
  onBack: () => void;
  isLoading: boolean;
}

function SaveGameScreen({ onSave, onBack, isLoading }: SaveGameScreenProps) {
  const { t } = useLanguage();
  const [saveName, setSaveName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (saveName.trim()) {
      onSave(saveName.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full">
      <div>
        <label className="block text-slate-300 font-semibold mb-2">
          {t('save.name')}
        </label>
        <input
          type="text"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          placeholder="My Save"
          disabled={isLoading}
          className={cn(
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded',
            'text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
          autoFocus
        />
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={!saveName.trim() || isLoading}
          className={cn(
            'flex-1 px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold',
            'rounded border border-cyan-400/50 transition-all',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {isLoading ? t('common.loading') : t('btn.save')}
        </button>
        <button
          type="button"
          onClick={onBack}
          disabled={isLoading}
          className={cn(
            'px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300',
            'rounded border border-slate-600 transition-all'
          )}
        >
          {t('btn.cancel')}
        </button>
      </div>
    </form>
  );
}

// ============================================================
// Load Game Sub-Component
// ============================================================

interface LoadGameScreenProps {
  onLoad: (filePath: string) => void;
  onBack: () => void;
  isLoading: boolean;
}

function LoadGameScreen({ onLoad, onBack, isLoading }: LoadGameScreenProps) {
  const { t } = useLanguage();
  const [saves, setSaves] = useState<SaveInfo[]>([]);
  const [isLoadingSaves, setIsLoadingSaves] = useState(true);

  // Load saves on mount
  useEffect(() => {
    const fetchSaves = async () => {
      setIsLoadingSaves(true);
      try {
        const saveList = await listSaves();
        setSaves(saveList);
      } finally {
        setIsLoadingSaves(false);
      }
    };
    fetchSaves();
  }, []);

  return (
    <div className="flex flex-col gap-4 w-full">
      {/* Saves List */}
      <div className="bg-slate-900/50 border border-slate-700 rounded overflow-hidden max-h-64 overflow-y-auto">
        {isLoadingSaves ? (
          <div className="p-6 text-center text-slate-400">{t('common.loading')}</div>
        ) : saves.length === 0 ? (
          <div className="p-6 text-center text-slate-400">{t('load.empty')}</div>
        ) : (
          <div className="divide-y divide-slate-700">
            {saves.map((save, index) => (
              <button
                key={index}
                onClick={() => onLoad(save.file_path)}
                disabled={isLoading}
                className={cn(
                  'w-full px-4 py-3 text-left transition-colors',
                  'hover:bg-slate-800/50 focus:bg-slate-800',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-cyan-400 font-semibold">{save.save_name}</p>
                    {save.metadata && (
                      <p className="text-slate-400 text-sm font-mono">
                        {save.metadata.current_year}/{save.metadata.current_month} - Turn {save.metadata.turn_number}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-slate-400 text-xs">
                      {new Date(save.saved_at).toLocaleString()}
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
        disabled={isLoading}
        className={cn(
          'w-full px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300',
          'rounded border border-slate-600 transition-all'
        )}
      >
        {t('btn.back')}
      </button>
    </div>
  );
}

