import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Set
from sklearn.metrics import adjusted_rand_score, v_measure_score
from backend.app.models import Alert, Incident, EvaluationReport, TimeToSurfaceStats

class EvaluationHarness:
    def __init__(self, ground_truth_incidents: List[Dict[str, Any]]):
        self.ground_truth = ground_truth_incidents
        # Map incident_id -> dict of ground truth info
        self.gt_map: Dict[str, Dict[str, Any]] = {
            inc["incident_id"]: inc for inc in ground_truth_incidents
        }

    def compute_pairwise_metrics(
        self,
        alerts: List[Alert],
        clusters: List[List[str]],
        sample_size: int = 5000
    ) -> Tuple[float, float, float]:
        """
        Computes pairwise precision, recall, and F1 over pairs of alerts.
        Alerts without ground truth incident_id are treated as unique noise singletons.
        For scalability on 16k+ alerts, uses random stratified pair sampling if total pairs > sample_size.
        """
        # Map alert_id -> ground truth cluster ID
        gt_cluster: Dict[str, str] = {}
        for a in alerts:
            if a.incident_id:
                gt_cluster[a.alert_id] = f"GT-{a.incident_id}"
            else:
                # Each noise alert is its own singleton class
                gt_cluster[a.alert_id] = f"NOISE-{a.alert_id}"

        # Map alert_id -> predicted cluster ID
        pred_cluster: Dict[str, str] = {}
        for c_idx, member_ids in enumerate(clusters):
            for m_id in member_ids:
                pred_cluster[m_id] = f"PRED-{c_idx}"

        # Get all alert IDs present
        alert_ids = [a.alert_id for a in alerts]
        n = len(alert_ids)
        if n < 2:
            return 1.0, 1.0, 1.0

        # Sample alert pairs to keep computation deterministic and fast
        np.random.seed(42)
        total_possible_pairs = n * (n - 1) // 2

        # Include all pairs that share a GT incident (the positive ground truth class)
        # to ensure recall is exact
        gt_groups: Dict[str, List[str]] = {}
        for a_id, g in gt_cluster.items():
            if not g.startswith("NOISE-"):
                gt_groups.setdefault(g, []).append(a_id)

        positive_pairs: Set[Tuple[str, str]] = set()
        for g, members in gt_groups.items():
            m_len = len(members)
            for i in range(m_len):
                for j in range(i + 1, m_len):
                    p = tuple(sorted((members[i], members[j])))
                    positive_pairs.add(p)

        # Sample negative pairs
        neg_sample_count = min(sample_size * 2, total_possible_pairs)
        sampled_pairs = set(positive_pairs)

        while len(sampled_pairs) < len(positive_pairs) + neg_sample_count:
            idx1 = np.random.randint(0, n)
            idx2 = np.random.randint(0, n)
            if idx1 != idx2:
                pair = tuple(sorted((alert_ids[idx1], alert_ids[idx2])))
                sampled_pairs.add(pair)

        tp = 0
        fp = 0
        fn = 0
        tn = 0

        for a1, a2 in sampled_pairs:
            gt_same = (gt_cluster.get(a1) == gt_cluster.get(a2))
            pred_same = (pred_cluster.get(a1) is not None and 
                         pred_cluster.get(a2) is not None and 
                         pred_cluster.get(a1) == pred_cluster.get(a2))

            if gt_same and pred_same:
                tp += 1
            elif not gt_same and pred_same:
                fp += 1
            elif gt_same and not pred_same:
                fn += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return round(precision, 4), round(recall, 4), round(f1, 4)

    def compute_clustering_metrics(
        self,
        alerts: List[Alert],
        clusters: List[List[str]]
    ) -> Tuple[float, float]:
        """Computes ARI and V-Measure on labeled incident alerts."""
        pred_map: Dict[str, int] = {}
        for c_idx, member_ids in enumerate(clusters):
            for m_id in member_ids:
                pred_map[m_id] = c_idx

        y_true = []
        y_pred = []

        for a in alerts:
            if a.incident_id:
                y_true.append(a.incident_id)
                y_pred.append(pred_map.get(a.alert_id, -1))

        if not y_true:
            return 1.0, 1.0

        ari = adjusted_rand_score(y_true, y_pred)
        v_measure = v_measure_score(y_true, y_pred)
        return round(float(ari), 4), round(float(v_measure), 4)

    def evaluate(
        self,
        method_name: str,
        alerts: List[Alert],
        predicted_incidents: List[Incident],
        purity_threshold: float = 0.5,
        late_threshold_sec: float = 300.0
    ) -> EvaluationReport:
        raw_count = len(alerts)
        card_count = len(predicted_incidents)
        notif_reduction = 1.0 - (card_count / raw_count) if raw_count > 0 else 0.0
        cards_per_true = card_count / len(self.gt_map) if len(self.gt_map) > 0 else 0.0
        alerts_per_card = raw_count / card_count if card_count > 0 else 0.0

        # Cluster memberships
        clusters = [[a.alert_id for a in inc.alerts] for inc in predicted_incidents]

        prec, rec, f1 = self.compute_pairwise_metrics(alerts, clusters)
        ari, vm = self.compute_clustering_metrics(alerts, clusters)

        # Incident Recall & Time-to-Surface
        # For each GT incident, find cards containing its alerts
        detected_incidents: Set[str] = set()
        tts_list: List[float] = []
        top1_correct = 0
        top3_correct = 0

        # Map each GT incident to earliest alert timestamp epoch
        gt_first_alert_time: Dict[str, float] = {}
        for a in alerts:
            if a.incident_id:
                if a.incident_id not in gt_first_alert_time:
                    gt_first_alert_time[a.incident_id] = a.timestamp_epoch
                else:
                    gt_first_alert_time[a.incident_id] = min(
                        gt_first_alert_time[a.incident_id], a.timestamp_epoch
                    )

        explainability_complete = 0

        for inc in predicted_incidents:
            # Check explainability
            if inc.origin and inc.origin.service and (len(inc.edges) > 0 or len(inc.alerts) == 1):
                explainability_complete += 1

            # Count ground truth representations in this card
            gt_counts: Dict[str, int] = {}
            for a in inc.alerts:
                if a.incident_id:
                    gt_counts[a.incident_id] = gt_counts.get(a.incident_id, 0) + 1

            total_alerts_in_card = len(inc.alerts)
            for gt_id, count in gt_counts.items():
                purity = count / total_alerts_in_card if total_alerts_in_card > 0 else 0.0
                if purity >= purity_threshold or count >= 2:
                    detected_incidents.add(gt_id)
                    # Time to surface = card start time - first alert time of that incident
                    card_epoch = inc.alerts[0].timestamp_epoch if inc.alerts else 0.0
                    gt_start = gt_first_alert_time.get(gt_id, card_epoch)
                    delay = max(0.0, card_epoch - gt_start)
                    tts_list.append(delay)

                    # Check origin accuracy
                    gt_root = self.gt_map[gt_id].get("root_cause_service")
                    if gt_root:
                        if inc.origin.service == gt_root:
                            top1_correct += 1
                        ranked_svcs = [r.service for r in inc.origin.ranking[:3]]
                        if gt_root in ranked_svcs or inc.origin.service == gt_root:
                            top3_correct += 1

        total_gt = len(self.gt_map)
        incident_recall = len(detected_incidents) / total_gt if total_gt > 0 else 1.0
        missed = [gt_id for gt_id in self.gt_map if gt_id not in detected_incidents]

        if not tts_list:
            tts_stats = TimeToSurfaceStats(median_sec=0.0, p90_sec=0.0, max_sec=0.0, late_count=0)
        else:
            tts_stats = TimeToSurfaceStats(
                median_sec=round(float(np.median(tts_list)), 1),
                p90_sec=round(float(np.percentile(tts_list, 90)), 1),
                max_sec=round(float(np.max(tts_list)), 1),
                late_count=int(sum(1 for t in tts_list if t > late_threshold_sec))
            )

        origin_top1 = (top1_correct / len(detected_incidents)) if detected_incidents else 0.0
        origin_top3 = (top3_correct / len(detected_incidents)) if detected_incidents else 0.0
        explain_cov = (explainability_complete / card_count) if card_count > 0 else 1.0

        return EvaluationReport(
            method=method_name,
            raw_alerts=raw_count,
            incident_cards=card_count,
            notification_reduction=round(notif_reduction * 100, 2),
            cards_per_true_incident=round(cards_per_true, 2),
            alerts_per_card=round(alerts_per_card, 2),
            incident_recall=round(incident_recall * 100, 2),
            missed_incidents=missed,
            pairwise_precision=prec,
            pairwise_recall=rec,
            pairwise_f1=f1,
            adjusted_rand_index=ari,
            v_measure=vm,
            origin_accuracy_top1=round(origin_top1 * 100, 2),
            origin_accuracy_top3=round(origin_top3 * 100, 2),
            explainability_coverage=round(explain_cov * 100, 2),
            time_to_surface=tts_stats
        )
