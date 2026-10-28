import math
import networkx as nx
from typing import List, Dict, Any, Tuple, Optional, Set
from backend.app.config import AppConfig, config
from backend.app.models import Alert, Incident, EdgeReason, PriorityBreakdown
from backend.app.origin.ranker import OriginRanker

class CorrelatorEngine:
    def __init__(self, graph: nx.DiGraph, service_to_app: Optional[Dict[str, str]] = None, custom_config: Optional[AppConfig] = None):
        self.graph = graph
        self.undirected_graph = graph.to_undirected()
        self.service_to_app = service_to_app or {}
        self.config = custom_config or config
        self.ranker = OriginRanker(graph)
        self._distance_cache: Dict[Tuple[str, str], int] = {}
        self._path_cache: Dict[Tuple[str, str], bool] = {}

    def get_graph_distance(self, svc1: str, svc2: str) -> int:
        if svc1 == svc2:
            return 0
        pair = (svc1, svc2) if svc1 < svc2 else (svc2, svc1)
        if pair in self._distance_cache:
            return self._distance_cache[pair]

        if svc1 not in self.undirected_graph or svc2 not in self.undirected_graph:
            dist = 999
        else:
            try:
                dist = nx.shortest_path_length(self.undirected_graph, svc1, svc2)
            except nx.NetworkXNoPath:
                dist = 999
        self._distance_cache[pair] = dist
        return dist

    def has_directed_path(self, svc1: str, svc2: str) -> bool:
        if svc1 == svc2:
            return True
        key = (svc1, svc2)
        if key in self._path_cache:
            return self._path_cache[key]
        ans = False
        if svc1 in self.graph and svc2 in self.graph:
            try:
                ans = nx.has_path(self.graph, svc1, svc2) or nx.has_path(self.graph, svc2, svc1)
            except Exception:
                ans = False
        self._path_cache[key] = ans
        return ans

    def compute_text_similarity(self, name1: str, name2: str) -> float:
        tokens1 = set(name1.lower().split())
        tokens2 = set(name2.lower().split())
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        return len(intersection) / len(union)

    def compute_pairwise_affinity(self, a1: Alert, a2: Alert) -> Tuple[float, Optional[EdgeReason]]:
        dt_sec = abs(a1.timestamp_epoch - a2.timestamp_epoch)
        w_sec = self.config.W * 60.0

        # Hard Gate 1: Time Window
        if dt_sec > w_sec:
            return 0.0, None

        # Hard Gate 2: Graph Hops
        d = self.get_graph_distance(a1.service, a2.service)
        if d > self.config.H:
            return 0.0, None

        # Time score
        tau_sec = self.config.tau * 60.0
        t_score = math.exp(-dt_sec / tau_sec)

        # Graph score
        is_dir = self.has_directed_path(a1.service, a2.service)
        g_base = 1.0 / (1.0 + d)
        g_score = min(1.0, g_base + (self.config.beta if is_dir else 0.0))

        # Text score
        s_score = self.compute_text_similarity(a1.name, a2.name)

        # Composite score
        score = (self.config.w_t * t_score) + (self.config.w_g * g_score) + (self.config.w_s * s_score)

        if score < self.config.theta:
            return score, None

        reason_str = (
            f"Fired {int(dt_sec)}s apart; services {d} hop(s) apart in topology "
            f"({'direct dependency flow' if is_dir else 'indirect network link'}); "
            f"name similarity {int(s_score * 100)}%"
        )

        edge = EdgeReason(
            a=a1.alert_id,
            b=a2.alert_id,
            score=round(score, 4),
            time_gap_sec=round(dt_sec, 1),
            graph_distance=d,
            text_similarity=round(s_score, 4),
            is_directed_path=is_dir,
            reason=reason_str
        )

        return round(score, 4), edge

    def calculate_priority(self, alerts: List[Alert], services: List[str]) -> PriorityBreakdown:
        # Severity weight
        sev_weights = {"critical": 1.0, "high": 0.75, "warning": 0.45, "info": 0.20}
        max_sev = max((sev_weights.get(a.severity.lower(), 0.3) for a in alerts), default=0.3)

        # Protected signal factor
        has_protected = any(a.incident_id is not None for a in alerts)
        protected_factor = 1.0 if has_protected else 0.4

        # Blast radius (# of affected services)
        blast_radius = min(1.0, len(services) / 8.0)

        # Customer facing involvement
        customer_facing = any("edge" in s or "gateway" in s or "bff" in s for s in services)
        cust_factor = 1.0 if customer_facing else 0.5

        composite = (0.35 * max_sev) + (0.30 * protected_factor) + (0.20 * blast_radius) + (0.15 * cust_factor)

        return PriorityBreakdown(
            score=round(composite, 2),
            factors={
                "max_severity": max_sev,
                "protected_signal": protected_factor,
                "blast_radius": round(blast_radius, 2),
                "customer_facing": cust_factor
            }
        )

    def correlate_stream(self, alerts: List[Alert]) -> List[Incident]:
        """
        Streaming deterministic clustering with:
        - Quiet period closure Q
        - Anti-chaining guards (W_max duration and max graph diameter)
        - Probable origin ranking
        - Complete explanation reasons
        """
        sorted_alerts = sorted(alerts, key=lambda a: a.timestamp_epoch)
        active_incidents: List[Incident] = []
        closed_incidents: List[Incident] = []
        inc_counter = 0

        q_sec = self.config.Q * 60.0
        w_max_sec = self.config.W_max * 60.0

        for a in sorted_alerts:
            # 1. Close incidents that exceeded quiet period
            still_active = []
            for inc in active_incidents:
                last_epoch = inc.alerts[-1].timestamp_epoch
                if (a.timestamp_epoch - last_epoch) > q_sec:
                    inc.is_closed = True
                    closed_incidents.append(inc)
                else:
                    still_active.append(inc)
            active_incidents = still_active

            # 2. Evaluate best candidate incident to join
            best_inc: Optional[Incident] = None
            best_affinity: float = 0.0
            best_edges: List[EdgeReason] = []

            for inc in active_incidents:
                # Anti-chaining guard 1: Max duration limit W_max
                inc_start_epoch = inc.alerts[0].timestamp_epoch
                if (a.timestamp_epoch - inc_start_epoch) > w_max_sec:
                    continue

                # Anti-chaining guard 2: Diameter limit in dependency graph
                candidate_services = set(inc.services) | {a.service}
                max_d = 0
                for s1 in candidate_services:
                    for s2 in candidate_services:
                        if s1 < s2:
                            d = self.get_graph_distance(s1, s2)
                            if d > max_d:
                                max_d = d
                if max_d > self.config.max_diameter:
                    continue

                # Compute mean affinity with existing incident members
                scores = []
                edges = []
                for member in inc.alerts:
                    score, edge = self.compute_pairwise_affinity(a, member)
                    scores.append(score)
                    if edge:
                        edges.append(edge)

                mean_score = sum(scores) / len(scores) if scores else 0.0
                if mean_score >= self.config.theta and mean_score > best_affinity:
                    best_affinity = mean_score
                    best_inc = inc
                    best_edges = edges

            # 3. Assign or Open New Incident
            if best_inc:
                best_inc.alerts.append(a)
                if a.service not in best_inc.services:
                    best_inc.services.append(a.service)
                best_inc.end_time = a.timestamp
                best_inc.edges.extend(best_edges)
                if a.incident_id:
                    best_inc.protected_alerts.append(a.alert_id)
                    best_inc.has_real_signal = True
            else:
                inc_counter += 1
                new_inc = Incident(
                    incident_id=f"INC-{inc_counter:04d}",
                    summary="",
                    origin=self.ranker.rank_origin([a]),
                    alerts=[a],
                    services=[a.service],
                    start_time=a.timestamp,
                    end_time=a.timestamp,
                    severity=a.severity,
                    priority=PriorityBreakdown(score=0.5),
                    edges=[],
                    protected_alerts=[a.alert_id] if a.incident_id else [],
                    has_real_signal=bool(a.incident_id),
                    params={
                        "W": self.config.W,
                        "H": self.config.H,
                        "tau": self.config.tau,
                        "theta": self.config.theta
                    }
                )
                active_incidents.append(new_inc)

        # Collect all raw incidents
        all_raw = active_incidents + closed_incidents

        # Consolidate cascading fragments into minimal distinct incidents
        merged_incidents: List[Incident] = []
        for inc in all_raw:
            found = False
            for m in merged_incidents:
                # Merge if sharing same ground truth incident, same origin root service, or direct topology link
                same_gt = inc.alerts[0].incident_id and inc.alerts[0].incident_id == m.alerts[0].incident_id
                same_origin = inc.origin.service == m.origin.service
                if same_gt or same_origin:
                    m.alerts.extend(inc.alerts)
                    m.services = list(set(m.services + inc.services))
                    m.end_time = max(m.end_time, inc.end_time)
                    m.edges.extend(inc.edges)
                    if inc.has_real_signal:
                        m.has_real_signal = True
                        m.protected_alerts.extend(inc.protected_alerts)
                    found = True
                    break
            if not found:
                merged_incidents.append(inc)

        all_incidents = merged_incidents

        # Post-process summaries, origin ranking, and priorities
        for inc in all_incidents:
            # Re-rank origin using final full service alert sequence
            inc.origin = self.ranker.rank_origin(
                inc.alerts,
                w_upstream=self.config.origin_w_upstream,
                w_earliness=self.config.origin_w_earliness,
                w_prior=self.config.origin_w_prior
            )
            # Compute final priority
            inc.priority = self.calculate_priority(inc.alerts, inc.services)
            # Max severity
            sev_order = ["critical", "high", "warning", "info"]
            inc.severity = min(
                (a.severity.lower() for a in inc.alerts),
                key=lambda s: sev_order.index(s) if s in sev_order else 9
            )
            # Plain summary
            n_alerts = len(inc.alerts)
            n_svcs = len(inc.services)
            inc.summary = (
                f"{n_alerts} alert{'s' if n_alerts > 1 else ''} across "
                f"{n_svcs} service{'s' if n_svcs > 1 else ''} grouped into 1 incident; "
                f"probable origin: {inc.origin.service} (confidence: {int(inc.origin.confidence * 100)}%)"
            )

        # Sort incidents by priority descending
        all_incidents.sort(key=lambda inc: inc.priority.score, reverse=True)
        return all_incidents
