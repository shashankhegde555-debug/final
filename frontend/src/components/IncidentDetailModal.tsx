import React, { useState } from 'react';
import { X, AlertTriangle, ArrowRight, BrainCircuit, Waves, GitCommit, Network, Clock, ShieldCheck, RefreshCw } from 'lucide-react';
import { Incident, TopologyData } from '../types';
import { CytoscapeGraph } from './CytoscapeGraph';

interface IncidentDetailModalProps {
  incident: Incident;
  topology: TopologyData;
  onClose: () => void;
  onTriggerLLM: (incidentId: string) => Promise<void>;
}

export const IncidentDetailModal: React.FC<IncidentDetailModalProps> = ({
  incident,
  topology,
  onClose,
  onTriggerLLM,
}) => {
  const [activeTab, setActiveTab] = useState<'why' | 'graph' | 'origin' | 'alerts'>('why');
  const [isGeneratingLLM, setIsGeneratingLLM] = useState(false);

  const handleLLMClick = async () => {
    setIsGeneratingLLM(true);
    try {
      await onTriggerLLM(incident.incident_id);
    } finally {
      setIsGeneratingLLM(false);
    }
  };

  // Build topology data scoped to this incident
  const incidentTopology: TopologyData = {
    ...topology,
    highlighted_services: incident.services,
    origin_service: incident.origin.service,
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-start justify-between bg-slate-950/60">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded border border-indigo-500/20">
                {incident.incident_id}
              </span>
              <span className={`px-2 py-0.5 text-xs font-bold rounded uppercase ${
                incident.severity === 'critical' ? 'bg-red-500/20 text-red-300 border border-red-500/40' :
                incident.severity === 'high' ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40' :
                'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              }`}>
                {incident.severity}
              </span>
              {incident.has_real_signal && (
                <span className="px-2 py-0.5 text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 rounded flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" /> Historically Real Incident Signal
                </span>
              )}
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">{incident.summary}</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Spans {incident.alerts.length} alerts across {incident.services.length} services • Window: {new Date(incident.start_time).toLocaleTimeString()} – {new Date(incident.end_time).toLocaleTimeString()}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 2B LLM Root-Cause & Water Pipe Analogy Card */}
        <div className="mx-6 my-4 p-4 rounded-xl bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-purple-950/40 border border-indigo-500/30 shadow-md">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-500/40 flex items-center justify-center shrink-0 text-blue-400 shadow-inner">
                <Waves className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">Water Pipe Analogy:</span>
                  <span className="text-[11px] font-semibold text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                    2B Parameter Model Diagnosis
                  </span>
                </div>
                <p className="text-sm font-semibold text-slate-100 mt-1 italic">
                  "{incident.water_pipe_analogy || 'A main valve failed upstream, causing pressure loss across all building branches.'}"
                </p>
                <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
                  {incident.ai_summary || 'Probable root cause identified by deterministic graph topology blast radius.'}
                </p>
              </div>
            </div>

            <button
              onClick={handleLLMClick}
              disabled={isGeneratingLLM}
              className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isGeneratingLLM ? 'animate-spin' : ''}`} />
              <span>{isGeneratingLLM ? 'Consulting 2B Model...' : 'Re-diagnose via 2B LLM'}</span>
            </button>
          </div>
        </div>

        {/* Sub-tabs */}
        <div className="px-6 border-b border-slate-800 flex items-center gap-2 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('why')}
            className={`px-3 py-2 border-b-2 transition ${
              activeTab === 'why' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            "Why Grouped?" Inspector ({incident.edges.length} Edges)
          </button>
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-3 py-2 border-b-2 transition ${
              activeTab === 'graph' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Cascade Topology Graph
          </button>
          <button
            onClick={() => setActiveTab('origin')}
            className={`px-3 py-2 border-b-2 transition ${
              activeTab === 'origin' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Origin Ranking Candidates ({incident.origin.ranking.length})
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`px-3 py-2 border-b-2 transition ${
              activeTab === 'alerts' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Redacted Alert List ({incident.alerts.length})
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6 overflow-y-auto max-h-[50vh]">
          {/* TAB 1: WHY GROUPED INSPECTOR */}
          {activeTab === 'why' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-400 flex items-center justify-between">
                <span>Pairwise mathematical affinity calculations between alerts:</span>
                <span className="font-mono text-[11px] text-slate-500">
                  Threshold θ = {incident.params?.theta ?? 0.50} • Time Decay τ = {incident.params?.tau ?? 5}m • Max Hops H = {incident.params?.H ?? 2}
                </span>
              </div>

              {incident.edges.length === 0 ? (
                <div className="p-6 text-center text-slate-500 text-xs bg-slate-950/40 rounded-xl border border-slate-800">
                  Singleton incident card (protected critical signal or novel rule).
                </div>
              ) : (
                <div className="space-y-2">
                  {incident.edges.map((edge, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/90 text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 hover:border-slate-700 transition"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] font-bold text-indigo-300">{edge.a}</span>
                          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                          <span className="font-mono text-[11px] font-bold text-indigo-300">{edge.b}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300">
                            Affinity: {(edge.score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-slate-300 text-xs">{edge.reason}</p>
                      </div>

                      <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400 shrink-0">
                        <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800">
                          Δt: {edge.time_gap_sec}s
                        </span>
                        <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800">
                          Dist: {edge.graph_distance} hop(s)
                        </span>
                        <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800">
                          Text Sim: {(edge.text_similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: CASCADE TOPOLOGY GRAPH */}
          {activeTab === 'graph' && (
            <div className="space-y-3">
              <p className="text-xs text-slate-400">
                Interactive dependency graph for this incident. Pulsating emerald node indicates probable root cause.
              </p>
              <CytoscapeGraph data={incidentTopology} height="360px" />
            </div>
          )}

          {/* TAB 3: ORIGIN RANKING CANDIDATES */}
          {activeTab === 'origin' && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {incident.origin.ranking.slice(0, 3).map((cand, idx) => (
                  <div
                    key={cand.service}
                    className={`p-4 rounded-xl border ${
                      idx === 0
                        ? 'bg-emerald-950/20 border-emerald-500/40 shadow-lg shadow-emerald-500/5'
                        : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-slate-400">Rank #{idx + 1}</span>
                      <span className="text-xs font-mono font-bold text-emerald-400">
                        {(cand.score * 100).toFixed(1)}% Score
                      </span>
                    </div>
                    <div className="text-sm font-bold text-white mb-2">{cand.service}</div>
                    
                    <div className="space-y-1.5 text-xs text-slate-400 border-t border-slate-800/80 pt-2 font-mono">
                      <div className="flex justify-between">
                        <span>Downstream Blast (50%):</span>
                        <span className="text-slate-200">{(cand.upstream_score * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Temporal Earliness (30%):</span>
                        <span className="text-slate-200">{(cand.earliness * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Historical Prior (20%):</span>
                        <span className="text-slate-200">{(cand.prior * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: REDACTED ALERTS LIST */}
          {activeTab === 'alerts' && (
            <div className="space-y-2">
              <div className="text-xs text-slate-400 mb-2">
                All alerts linked to this incident with hostnames, IPs, and tenant IDs pseudonymized:
              </div>
              <div className="divide-y divide-slate-800/80 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/60">
                {incident.alerts.map((a) => (
                  <div key={a.alert_id} className="p-3 text-xs flex flex-col md:flex-row md:items-center justify-between gap-2 hover:bg-slate-900/50 transition">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-indigo-400 font-semibold">{a.alert_id}</span>
                        <span className="font-bold text-slate-200">{a.service}</span>
                        <span className="text-slate-500">•</span>
                        <span className="text-slate-300">{a.name}</span>
                        <span className={`px-1.5 py-0.2 text-[10px] font-bold rounded ${
                          a.severity === 'critical' ? 'bg-red-500/20 text-red-300' : 'bg-orange-500/20 text-orange-300'
                        }`}>
                          {a.severity}
                        </span>
                      </div>
                      <p className="text-slate-400 font-mono text-[11px]">{a.message}</p>
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono shrink-0">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
