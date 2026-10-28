#!/usr/bin/env python3
"""
Synthetic data generator for AO-01 alert correlation benchmark.
Generates:
1. 70-service microservices platform dependency graph (directed graph, A -> B means A depends on B).
2. 3-4 weeks of alert history (~600 alerts/day) with timestamps, sources, severities, hosts, messages.
3. 10 realistic ground-truth incidents drawn from the 18 root-cause server catalogue:
   - Database slowdown, OOM leak, Disk full, Traffic spike, Bad deployment, Network partition,
     DNS failure, SSL cert expiry, Third-party gateway outage, Connection pool exhaustion.
4. Overlapping incidents for anti-chaining validation.
5. Novel rule appearing only in the final incident.
6. Recurring noise rules (flapping health checks, nightly backup CPU spikes) that never link to incidents.
"""

import json
import random
import os
from datetime import datetime, timedelta, timezone

def generate_topology():
    """Generates a realistic 70-service dependency graph across 5 architectural tiers."""
    tiers = {
        "edge": [
            "edge-cdn", "edge-waf", "dns-resolver", "ssl-terminator"
        ],
        "gateway": [
            "api-gateway", "mobile-bff", "web-bff", "partner-gateway", "webhook-ingress"
        ],
        "service": [
            "auth-service", "user-service", "cart-service", "order-service", "payment-service",
            "inventory-service", "catalog-service", "pricing-service", "notification-service",
            "search-service", "recommendation-service", "shipping-service", "billing-service",
            "coupon-service", "fraud-detection", "audit-service", "reporting-service",
            "email-dispatcher", "sms-gateway-client", "analytics-collector", "session-manager",
            "review-service", "wishlist-service", "merchant-portal-api", "customer-support-api",
            "tax-calculator", "currency-converter", "pdf-generator", "export-worker",
            "image-resizer", "file-storage-api", "warehouse-sync", "returns-service",
            "loyalty-service", "giftcard-service", "checkout-orchestrator", "feed-aggregator",
            "rate-limiter", "feature-flags-service", "event-stream-router", "subscription-manager"
        ],
        "datastore": [
            "users-db", "orders-db", "payments-db", "inventory-db", "catalog-db",
            "session-redis", "cache-redis-cluster", "search-elasticsearch",
            "events-kafka", "jobs-rabbitmq", "timeseries-influx", "audit-postgres",
            "warehouse-replica-db", "reporting-olap-db"
        ],
        "thirdparty": [
            "stripe-api", "sendgrid-smtp", "twilio-sms-api", "google-maps-api",
            "aws-s3-endpoint", "taxjar-api", "cloud-kms", "datadog-agent", "pagerduty-webhook", "elastic-cloud"
        ]
    }

    services = []
    dependencies = {}
    applications = {}

    # Map services to applications
    app_mapping = {
        "edge": "networking-edge",
        "gateway": "ingress-routing",
        "auth-service": "identity-app",
        "user-service": "identity-app",
        "session-manager": "identity-app",
        "order-service": "order-management",
        "cart-service": "order-management",
        "checkout-orchestrator": "order-management",
        "shipping-service": "logistics-app",
        "warehouse-sync": "logistics-app",
        "returns-service": "logistics-app",
        "payment-service": "payments-app",
        "billing-service": "payments-app",
        "fraud-detection": "payments-app",
        "inventory-service": "inventory-app",
        "pricing-service": "inventory-app",
        "catalog-service": "catalog-search-app",
        "search-service": "catalog-search-app",
        "recommendation-service": "catalog-search-app",
        "notification-service": "comms-app",
        "email-dispatcher": "comms-app",
        "sms-gateway-client": "comms-app",
    }

    all_service_names = []
    for tier, s_list in tiers.items():
        for s in s_list:
            all_service_names.append(s)
            app = app_mapping.get(s, f"{s.split('-')[0]}-app")
            applications[s] = app
            dependencies[s] = []

    # Setup realistic dependencies (A depends on B)
    # Edge depends on Gateway
    dependencies["edge-cdn"] = ["api-gateway", "web-bff"]
    dependencies["edge-waf"] = ["api-gateway", "partner-gateway"]
    dependencies["ssl-terminator"] = ["edge-cdn", "edge-waf"]

    # Gateway depends on Services
    dependencies["api-gateway"] = ["auth-service", "session-manager", "rate-limiter", "feature-flags-service"]
    dependencies["mobile-bff"] = ["api-gateway", "cart-service", "catalog-service", "order-service"]
    dependencies["web-bff"] = ["api-gateway", "user-service", "catalog-service", "search-service"]
    dependencies["partner-gateway"] = ["auth-service", "order-service", "inventory-service"]

    # Business services dependencies
    dependencies["checkout-orchestrator"] = ["cart-service", "order-service", "payment-service", "inventory-service", "tax-calculator"]
    dependencies["order-service"] = ["orders-db", "inventory-service", "payment-service", "notification-service", "events-kafka"]
    dependencies["cart-service"] = ["session-redis", "pricing-service", "catalog-service", "coupon-service"]
    dependencies["payment-service"] = ["payments-db", "fraud-detection", "stripe-api", "billing-service", "cloud-kms"]
    dependencies["billing-service"] = ["payments-db", "pdf-generator", "notification-service"]
    dependencies["inventory-service"] = ["inventory-db", "warehouse-sync", "events-kafka"]
    dependencies["catalog-service"] = ["catalog-db", "cache-redis-cluster", "search-service"]
    dependencies["search-service"] = ["search-elasticsearch", "catalog-db"]
    dependencies["recommendation-service"] = ["catalog-service", "search-elasticsearch", "analytics-collector"]
    dependencies["notification-service"] = ["email-dispatcher", "sms-gateway-client", "jobs-rabbitmq"]
    dependencies["email-dispatcher"] = ["sendgrid-smtp", "audit-service"]
    dependencies["sms-gateway-client"] = ["twilio-sms-api", "audit-service"]
    dependencies["auth-service"] = ["users-db", "session-redis", "cloud-kms"]
    dependencies["user-service"] = ["users-db", "audit-service"]
    dependencies["fraud-detection"] = ["payments-db", "events-kafka", "session-redis"]
    dependencies["shipping-service"] = ["google-maps-api", "orders-db", "events-kafka"]
    dependencies["tax-calculator"] = ["taxjar-api", "cache-redis-cluster"]
    dependencies["warehouse-sync"] = ["inventory-db", "jobs-rabbitmq"]
    dependencies["returns-service"] = ["orders-db", "inventory-service", "shipping-service"]
    dependencies["loyalty-service"] = ["users-db", "orders-db"]
    dependencies["analytics-collector"] = ["timeseries-influx", "events-kafka"]
    dependencies["export-worker"] = ["warehouse-replica-db", "aws-s3-endpoint"]
    dependencies["reporting-service"] = ["reporting-olap-db", "export-worker"]
    dependencies["audit-service"] = ["audit-postgres", "events-kafka"]
    dependencies["session-manager"] = ["session-redis"]

    # Assemble service list
    for tier, s_list in tiers.items():
        for s in s_list:
            services.append({
                "service": s,
                "tier": tier,
                "application": applications[s],
                "dependencies": dependencies[s]
            })

    return services, dependencies

def generate_synthetic_dataset(output_dir="data/synthetic", days=28, seed=42):
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    services, deps = generate_topology()

    with open(os.path.join(output_dir, "topology.json"), "w") as f:
        json.dump({"services": services}, f, indent=2)

    base_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    total_seconds = days * 86400

    alerts = []
    incidents = []

    # 1. Incident scenarios mapped to the 18 root causes
    incident_scenarios = [
        {
            "id": "INC-001",
            "day": 3,
            "hour": 14,
            "root_cause_service": "orders-db",
            "root_cause_type": "database_slowdown",
            "catalog_id": 1,
            "title": "Database slowdown on orders-db due to unindexed query lock",
            "cascade_hops": [
                ("orders-db", "DBConnectionLatencyHigh", "PostgreSQL query execution latency > 15000ms", "critical", 0),
                ("orders-db", "LockContentionDetected", "Row lock contention on orders table > 95%", "critical", 2),
                ("order-service", "HTTP504GatewayTimeout", "Upstream DB timeout on save_order", "critical", 4),
                ("order-service", "CPUThrottlingAlert", "Thread starvation waiting on DB pool connections", "high", 6),
                ("checkout-orchestrator", "OrderPlacementFailed", "Downstream order-service returned 504", "critical", 7),
                ("cart-service", "CheckoutHandoffFailed", "Checkout orchestrator unresponsive", "high", 9),
                ("mobile-bff", "ErrorRateExceededThreshold", "HTTP 5xx rate > 25% on /v1/checkout", "high", 11),
                ("web-bff", "ErrorRateExceededThreshold", "HTTP 5xx rate > 30% on /web/orders", "high", 12),
                ("api-gateway", "HighLatencyP99", "P99 gateway latency > 8000ms on order routes", "warning", 14),
                ("edge-waf", "ClientErrorBurst", "504 response burst from api-gateway", "warning", 16),
                ("edge-cdn", "StatusPageDegradedWarning", "Automated synthetic check failed for checkout flow", "critical", 18)
            ]
        },
        {
            "id": "INC-002",
            "day": 6,
            "hour": 9,
            "root_cause_service": "cart-service",
            "root_cause_type": "memory_leak_oom",
            "catalog_id": 2,
            "title": "Out of memory leak in cart-service session serialization",
            "cascade_hops": [
                ("cart-service", "MemoryUsageCritical", "JVM Old Gen Heap usage > 96%", "critical", 0),
                ("cart-service", "ProcessRestartOOMKilled", "Container restarted due to Linux OOM killer", "critical", 5),
                ("session-redis", "ClientConnectionReset", "Abrupt TCP connection termination from cart-service", "warning", 6),
                ("checkout-orchestrator", "CartServiceUnreachable", "Connection refused connecting to cart-service:8080", "high", 7),
                ("mobile-bff", "CartFetchFailure", "Unable to retrieve cart items for active sessions", "high", 8),
                ("api-gateway", "UpstreamServiceDown", "Upstream cart-service health check failing", "high", 9)
            ]
        },
        {
            "id": "INC-003",
            "day": 9,
            "hour": 22,
            "root_cause_service": "payments-db",
            "root_cause_type": "disk_full",
            "catalog_id": 3,
            "title": "Disk full on payments-db WAL volume",
            "cascade_hops": [
                ("payments-db", "DiskSpaceLow", "WAL directory disk free space < 2%", "critical", 0),
                ("payments-db", "ReadOnlyModeTriggered", "PostgreSQL switched to read-only due to ENOSPC", "critical", 3),
                ("payment-service", "PaymentTransactionWriteError", "Cannot insert into payment_transactions: DB read-only", "critical", 4),
                ("billing-service", "InvoiceLedgerFailed", "Ledger synchronization failed due to DB write error", "high", 6),
                ("checkout-orchestrator", "PaymentDeclinedError", "Payment service returned 500 DB write error", "critical", 7),
                ("partner-gateway", "PartnerPaymentNotificationFailed", "Webhook delivery aborted for completed charges", "warning", 9)
            ]
        },
        {
            "id": "INC-004",
            "day": 13,
            "hour": 16,
            "root_cause_service": "edge-cdn",
            "root_cause_type": "traffic_spike",
            "catalog_id": 4,
            "title": "Traffic spike and bot flood on flash sale event",
            "cascade_hops": [
                ("edge-cdn", "RequestRateSurge", "Ingress request rate > 400% baseline", "high", 0),
                ("edge-waf", "RateLimitThresholdExceeded", "WAF rate limit triggered for top ASNs", "warning", 2),
                ("api-gateway", "CPUUtilizationHigh", "Gateway CPU utilization > 92%", "high", 3),
                ("rate-limiter", "RedisRateLimitQueryLatency", "Rate limiter query backlog elevated", "warning", 4),
                ("catalog-service", "CatalogCacheMissSpike", "Catalog cache misses surged 350%", "warning", 5),
                ("catalog-db", "ReadIOPSLimitReached", "Read IOPS maxed out on catalog replica", "high", 6)
            ]
        },
        {
            "id": "INC-005",
            "day": 16,
            "hour": 11,
            "root_cause_service": "user-service",
            "root_cause_type": "bad_deployment",
            "catalog_id": 5,
            "title": "Bad deployment of user-service v2.14 schema migration",
            "cascade_hops": [
                ("user-service", "DeploymentRolloutErrorRate", "HTTP 500 error rate surged to 45% immediately after deploy", "critical", 0),
                ("user-service", "DatabaseQuerySyntaxError", "Missing column 'mfa_enforced' on users table", "critical", 1),
                ("auth-service", "UserValidationFailed", "User validation failed in auth pipeline", "critical", 3),
                ("api-gateway", "AuthTokenValidationTimeout", "Token verification latency exceeded 2000ms", "high", 4),
                ("web-bff", "UserProfileRenderFailed", "BFF unable to load user profile", "high", 5)
            ]
        },
        {
            "id": "INC-006",
            "day": 19,
            "hour": 3,
            "root_cause_service": "cloud-kms",
            "root_cause_type": "network_partition",
            "catalog_id": 6,
            "title": "Network partition / unreachable cloud-kms key provider",
            "cascade_hops": [
                ("cloud-kms", "EndpointTimeout", "TCP handshake timeout to kms.cloud.internal", "critical", 0),
                ("auth-service", "TokenDecryptionFailed", "Unable to decrypt JWT secret from KMS", "critical", 2),
                ("payment-service", "CardDataDecryptionFailed", "Unable to decrypt payment token", "critical", 3),
                ("checkout-orchestrator", "SecurityModuleTimeout", "Security token decrypt timed out", "high", 5)
            ]
        },
        {
            "id": "INC-007",
            "day": 21,
            "hour": 8,
            "root_cause_service": "dns-resolver",
            "root_cause_type": "dns_failure",
            "catalog_id": 7,
            "title": "Internal DNS resolver failure across service cluster",
            "cascade_hops": [
                ("dns-resolver", "QueryResolutionFailure", "CoreDNS resolution error rate > 60%", "critical", 0),
                ("shipping-service", "HostNotFoundGoogleMaps", "Name resolution failed for maps.googleapis.com", "high", 2),
                ("email-dispatcher", "HostNotFoundSendgrid", "Name resolution failed for smtp.sendgrid.net", "high", 3),
                ("tax-calculator", "HostNotFoundTaxjar", "Name resolution failed for api.taxjar.com", "high", 4)
            ]
        },
        {
            "id": "INC-008",
            "day": 23,
            "hour": 0,
            "root_cause_service": "ssl-terminator",
            "root_cause_type": "expired_certificate",
            "catalog_id": 8,
            "title": "Expired SSL/TLS wildcard certificate on edge ingress",
            "cascade_hops": [
                ("ssl-terminator", "SSLCertificateExpired", "Wildcard cert for *.example.com expired at 00:00:00 UTC", "critical", 0),
                ("edge-cdn", "UpstreamHandshakeFailed", "TLS handshake validation error from client probes", "critical", 1),
                ("mobile-bff", "TLSClientVerificationError", "Mobile SDK TLS handshake rejected", "high", 3),
                ("partner-gateway", "MutualTLSHandshakeRejected", "Partner API certificate validation failed", "high", 4)
            ]
        },
        # Overlapping Incidents (Day 25, 14:00 - anti-chaining test)
        {
            "id": "INC-009A",
            "day": 25,
            "hour": 14,
            "minute": 5,
            "root_cause_service": "stripe-api",
            "root_cause_type": "third_party_outage",
            "catalog_id": 9,
            "title": "Third-party payment gateway outage on Stripe API",
            "cascade_hops": [
                ("stripe-api", "ExternalService503Unavailable", "Stripe API returning HTTP 503 Service Unavailable", "critical", 0),
                ("payment-service", "PaymentGatewayTimeout", "Charge attempt timed out after 3 retries", "critical", 1),
                ("billing-service", "SubscriptionChargeFailed", "Stripe billing charge failed", "high", 3),
                ("checkout-orchestrator", "PaymentProcessingFailed", "Payment service returned upstream gateway error", "critical", 4)
            ]
        },
        {
            "id": "INC-009B",  # Concurrent incident in separate subsystem!
            "day": 25,
            "hour": 14,
            "minute": 12,
            "root_cause_service": "search-elasticsearch",
            "root_cause_type": "connection_pool_exhaustion",
            "catalog_id": 10,
            "title": "Connection pool exhaustion on search-elasticsearch cluster",
            "cascade_hops": [
                ("search-elasticsearch", "ConnectionPoolExhausted", "Active connections 100/100, pending queue > 500", "critical", 0),
                ("search-service", "SearchQueryExecutionTimeout", "Query rejected due to ES connection timeout", "high", 2),
                ("catalog-service", "ProductSearchDegraded", "Search fallback activated due to search-service failure", "warning", 3),
                ("recommendation-service", "ModelCandidateFetchError", "Failed to retrieve candidate items from ES", "warning", 4)
            ]
        },
        # Final incident featuring a NOVEL alert rule never seen in history!
        {
            "id": "INC-010",
            "day": 27,
            "hour": 17,
            "root_cause_service": "cache-redis-cluster",
            "root_cause_type": "cache_failure",
            "catalog_id": 12,
            "title": "Cache failure and cluster node eviction on cache-redis-cluster",
            "cascade_hops": [
                ("cache-redis-cluster", "NovelRedisSplitBrainDetected", "CRITICAL: Split-brain detected across Redis shards", "critical", 0), # NOVEL RULE!
                ("catalog-service", "CacheMissSurgeWarning", "Redis cache miss rate reached 99.4%", "high", 2),
                ("catalog-db", "PrimaryDatabaseLoadSpike", "Database CPU reached 98% due to cache bypass", "critical", 4),
                ("pricing-service", "PriceLookupLatencyHigh", "Price retrieval latency > 2500ms", "high", 5)
            ]
        }
    ]

    alert_id_counter = 1000

    # Generate incident alerts
    for inc in incident_scenarios:
        inc_start = base_time + timedelta(days=inc["day"], hours=inc["hour"], minutes=inc.get("minute", 0))
        inc_alerts = []

        for svc, alert_name, msg, sev, delay_min in inc["cascade_hops"]:
            t = inc_start + timedelta(minutes=delay_min, seconds=random.randint(0, 45))
            alert_id_counter += 1
            a_id = f"ALT-{alert_id_counter}"
            
            # Host & customer references
            host = f"srv-{svc}-{random.randint(10, 99)}.prod.internal"
            cust = f"cust-{random.randint(100, 999)}" if random.random() < 0.4 else None

            alert_obj = {
                "alert_id": a_id,
                "timestamp": t.isoformat(),
                "timestamp_epoch": t.timestamp(),
                "source": "prometheus" if "CPU" in alert_name or "Memory" in alert_name or "Disk" in alert_name else ("datadog" if "Rate" in alert_name or "Latency" in alert_name else "sentry"),
                "service": svc,
                "severity": sev,
                "name": alert_name,
                "message": f"[{sev.upper()}] {msg} on {host} (ref: {cust or 'system'})",
                "host": host,
                "customer_ref": cust,
                "incident_id": inc["id"]
            }
            alerts.append(alert_obj)
            inc_alerts.append(alert_obj)

        incidents.append({
            "incident_id": inc["id"],
            "title": inc["title"],
            "root_cause_service": inc["root_cause_service"],
            "root_cause_type": inc["root_cause_type"],
            "catalog_id": inc["catalog_id"],
            "start_time": min(a["timestamp"] for a in inc_alerts),
            "end_time": max(a["timestamp"] for a in inc_alerts),
            "alert_count": len(inc_alerts),
            "services": list(set(a["service"] for a in inc_alerts))
        })

    # 2. Generate Background Operational Noise (~550-650 alerts per day)
    # Define recurring noise patterns that NEVER link to incidents
    noise_rules = [
        # Nightly backup CPU spikes (Scheduled job collision)
        {"service": "reporting-olap-db", "name": "NightlyBackupCPUSpike", "sev": "warning", "source": "prometheus",
         "msg": "Scheduled backup snapshot running; CPU spike to 85%", "type": "periodic_nightly"},
        {"service": "export-worker", "name": "CronBatchSyncJobRunning", "sev": "info", "source": "cron",
         "msg": "Hourly analytics aggregation batch completed with transient lag", "type": "periodic_hourly"},
        # Flapping health checks
        {"service": "image-resizer", "name": "HealthCheckProbeFlapping", "sev": "warning", "source": "uptime-kuma",
         "msg": "HTTP GET /health probe timeout > 1000ms from zone us-east", "type": "flapping"},
        {"service": "file-storage-api", "name": "S3Transient503Retried", "sev": "info", "source": "datadog",
         "msg": "S3 multipart upload received transient 503 SlowDown; retried successfully", "type": "transient"},
        {"service": "sms-gateway-client", "name": "CarrierDeliveryReportDelayed", "sev": "info", "source": "twilio",
         "msg": "DLR callback queue age > 45s due to carrier throughput limit", "type": "noisy_background"},
        {"service": "analytics-collector", "name": "BufferFlushHighWatermark", "sev": "warning", "source": "prometheus",
         "msg": "Memory buffer reached 80% capacity before scheduled disk flush", "type": "harmless_spike"},
        {"service": "user-service", "name": "PasswordResetRateNotice", "sev": "info", "source": "sentry",
         "msg": "User password reset requests normal daily variance notice", "type": "routine"},
        {"service": "feed-aggregator", "name": "ExternalRSSFeedTimeout", "sev": "warning", "source": "datadog",
         "msg": "Public partner RSS feed connection timed out after 5000ms", "type": "routine"}
    ]

    # Populate 28 days of background noise
    for day in range(days):
        day_date = base_time + timedelta(days=day)
        # 550 to 650 background noise alerts per day
        daily_noise_target = random.randint(550, 650)
        
        for _ in range(daily_noise_target):
            # Select rule
            rule = random.choice(noise_rules)
            
            # Timing
            if rule["type"] == "periodic_nightly":
                # Fires between 02:00 and 04:00 UTC
                t = day_date + timedelta(hours=random.randint(2, 3), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
            elif rule["type"] == "periodic_hourly":
                t = day_date + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 5), seconds=random.randint(0, 59))
            else:
                t = day_date + timedelta(seconds=random.randint(0, 86399))

            alert_id_counter += 1
            a_id = f"ALT-{alert_id_counter}"
            host = f"srv-{rule['service']}-{random.randint(10, 99)}.prod.internal"
            cust = f"cust-{random.randint(100, 999)}" if random.random() < 0.25 else None

            alerts.append({
                "alert_id": a_id,
                "timestamp": t.isoformat(),
                "timestamp_epoch": t.timestamp(),
                "source": rule["source"],
                "service": rule["service"],
                "severity": rule["sev"],
                "name": rule["name"],
                "message": f"[{rule['sev'].upper()}] {rule['msg']} on {host}",
                "host": host,
                "customer_ref": cust,
                "incident_id": None  # Unlinked ground truth noise
            })

    # Sort alerts chronologically
    alerts.sort(key=lambda x: x["timestamp_epoch"])

    # Save to disk
    alerts_file = os.path.join(output_dir, "alerts.json")
    incidents_file = os.path.join(output_dir, "incidents.json")

    with open(alerts_file, "w") as f:
        json.dump({"alerts": alerts}, f, indent=2)

    with open(incidents_file, "w") as f:
        json.dump({"incidents": incidents}, f, indent=2)

    print(f"Generated {len(alerts)} alerts across {days} days.")
    print(f"Generated {len(incidents)} real ground-truth incidents.")
    print(f"Topology services: {len(services)}.")
    return alerts, incidents, services

if __name__ == "__main__":
    generate_synthetic_dataset()
