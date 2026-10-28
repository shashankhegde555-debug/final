from typing import List, Set, Dict, Any
from backend.app.models import Alert, Incident, PriorityBreakdown, OriginInfo

class RecallGuard:
    def __init__(self, historical_alerts: List[Alert]):
        # The Protected Set: Any rule_key that ever participated in a confirmed incident
        self.protected_rule_keys: Set[str] = {
            a.rule_key for a in historical_alerts if a.incident_id is not None and a.rule_key
        }
        # Baseline seen keys
        self.seen_rule_keys: Set[str] = {
            a.rule_key for a in historical_alerts if a.rule_key
        }

    def is_protected(self, alert: Alert) -> bool:
        return bool(alert.rule_key in self.protected_rule_keys or alert.incident_id is not None)

    def is_novel(self, alert: Alert) -> bool:
        return bool(alert.rule_key and alert.rule_key not in self.seen_rule_keys)

    def protect_and_prioritize(
        self,
        incidents: List[Incident],
        unclustered_alerts: List[Alert]
    ) -> List[Incident]:
        """
        Guarantees that:
        1. Any incident containing a protected alert has has_real_signal=True and elevated priority.
        2. Any orphaned protected alert or novel alert that didn't join a cluster is NEVER dropped;
           it is preserved as a dedicated Singleton Incident Card.
        """
        output = list(incidents)

        for inc in output:
            for a in inc.alerts:
                if self.is_protected(a):
                    if a.alert_id not in inc.protected_alerts:
                        inc.protected_alerts.append(a.alert_id)
                    inc.has_real_signal = True

            # If it contains protected signals, ensure priority reflects it
            if inc.has_real_signal:
                inc.priority.score = max(inc.priority.score, 0.85)
                inc.priority.factors["protected_signal"] = 1.0

        # Singleton protection for unclustered protected or novel alerts
        for unclustered in unclustered_alerts:
            if self.is_protected(unclustered) or self.is_novel(unclustered):
                singleton_inc = Incident(
                    incident_id=f"INC-GUARD-{unclustered.alert_id}",
                    summary=f"Guarded Signal: {unclustered.name} on {unclustered.service} (Historically confirmed or novel)",
                    origin=OriginInfo(service=unclustered.service, confidence=0.85),
                    alerts=[unclustered],
                    services=[unclustered.service],
                    start_time=unclustered.timestamp,
                    end_time=unclustered.timestamp,
                    severity=unclustered.severity,
                    priority=PriorityBreakdown(
                        score=0.90,
                        factors={"protected_signal": 1.0, "singleton_guard": 1.0}
                    ),
                    edges=[],
                    protected_alerts=[unclustered.alert_id],
                    has_real_signal=True
                )
                output.append(singleton_inc)

        output.sort(key=lambda inc: inc.priority.score, reverse=True)
        return output
