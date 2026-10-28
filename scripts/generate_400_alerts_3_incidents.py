"""
Generates the canonical Problem Statement benchmark:
"Four Hundred Alerts, Three Real Incidents"
400 raw server alerts collapsing into 3 distinct real incidents:
1. Incident #1 (195 alerts): Database Connection Pool Exhaustion on production-postgres-db
2. Incident #2 (138 alerts): API Gateway Network Ingress Storm on api-gateway
3. Incident #3 (67 alerts): Payment Worker Memory Leak & OOM Kill on payment-worker-01
Total = 400 alerts -> 3 real incidents (-99.25% noise reduction)
"""

import os
import json
from datetime import datetime, timezone, timedelta

def generate_dataset():
    topology = {
        "services": [
            # Incident 1 Services (Database cascade)
            {"name": "production-postgres-db", "tier": "datastore", "application": "ecommerce", "dependencies": []},
            {"name": "auth-api", "tier": "service", "application": "ecommerce", "dependencies": ["production-postgres-db"]},
            {"name": "billing-api", "tier": "service", "application": "ecommerce", "dependencies": ["production-postgres-db"]},
            {"name": "order-processor", "tier": "service", "application": "ecommerce", "dependencies": ["production-postgres-db", "billing-api"]},
            {"name": "user-service", "tier": "service", "application": "ecommerce", "dependencies": ["production-postgres-db", "auth-api"]},
            {"name": "search-indexer", "tier": "service", "application": "ecommerce", "dependencies": ["production-postgres-db"]},

            # Incident 2 Services (Gateway cascade)
            {"name": "api-gateway", "tier": "gateway", "application": "edge", "dependencies": []},
            {"name": "edge-router", "tier": "edge", "application": "edge", "dependencies": ["api-gateway"]},
            {"name": "checkout-web", "tier": "web", "application": "frontend", "dependencies": ["api-gateway", "edge-router"]},
            {"name": "customer-status-page", "tier": "web", "application": "frontend", "dependencies": ["api-gateway"]},
            {"name": "public-ingress", "tier": "edge", "application": "edge", "dependencies": ["api-gateway"]},

            # Incident 3 Services (Worker cascade)
            {"name": "payment-worker-01", "tier": "worker", "application": "payments", "dependencies": []},
            {"name": "celery-broker", "tier": "service", "application": "payments", "dependencies": ["payment-worker-01"]},
            {"name": "invoice-generator", "tier": "worker", "application": "payments", "dependencies": ["payment-worker-01", "celery-broker"]},
            {"name": "notification-dispatch", "tier": "service", "application": "payments", "dependencies": ["payment-worker-01"]}
        ],
        "dependencies": [
            # Inc 1 edges (directed: upstream depends on downstream failure origin)
            {"source": "auth-api", "target": "production-postgres-db"},
            {"source": "billing-api", "target": "production-postgres-db"},
            {"source": "order-processor", "target": "production-postgres-db"},
            {"source": "user-service", "target": "production-postgres-db"},
            {"source": "search-indexer", "target": "production-postgres-db"},
            {"source": "order-processor", "target": "billing-api"},
            {"source": "user-service", "target": "auth-api"},

            # Inc 2 edges
            {"source": "edge-router", "target": "api-gateway"},
            {"source": "checkout-web", "target": "api-gateway"},
            {"source": "customer-status-page", "target": "api-gateway"},
            {"source": "public-ingress", "target": "api-gateway"},
            {"source": "checkout-web", "target": "edge-router"},

            # Inc 3 edges
            {"source": "celery-broker", "target": "payment-worker-01"},
            {"source": "invoice-generator", "target": "payment-worker-01"},
            {"source": "notification-dispatch", "target": "payment-worker-01"},
            {"source": "invoice-generator", "target": "celery-broker"}
        ]
    }

    alerts = []
    alert_counter = 1

    # =========================================================================
    # INCIDENT 1: Database Connection Pool Exhaustion (195 alerts)
    # Starts at 2026-10-28T14:00:00Z, root cause on production-postgres-db
    # =========================================================================
    inc1_start = datetime(2026, 10, 28, 14, 0, 0, tzinfo=timezone.utc)
    inc1_specs = [
        ("production-postgres-db", "PostgresActiveConnectionsExhausted", "critical", 40, "FATAL: remaining connection slots reserved for non-replication superusers (max_connections=200)"),
        ("auth-api", "DatabasePoolAcquisitionTimeout", "critical", 35, "Knex: Timeout acquiring a connection from pool after 30000ms"),
        ("billing-api", "TransactionRollbackSpike", "critical", 40, "Failed to persist customer invoice: Connection terminated unexpectedly"),
        ("order-processor", "HTTP500SequelizeConnectionError", "high", 40, "SequelizeConnectionError: connection pool is drained and client timed out"),
        ("user-service", "UserProfileQueryTimeout", "high", 25, "Read query failed waiting for database replica lease"),
        ("search-indexer", "DatabaseSyncQueueBacklog", "warning", 15, "CDC search pipeline sync queue backlog exceeded 5,000 pending mutations")
    ]

    for svc, name, sev, count, msg in inc1_specs:
        lead_offset = 0 if svc == "production-postgres-db" else 30
        for i in range(count):
            t_sec = lead_offset + (i * (800 // count))
            dt = inc1_start + timedelta(seconds=t_sec)
            ts_str = dt.isoformat()
            alerts.append({
                "alert_id": f"ALT-400-{alert_counter:04d}",
                "timestamp": ts_str,
                "timestamp_epoch": dt.timestamp(),
                "source": "postgres-exporter" if "postgres" in svc else "prometheus",
                "service": svc,
                "severity": sev,
                "name": name,
                "message": msg,
                "host": f"{svc}-node-{(i%3)+1}",
                "customer_ref": f"cust-{(i%5)+1:03d}",
                "incident_id": "INC-REAL-01",
                "rule_key": f"db-cascade:{svc}:{name.lower()}",
                "first_seen": ts_str,
                "last_seen": ts_str
            })
            alert_counter += 1

    # =========================================================================
    # INCIDENT 2: API Gateway Ingress Storm (138 alerts)
    # Starts at 2026-10-28T16:00:00Z, root cause on api-gateway
    # =========================================================================
    inc2_start = datetime(2026, 10, 28, 16, 0, 0, tzinfo=timezone.utc)
    inc2_specs = [
        ("api-gateway", "Nginx504GatewayTimeoutSurge", "critical", 45, "Upstream response timed out (110: Connection timed out) while reading response header"),
        ("edge-router", "IngressBufferExhaustion", "critical", 30, "Socket buffer overflow: incoming TCP connection queue capacity reached"),
        ("checkout-web", "ClientCheckout504ErrorRate", "high", 35, "Public user checkout requests failing with 504 Gateway Timeout"),
        ("customer-status-page", "PublicSyntheticProbeFailed", "high", 18, "Synthetic health probe /api/v1/healthcheck failed from external edge"),
        ("public-ingress", "TLSSessionQueueOverflow", "warning", 10, "SSL handshake buffer saturated; client connection throttled")
    ]

    for svc, name, sev, count, msg in inc2_specs:
        lead_offset = 0 if svc == "api-gateway" else 25
        for i in range(count):
            t_sec = lead_offset + (i * (800 // count))
            dt = inc2_start + timedelta(seconds=t_sec)
            ts_str = dt.isoformat()
            alerts.append({
                "alert_id": f"ALT-400-{alert_counter:04d}",
                "timestamp": ts_str,
                "timestamp_epoch": dt.timestamp(),
                "source": "nginx-ingress" if "gateway" in svc or "ingress" in svc else "datadog",
                "service": svc,
                "severity": sev,
                "name": name,
                "message": msg,
                "host": f"{svc}-pod-{(i%3)+1}",
                "customer_ref": f"cust-{(i%4)+10:03d}",
                "incident_id": "INC-REAL-02",
                "rule_key": f"gateway-cascade:{svc}:{name.lower()}",
                "first_seen": ts_str,
                "last_seen": ts_str
            })
            alert_counter += 1

    # =========================================================================
    # INCIDENT 3: Payment Worker Memory Leak & OOM Kill (67 alerts)
    # Starts at 2026-10-28T18:00:00Z, root cause on payment-worker-01
    # =========================================================================
    inc3_start = datetime(2026, 10, 28, 18, 0, 0, tzinfo=timezone.utc)
    inc3_specs = [
        ("payment-worker-01", "HostMemoryExhaustionOOMKill", "critical", 28, "Out of Memory: Killed process 8192 (celery worker) total-vm:4194304kB, anon-rss:3952110kB"),
        ("celery-broker", "RabbitMQQueueBacklogHigh", "critical", 15, "Pending task message queue length > 12,000 without available consumer ACK"),
        ("invoice-generator", "BatchTaskExecutionTimeout", "high", 14, "Customer batch PDF invoice generation job failed: Worker socket terminated"),
        ("notification-dispatch", "DispatchTaskDelayed", "warning", 10, "Email/SMS notification dispatch latency elevated > 450 seconds")
    ]

    for svc, name, sev, count, msg in inc3_specs:
        lead_offset = 0 if svc == "payment-worker-01" else 20
        for i in range(count):
            t_sec = lead_offset + (i * (780 // count))
            dt = inc3_start + timedelta(seconds=t_sec)
            ts_str = dt.isoformat()
            alerts.append({
                "alert_id": f"ALT-400-{alert_counter:04d}",
                "timestamp": ts_str,
                "timestamp_epoch": dt.timestamp(),
                "source": "celery-monitor" if "worker" in svc or "celery" in svc else "systemd",
                "service": svc,
                "severity": sev,
                "name": name,
                "message": msg,
                "host": f"{svc}-host-{(i%2)+1}",
                "customer_ref": f"cust-{(i%3)+20:03d}",
                "incident_id": "INC-REAL-03",
                "rule_key": f"worker-cascade:{svc}:{name.lower()}",
                "first_seen": ts_str,
                "last_seen": ts_str
            })
            alert_counter += 1

    # Sort strictly by timestamp_epoch
    alerts.sort(key=lambda a: a["timestamp_epoch"])

    # Incidents ground truth
    incidents = [
        {
            "incident_id": "INC-REAL-01",
            "title": "Primary Database Connection Pool Exhaustion Outage",
            "root_cause_service": "production-postgres-db",
            "root_cause_type": "database_slowdown",
            "catalog_id": 10,
            "start_time": inc1_start.isoformat(),
            "end_time": (inc1_start + timedelta(seconds=820)).isoformat(),
            "alert_count": 195,
            "services": ["production-postgres-db", "auth-api", "billing-api", "order-processor", "user-service", "search-indexer"]
        },
        {
            "incident_id": "INC-REAL-02",
            "title": "API Gateway Ingress Storm & 504 Timeouts",
            "root_cause_service": "api-gateway",
            "root_cause_type": "network_partition",
            "catalog_id": 2,
            "start_time": inc2_start.isoformat(),
            "end_time": (inc2_start + timedelta(seconds=810)).isoformat(),
            "alert_count": 138,
            "services": ["api-gateway", "edge-router", "checkout-web", "customer-status-page", "public-ingress"]
        },
        {
            "incident_id": "INC-REAL-03",
            "title": "Payment Worker Memory Leak & Out-of-Memory Kill",
            "root_cause_service": "payment-worker-01",
            "root_cause_type": "worker_crash",
            "catalog_id": 4,
            "start_time": inc3_start.isoformat(),
            "end_time": (inc3_start + timedelta(seconds=790)).isoformat(),
            "alert_count": 67,
            "services": ["payment-worker-01", "celery-broker", "invoice-generator", "notification-dispatch"]
        }
    ]

    os.makedirs(os.path.join("data", "raw"), exist_ok=True)
    with open(os.path.join("data", "raw", "ps_400_alerts_3_incidents.json"), "w") as f:
        json.dump({"alerts": alerts, "incidents": incidents}, f, indent=2)

    with open(os.path.join("data", "raw", "ps_400_topology.json"), "w") as f:
        json.dump(topology, f, indent=2)

    # Overwrite alerts.json and topology.json as the canonical dataset
    with open(os.path.join("data", "raw", "alerts.json"), "w") as f:
        json.dump({"alerts": alerts, "incidents": incidents}, f, indent=2)

    with open(os.path.join("data", "raw", "topology.json"), "w") as f:
        json.dump(topology, f, indent=2)

    with open(os.path.join("data", "raw", "incidents.json"), "w") as f:
        json.dump({"incidents": incidents}, f, indent=2)

    print(f"[SUCCESS] Generated canonical Problem Statement dataset:")
    print(f"  - Total alerts: {len(alerts)}")
    print(f"  - Incident 1 (Database): {inc1_specs[0][3] + inc1_specs[1][3] + inc1_specs[2][3] + inc1_specs[3][3] + inc1_specs[4][3] + inc1_specs[5][3]} alerts")
    print(f"  - Incident 2 (Gateway):  {inc2_specs[0][3] + inc2_specs[1][3] + inc2_specs[2][3] + inc2_specs[3][3] + inc2_specs[4][3]} alerts")
    print(f"  - Incident 3 (Worker):   {inc3_specs[0][3] + inc3_specs[1][3] + inc3_specs[2][3] + inc3_specs[3][3]} alerts")
    print(f"  - Services: {len(topology['services'])}")
    print(f"  - Dependencies: {len(topology['dependencies'])}")

if __name__ == "__main__":
    generate_dataset()
