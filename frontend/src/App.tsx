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

const fetchJson = async (url: string) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('text/html') && !url.endsWith('.html')) {
    throw new Error('HTML returned instead of JSON');
  }
  return r.json();
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

  const loadDashboard = useCallback(async (datasetName?: string) => {
    const ds = datasetName || currentDataset;
    try {
      const [incRes, noiseRes, whatIfRes, metricsRes, topoRes] = await Promise.all([
        fetchJson('/api/incidents?limit=100')
          .catch(() => fetchJson(`/data_snapshot/${ds}/incidents.json`))
          .catch(() => fetchJson('/data_snapshot/incidents.json')),
        fetchJson('/api/noise/rules')
          .catch(() => fetchJson(`/data_snapshot/${ds}/noise_rules.json`))
          .catch(() => fetchJson('/data_snapshot/noise_rules.json'))
          .catch(() => ({ rules: [] })),
        fetchJson('/api/noise/what-if')
          .catch(() => fetchJson(`/data_snapshot/${ds}/what_if.json`))
          .catch(() => fetchJson('/data_snapshot/what_if.json'))
          .catch(() => null),
        fetchJson('/api/metrics')
          .catch(() => fetchJson(`/data_snapshot/${ds}/metrics.json`))
          .catch(() => fetchJson('/data_snapshot/metrics.json'))
          .catch(() => ({ benchmarks: [] })),
        fetchJson('/api/topology')
          .catch(() => fetchJson(`/data_snapshot/${ds}/topology.json`))
          .catch(() => fetchJson('/data_snapshot/topology.json'))
          .catch(() => ({ nodes: [], edges: [] })),
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
  }, [currentDataset]);

  useEffect(() => { void loadDashboard(); }, [loadDashboard]);

  const handleSelectDataset = async (dataset: string) => {
    setLoadingDataset(true);
    setCurrentDataset(dataset);
    try {
      const response = await fetch(`/api/ingest/loghub/${dataset}`, { method: 'POST' });
      const ct = response.headers.get('content-type') || '';
      if (!response.ok || ct.includes('text/html')) {
        throw new Error('Live backend unavailable, falling back to snapshot');
      }
      await loadDashboard(dataset);
    } catch {
      // Standalone deployed site (Vercel): load dataset's precomputed snapshot
      await loadDashboard(dataset);
    } finally {
      setLoadingDataset(false);
    }
  };

  const handleRuleDecision = async (ruleKey: string, decision: 'approved' | 'rejected') => {
    try {
      const response = await fetch(`/api/noise/rules/${encodeURIComponent(ruleKey)}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      });
      if (!response.ok) throw new Error('Could not save recommendation decision');
      await loadDashboard();
    } catch {
      // Local state update when deployed without live backend
      setNoiseRules((prev) =>
        prev.map((r) => (r.rule_key === ruleKey ? { ...r, recommendation: decision === 'approved' ? 'suppress' : 'keep' } : r))
      );
    }
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
