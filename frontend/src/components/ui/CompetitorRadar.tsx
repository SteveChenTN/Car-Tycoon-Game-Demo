import { useMemo } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import type { Company } from '@/types';

interface CompetitorRadarProps {
  playerCompany?: Company;
  rivalCompany?: Company;
}

interface RadarDataPoint {
  metric: string;
  player: number;
  rival: number;
  fullMark: number;
}

// Mock data generator
function generateMockData(): RadarDataPoint[] {
  return [
    {
      metric: 'Tech',
      player: 65 + Math.random() * 20,
      rival: 55 + Math.random() * 25,
      fullMark: 100,
    },
    {
      metric: 'Brand',
      player: 45 + Math.random() * 30,
      rival: 60 + Math.random() * 20,
      fullMark: 100,
    },
    {
      metric: 'Cash',
      player: 55 + Math.random() * 25,
      rival: 50 + Math.random() * 30,
      fullMark: 100,
    },
    {
      metric: 'Quality',
      player: 70 + Math.random() * 20,
      rival: 55 + Math.random() * 25,
      fullMark: 100,
    },
    {
      metric: 'Market',
      player: 40 + Math.random() * 30,
      rival: 45 + Math.random() * 30,
      fullMark: 100,
    },
  ];
}

function normalizeToScale(value: number, max: number): number {
  return Math.min(100, (value / max) * 100);
}

function companyToRadarData(player?: Company, rival?: Company): RadarDataPoint[] {
  if (!player || !rival) {
    return generateMockData();
  }

  const maxCash = Math.max(player.cash, rival.cash, 1000000);
  
  return [
    {
      metric: 'Tech',
      player: player.tech_level || 50,
      rival: rival.tech_level || 50,
      fullMark: 100,
    },
    {
      metric: 'Brand',
      player: player.brand_strength || 50,
      rival: rival.brand_strength || 50,
      fullMark: 100,
    },
    {
      metric: 'Cash',
      player: normalizeToScale(player.cash, maxCash),
      rival: normalizeToScale(rival.cash, maxCash),
      fullMark: 100,
    },
    {
      metric: 'Quality',
      player: player.quality_rating || 50,
      rival: rival.quality_rating || 50,
      fullMark: 100,
    },
    {
      metric: 'Market',
      player: (player.market_share || 5) * 10,
      rival: (rival.market_share || 5) * 10,
      fullMark: 100,
    },
  ];
}

export function CompetitorRadar({ playerCompany, rivalCompany }: CompetitorRadarProps) {
  const data = useMemo(() => {
    return companyToRadarData(playerCompany, rivalCompany);
  }, [playerCompany, rivalCompany]);

  const playerName = playerCompany?.name || 'Your Company';
  const rivalName = rivalCompany?.name || 'AI Rival';

  return (
    <div className="h-full flex flex-col bg-slate-950/50 rounded-lg border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
          <span className="text-xs font-mono text-amber-400 uppercase tracking-wider">
            Competitor Analysis
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="px-4 py-2 flex items-center justify-center gap-6 border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-cyan-400 rounded" />
          <span className="text-xs font-mono text-slate-400">{playerName}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-rose-400 rounded" />
          <span className="text-xs font-mono text-slate-400">{rivalName}</span>
        </div>
      </div>

      {/* Radar Chart */}
      <div className="flex-1 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data}>
            <PolarGrid stroke="#334155" strokeWidth={0.5} />
            <PolarAngleAxis
              dataKey="metric"
              tick={{
                fill: '#94a3b8',
                fontSize: 12,
                fontFamily: 'monospace',
              }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{
                fill: '#475569',
                fontSize: 10,
                fontFamily: 'monospace',
              }}
              tickCount={6}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '4px',
                fontSize: '12px',
                fontFamily: 'monospace',
              }}
              formatter={(value: number) => value.toFixed(1)}
            />
            <Radar
              name={playerName}
              dataKey="player"
              stroke="#06b6d4"
              fill="#06b6d4"
              fillOpacity={0.3}
              strokeWidth={2}
            />
            <Radar
              name={rivalName}
              dataKey="rival"
              stroke="#f43f5e"
              fill="#f43f5e"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Stats */}
      <div className="px-4 py-2 border-t border-slate-800/50 flex justify-around text-xs font-mono">
        <div className="text-center">
          <div className="text-slate-500">Advantage</div>
          <div className="text-cyan-400 font-bold">
            {data.filter(d => d.player > d.rival).length}/5
          </div>
        </div>
        <div className="text-center">
          <div className="text-slate-500">Behind</div>
          <div className="text-rose-400 font-bold">
            {data.filter(d => d.player < d.rival).length}/5
          </div>
        </div>
      </div>
    </div>
  );
}


