import React from 'react';
import { Shield, ShieldAlert, Activity, Sliders, BarChart3, Network, Zap, Upload, Database } from 'lucide-react';

interface HeaderProps {
  activeTab: 'feed' | 'noise' | 'metrics' | 'topology';
  setActiveTab: (tab: 'feed' | 'noise' | 'metrics' | 'topology') => void;
  redactionEnabled: boolean;
  setRedactionEnabled: (val: boolean) => void;
  rawAlertsCount: number;
  incidentsCount: number;
  reductionPercentage: number;
  incidentRecall: number;
  onUploadFile?: (file: File) => void;
  onLoadRealSample?: () => void;
  onLoadLoghubDataset?: (dataset: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  redactionEnabled,
  setRedactionEnabled,
  rawAlertsCount,
  incidentsCount,
  reductionPercentage,
  incidentRecall,
  onUploadFile,
  onLoadRealSample,
  onLoadLoghubDataset,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5 shadow-md">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Logo & Subtitle */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-tight">AO-01 Root Cause Intelligence</h1>
              <span className="px-2 py-0.5 text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full">
                Sidecar Brain
              </span>
            </div>
            <p className="text-xs text-slate-400">
              "Four Hundred Alerts, Three Real Incidents" — Graph Origin Ranking & Noise Filter
            </p>
          </div>
        </div>

        {/* Global Live Counters */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 flex items-center gap-2">
            <span className="text-slate-400">Raw Stream:</span>
            <span className="font-mono font-bold text-slate-200">{rawAlertsCount.toLocaleString()}</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 flex items-center gap-2">
            <span className="text-slate-400">Incident Cards:</span>
            <span className="font-mono font-bold text-indigo-400">{incidentsCount.toLocaleString()}</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2">
            <span className="text-emerald-400 font-medium">Reduction:</span>
            <span className="font-mono font-bold text-emerald-300">-{reductionPercentage.toFixed(1)}%</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center gap-2">
            <span className="text-cyan-400 font-medium">Recall:</span>
            <span className="font-mono font-bold text-cyan-300">{incidentRecall.toFixed(0)}% Guaranteed</span>
          </div>

          {/* Upload Real Data & Real Outage Sample Buttons */}
          {onUploadFile && (
            <label className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition cursor-pointer shadow-sm">
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Real Data (CSV/JSON)</span>
              <input
                type="file"
                accept=".csv,.json,.jsonl"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    onUploadFile(e.target.files[0]);
                  }
                }}
              />
            </label>
          )}

          {/* Real Production Datasets Selector */}
          <div className="flex items-center gap-1.5">
            <select
              defaultValue=""
              onChange={(e) => {
                const val = e.target.value;
                if (!val) return;
                if (val === 'postgres' && onLoadRealSample) {
                  onLoadRealSample();
                } else if (onLoadLoghubDataset) {
                  onLoadLoghubDataset(val);
                }
                e.target.value = '';
              }}
              className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-500/40 cursor-pointer transition shadow-sm outline-none"
              title="Select authentic published production server datasets"
            >
              <option value="" disabled>⚡ Load Real Production Data...</option>
              <option value="zookeeper">Real Zookeeper Cluster (Loghub, 2k logs)</option>
              <option value="hadoop">Real Hadoop Cluster (Loghub, 960 errors)</option>
              <option value="openstack">Real OpenStack Cloud (Loghub, 2k logs)</option>
              <option value="hdfs">Real HDFS Storage (Loghub, block fails)</option>
              <option value="postgres">Real Postgres DB Outage (Multi-Tier)</option>
            </select>
          </div>

          {/* Redaction Switch */}
          <button
            onClick={() => setRedactionEnabled(!redactionEnabled)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition border ${
              redactionEnabled
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30 hover:bg-amber-500/20'
                : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20'
            }`}
            title="Toggle IP, Hostname, and Customer ID Redaction"
          >
            {redactionEnabled ? (
              <>
                <Shield className="w-3.5 h-3.5 text-amber-400" />
                <span>Redaction ON</span>
              </>
            ) : (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                <span>Redaction OFF (Exposed)</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto flex items-center gap-1 mt-3 border-t border-slate-800/80 pt-2 text-xs font-medium">
        <button
          onClick={() => setActiveTab('feed')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
            activeTab === 'feed'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Incident Feed</span>
        </button>

        <button
          onClick={() => setActiveTab('noise')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
            activeTab === 'noise'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Noise & Recommendations</span>
        </button>

        <button
          onClick={() => setActiveTab('metrics')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
            activeTab === 'metrics'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>Evaluation & Benchmarks</span>
        </button>

        <button
          onClick={() => setActiveTab('topology')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
            activeTab === 'topology'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          <Network className="w-3.5 h-3.5" />
          <span>Service Topology Map</span>
        </button>
      </div>
    </header>
  );
};
