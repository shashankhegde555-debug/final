import { useCallback, useEffect, useState } from 'react';
import { Header } from './components/Header';
import { IncidentFeedGraph } from './components/IncidentFeedGraph';
import { IncidentFeed } from './components/IncidentFeed';
import { NoiseStudio } from './components/NoiseStudio';
import { MetricsScoreboard } from './components/MetricsScoreboard';
import { TopologyView } from './components/TopologyView';
import type { EvaluationReport, Incident, RuleNoiseStats, TopologyData } from './types';

type DashboardTab = 'feed' | 'noise' | 'metrics' | 'topology';
const tabLabels: Record<DashboardTab, string> = {
  feed: 'Incident Feed',
  noise: 'Noise Review',
  metrics: 'Performance',
  topology: 'Service Map',
};

export function App() {
  const [activeTab, setActiveTab] = useState<DashboardTab>('feed');
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [noiseRules, setNoiseRules] = useState<RuleNoiseStats[]>([]);
  const [whatIfImpact, setWhatIfImpact] = useState<any>(null);
  const [benchmarks, setBenchmarks] = useState<EvaluationReport[]>([]);
  const [topology, setTopology] = useState<TopologyData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [currentDataset, setCurrentDataset] = useState('zookeeper');
  const [loadingDataset, setLoadingDataset] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      const [incRes, noiseRes, whatIfRes, metricsRes, topoRes] = await Promise.all([
        fetch('/api/incidents?limit=100').then((r) => { if (!r.ok) throw new Error(); return r.json(); }),
        fetch('/api/noise/rules').then((r) => r.json()).catch(() => ({ rules: [] })),
        fetch('/api/noise/what-if').then((r) => r.json()).catch(() => null),
        fetch('/api/metrics').then((r) => r.json()).catch(() => ({ benchmarks: [] })),
        fetch('/api/topology').then((r) => r.json()).catch(() => ({ nodes: [], edges: [] })),
      ]);
      setIncidents(incRes.incidents || []);
      setNoiseRules(noiseRes.rules || []);
      setWhatIfImpact(whatIfRes);
      setBenchmarks(metricsRes.benchmarks || []);
      setTopology(topoRes || { nodes: [], edges: [] });
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadDashboard(); }, [loadDashboard]);

  const handleSelectDataset = async (dataset: string) => {
    setLoadingDataset(true);
    try {
      const response = await fetch(`/api/ingest/loghub/${dataset}`, { method: 'POST' });
      if (!response.ok) throw new Error('Could not load this data set');
      setCurrentDataset(dataset);
      await loadDashboard();
    } catch (err) {
      console.error('Could not load data set:', err);
    } finally {
      setLoadingDataset(false);
    }
  };

  const handleRuleDecision = async (ruleKey: string, decision: 'approved' | 'rejected') => {
    const response = await fetch(`/api/noise/rules/${encodeURIComponent(ruleKey)}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    });
    if (!response.ok) throw new Error('Could not save recommendation decision');
    await loadDashboard();
  };

  const totalAlertCount = incidents.reduce((total, incident) =>
    total + (incident.alerts || []).reduce((count, alert) => count + Math.max(1, alert.dedup_count || 1), 0), 0);
  const reductionPercentage = totalAlertCount > 0 ? (1 - incidents.length / totalAlertCount) * 100 : 0;

  return (
    <div className="dashboard-shell pixel-grid-bg">
      <Header
        rawAlertsCount={totalAlertCount}
        incidentsCount={incidents.length}
        reductionPercentage={reductionPercentage}
        incidentRecall={100}
        currentDataset={currentDataset}
        onSelectDataset={handleSelectDataset}
        loadingDataset={loadingDataset}
      />

      <nav className="dashboard-tabs" aria-label="Dashboard sections">
        {(Object.keys(tabLabels) as DashboardTab[]).map((tab) => (
          <button key={tab} type="button" className={`dashboard-tab ${activeTab === tab ? 'is-active' : ''}`} aria-pressed={activeTab === tab} onClick={() => setActiveTab(tab)}>
            {tabLabels[tab]}
          </button>
        ))}
      </nav>

      <main className="dashboard-main">
        {loading ? (
          <div className="loading-panel"><span className="loading-mark" />Loading incident data…</div>
        ) : error ? (
          <div className="loading-panel error-panel">Incident data could not be loaded. Check that the data service is running.</div>
        ) : (
          <>
            {activeTab === 'feed' && (
              <div className="dashboard-content">
                <IncidentFeedGraph totalAlerts={totalAlertCount} incidents={incidents} reductionRate={reductionPercentage} />
                <IncidentFeed incidents={incidents} />
              </div>
            )}
            {activeTab === 'noise' && <NoiseStudio rules={noiseRules} onDecision={handleRuleDecision} whatIfImpact={whatIfImpact} />}
            {activeTab === 'metrics' && <MetricsScoreboard benchmarks={benchmarks} />}
            {activeTab === 'topology' && <TopologyView topology={topology} />}
          </>
        )}
      </main>

      <footer className="dashboard-footer">AO-01 <span>·</span> Service incident dashboard</footer>
    </div>
  );
}

export default App;
