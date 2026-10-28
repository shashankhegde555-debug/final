import React, { useState } from 'react';
import { TopologyData } from '../types';
import { CytoscapeGraph } from './CytoscapeGraph';
import { Search, Layers, Server } from 'lucide-react';

interface TopologyViewProps {
  topology: TopologyData;
}

export const TopologyView: React.FC<TopologyViewProps> = ({ topology }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTier, setSelectedTier] = useState<string>('all');

  const filteredNodes = topology.nodes.filter((n) => {
    if (searchTerm && !n.id.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    if (selectedTier !== 'all' && n.tier !== selectedTier) {
      return false;
    }
    return true;
  });

  const filteredData: TopologyData = {
    ...topology,
    nodes: filteredNodes,
  };

  const tierCounts: Record<string, number> = {};
  topology.nodes.forEach((n) => {
    tierCounts[n.tier] = (tierCounts[n.tier] || 0) + 1;
  });

  return (
    <div className="space-y-4">
      {/* Top Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 font-medium">Filter by Architecture Tier:</span>
          {['all', 'edge', 'gateway', 'service', 'datastore', 'thirdparty'].map((tier) => (
            <button
              key={tier}
              onClick={() => setSelectedTier(tier)}
              className={`px-2.5 py-1 rounded-md font-semibold capitalize transition ${
                selectedTier === tier
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {tier} ({tier === 'all' ? topology.nodes.length : tierCounts[tier] || 0})
            </button>
          ))}
        </div>

        <div className="relative w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search service name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700/80 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Main Cytoscape View */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 shadow-md">
        <div className="flex items-center justify-between mb-3 text-xs text-slate-400">
          <span>74-Service Dependency Topology (Directed Edges: A → B means A depends on B)</span>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-sky-500"></span> Edge</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-indigo-500"></span> Gateway</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-teal-500"></span> Services</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-500"></span> Datastores</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-pink-500"></span> 3rd-Party</span>
          </div>
        </div>
        <CytoscapeGraph data={filteredData} height="520px" />
      </div>
    </div>
  );
};
