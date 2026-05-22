/**
 * ExecutiveRoom - 高管套房
 * 管理董事会成员、外交关系、竞争对手互动
 */

import React, { useState, useEffect } from 'react';
import { useGameContext } from '@/contexts/GameContext';
import {
  getCompanyStaff,
  getCompanyRelations,
  fireStaff,
  performDiplomacyAction,
  type StaffMember,
  type CompanyRelation,
} from '@/services/executiveService';
import {
  Users,
  TrendingUp,
  DollarSign,
  Heart,
  AlertTriangle,
  UserMinus,
  UserPlus,
  Handshake,
  Skull,
  Eye,
} from 'lucide-react';

export const ExecutiveRoom: React.FC = () => {
  const { gameState } = useGameContext();
  const [activeTab, setActiveTab] = useState<'board' | 'diplomacy'>('board');
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [relations, setRelations] = useState<CompanyRelation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // TODO: 从 GameContext 获取 companyId
      const companyId = 1;
      const [staffData, relationsData] = await Promise.all([
        getCompanyStaff(companyId),
        getCompanyRelations(companyId),
      ]);
      setStaff(staffData);
      setRelations(relationsData);
    } catch (error) {
      console.error('Failed to load executive data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFireStaff = async (staffMember: StaffMember) => {
    if (!confirm(`确定要解雇 ${staffMember.name}？需要支付离职费 $${staffMember.severance_cost?.toLocaleString()}`)) {
      return;
    }

    const companyId = 1;
    const result = await fireStaff(companyId, staffMember.id);

    if (result.success) {
      setStaff(staff.filter((s) => s.id !== staffMember.id));
      alert(`已解雇 ${staffMember.name}，支付离职费 $${result.severance_paid?.toLocaleString()}`);
    } else {
      alert(`解雇失败: ${result.error}`);
    }
  };

  const handleDiplomacyAction = async (relation: CompanyRelation, action: string) => {
    const companyId = 1;
    let actionType: 'insult' | 'praise' | 'propose_alliance' | 'spy' | 'headhunt';
    let description = '';
    let cost = 0;

    switch (action) {
      case 'insult':
        actionType = 'insult';
        description = '公开批评对手';
        cost = 0;
        break;
      case 'ally':
        actionType = 'propose_alliance';
        description = '提议结盟';
        cost = 50000;
        break;
      case 'spy':
        actionType = 'spy';
        description = '窃取商业机密';
        cost = 100000;
        break;
      default:
        return;
    }

    if (!confirm(`${description} - ${relation.company_name}\n成本: $${cost.toLocaleString()}`)) {
      return;
    }

    const result = await performDiplomacyAction(companyId, {
      action_type: actionType,
      target_company_id: relation.company_id,
      description,
      cost,
    });

    if (result.success) {
      alert(`行动成功！${result.result || ''}`);
      loadData(); // 重新加载数据
    } else {
      alert(`行动失败: ${result.error}`);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <Users className="w-12 h-12 text-cyan-400 animate-pulse mx-auto mb-4" />
          <p className="text-slate-400 font-mono text-sm">加载高管数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-950">
      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-800 p-6">
        <h1 className="text-2xl font-bold text-cyan-400 font-mono flex items-center gap-3">
          <Users className="w-6 h-6" />
          高管套房 / EXECUTIVE SUITE
        </h1>
        <p className="text-slate-500 text-sm mt-2 font-mono">
          管理董事会成员和外交关系
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-slate-900/50 border-b border-slate-800 px-6 flex gap-2">
        <button
          onClick={() => setActiveTab('board')}
          className={`px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeTab === 'board'
              ? 'bg-cyan-900 text-cyan-400 border-b-2 border-cyan-500'
              : 'text-slate-400 hover:text-cyan-400'
          }`}
        >
          董事会
        </button>
        <button
          onClick={() => setActiveTab('diplomacy')}
          className={`px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeTab === 'diplomacy'
              ? 'bg-purple-900 text-purple-400 border-b-2 border-purple-500'
              : 'text-slate-400 hover:text-purple-400'
          }`}
        >
          外交关系
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === 'board' && (
          <BoardOfDirectors staff={staff} onFireStaff={handleFireStaff} />
        )}
        {activeTab === 'diplomacy' && (
          <DiplomacyPanel relations={relations} onAction={handleDiplomacyAction} />
        )}
      </div>
    </div>
  );
};

// ============================================================
// Board of Directors Component
// ============================================================

interface BoardOfDirectorsProps {
  staff: StaffMember[];
  onFireStaff: (staff: StaffMember) => void;
}

const BoardOfDirectors: React.FC<BoardOfDirectorsProps> = ({ staff, onFireStaff }) => {
  return (
    <div className="grid grid-cols-2 gap-6">
      {staff.map((member) => (
        <StaffCard key={member.id} staff={member} onFire={onFireStaff} />
      ))}

      {/* Hire New Staff Card */}
      <div className="bg-slate-900/30 border-2 border-dashed border-slate-700 rounded-lg p-6 flex flex-col items-center justify-center hover:border-cyan-500 transition-all cursor-pointer">
        <UserPlus className="w-12 h-12 text-slate-600 mb-4" />
        <span className="text-slate-500 font-mono text-sm">招聘新成员</span>
        <span className="text-xs text-slate-700 mt-2">即将推出</span>
      </div>
    </div>
  );
};

// ============================================================
// Staff Card Component
// ============================================================

interface StaffCardProps {
  staff: StaffMember;
  onFire: (staff: StaffMember) => void;
}

const StaffCard: React.FC<StaffCardProps> = ({ staff, onFire }) => {
  const isPlayer = staff.role === 'CEO';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-cyan-500/50 transition-all">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center text-3xl">
            {staff.portrait_icon}
          </div>
          <div>
            <h3 className="font-bold text-cyan-400 font-mono">{staff.name}</h3>
            <span className="text-xs text-slate-500 font-mono">{staff.role}</span>
          </div>
        </div>

        {!isPlayer && (
          <button
            onClick={() => onFire(staff)}
            className="p-2 text-rose-400 hover:bg-rose-900/20 rounded transition-all"
            title="解雇"
          >
            <UserMinus className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Loyalty Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-slate-500 flex items-center gap-1">
            <Heart className="w-3 h-3" />
            忠诚度
          </span>
          <span className="text-slate-300 font-mono font-bold">{staff.loyalty}%</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${
              staff.loyalty >= 70
                ? 'bg-emerald-500'
                : staff.loyalty >= 40
                ? 'bg-amber-500'
                : 'bg-rose-500'
            }`}
            style={{ width: `${staff.loyalty}%` }}
          />
        </div>
      </div>

      {/* Skills */}
      <div className="space-y-2 mb-4">
        {staff.skill_engineering !== undefined && (
          <SkillBar label="工程" value={staff.skill_engineering} />
        )}
        {staff.skill_finance !== undefined && (
          <SkillBar label="财务" value={staff.skill_finance} />
        )}
        {staff.skill_marketing !== undefined && (
          <SkillBar label="市场" value={staff.skill_marketing} />
        )}
        {staff.skill_operations !== undefined && (
          <SkillBar label="运营" value={staff.skill_operations} />
        )}
      </div>

      {/* Salary */}
      <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-500 flex items-center gap-1">
          <DollarSign className="w-3 h-3" />
          月薪
        </span>
        <span className="text-sm text-amber-400 font-mono font-bold">
          ${staff.salary_monthly.toLocaleString()}
        </span>
      </div>
    </div>
  );
};

// ============================================================
// Skill Bar Component
// ============================================================

interface SkillBarProps {
  label: string;
  value: number;
}

const SkillBar: React.FC<SkillBarProps> = ({ label, value }) => {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-slate-500">{label}</span>
        <span className="text-slate-300 font-mono">{value}</span>
      </div>
      <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-cyan-500"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
};

// ============================================================
// Diplomacy Panel Component
// ============================================================

interface DiplomacyPanelProps {
  relations: CompanyRelation[];
  onAction: (relation: CompanyRelation, action: string) => void;
}

const DiplomacyPanel: React.FC<DiplomacyPanelProps> = ({ relations, onAction }) => {
  return (
    <div className="space-y-4">
      {relations.map((relation) => (
        <DiplomacyCard key={relation.company_id} relation={relation} onAction={onAction} />
      ))}
    </div>
  );
};

// ============================================================
// Diplomacy Card Component
// ============================================================

interface DiplomacyCardProps {
  relation: CompanyRelation;
  onAction: (relation: CompanyRelation, action: string) => void;
}

const DiplomacyCard: React.FC<DiplomacyCardProps> = ({ relation, onAction }) => {
  const getStatusColor = () => {
    switch (relation.status) {
      case 'hostile':
        return 'text-rose-400 bg-rose-900/20';
      case 'rival':
        return 'text-orange-400 bg-orange-900/20';
      case 'neutral':
        return 'text-slate-400 bg-slate-800/20';
      case 'friendly':
        return 'text-emerald-400 bg-emerald-900/20';
      case 'allied':
        return 'text-cyan-400 bg-cyan-900/20';
    }
  };

  const getStatusLabel = () => {
    switch (relation.status) {
      case 'hostile':
        return '敌对';
      case 'rival':
        return '竞争';
      case 'neutral':
        return '中立';
      case 'friendly':
        return '友好';
      case 'allied':
        return '同盟';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-cyan-500/50 transition-all">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-bold text-cyan-400 font-mono text-lg">{relation.company_name}</h3>
          <span className={`text-xs font-mono px-2 py-1 rounded ${getStatusColor()}`}>
            {getStatusLabel()}
          </span>
        </div>

        {/* Relation Score */}
        <div className="text-right">
          <div className="text-2xl font-bold font-mono text-slate-300">
            {relation.relation_score > 0 ? '+' : ''}
            {relation.relation_score}
          </div>
          <div className="text-xs text-slate-500">关系分数</div>
        </div>
      </div>

      {/* Relation Bar */}
      <div className="mb-4">
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${
              relation.relation_score >= 50
                ? 'bg-emerald-500'
                : relation.relation_score >= 0
                ? 'bg-slate-500'
                : 'bg-rose-500'
            }`}
            style={{
              width: `${Math.abs(relation.relation_score)}%`,
              marginLeft: relation.relation_score < 0 ? 'auto' : '0',
            }}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onAction(relation, 'insult')}
          className="flex-1 py-2 px-3 bg-rose-900/20 hover:bg-rose-900/40 text-rose-400 rounded text-xs font-mono font-bold transition-all flex items-center justify-center gap-2"
        >
          <Skull className="w-4 h-4" />
          侮辱
        </button>
        <button
          onClick={() => onAction(relation, 'ally')}
          className="flex-1 py-2 px-3 bg-emerald-900/20 hover:bg-emerald-900/40 text-emerald-400 rounded text-xs font-mono font-bold transition-all flex items-center justify-center gap-2"
        >
          <Handshake className="w-4 h-4" />
          结盟
        </button>
        <button
          onClick={() => onAction(relation, 'spy')}
          className="flex-1 py-2 px-3 bg-purple-900/20 hover:bg-purple-900/40 text-purple-400 rounded text-xs font-mono font-bold transition-all flex items-center justify-center gap-2"
        >
          <Eye className="w-4 h-4" />
          间谍
        </button>
      </div>
    </div>
  );
};


