import React, { useState } from 'react';
import type { Incident } from '../types';

interface IncidentFeedGraphProps {
  totalAlerts: number;
  incidents: Incident[];
  reductionRate: number;
}

export const IncidentFeedGraph: React.FC<IncidentFeedGraphProps> = ({
  totalAlerts,
  incidents,
  reductionRate,
}) => {
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(
    incidents.length > 0 ? incidents[0] : null
  );

  const incidentsCount = incidents.length;
  // Compute max alerts for y-axis scaling (at least 16 to fit 10-15 alerts nicely)
  const maxAlerts = Math.max(16, ...incidents.map((i) => i.alerts?.length || 0));
  const chartHeight = 180; // px

  return (
    <div className="w-full bg-black border-2 border-white p-5 shadow-[5px_5px_0px_#ff0033] mb-8 font-mono">
      {/* Header & Plain English Legend */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between border-b-2 border-red-600 pb-4 mb-4 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-red-600 inline-block animate-pulse"></span>
            <h2 className="text-base font-bold text-white tracking-wider uppercase font-['Silkscreen']">
              INCIDENT FEED GRAPH: 10–15 ALERTS PER INCIDENT
            </h2>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Standard activity graph comparing raw incoming server alarms with consolidated incident tickets.
          </p>
        </div>

        {/* Normal Graph Legend using Green and Orange */}
        <div className="flex flex-wrap items-center gap-4 text-xs bg-neutral-950 p-2.5 border border-neutral-800">
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 bg-orange-500 border border-orange-400 inline-block"></span>
            <span className="text-orange-400 font-bold">
              Orange: Raw Alerts Fired (10–15 Alarms)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 bg-green-500 border border-green-400 inline-block"></span>
            <span className="text-green-400 font-bold">
              Green: Actionable Ticket (Root Cause Isolated)
            </span>
          </div>
        </div>
      </div>

      {/* Main Standard Graph Area */}
      <div className="relative bg-neutral-950/80 border border-neutral-850 p-4 pt-6">
        {/* Y-Axis Grid Lines & Labels */}
        <div className="relative w-full" style={{ height: `${chartHeight}px` }}>
          {/* Horizontal Grid lines */}
          {[15, 10, 5, 0].map((val) => {
            const bottomPercent = (val / maxAlerts) * 100;
            return (
              <div
                key={val}
                className="absolute w-full flex items-center border-b border-neutral-800/80 pointer-events-none"
                style={{ bottom: `${bottomPercent}%` }}
              >
                <span className="text-[10px] text-neutral-500 font-bold w-10 text-right pr-2">
                  {val}
                </span>
                <div className="flex-1 border-b border-dashed border-neutral-800"></div>
              </div>
            );
          })}

          {/* Bar Columns Container */}
          <div
            className="absolute left-10 right-0 top-0 bottom-0 flex items-end gap-2 sm:gap-3 overflow-x-auto pb-1 px-2"
            style={{ height: `${chartHeight}px` }}
          >
            {incidents.map((inc, idx) => {
              const alertCount = inc.alerts?.length || 0;
              const barHeightPx = Math.max(16, (alertCount / maxAlerts) * (chartHeight - 30));
              const isSelected = selectedIncident?.incident_id === inc.incident_id;

              return (
                <div
                  key={inc.incident_id || idx}
                  onClick={() => setSelectedIncident(inc)}
                  className={`flex flex-col items-center flex-shrink-0 cursor-pointer group transition-transform ${
                    isSelected ? 'scale-105' : 'hover:scale-102'
                  }`}
                  style={{ width: '48px' }}
                >
                  {/* Green Ticket Indicator at the top of each incident column */}
                  <div className="flex items-center gap-1 mb-1.5" title="1 Actionable Ticket Formed">
                    <span className="w-2.5 h-2.5 rounded-none bg-green-500 border border-green-300 shadow-[0_0_6px_#22c55e]"></span>
                    <span className="text-[9px] font-bold text-green-400">1</span>
                  </div>

                  {/* Orange Value Label */}
                  <span className="text-[11px] font-bold text-orange-400 mb-1 leading-none">
                    {alertCount}
                  </span>

                  {/* Orange Alert Count Bar */}
                  <div
                    className={`w-full border transition-all ${
                      isSelected
                        ? 'bg-orange-500 border-white shadow-[0_0_10px_#f97316]'
                        : 'bg-orange-600/90 hover:bg-orange-500 border-orange-400'
                    }`}
                    style={{ height: `${barHeightPx}px` }}
                    title={`Incident ${inc.incident_id}: ${alertCount} alerts firing across server '${inc.origin.service}'`}
                  >
                    {/* Inner texture lines for pixel feel */}
                    <div className="w-full h-full bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.25)_50%)] bg-[length:100%_4px]"></div>
                  </div>

                  {/* X-Axis Incident ID Label */}
                  <span
                    className={`text-[9px] font-bold mt-2 truncate w-full text-center ${
                      isSelected ? 'text-white bg-red-600 px-0.5' : 'text-neutral-400 group-hover:text-white'
                    }`}
                  >
                    #{idx + 1 < 10 ? `0${idx + 1}` : idx + 1}
                  </span>

                  {/* Origin Server abbreviation */}
                  <span className="text-[8px] text-neutral-500 truncate w-full text-center mt-0.5">
                    {inc.origin.service.slice(0, 7)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* X-Axis Footer Bar */}
        <div className="mt-6 pt-2 border-t border-neutral-800 flex flex-col sm:flex-row items-center justify-between text-xs text-neutral-400 gap-2">
          <div className="flex items-center gap-2">
            <span className="text-white font-bold">X-Axis:</span>
            <span>Real Server Incidents (Grouped 10–15 alerts per incident)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-white font-bold">Y-Axis:</span>
            <span>Alert Storm Volume (0 to 15 Alarms)</span>
          </div>
        </div>
      </div>

      {/* Selected Incident Inspector Card (Simple English for Judges) */}
      {selectedIncident && (
        <div className="mt-4 p-4 bg-neutral-950 border border-neutral-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-white uppercase bg-red-600 px-2 py-0.5">
                {selectedIncident.incident_id}
              </span>
              <span className="text-xs text-orange-400 font-bold">
                🟠 {selectedIncident.alerts?.length || 0} Raw Alarms Fired
              </span>
              <span className="text-xs text-green-400 font-bold">
                🟢 1 Grouped Actionable Ticket
              </span>
            </div>
            <div className="text-sm font-bold text-white mt-1">
              ROOT CAUSE ORIGIN: <span className="text-red-500">{selectedIncident.origin.service}</span> ({Math.round(selectedIncident.origin.confidence * 100)}% confidence)
            </div>
            <p className="text-xs text-neutral-300">
              {selectedIncident.summary || selectedIncident.ai_summary}
            </p>
          </div>

          <div className="text-right flex-shrink-0">
            <div className="text-[10px] text-neutral-400 uppercase">Affected Services:</div>
            <div className="text-xs text-white font-bold">
              {selectedIncident.services?.length || 1} servers ({selectedIncident.services?.slice(0, 3).join(', ')})
            </div>
            <div className="text-[10px] text-green-400 font-bold mt-1">
              ✓ Noise Reduced: -{(((selectedIncident.alerts?.length - 1) / Math.max(1, selectedIncident.alerts?.length)) * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      )}

      {/* Judge Fact Bar */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-center">
        <div className="border border-neutral-800 p-2 bg-neutral-950">
          <span className="text-[10px] text-orange-400 block font-bold">🟠 TOTAL RAW ALERTS:</span>
          <span className="text-sm font-bold text-white">{totalAlerts}</span>
        </div>
        <div className="border border-neutral-800 p-2 bg-neutral-950">
          <span className="text-[10px] text-green-400 block font-bold">🟢 REAL INCIDENTS:</span>
          <span className="text-sm font-bold text-white">{incidentsCount}</span>
        </div>
        <div className="border border-neutral-800 p-2 bg-neutral-950">
          <span className="text-[10px] text-neutral-400 block font-bold">⚡ ALERTS PER INCIDENT:</span>
          <span className="text-sm font-bold text-white">
            10 to 15 (avg {(totalAlerts / Math.max(1, incidentsCount)).toFixed(1)})
          </span>
        </div>
        <div className="border border-neutral-800 p-2 bg-neutral-950">
          <span className="text-[10px] text-red-400 block font-bold">🎯 NOISE SUPPRESSED:</span>
          <span className="text-sm font-bold text-red-500">-{reductionRate.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
};
