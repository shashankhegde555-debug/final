import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.models import Alert, RuleNoiseStats

class NoiseAnalyzer:
    def __init__(self, suppress_min_fires: int = 30):
        self.suppress_min_fires = suppress_min_fires
        self._decisions: Dict[str, Dict[str, Any]] = {}

    def compute_wilson_score(self, successes: int, total: int, confidence: float = 0.95) -> float:
        """Computes Wilson lower bound interval for alert link rate."""
        if total == 0:
            return 0.0
        z = 1.96  # 95% confidence
        p = successes / total
        denominator = 1 + z**2 / total
        centre_adjusted_probability = p + z**2 / (2 * total)
        adjusted_standard_deviation = math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)
        lower_bound = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
        return max(0.0, lower_bound)

    def analyze_rules(self, alerts: List[Alert]) -> List[RuleNoiseStats]:
        rule_counts: Dict[str, int] = {}
        rule_linked: Dict[str, int] = {}
        rule_examples: Dict[str, List[str]] = {}
        rule_meta: Dict[str, Dict[str, str]] = {}

        for a in alerts:
            rk = a.rule_key or f"{a.source}:{a.service}:{a.name}"
            rule_counts[rk] = rule_counts.get(rk, 0) + 1
            if a.incident_id:
                rule_linked[rk] = rule_linked.get(rk, 0) + 1

            if rk not in rule_examples:
                rule_examples[rk] = []
            if len(rule_examples[rk]) < 3:
                rule_examples[rk].append(a.timestamp)

            if rk not in rule_meta:
                rule_meta[rk] = {
                    "source": a.source,
                    "service": a.service,
                    "normalized_name": a.name
                }

        results: List[RuleNoiseStats] = []

        for rk, n_fires in rule_counts.items():
            n_link = rule_linked.get(rk, 0)
            meta = rule_meta[rk]
            link_rate = round(n_link / n_fires, 4)
            wilson = round(self.compute_wilson_score(n_link, n_fires), 4)

            # Recommendation logic:
            if n_link == 0 and n_fires >= self.suppress_min_fires:
                rec = "Suppress candidate"
                risk = "Low Risk: Rule has fired >= 30 times across historical records with zero incident correlation."
                evidence = f"Fired {n_fires} times in history without ever preceding or participating in a confirmed incident."
            elif n_link == 0 and n_fires < self.suppress_min_fires:
                rec = "Keep - insufficient evidence"
                risk = "Caution: Low volume of firings. Suppressing rare alerts carries high risk of missing unusual outages."
                evidence = f"Fired only {n_fires} times (threshold for suppression is {self.suppress_min_fires})."
            elif n_link > 0 and link_rate < 0.20:
                rec = "Raise threshold / add duration"
                risk = f"Moderate Risk: Associated with {n_link} incident alert(s), but has high noise ratio ({n_fires - n_link} false alarms)."
                evidence = f"{n_link}/{n_fires} fires linked to incidents ({link_rate*100:.1f}% link rate). Recommend 5-minute sustained duration check."
            elif link_rate >= 0.20:
                rec = "Keep and page"
                risk = "High Risk: High correlation with real production incidents. Must never be silenced."
                evidence = f"High-fidelity signal: {n_link}/{n_fires} firings ({link_rate*100:.1f}%) directly linked to historical outages."
            else:
                rec = "Surface by default (novel)"
                risk = "High Risk: Unknown or novel signature."
                evidence = "Never observed in baseline history."

            # Check if user made a recorded decision
            dec_info = self._decisions.get(rk, {})
            decision = dec_info.get("decision")
            dec_time = dec_info.get("timestamp")

            results.append(RuleNoiseStats(
                rule_key=rk,
                source=meta["source"],
                service=meta["service"],
                normalized_name=meta["normalized_name"],
                n_fires=n_fires,
                n_linked=n_link,
                link_rate=link_rate,
                recommendation=rec,
                evidence=evidence,
                risk_note=risk,
                decision=decision,
                decision_timestamp=dec_time
            ))

        # Sort by fires descending
        results.sort(key=lambda r: (r.recommendation == "Suppress candidate", r.n_fires), reverse=True)
        return results

    def record_decision(self, rule_key: str, decision: str) -> Dict[str, Any]:
        """
        Records human decision (approve/reject).
        SAFETY MANDATE: Strictly audit-recorded locally; NEVER executed or forwarded to monitoring systems.
        """
        assert decision in ["approved", "rejected", None]
        now_str = datetime.now(timezone.utc).isoformat()
        self._decisions[rule_key] = {
            "decision": decision,
            "timestamp": now_str
        }
        return {
            "rule_key": rule_key,
            "decision": decision,
            "timestamp": now_str,
            "execution_note": "AUDIT RECORDED ONLY. No external monitoring tools or live alert rules were altered."
        }

    def compute_what_if_impact(self, alerts: List[Alert]) -> Dict[str, Any]:
        """Computes reduction in alerts if all approved suppressions were applied."""
        stats = self.analyze_rules(alerts)
        approved_keys = {
            s.rule_key for s in stats if s.decision == "approved" or (s.decision is None and s.recommendation == "Suppress candidate")
        }

        raw_total = len(alerts)
        suppressed_count = sum(1 for a in alerts if a.rule_key in approved_keys)
        remaining_alerts = raw_total - suppressed_count

        # Verify safety guard: ensure NO incident alerts are in the approved suppression set
        incident_alerts_suppressed = sum(1 for a in alerts if a.rule_key in approved_keys and a.incident_id is not None)

        return {
            "total_raw_alerts": raw_total,
            "alerts_suppressed": suppressed_count,
            "alerts_remaining": remaining_alerts,
            "reduction_percentage": round((suppressed_count / raw_total) * 100, 2) if raw_total > 0 else 0.0,
            "incident_alerts_suppressed": incident_alerts_suppressed,
            "safety_passed": (incident_alerts_suppressed == 0)
        }

noise_analyzer = NoiseAnalyzer()
