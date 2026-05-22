import { Play, Pause, TrendingUp, TrendingDown, Menu } from 'lucide-react';
import { useGameContext } from '@/contexts/GameContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { formatCurrency, formatGameDate } from '@/utils/formatters';
import { cn } from '@/lib/utils';
import { NextTurnButton } from '@/components/ui/NextTurnButton';

interface StatusBarProps {
  isPaused: boolean;
  onTogglePause: () => void;
  onTurnComplete?: () => void;
  onToggleSidebar?: () => void;
}

export function StatusBar({ isPaused, onTogglePause, onTurnComplete, onToggleSidebar }: StatusBarProps) {
  const { gameState, isConnected } = useGameContext();
  const { t } = useLanguage();

  console.log('[StatusBar] Render - gameState:', gameState);
  console.log('[StatusBar] isConnected:', isConnected);

  // 从gameState获取真实数据
  const companyCash = gameState?.playerCompany?.cash;
  // GDP趋势：如果API不提供，暂时隐藏
  const gdpTrend: number | null = null; // TODO: 从API获取GDP趋势数据

  // 防御性检查：如果gameState不存在，显示默认值
  const displayYear = gameState?.current_year ?? 0;
  const displayMonth = gameState?.current_month ?? 0;
  const displayWeek = gameState?.current_week ?? 0;
  const displayTurn = gameState?.turn_number ?? 0;

  console.log('[StatusBar] Display values:', { 
    displayYear, 
    displayMonth, 
    displayWeek, 
    displayTurn,
    companyCash,
    formattedDate: formatGameDate(displayYear, displayMonth, displayWeek),
    formattedCash: companyCash !== undefined ? formatCurrency(companyCash) : '---'
  });

  return (
    <header className="h-[60px] flex items-center justify-between px-4 md:px-6 bg-surface border-b border-surface-hover">
      {/* Left: Hamburger (Mobile) + Date & Turn */}
      <div className="flex items-center gap-4 md:gap-6">
        {/* Hamburger Button - Mobile Only */}
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="md:hidden p-2 text-secondary hover:text-accent-primary transition-colors"
            aria-label="Toggle sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="flex flex-col">
          <span className="text-xs text-muted uppercase tracking-wider">{t('status.date')}</span>
          <span className="text-sm font-mono text-accent-primary">
            {gameState && displayYear > 0
              ? formatGameDate(displayYear, displayMonth, displayWeek)
              : 'Loading...'}
          </span>
        </div>

        <div className="h-8 w-px bg-surface-hover hidden sm:block" />

        <div className="flex flex-col hidden sm:flex">
          <span className="text-xs text-muted uppercase tracking-wider">{t('status.turn')}</span>
          <span className="text-sm font-mono text-primary">
            {displayTurn}
          </span>
        </div>
      </div>

      {/* Center: Cash */}
      <div className="flex flex-col items-center hidden md:flex">
        <span className="text-xs text-muted uppercase tracking-wider">{t('status.cash')}</span>
        <span className="text-lg font-mono font-bold text-accent-success">
          {companyCash !== undefined ? formatCurrency(companyCash) : '---'}
        </span>
      </div>

      {/* Right: GDP Trend & Controls */}
      <div className="flex items-center gap-3 md:gap-6">
        {/* GDP Trend - 暂时隐藏，等待API支持 */}
        {gdpTrend !== null && (
          <>
            <div className="flex items-center gap-2 hidden lg:flex">
              <span className="text-xs text-muted uppercase tracking-wider">{t('status.worldGDP')}</span>
              <div className={cn(
                'flex items-center gap-1 font-mono text-sm',
                gdpTrend >= 0 ? 'text-accent-success' : 'text-accent-danger'
              )}>
                {gdpTrend >= 0 ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                <span>{gdpTrend >= 0 ? '+' : ''}{(gdpTrend * 100).toFixed(1)}%</span>
              </div>
            </div>
            <div className="h-8 w-px bg-surface-hover hidden lg:block" />
          </>
        )}

        {/* Next Turn Button */}
        <NextTurnButton onTurnComplete={onTurnComplete} disabled={isPaused} />

        <div className="h-8 w-px bg-surface-hover hidden md:block" />

        {/* Pause/Play Button */}
        <button
          onClick={onTogglePause}
          className={cn(
            'flex items-center gap-2 px-3 md:px-4 py-2 rounded transition-colors',
            isPaused
              ? 'bg-accent-success/20 text-accent-success hover:bg-accent-success/30'
              : 'bg-accent-warning/20 text-accent-warning hover:bg-accent-warning/30'
          )}
        >
          {isPaused ? (
            <>
              <Play className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase hidden sm:inline">{t('status.resume')}</span>
            </>
          ) : (
            <>
              <Pause className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase hidden sm:inline">{t('status.pause')}</span>
            </>
          )}
        </button>

        {/* Connection Status */}
        <div
          className={cn(
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-accent-success' : 'bg-accent-danger'
          )}
          title={isConnected ? t('status.connected') : t('status.disconnected')}
        />
      </div>
    </header>
  );
}

