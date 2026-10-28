import React from 'react';
import { Play, Pause, RotateCcw, FastForward, Activity } from 'lucide-react';

interface ReplayControlProps {
  isPlaying: boolean;
  onTogglePlay: () => void;
  speed: number;
  onSetSpeed: (s: number) => void;
  onReset: () => void;
  currentReplayCount: number;
  totalAlerts: number;
}

export const ReplayControl: React.FC<ReplayControlProps> = ({
  isPlaying,
  onTogglePlay,
  speed,
  onSetSpeed,
  onReset,
  currentReplayCount,
  totalAlerts,
}) => {
  const percent = totalAlerts > 0 ? Math.min(100, (currentReplayCount / totalAlerts) * 100) : 0;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 bg-slate-900/95 border border-slate-700/80 rounded-2xl px-5 py-2.5 shadow-2xl backdrop-blur-md flex items-center gap-4 text-xs">
      <div className="flex items-center gap-2">
        <button
          onClick={onTogglePlay}
          className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-white transition ${
            isPlaying ? 'bg-amber-600 hover:bg-amber-500' : 'bg-indigo-600 hover:bg-indigo-500'
          }`}
          title={isPlaying ? 'Pause Replay' : 'Play Live Alert Stream Replay'}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>

        <button
          onClick={onReset}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          title="Reset Replay Stream"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
        <span>Stream:</span>
        <strong className="text-slate-200">{currentReplayCount.toLocaleString()}</strong>
        <span>/ {totalAlerts.toLocaleString()}</span>
      </div>

      {/* Progress Bar */}
      <div className="w-36 md:w-56 h-2 rounded-full bg-slate-800 overflow-hidden relative">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 rounded-full transition-all duration-150"
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Speed Controls */}
      <div className="flex items-center gap-1">
        {[1, 5, 25, 100].map((s) => (
          <button
            key={s}
            onClick={() => onSetSpeed(s)}
            className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold transition ${
              speed === s
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
};
