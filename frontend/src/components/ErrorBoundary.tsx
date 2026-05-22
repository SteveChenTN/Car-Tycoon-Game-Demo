import React, { Component, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * ErrorBoundary - 错误边界组件
 * 捕获子组件中的JavaScript错误，显示友好的降级UI
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error);
    console.error('[ErrorBoundary] Error info:', errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    
    // 刷新页面重新加载
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认错误UI - 工业风格
      return (
        <div className="h-full w-full flex items-center justify-center bg-slate-950 text-white">
          <div className="max-w-2xl p-8">
            {/* 错误图标 */}
            <div className="flex items-center justify-center mb-6">
              <div className="relative">
                <div className="absolute inset-0 bg-red-500 blur-xl opacity-30 animate-pulse" />
                <AlertTriangle className="w-24 h-24 text-red-500 relative z-10" />
              </div>
            </div>

            {/* 错误标题 */}
            <h1 className="text-3xl font-bold font-mono text-red-400 text-center mb-4 uppercase tracking-wider">
              ⚠️ System Malfunction
            </h1>
            
            <p className="text-slate-400 text-center mb-6 font-mono text-sm">
              系统检测到严重故障。请联系技术支持部门。
            </p>

            {/* 错误详情（开发模式） */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className="bg-slate-900 border border-red-500/30 rounded p-4 mb-6 overflow-auto max-h-64">
                <h3 className="text-red-400 font-mono text-sm font-bold mb-2">
                  DEBUG INFO:
                </h3>
                <pre className="text-xs text-red-300 font-mono whitespace-pre-wrap">
                  {this.state.error.toString()}
                </pre>
                {this.state.errorInfo && (
                  <pre className="text-xs text-slate-500 font-mono whitespace-pre-wrap mt-2">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex gap-4 justify-center">
              <button
                onClick={this.handleReset}
                className="bg-red-600 hover:bg-red-500 px-6 py-3 rounded font-mono text-sm font-bold transition-colors uppercase tracking-wider"
              >
                🔄 重新启动系统
              </button>
              
              <button
                onClick={() => window.history.back()}
                className="bg-slate-700 hover:bg-slate-600 px-6 py-3 rounded font-mono text-sm font-bold transition-colors uppercase tracking-wider"
              >
                ← 返回上一页
              </button>
            </div>

            {/* 诊断信息 */}
            <div className="mt-8 text-center">
              <p className="text-slate-600 font-mono text-xs">
                错误时间: {new Date().toLocaleString('zh-CN')}
              </p>
              <p className="text-slate-600 font-mono text-xs mt-1">
                错误类型: {this.state.error?.name || 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}


