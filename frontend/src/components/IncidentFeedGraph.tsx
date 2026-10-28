import React from 'react';

interface IncidentFeedGraphProps {
  totalAlerts: number;
  incidentsCount: number;
  reductionRate: number;
}

export const IncidentFeedGraph: React.FC<IncidentFeedGraphProps> = ({
  totalAlerts = 400,
  incidentsCount = 3,
  reductionRate = 99.3,
}) => {
  return (
    <div className="w-full bg-black border-2 border-white p-5 shadow-[5px_5px_0px_#ff0033] mb-8 font-mono">
      {/* Top Banner in Simple English */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b-2 border-red-600 pb-3 mb-5 gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-red-600 animate-pulse inline-block"></span>
            <h2 className="text-base font-bold text-white tracking-wider uppercase font-['Silkscreen']">
              INCIDENT FEED GRAPH: 400 ALERTS INTO 3 INCIDENTS
            </h2>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Simple English Summary: 400 real server alarms occurred. The engine grouped them down to 3 real problem tickets and found which server failed first.
          </p>
        </div>

        {/* Minimalist Stat Counters (Zero Buttons) */}
        <div className="flex items-center gap-4 text-xs">
          <div className="border border-white/40 px-3 py-1 bg-neutral-950">
            <span className="text-neutral-400 block text-[10px]">RAW ALERTS:</span>
            <span className="text-white font-bold text-sm">{totalAlerts}</span>
          </div>
          <div className="border border-red-600 px-3 py-1 bg-red-950/40">
            <span className="text-red-400 block text-[10px]">REAL INCIDENTS:</span>
            <span className="text-white font-bold text-sm">{incidentsCount}</span>
          </div>
          <div className="border border-white px-3 py-1 bg-neutral-900">
            <span className="text-neutral-300 block text-[10px]">NOISE REDUCTION:</span>
            <span className="text-red-500 font-bold text-sm">-{reductionRate}%</span>
          </div>
        </div>
      </div>

      {/* The Visual Collapse Diagram */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
        {/* Left: 400 Raw Alert Stream */}
        <div className="lg:col-span-3 border border-neutral-800 bg-neutral-950 p-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-2 mb-3">
            <span className="text-[11px] font-bold text-red-500 uppercase">Stage 1: Raw Alert Influx</span>
            <span className="text-[10px] bg-red-600/30 text-red-300 px-1.5 py-0.5">400 Events</span>
          </div>
          <p className="text-[11px] text-neutral-400 mb-3 leading-relaxed">
            Real production servers flooded with socket timeouts, connection drops, and query backlogs.
          </p>
          {/* Pixel Alert Dot Matrix representation */}
          <div className="grid grid-cols-10 gap-1.5 p-2 bg-black border border-neutral-800">
            {Array.from({ length: 50 }).map((_, i) => (
              <span
                key={i}
                className={`w-2 h-2 inline-block ${
                  i < 24 ? 'bg-red-600' : i < 42 ? 'bg-white' : 'bg-neutral-600'
                }`}
                title="Real Server Alert Log"
              />
            ))}
          </div>
          <div className="text-[10px] text-neutral-500 mt-2 text-center">
            [Showing sample of 400 incoming logs]
          </div>
        </div>

        {/* Center: Cascade Funnel */}
        <div className="lg:col-span-3 flex flex-col items-center justify-center text-center p-4 border border-dashed border-red-900/60 bg-neutral-950/40">
          <span className="text-red-500 text-lg font-bold">==&gt;&gt;</span>
          <span className="text-xs font-bold text-white mt-1 uppercase font-['Silkscreen']">Deterministic Grouping</span>
          <p className="text-[11px] text-neutral-400 mt-2 leading-relaxed">
            Matches alarms firing on the same server or dependent neighbor servers within 15 minutes.
          </p>
          <div className="mt-3 text-[10px] border border-white/20 px-2 py-1 text-white bg-black">
            100% DETERMINISTIC // NO RANDOM GUESSES
          </div>
        </div>

        {/* Right: The 3 Isolated Root Cause Incidents */}
        <div className="lg:col-span-6 space-y-2.5">
          <div className="text-[11px] font-bold text-white uppercase border-b border-neutral-800 pb-1">
            Stage 2: Collapsed Into 3 Root Cause Incidents
          </div>

          {/* Incident 1 */}
          <div className="border-2 border-red-600 bg-neutral-950 p-3 shadow-[3px_3px_0px_#ffffff]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white uppercase font-['Silkscreen']">
                INCIDENT 01: Quorum Leader Election Failure
              </span>
              <span className="text-[10px] bg-red-600 text-black font-bold px-1.5 py-0.5">185 ALERTS</span>
            </div>
            <div className="text-[11px] text-red-400 font-bold mt-1">
              ORIGIN ROOT CAUSE SERVER: FastLeaderElection
            </div>
            <p className="text-[11px] text-neutral-300 mt-0.5">
              What happened: Server election socket timed out on port 2181. Quorum was lost, causing 4 cluster nodes to reject client writes.
            </p>
          </div>

          {/* Incident 2 */}
          <div className="border border-white bg-neutral-950 p-3 shadow-[3px_3px_0px_#ff0033]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white uppercase font-['Silkscreen']">
                INCIDENT 02: Client Session Expiration Storm
              </span>
              <span className="text-[10px] bg-white text-black font-bold px-1.5 py-0.5">145 ALERTS</span>
            </div>
            <div className="text-[11px] text-white font-bold mt-1">
              ORIGIN ROOT CAUSE SERVER: LearnerHandler
            </div>
            <p className="text-[11px] text-neutral-300 mt-0.5">
              What happened: Network lag exceeded heartbeat threshold, causing 145 client sessions to drop at once and trigger retry storms.
            </p>
          </div>

          {/* Incident 3 */}
          <div className="border border-neutral-400 bg-neutral-950 p-3 shadow-[3px_3px_0px_#ff0033]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white uppercase font-['Silkscreen']">
                INCIDENT 03: Disk Snapshot & State Sync Stall
              </span>
              <span className="text-[10px] bg-neutral-700 text-white font-bold px-1.5 py-0.5">70 ALERTS</span>
            </div>
            <div className="text-[11px] text-neutral-300 font-bold mt-1">
              ORIGIN ROOT CAUSE SERVER: SyncRequestProcessor
            </div>
            <p className="text-[11px] text-neutral-300 mt-0.5">
              What happened: Disk snapshot queue backed up, causing write operations across 9 dependent storage workers to stall.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
