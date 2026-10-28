from typing import List, Dict, Any
from backend.app.models import Alert, Incident, OriginInfo, PriorityBreakdown, EdgeReason

def run_raw_baseline(alerts: List[Alert]) -> List[Incident]:
    """Baseline 1: No correlation at all. Every alert is its own incident card."""
    incidents = []
    for a in alerts:
        inc = Incident(
            incident_id=f"INC-RAW-{a.alert_id}",
            summary=f"Raw Alert: {a.name} on {a.service}",
            origin=OriginInfo(service=a.service, confidence=0.2),
            alerts=[a],
            services=[a.service],
            start_time=a.timestamp,
            end_time=a.timestamp,
            severity=a.severity,
            priority=PriorityBreakdown(score=0.5),
            edges=[]
        )
        incidents.append(inc)
    return incidents

def run_service_window_baseline(alerts: List[Alert], window_sec: float = 600.0) -> List[Incident]:
    """Baseline 2: Trivial rule: Group alerts on the same service within a 10-minute window."""
    sorted_alerts = sorted(alerts, key=lambda a: a.timestamp_epoch)
    clusters: List[List[Alert]] = []
    active_by_service: Dict[str, List[Alert]] = {}

    for a in sorted_alerts:
        svc = a.service
        existing = active_by_service.get(svc)
        if existing and (a.timestamp_epoch - existing[-1].timestamp_epoch) <= window_sec:
            existing.append(a)
        else:
            new_cluster = [a]
            active_by_service[svc] = new_cluster
            clusters.append(new_cluster)

    incidents = []
    for idx, c in enumerate(clusters):
        first = c[0]
        last = c[-1]
        inc = Incident(
            incident_id=f"INC-SVC-WIN-{idx+1:04d}",
            summary=f"{len(c)} alert(s) on service {first.service}",
            origin=OriginInfo(service=first.service, confidence=0.35),
            alerts=c,
            services=[first.service],
            start_time=first.timestamp,
            end_time=last.timestamp,
            severity=first.severity,
            priority=PriorityBreakdown(score=0.6),
            edges=[]
        )
        incidents.append(inc)
    return incidents

def run_keep_topology_processor_baseline(
    alerts: List[Alert],
    service_to_app: Dict[str, str],
    lookback_window_sec: float = 900.0  # 15 minutes default in Keep
) -> List[Incident]:
    """
    Baseline 3: Keep Topology Processor emulation (keep/topologies/topology_processor.py).
    Groups alerts occurring on services belonging to the same 'Application' within a 15-minute sliding window.
    Does not perform graph upstream root cause analysis or cross-application tracing.
    """
    sorted_alerts = sorted(alerts, key=lambda a: a.timestamp_epoch)
    clusters: List[List[Alert]] = []
    active_by_app: Dict[str, List[Alert]] = {}

    for a in sorted_alerts:
        app = service_to_app.get(a.service, a.service)
        existing = active_by_app.get(app)
        if existing and (a.timestamp_epoch - existing[-1].timestamp_epoch) <= lookback_window_sec:
            existing.append(a)
        else:
            new_cluster = [a]
            active_by_app[app] = new_cluster
            clusters.append(new_cluster)

    incidents = []
    for idx, c in enumerate(clusters):
        first = c[0]
        last = c[-1]
        svcs = list(set(x.service for x in c))
        app = service_to_app.get(first.service, first.service)
        inc = Incident(
            incident_id=f"INC-KEEP-TOPO-{idx+1:04d}",
            summary=f"Keep Topology Incident for application '{app}': {len(c)} alerts across {len(svcs)} service(s)",
            origin=OriginInfo(service=first.service, confidence=0.4),
            alerts=c,
            services=svcs,
            start_time=first.timestamp,
            end_time=last.timestamp,
            severity=first.severity,
            priority=PriorityBreakdown(score=0.7),
            edges=[]
        )
        incidents.append(inc)
    return incidents
