import { GlobalTicker } from '@/components/layout/GlobalTicker';
import { NextTurnButton } from '@/components/ui/NextTurnButton';
import { NetworkTopology } from '@/components/ui/NetworkTopology';
import { FinancialTerminal } from '@/components/ui/FinancialTerminal';
import { CompetitorRadar } from '@/components/ui/CompetitorRadar';
import type { EventLog } from '@/types';

/**
 * Component Preview Page
 * 用于展示和测试新创建的 Dashboard 组件
 */
export function ComponentPreview() {
  // Mock event data
  const mockEvents: EventLog[] = [
    {
      id: 1,
      turn_number: 10,
      event_type: 'news',
      title: 'New factory opened in Europe',
      description: 'Your company has opened a new factory in Europe',
      severity: 'info',
      created_at: new Date().toISOString(),
    },
    {
      id: 2,
      turn_number: 11,
      event_type: 'warning',
      title: 'Market share declining in Asia',
      description: 'Your market share is declining in Asia',
      severity: 'warning',
      created_at: new Date().toISOString(),
    },
    {
      id: 3,
      turn_number: 12,
      event_type: 'alert',
      title: 'CRITICAL: Cash flow negative',
      description: 'Your cash flow has turned negative',
      severity: 'critical',
      created_at: new Date().toISOString(),
    },
  ];

  return (
    <div className="w-full h-screen bg-slate-950 p-8 overflow-auto pb-20">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-cyan-400 mb-2">
            Dashboard Components Preview
          </h1>
          <p className="text-slate-400">
            展示所有新创建的组件（使用 Mock 数据）
          </p>
        </div>

        {/* Network Topology */}
        <section>
          <h2 className="text-xl font-semibold text-slate-300 mb-4">
            1. Network Topology
          </h2>
          <div className="h-[400px] border border-slate-800 rounded-lg">
            <NetworkTopology />
          </div>
        </section>

        {/* Financial Terminal */}
        <section>
          <h2 className="text-xl font-semibold text-slate-300 mb-4">
            2. Financial Terminal
          </h2>
          <div className="h-[400px] border border-slate-800 rounded-lg">
            <FinancialTerminal />
          </div>
        </section>

        {/* Competitor Radar */}
        <section>
          <h2 className="text-xl font-semibold text-slate-300 mb-4">
            3. Competitor Radar
          </h2>
          <div className="h-[400px] border border-slate-800 rounded-lg">
            <CompetitorRadar />
          </div>
        </section>

        {/* Next Turn Button */}
        <section>
          <h2 className="text-xl font-semibold text-slate-300 mb-4">
            4. Next Turn Button
          </h2>
          <div className="flex justify-center items-center h-[300px] border border-slate-800 rounded-lg bg-slate-900/30">
            <NextTurnButton
              onTurnComplete={() =>
                console.log('[Preview] Turn completed!')
              }
            />
          </div>
        </section>

        {/* Global Ticker */}
        <section>
          <h2 className="text-xl font-semibold text-slate-300 mb-4">
            5. Global Ticker
          </h2>
          <div className="relative h-[100px] border border-slate-800 rounded-lg overflow-hidden">
            <GlobalTicker events={mockEvents} />
          </div>
        </section>
      </div>
    </div>
  );
}


