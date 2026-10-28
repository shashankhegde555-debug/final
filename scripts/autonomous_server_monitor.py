"""
Autonomous Server Monitoring Agent & Alert Streamer
===================================================
Runs continuously on a server (or server fleet) as an autonomous daemon.
Features:
1. Metric Watcher: Tracks CPU, RAM, Disk, and Connection Backlogs autonomously via psutil.
2. Log Tailer: Watches specified log files (/var/log/syslog, nginx error.log, app.log, etc.) for error spikes.
3. Autonomous Streamer: Directly pushes alerts via HTTP webhook to the AIOps correlation engine (http://localhost:8000/api/webhook/alert).
4. Cascading Outage Simulation (--simulate-cascade): Simulates a live multi-tier server outage in real time so you can observe the correlation engine autonomously grouping alerts and isolating the root-cause server.

Usage:
  # Run continuous autonomous server monitoring on the local machine:
  python scripts/autonomous_server_monitor.py --server-name srv-db-master --interval 5

  # Monitor a specific application log file:
  python scripts/autonomous_server_monitor.py --server-name app-backend --log-file /var/log/nginx/error.log

  # Run an autonomous live cascading outage simulation:
  python scripts/autonomous_server_monitor.py --simulate-cascade
"""

import sys
import os
import time
import socket
import argparse
import json
import urllib.request
from datetime import datetime, timezone

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def send_alert_webhook(api_url: str, alert_payload: dict) -> dict:
    """Sends an alert autonomously to the engine webhook."""
    webhook_url = f"{api_url.rstrip('/')}/api/webhook/alert"
    req_data = json.dumps(alert_payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[!] Webhook error: {e}")
        return {}


def monitor_system_metrics(server_name: str, api_url: str, cpu_thresh=85.0, mem_thresh=85.0, disk_thresh=90.0):
    """Continuously monitors real OS system metrics and pushes alerts autonomously."""
    if not HAS_PSUTIL:
        print("[!] psutil not installed. Running in basic heartbeat mode.")
        return

    cpu_pct = psutil.cpu_percent(interval=1.0)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/') if os.name != 'nt' else psutil.disk_usage('C:\\')

    alerts_to_send = []

    if cpu_pct >= cpu_thresh:
        alerts_to_send.append({
            "server": server_name,
            "name": "CPUSaturationHigh",
            "severity": "critical" if cpu_pct > 95 else "high",
            "source": "autonomous-agent",
            "message": f"Sustained CPU utilization at {cpu_pct:.1f}% exceeds threshold ({cpu_thresh}%)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    if mem.percent >= mem_thresh:
        alerts_to_send.append({
            "server": server_name,
            "name": "HostMemoryExhaustion",
            "severity": "critical" if mem.percent > 95 else "high",
            "source": "autonomous-agent",
            "message": f"RAM usage at {mem.percent:.1f}% ({mem.used // (1024**2)}MB used of {mem.total // (1024**2)}MB)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    if disk.percent >= disk_thresh:
        alerts_to_send.append({
            "server": server_name,
            "name": "DiskCapacityWarning",
            "severity": "warning",
            "source": "autonomous-agent",
            "message": f"Storage volume at {disk.percent:.1f}% capacity",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    for alert in alerts_to_send:
        print(f"[+] Autonomous alert triggered on {server_name}: {alert['name']} ({alert['severity']})")
        res = send_alert_webhook(api_url, alert)
        assigned = res.get("assigned_incident")
        if assigned:
            print(f"    --> Correlated into Incident: {assigned.get('incident_id')} | Root Cause Server: {assigned.get('origin_root_cause_server')}")


def tail_log_file(log_path: str, server_name: str, api_url: str):
    """Tails a log file and autonomously pushes alerts when errors are detected."""
    if not os.path.exists(log_path):
        print(f"[!] Log file does not exist: {log_path}")
        return

    print(f"[*] Autonomously tailing {log_path} on {server_name}...")
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        # Seek to end
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue

            line_lower = line.lower()
            if any(k in line_lower for k in ["error", "fatal", "panic", "exception", "timeout", "refused"]):
                alert = {
                    "server": server_name,
                    "name": "ApplicationLogErrorSurge",
                    "severity": "critical" if any(k in line_lower for k in ["fatal", "panic"]) else "high",
                    "source": "log-tailer",
                    "message": line.strip()[:250],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                print(f"[+] Error detected in log: {alert['message'][:80]}")
                send_alert_webhook(api_url, alert)


def run_cascading_outage_simulation(api_url: str, delay_sec: float = 2.0):
    """
    Simulates a live multi-tier cascading outage in real time.
    Watch how the correlation engine groups them autonomously into a single incident and isolates the origin.
    """
    print("\n" + "="*70)
    print("STARTING LIVE AUTONOMOUS SERVER OUTAGE SIMULATION")
    print("Scenario: Database Connection Pool Collapse Cascades Through Microservices")
    print("="*70 + "\n")

    cascade_steps = [
        {
            "server": "production-postgres-db",
            "name": "PostgresActiveConnectionsExhausted",
            "severity": "critical",
            "source": "postgres-exporter",
            "message": "FATAL: remaining connection slots are reserved for non-replication superuser connections (max_connections=200)"
        },
        {
            "server": "production-postgres-db",
            "name": "QueryExecutionQueueBacklog",
            "severity": "critical",
            "source": "prometheus",
            "message": "Pending client query queue length > 450 waiting on db connection"
        },
        {
            "server": "auth-api",
            "name": "DatabasePoolAcquisitionTimeout",
            "severity": "critical",
            "source": "datadog",
            "message": "Knex: Timeout acquiring a connection from pool after 30000ms"
        },
        {
            "server": "billing-api",
            "name": "TransactionRollbackSpike",
            "severity": "critical",
            "source": "datadog",
            "message": "Failed to persist customer invoice: Connection terminated unexpectedly"
        },
        {
            "server": "order-processor",
            "name": "HTTP500InternalErrorRate",
            "severity": "high",
            "source": "sentry",
            "message": "500 Internal Server Error returned to checkout client: SequelizeConnectionError"
        },
        {
            "server": "api-gateway",
            "name": "Nginx504GatewayTimeoutSurge",
            "severity": "critical",
            "source": "nginx-ingress",
            "message": "Upstream response timed out (110: Connection timed out) while reading response header from upstream"
        },
        {
            "server": "customer-status-page",
            "name": "PublicSyntheticCheckoutFlowFailed",
            "severity": "critical",
            "source": "uptime-robot",
            "message": "HTTP POST /v1/checkout failed with status 504 Gateway Timeout from edge probe"
        }
    ]

    for idx, step in enumerate(cascade_steps, 1):
        step["timestamp"] = datetime.now(timezone.utc).isoformat()
        print(f"\n[Step {idx}/{len(cascade_steps)}] Server '{step['server']}' fired alert: {step['name']}")
        res = send_alert_webhook(api_url, step)
        assigned = res.get("assigned_incident")
        if assigned:
            print(f"  [Autonomous Engine Decision]:")
            print(f"    - Assigned to Incident: {assigned.get('incident_id')}")
            print(f"    - Origin Root Cause Server: {assigned.get('origin_root_cause_server')} (Confidence: {round((assigned.get('confidence') or 0)*100)}%)")
            print(f"    - Total Alerts Collapsed: {assigned.get('total_alerts_collapsed')}")
            print(f"    - Affected Servers: {assigned.get('servers_affected')}")
            print(f"    - AI Diagnosis: {assigned.get('brief_description', '')[:100]}...")
        time.sleep(delay_sec)

    print("\n" + "="*70)
    print("SIMULATION COMPLETE: Check your dashboard at http://localhost:3000 to see the live graph and root cause!")
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Autonomous Server Monitoring Agent")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Correlation engine base URL")
    parser.add_argument("--server-name", default=socket.gethostname(), help="Identifier for this server/node")
    parser.add_argument("--interval", type=int, default=5, help="Metric collection interval in seconds")
    parser.add_argument("--log-file", default=None, help="Optional log file path to tail autonomously")
    parser.add_argument("--simulate-cascade", action="store_true", help="Run a live multi-tier cascading outage simulation")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between cascade alerts in simulation mode")

    args = parser.parse_args()

    if args.simulate_cascade:
        run_cascading_outage_simulation(args.api_url, delay_sec=args.delay)
        return

    if args.log_file:
        tail_log_file(args.log_file, args.server_name, args.api_url)
        return

    print(f"[*] Autonomous Server Monitor active for server '{args.server_name}'")
    print(f"[*] Streaming alerts to {args.api_url}/api/webhook/alert every {args.interval}s")
    print("[*] Press Ctrl+C to stop.")

    try:
        while True:
            monitor_system_metrics(args.server_name, args.api_url)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[*] Autonomous monitor stopped.")


if __name__ == "__main__":
    main()
