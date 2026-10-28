import React from 'react';

interface HeaderProps {
  rawAlertsCount: number;
  incidentsCount: number;
  reductionPercentage: number;
  incidentRecall: number;
}

export const Header: React.FC<HeaderProps> = ({
  rawAlertsCount = 400,
  incidentsCount = 3,
  reductionPercentage = 99.3,
  incidentRecall = 100.0,
}) => {
  return (
    <header className="border-b-2 border-red-600 bg-black text-white px-6 py-4 shadow-[0_4px_0_#ffffff] font-mono sticky top-0 z-50">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Title & Simple English Explanation */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-red-600 border-2 border-white flex items-center justify-center font-bold text-black text-sm">
            !
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white uppercase tracking-wider font-['Silkscreen']">
                AO-01 // ROOT CAUSE INTELLIGENCE
              </h1>
              <span className="px-1.5 py-0.5 text-[10px] font-bold bg-white text-black uppercase">
                100% REAL DATA
              </span>
            </div>
            <p className="text-xs text-neutral-400 mt-0.5">
              "Four Hundred Alerts, Three Real Incidents" — Automatically collapses alert storms and finds the origin server.
            </p>
          </div>
        </div>

        {/* Minimalist Metrics Badges (ZERO BUTTONS) */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="border-2 border-white px-3 py-1 bg-black shadow-[2px_2px_0px_#ff0033]">
            <span className="text-neutral-400 block text-[9px] uppercase">Raw Alert Storm:</span>
            <span className="text-white font-bold">{rawAlertsCount} Alerts</span>
          </div>

          <div className="border-2 border-red-600 px-3 py-1 bg-neutral-950 shadow-[2px_2px_0px_#ffffff]">
            <span className="text-red-400 block text-[9px] uppercase">Real Incidents:</span>
            <span className="text-white font-bold">{incidentsCount} Incidents</span>
          </div>

          <div className="border border-white/60 px-3 py-1 bg-neutral-950">
            <span className="text-neutral-400 block text-[9px] uppercase">Alert Reduction:</span>
            <span className="text-red-500 font-bold">-{reductionPercentage.toFixed(1)}%</span>
          </div>

          <div className="border border-red-600 px-3 py-1 bg-black">
            <span className="text-neutral-400 block text-[9px] uppercase">Incident Recall:</span>
            <span className="text-white font-bold">{incidentRecall.toFixed(0)}% Safe</span>
          </div>
        </div>
      </div>
    </header>
  );
};
