import React, { useEffect, useMemo, useState } from 'react';
import type { Alert, Incident } from '../types';

interface IncidentFeedGraphProps {
  totalAlerts: number;
  incidents: Incident[];
  reductionRate: number;
}

interface TimelineBin {
  start: number;
  end: number;
  rawAlerts: number;
  incidentStarts: Incident[];
  activeIncidents: Incident[];
}

const alertTime = (alert: Alert) => {
  const epoch = Number(alert.timestamp_epoch);
  if (Number.isFinite(epoch) && epoch > 0) return epoch * 1000;
  return Date.parse(alert.timestamp);
};

const incidentAlertCount = (incident: Incident) => (incident.alerts || []).reduce(
  (count, alert) => count + Math.max(1, alert.dedup_count || 1), 0);

const formatTime = (value: number, includeDate: boolean) => {
  const date = new Date(value);
  return includeDate
    ? date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
};

export const IncidentFeedGraph: React.FC<IncidentFeedGraphProps> = ({ totalAlerts, incidents, reductionRate }) => {
  const [selectedId, setSelectedId] = useState<string | null>(incidents[0]?.incident_id ?? null);
  const [explanation, setExplanation] = useState<{ brief_description?: string; what_it_implies?: string } | null>(null);
  const [explanationLoading, setExplanationLoading] = useState(false);

  const { bins, maxAlerts, startTime, endTime } = useMemo(() => {
    const eventTimes = incidents.flatMap((incident) =>
      (incident.alerts || []).map(alertTime).filter(Number.isFinite));
    const starts = incidents.map((incident) => Date.parse(incident.start_time)).filter(Number.isFinite);
    const times = [...eventTimes, ...starts];
    const minimum = times.length ? Math.min(...times) : Date.now();
    const maximum = times.length ? Math.max(...times) : minimum + 1;
    const span = Math.max(60_000, maximum - minimum + 1);
    const binCount = Math.min(16, Math.max(8, Math.ceil(incidents.length / 2)));
    const binSize = span / binCount;
    const timeline: TimelineBin[] = Array.from({ length: binCount }, (_, index) => ({
      start: minimum + index * binSize,
      end: minimum + (index + 1) * binSize,
      rawAlerts: 0,
      incidentStarts: [],
      activeIncidents: [],
    }));

    incidents.forEach((incident) => {
      const parsedStart = Date.parse(incident.start_time);
      const start = Number.isFinite(parsedStart) ? parsedStart : minimum;
      const startIndex = Math.min(binCount - 1, Math.max(0, Math.floor((start - minimum) / binSize)));
      timeline[startIndex].incidentStarts.push(incident);

      (incident.alerts || []).forEach((alert) => {
        const time = alertTime(alert);
        const index = Number.isFinite(time)
          ? Math.min(binCount - 1, Math.max(0, Math.floor((time - minimum) / binSize)))
          : startIndex;
        const bin = timeline[index];
        bin.rawAlerts += Math.max(1, alert.dedup_count || 1);
        if (!bin.activeIncidents.some((item) => item.incident_id === incident.incident_id)) {
          bin.activeIncidents.push(incident);
        }
      });
    });

    return {
      bins: timeline,
      maxAlerts: Math.max(1, ...timeline.map((bin) => bin.rawAlerts)),
      startTime: minimum,
      endTime: maximum,
    };
  }, [incidents]);

  const selectedIncident = incidents.find((incident) => incident.incident_id === selectedId) ?? incidents[0] ?? null;
  const selectedIncidentId = selectedIncident?.incident_id;
  const dateRange = new Date(startTime).toLocaleDateString() === new Date(endTime).toLocaleDateString();

  useEffect(() => {
    setSelectedId((current) => incidents.some((incident) => incident.incident_id === current)
      ? current
      : incidents[0]?.incident_id ?? null);
  }, [incidents]);

  useEffect(() => {
    if (!selectedIncidentId) {
      setExplanation(null);
      return;
    }

    let current = true;
    setExplanation(null);
    setExplanationLoading(true);
    fetch(`/api/incidents/${encodeURIComponent(selectedIncidentId)}/explain`, { method: 'POST' })
      .then((response) => {
        if (!response.ok) throw new Error('Explanation unavailable');
        return response.json();
      })
      .then((result) => { if (current) setExplanation(result); })
      .catch(() => { if (current) setExplanation(null); })
      .finally(() => { if (current) setExplanationLoading(false); });

    return () => { current = false; };
  }, [selectedIncidentId]);

  return (
    <section className="incident-chart-panel" aria-labelledby="incident-chart-title">
      <header className="incident-chart-header">
        <div>
          <p className="chart-kicker">LIVE INCIDENT FEED</p>
          <h2 id="incident-chart-title">Alert activity over time</h2>
          <p className="chart-intro">Red bars show incoming alerts. White markers show when the system opened an incident.</p>
        </div>
        <div className="chart-summary" aria-label="Feed totals">
          <div><strong>{totalAlerts.toLocaleString()}</strong><span>raw alerts</span></div>
          <div><strong>{incidents.length.toLocaleString()}</strong><span>incidents opened</span></div>
          <div><strong>{reductionRate.toFixed(1)}%</strong><span>alert reduction</span></div>
        </div>
      </header>

      {incidents.length === 0 ? (
        <div className="chart-empty">No incidents are available to graph.</div>
      ) : (
        <>
          <div className="chart-legend">
            <span className="legend-item"><span className="legend-swatch alert-swatch" /> Alerts received</span>
            <span className="legend-item"><span className="legend-swatch incident-swatch" /> Incidents opened</span>
            <span className="legend-hint">Select a time window to inspect its highest-priority incident.</span>
          </div>
          <div className="timeline-chart">
            <div className="timeline-y-axis" aria-hidden="true">
              {[maxAlerts, Math.round(maxAlerts / 2), 0].map((value, index) => <span key={`${value}-${index}`}>{value}</span>)}
            </div>
            <div className="timeline-main">
              <div className="timeline-plot" style={{ '--bin-count': bins.length } as React.CSSProperties}>
                {[0, 50, 100].map((position) => <span key={position} className={`timeline-gridline grid-${position}`} aria-hidden="true" />)}
                {bins.map((bin, index) => {
                  const incidentsInWindow = bin.activeIncidents.length ? bin.activeIncidents : bin.incidentStarts;
                  const selectedInBin = incidentsInWindow
                    .slice()
                    .sort((a, b) => (b.priority?.score || 0) - (a.priority?.score || 0))[0];
                  const selected = selectedIncident?.incident_id === selectedInBin?.incident_id;
                  const intensity = bin.rawAlerts / maxAlerts;
                  const height = bin.rawAlerts ? Math.max(5, intensity * 100) : 0;
                  const title = `${formatTime(bin.start, !dateRange)} — ${bin.rawAlerts} alerts, ${bin.incidentStarts.length} incidents opened`;

                  return (
                    <button
                      key={index}
                      type="button"
                      className={`timeline-bin ${selected ? 'is-selected' : ''} ${bin.rawAlerts ? '' : 'is-empty'}`}
                      onClick={() => selectedInBin && setSelectedId(selectedInBin.incident_id)}
                      disabled={!selectedInBin}
                      aria-pressed={selected}
                      aria-label={`${title}${selectedInBin ? `. Inspect ${selectedInBin.incident_id}` : ''}`}
                      title={title}
                    >
                      <span className="timeline-value">{bin.rawAlerts || ''}</span>
                      <span className="timeline-bar-area">
                        <span className="timeline-bar" style={{ height: `${height}%`, opacity: 0.6 + intensity * 0.4 }} />
                      </span>
                      <span className="timeline-opened" aria-label={`${bin.incidentStarts.length} incidents opened`}>
                        {bin.incidentStarts.slice(0, 3).map((incident) => <i key={incident.incident_id} />)}
                        {bin.incidentStarts.length > 3 && <b>+{bin.incidentStarts.length - 3}</b>}
                      </span>
                      <span className="timeline-label">{formatTime(bin.start, !dateRange)}</span>
                    </button>
                  );
                })}
              </div>
              <div className="timeline-axis-caption">{formatTime(startTime, true)} <span>TIME</span> {formatTime(endTime, true)}</div>
            </div>
          </div>

          {selectedIncident && (
            <div className="selected-incident" aria-live="polite">
              <div className="selected-mark" aria-hidden="true" />
              <div className="selected-copy">
                <div className="selected-overline">INCIDENT DETAIL <span>{selectedIncident.incident_id}</span></div>
                <h3>{selectedIncident.summary}</h3>
                <p>Likely source: <strong>{selectedIncident.origin.service}</strong> · {incidentAlertCount(selectedIncident)} raw alerts · {selectedIncident.alerts?.length ?? 0} grouped records · {selectedIncident.services?.length ?? 0} services</p>
                <div className="selected-explanation" aria-live="polite">
                  <p>{explanationLoading ? 'Loading explanation…' : explanation?.brief_description || selectedIncident.ai_summary || 'Explanation is not available right now.'}</p>
                  {(explanation?.what_it_implies || selectedIncident.ai_implication) && <p>{explanation?.what_it_implies || selectedIncident.ai_implication}</p>}
                </div>
              </div>
              <div className="selected-confidence"><strong>{Math.round(selectedIncident.origin.confidence * 100)}%</strong><span>source match</span></div>
              <div className="selected-priority">Priority <strong>{Math.round((selectedIncident.priority?.score ?? 0) * 100)}</strong></div>
            </div>
          )}
        </>
      )}
    </section>
  );
};
