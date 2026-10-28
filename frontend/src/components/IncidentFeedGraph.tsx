import React from 'react';
import { Incident } from '../types';

interface IncidentFeedGraphProps {
  totalAlerts: number;
  incidents: Incident[];
  reductionRate: number;
}

export const IncidentFeedGraph: React.FC<IncidentFeedGraphProps> = ({
  totalAlerts,
  incidents,
  reductionRate,
}) => {
  const incidentsCount = incidents.length;

  return (
    <div className="w-full bg-black border-2 border-white p-5 shadow-[5px_5px_0px_#ff0033] mb-8 font-mono">
      {/* Top Banner in Simple English */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b-2 border-red-600 pb-3 mb-5 gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-red-600 animate-pulse inline-block"></span>
            <h2 className="text-base font-bold text-white tracking-wider uppercase font-['Silkscreen']">
              INCIDENT FEED GRAPH: {totalAlerts} ALERTS INTO {incidentsCount} INCIDENTS
            </h2>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Simple English Summary: {totalAlerts} real server alarms occurred. The engine grouped them down to {incidentsCount} real problem tickets and pinpointed the origin servers.
          </p>
        </div>

        {/* Dynamic Metric Badges */}
        <div className="flex items-center gap-4 text-xs">
          <div className="border border-white/40 px-3 py-1 bg-neutral-950">
            <span className="text-neutral-400 block text-[10px]">RAW ALERTS:</span>
            <span className="text-white font-bold text-sm">{totalAlerts}</span>
          </div>
          <div className="border border-red-600 px-3 py-1 bg-red-950/40">
            <span className="text-red-400 block text-[10px]">REAL INCIDENTS:</span>
            <span className="text-white font-bold text-sm">{incidentsCount}</span>
          </div>
          <div className="border border-white px-3 py-1 bg-neutral-900">
            <span className="text-neutral-300 block text-[10px]">NOISE REDUCTION:</span>
            <span className="text-red-500 font-bold text-sm">-{reductionRate.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* The Visual Collapse Diagram */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
        {/* Left: Raw Alert Influx */}
        <div className="lg:col-span-3 border border-neutral-800 bg-neutral-950 p-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-2 mb-3">
            <span className="text-[11px] font-bold text-red-500 uppercase">Stage 1: Raw Influx</span>
            <span className="text-[10px] bg-red-600/30 text-red-300 px-1.5 py-0.5">{totalAlerts} Events</span>
          </div>
          <p className="text-[11px] text-neutral-400 mb-3 leading-relaxed">
            Real production servers flooded with socket timeouts, connection drops, and query backlogs.
          </p>
          {/* Pixel Alert Dot Matrix representation */}
          <div className="grid grid-cols-10 gap-1.5 p-2 bg-black border border-neutral-800">
            {Array.from({ length: 50 }).map((_, i) => (
              <span
                key={i}
                className={`w-2 h-2 inline-block ${
                  i % 3 === 0 ? 'bg-red-600' : i % 2 === 0 ? 'bg-white' : 'bg-neutral-600'
                }`}
                title="Real Server Log Event"
              />
            ))}
          </div>
          <div className="text-[10px] text-neutral-500 mt-2 text-center">
            [Visual sample of {totalAlerts} incoming server events]
          </div>
        </div>

        {/* Center: Cascade Funnel */}
        <div className="lg:col-span-3 flex flex-col items-center justify-center text-center p-4 border border-dashed border-red-900/60 bg-neutral-950/40">
          <span className="text-red-500 text-lg font-bold">==&gt;&gt;</span>
          <span className="text-xs font-bold text-white mt-1 uppercase font-['Silkscreen']">Deterministic Grouping</span>
          <p className="text-[11px] text-neutral-400 mt-2 leading-relaxed">
            Matches alarms firing on the same server or dependent neighbor servers within 15 minutes.
          </p>
          <div className="mt-3 text-[10px] border border-white/20 px-2 py-1 text-white bg-black">
            100% DETERMINISTIC // NO RANDOM GUESSES
          </div>
        </div>

        {/* Right: Top Grouped Incidents (Rendered dynamically from actual data!) */}
        <div className="lg:col-span-6 space-y-2.5">
          <div className="text-[11px] font-bold text-white uppercase border-b border-neutral-800 pb-1">
            Stage 2: Collapsed Into {incidentsCount} Incidents
          </div>

          {incidents.slice(0, 3).map((inc, idx) => (
            <div
              key={inc.incident_id || idx}
              className={`p-3 bg-neutral-950 ${
                idx === 0
                  ? 'border-2 border-red-600 shadow-[3px_3px_0px_#ffffff]'
                  : 'border border-white shadow-[3px_3px_0px_#ff0033]'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white uppercase font-['Silkscreen']">
                  INCIDENT #{idx + 1}: {inc.origin.service} Failure
                </span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 ${
                  idx === 0 ? 'bg-red-600 text-white' : 'bg-white text-black'
                }`}>
                  {inc.alerts.length} ALERTS
                </span>
              </div>
              <div className="text-[11px] text-red-400 font-bold mt-1">
                ORIGIN ROOT CAUSE SERVER: {inc.origin.service} ({Math.round(inc.origin.confidence * 100)}% conf)
              </div>
              <p className="text-[11px] text-neutral-300 mt-0.5 truncate">
                {inc.ai_summary || inc.summary}
              </p>
            </div>
          ))}

          {incidents.length > 3 && (
            <div className="text-[10px] text-neutral-400 text-center border border-dashed border-neutral-800 py-1">
              + {incidents.length - 3} more real incidents grouped below
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
