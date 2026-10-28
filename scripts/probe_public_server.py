"""
Public Internet Server Probe & Health Monitor
=============================================
Allows you to monitor ANY public server or API on the internet without needing your own server!
Uses real public HTTP/HTTPS endpoints, detects slow response times, SSL errors, 502/503/504
server errors, and pushes live alerts to the correlation engine.

Includes built-in support for:
- Testing public servers: e.g. https://httpbin.org, https://api.github.com
- Simulating live outages using public test servers: https://httpstat.us (500, 502, 504, 429)
- Any custom public domain or IP you provide!

Usage:
  # Probe any public website/server on the internet:
  python scripts/probe_public_server.py --url https://api.github.com

  # Simulate a live multi-tier failure across public test servers on the internet:
  python scripts/probe_public_server.py --test-public-outage
"""

import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone


def send_alert_webhook(api_url: str, alert_payload: dict):
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
        print(f"[!] Engine webhook error: {e}")
        return {}


def probe_server(url: str, server_name: str, api_url: str, timeout_sec: float = 4.0):
    """Probes a real public server over the internet and fires alerts if slow or failing."""
    start_time = time.time()
    headers = {"User-Agent": "AIOps-Server-Probe/1.0"}
    req = urllib.request.Request(url, headers=headers)

    print(f"[*] Probing public server '{server_name}' ({url})...")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            elapsed = time.time() - start_time
            status_code = resp.getcode()
            print(f"    --> Response: HTTP {status_code} in {elapsed*1000:.0f}ms [OK]")

            if elapsed > 2.0:
                # Latency alert
                alert = {
                    "server": server_name,
                    "name": "PublicServerHighLatency",
                    "severity": "warning",
                    "source": "public-http-probe",
                    "message": f"High response latency: {elapsed*1000:.0f}ms (threshold 2000ms)",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                send_alert_webhook(api_url, alert)

    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        severity = "critical" if e.code >= 500 else "high"
        alert = {
            "server": server_name,
            "name": f"HTTPServerError{e.code}",
            "severity": severity,
            "source": "public-http-probe",
            "message": f"Server returned HTTP {e.code} ({e.reason}) after {elapsed*1000:.0f}ms",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        print(f"    --> [FAIL] HTTP {e.code}: {e.reason} -> Streaming alert to engine!")
        res = send_alert_webhook(api_url, alert)
        assigned = res.get("assigned_incident")
        if assigned:
            print(f"        [Correlated into Incident {assigned.get('incident_id')} | Origin: {assigned.get('origin_root_cause_server')}]")

    except Exception as e:
        elapsed = time.time() - start_time
        alert = {
            "server": server_name,
            "name": "ServerConnectionFailure",
            "severity": "critical",
            "source": "public-http-probe",
            "message": f"Connection failed to public server: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        print(f"    --> [FAIL] Connection error: {e} -> Streaming alert to engine!")
        send_alert_webhook(api_url, alert)


def run_public_outage_demo(api_url: str):
    """
    Probes real public endpoints on the internet (using httpstat.us and public test APIs)
    to demonstrate live failure detection on actual remote internet servers.
    """
    print("\n" + "="*70)
    print("PROBING ACTUAL PUBLIC SERVERS ON THE INTERNET")
    print("="*70 + "\n")

    test_targets = [
        ("public-auth-api", "https://httpstat.us/200?sleep=100"),
        ("public-billing-gateway", "https://httpstat.us/500"),
        ("public-database-proxy", "https://httpstat.us/503"),
        ("public-cdn-edge", "https://httpstat.us/504?sleep=1500"),
    ]

    for name, url in test_targets:
        probe_server(url, name, api_url)
        time.sleep(1.0)

    print("\n" + "="*70)
    print("PROBING COMPLETE: Check your dashboard at http://localhost:3000 to see live correlated incidents!")
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Public Server Health Probe")
    parser.add_argument("--url", default=None, help="Public URL or API endpoint to probe")
    parser.add_argument("--server-name", default=None, help="Name of the public server")
    parser.add_argument("--api-url", default="http://localhost:8000", help="AIOps engine URL")
    parser.add_argument("--test-public-outage", action="store_true", help="Probe real public failure endpoints on the internet")
    parser.add_argument("--interval", type=int, default=10, help="Continuous probe interval in seconds")

    args = parser.parse_args()

    if args.test_public_outage:
        run_public_outage_demo(args.api_url)
        return

    if args.url:
        s_name = args.server_name or args.url.split("//")[-1].split("/")[0]
        print(f"[*] Continuously probing public server '{s_name}' every {args.interval}s...")
        try:
            while True:
                probe_server(args.url, s_name, args.api_url)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[*] Probe stopped.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
