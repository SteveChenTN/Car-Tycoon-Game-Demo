import React, { useState, useEffect, useRef } from 'react';
import { useEngineering } from '../../contexts/EngineeringContext';
import { MessageSquare, X, Minimize2, Maximize2 } from 'lucide-react';

/**
 * ChiefEngineer - AI总工程师助手
 * 固定右侧边栏，监控工程状态，提供响应式建议
 */
export const ChiefEngineer: React.FC = () => {
  const { aiMessages, clearAIMessages } = useEngineering();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [aiMessages]);

  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="fixed bottom-6 right-6 bg-cyan-600 hover:bg-cyan-500 text-white rounded-full p-4 shadow-lg transition-all z-50 flex items-center gap-2 font-mono text-sm font-bold"
      >
        <MessageSquare className="w-5 h-5" />
        总工程师
      </button>
    );
  }

  return (
    <div
      className={`fixed right-0 top-0 h-full bg-slate-900 border-l border-cyan-500/50 flex flex-col transition-all duration-300 z-40 ${
        isCollapsed ? 'w-14' : 'w-80'
      }`}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-cyan-900 to-slate-900 border-b border-cyan-500/50 p-3 flex items-center justify-between">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-cyan-400" />
            <span className="font-mono text-sm font-bold text-cyan-400">总工程师 AI</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 hover:bg-cyan-800 rounded transition-colors"
            title={isCollapsed ? '展开' : '收起'}
          >
            {isCollapsed ? (
              <Maximize2 className="w-4 h-4 text-cyan-400" />
            ) : (
              <Minimize2 className="w-4 h-4 text-cyan-400" />
            )}
          </button>
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1 hover:bg-cyan-800 rounded transition-colors"
            title="最小化"
          >
            <X className="w-4 h-4 text-cyan-400" />
          </button>
        </div>
      </div>

      {/* Content (only show when not collapsed) */}
      {!isCollapsed && (
        <>
          {/* Avatar & Intro */}
          <div className="p-4 bg-slate-800/50 border-b border-slate-700">
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center text-2xl flex-shrink-0">
                🤖
              </div>
              <div className="flex-1">
                <h3 className="font-mono text-sm font-bold text-cyan-400 mb-1">
                  Chief Engineer AI
                </h3>
                <p className="text-xs text-slate-400 font-mono leading-relaxed">
                  实时监控你的设计，给出专业建议。我会在关键时刻主动提醒你。
                </p>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {aiMessages.length === 0 && (
              <div className="text-center text-slate-500 font-mono text-xs mt-8">
                <div className="text-3xl mb-2">💤</div>
                <p>等待中...</p>
                <p className="mt-1">开始调整参数，我会给你反馈。</p>
              </div>
            )}

            {aiMessages.map((msg, idx) => (
              <AIMessageBubble key={idx} message={msg} />
            ))}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Footer Actions */}
          <div className="p-3 border-t border-slate-700 bg-slate-800/30">
            <button
              onClick={clearAIMessages}
              className="w-full bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-2 rounded text-xs font-mono transition-colors"
            >
              🗑️ 清空消息
            </button>
          </div>
        </>
      )}

      {/* Collapsed State Icon */}
      {isCollapsed && (
        <div className="flex-1 flex items-center justify-center">
          <div className="transform -rotate-90 whitespace-nowrap font-mono text-xs text-cyan-400 font-bold">
            AI ASSISTANT
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================
// AI Message Bubble
// ============================================================

interface AIMessageBubbleProps {
  message: string;
}

const AIMessageBubble: React.FC<AIMessageBubbleProps> = ({ message }) => {
  // 检测消息类型 (基于emoji或关键词)
  const isWarning = message.includes('⚠️') || message.includes('警告');
  const isError = message.includes('❌') || message.includes('不适配') || message.includes('失败');
  const isSuccess = message.includes('✅') || message.includes('成功') || message.includes('完美');
  const isFire = message.includes('🔥') || message.includes('爆震');

  let bgColor = 'bg-slate-800';
  let borderColor = 'border-slate-600';
  let textColor = 'text-slate-200';

  if (isError) {
    bgColor = 'bg-red-900/30';
    borderColor = 'border-red-500';
    textColor = 'text-red-300';
  } else if (isWarning || isFire) {
    bgColor = 'bg-yellow-900/30';
    borderColor = 'border-yellow-500';
    textColor = 'text-yellow-300';
  } else if (isSuccess) {
    bgColor = 'bg-green-900/30';
    borderColor = 'border-green-500';
    textColor = 'text-green-300';
  }

  return (
    <div
      className={`${bgColor} border ${borderColor} rounded-lg p-3 animate-fadeIn`}
    >
      <p className={`text-xs font-mono ${textColor} leading-relaxed`}>
        {message}
      </p>
      <div className="text-[10px] text-slate-500 font-mono mt-2">
        {new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
      </div>
    </div>
  );
};

// ============================================================
// CSS Animation (add to your global CSS or inline)
// ============================================================
// You can add this to your index.css:
// @keyframes fadeIn {
//   from { opacity: 0; transform: translateY(-10px); }
//   to { opacity: 1; transform: translateY(0); }
// }
// .animate-fadeIn {
//   animation: fadeIn 0.3s ease-out;
// }


