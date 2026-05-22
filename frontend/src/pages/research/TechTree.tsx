/**
 * TechTree - 技术树研发中心
 * 可视化技术依赖关系图，支持点击开始研发
 */

import React, { useState, useEffect } from 'react';
import { useGameContext } from '@/contexts/GameContext';
import { getTechTree, startResearch, type TechNode, type TechTree as TechTreeType } from '@/services/techService';
import { FlaskConical, Lock, Zap, CheckCircle, Clock, BookOpen } from 'lucide-react';
import { ProjectStarterWizard } from './ProjectStarterWizard';
import { ReverseEngineeringLab } from './ReverseEngineeringLab';

export const TechTree: React.FC = () => {
  const { gameState } = useGameContext();
  const [techTree, setTechTree] = useState<TechTreeType | null>(null);
  const [selectedNode, setSelectedNode] = useState<TechNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'tech' | 'projects' | 'reverse'>('tech');
  const companyId = 1; // TODO: 从GameContext获取

  useEffect(() => {
    loadTechTree();
  }, []);

  const loadTechTree = async () => {
    setLoading(true);
    try {
      const tree = await getTechTree();
      // 计算每个节点的状态
      const nodesWithStatus = tree.nodes.map((node) => ({
        ...node,
        status: calculateNodeStatus(node, tree.nodes),
      }));
      setTechTree({
        ...tree,
        nodes: nodesWithStatus,
      });
    } catch (error) {
      console.error('Failed to load tech tree:', error);
    } finally {
      setLoading(false);
    }
  };

  // 计算节点状态：locked, available, researching, completed
  const calculateNodeStatus = (node: TechNode, allNodes: TechNode[]): TechNode['status'] => {
    // Mock logic: 第一个节点已完成，有直接依赖的为 available，其他为 locked
    if (node.unlock_requirements.length === 0) {
      return 'completed';
    }

    const allParentsCompleted = node.unlock_requirements.every((reqId) => {
      const parent = allNodes.find((n) => n.id === reqId);
      return parent?.status === 'completed';
    });

    return allParentsCompleted ? 'available' : 'locked';
  };

  const handleStartResearch = async (node: TechNode) => {
    if (node.status !== 'available') return;

    // TODO: 从 GameContext 获取 companyId
    const companyId = 1;
    const result = await startResearch(companyId, node.id);

    if (result.success) {
      // 更新节点状态
      if (techTree) {
        const updatedNodes = techTree.nodes.map((n) =>
          n.id === node.id ? { ...n, status: 'researching' as const, progress: 0 } : n
        );
        setTechTree({ ...techTree, nodes: updatedNodes });
      }
    } else {
      alert(`研发失败: ${result.error || result.message}`);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-deep">
        <div className="text-center">
          <FlaskConical className="w-12 h-12 text-accent-primary animate-pulse mx-auto mb-4" />
          <p className="text-secondary font-mono text-sm">加载技术树...</p>
        </div>
      </div>
    );
  }

  if (!techTree) {
    return (
      <div className="h-full flex items-center justify-center bg-deep">
        <p className="text-accent-danger font-mono">无法加载技术树</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-deep">
      {/* Tab Navigation */}
      <div className="flex border-b border-surface-hover">
        <button
          onClick={() => setActiveTab('tech')}
          className={`px-6 py-3 font-mono text-sm transition-colors ${
            activeTab === 'tech'
              ? 'text-accent-primary border-b-2 border-accent-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <FlaskConical className="w-4 h-4 inline mr-2" />
          技术树
        </button>
        <button
          onClick={() => setActiveTab('projects')}
          className={`px-6 py-3 font-mono text-sm transition-colors ${
            activeTab === 'projects'
              ? 'text-accent-primary border-b-2 border-accent-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <BookOpen className="w-4 h-4 inline mr-2" />
          研发项目
        </button>
        <button
          onClick={() => setActiveTab('reverse')}
          className={`px-6 py-3 font-mono text-sm transition-colors ${
            activeTab === 'reverse'
              ? 'text-accent-warning border-b-2 border-accent-warning'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <Zap className="w-4 h-4 inline mr-2" />
          逆向工程
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'tech' && (
          <div className="h-full flex">
            <div className="flex-1 overflow-auto p-8">
              <div className="mb-6">
                <h1 className="text-2xl font-bold text-accent-primary font-mono flex items-center gap-3">
                  <FlaskConical className="w-6 h-6" />
                  研发中心 / RESEARCH CENTER
                </h1>
                <p className="text-muted text-sm mt-2 font-mono">
                  解锁新技术以提升设计能力和生产效率
                </p>
              </div>

              {/* Categories Legend */}
              <div className="flex gap-4 mb-6">
                {Object.entries(techTree.categories).map(([key, category]) => (
                  <div key={key} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: category.color }}
                    />
                    <span className="text-xs text-secondary font-mono">{category.name}</span>
                  </div>
                ))}
              </div>

              {/* Tech Grid (Simple Layout) */}
              <div className="grid grid-cols-3 gap-6">
                {techTree.nodes.map((node) => (
                  <TechNodeCard
                    key={node.id}
                    node={node}
                    category={techTree.categories[node.category]}
                    onSelect={() => setSelectedNode(node)}
                    onStartResearch={() => handleStartResearch(node)}
                    isSelected={selectedNode?.id === node.id}
                  />
                ))}
              </div>

              {/* SVG Connections (Simplified - draw lines between nodes) */}
              <svg className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-30">
                {/* TODO: 根据节点位置绘制连接线 */}
              </svg>
            </div>

            {/* Right Sidebar - Node Details */}
            {selectedNode && (
              <div className="w-96 bg-deep border-l border-surface-hover p-6 overflow-auto">
                <TechNodeDetails node={selectedNode} onClose={() => setSelectedNode(null)} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'projects' && (
          <div className="p-6">
            <ProjectStarterWizard
              companyId={companyId}
              onProjectStarted={(result) => {
                console.log('Project started:', result);
                // 可以显示成功消息或刷新数据
              }}
            />
          </div>
        )}

        {activeTab === 'reverse' && (
          <div className="p-6">
            <ReverseEngineeringLab
              companyId={companyId}
              onReverseEngineerComplete={(result) => {
                console.log('Reverse engineering complete:', result);
                // 可以显示成功消息或刷新数据
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================
// Tech Node Card Component
// ============================================================

interface TechNodeCardProps {
  node: TechNode;
  category: { name: string; color: string };
  onSelect: () => void;
  onStartResearch: () => void;
  isSelected: boolean;
}

const TechNodeCard: React.FC<TechNodeCardProps> = ({
  node,
  category,
  onSelect,
  onStartResearch,
  isSelected,
}) => {
  const getStatusStyle = () => {
    switch (node.status) {
      case 'locked':
        return 'bg-deep border-surface-hover text-muted cursor-not-allowed';
      case 'available':
        return 'bg-deep border-accent-warning/50 text-accent-warning hover:border-accent-warning cursor-pointer';
      case 'researching':
        return 'bg-accent-primary/20 border-accent-primary/50 text-accent-primary animate-pulse';
      case 'completed':
        return 'bg-deep border-accent-primary text-accent-glow';
      default:
        return 'bg-deep border-surface-hover';
    }
  };

  const getStatusIcon = () => {
    switch (node.status) {
      case 'locked':
        return <Lock className="w-4 h-4" />;
      case 'available':
        return <Zap className="w-4 h-4" />;
      case 'researching':
        return <Clock className="w-4 h-4 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4" />;
    }
  };

  return (
    <div
      className={`relative p-4 rounded-lg border-2 transition-all ${getStatusStyle()} ${
        isSelected ? 'ring-2 ring-accent-primary' : ''
      }`}
      onClick={onSelect}
    >
      {/* Category Badge */}
      <div className="flex items-center justify-between mb-2">
        <div
          className="px-2 py-1 rounded text-xs font-mono font-bold"
          style={{
            backgroundColor: category.color + '20',
            color: category.color,
          }}
        >
          {category.name}
        </div>
        {getStatusIcon()}
      </div>

      {/* Name */}
      <h3 className="font-bold text-sm mb-1 font-mono">{node.name}</h3>

      {/* Description */}
      <p className="text-xs text-muted mb-3 line-clamp-2">{node.description}</p>

      {/* Cost & Time */}
      <div className="flex items-center justify-between text-xs font-mono">
        <div>
          <span className="text-muted">成本:</span>{' '}
          <span className="text-accent-warning font-bold">${node.cost.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-muted">{node.research_time_turns}回合</span>
        </div>
      </div>

      {/* Progress Bar (if researching) */}
      {node.status === 'researching' && (
        <div className="mt-2 h-1 bg-surface-hover rounded-full overflow-hidden">
          <div
            className="h-full bg-accent-primary transition-all"
            style={{ width: `${node.progress || 0}%` }}
          />
        </div>
      )}

      {/* Start Research Button */}
      {node.status === 'available' && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onStartResearch();
          }}
          className="mt-3 w-full py-2 bg-accent-warning/20 hover:bg-accent-warning/30 text-accent-warning rounded text-xs font-mono font-bold transition-all"
        >
          开始研发
        </button>
      )}
    </div>
  );
};

// ============================================================
// Tech Node Details Sidebar
// ============================================================

interface TechNodeDetailsProps {
  node: TechNode;
  onClose: () => void;
}

const TechNodeDetails: React.FC<TechNodeDetailsProps> = ({ node, onClose }) => {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-accent-primary font-mono">{node.name}</h2>
        <button
          onClick={onClose}
          className="text-muted hover:text-primary text-xl"
        >
          ×
        </button>
      </div>

      <div className="space-y-4">
        {/* Description */}
        <div>
          <h3 className="text-xs text-muted font-mono mb-1">说明</h3>
          <p className="text-sm text-primary">{node.description}</p>
        </div>

        {/* Requirements */}
        {node.unlock_requirements.length > 0 && (
          <div>
            <h3 className="text-xs text-muted font-mono mb-2">前置技术</h3>
            <div className="space-y-1">
              {node.unlock_requirements.map((reqId) => (
                <div
                  key={reqId}
                  className="text-xs px-2 py-1 bg-surface rounded text-secondary font-mono"
                >
                  {reqId}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Effects */}
        <div>
          <h3 className="text-xs text-muted font-mono mb-2">解锁效果</h3>
          <div className="space-y-1 text-xs">
            {Object.entries(node.effects).map(([key, value]) => {
              if (!value) return null;
              return (
                <div key={key} className="flex justify-between">
                  <span className="text-secondary">{formatEffectKey(key)}:</span>
                  <span className="text-accent-primary font-mono font-bold">
                    {Array.isArray(value) ? value.join(', ') : value}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cost */}
        <div className="pt-4 border-t border-surface-hover">
          <div className="flex justify-between mb-2">
            <span className="text-sm text-secondary">研发成本</span>
            <span className="text-lg text-accent-warning font-mono font-bold">
              ${node.cost.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-secondary">所需回合</span>
            <span className="text-lg text-primary font-mono font-bold">
              {node.research_time_turns}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper: Format effect keys
function formatEffectKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

