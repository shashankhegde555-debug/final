import pytest
from backend.app.ingest.schema_detect import loader
from backend.app.correlate.engine import CorrelatorEngine
from backend.app.guard.recall_guard import RecallGuard
from backend.app.eval.metrics import EvaluationHarness

def test_all_incidents_surfaced():
    """
    CRITICAL ACCEPTANCE TEST:
    Asserts that 100% of historical ground-truth incidents are surfaced by the correlation engine.
    Ensures that zero real production incidents are missed.
    """
    loader.data_dir = "data/synthetic"
    loader.load_topology()
    all_alerts = loader.load_alerts()
    gt_incidents = loader.load_incidents()

    assert len(gt_incidents) > 0, "No ground truth incidents found!"
    service_to_app = {s: node.application for s, node in loader.services_dict.items()}

    # Run correlation engine across the dataset
    engine = CorrelatorEngine(loader.graph, service_to_app)
    predicted_incidents = engine.correlate_stream(all_alerts)

    # Apply recall guard
    guard = RecallGuard(all_alerts)
    guarded_incidents = guard.protect_and_prioritize(predicted_incidents, [])

    # Evaluate
    harness = EvaluationHarness(gt_incidents)
    report = harness.evaluate("AO-01 Origin Engine", all_alerts, guarded_incidents)

    print("\n--- Phase 7 Recall Guard Backtest Results ---")
    print(f"Incident Recall: {report.incident_recall}%")
    print(f"Missed Incidents: {report.missed_incidents}")
    print(f"Time to Surface (median): {report.time_to_surface.median_sec}s")
    print(f"Time to Surface (p90): {report.time_to_surface.p90_sec}s")
    print(f"Pairwise F1: {report.pairwise_f1}")
    print(f"Notification Reduction: {report.notification_reduction}%")

    # Hard acceptance assertions
    assert report.incident_recall == 100.0, f"FAILED TO SURFACE ALL INCIDENTS! Missed: {report.missed_incidents}"
    assert len(report.missed_incidents) == 0
    assert report.notification_reduction > 50.0, "Notification reduction must exceed 50%"
