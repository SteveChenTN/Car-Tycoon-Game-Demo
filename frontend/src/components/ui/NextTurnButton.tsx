import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useLanguage } from '@/contexts/LanguageContext';
import { useGameContext } from '@/contexts/GameContext';
import { nextTurn } from '@/services/gameApi';

interface NextTurnButtonProps {
  onTurnComplete?: () => void;
  disabled?: boolean;
}

const HOLD_DURATION = 1000; // 1 second in milliseconds

export function NextTurnButton({ onTurnComplete, disabled = false }: NextTurnButtonProps) {
  const { t } = useLanguage();
  const { refreshGameState } = useGameContext();
  const [isHolding, setIsHolding] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [flashComplete, setFlashComplete] = useState(false);
  
  const holdTimerRef = useRef<NodeJS.Timeout | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);

  const clearTimers = () => {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  const handleMouseDown = () => {
    if (disabled || isProcessing) return;

    setIsHolding(true);
    setProgress(0);
    startTimeRef.current = Date.now();

    // Update progress smoothly
    progressIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTimeRef.current;
      const newProgress = Math.min((elapsed / HOLD_DURATION) * 100, 100);
      setProgress(newProgress);
    }, 16); // ~60fps

    // Trigger action when hold duration is complete
    holdTimerRef.current = setTimeout(async () => {
      setIsHolding(false);
      setIsProcessing(true);
      clearTimers();

      try {
        // Call the backend API using the gameApi service
        const result = await nextTurn();
        
        if (result.success) {
          // Flash white on success
          setFlashComplete(true);
          
          console.log('[NextTurnButton] Turn advanced successfully, refreshing game state...');
          
          // Refresh game state after a delay to ensure backend has processed
          // Increased delay to 1000ms to ensure backend has committed all changes
          setTimeout(() => {
            console.log('[NextTurnButton] Calling refreshGameState()...');
            refreshGameState();
          }, 1000);
          
          setTimeout(() => {
            setFlashComplete(false);
            setProgress(0);
            setIsProcessing(false);
          }, 300);

          // Trigger callback
          if (onTurnComplete) {
            onTurnComplete();
          }
        } else {
          console.error('[NextTurnButton] Turn advance failed:', result.error);
          setIsProcessing(false);
          setProgress(0);
        }
      } catch (error) {
        console.error('[NextTurnButton] Failed to process turn:', error);
        setIsProcessing(false);
        setProgress(0);
      }
    }, HOLD_DURATION);
  };

  const handleMouseUp = () => {
    if (!isHolding) return;
    
    setIsHolding(false);
    setProgress(0);
    clearTimers();
  };

  const handleMouseLeave = () => {
    if (!isHolding) return;
    
    setIsHolding(false);
    setProgress(0);
    clearTimers();
  };

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, []);

  return (
    <div className="relative">
      <motion.button
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onTouchStart={handleMouseDown}
        onTouchEnd={handleMouseUp}
        disabled={disabled || isProcessing}
        className={`
          relative w-40 h-40 rounded-full 
          flex items-center justify-center
          font-mono font-bold text-sm tracking-wider
          transition-all duration-200
          ${
            disabled || isProcessing
              ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
              : flashComplete
              ? 'bg-white text-black shadow-[0_0_30px_rgba(255,255,255,0.8)]'
              : isHolding
              ? 'bg-cyan-600 text-white shadow-[0_0_20px_rgba(6,182,212,0.6)]'
              : 'bg-slate-900 text-cyan-400 border-2 border-cyan-500/50 hover:border-cyan-400 hover:shadow-[0_0_15px_rgba(6,182,212,0.4)]'
          }
        `}
        whileHover={!disabled && !isProcessing ? { scale: 1.05 } : {}}
        whileTap={!disabled && !isProcessing ? { scale: 0.98 } : {}}
      >
        {/* Background Circle */}
        <div className="absolute inset-2 rounded-full border border-slate-700/50" />

        {/* Progress Ring */}
        <svg
          className="absolute inset-0 -rotate-90"
          viewBox="0 0 160 160"
        >
          <circle
            cx="80"
            cy="80"
            r="70"
            fill="none"
            stroke="rgba(6, 182, 212, 0.1)"
            strokeWidth="4"
          />
          <motion.circle
            cx="80"
            cy="80"
            r="70"
            fill="none"
            stroke="#06b6d4"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={2 * Math.PI * 70}
            strokeDashoffset={2 * Math.PI * 70 * (1 - progress / 100)}
            initial={false}
            className="drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]"
          />
        </svg>

        {/* Button Text */}
        <div className="relative z-10 flex flex-col items-center gap-1">
          <span className="text-lg">
            {isProcessing ? t('status.simulating') : t('status.nextWeek')}
          </span>
          {isHolding && (
            <span className="text-xs text-cyan-200">
              {Math.round(progress)}%
            </span>
          )}
        </div>

        {/* Pulse Animation when idle */}
        {!isHolding && !isProcessing && !disabled && (
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-cyan-400"
            animate={{
              scale: [1, 1.1, 1],
              opacity: [0.5, 0, 0.5],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
      </motion.button>

      {/* Hold Instruction */}
      {!disabled && !isProcessing && (
        <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <span className="text-xs text-slate-500 font-mono">
            {t('status.holdToAdvance')}
          </span>
        </div>
      )}
    </div>
  );
}

