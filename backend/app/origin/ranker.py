import networkx as nx
from typing import List, Dict, Any, Tuple, Optional
from backend.app.models import Alert, OriginInfo, OriginRankingItem, DependencyPath

class OriginRanker:
    def __init__(self, graph: nx.DiGraph, historical_priors: Optional[Dict[str, float]] = None):
        self.graph = graph
        # Historical frequency prior of root-cause services
        self.priors: Dict[str, float] = historical_priors or {
            "orders-db": 0.45,
            "payments-db": 0.40,
            "catalog-db": 0.35,
            "users-db": 0.30,
            "cart-service": 0.25,
            "ssl-terminator": 0.25,
            "dns-resolver": 0.25,
            "cloud-kms": 0.25,
            "stripe-api": 0.25,
            "search-elasticsearch": 0.25,
            "cache-redis-cluster": 0.25,
            "edge-cdn": 0.20,
            "user-service": 0.20
        }

    def rank_origin(
        self,
        alerts: List[Alert],
        w_upstream: float = 0.50,
        w_earliness: float = 0.30,
        w_prior: float = 0.20
    ) -> OriginInfo:
        """
        Ranks probable origin across the alerting service set S:
        - upstream_score(s): Downstream blast radius (other alerting services reachable from s in dependency graph).
        - earliness(s): Normalized temporal order of s's first alert.
        - prior(s): Historical root-cause likelihood (smoothed).
        """
        if not alerts:
            return OriginInfo(service="unknown", confidence=0.0, ranking=[], paths=[])

        # Service first alert times
        service_first_seen: Dict[str, float] = {}
        for a in alerts:
            svc = a.service
            if svc not in service_first_seen or a.timestamp_epoch < service_first_seen[svc]:
                service_first_seen[svc] = a.timestamp_epoch

        alerting_services = list(service_first_seen.keys())
        num_services = len(alerting_services)

        if num_services == 1:
            only_svc = alerting_services[0]
            item = OriginRankingItem(
                service=only_svc,
                score=1.0,
                upstream_score=1.0,
                earliness=1.0,
                prior=self.priors.get(only_svc, 0.1),
                first_alert_time=alerts[0].timestamp
            )
            return OriginInfo(service=only_svc, confidence=0.9, ranking=[item], paths=[])

        # Earliness scores
        sorted_by_time = sorted(alerting_services, key=lambda s: service_first_seen[s])
        earliness_scores: Dict[str, float] = {}
        for rank_idx, s in enumerate(sorted_by_time):
            # Rank 0 is earliest -> score 1.0
            earliness_scores[s] = 1.0 - (rank_idx / (num_services - 1)) if num_services > 1 else 1.0

        # Upstream scores (reachability in dependency graph)
        # Edge (A, B) means A depends on B.
        # If B fails, its failure propagates to any A that depends on B.
        # So we look at reverse reachability in graph, or forward in reversed graph!
        rev_graph = self.graph.reverse()
        upstream_scores: Dict[str, float] = {}
        candidate_paths: Dict[str, List[DependencyPath]] = {}

        for cand in alerting_services:
            reachable_count = 0
            paths_from_cand = []

            for other in alerting_services:
                if other == cand:
                    continue
                # Is other reachable from cand via dependency failure propagation?
                if cand in rev_graph and other in rev_graph:
                    try:
                        if nx.has_path(rev_graph, cand, other):
                            path = nx.shortest_path(rev_graph, cand, other)
                            reachable_count += 1
                            paths_from_cand.append(DependencyPath(to_service=other, path=path))
                    except Exception:
                        pass

            upstream_scores[cand] = reachable_count / (num_services - 1) if (num_services > 1) else 1.0
            candidate_paths[cand] = paths_from_cand

        # Composite scores
        ranking_items: List[OriginRankingItem] = []
        for s in alerting_services:
            u = upstream_scores.get(s, 0.0)
            e = earliness_scores.get(s, 0.0)
            p = self.priors.get(s, 0.05)
            comp_score = (w_upstream * u) + (w_earliness * e) + (w_prior * p)
            first_ts = next((a.timestamp for a in alerts if a.service == s), None)
            ranking_items.append(OriginRankingItem(
                service=s,
                score=round(comp_score, 4),
                upstream_score=round(u, 4),
                earliness=round(e, 4),
                prior=round(p, 4),
                first_alert_time=first_ts
            ))

        ranking_items.sort(key=lambda r: r.score, reverse=True)
        top = ranking_items[0]
        confidence = min(0.99, top.score)

        return OriginInfo(
            service=top.service,
            confidence=round(confidence, 2),
            ranking=ranking_items,
            paths=candidate_paths.get(top.service, [])
        )
