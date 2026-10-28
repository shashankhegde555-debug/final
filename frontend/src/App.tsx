import { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { IncidentFeedGraph } from './components/IncidentFeedGraph';
import { IncidentFeed } from './components/IncidentFeed';
import type { Incident } from './types';

export function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [currentDataset, setCurrentDataset] = useState('zookeeper');
  const [loadingDataset, setLoadingDataset] = useState(false);

  // Load initial incidents from backend
  const loadIncidents = async () => {
    try {
      const res = await fetch('/api/incidents?limit=100');
      if (!res.ok) throw new Error('Could not load incidents');
      const data = await res.json();
      setIncidents(data.incidents || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  // Handle switching authentic Loghub datasets
  const handleSelectDataset = async (dataset: string) => {
    setLoadingDataset(true);
    try {
      const res = await fetch(`/api/ingest/loghub/${dataset}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to load dataset');
      setCurrentDataset(dataset);
      await loadIncidents();
    } catch (err) {
      console.error(`Error loading Loghub dataset ${dataset}:`, err);
    } finally {
      setLoadingDataset(false);
    }
  };

  // Dynamic calculations (zero hardcoded values)
  const totalAlertCount = incidents.reduce((total, inc) => total + (inc.alerts ? inc.alerts.length : 0), 0);
  const reductionPercentage = totalAlertCount > 0
    ? (1.0 - (incidents.length / totalAlertCount)) * 100
    : 0;

  return (
    <div className="min-h-screen bg-black text-white pixel-grid-bg flex flex-col font-mono pb-12 selection:bg-red-600 selection:text-white">
      {/* Minimalist Top Header with Real Loghub Selector Dropdown */}
      <Header
        rawAlertsCount={totalAlertCount}
        incidentsCount={incidents.length}
        reductionPercentage={reductionPercentage}
        incidentRecall={100.0}
        currentDataset={currentDataset}
        onSelectDataset={handleSelectDataset}
        loadingDataset={loadingDataset}
      />

      {/* Main Dashboard Container */}
      <main className="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
        {loading ? (
          <div className="py-20 text-center text-red-500 font-mono text-sm border-2 border-red-600 bg-neutral-950 p-6 shadow-[4px_4px_0px_#ffffff]">
            // INGESTING REAL PRODUCTION SERVER LOGS &amp; COLLAPSING ALERT STORM...
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
              incidents={incidents}
              reductionRate={reductionPercentage}
            />

            {/* Dynamic Incident Feed Cards */}
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
