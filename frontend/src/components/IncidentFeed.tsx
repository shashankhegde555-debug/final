import React from 'react';
import type { Incident } from '../types';

interface IncidentFeedProps {
  incidents: Incident[];
}

const formatSeverity = (value: string) =>
  value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();

export const IncidentFeed: React.FC<IncidentFeedProps> = ({ incidents }) => {
  return (
    <section className="w-full bg-black border-2 border-white p-5 shadow-[5px_5px_0px_#ff0033] font-mono">
      {/* Section Header */}
      <div className="flex items-center justify-between border-b-2 border-red-600 pb-3 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-red-600 inline-block"></span>
            <h2 className="text-sm font-bold text-white tracking-wider uppercase font-['Silkscreen']">
              REAL INCIDENT LIST // {incidents.length} COLLAPSED TICKETS
            </h2>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Each ticket contains 10 to 15 clustered server alerts with the probable origin root-cause pinpointed.
          </p>
        </div>
        <span className="text-xs bg-neutral-900 border border-white/40 px-2.5 py-1 text-white font-bold">
          {incidents.length} TICKETS
        </span>
      </div>

      {/* Incident List */}
      {incidents.length === 0 ? (
        <div className="text-center py-12 text-neutral-500 border border-dashed border-neutral-800">
          No active incidents detected.
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((incident, idx) => {
            const isTop = idx === 0;
            const alertCount = incident.alerts?.length || 0;
            const sev = incident.severity?.toLowerCase() || 'warning';

            return (
              <article
                key={incident.incident_id || idx}
                className={`p-4 bg-neutral-950 transition-all ${
                  isTop
                    ? 'border-2 border-red-600 shadow-[4px_4px_0px_#ffffff]'
                    : 'border border-neutral-800 hover:border-white shadow-[2px_2px_0px_#ff0033]'
                }`}
              >
                {/* Meta Header */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-850 pb-2 mb-2.5">
                  <div className="flex items-center gap-2.5">
                    <span className="text-xs font-bold text-white uppercase bg-red-600 px-2 py-0.5">
                      {incident.incident_id}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 border ${
                        sev === 'critical'
                          ? 'border-red-500 text-red-400 bg-red-950/40'
                          : sev === 'high'
                          ? 'border-orange-500 text-orange-400 bg-orange-950/40'
                          : 'border-yellow-600 text-yellow-400 bg-yellow-950/30'
                      }`}
                    >
                      {formatSeverity(incident.severity)}
                    </span>
                    <span className="text-xs font-bold text-orange-400">
                      🟠 {alertCount} ALERTS IN THIS INCIDENT
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-neutral-400 text-[11px]">
                      Origin Server: <strong className="text-white">{incident.origin.service}</strong>
                    </span>
                    <span className="text-green-400 font-bold text-[11px]">
                      🟢 {Math.round(incident.origin.confidence * 100)}% Confidence
                    </span>
                  </div>
                </div>

                {/* Main Summary */}
                <h3 className="text-sm font-bold text-white mb-2 leading-relaxed">
                  {incident.summary || incident.ai_summary}
                </h3>

                {/* Plain English Details & Affected Nodes */}
                <div className="flex flex-wrap items-center justify-between text-xs text-neutral-400 gap-2 pt-2 border-t border-neutral-900">
                  <div className="flex flex-wrap items-center gap-4 text-[11px]">
                    <span>
                      <strong className="text-neutral-300">Root Cause Node:</strong> {incident.origin.service}
                    </span>
                    <span>
                      <strong className="text-neutral-300">Affected Services:</strong>{' '}
                      {incident.services?.length || 1} ({incident.services?.slice(0, 4).join(', ')})
                    </span>
                    <span>
                      <strong className="text-neutral-300">Time Window:</strong>{' '}
                      {incident.start_time?.slice(11, 19)} &rarr; {incident.end_time?.slice(11, 19)}
                    </span>
                  </div>

                  <span className="text-[10px] text-green-400 bg-green-950/30 border border-green-800/60 px-2 py-0.5 font-bold">
                    1 Actionable Ticket (Suppressed {alertCount - 1} duplicate alarms)
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};
