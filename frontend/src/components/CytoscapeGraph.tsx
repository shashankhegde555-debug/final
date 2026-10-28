import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { TopologyData } from '../types';

interface CytoscapeGraphProps {
  data: TopologyData;
  height?: string;
  onNodeSelect?: (nodeId: string) => void;
}

export const CytoscapeGraph: React.FC<CytoscapeGraphProps> = ({
  data,
  height = '420px',
  onNodeSelect,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Filter nodes to highlighted ones + their immediate neighbors to avoid cluttering if incident is selected
    const isIncidentFiltered = (data.highlighted_services && data.highlighted_services.length > 0);
    const highlightedSet = new Set(data.highlighted_services || []);

    const relevantNodes = isIncidentFiltered
      ? data.nodes.filter(n => highlightedSet.has(n.id))
      : data.nodes;

    const relevantNodeIds = new Set(relevantNodes.map(n => n.id));

    const relevantEdges = data.edges.filter(
      e => relevantNodeIds.has(e.source) && relevantNodeIds.has(e.target)
    );

    const elements = [
      ...relevantNodes.map(n => ({
        data: {
          id: n.id,
          label: n.id,
          tier: n.tier,
          isOrigin: n.id === data.origin_service,
          isHighlighted: highlightedSet.has(n.id),
        },
      })),
      ...relevantEdges.map((e, idx) => ({
        data: {
          id: `edge-${idx}`,
          source: e.source,
          target: e.target,
          isActive: e.is_active_path,
        },
      })),
    ];

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-size': '11px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'background-color': '#1e293b',
            'border-width': 2,
            'border-color': '#475569',
            'width': 34,
            'height': 34,
          },
        },
        {
          selector: 'node[tier = "edge"]',
          style: { 'background-color': '#0369a1', 'border-color': '#38bdf8' },
        },
        {
          selector: 'node[tier = "gateway"]',
          style: { 'background-color': '#4338ca', 'border-color': '#818cf8' },
        },
        {
          selector: 'node[tier = "service"]',
          style: { 'background-color': '#0f766e', 'border-color': '#2dd4bf' },
        },
        {
          selector: 'node[tier = "datastore"]',
          style: { 'background-color': '#b45309', 'border-color': '#f59e0b' },
        },
        {
          selector: 'node[tier = "thirdparty"]',
          style: { 'background-color': '#be185d', 'border-color': '#f472b6' },
        },
        {
          selector: 'node[?isHighlighted]',
          style: {
            'border-width': 3,
            'border-color': '#ef4444',
            'width': 40,
            'height': 40,
          },
        },
        {
          selector: 'node[?isOrigin]',
          style: {
            'background-color': '#059669',
            'border-width': 5,
            'border-color': '#10b981',
            'width': 50,
            'height': 50,
            'font-size': '13px',
            'font-weight': 700,
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#334155',
            'target-arrow-color': '#334155',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.2,
          },
        },
        {
          selector: 'edge[?isActive]',
          style: {
            'width': 3.5,
            'line-color': '#10b981',
            'target-arrow-color': '#10b981',
            'line-style': 'dashed',
          },
        },
      ],
      layout: {
        name: isIncidentFiltered ? 'breadthfirst' : 'concentric',
        directed: true,
        padding: 25,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (onNodeSelect) {
        onNodeSelect(node.id());
      }
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [data, onNodeSelect]);

  return (
    <div className="relative border border-slate-800 rounded-xl overflow-hidden bg-slate-950/70 shadow-inner">
      <div className="absolute top-2 left-3 z-10 text-[11px] font-semibold text-slate-400 bg-slate-900/90 px-2.5 py-1 rounded-md border border-slate-700/60 backdrop-blur-sm">
        {data.origin_service ? (
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Probable Root Cause Origin: <strong className="text-emerald-300">{data.origin_service}</strong>
          </span>
        ) : (
          <span>Topology Service Graph</span>
        )}
      </div>
      <div ref={containerRef} style={{ height }} className="w-full" />
    </div>
  );
};
