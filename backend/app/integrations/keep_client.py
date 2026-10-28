import logging
from typing import List, Dict, Any, Optional
import httpx
from backend.app.config import config
from backend.app.models import Alert, Incident

logger = logging.getLogger("keep_client")

class KeepClient:
    """
    Thin client wrapper for verified Keep REST API endpoints.
    Reference: keephq/keep upstream API models (keep/api/models/db/incident.py, keep/api/routes)
    """
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        dry_run: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.dry_run = dry_run
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "ao01-origin-brain/1.0"
        }
        if self.api_key:
            self.headers["X-API-KEY"] = self.api_key

    def _validate_safety(self, url: str):
        """Enforces Safety Rule 2 & Section 10: refuses remote live URLs unless dry_run is overridden."""
        is_local = "localhost" in url or "127.0.0.1" in url or "host.docker.internal" in url
        if not is_local and not self.dry_run:
            raise PermissionError(
                f"SAFETY SHIELD: Keep client refused connection to non-localhost target '{url}'. "
                f"Live system modification is strictly prohibited."
            )

    def test_connection(self) -> Dict[str, Any]:
        if self.dry_run:
            return {"status": "ok", "mode": "dry-run (simulated)", "url": self.base_url}
        try:
            self._validate_safety(self.base_url)
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/docs", headers=self.headers)
                return {"status": "connected" if res.status_code == 200 else "degraded", "code": res.status_code}
        except Exception as e:
            return {"status": "unreachable", "error": str(e), "url": self.base_url}

    def push_alert_event(self, alert: Alert) -> Dict[str, Any]:
        """Pushes an incoming alert event into Keep webhook ingestion (/alerts/event)."""
        payload = {
            "id": alert.alert_id,
            "name": alert.name,
            "status": "firing",
            "lastReceived": alert.timestamp,
            "environment": "production",
            "service": alert.service,
            "source": [alert.source],
            "severity": alert.severity,
            "message": alert.message,
            "labels": {
                "host": alert.host or "unknown",
                "customer_ref": alert.customer_ref or "none",
                "rule_key": alert.rule_key or "default"
            }
        }
        if self.dry_run:
            return {"status": "recorded", "mode": "dry-run", "event": payload}

        self._validate_safety(self.base_url)
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{self.base_url}/alerts/event", json=payload, headers=self.headers)
            res.raise_for_status()
            return res.json()

    def create_incident(self, incident: Incident) -> Dict[str, Any]:
        """Creates a correlated incident in Keep (/incidents) with our probable origin and reasons."""
        payload = {
            "name": f"[{incident.severity.upper()}] Origin: {incident.origin.service} ({len(incident.alerts)} alerts)",
            "description": (
                f"{incident.summary}\n"
                f"Probable Root Cause: {incident.origin.service} (Confidence: {int(incident.origin.confidence*100)}%)\n"
                f"Water Pipe Analogy: {incident.water_pipe_analogy or 'N/A'}\n"
                f"Affected Services: {', '.join(incident.services)}\n"
                f"Correlated by: AO-01 Graph-Aware Deterministic Brain"
            ),
            "severity": incident.severity,
            "incident_type": "graph-topology-correlated",
            "is_visible": True,
            "is_predicted": False,
            "alert_ids": [a.alert_id for a in incident.alerts]
        }
        if self.dry_run:
            return {"status": "created", "mode": "dry-run (safe local record)", "keep_incident": payload}

        self._validate_safety(self.base_url)
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{self.base_url}/incidents", json=payload, headers=self.headers)
            res.raise_for_status()
            return res.json()

class KeepSink:
    """Synchronizes our engine's correlated incidents to Keep."""
    def __init__(self, client: Optional[KeepClient] = None):
        self.client = client or KeepClient(
            base_url=config.keep_url,
            api_key=config.keep_api_key,
            dry_run=config.keep_dry_run
        )

    def sync_incidents(self, incidents: List[Incident]) -> Dict[str, Any]:
        results = []
        for inc in incidents:
            res = self.client.create_incident(inc)
            results.append(res)
        return {
            "synced_count": len(results),
            "dry_run": self.client.dry_run,
            "target": self.client.base_url,
            "sample": results[:3]
        }

keep_client = KeepClient(base_url=config.keep_url, api_key=config.keep_api_key, dry_run=config.keep_dry_run)
keep_sink = KeepSink(keep_client)
