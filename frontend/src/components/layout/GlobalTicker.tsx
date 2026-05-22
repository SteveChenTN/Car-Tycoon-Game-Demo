import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { EventLog } from '@/types';

interface GlobalTickerProps {
  events: EventLog[];
}

export function GlobalTicker({ events }: GlobalTickerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Keep only the latest 20 events for performance
  const recentEvents = events.slice(-20).reverse();

  return (
    <div className="fixed bottom-0 left-0 right-0 h-10 bg-slate-950 border-t border-cyan-500/30 z-50 overflow-hidden">
      <div className="relative h-full">
        {/* Scrolling Marquee */}
        <div
          ref={containerRef}
          className="flex items-center h-full gap-8 px-4 animate-scroll"
        >
          <AnimatePresence mode="popLayout">
            {recentEvents.map((event) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-2 whitespace-nowrap flex-shrink-0"
              >
                {/* Severity Indicator */}
                <div
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    event.severity === 'critical'
                      ? 'bg-rose-500 animate-pulse'
                      : event.severity === 'warning'
                      ? 'bg-amber-400'
                      : 'bg-cyan-400'
                  }`}
                />

                {/* Event Content */}
                <span
                  className={`font-mono text-xs ${
                    event.severity === 'critical'
                      ? 'text-rose-400'
                      : event.severity === 'warning'
                      ? 'text-amber-400'
                      : 'text-cyan-400'
                  }`}
                >
                  {event.event_type === 'news' ? '📰' : '⚠️'} {event.title}
                </span>

                {/* Separator */}
                <span className="text-slate-600 mx-2">|</span>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Fallback Message */}
          {recentEvents.length === 0 && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-slate-600 animate-pulse" />
              <span className="font-mono text-xs text-slate-500">
                Awaiting market data...
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Gradient Fade Effect */}
      <div className="absolute inset-y-0 left-0 w-20 bg-gradient-to-r from-slate-950 to-transparent pointer-events-none" />
      <div className="absolute inset-y-0 right-0 w-20 bg-gradient-to-l from-slate-950 to-transparent pointer-events-none" />
    </div>
  );
}

