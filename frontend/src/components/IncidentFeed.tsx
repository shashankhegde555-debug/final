import React, { useState } from 'react';
import { Incident } from '../types';
import { AlertCircle, ArrowRight, ShieldCheck, Waves, ChevronRight, Filter } from 'lucide-react';

interface IncidentFeedProps {
  incidents: Incident[];
  onSelectIncident: (inc: Incident) => void;
}

export const IncidentFeed: React.FC<IncidentFeedProps> = ({
  incidents,
  onSelectIncident,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [protectedOnly, setProtectedOnly] = useState<boolean>(false);

  const filtered = incidents.filter((inc) => {
    if (filterSeverity !== 'all' && inc.severity.toLowerCase() !== filterSeverity) {
      return false;
    }
    if (protectedOnly && !inc.has_real_signal) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Feed Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 font-medium">Filter by Severity:</span>
          {['all', 'critical', 'high', 'warning'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-2.5 py-1 rounded-md font-semibold capitalize transition ${
                filterSeverity === sev
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        <button
          onClick={() => setProtectedOnly(!protectedOnly)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-semibold transition border ${
            protectedOnly
              ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
              : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Historically Real Incidents Only</span>
        </button>
      </div>

      {/* Incident Cards Grid */}
      <div className="grid grid-cols-1 gap-3">
        {filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm bg-slate-900/40 rounded-2xl border border-slate-800">
            No incident cards match current filter.
          </div>
        ) : (
          filtered.map((inc) => (
            <div
              key={inc.incident_id}
              onClick={() => onSelectIncident(inc)}
              className="group p-4 rounded-xl bg-slate-900/80 hover:bg-slate-850 border border-slate-800/90 hover:border-indigo-500/50 shadow-md transition-all cursor-pointer relative overflow-hidden"
            >
              {/* Left severity indicator bar */}
              <div className={`absolute top-0 left-0 bottom-0 w-1.5 ${
                inc.severity === 'critical' ? 'bg-red-500' :
                inc.severity === 'high' ? 'bg-orange-500' : 'bg-amber-500'
              }`} />

              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1.5 pl-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                      {inc.incident_id}
                    </span>

                    <span className={`px-2 py-0.5 text-[11px] font-bold rounded uppercase ${
                      inc.severity === 'critical' ? 'bg-red-500/20 text-red-300' :
                      inc.severity === 'high' ? 'bg-orange-500/20 text-orange-300' :
                      'bg-amber-500/20 text-amber-300'
                    }`}>
                      {inc.severity}
                    </span>

                    <span className="px-2.5 py-0.5 text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                      Probable Origin: <strong>{inc.origin.service}</strong> ({(inc.origin.confidence * 100).toFixed(0)}%)
                    </span>

                    {inc.has_real_signal && (
                      <span className="px-2 py-0.5 text-[11px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 rounded flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3" /> Real Signal
                      </span>
                    )}

                    <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                      {inc.alerts.length} alert{inc.alerts.length > 1 ? 's' : ''} → 1 incident
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-white group-hover:text-indigo-300 transition">
                    {inc.summary}
                  </h3>

                  {/* Brief Root-Cause Preview */}
                  {(inc.ai_summary || inc.water_pipe_analogy) && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-300">
                      <span className="font-semibold text-indigo-400">Diagnosis:</span>
                      <span className="truncate text-slate-300">{inc.ai_summary || inc.water_pipe_analogy}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-4 shrink-0 pl-2 md:pl-0">
                  <div className="text-right text-xs text-slate-400 font-mono">
                    <div>Priority: <strong className="text-slate-200">{(inc.priority.score * 100).toFixed(0)}</strong></div>
                    <div className="text-[11px] text-slate-500">{new Date(inc.start_time).toLocaleTimeString()}</div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition" />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
