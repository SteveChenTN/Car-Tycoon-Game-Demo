import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { PowerCurvePoint } from '../../utils/engineeringCalc';

interface DynoGraphProps {
  data: PowerCurvePoint[];
  maxRpm?: number; // 最大安全转速，用于设置X轴域
  className?: string;
}

/**
 * DynoGraph - 引擎动力曲线图表
 * 显示扭矩和功率随转速变化的曲线
 */
export const DynoGraph: React.FC<DynoGraphProps> = ({ data, maxRpm, className = '' }) => {
  // 如果没有数据，显示占位符
  if (!data || data.length === 0) {
    return (
      <div className={`flex items-center justify-center bg-slate-900 border border-cyan-500/30 rounded ${className}`}>
        <div className="text-center text-slate-500">
          <div className="text-5xl mb-4">📊</div>
          <p className="font-mono text-sm">调整参数以查看动力曲线</p>
        </div>
      </div>
    );
  }

  // 自定义 Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-800 border border-cyan-500 px-4 py-2 rounded shadow-lg">
          <p className="font-mono text-cyan-400 text-sm font-bold mb-1">
            {data.rpm} RPM
          </p>
          <p className="font-mono text-orange-400 text-xs">
            扭矩: {data.torque} Nm
          </p>
          <p className="font-mono text-purple-400 text-xs">
            功率: {data.power} HP
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`bg-slate-900 border border-cyan-500/30 rounded p-4 ${className}`}>
      <div className="mb-2">
        <h3 className="font-mono text-cyan-400 text-sm font-bold uppercase tracking-wide">
          Dyno Chart - 动力曲线
        </h3>
      </div>
      
      <ResponsiveContainer width="100%" height={350}>
        <LineChart
          data={data}
          margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
          {...(maxRpm ? { domain: { x: [0, maxRpm] } } : {})}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          
          <XAxis
            dataKey="rpm"
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }}
            {...(maxRpm ? { domain: [0, maxRpm] } : {})}
            label={{
              value: 'RPM (转速)',
              position: 'insideBottom',
              offset: -5,
              style: { fill: '#64748b', fontSize: 12, fontFamily: 'monospace' }
            }}
          />
          
          <YAxis
            yAxisId="left"
            stroke="#fb923c"
            tick={{ fill: '#fb923c', fontSize: 11, fontFamily: 'monospace' }}
            label={{
              value: 'Torque (Nm)',
              angle: -90,
              position: 'insideLeft',
              style: { fill: '#fb923c', fontSize: 12, fontFamily: 'monospace' }
            }}
          />
          
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#a78bfa"
            tick={{ fill: '#a78bfa', fontSize: 11, fontFamily: 'monospace' }}
            label={{
              value: 'Power (HP)',
              angle: 90,
              position: 'insideRight',
              style: { fill: '#a78bfa', fontSize: 12, fontFamily: 'monospace' }
            }}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          <Legend
            wrapperStyle={{
              fontFamily: 'monospace',
              fontSize: '12px',
              paddingTop: '10px'
            }}
          />
          
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="torque"
            stroke="#fb923c"
            strokeWidth={2}
            dot={false}
            name="扭矩 (Nm)"
            animationDuration={500}
          />
          
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="power"
            stroke="#a78bfa"
            strokeWidth={2}
            dot={false}
            name="功率 (HP)"
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
      
      <div className="mt-3 grid grid-cols-2 gap-4 text-xs font-mono">
        <div className="bg-slate-800/50 rounded px-3 py-2 border border-orange-500/30">
          <span className="text-slate-400">峰值扭矩:</span>
          <span className="text-orange-400 font-bold ml-2">
            {Math.max(...data.map(d => d.torque))} Nm
          </span>
        </div>
        <div className="bg-slate-800/50 rounded px-3 py-2 border border-purple-500/30">
          <span className="text-slate-400">峰值功率:</span>
          <span className="text-purple-400 font-bold ml-2">
            {Math.max(...data.map(d => d.power))} HP
          </span>
        </div>
      </div>
    </div>
  );
};

