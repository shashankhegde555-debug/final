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
      ? data.nodes.filter((node) =>
          highlightedSet.has(node.id) || data.edges.some((edge) =>
            (highlightedSet.has(edge.source) && edge.target === node.id) ||
            (highlightedSet.has(edge.target) && edge.source === node.id)
          )
        )
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
            'font-size': '10px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 8,
            'text-outline-color': '#090909',
            'text-outline-width': 2,
            'background-color': '#151313',
            'border-width': 2,
            'border-color': '#817977',
            'width': 34,
            'height': 34,
          },
        },
        {
          selector: 'node[tier = "edge"]',
          style: { 'background-color': '#171717', 'border-color': '#ded8d5' },
        },
        {
          selector: 'node[tier = "gateway"]',
          style: { 'background-color': '#281615', 'border-color': '#a63b35' },
        },
        {
          selector: 'node[tier = "service"]',
          style: { 'background-color': '#211d1c', 'border-color': '#b8aeaa' },
        },
        {
          selector: 'node[tier = "datastore"]',
          style: { 'background-color': '#3a1816', 'border-color': '#f04438' },
        },
        {
          selector: 'node[tier = "thirdparty"]',
          style: { 'background-color': '#292626', 'border-color': '#8e8582' },
        },
        {
          selector: 'node[?isHighlighted]',
          style: {
            'border-width': 3,
            'border-color': '#ff8178',
            'width': 40,
            'height': 40,
          },
        },
        {
          selector: 'node[?isOrigin]',
          style: {
            'background-color': '#f04438',
            'border-width': 5,
            'border-color': '#ffd2cf',
            'color': '#090909',
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
            'line-color': '#514745',
            'target-arrow-color': '#766c69',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.2,
          },
        },
        {
          selector: 'edge[?isActive]',
          style: {
            'width': 3.5,
            'line-color': '#f04438',
            'target-arrow-color': '#f04438',
            'line-style': 'dashed',
          },
        },
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        padding: 48,
        spacingFactor: 1.2,
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
    <div className="relative border border-slate-800 rounded-xl overflow-hidden bg-slate-950/70 shadow-inner topology-graph-frame">
      <div className="absolute top-2 left-3 z-10 text-[11px] font-semibold text-slate-400 bg-slate-900/90 px-2.5 py-1 rounded-md border border-slate-700/60 backdrop-blur-sm graph-origin-label">
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
