import React from 'react';
import type { Incident } from '../types';

interface IncidentFeedProps {
  incidents: Incident[];
}

const severities = ['critical', 'high', 'warning'] as const;
const formatSeverity = (value: string) => value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();

function IncidentChart({ incidents }: IncidentFeedProps) {
  const counts = severities.map((severity) => ({
    severity,
    count: incidents.filter((incident) => incident.severity.toLowerCase() === severity).length,
  }));
  const maxCount = Math.max(1, ...counts.map(({ count }) => count));

  return (
    <section className="chart-panel" aria-labelledby="incident-chart-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AT A GLANCE</p>
          <h2 id="incident-chart-title">Incident Feed</h2>
          <p className="section-description">Each bar shows the number of incidents at that level.</p>
        </div>
        <p className="chart-total"><strong>{incidents.length}</strong><span>incidents</span></p>
      </div>

      <div
        className="severity-chart"
        role="img"
        aria-label={counts.map(({ severity, count }) => `${formatSeverity(severity)}: ${count} incidents`).join(', ')}
      >
        {counts.map(({ severity, count }) => (
          <div className="chart-row" key={severity}>
            <span className="chart-label">{formatSeverity(severity)}</span>
            <div className="chart-track" aria-hidden="true">
              <div
                className={`chart-bar severity-${severity}`}
                style={{ width: count === 0 ? '0%' : `${Math.max(4, (count / maxCount) * 100)}%` }}
              />
            </div>
            <span className="chart-count">{count}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export const IncidentFeed: React.FC<IncidentFeedProps> = ({ incidents }) => (
  <div className="feed-layout">
    <IncidentChart incidents={incidents} />

    <section className="incident-section" aria-labelledby="incident-list-title">
      <div className="section-heading list-heading">
        <div>
          <p className="eyebrow">ALL EVENTS</p>
          <h2 id="incident-list-title">Incidents</h2>
        </div>
        <span className="plain-count">{incidents.length} shown</span>
      </div>

      {incidents.length === 0 ? (
        <div className="empty-state">No incidents to show.</div>
      ) : (
        <div className="incident-list">
          {incidents.map((incident) => (
            <article className="incident-card" key={incident.incident_id}>
              <div className={`severity-marker severity-${incident.severity.toLowerCase()}`} aria-hidden="true" />
              <div className="incident-main">
                <div className="incident-meta">
                  <span className="incident-id">{incident.incident_id}</span>
                  <span className={`severity-tag severity-${incident.severity.toLowerCase()}`}>
                    {formatSeverity(incident.severity)}
                  </span>
                </div>
                <h3>{incident.summary}</h3>
                <p className="incident-facts">
                  <span><strong>Main service:</strong> {incident.origin.service}</span>
                  <span><strong>Alerts:</strong> {incident.alerts.length}</span>
                  <span><strong>Services affected:</strong> {incident.services.length}</span>
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  </div>
);
