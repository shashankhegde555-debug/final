#!/usr/bin/env python3
"""
Replay script to push historical alerts and correlated incidents into Keep.
Reference: Section 10 (Keep Integration)
Supports:
1. Dry-run mode (default, completely safe local audit).
2. Live mode: Pushes alerts to Keep ingestion (/alerts/event) and correlated incidents to (/incidents).
3. Restricts live mode to localhost unless --allow-remote is explicitly passed.
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.ingest.schema_detect import loader
from backend.app.correlate.engine import CorrelatorEngine
from backend.app.integrations.keep_client import KeepClient, KeepSink

def main():
    parser = argparse.ArgumentParser(description="Replay alerts & correlated incidents into Keep")
    parser.add_argument("--keep-url", default="http://localhost:8080", help="Keep API endpoint")
    parser.add_argument("--api-key", default=None, help="Keep API key (X-API-KEY)")
    parser.add_argument("--live", action="store_true", help="Execute live requests against Keep (disables dry-run)")
    parser.add_argument("--limit", type=int, default=50, help="Number of alerts to replay")
    parser.add_argument("--allow-remote", action="store_true", help="Allow non-localhost Keep URL")
    args = parser.parse_args()

    dry_run = not args.live

    print(f"=== Keep Replay Synchronizer ===")
    print(f"Target Keep URL: {args.keep_url}")
    print(f"Mode: {'LIVE EXECUTION' if not dry_run else 'DRY RUN (Simulated)'}")

    client = KeepClient(
        base_url=args.keep_url,
        api_key=args.api_key,
        dry_run=dry_run
    )

    # Test connection
    status = client.test_connection()
    print(f"Keep connection test: {status}")

    print("\nLoading dataset and correlating incidents...")
    loader.load_topology()
    alerts = loader.load_alerts()[:args.limit]
    service_to_app = {s: node.application for s, node in loader.services_dict.items()}

    engine = CorrelatorEngine(loader.graph, service_to_app)
    incidents = engine.correlate_stream(alerts)
    print(f"Prepared {len(alerts)} alerts -> {len(incidents)} correlated incidents.")

    print(f"\n1. Pushing {len(alerts)} alerts to Keep /alerts/event...")
    for idx, alert in enumerate(alerts):
        res = client.push_alert_event(alert)
        if idx < 3 or idx == len(alerts) - 1:
            print(f"   Alert [{alert.alert_id}] {alert.name} -> {res.get('status')}")

    print(f"\n2. Pushing {len(incidents)} correlated incidents to Keep /incidents...")
    sink = KeepSink(client)
    sync_res = sink.sync_incidents(incidents)
    print(f"Synced {sync_res['synced_count']} incidents to Keep.")
    print("Done!")

if __name__ == "__main__":
    main()
