#!/usr/bin/env python3
"""
CLI Evaluation and parameter sweep harness for AO-01.
Computes before/after metrics against ground-truth incidents:
- Raw baseline
- Service 10-minute window baseline
- Keep Topology Processor baseline (application membership)
- Our correlation engine (once implemented in Phase 4)
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from typing import List, Dict, Any
from backend.app.ingest.schema_detect import loader
from backend.app.eval.metrics import EvaluationHarness
from backend.app.eval.baselines import (
    run_raw_baseline,
    run_service_window_baseline,
    run_keep_topology_processor_baseline
)

def print_report_table(reports):
    header = f"{'Method':<28} | {'Reduction':<10} | {'Cards':<8} | {'Inc Recall':<10} | {'Pairwise F1':<11} | {'ARI':<7} | {'Origin T1':<9} | {'TTS Med':<8}"
    sep = "-" * len(header)
    print("\n" + sep)
    print(header)
    print(sep)
    for r in reports:
        print(f"{r.method:<28} | {r.notification_reduction:>8.1f}% | {r.incident_cards:>8} | {r.incident_recall:>8.1f}% | {r.pairwise_f1:>11.4f} | {r.adjusted_rand_index:>7.4f} | {r.origin_accuracy_top1:>7.1f}% | {r.time_to_surface.median_sec:>7.1f}s")
    print(sep + "\n")

def main():
    parser = argparse.ArgumentParser(description="AO-01 Evaluation Harness")
    parser.add_argument("--data-dir", default="data/synthetic", help="Path to data directory")
    parser.add_argument("--sample", type=int, default=1500, help="Number of alerts to evaluate for fast run")
    parser.add_argument("--all", action="store_true", help="Run across all alerts in dataset")
    parser.add_argument("--sweep", action="store_true", help="Run parameter grid sweep")
    args = parser.parse_args()

    print("Loading topology, alerts, and ground-truth incidents...")
    loader.data_dir = args.data_dir
    loader.load_topology()
    all_alerts = loader.load_alerts()
    gt_incidents = loader.load_incidents()

    if args.all:
        eval_alerts = all_alerts
    else:
        # Take a slice including at least 3 incidents for fast benchmark
        eval_alerts = all_alerts[:args.sample]

    print(f"Loaded {len(eval_alerts)} alerts ({len(all_alerts)} total in dataset) and {len(gt_incidents)} incidents.")
    harness = EvaluationHarness(gt_incidents)

    # 1. Baseline 1: Raw alerts
    print("Evaluating Baseline 1: Raw alerts...")
    raw_cards = run_raw_baseline(eval_alerts)
    report_raw = harness.evaluate("1. Raw (No Correlation)", eval_alerts, raw_cards)

    # 2. Baseline 2: Service 10-min window
    print("Evaluating Baseline 2: Service 10-min window...")
    svc_win_cards = run_service_window_baseline(eval_alerts, window_sec=600.0)
    report_svc = harness.evaluate("2. Service-Window (10m)", eval_alerts, svc_win_cards)

    # 3. Baseline 3: Keep Topology Processor (Application-membership 15m)
    print("Evaluating Baseline 3: Keep Topology Processor (App 15m)...")
    service_to_app = {s: node.application for s, node in loader.services_dict.items()}
    keep_cards = run_keep_topology_processor_baseline(eval_alerts, service_to_app, lookback_window_sec=900.0)
    report_keep = harness.evaluate("3. Keep Topology (App 15m)", eval_alerts, keep_cards)

    reports = [report_raw, report_svc, report_keep]

    # 4. Check if our correlation engine is implemented (Phase 4)
    try:
        from backend.app.correlate.engine import CorrelatorEngine
        print("Evaluating Method 4: AO-01 Graph-Aware Origin Engine...")
        engine = CorrelatorEngine(loader.graph, service_to_app)
        our_cards = engine.correlate_stream(eval_alerts)
        report_our = harness.evaluate("4. AO-01 Origin Engine (Ours)", eval_alerts, our_cards)
        reports.append(report_our)
    except ImportError:
        pass

    print_report_table(reports)

if __name__ == "__main__":
    main()
