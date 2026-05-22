import { useState, ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { GlobalTicker } from './GlobalTicker';
import { useGameContext } from '@/contexts/GameContext';
import type { NavigationModule } from '@/types';

interface AppShellProps {
  children: ReactNode;
  activeModule: NavigationModule;
  onNavigate: (module: NavigationModule) => void;
  onTurnComplete?: () => void;
}

export function AppShell({ children, activeModule, onNavigate, onTurnComplete }: AppShellProps) {
  const [isPaused, setIsPaused] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { eventHistory } = useGameContext();

  const handleTogglePause = () => {
    setIsPaused((prev) => !prev);
  };

  const handleToggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };

  const handleCloseSidebar = () => {
    setIsSidebarOpen(false);
  };

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col md:flex-row bg-deep">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-gradient-to-br from-deep via-black to-deep retro-grid opacity-30 pointer-events-none" />

      {/* Sidebar - Fixed 260px on desktop, drawer on mobile */}
      <Sidebar 
        activeModule={activeModule} 
        onNavigate={onNavigate}
        isOpen={isSidebarOpen}
        onClose={handleCloseSidebar}
      />

      {/* Main Content Area - Fluid width */}
      <div className="flex-1 h-full overflow-hidden flex flex-col relative min-w-0 z-10">
        {/* Status Bar - Fixed 60px height */}
        <StatusBar 
          isPaused={isPaused} 
          onTogglePause={handleTogglePause} 
          onTurnComplete={onTurnComplete}
          onToggleSidebar={handleToggleSidebar}
        />

        {/* Content - Scrollable */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden min-w-0">
          {children}
        </main>
      </div>

      {/* Global Ticker - Fixed at bottom */}
      <GlobalTicker events={eventHistory} />
    </div>
  );
}

