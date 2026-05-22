import { useGameContext } from '@/contexts/GameContext';
import { NetworkTopology } from '@/components/ui/NetworkTopology';
import { FinancialTerminal } from '@/components/ui/FinancialTerminal';
import { CompetitorRadar } from '@/components/ui/CompetitorRadar';
import { NextTurnButton } from '@/components/ui/NextTurnButton';
import { formatGameDate } from '@/utils/formatters';

export function Dashboard() {
  const { gameState, latestEvent, isConnected } = useGameContext();

  const handleTurnComplete = () => {
    console.log('[Dashboard] Turn processed successfully');
  };

  return (
    <div className="w-full h-full overflow-auto bg-slate-950">
      {/* Bento Box Grid Layout */}
      <div className="h-full p-4 grid grid-cols-12 grid-rows-12 gap-4">
        {/* Top Status Bar - Full Width */}
        <div className="col-span-12 row-span-1 flex items-center justify-between px-4 bg-slate-900/50 rounded-lg border border-slate-800/50">
          {/* Left: Game Time */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-emerald-400' : 'bg-rose-400'
                } animate-pulse`}
              />
              <span className="text-xs font-mono text-slate-400">
                {isConnected ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>

            {gameState && (
              <>
                <div className="h-4 w-px bg-slate-700" />
                <div className="flex items-center gap-4 font-mono text-sm">
                  <div>
                    <span className="text-slate-500">Date:</span>{' '}
                    <span className="text-cyan-400 font-bold">
                      {formatGameDate(gameState.current_year, gameState.current_month, gameState.current_week)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Turn:</span>{' '}
                    <span className="text-slate-300">{gameState.turn_number}</span>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Right: Latest Event Summary */}
          {latestEvent && (
            <div className="flex items-center gap-3 max-w-md">
              <div
                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  latestEvent.severity === 'critical'
                    ? 'bg-rose-500 animate-pulse'
                    : latestEvent.severity === 'warning'
                    ? 'bg-amber-400'
                    : 'bg-cyan-400'
                }`}
              />
              <span className="text-xs font-mono text-slate-400 truncate">
                {latestEvent.title}
              </span>
            </div>
          )}
        </div>

        {/* Main Network Topology - Large Left Panel */}
        <div className="col-span-7 row-span-7">
          <NetworkTopology />
        </div>

        {/* Financial Terminal - Right Top */}
        <div className="col-span-5 row-span-7">
          <FinancialTerminal />
        </div>

        {/* Competitor Radar - Bottom Left */}
        <div className="col-span-5 row-span-4">
          <CompetitorRadar />
        </div>

        {/* Next Turn Control - Bottom Center */}
        <div className="col-span-4 row-span-4 flex items-center justify-center bg-slate-900/30 rounded-lg border border-slate-800/30">
          <NextTurnButton onTurnComplete={handleTurnComplete} disabled={!isConnected} />
        </div>

        {/* Quick Stats Panel - Bottom Right */}
        <div className="col-span-3 row-span-4 bg-slate-950/50 rounded-lg border border-slate-800/50 p-4 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800/50">
            <div className="w-2 h-2 bg-purple-400 rounded-full" />
            <span className="text-xs font-mono text-purple-400 uppercase tracking-wider">
              Quick Stats
            </span>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500">Active Plants</span>
              <span className="text-sm font-mono text-slate-300 font-bold">
                ---
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500">Models in Prod</span>
              <span className="text-sm font-mono text-slate-300 font-bold">
                ---
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500">R&D Projects</span>
              <span className="text-sm font-mono text-cyan-400 font-bold">
                ---
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-500">Employees</span>
              <span className="text-sm font-mono text-slate-300 font-bold">
                ---
              </span>
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-slate-800/50">
              <span className="text-xs text-slate-500">Global Rank</span>
              <span className="text-sm font-mono text-amber-400 font-bold">
                ---
              </span>
            </div>
          </div>

          {/* Status Indicator */}
          <div className="pt-3 border-t border-slate-800/50">
            <div className="flex items-center gap-2">
              <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-purple-500"
                  style={{ width: '0%' }}
                />
              </div>
            </div>
            <span className="text-xs text-slate-600 mt-1 block">
              Overall Performance
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
