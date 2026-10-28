import re
import json
import os
import networkx as nx
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from backend.app.models import Alert, ServiceNode

# Normalization regex
_UUID_OR_HEX = re.compile(r'(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{16,64})', re.IGNORECASE)
_IP_PATTERN = re.compile(r'\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?')
_HOST_PATTERN = re.compile(r'(?:srv|host|node|pod)[-_a-zA-Z0-9.]+', re.IGNORECASE)
_DIGITS_PATTERN = re.compile(r'(?:^|[_ -])\d+(?:$|[_ -])')

def normalize_alert_name(name: str, message: str = "") -> str:
    """Produces clean normalized rule name by stripping transient runtime IDs, numbers, and hosts."""
    base = name.lower()
    base = _UUID_OR_HEX.sub('', base)
    base = _IP_PATTERN.sub('', base)
    base = _HOST_PATTERN.sub('', base)
    base = _DIGITS_PATTERN.sub(' ', base)
    base = re.sub(r'[\d_]+', ' ', base)
    base = re.sub(r'[^a-z0-9-]+', ' ', base).strip()
    return base or "generic-alert"

def build_rule_key(source: str, service: str, name: str) -> str:
    norm = normalize_alert_name(name)
    return f"{source.lower().strip()}:{service.lower().strip()}:{norm}"

class DatasetLoader:
    def __init__(self, data_dir: str = "data/synthetic"):
        self.data_dir = data_dir
        self.graph = nx.DiGraph()
        self.services_dict: Dict[str, ServiceNode] = {}
        self.raw_alerts: List[Alert] = []
        self.incidents: List[Dict[str, Any]] = []

    def load_topology(self, filepath: Optional[str] = None) -> nx.DiGraph:
        path = filepath or os.path.join(self.data_dir, "topology.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Topology file not found at {path}")

        with open(path, "r") as f:
            data = json.load(f)

        self.graph = nx.DiGraph()
        self.services_dict.clear()

        for s_info in data.get("services", []):
            s_node = ServiceNode(**s_info)
            self.services_dict[s_node.service] = s_node
            self.graph.add_node(
                s_node.service,
                tier=s_node.tier,
                application=s_node.application
            )

        # Edges: A -> B means A depends on B (downstream failure in B breaks upstream A)
        for s_node in self.services_dict.values():
            for dep in s_node.dependencies:
                if dep in self.services_dict:
                    self.graph.add_edge(s_node.service, dep)

        return self.graph

    def load_alerts(self, filepath: Optional[str] = None) -> List[Alert]:
        path = filepath or os.path.join(self.data_dir, "alerts.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Alerts file not found at {path}")

        with open(path, "r") as f:
            data = json.load(f)

        raw_list = data.get("alerts", [])
        self.raw_alerts = []

        for item in raw_list:
            # Map alternative keys if necessary
            a_id = item.get("alert_id") or item.get("id") or item.get("alertId")
            ts = item.get("timestamp") or item.get("time") or item.get("@timestamp")
            
            # Epoch conversion
            if "timestamp_epoch" in item:
                epoch = float(item["timestamp_epoch"])
            else:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    epoch = dt.timestamp()
                except Exception:
                    epoch = 0.0

            src = item.get("source") or "unknown"
            svc = item.get("service") or item.get("app") or "unknown"
            sev = (item.get("severity") or item.get("level") or "warning").lower()
            name = item.get("name") or item.get("rule") or "Alert"
            msg = item.get("message") or item.get("description") or name
            host = item.get("host") or item.get("node")
            cust = item.get("customer_ref") or item.get("tenant_id")
            inc_id = item.get("incident_id")

            rk = build_rule_key(src, svc, name)

            alert = Alert(
                alert_id=str(a_id),
                timestamp=ts,
                timestamp_epoch=epoch,
                source=src,
                service=svc,
                severity=sev,
                name=name,
                message=msg,
                host=host,
                customer_ref=cust,
                incident_id=inc_id,
                rule_key=rk,
                first_seen=ts,
                last_seen=ts
            )
            self.raw_alerts.append(alert)

        return self.raw_alerts

    def load_incidents(self, filepath: Optional[str] = None) -> List[Dict[str, Any]]:
        path = filepath or os.path.join(self.data_dir, "incidents.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                self.incidents = json.load(f).get("incidents", [])
        return self.incidents

    def deduplicate(self, window_sec: float = 300.0) -> List[Alert]:
        """Sliding-window exact deduplication for (rule_key, host). Keeps first/last seen and counts."""
        if not self.raw_alerts:
            self.load_alerts()

        sorted_alerts = sorted(self.raw_alerts, key=lambda a: a.timestamp_epoch)
        deduped: List[Alert] = []
        active_buckets: Dict[Tuple[str, Optional[str]], Alert] = {}

        for a in sorted_alerts:
            key = (a.rule_key or "", a.host)
            existing = active_buckets.get(key)

            if existing and (a.timestamp_epoch - existing.timestamp_epoch) <= window_sec:
                # Collapse into existing
                existing.dedup_count += 1
                existing.last_seen = a.timestamp
            else:
                new_a = a.model_copy()
                new_a.dedup_count = 1
                active_buckets[key] = new_a
                deduped.append(new_a)

        return deduped

    def profile_data(self) -> Dict[str, Any]:
        """Generates statistical profile of dataset."""
        if not self.raw_alerts:
            self.load_alerts()

        total = len(self.raw_alerts)
        linked = sum(1 for a in self.raw_alerts if a.incident_id is not None)
        unlinked = total - linked

        sources: Dict[str, int] = {}
        services: Dict[str, int] = {}
        rule_keys: Dict[str, int] = {}
        rule_linked: Dict[str, int] = {}

        for a in self.raw_alerts:
            sources[a.source] = sources.get(a.source, 0) + 1
            services[a.service] = services.get(a.service, 0) + 1
            rk = a.rule_key or "unknown"
            rule_keys[rk] = rule_keys.get(rk, 0) + 1
            if a.incident_id:
                rule_linked[rk] = rule_linked.get(rk, 0) + 1

        zero_incident_rules = [rk for rk in rule_keys if rk not in rule_linked]
        deduped = self.deduplicate()
        dedup_rate = (1.0 - (len(deduped) / total)) if total > 0 else 0.0

        return {
            "total_alerts": total,
            "deduped_alert_groups": len(deduped),
            "exact_dedup_reduction": round(dedup_rate * 100, 2),
            "ground_truth_incident_alerts": linked,
            "unlinked_noise_alerts": unlinked,
            "noise_percentage": round((unlinked / total) * 100, 2) if total > 0 else 0.0,
            "distinct_sources": len(sources),
            "sources": sources,
            "distinct_services": len(services),
            "top_services": sorted(services.items(), key=lambda x: x[1], reverse=True)[:8],
            "total_rule_keys": len(rule_keys),
            "zero_incident_rules_count": len(zero_incident_rules),
            "zero_incident_rules_samples": zero_incident_rules[:5],
            "graph_nodes": self.graph.number_of_nodes(),
            "graph_edges": self.graph.number_of_edges()
        }

loader = DatasetLoader()
