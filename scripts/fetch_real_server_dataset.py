"""
Real-World Production Server Dataset Downloader & Ingestor
==========================================================
Fetches authentic, published production server incident and error datasets from Loghub
(anonymized real production logs from real supercomputers, cloud clusters, Hadoop, and Zookeeper).

Downloads and ingests within 10-20 seconds!

Available Datasets:
- zookeeper  : Distributed consensus cluster failure logs (2,000 logs, 1,331 warnings/errors)
- hadoop     : Distributed computing cluster job failures (2,000 logs, 960 warnings/errors)
- openstack  : Multi-node cloud infrastructure server logs (nova, neutron, glance, keystone)
- hdfs       : Hadoop Distributed File System server logs (block failures, replication lag)
- bgl        : IBM Blue Gene/L supercomputer cluster failure logs

Usage:
  # Download and immediately ingest real Zookeeper cluster server data:
  python scripts/fetch_real_server_dataset.py --dataset zookeeper

  # Download and immediately ingest real OpenStack cloud server logs:
  python scripts/fetch_real_server_dataset.py --dataset openstack

  # Save to CSV without auto-uploading:
  python scripts/fetch_real_server_dataset.py --dataset hadoop --no-upload
"""

import os
import sys
import csv
import io
import json
import argparse
import urllib.request
from datetime import datetime, timezone

LOGHUB_URLS = {
    "zookeeper": "https://raw.githubusercontent.com/logpai/loghub/master/Zookeeper/Zookeeper_2k.log_structured.csv",
    "hadoop": "https://raw.githubusercontent.com/logpai/loghub/master/Hadoop/Hadoop_2k.log_structured.csv",
    "openstack": "https://raw.githubusercontent.com/logpai/loghub/master/OpenStack/OpenStack_2k.log_structured.csv",
    "hdfs": "https://raw.githubusercontent.com/logpai/loghub/master/HDFS/HDFS_2k.log_structured.csv",
    "bgl": "https://raw.githubusercontent.com/logpai/loghub/master/BGL/BGL_2k.log_structured.csv",
}


def download_and_parse(dataset_name: str):
    url = LOGHUB_URLS.get(dataset_name.lower())
    if not url:
        raise ValueError(f"Unknown dataset: {dataset_name}. Choose from: {list(LOGHUB_URLS.keys())}")

    print(f"[*] Downloading real-world production server dataset '{dataset_name}' from Loghub...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw_content = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw_content))
    rows = list(reader)
    print(f"[+] Downloaded {len(rows)} real server log records.")

    normalized_alerts = []
    base_year = 2026

    for idx, row in enumerate(rows):
        # Extract timestamp
        date_str = row.get("Date", "2026-10-28")
        time_str = row.get("Time", "12:00:00").replace(",", ".")
        try:
            # Handle MM-DD or YYYY-MM-DD
            parts = date_str.split("-")
            if len(parts) == 2:
                # e.g. 05-16 -> 2026-05-16
                iso_ts = f"2026-{parts[0]}-{parts[1]}T{time_str[:8]}Z"
            elif len(parts) == 3:
                iso_ts = f"2026-{parts[1]}-{parts[2]}T{time_str[:8]}Z"
            else:
                iso_ts = datetime.now(timezone.utc).isoformat()
        except Exception:
            iso_ts = datetime.now(timezone.utc).isoformat()

        # Extract severity
        raw_level = (row.get("Level") or row.get("Label") or "INFO").upper()
        if any(k in raw_level for k in ["FATAL", "CRITICAL", "PANIC", "EMERG"]):
            sev = "critical"
        elif any(k in raw_level for k in ["ERROR", "ERR", "FAIL"]):
            sev = "high"
        elif any(k in raw_level for k in ["WARN", "WARNING"]):
            sev = "warning"
        else:
            sev = "info"

        # Extract server / component name
        server = (
            row.get("Component")
            or row.get("Node")
            or row.get("Process")
            or row.get("ADDR")
            or f"{dataset_name}-node-{(idx % 5) + 1}"
        )
        # Clean up server name for readability
        raw_comp = row.get("Component") or row.get("Node") or row.get("Process") or row.get("ADDR") or f"{dataset_name}-node-{(idx % 5) + 1}"
        server = raw_comp.split(":")[-1].split("/")[-1].replace("org.apache.", "").replace("hadoop.", "").replace("$", "_").strip()
        if not server or server.isdigit():
            server = "ZooKeeperServer" if "zookeeper" in dataset_name else f"{dataset_name.capitalize()}Core"
        if len(server) > 30:
            server = server[:30]

        # Extract message and rule name
        msg = row.get("Content") or "Server event"
        name = row.get("EventId") or row.get("EventTemplate") or f"{dataset_name.capitalize()}Alert"
        if len(name) > 40:
            name = name[:40]

        alert = {
            "alert_id": f"REAL-{dataset_name.upper()}-{idx+1:05d}",
            "timestamp": iso_ts,
            "server": server,
            "service": server,
            "alertname": name,
            "name": name,
            "severity": sev,
            "message": msg[:250],
            "source": f"production-{dataset_name}-cluster"
        }
        normalized_alerts.append(alert)

    # Collect diverse failures across distinct server components so incidents represent different failure modes
    from collections import defaultdict
    comp_map = defaultdict(list)
    for a in normalized_alerts:
        comp_map[a["server"]].append(a)

    # Rank components by frequency of warnings and errors
    ranked_comps = sorted(
        comp_map.keys(),
        key=lambda c: (
            len([x for x in comp_map[c] if x["severity"] in ["critical", "high", "warning"]]),
            len(comp_map[c])
        ),
        reverse=True
    )

    selected_alerts = []
    base_epoch = 1793190000.0

    # Extract distinct 15-alert failure episodes per component with 30-minute gaps between episodes
    for comp in ranked_comps:
        comp_alerts = [x for x in comp_map[comp] if x["severity"] in ["critical", "high", "warning"]]
        if len(comp_alerts) < 8:
            comp_alerts = comp_map[comp]

        for start_idx in range(0, min(len(comp_alerts), 45), 15):
            batch = comp_alerts[start_idx : start_idx + 15]
            if len(batch) >= 10:
                for b_idx, a_item in enumerate(batch):
                    a_copy = dict(a_item)
                    ep = base_epoch + b_idx * 6.0
                    a_copy["timestamp_epoch"] = ep
                    a_copy["timestamp"] = datetime.fromtimestamp(ep, tz=timezone.utc).isoformat()
                    selected_alerts.append(a_copy)
                base_epoch += 1800.0  # 30-minute gap to distinct incident
            if len(selected_alerts) >= 420:
                break
        if len(selected_alerts) >= 420:
            break

    # If any room left, fill with remaining diverse alerts
    if len(selected_alerts) < 380:
        for a_item in normalized_alerts:
            if a_item["alert_id"] not in {x["alert_id"] for x in selected_alerts}:
                selected_alerts.append(a_item)
            if len(selected_alerts) >= 405:
                break

    print(f"[+] Extracted {len(selected_alerts)} diverse real server failure alerts across {len(set(a['server'] for a in selected_alerts))} production nodes.")
    return selected_alerts


def save_to_csv(alerts: list, out_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["alert_id", "timestamp", "server", "alertname", "severity", "message", "source"])
        writer.writeheader()
        writer.writerows(alerts)
    print(f"[+] Saved structured CSV to: {out_path}")


def upload_to_engine(csv_path: str, api_url: str):
    upload_url = f"{api_url.rstrip('/')}/api/ingest/upload"
    print(f"[*] Uploading to correlation engine at {upload_url}...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(csv_path)}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        upload_url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode())
        print(f"\n[SUCCESS] Engine Correlated Real Dataset!")
        print(f"  - Alerts Loaded: {res.get('alerts_loaded')}")
        print(f"  - Incidents Formed: {res.get('incidents_created')}")
        print(f"  - Servers/Components Discovered: {res.get('services_discovered')}")
        print(f"  - Topology Graph Nodes: {res.get('graph_nodes')}")
        print(f"  - Topology Graph Edges: {res.get('graph_edges')}")
        print(f"\nCheck your live dashboard at http://localhost:3000 to see the real clusters and root causes!")


def main():
    parser = argparse.ArgumentParser(description="Fetch and ingest real-world server datasets")
    parser.add_argument("--dataset", default="zookeeper", choices=list(LOGHUB_URLS.keys()), help="Dataset name")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Engine API URL")
    parser.add_argument("--no-upload", action="store_true", help="Do not upload to engine")
    args = parser.parse_args()

    alerts = download_and_parse(args.dataset)
    csv_path = os.path.join("data", f"real_{args.dataset}_production_alerts.csv")
    save_to_csv(alerts, csv_path)

    if not args.no_upload:
        upload_to_engine(csv_path, args.api_url)


if __name__ == "__main__":
    main()
