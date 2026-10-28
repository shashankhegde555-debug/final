import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { IncidentFeed } from './components/IncidentFeed';
import { IncidentDetailModal } from './components/IncidentDetailModal';
import { NoiseStudio } from './components/NoiseStudio';
import { MetricsScoreboard } from './components/MetricsScoreboard';
import { TopologyView } from './components/TopologyView';
import { ReplayControl } from './components/ReplayControl';
import { Incident, RuleNoiseStats, EvaluationReport, TopologyData } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'feed' | 'noise' | 'metrics' | 'topology'>('feed');
  const [redactionEnabled, setRedactionEnabled] = useState<boolean>(true);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [noiseRules, setNoiseRules] = useState<RuleNoiseStats[]>([]);
  const [whatIfImpact, setWhatIfImpact] = useState<any>(null);
  const [benchmarks, setBenchmarks] = useState<EvaluationReport[]>([]);
  const [topology, setTopology] = useState<TopologyData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState<boolean>(true);

  // Replay stream simulation
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(5);
  const [replayAlertCount, setReplayAlertCount] = useState<number>(16848);
  const totalAlertsCount = 16848;

  // Initial Data Fetch
  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [incRes, noiseRes, whatIfRes, metricsRes, topoRes, redactRes] = await Promise.all([
          fetch('/api/incidents?limit=100').then((r) => r.json()),
          fetch('/api/noise/rules').then((r) => r.json()),
          fetch('/api/noise/what-if').then((r) => r.json()),
          fetch('/api/metrics').then((r) => r.json()),
          fetch('/api/topology').then((r) => r.json()),
          fetch('/api/redaction').then((r) => r.json()),
        ]);

        setIncidents(incRes.incidents || []);
        setNoiseRules(noiseRes.rules || []);
        setWhatIfImpact(whatIfRes || null);
        setBenchmarks(metricsRes.benchmarks || []);
        setTopology(topoRes || { nodes: [], edges: [] });
        setRedactionEnabled(redactRes.redaction_enabled ?? true);
      } catch (err) {
        console.error('Error fetching initial data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  // Handle Redaction Toggle
  const handleRedactionToggle = async (val: boolean) => {
    setRedactionEnabled(val);
    try {
      await fetch('/api/redaction', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ redaction_enabled: val }),
      });
      // Refresh incidents with new redaction view
      const incRes = await fetch('/api/incidents?limit=100').then((r) => r.json());
      setIncidents(incRes.incidents || []);
      if (selectedIncident) {
        const detail = await fetch(`/api/incidents/${selectedIncident.incident_id}`).then((r) => r.json());
        setSelectedIncident(detail);
      }
    } catch (err) {
      console.error('Error updating redaction:', err);
    }
  };

  // Handle Rule Decision in Noise Studio
  const handleRuleDecision = async (ruleKey: string, decision: 'approved' | 'rejected') => {
    try {
      await fetch(`/api/noise/rules/${encodeURIComponent(ruleKey)}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      });
      // Refresh noise rules and what-if
      const [noiseRes, whatIfRes] = await Promise.all([
        fetch('/api/noise/rules').then((r) => r.json()),
        fetch('/api/noise/what-if').then((r) => r.json()),
      ]);
      setNoiseRules(noiseRes.rules || []);
      setWhatIfImpact(whatIfRes || null);
    } catch (err) {
      console.error('Error recording rule decision:', err);
    }
  };

  // Handle on-demand 2B LLM diagnosis
  const handleTriggerLLM = async (incidentId: string) => {
    try {
      const res = await fetch(`/api/incidents/${incidentId}/explain`, {
        method: 'POST',
      }).then((r) => r.json());

      if (selectedIncident && selectedIncident.incident_id === incidentId) {
        setSelectedIncident({
          ...selectedIncident,
          water_pipe_analogy: res.water_pipe_analogy,
          ai_summary: res.diagnostic_summary,
        });
      }

      setIncidents((prev) =>
        prev.map((inc) =>
          inc.incident_id === incidentId
            ? { ...inc, water_pipe_analogy: res.water_pipe_analogy, ai_summary: res.diagnostic_summary }
            : inc
        )
      );
    } catch (err) {
      console.error('Error triggering LLM diagnosis:', err);
    }
  };

  // Replay Timer Loop
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setReplayAlertCount((prev) => {
        const next = prev + speed * 15;
        if (next >= totalAlertsCount) {
          setIsPlaying(false);
          return totalAlertsCount;
        }
        return next;
      });
    }, 150);
    return () => clearInterval(interval);
  }, [isPlaying, speed]);

  const handleResetReplay = () => {
    setIsPlaying(false);
    setReplayAlertCount(1500);
  };

  // Slice displayed incidents proportional to replay progression
  const displayedIncidents = incidents.slice(
    0,
    Math.max(5, Math.floor((replayAlertCount / totalAlertsCount) * incidents.length))
  );

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans antialiased pb-24">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        redactionEnabled={redactionEnabled}
        setRedactionEnabled={handleRedactionToggle}
        rawAlertsCount={replayAlertCount}
        incidentsCount={displayedIncidents.length}
        reductionPercentage={53.3}
        incidentRecall={100.0}
      />

      {/* Main Body */}
      <main className="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
        {loading ? (
          <div className="py-24 text-center text-slate-500 text-sm animate-pulse">
            Loading AO-01 deterministic correlation engine & platform telemetry...
          </div>
        ) : (
          <>
            {activeTab === 'feed' && (
              <IncidentFeed
                incidents={displayedIncidents}
                onSelectIncident={(inc) => setSelectedIncident(inc)}
              />
            )}

            {activeTab === 'noise' && (
              <NoiseStudio
                rules={noiseRules}
                onDecision={handleRuleDecision}
                whatIfImpact={whatIfImpact}
              />
            )}

            {activeTab === 'metrics' && (
              <MetricsScoreboard benchmarks={benchmarks} />
            )}

            {activeTab === 'topology' && (
              <TopologyView topology={topology} />
            )}
          </>
        )}
      </main>

      {/* Replay Floating Control Bar */}
      <ReplayControl
        isPlaying={isPlaying}
        onTogglePlay={() => setIsPlaying(!isPlaying)}
        speed={speed}
        onSetSpeed={(s) => setSpeed(s)}
        onReset={handleResetReplay}
        currentReplayCount={replayAlertCount}
        totalAlerts={totalAlertsCount}
      />

      {/* Incident Detail Modal */}
      {selectedIncident && (
        <IncidentDetailModal
          incident={selectedIncident}
          topology={topology}
          onClose={() => setSelectedIncident(null)}
          onTriggerLLM={handleTriggerLLM}
        />
      )}
    </div>
  );
}

export default App;
