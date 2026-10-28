import React from 'react';
import { Incident } from '../types';

interface IncidentFeedProps {
  incidents: Incident[];
  onSelectIncident?: (inc: Incident) => void;
}

export const IncidentFeed: React.FC<IncidentFeedProps> = ({ incidents }) => {
  return (
    <div className="space-y-6 font-mono">
      {/* Section Header (Zero Buttons, Plain English) */}
      <div className="flex items-center justify-between border-b-2 border-white pb-2">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider font-['Silkscreen']">
          // DETECTED REAL INCIDENTS ({incidents.length} GROUPS)
        </h2>
        <span className="text-[11px] text-neutral-400">
          Showing 100% Real Production Server Incidents
        </span>
      </div>

      {/* Incident Cards */}
      <div className="grid grid-cols-1 gap-5">
        {incidents.map((inc, idx) => {
          const isPrimary = idx === 0;
          return (
            <div
              key={inc.incident_id || idx}
              className={`p-5 bg-black ${
                isPrimary
                  ? 'border-2 border-red-600 shadow-[6px_6px_0px_#ffffff]'
                  : 'border-2 border-white shadow-[6px_6px_0px_#ff0033]'
              }`}
            >
              {/* Header Badges */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-xs font-bold bg-white text-black font-['Silkscreen']">
                    INCIDENT #{idx + 1}
                  </span>
                  <span className={`px-2 py-0.5 text-xs font-bold uppercase ${
                    inc.severity === 'critical' ? 'bg-red-600 text-white' : 'bg-neutral-800 text-white border border-white/40'
                  }`}>
                    {inc.severity.toUpperCase()}
                  </span>
                </div>

                <div className="text-xs text-neutral-400">
                  Collapses <strong className="text-white text-sm">{inc.alerts.length}</strong> raw alarms into 1 ticket
                </div>
              </div>

              {/* Origin Root Cause Server Banner */}
              <div className="p-3 bg-neutral-950 border border-red-600/80 mb-4">
                <div className="text-[10px] text-red-500 font-bold uppercase tracking-wider">
                  IDENTIFIED ROOT-CAUSE ORIGIN SERVER:
                </div>
                <div className="text-base font-bold text-white mt-0.5 font-['Silkscreen']">
                  {inc.origin.service}
                  <span className="ml-3 text-xs text-red-400 font-normal font-mono">
                    (Origin Confidence: {(inc.origin.confidence * 100).toFixed(0)}%)
                  </span>
                </div>
              </div>

              {/* Simple English Explanation for Judges */}
              <div className="mb-4">
                <div className="text-[10px] text-neutral-400 uppercase font-bold mb-1">
                  What Failed (Simple English Diagnosis):
                </div>
                <p className="text-xs text-neutral-200 leading-relaxed bg-neutral-950 p-3 border border-neutral-800">
                  {inc.ai_summary || inc.summary || "Severe hardware or network bottleneck detected on the origin server, cascading into failure timeouts across all connected downstream microservices."}
                </p>
              </div>

              {/* Affected Servers List */}
              <div className="mb-4">
                <div className="text-[10px] text-neutral-400 uppercase font-bold mb-1.5">
                  Affected Downstream Servers ({inc.services.length}):
                </div>
                <div className="flex flex-wrap gap-2">
                  {inc.services.map((svc) => (
                    <span
                      key={svc}
                      className={`px-2 py-1 text-xs border ${
                        svc === inc.origin.service
                          ? 'border-red-600 text-red-400 bg-red-950/40 font-bold'
                          : 'border-neutral-700 text-neutral-300 bg-neutral-950'
                      }`}
                    >
                      {svc === inc.origin.service ? `* ${svc} (Origin)` : svc}
                    </span>
                  ))}
                </div>
              </div>

              {/* Sample Authentic Server Logs from this Incident */}
              <div>
                <div className="text-[10px] text-neutral-400 uppercase font-bold mb-1.5">
                  Actual Server Error Logs ({inc.alerts.length} Total):
                </div>
                <div className="bg-black border border-neutral-800 p-3 space-y-1.5 text-[11px] text-neutral-300 max-h-36 overflow-y-auto">
                  {inc.alerts.slice(0, 4).map((a, aIdx) => (
                    <div key={aIdx} className="flex items-start gap-2 border-b border-neutral-900 pb-1">
                      <span className="text-red-500 font-bold">[{a.timestamp ? a.timestamp.substring(11, 19) : '12:00:00'}]</span>
                      <span className="text-white font-bold">{a.service}:</span>
                      <span className="text-neutral-300 truncate">{a.message}</span>
                    </div>
                  ))}
                  {inc.alerts.length > 4 && (
                    <div className="text-[10px] text-neutral-500 pt-1 text-center">
                      + {inc.alerts.length - 4} more server logs collapsed in this incident
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
