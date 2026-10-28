import React from 'react';

interface HeaderProps {
  rawAlertsCount: number;
  incidentsCount: number;
  reductionPercentage: number;
  incidentRecall: number;
  currentDataset: string;
  onSelectDataset: (dataset: string) => void;
  loadingDataset?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  rawAlertsCount,
  incidentsCount,
  reductionPercentage,
  incidentRecall = 100.0,
  currentDataset,
  onSelectDataset,
  loadingDataset = false,
}) => {
  return (
    <header className="dashboard-header border-b-2 border-red-600 bg-black text-white px-6 py-4 shadow-[0_4px_0_#ffffff] font-mono sticky top-0 z-50">
      <div className="dashboard-header-inner max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Title & Simple English Subtitle */}
        <div className="flex items-center gap-3">
          <div className="brand-icon w-8 h-8 bg-red-600 border-2 border-white flex items-center justify-center font-bold text-black text-sm shadow-[2px_2px_0px_#ffffff]">
            AO
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="brand-title text-base font-bold text-white uppercase tracking-wider font-['Silkscreen']">
                AO-01 <span>Incident intelligence</span>
              </h1>
              <span className="data-badge px-1.5 py-0.5 text-[10px] font-bold bg-white text-black uppercase">
                Production data
              </span>
            </div>
            <p className="text-xs text-neutral-400 mt-0.5">
              Alerts grouped into incidents, with the likely source shown for each one.
            </p>
          </div>
        </div>

        {/* Center: Real Loghub Dataset Selector Dropdown */}
        <div className="dataset-control flex items-center gap-2">
          <span className="dataset-label text-red-500 text-xs font-bold uppercase tracking-wider font-['Silkscreen']">
            Data set
          </span>
          <select
            value={currentDataset}
            disabled={loadingDataset}
            onChange={(e) => onSelectDataset(e.target.value)}
            className="dataset-select bg-black text-white border-2 border-red-600 px-3 py-1 text-xs font-mono font-bold shadow-[3px_3px_0px_#ffffff] cursor-pointer outline-none hover:bg-neutral-950 transition disabled:opacity-50"
            title="Switch between authentic production server datasets from Loghub"
          >
            <option value="zookeeper">⚡ Real Zookeeper Cluster (Loghub, ~412 alerts)</option>
            <option value="hadoop">⚡ Real Hadoop Cluster (Loghub, ~415 alerts)</option>
            <option value="bgl">⚡ Real BGL Supercomputer (Loghub, ~396 alerts)</option>
            <option value="openstack">⚡ Real OpenStack Cloud (Loghub, ~415 alerts)</option>
            <option value="hdfs">⚡ Real HDFS Storage (Loghub, ~80 alerts)</option>
          </select>
          {loadingDataset && (
            <span className="dataset-loading text-[10px] text-red-500 font-bold animate-pulse">
              Loading…
            </span>
          )}
        </div>

        {/* Dynamic Minimalist Metric Badges (Computed from real data) */}
        <div className="header-metrics flex flex-wrap items-center gap-3 text-xs">
          <div className="metric-card border-2 border-white px-3 py-1 bg-black shadow-[2px_2px_0px_#ff0033]">
            <span className="text-neutral-400 block text-[9px] uppercase">Alerts</span>
            <span className="text-white font-bold">{rawAlertsCount.toLocaleString()}</span>
          </div>

          <div className="metric-card border-2 border-red-600 px-3 py-1 bg-neutral-950 shadow-[2px_2px_0px_#ffffff]">
            <span className="text-red-400 block text-[9px] uppercase">Incidents</span>
            <span className="text-white font-bold">{incidentsCount}</span>
          </div>

          <div className="metric-card border border-white/60 px-3 py-1 bg-neutral-950">
            <span className="text-neutral-400 block text-[9px] uppercase">Fewer tickets</span>
            <span className="text-red-500 font-bold">-{reductionPercentage.toFixed(1)}%</span>
          </div>

          <div className="metric-card border border-red-600 px-3 py-1 bg-black">
            <span className="text-neutral-400 block text-[9px] uppercase">Recall</span>
            <span className="text-white font-bold">{incidentRecall.toFixed(0)}% Safe</span>
          </div>
        </div>
      </div>
    </header>
  );
};
