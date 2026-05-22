import { useState, useEffect } from 'react';
import { GameProvider } from './contexts/GameContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { AppShell } from './components/layout/AppShell';
import { MainMenu } from './components/layout/MainMenu';
import { PauseMenu } from './components/layout/PauseMenu';
import { Dashboard } from './pages/Dashboard';
import { EngineeringHub } from './pages/engineering';
import { FactoryManager } from './pages/factory';
import { MarketDashboard } from './pages/market';
import { TechTree } from './pages/research';
import { ExecutiveRoom } from './pages/executive';
import { FinancialReports } from './pages/reports';
import { MonthlyReportModal } from './components/game/MonthlyReportModal';
import { ErrorBoundary } from './components/ErrorBoundary';
import type { NavigationModule } from './types';

function App() {
  const [activeModule, setActiveModule] = useState<NavigationModule>('dashboard');
  const [showMonthlyReport, setShowMonthlyReport] = useState(false);
  const [isGameStarted, setIsGameStarted] = useState(false);
  const [showPauseMenu, setShowPauseMenu] = useState(false);

  // ESC key handler for pause menu
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isGameStarted) {
        setShowPauseMenu((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isGameStarted]);

  // 根据activeModule渲染不同的页面
  const renderContent = () => {
    switch (activeModule) {
      case 'dashboard':
        return <Dashboard />;
      case 'design':
      case 'engineering':
        return <EngineeringHub />;
      case 'factory':
        return <FactoryManager />;
      case 'market':
        return <MarketDashboard />;
      case 'executive':
        return <ExecutiveRoom />;
      case 'research':
        return <TechTree />;
      case 'reports':
        return <FinancialReports />;
      default:
        return <Dashboard />;
    }
  };

  // 处理回合完成（从NextTurnButton触发）
  const handleTurnComplete = () => {
    setShowMonthlyReport(true);
  };

  // 处理游戏开始
  const handleGameStart = () => {
    setIsGameStarted(true);
    // 游戏开始后，等待一小段时间让后端完成加载，然后刷新游戏状态
    setTimeout(() => {
      // 通过 window 事件触发状态刷新
      window.dispatchEvent(new CustomEvent('gameLoaded'));
    }, 500);
  };

  // 处理返回主菜单
  const handleMainMenu = () => {
    setShowPauseMenu(false);
    setIsGameStarted(false);
    setActiveModule('dashboard');
  };

  return (
    <LanguageProvider defaultLanguage="en">
      <GameProvider>
        {/* Main Menu (shown if game not started) */}
        {!isGameStarted && <MainMenu onGameStart={handleGameStart} />}

        {/* Game UI (shown if game started) */}
        {isGameStarted && (
          <>
            <AppShell activeModule={activeModule} onNavigate={setActiveModule} onTurnComplete={handleTurnComplete}>
              <ErrorBoundary>
                {renderContent()}
              </ErrorBoundary>
            </AppShell>
            
            {/* Monthly Report Modal */}
            <MonthlyReportModal 
              isOpen={showMonthlyReport} 
              onClose={() => setShowMonthlyReport(false)} 
            />

            {/* Pause Menu */}
            <PauseMenu
              isOpen={showPauseMenu}
              onClose={() => setShowPauseMenu(false)}
              onMainMenu={handleMainMenu}
            />
          </>
        )}
      </GameProvider>
    </LanguageProvider>
  );
}

export default App;

