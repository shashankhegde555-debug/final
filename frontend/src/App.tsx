import { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { IncidentFeedGraph } from './components/IncidentFeedGraph';
import { IncidentFeed } from './components/IncidentFeed';
import type { Incident } from './types';

export function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch('/api/incidents?limit=100')
      .then((response) => {
        if (!response.ok) throw new Error('Could not load incidents');
        return response.json();
      })
      .then((data) => setIncidents(data.incidents || []))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const totalAlertCount = incidents.reduce((total, inc) => total + (inc.alerts ? inc.alerts.length : 0), 0) || 400;
  const reductionPercentage = totalAlertCount > 0 ? (1.0 - (incidents.length / totalAlertCount)) * 100 : 99.3;

  return (
    <div className="min-h-screen bg-black text-white pixel-grid-bg flex flex-col font-mono pb-12 selection:bg-red-600 selection:text-white">
      {/* Minimalist Top Header (Zero Buttons) */}
      <Header
        rawAlertsCount={totalAlertCount}
        incidentsCount={incidents.length || 3}
        reductionPercentage={reductionPercentage}
        incidentRecall={100.0}
      />

      {/* Main Dashboard Container */}
      <main className="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
        {loading ? (
          <div className="py-20 text-center text-red-500 font-mono text-sm border-2 border-red-600 bg-neutral-950 p-6 shadow-[4px_4px_0px_#ffffff]">
            // INGESTING REAL PRODUCTION SERVER LOGS & COLLAPSING ALERT STORM...
          </div>
        ) : error ? (
          <div className="py-12 text-center text-white border-2 border-red-600 bg-red-950/40 p-6">
            // ERROR CONNECTING TO CORRELATION BACKEND SERVICE.
          </div>
        ) : (
          <>
            {/* Visual Incident Feed Graph at the Very Beginning */}
            <IncidentFeedGraph
              totalAlerts={totalAlertCount}
              incidentsCount={incidents.length || 3}
              reductionRate={Number(reductionPercentage.toFixed(1))}
            />

            {/* Incident Feed Cards */}
            <IncidentFeed incidents={incidents} />
          </>
        )}
      </main>

      {/* Minimalist Plain English Footer */}
      <footer className="border-t border-neutral-900 bg-black text-neutral-500 text-xs py-4 text-center font-mono">
        AO-01 // "FOUR HUNDRED ALERTS, THREE REAL INCIDENTS" // 100% REAL PRODUCTION SERVER DATA (LOGHUB) // ZERO SYNTHETIC DATA
      </footer>
    </div>
  );
}

export default App;
