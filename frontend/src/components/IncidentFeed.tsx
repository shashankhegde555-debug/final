import React, { useState } from 'react';
import type { Incident } from '../types';

interface IncidentFeedProps {
  incidents: Incident[];
}

const formatSeverity = (value: string) =>
  value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();

export const IncidentFeed: React.FC<IncidentFeedProps> = ({ incidents }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <section className="w-full bg-black border-2 border-white p-5 shadow-[5px_5px_0px_#ff0033] font-mono">
      {/* Section Header */}
      <div className="flex items-center justify-between border-b-2 border-red-600 pb-3 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-red-600 inline-block animate-pulse"></span>
            <h2 className="text-sm font-bold text-white tracking-wider uppercase font-['Silkscreen']">
              REAL INCIDENT LIST // {incidents.length} COLLAPSED TICKETS
            </h2>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Local AI generated brief descriptions and plain English implications for each distinct server incident.
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
        <div className="space-y-4">
          {incidents.map((incident, idx) => {
            const isTop = idx === 0;
            const alertCount = incident.alerts?.length || 0;
            const rawAlertCount = (incident.alerts || []).reduce(
              (count, alert) => count + Math.max(1, alert.dedup_count || 1), 0);
            const priorityScore = Math.round((incident.priority?.score || 0) * 100);
            const sev = incident.severity?.toLowerCase() || 'warning';
            const isExpanded = expandedId === incident.incident_id;

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
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-850 pb-2.5 mb-3">
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
                      {rawAlertCount} raw alerts → {alertCount} grouped records
                    </span>
                    <span className="dedup-summary">{Math.max(0, rawAlertCount - alertCount)} repeats removed</span>
                  </div>

                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-neutral-400 text-[11px]">
                      Origin Node: <strong className="text-white">{incident.origin.service}</strong>
                    </span>
                    <span className="text-green-400 font-bold text-[11px]">
                      🟢 {Math.round(incident.origin.confidence * 100)}% Confidence
                    </span>
                    <span className="priority-score">
                      Priority <strong>{priorityScore}/100</strong>
                    </span>
                  </div>
                </div>

                {/* Main Distinct Title */}
                <h3 className="text-sm font-bold text-white mb-2 leading-relaxed font-['Silkscreen']">
                  {incident.summary}
                </h3>

                {/* Local AI Brief Description (Simple English) */}
                <div className="bg-black/80 border border-neutral-800 p-3 mb-2.5 space-y-2">
                  <div className="flex items-start gap-2">
                    <span className="text-xs text-neutral-400 font-bold flex-shrink-0 uppercase tracking-wider">
                      💬 Brief Description:
                    </span>
                    <p className="text-xs text-neutral-200 leading-relaxed">
                      {incident.ai_summary || incident.summary}
                    </p>
                  </div>

                  {/* What It Implies (Simple English) */}
                  <div className="flex items-start gap-2 border-t border-neutral-850 pt-2">
                    <span className="text-xs text-green-400 font-bold flex-shrink-0 uppercase tracking-wider">
                      ⚠️ What It Implies:
                    </span>
                    <p className="text-xs text-green-300/90 leading-relaxed font-semibold">
                      {incident.ai_implication ||
                        "What this implies: Downstream microservices are unable to complete read/write requests on this node until failure recovery completes."}
                    </p>
                  </div>
                </div>

                {/* Collapsible Distinct Alert Details Preview */}
                <div className="text-xs">
                  <div className="flex items-center justify-between text-neutral-400 py-1 border-t border-neutral-900">
                    <div className="flex flex-wrap items-center gap-3 text-[11px]">
                      <span>
                        <strong className="text-neutral-300">Root Node:</strong> {incident.origin.service}
                      </span>
                      <span>
                        <strong className="text-neutral-300">Affected Services:</strong>{' '}
                        {incident.services?.length || 1} ({incident.services?.slice(0, 3).join(', ')})
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => toggleExpand(incident.incident_id)}
                      className="text-[10px] text-orange-400 hover:text-white underline font-bold cursor-pointer"
                    >
                      {isExpanded ? '[-] Hide Raw Alerts' : `[+] Inspect ${alertCount} Raw Alerts`}
                    </button>
                  </div>

                  {/* Expanded Alert Stream showing distinct server log messages */}
                  {isExpanded && (
                    <div className="mt-2.5 p-2.5 bg-black border border-neutral-800 space-y-1.5 max-h-48 overflow-y-auto">
                      {!!incident.edges?.length && (
                        <div className="correlation-explanation">
                          <strong>Why these alerts were grouped</strong>
                          {incident.edges.slice(0, 4).map((edge, edgeIdx) => (
                            <p key={`${edge.a}-${edge.b}-${edgeIdx}`}>{edge.reason}</p>
                          ))}
                          {incident.edges.length > 4 && <span>{incident.edges.length - 4} more matching links</span>}
                        </div>
                      )}
                      <div className="text-[10px] text-neutral-500 uppercase font-bold border-b border-neutral-800 pb-1 mb-1">
                        Grouped alert records ({alertCount}); original alert count ({rawAlertCount}):
                      </div>
                      {incident.alerts?.map((a, aIdx) => (
                        <div key={a.alert_id || aIdx} className="text-[11px] font-mono flex items-start gap-2 py-0.5 border-b border-neutral-900">
                          <span className="text-red-500 font-bold flex-shrink-0">[{a.name}]</span>
                          <span className="text-neutral-400 flex-shrink-0 font-semibold">{a.service}:</span>
                          <span className="text-neutral-200 truncate">{a.message}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};
